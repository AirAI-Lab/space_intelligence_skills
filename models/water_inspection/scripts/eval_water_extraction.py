#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水体区域提取对比评估

对比不同 RADIO 配置的水体提取能力:
1. RADIO only (SigLIP2)
2. RADIO + DINOv3
3. RADIO + SAM3
4. RADIO + DINOv3 + SAM3

目标: 评估哪个配置最能准确提取水体区域

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import sys
import json
import yaml
import numpy as np
from pathlib import Path
from collections import defaultdict
from typing import Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import cv2


def load_dataset(dataset_dir):
    """加载数据集"""
    meta_dir = Path(dataset_dir) / "meta"
    samples = []
    for meta_file in sorted(meta_dir.glob("*.json")):
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["image_path"] = str(Path(dataset_dir) / "images" / meta["image"])
        meta["mask_dir"] = str(Path(dataset_dir) / "masks")
        samples.append(meta)
    return samples


def compute_iou(mask1: np.ndarray, mask2: np.ndarray) -> float:
    """计算 IoU"""
    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()
    if union == 0:
        return 1.0 if intersection == 0 else 0.0
    return intersection / union


def compute_metrics(pred_mask: np.ndarray, gt_mask: np.ndarray) -> Dict[str, float]:
    """计算评估指标"""
    # 确保是布尔类型
    pred_mask = pred_mask.astype(bool)
    gt_mask = gt_mask.astype(bool)

    # IoU
    iou = compute_iou(pred_mask, gt_mask)

    # Precision, Recall, F1
    tp = np.logical_and(pred_mask, gt_mask).sum()
    fp = np.logical_and(pred_mask, ~gt_mask).sum()
    fn = np.logical_and(~pred_mask, gt_mask).sum()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "iou": iou,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def get_water_gt_mask(sample: dict) -> np.ndarray:
    """获取水体的 GT 掩码"""
    mask_dir = sample["mask_dir"]
    image_path = sample["image_path"]

    # 读取图像尺寸
    image = cv2.imread(image_path)
    if image is None:
        return None
    h, w = image.shape[:2]

    # 合并所有水类别的掩码
    water_mask = np.zeros((h, w), dtype=bool)

    for cls_info in sample.get("classes", []):
        mask_file = cls_info.get("mask_file")
        if mask_file:
            mask_path = os.path.join(mask_dir, mask_file)
            if os.path.exists(mask_path):
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                if mask is not None:
                    # 调整尺寸
                    if mask.shape != (h, w):
                        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
                    water_mask = water_mask | (mask > 127)

    return water_mask


def extract_water_region_radio(segmentor, image: np.ndarray, threshold: float = 0.1) -> np.ndarray:
    """
    使用 RADIO 提取水体区域

    策略: 合并所有水类别的热图，取最大值
    """
    # 定义水相关类别
    water_prompts = {
        "water": [
            "water surface in river or lake",
            "flowing water in channel",
            "standing water body",
        ]
    }

    # 简单配置
    classes_config = {
        "water": {"prompts": water_prompts["water"]},
        "background": {"prompts": ["concrete", "land", "vegetation", "sky"]}
    }

    # 计算热图
    heatmaps = segmentor.compute_patch_similarity(image, classes_config)

    if "water" not in heatmaps:
        return None

    # 阈值化
    water_heatmap = heatmaps["water"]
    water_mask = water_heatmap > threshold

    return water_mask


def extract_water_region_unified(segmentor, image: np.ndarray, threshold: float = 0.1) -> np.ndarray:
    """
    使用统一的水体提示词提取水体区域

    策略: 使用单一 "water" 类别，合并所有水类别的热图
    """
    # 获取所有水类别的热图
    classes_config = {
        "water": {
            "prompts": [
                "water surface in natural river",
                "water body in lake or reservoir",
                "flowing water in channel",
                "standing water",
            ]
        },
        "background": {
            "prompts": [
                "concrete embankment",
                "land and vegetation",
                "sky and clouds",
                "buildings and structures",
            ]
        }
    }

    heatmaps = segmentor.compute_patch_similarity(image, classes_config)

    if "water" not in heatmaps:
        return None

    water_heatmap = heatmaps["water"]
    water_mask = water_heatmap > threshold

    return water_mask


def evaluate_config(
    config_name: str,
    segmentor,
    samples: list,
    extract_fn,
    threshold: float = 0.1,
) -> Dict[str, float]:
    """评估单个配置"""
    print(f"\n评估配置: {config_name}")
    print("-" * 60)

    all_metrics = []

    for i, sample in enumerate(samples[:50]):  # 评估前 50 个样本
        image_path = sample["image_path"]
        if not os.path.exists(image_path):
            continue

        image = cv2.imread(image_path)
        if image is None:
            continue

        # 获取 GT 水体掩码
        gt_mask = get_water_gt_mask(sample)
        if gt_mask is None or not gt_mask.any():
            continue

        # 提取预测水体掩码
        try:
            pred_mask = extract_fn(segmentor, image, threshold)
            if pred_mask is None:
                continue

            # 调整尺寸
            if pred_mask.shape != gt_mask.shape:
                pred_mask = cv2.resize(
                    pred_mask.astype(np.uint8),
                    (gt_mask.shape[1], gt_mask.shape[0]),
                    interpolation=cv2.INTER_NEAREST
                ).astype(bool)

            # 计算指标
            metrics = compute_metrics(pred_mask, gt_mask)
            all_metrics.append(metrics)

            if i < 10:  # 打印前 10 个样本
                status = "✓" if metrics["iou"] > 0.5 else "✗"
                print(f"  {status} {sample['image']}: IoU={metrics['iou']:.3f}, F1={metrics['f1']:.3f}")

        except Exception as e:
            print(f"  ✗ {sample['image']}: {e}")
            continue

    if not all_metrics:
        return {}

    # 计算平均指标
    avg_metrics = {
        "iou": np.mean([m["iou"] for m in all_metrics]),
        "precision": np.mean([m["precision"] for m in all_metrics]),
        "recall": np.mean([m["recall"] for m in all_metrics]),
        "f1": np.mean([m["f1"] for m in all_metrics]),
        "num_samples": len(all_metrics),
    }

    print(f"\n平均指标 ({len(all_metrics)} 样本):")
    print(f"  IoU: {avg_metrics['iou']:.3f}")
    print(f"  Precision: {avg_metrics['precision']:.3f}")
    print(f"  Recall: {avg_metrics['recall']:.3f}")
    print(f"  F1: {avg_metrics['f1']:.3f}")

    return avg_metrics


def main():
    print("=" * 70)
    print("水体区域提取对比评估")
    print("目标: 评估不同 RADIO 配置的水体提取能力")
    print("=" * 70)

    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "water_inspection.yaml"
    dataset_dir = project_root / "data" / "datasets"

    # 加载配置
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 加载数据集
    print(f"\n加载数据集: {dataset_dir}")
    samples = load_dataset(str(dataset_dir))
    print(f"  样本数: {len(samples)}")

    # 容器内路径
    radio_code_dir = "/app/models/NVlabs_RADIO"
    siglip2_dir = "/app/models/siglip2-giant-opt-patch16-384"
    checkpoint_path = "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"

    results = {}

    # ============ 配置 1: RADIO only ============
    print("\n" + "=" * 70)
    print("配置 1: RADIO only (SigLIP2)")
    print("=" * 70)

    from models.open_vocab.radseg_segmentor import RADSegWaterSegmentor

    segmentor_radio = RADSegWaterSegmentor(
        checkpoint_path=checkpoint_path,
        radio_code_dir=radio_code_dir,
        siglip2_dir=siglip2_dir,
        device="cuda",
        input_size=config["cloud"]["radio"]["inference"]["input_size"],
        config=config,
        use_scra=True,
        use_dino=False,
        use_sam=False,
    )

    results["RADIO_only"] = evaluate_config(
        "RADIO only",
        segmentor_radio,
        samples,
        extract_water_region_unified,
        threshold=0.1,
    )

    # 清理
    del segmentor_radio
    torch.cuda.empty_cache()

    # ============ 配置 2: RADIO + DINOv3 ============
    print("\n" + "=" * 70)
    print("配置 2: RADIO + DINOv3")
    print("=" * 70)

    segmentor_dino = RADSegWaterSegmentor(
        checkpoint_path=checkpoint_path,
        radio_code_dir=radio_code_dir,
        siglip2_dir=siglip2_dir,
        device="cuda",
        input_size=config["cloud"]["radio"]["inference"]["input_size"],
        config=config,
        use_scra=True,
        use_dino=True,
        use_sam=False,
    )

    results["RADIO_DINOv3"] = evaluate_config(
        "RADIO + DINOv3",
        segmentor_dino,
        samples,
        extract_water_region_unified,
        threshold=0.1,
    )

    # 清理
    del segmentor_dino
    torch.cuda.empty_cache()

    # ============ 配置 3: RADIO + SAM3 ============
    print("\n" + "=" * 70)
    print("配置 3: RADIO + SAM3")
    print("=" * 70)

    segmentor_sam = RADSegWaterSegmentor(
        checkpoint_path=checkpoint_path,
        radio_code_dir=radio_code_dir,
        siglip2_dir=siglip2_dir,
        device="cuda",
        input_size=config["cloud"]["radio"]["inference"]["input_size"],
        config=config,
        use_scra=True,
        use_dino=False,
        use_sam=True,
    )

    results["RADIO_SAM3"] = evaluate_config(
        "RADIO + SAM3",
        segmentor_sam,
        samples,
        extract_water_region_unified,
        threshold=0.1,
    )

    # 清理
    del segmentor_sam
    torch.cuda.empty_cache()

    # ============ 配置 4: RADIO + DINOv3 + SAM3 ============
    print("\n" + "=" * 70)
    print("配置 4: RADIO + DINOv3 + SAM3")
    print("=" * 70)

    segmentor_full = RADSegWaterSegmentor(
        checkpoint_path=checkpoint_path,
        radio_code_dir=radio_code_dir,
        siglip2_dir=siglip2_dir,
        device="cuda",
        input_size=config["cloud"]["radio"]["inference"]["input_size"],
        config=config,
        use_scra=True,
        use_dino=True,
        use_sam=True,
    )

    results["RADIO_DINOv3_SAM3"] = evaluate_config(
        "RADIO + DINOv3 + SAM3",
        segmentor_full,
        samples,
        extract_water_region_unified,
        threshold=0.1,
    )

    # 清理
    del segmentor_full
    torch.cuda.empty_cache()

    # ============ 对比总结 ============
    print("\n" + "=" * 70)
    print("对比总结")
    print("=" * 70)

    print(f"\n{'配置':<25} {'IoU':>10} {'Precision':>12} {'Recall':>10} {'F1':>10}")
    print("-" * 70)

    for config_name, metrics in results.items():
        if metrics:
            print(f"{config_name:<25} "
                  f"{metrics['iou']:>10.3f} "
                  f"{metrics['precision']:>12.3f} "
                  f"{metrics['recall']:>10.3f} "
                  f"{metrics['f1']:>10.3f}")

    # 找出最佳配置
    best_config = max(results.keys(), key=lambda k: results[k].get("iou", 0))
    print(f"\n最佳配置: {best_config}")
    print(f"  IoU: {results[best_config]['iou']:.3f}")
    print(f"  F1: {results[best_config]['f1']:.3f}")

    # 结论
    print("\n" + "=" * 70)
    print("结论与建议")
    print("=" * 70)

    best_iou = results[best_config]["iou"]

    if best_iou > 0.7:
        print("✓ 水体提取效果良好，可以用于后续水质分类")
        print("  建议策略:")
        print("  1. 使用最佳配置提取水体区域")
        print("  2. 在水体区域内训练水质分类头")
        print("  3. 结合颜色语义提示词进行细分类")
    elif best_iou > 0.5:
        print("△ 水体提取效果中等，可能需要进一步优化")
        print("  建议:")
        print("  1. 调整阈值或提示词")
        print("  2. 增加水体样本进行微调")
    else:
        print("✗ 水体提取效果不理想，需要重新设计策略")
        print("  建议:")
        print("  1. 使用传统图像处理方法 (颜色阈值)")
        print("  2. 训练专门的水体分割模型")


if __name__ == "__main__":
    main()
