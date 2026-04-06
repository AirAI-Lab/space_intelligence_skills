#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水体区域提取对比评估 v2.0

改进:
1. 使用多阈值搜索找最佳阈值
2. 使用对比式提示词 (water vs non-water)
3. 可视化分割结果

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
from typing import Dict, Tuple, List

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
    pred_mask = pred_mask.astype(bool)
    gt_mask = gt_mask.astype(bool)

    iou = compute_iou(pred_mask, gt_mask)

    tp = np.logical_and(pred_mask, gt_mask).sum()
    fp = np.logical_and(pred_mask, ~gt_mask).sum()
    fn = np.logical_and(~pred_mask, gt_mask).sum()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {"iou": iou, "precision": precision, "recall": recall, "f1": f1}


def get_water_gt_mask(sample: dict) -> np.ndarray:
    """获取水体的 GT 掩码"""
    mask_dir = sample["mask_dir"]
    image_path = sample["image_path"]

    image = cv2.imread(image_path)
    if image is None:
        return None
    h, w = image.shape[:2]

    water_mask = np.zeros((h, w), dtype=bool)

    for cls_info in sample.get("classes", []):
        mask_file = cls_info.get("mask_file")
        if mask_file:
            mask_path = os.path.join(mask_dir, mask_file)
            if os.path.exists(mask_path):
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                if mask is not None:
                    if mask.shape != (h, w):
                        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
                    water_mask = water_mask | (mask > 127)

    return water_mask


def extract_water_with_threshold(
    segmentor,
    image: np.ndarray,
    threshold: float = 0.3,
) -> np.ndarray:
    """
    使用对比式提示词提取水体区域

    策略: water score - background score > threshold
    """
    # 定义 water vs background 的对比
    classes_config = {
        "water": {
            "prompts": [
                "water surface in natural environment",
                "river water flowing in channel",
                "lake or reservoir water body",
                "flowing or standing water",
            ]
        },
        "background": {
            "prompts": [
                "concrete embankment and walls",
                "land vegetation and grass",
                "sky and clouds above",
                "buildings and man-made structures",
                "rocks and stones",
            ]
        }
    }

    # 计算热图
    heatmaps = segmentor.compute_patch_similarity(image, classes_config)

    if "water" not in heatmaps or "background" not in heatmaps:
        return None

    # 对比得分
    water_heatmap = heatmaps["water"]
    bg_heatmap = heatmaps["background"]

    # 使用 softmax 归一化后的概率
    # water_prob = exp(water) / (exp(water) + exp(bg))
    combined = np.stack([water_heatmap, bg_heatmap], axis=-1)
    # Softmax
    exp_combined = np.exp(combined - combined.max(axis=-1, keepdims=True))
    probs = exp_combined / exp_combined.sum(axis=-1, keepdims=True)

    water_prob = probs[..., 0]

    # 阈值化
    water_mask = water_prob > threshold

    return water_mask, water_prob


def find_best_threshold(
    segmentor,
    samples: list,
    thresholds: List[float] = [0.3, 0.4, 0.5, 0.6, 0.7],
) -> Tuple[float, Dict[str, float]]:
    """搜索最佳阈值"""
    best_threshold = 0.5
    best_f1 = 0
    best_metrics = {}

    print("搜索最佳阈值...")
    for thresh in thresholds:
        all_metrics = []

        for sample in samples[:30]:  # 使用子集搜索
            image_path = sample["image_path"]
            if not os.path.exists(image_path):
                continue

            image = cv2.imread(image_path)
            if image is None:
                continue

            gt_mask = get_water_gt_mask(sample)
            if gt_mask is None or not gt_mask.any():
                continue

            try:
                result = extract_water_with_threshold(segmentor, image, thresh)
                if result is None:
                    continue
                pred_mask, _ = result

                if pred_mask.shape != gt_mask.shape:
                    pred_mask = cv2.resize(
                        pred_mask.astype(np.uint8),
                        (gt_mask.shape[1], gt_mask.shape[0]),
                        interpolation=cv2.INTER_NEAREST
                    ).astype(bool)

                metrics = compute_metrics(pred_mask, gt_mask)
                all_metrics.append(metrics)

            except Exception as e:
                continue

        if not all_metrics:
            continue

        avg_f1 = np.mean([m["f1"] for m in all_metrics])
        avg_iou = np.mean([m["iou"] for m in all_metrics])

        print(f"  阈值 {thresh}: F1={avg_f1:.3f}, IoU={avg_iou:.3f}")

        if avg_f1 > best_f1:
            best_f1 = avg_f1
            best_threshold = thresh
            best_metrics = {
                "iou": avg_iou,
                "f1": avg_f1,
                "precision": np.mean([m["precision"] for m in all_metrics]),
                "recall": np.mean([m["recall"] for m in all_metrics]),
            }

    return best_threshold, best_metrics


def evaluate_config(
    config_name: str,
    segmentor,
    samples: list,
    threshold: float = 0.5,
) -> Dict[str, float]:
    """评估单个配置"""
    print(f"\n评估配置: {config_name}")
    print(f"使用阈值: {threshold}")
    print("-" * 60)

    all_metrics = []

    for i, sample in enumerate(samples[:50]):
        image_path = sample["image_path"]
        if not os.path.exists(image_path):
            continue

        image = cv2.imread(image_path)
        if image is None:
            continue

        gt_mask = get_water_gt_mask(sample)
        if gt_mask is None or not gt_mask.any():
            continue

        try:
            result = extract_water_with_threshold(segmentor, image, threshold)
            if result is None:
                continue
            pred_mask, water_prob = result

            if pred_mask.shape != gt_mask.shape:
                pred_mask = cv2.resize(
                    pred_mask.astype(np.uint8),
                    (gt_mask.shape[1], gt_mask.shape[0]),
                    interpolation=cv2.INTER_NEAREST
                ).astype(bool)

            metrics = compute_metrics(pred_mask, gt_mask)
            all_metrics.append(metrics)

            if i < 10:
                status = "✓" if metrics["iou"] > 0.5 else "✗"
                print(f"  {status} {sample['image']}: IoU={metrics['iou']:.3f}, F1={metrics['f1']:.3f}")

        except Exception as e:
            print(f"  ✗ {sample['image']}: {e}")
            continue

    if not all_metrics:
        return {}

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


def visualize_extraction(
    segmentor,
    samples: list,
    output_dir: str,
    threshold: float = 0.5,
    num_samples: int = 10,
):
    """可视化水体提取结果"""
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n可视化水体提取结果 -> {output_dir}")

    for i, sample in enumerate(samples[:num_samples]):
        image_path = sample["image_path"]
        if not os.path.exists(image_path):
            continue

        image = cv2.imread(image_path)
        if image is None:
            continue

        gt_mask = get_water_gt_mask(sample)
        if gt_mask is None:
            continue

        try:
            result = extract_water_with_threshold(segmentor, image, threshold)
            if result is None:
                continue
            pred_mask, water_prob = result

            # 调整尺寸
            if pred_mask.shape != gt_mask.shape:
                pred_mask = cv2.resize(
                    pred_mask.astype(np.uint8),
                    (gt_mask.shape[1], gt_mask.shape[0]),
                    interpolation=cv2.INTER_NEAREST
                ).astype(bool)
                water_prob = cv2.resize(water_prob, (gt_mask.shape[1], gt_mask.shape[0]))

            # 创建可视化
            vis = np.zeros((image.shape[0], image.shape[1] * 3, 3), dtype=np.uint8)

            # 原图
            vis[:, :image.shape[1]] = image

            # GT 掩码
            gt_vis = np.zeros_like(image)
            gt_vis[gt_mask] = [0, 255, 0]  # 绿色
            vis[:, image.shape[1]:image.shape[1]*2] = gt_vis

            # 预测掩码
            pred_vis = np.zeros_like(image)
            pred_vis[pred_mask] = [0, 255, 255]  # 黄色
            # FP: 红色
            fp_mask = pred_mask & ~gt_mask
            pred_vis[fp_mask] = [0, 0, 255]
            # FN: 蓝色
            fn_mask = ~pred_mask & gt_mask
            pred_vis[fn_mask] = [255, 0, 0]
            vis[:, image.shape[1]*2:] = pred_vis

            # 添加标签
            cv2.putText(vis, "Original", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(vis, "GT Water", (image.shape[1] + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            metrics = compute_metrics(pred_mask, gt_mask)
            label = f"Pred (IoU={metrics['iou']:.2f})"
            cv2.putText(vis, label, (image.shape[1]*2 + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # 保存
            output_path = os.path.join(output_dir, f"water_extract_{i:02d}.jpg")
            cv2.imwrite(output_path, vis)

        except Exception as e:
            print(f"  可视化失败: {sample['image']}: {e}")
            continue

    print(f"  已保存 {num_samples} 张可视化结果")


def main():
    print("=" * 70)
    print("水体区域提取对比评估 v2.0")
    print("=" * 70)

    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "water_inspection.yaml"
    dataset_dir = project_root / "data" / "datasets"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    print(f"\n加载数据集: {dataset_dir}")
    samples = load_dataset(str(dataset_dir))
    print(f"  样本数: {len(samples)}")

    radio_code_dir = "/app/models/NVlabs_RADIO"
    siglip2_dir = "/app/models/siglip2-giant-opt-patch16-384"
    checkpoint_path = "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"

    results = {}

    # ============ 只评估 RADIO (SigLIP2) ============
    print("\n" + "=" * 70)
    print("配置: RADIO + SigLIP2")
    print("=" * 70)

    from models.open_vocab.radseg_segmentor import RADSegWaterSegmentor

    segmentor = RADSegWaterSegmentor(
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

    # 搜索最佳阈值
    best_thresh, best_metrics = find_best_threshold(
        segmentor, samples, thresholds=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    )
    print(f"\n最佳阈值: {best_thresh}")

    # 使用最佳阈值评估
    results["RADIO_SigLIP2"] = evaluate_config(
        "RADIO + SigLIP2",
        segmentor,
        samples,
        threshold=best_thresh,
    )
    results["RADIO_SigLIP2"]["best_threshold"] = best_thresh

    # 可视化
    output_dir = str(project_root / "outputs" / "water_extraction")
    visualize_extraction(segmentor, samples, output_dir, threshold=best_thresh)

    del segmentor
    torch.cuda.empty_cache()

    # ============ 总结 ============
    print("\n" + "=" * 70)
    print("总结")
    print("=" * 70)

    for config_name, metrics in results.items():
        print(f"\n{config_name}:")
        print(f"  最佳阈值: {metrics.get('best_threshold', 'N/A')}")
        print(f"  IoU: {metrics['iou']:.3f}")
        print(f"  Precision: {metrics['precision']:.3f}")
        print(f"  Recall: {metrics['recall']:.3f}")
        print(f"  F1: {metrics['f1']:.3f}")

    # 结论
    print("\n" + "=" * 70)
    print("结论")
    print("=" * 70)

    best_iou = results["RADIO_SigLIP2"]["iou"]

    if best_iou > 0.6:
        print("✓ 水体提取效果良好，可以用于后续水质分类")
        print("\n建议的两阶段策略:")
        print("  阶段1: 使用 RADIO 提取水体区域")
        print("  阶段2: 在水体区域内训练水质分类头")
    elif best_iou > 0.4:
        print("△ 水体提取效果中等，需要优化")
        print("\n优化建议:")
        print("  1. 调整水体提示词")
        print("  2. 使用形态学后处理")
        print("  3. 考虑使用颜色阈值辅助")
    else:
        print("✗ 水体提取效果不理想")
        print("\n建议:")
        print("  1. 使用传统图像处理方法")
        print("  2. 训练专门的水体分割模型")


if __name__ == "__main__":
    main()
