#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
颜色分布分析脚本

分析各类别的实际 RGB 分布，用于优化颜色分类规则

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

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2


def main():
    print("=" * 70)
    print("水质类别颜色分布分析")
    print("=" * 70)

    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "water_inspection.yaml"
    dataset_dir = project_root / "data" / "datasets"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    classes_config = config["cloud"]["radio"]["classes"]

    # 加载数据集
    meta_dir = Path(dataset_dir) / "meta"

    class_colors = defaultdict(list)

    for meta_file in sorted(meta_dir.glob("*.json")):
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        gt_class = meta.get("active_class")
        if not gt_class:
            continue

        image_path = Path(dataset_dir) / "images" / meta["image"]
        if not image_path.exists():
            continue

        image = cv2.imread(str(image_path))
        if image is None:
            continue

        # 采样像素
        h, w = image.shape[:2]
        # 中心区域采样
        cy, cx = h // 2, w // 2
        crop_size = min(h, w) // 4
        y1, y2 = max(0, cy - crop_size), min(h, cy + crop_size)
        x1, x2 = max(0, cx - crop_size), min(w, cx + crop_size)

        crop = image[y1:y2, x1:x2]
        pixels = crop.reshape(-1, 3)

        # 随机采样 1000 像素
        if len(pixels) > 1000:
            idx = np.random.choice(len(pixels), 1000, replace=False)
            pixels = pixels[idx]

        # 计算 BGR 均值
        b_mean = pixels[:, 0].mean()
        g_mean = pixels[:, 1].mean()
        r_mean = pixels[:, 2].mean()
        brightness = (b_mean + g_mean + r_mean) / 3
        rgb_range = max(r_mean, g_mean, b_mean) - min(r_mean, g_mean, b_mean)

        class_colors[gt_class].append({
            "image": meta["image"],
            "b": b_mean,
            "g": g_mean,
            "r": r_mean,
            "brightness": brightness,
            "range": rgb_range,
        })

    # 统计各类别
    print("\n各类别颜色分布 (BGR 顺序):")
    print("=" * 70)

    class_stats = {}

    for cls_name in ["normal_water", "black_water", "turbid_water", "red_water",
                     "green_water", "milky_foam_water", "dam_seepage"]:
        if cls_name not in class_colors:
            continue

        samples = class_colors[cls_name]
        n = len(samples)

        b_vals = [s["b"] for s in samples]
        g_vals = [s["g"] for s in samples]
        r_vals = [s["r"] for s in samples]
        bright_vals = [s["brightness"] for s in samples]
        range_vals = [s["range"] for s in samples]

        stats = {
            "count": n,
            "b": {"mean": np.mean(b_vals), "std": np.std(b_vals), "min": np.min(b_vals), "max": np.max(b_vals)},
            "g": {"mean": np.mean(g_vals), "std": np.std(g_vals), "min": np.min(g_vals), "max": np.max(g_vals)},
            "r": {"mean": np.mean(r_vals), "std": np.std(r_vals), "min": np.min(r_vals), "max": np.max(r_vals)},
            "brightness": {"mean": np.mean(bright_vals), "std": np.std(bright_vals)},
            "range": {"mean": np.mean(range_vals), "std": np.std(range_vals)},
        }

        class_stats[cls_name] = stats

        print(f"\n{cls_name} ({n} 样本):")
        print(f"  B: {stats['b']['mean']:.1f} ± {stats['b']['std']:.1f} (范围: {stats['b']['min']:.1f} - {stats['b']['max']:.1f})")
        print(f"  G: {stats['g']['mean']:.1f} ± {stats['g']['std']:.1f} (范围: {stats['g']['min']:.1f} - {stats['g']['max']:.1f})")
        print(f"  R: {stats['r']['mean']:.1f} ± {stats['r']['std']:.1f} (范围: {stats['r']['min']:.1f} - {stats['r']['max']:.1f})")
        print(f"  亮度: {stats['brightness']['mean']:.1f} ± {stats['brightness']['std']:.1f}")
        print(f"  RGB范围: {stats['range']['mean']:.1f} ± {stats['range']['std']:.1f}")

        # 推导分类规则
        r_g_diff = stats['r']['mean'] - stats['g']['mean']
        g_b_diff = stats['g']['mean'] - stats['b']['mean']
        r_b_diff = stats['r']['mean'] - stats['b']['mean']

        print(f"  R-G: {r_g_diff:.1f}, G-B: {g_b_diff:.1f}, R-B: {r_b_diff:.1f}")

        # 建议的规则
        print(f"  建议规则:")
        if stats['brightness']['mean'] < 80:
            print(f"    - 暗色: brightness < 100")
        if stats['brightness']['mean'] > 150:
            print(f"    - 亮色: brightness > 140")
        if r_g_diff > 15:
            print(f"    - 红色调: R > G + 10")
        if g_b_diff > 15:
            print(f"    - 绿色调: G > B + 10")
        if r_b_diff > 30:
            print(f"    - 暖色调: R > B + 20")

    # 推荐颜色提示
    print("\n" + "=" * 70)
    print("推荐 color_hint 配置 (BGR 顺序):")
    print("=" * 70)

    for cls_name, stats in class_stats.items():
        b = int(stats['b']['mean'])
        g = int(stats['g']['mean'])
        r = int(stats['r']['mean'])
        print(f"  {cls_name}: [{b}, {g}, {r}]")


if __name__ == "__main__":
    main()
