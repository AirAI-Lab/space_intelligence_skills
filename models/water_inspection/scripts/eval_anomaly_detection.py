#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水质异常检测评估脚本 v2.0

重点评估:
1. 异常类别准确率 (black_water, turbid_water, red_water, green_water, milky_foam_water, dam_seepage)
2. 误检率 (正常水质被误检为异常)
3. 漏检率 (异常未被检测)
4. IoU (用于分割质量评估)

5. DINOv3-7B 融合对检测效果的影响

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
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import cv2


def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_dataset(dataset_dir):
    meta_dir = Path(dataset_dir) / "meta"
    samples = []
    for meta_file in sorted(meta_dir.glob("*.json")):
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        meta["image_path"] = str(Path(dataset_dir) / "images" / meta["image"])
        meta["mask_dir"] = str(Path(dataset_dir) / "masks")
        samples.append(meta)
    return samples


def compute_iou(mask1, mask2):
    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()
    if union == 0:
        return 1.0 if intersection == 0 else 0.0
    return intersection / union


def evaluate_segmentor(segmentor, samples, classes_config, anomaly_classes):
    results = {
        "per_class": defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "iou": []}),
        "false_positive": 0,
        "false_negative": 0,
        "total_normal": 0,
        "total_anomaly": 0,
    }
    for sample in samples:
        image_path = sample["image_path"]
        if not os.path.exists(image_path):
            continue
        image = cv2.imread(image_path)
        if image is None:
            continue
        gt_class = sample.get("active_class")
        if not gt_class:
            continue
        is_normal = (gt_class == "normal_water")
        if is_normal:
            results["total_normal"] += 1
        else:
            results["total_anomaly"] += 1
        try:
            segments = segmentor.segment(image, classes_config)
        except Exception as e:
            print(f"  [错误] {image_path}: {e}")
            continue
        pred_class = None
        pred_mask = None
        if segments:
            best = max(segments.values(), key=lambda s: s.score)
            pred_class = best.class_name
            pred_mask = best.mask
        if is_normal:
            if pred_class is not None:
                results["false_positive"] += 1
                print(f"  [误检] {sample['image']}: normal_water -> {pred_class}")
        else:
            if pred_class is None:
                results["false_negative"] += 1
                print(f"  [漏检] {sample['image']}: {gt_class} -> none")
            elif pred_class == gt_class:
                results["per_class"][gt_class]["tp"] += 1
            else:
                results["per_class"][gt_class]["fn"] += 1
                results["per_class"][pred_class]["fp"] += 1
                print(f"  [错分] {sample['image']}: {gt_class} -> {pred_class}")
            if pred_mask is not None:
                for cls_info in sample.get("classes", []):
                    if cls_info["class"] == gt_class:
                        mask_path = os.path.join(sample["mask_dir"], cls_info["mask_file"])
                        if os.path.exists(mask_path):
                            gt_mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                            gt_mask = gt_mask > 127
                            iou = compute_iou(pred_mask, gt_mask)
                            results["per_class"][gt_class]["iou"].append(iou)
                        break
    return results


def main():
    print("=" * 60)
    print("水质异常检测评估 v2.0")
    print("目标: 精准检出异常， 避免误检和漏检")
    print("=" * 60)
    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "water_inspection.yaml"
    dataset_dir = project_root / "data" / "datasets"
    config = load_config(str(config_path))
    classes_config = config["cloud"]["radio"]["classes"]
    ANOMALY_CLASSES = [
        "black_water",
        "turbid_water",
        "red_water",
        "green_water",
        "milky_foam_water",
        "dam_seepage",
    ]
    print(f"\n加载数据集: {dataset_dir}")
    samples = load_dataset(str(dataset_dir))
    print(f"  样本数: {len(samples)}")
    class_counts = defaultdict(int)
    for sample in samples:
        gt_class = sample.get("active_class")
        if gt_class:
            class_counts[gt_class] += 1
    print(f"  类别分布: {dict(class_counts)}")
    radio_code_dir = "/app/models/NVlabs_RADIO"
    siglip2_dir = "/app/models/siglip2-giant-opt-patch16-384"
    checkpoint_path = "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"
    print("\n" + "=" * 60)
    print("评估 Baseline (SigLIP2 only)")
    print("=" * 60)
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
    print("开始评估...")
    t0 = time.time()
    results = evaluate_segmentor(segmentor, samples, classes_config, ANOMALY_CLASSES)
    eval_time = time.time() - t0
    print("\n" + "-" * 60)
    print("Baseline 结果:")
    print("-" * 60)
    print("\n异常类别检测:")
    total_tp = 0
    total_fn = 0
    for cls_name in ANOMALY_CLASSES:
        tp = results["per_class"][cls_name]["tp"]
        fn = results["per_class"][cls_name]["fn"]
        fp = results["per_class"][cls_name]["fp"]
        ious = results["per_class"][cls_name]["iou"]
        total = class_counts.get(cls_name, 0)
        total_tp += tp
        total_fn += fn
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        miou = np.mean(ious) if ious else 0
        print(f"  {cls_name}:")
        print(f"    检出: {tp}/{total}, Precision: {precision:.2%}, Recall: {recall:.2%}, F1: {f1:.2%}")
        if miou > 0:
            print(f"    mIoU: {miou:.4f}")
    fp_rate = results["false_positive"] / results["total_normal"] if results["total_normal"] > 0 else 0
    fn_rate = results["false_negative"] / results["total_anomaly"] if results["total_anomaly"] > 0 else 0
    print(f"\n误检率 (正常→异常): {results['false_positive']}/{results['total_normal']} = {fp_rate:.2%}")
    print(f"漏检率 (异常→未检出): {results['false_negative']}/{results['total_anomaly']} = {fn_rate:.2%}")
    print(f"评估时间: {eval_time:.1f}s")
    del segmentor
    torch.cuda.empty_cache()
    print("\n" + "=" * 60)
    print("评估 DINOv3-7B (门控融合)")
    print("=" * 60)
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
    print("开始评估...")
    t0 = time.time()
    results_dino = evaluate_segmentor(segmentor_dino, samples, classes_config, ANOMALY_CLASSES)
    eval_time_dino = time.time() - t0
    print("\n" + "-" * 60)
    print("DINOv3-7B 结果:")
    print("-" * 60)
    print("\n异常类别检测:")
    total_tp_dino = 0
    total_fn_dino = 0
    for cls_name in ANOMALY_CLASSES:
        tp = results_dino["per_class"][cls_name]["tp"]
        fn = results_dino["per_class"][cls_name]["fn"]
        fp = results_dino["per_class"][cls_name]["fp"]
        ious = results_dino["per_class"][cls_name]["iou"]
        total = class_counts.get(cls_name, 0)
        total_tp_dino += tp
        total_fn_dino += fn
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        miou = np.mean(ious) if ious else 0
        print(f"  {cls_name}:")
        print(f"    检出: {tp}/{total}, Precision: {precision:.2%}, Recall: {recall:.2%}, F1: {f1:.2%}")
        if miou > 0:
            print(f"    mIoU: {miou:.4f}")
    fp_rate_dino = results_dino["false_positive"] / results_dino["total_normal"] if results_dino["total_normal"] > 0 else 0
    fn_rate_dino = results_dino["false_negative"] / results_dino["total_anomaly"] if results_dino["total_anomaly"] > 0 else 0
    print(f"\n误检率 (正常→异常): {results_dino['false_positive']}/{results_dino['total_normal']} = {fp_rate_dino:.2%}")
    print(f"漏检率 (异常→未检出): {results_dino['false_negative']}/{results_dino['total_anomaly']} = {fn_rate_dino:.2%}")
    print(f"评估时间: {eval_time_dino:.1f}s")
    print("\n" + "=" * 60)
    print("对比总结")
    print("=" * 60)
    print(f"\n{'指标':<20} {'Baseline':>15} {'DINOv3-7B':>15} {'提升':>10}")
    print("-" * 60)
    fp_diff = fp_rate_dino - fp_rate
    fn_diff = fn_rate_dino - fn_rate
    tp_diff = total_tp_dino - total_tp
    print(f"{'误检率':<20} {fp_rate:.2%} {fp_rate_dino:.2%} {fp_diff:+.2%}")
    print(f"{'漏检率':<20} {fn_rate:.2%} {fn_rate_dino:.2%} {fn_diff:+.2%}")
    print(f"{'异常总检出数':<20} {total_tp:>15} {total_tp_dino:>15} {tp_diff:>+10}")


if __name__ == "__main__":
    main()
