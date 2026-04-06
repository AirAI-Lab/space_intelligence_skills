#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DINOv3-7B 特征融合对比评估脚本

对比:
  1. Baseline (SigLIP2 only)
  2. With DINOv3-7B (优化后的门控融合)

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import sys
import json
import time
import yaml
import numpy as np
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import cv2


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_dataset(dataset_dir: str) -> List[dict]:
    """加载数据集元数据"""
    meta_dir = Path(dataset_dir) / "meta"
    samples = []

    for meta_file in sorted(meta_dir.glob("*.json")):
        with open(meta_file, 'r', encoding='utf-8') as f:
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


def compute_pixel_accuracy(pred_mask: np.ndarray, gt_mask: np.ndarray) -> float:
    """计算像素级准确率"""
    total = pred_mask.size
    correct = (pred_mask == gt_mask).sum()
    return correct / total


def evaluate_segmentor(
    segmentor,
    samples: List[dict],
    classes_config: dict,
    class_names: List[str],
) -> Dict[str, float]:
    """评估分割器"""
    results = {
        "per_class": defaultdict(lambda: {"iou": [], "acc": [], "count": 0}),
        "overall": {"iou": [], "acc": []},
        "class_accuracy": defaultdict(int),  # 类别预测正确数
        "confusion": defaultdict(lambda: defaultdict(int)),  # 混淆矩阵
    }

    for sample in samples:
        image_path = sample["image_path"]
        if not os.path.exists(image_path):
            print(f"  [跳过] 图像不存在: {image_path}")
            continue

        image = cv2.imread(image_path)
        if image is None:
            print(f"  [跳过] 无法读取: {image_path}")
            continue

        gt_class = sample.get("active_class")
        if not gt_class:
            continue

        # 执行分割
        try:
            segments = segmentor.segment(image, classes_config)
        except Exception as e:
            print(f"  [错误] {image_path}: {e}")
            continue

        # 获取预测类别
        pred_class = None
        pred_mask = None
        if segments:
            # 取得分最高的
            best = max(segments.values(), key=lambda s: s.score)
            pred_class = best.class_name
            pred_mask = best.mask

        # 加载 GT mask
        gt_mask = None
        for cls_info in sample.get("classes", []):
            if cls_info["class"] == gt_class:
                mask_path = os.path.join(sample["mask_dir"], cls_info["mask_file"])
                if os.path.exists(mask_path):
                    gt_mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                    gt_mask = gt_mask > 127
                break

        # 记录混淆矩阵
        results["confusion"][gt_class][pred_class or "none"] += 1

        # 类别准确率
        if pred_class == gt_class:
            results["class_accuracy"][gt_class] += 1

        # 计算 IoU 和 像素准确率
        if pred_mask is not None and gt_mask is not None:
            iou = compute_iou(pred_mask, gt_mask)
            acc = compute_pixel_accuracy(pred_mask, gt_mask)

            results["per_class"][gt_class]["iou"].append(iou)
            results["per_class"][gt_class]["acc"].append(acc)
            results["per_class"][gt_class]["count"] += 1

            results["overall"]["iou"].append(iou)
            results["overall"]["acc"].append(acc)

    # 汇总统计
    summary = {
        "mean_iou": np.mean(results["overall"]["iou"]) if results["overall"]["iou"] else 0.0,
        "mean_acc": np.mean(results["overall"]["acc"]) if results["overall"]["acc"] else 0.0,
        "class_accuracy": {},
        "per_class_iou": {},
    }

    # 计算每个类别的统计
    class_counts = defaultdict(int)
    for sample in samples:
        gt_class = sample.get("active_class")
        if gt_class:
            class_counts[gt_class] += 1

    for cls_name in class_names:
        # 类别准确率
        correct = results["class_accuracy"].get(cls_name, 0)
        total = class_counts.get(cls_name, 0)
        summary["class_accuracy"][cls_name] = f"{correct}/{total}" if total > 0 else "0/0"

        # IoU
        ious = results["per_class"][cls_name]["iou"]
        if ious:
            summary["per_class_iou"][cls_name] = np.mean(ious)

    # 打印混淆矩阵
    print("\n混淆矩阵 (行=GT, 列=Pred):")
    all_pred_classes = set()
    for gt_cls in results["confusion"]:
        all_pred_classes.update(results["confusion"][gt_cls].keys())

    header = "            " + "  ".join(f"{c[:10]:>10}" for c in sorted(all_pred_classes))
    print(header)
    for gt_cls in sorted(results["confusion"].keys()):
        row = f"{gt_cls[:10]:>12}"
        for pred_cls in sorted(all_pred_classes):
            count = results["confusion"][gt_cls].get(pred_cls, 0)
            row += f"  {count:>10}"
        print(row)

    return summary


def main():
    print("=" * 60)
    print("DINOv3-7B 特征融合对比评估")
    print("=" * 60)

    # 路径配置
    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "water_inspection.yaml"
    dataset_dir = project_root / "data" / "datasets"

    # 容器内路径 (覆盖环境变量)
    radio_code_dir = "/app/models/NVlabs_RADIO"
    siglip2_dir = "/app/models/siglip2-giant-opt-patch16-384"
    checkpoint_path = "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"

    # 验证路径
    import os
    if not os.path.exists(radio_code_dir):
        print(f"错误: RADIO 代码目录不存在: {radio_code_dir}")
        return
    if not os.path.exists(siglip2_dir):
        print(f"错误: SigLIP2 目录不存在: {siglip2_dir}")
        return
    if not os.path.exists(checkpoint_path):
        print(f"错误: 模型权重不存在: {checkpoint_path}")
        return

    print(f"RADIO 代码: {radio_code_dir}")
    print(f"SigLIP2: {siglip2_dir}")
    print(f"模型权重: {checkpoint_path}")

    # 加载配置
    config = load_config(str(config_path))
    classes_config = config["cloud"]["radio"]["classes"]

    # 定义类别顺序
    CLASS_NAMES = [
        "black_water",
        "turbid_water",
        "red_water",
        "green_water",
        "milky_foam_water",
        "dam_seepage",
        "normal_water",
    ]

    # 加载数据集
    print(f"\n加载数据集: {dataset_dir}")
    samples = load_dataset(str(dataset_dir))
    print(f"  样本数: {len(samples)}")

    # 统计各类别数量
    class_counts = defaultdict(int)
    for sample in samples:
        gt_class = sample.get("active_class")
        if gt_class:
            class_counts[gt_class] += 1
    print(f"  类别分布: {dict(class_counts)}")

    # ════════════════════════════════════════════════════════════════════════
    # 1. Baseline (SigLIP2 only)
    # ════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("1. Baseline (SigLIP2 only)")
    print("=" * 60)

    from models.open_vocab.radseg_segmentor import RADSegWaterSegmentor

    segmentor_baseline = RADSegWaterSegmentor(
        checkpoint_path=checkpoint_path,
        radio_code_dir=radio_code_dir,
        siglip2_dir=siglip2_dir,
        device="cuda",
        input_size=config["cloud"]["radio"]["inference"]["input_size"],
        config=config,
        use_scra=True,
        use_dino=False,  # 不使用 DINO
        use_sam=False,
    )

    print("开始评估 Baseline...")
    t0 = time.time()
    baseline_results = evaluate_segmentor(
        segmentor_baseline, samples, classes_config, CLASS_NAMES
    )
    baseline_time = time.time() - t0

    print(f"\n[Baseline 结果]")
    print(f"  mIoU: {baseline_results['mean_iou']:.4f}")
    print(f"  mAcc: {baseline_results['mean_acc']:.4f}")
    print(f"  类别准确率:")
    for cls_name in CLASS_NAMES:
        print(f"    {cls_name}: {baseline_results['class_accuracy'].get(cls_name, 'N/A')}")

    # ════════════════════════════════════════════════════════════════════════
    # 2. With DINOv3-7B (优化后的门控融合)
    # ════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("2. With DINOv3-7B (门控融合)")
    print("=" * 60)

    # 释放显存
    del segmentor_baseline
    torch.cuda.empty_cache()

    segmentor_dino = RADSegWaterSegmentor(
        checkpoint_path=checkpoint_path,
        radio_code_dir=radio_code_dir,
        siglip2_dir=siglip2_dir,
        device="cuda",
        input_size=config["cloud"]["radio"]["inference"]["input_size"],
        config=config,
        use_scra=True,
        use_dino=True,  # 使用 DINO
        use_sam=False,
    )

    print("开始评估 DINOv3-7B...")
    t0 = time.time()
    dino_results = evaluate_segmentor(
        segmentor_dino, samples, classes_config, CLASS_NAMES
    )
    dino_time = time.time() - t0

    print(f"\n[DINOv3-7B 结果]")
    print(f"  mIoU: {dino_results['mean_iou']:.4f}")
    print(f"  mAcc: {dino_results['mean_acc']:.4f}")
    print(f"  类别准确率:")
    for cls_name in CLASS_NAMES:
        print(f"    {cls_name}: {dino_results['class_accuracy'].get(cls_name, 'N/A')}")

    # ════════════════════════════════════════════════════════════════════════
    # 对比总结
    # ════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("对比总结")
    print("=" * 60)

    print(f"\n{'指标':<15} {'Baseline':>12} {'DINOv3-7B':>12} {'提升':>12}")
    print("-" * 55)
    print(f"{'mIoU':<15} {baseline_results['mean_iou']:>12.4f} {dino_results['mean_iou']:>12.4f} {dino_results['mean_iou'] - baseline_results['mean_iou']:>+12.4f}")
    print(f"{'mAcc':<15} {baseline_results['mean_acc']:>12.4f} {dino_results['mean_acc']:>12.4f} {dino_results['mean_acc'] - baseline_results['mean_acc']:>+12.4f}")
    print(f"{'推理时间(s)':<15} {baseline_time:>12.1f} {dino_time:>12.1f} {dino_time - baseline_time:>+12.1f}")

    # 保存结果
    results_path = project_root / "outputs" / "dino_comparison_results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)

    comparison = {
        "baseline": baseline_results,
        "dino": dino_results,
        "improvement": {
            "miou": dino_results["mean_iou"] - baseline_results["mean_iou"],
            "macc": dino_results["mean_acc"] - baseline_results["mean_acc"],
        }
    }

    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {results_path}")


if __name__ == "__main__":
    main()
