#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
混合分割器评估脚本

对比:
1. 纯 RADIO 分割 (RADSeg)
2. 纯颜色分割
3. 混合分割 (颜色优先 + RADIO 辅助)

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


def evaluate_color_only(samples, classes_config):
    """评估纯颜色分类"""
    from models.open_vocab.hybrid_segmentor import ColorWaterClassifier

    classifier = ColorWaterClassifier(classes_config)

    results = {
        "correct": 0,
        "total": 0,
        "per_class": defaultdict(lambda: {"correct": 0, "total": 0}),
        "confusion": defaultdict(lambda: defaultdict(int)),
    }

    print("评估纯颜色分类...")
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

        # 使用整张图像进行分类
        pixels = image.reshape(-1, 3)
        pred_class, score, all_scores = classifier.classify_region(pixels)

        results["total"] += 1
        results["per_class"][gt_class]["total"] += 1

        if pred_class == gt_class:
            results["correct"] += 1
            results["per_class"][gt_class]["correct"] += 1
            status = "✓"
        else:
            status = "✗"

        results["confusion"][gt_class][pred_class] += 1

        if results["total"] <= 30:
            print(f"  {status} {sample['image']}: GT={gt_class}, Pred={pred_class} ({score:.2f})")

    accuracy = results["correct"] / results["total"] if results["total"] > 0 else 0
    print(f"\n纯颜色分类准确率: {results['correct']}/{results['total']} = {accuracy:.2%}")

    print("\n各类别准确率:")
    for cls_name in results["per_class"]:
        c = results["per_class"][cls_name]["correct"]
        t = results["per_class"][cls_name]["total"]
        if t > 0:
            print(f"  {cls_name}: {c}/{t} = {c/t:.2%}")

    return results


def evaluate_hybrid(segmentor, samples, classes_config):
    """评估混合分割器"""
    from models.open_vocab.hybrid_segmentor import HybridWaterSegmentor

    hybrid = HybridWaterSegmentor(
        radio_segmentor=segmentor,
        classes_config=classes_config,
        use_radio_refinement=True,
        radio_weight=0.3,
        color_weight=0.7,
    )

    results = {
        "correct": 0,
        "total": 0,
        "fp": 0,  # 误检 (normal -> anomaly)
        "fn": 0,  # 漏检 (anomaly -> none)
        "total_normal": 0,
        "total_anomaly": 0,
        "per_class": defaultdict(lambda: {"correct": 0, "total": 0}),
    }

    anomaly_classes = {
        k for k, v in classes_config.items()
        if not v.get("is_background", False)
    }

    print("评估混合分割器...")
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

        # 执行分割
        segments = hybrid.segment(image, threshold=0.2, min_area=0.005)

        # 获取预测类别
        if segments:
            pred_class = list(segments.keys())[0]
        else:
            pred_class = None

        results["total"] += 1
        results["per_class"][gt_class]["total"] += 1

        if is_normal:
            if pred_class is not None:
                results["fp"] += 1
                status = "✗ [误检]"
            else:
                status = "✓"
        else:
            if pred_class is None:
                results["fn"] += 1
                status = "✗ [漏检]"
            elif pred_class == gt_class:
                results["correct"] += 1
                results["per_class"][gt_class]["correct"] += 1
                status = "✓"
            else:
                status = f"✗ [错分 -> {pred_class}]"

        if results["total"] <= 30:
            print(f"  {status} {sample['image']}: GT={gt_class}")

    accuracy = results["correct"] / results["total_anomaly"] if results["total_anomaly"] > 0 else 0
    fp_rate = results["fp"] / results["total_normal"] if results["total_normal"] > 0 else 0
    fn_rate = results["fn"] / results["total_anomaly"] if results["total_anomaly"] > 0 else 0

    print(f"\n混合分割结果:")
    print(f"  异常检出准确率: {results['correct']}/{results['total_anomaly']} = {accuracy:.2%}")
    print(f"  误检率 (normal→anomaly): {results['fp']}/{results['total_normal']} = {fp_rate:.2%}")
    print(f"  漏检率 (anomaly→none): {results['fn']}/{results['total_anomaly']} = {fn_rate:.2%}")

    print("\n各类别准确率:")
    for cls_name in anomaly_classes:
        c = results["per_class"][cls_name]["correct"]
        t = results["per_class"][cls_name]["total"]
        if t > 0:
            print(f"  {cls_name}: {c}/{t} = {c/t:.2%}")

    return results


def main():
    print("=" * 70)
    print("混合分割器评估")
    print("=" * 70)

    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "water_inspection.yaml"
    dataset_dir = project_root / "data" / "datasets"

    # 加载配置
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    classes_config = config["cloud"]["radio"]["classes"]

    # 加载数据集
    print(f"\n加载数据集: {dataset_dir}")
    samples = load_dataset(str(dataset_dir))
    print(f"  样本数: {len(samples)}")

    # 统计类别分布
    class_counts = defaultdict(int)
    for sample in samples:
        gt_class = sample.get("active_class")
        if gt_class:
            class_counts[gt_class] += 1
    print(f"  类别分布: {dict(class_counts)}")

    print("\n" + "=" * 70)
    print("测试 1: 纯颜色分类")
    print("=" * 70)
    color_results = evaluate_color_only(samples, classes_config)

    print("\n" + "=" * 70)
    print("测试 2: 混合分割器")
    print("=" * 70)

    # 初始化 RADIO 模型
    radio_code_dir = "/app/models/NVlabs_RADIO"
    siglip2_dir = "/app/models/siglip2-giant-opt-patch16-384"
    checkpoint_path = "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"

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

    hybrid_results = evaluate_hybrid(segmentor, samples, classes_config)

    # 对比总结
    print("\n" + "=" * 70)
    print("对比总结")
    print("=" * 70)

    color_acc = color_results["correct"] / color_results["total"] if color_results["total"] > 0 else 0
    hybrid_acc = hybrid_results["correct"] / hybrid_results["total_anomaly"] if hybrid_results["total_anomaly"] > 0 else 0
    hybrid_fp = hybrid_results["fp"] / hybrid_results["total_normal"] if hybrid_results["total_normal"] > 0 else 0
    hybrid_fn = hybrid_results["fn"] / hybrid_results["total_anomaly"] if hybrid_results["total_anomaly"] > 0 else 0

    print(f"\n{'方法':<20} {'准确率':>15} {'误检率':>15} {'漏检率':>15}")
    print("-" * 70)
    print(f"{'纯颜色分类':<20} {color_acc:>15.2%} {'N/A':>15} {'N/A':>15}")
    print(f"{'混合分割器':<20} {hybrid_acc:>15.2%} {hybrid_fp:>15.2%} {hybrid_fn:>15.2%}")


if __name__ == "__main__":
    main()
