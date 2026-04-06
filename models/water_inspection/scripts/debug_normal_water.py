#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
normal_water 检测调试脚本

分析 normal_water 样本的得分分布
"""

import os
import sys
import json
import yaml
import numpy as np
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import cv2


def load_config(config_path: str) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    print("=" * 60)
    print("normal_water 检测调试")
    print("=" * 60)

    # 路径
    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "water_inspection.yaml"
    dataset_dir = project_root / "data" / "datasets"

    config = load_config(str(config_path))
    classes_config = config["cloud"]["radio"]["classes"]

    # 容器内路径
    radio_code_dir = "/app/models/NVlabs_RADIO"
    siglip2_dir = "/app/models/siglip2-giant-opt-patch16-384"
    checkpoint_path = "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"

    # 加载数据集
    meta_dir = Path(dataset_dir) / "meta"
    normal_samples = []
    for meta_file in sorted(meta_dir.glob("*.json")):
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
            if meta.get("active_class") == "normal_water":
                meta["image_path"] = str(Path(dataset_dir) / "images" / meta["image"])
                normal_samples.append(meta)

    print(f"找到 {len(normal_samples)} 个 normal_water 样本")

    # 加载模型
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

    # 分析每个样本的得分
    print("\n分析 normal_water 样本得分分布:")
    print("-" * 80)

    score_stats = defaultdict(list)

    for i, sample in enumerate(normal_samples[:10]):  # 只分析前10个
        image = cv2.imread(sample["image_path"])
        if image is None:
            continue

        # 计算热图
        heatmaps = segmentor.compute_patch_similarity(image, classes_config)

        # 获取各类别得分
        scores = {}
        for cls_name, hm in heatmaps.items():
            scores[cls_name] = {
                "max": float(hm.max()),
                "mean": float(hm.mean()),
                "thresholded_mean": float(hm[hm > 0.3].mean()) if (hm > 0.3).any() else 0.0,
            }
            score_stats[cls_name].append(scores[cls_name]["max"])

        # 找最高得分类别
        best_cls = max(scores.keys(), key=lambda k: scores[k]["max"])
        best_score = scores[best_cls]["max"]
        normal_score = scores.get("normal_water", {}).get("max", 0)

        print(f"\n样本 {i+1}: {sample['image']}")
        print(f"  最高分类别: {best_cls} (得分: {best_score:.4f})")
        print(f"  normal_water 得分: {normal_score:.4f}")
        print(f"  各类别最高分:")
        for cls_name in ["black_water", "turbid_water", "milky_foam_water", "normal_water", "green_water"]:
            if cls_name in scores:
                print(f"    {cls_name}: {scores[cls_name]['max']:.4f}")

    # 统计汇总
    print("\n" + "=" * 60)
    print("得分分布汇总 (10个 normal_water 样本):")
    print("-" * 60)
    for cls_name in ["black_water", "turbid_water", "milky_foam_water", "normal_water", "green_water"]:
        if cls_name in score_stats:
            scores = score_stats[cls_name]
            print(f"  {cls_name}:")
            print(f"    max: {np.max(scores):.4f}, min: {np.min(scores):.4f}, mean: {np.mean(scores):.4f}")


if __name__ == "__main__":
    main()
