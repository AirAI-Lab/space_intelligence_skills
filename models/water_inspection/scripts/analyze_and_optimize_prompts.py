#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据集分析和颜色提示词优化

分析:
1. 类别分布
2. 各类别实际颜色统计
3. 生成推荐的 color_hint 配置
4. 为 dam_seepage 设计专门的提示词

作者: 空中智能体团队
日期: 2026-04-05
"""

import json
import yaml
import numpy as np
import cv2
from pathlib import Path
from collections import defaultdict


def analyze_dataset():
    """分析数据集 - 使用 mask 文件提取像素特征"""
    dataset_dir = Path("data/datasets")
    meta_dir = dataset_dir / "meta"
    mask_dir = dataset_dir / "masks"

    class_counts = defaultdict(int)
    class_colors = defaultdict(list)
    class_samples = defaultdict(list)

    for meta_file in sorted(meta_dir.glob("*.json")):
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        gt_class = meta.get("active_class")
        if not gt_class:
            continue

        # 读取图像
        image_path = dataset_dir / "images" / meta["image"]
        if not image_path.exists():
            continue

        image = cv2.imread(str(image_path))
        if image is None:
            continue

        # 从 classes 中找到 active_class 对应的 mask 文件
        mask_file = None
        for cls_info in meta.get("classes", []):
            if cls_info.get("class") == gt_class:
                mask_file = cls_info.get("mask_file")
                break

        if not mask_file:
            # 如果没有找到 mask，跳过此样本
            print(f"警告: {meta['image']} 缺少 {gt_class} 的 mask 文件")
            continue

        mask_path = mask_dir / mask_file
        if not mask_path.exists():
            print(f"警告: mask 文件不存在 {mask_path}")
            continue

        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            continue

        # 确保 mask 和图像尺寸匹配
        h, w = image.shape[:2]
        if mask.shape != (h, w):
            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)

        # 只从 mask 区域内提取像素 (mask > 127 表示属于该类别)
        mask_binary = mask > 127
        if not mask_binary.any():
            continue

        # 提取 mask 区域内的像素
        ys, xs = np.where(mask_binary)
        pixels = image[ys, xs].astype(np.float32)

        class_counts[gt_class] += 1
        class_samples[gt_class].append(meta["image"])

        if len(pixels) == 0:
            continue

        # 采样最多 1000 个像素
        if len(pixels) > 1000:
            idx = np.random.choice(len(pixels), 1000, replace=False)
            pixels = pixels[idx]

        b_mean = pixels[:, 0].mean()
        g_mean = pixels[:, 1].mean()
        r_mean = pixels[:, 2].mean()

        class_colors[gt_class].append([b_mean, g_mean, r_mean])

    return class_counts, class_colors, class_samples


def compute_color_stats(class_colors):
    """计算颜色统计"""
    stats = {}

    for cls_name, colors in class_colors.items():
        colors = np.array(colors)
        if len(colors) == 0:
            continue

        b_mean = colors[:, 0].mean()
        g_mean = colors[:, 1].mean()
        r_mean = colors[:, 2].mean()

        b_std = colors[:, 0].std()
        g_std = colors[:, 1].std()
        r_std = colors[:, 2].std()

        brightness = (b_mean + g_mean + r_mean) / 3
        rgb_range = max(r_mean, g_mean, b_mean) - min(r_mean, g_mean, b_mean)

        r_g = r_mean - g_mean
        g_b = g_mean - b_mean
        r_b = r_mean - b_mean

        stats[cls_name] = {
            "count": len(colors),
            "bgr_mean": [b_mean, g_mean, r_mean],
            "bgr_std": [b_std, g_std, r_std],
            "brightness": brightness,
            "rgb_range": rgb_range,
            "r_g_diff": r_g,
            "g_b_diff": g_b,
            "r_b_diff": r_b,
        }

    return stats


def generate_optimized_prompts(stats):
    """生成优化的提示词"""
    prompts = {}

    # normal_water
    prompts["normal_water"] = {
        "positive": [
            "clear transparent river water with balanced RGB channels",
            "clean unpolluted water body showing natural blue gray tone",
            "crystal clear water surface without visible color tint",
            "healthy river water with G channel around 120 to 140",
        ],
        "negative": [
            "bright vivid red rust colored water",
            "thick bright green algae bloom",
            "milky white gray turbid foam water",
            "blackish gray sewage water",
        ],
    }

    # black_water
    if "black_water" in stats:
        s = stats["black_water"]
        prompts["black_water"] = {
            "positive": [
                f"dark blackish gray water with all RGB channels below 130",
                f"opaque polluted water with RGB range less than 25",
                f"dark contaminated water appearing uniformly black gray",
                f"black sewage water with low brightness around {int(s['brightness'])}",
            ],
            "negative": [
                "bright clear transparent water with high visibility",
                "white milky foam water with brightness above 150",
                "red rust colored water with R channel dominant",
                "green algae water with G channel clearly highest",
            ],
        }

    # turbid_water (黄褐色)
    if "turbid_water" in stats:
        s = stats["turbid_water"]
        prompts["turbid_water"] = {
            "positive": [
                f"yellowish brown muddy water with R channel around {int(s['bgr_mean'][2])}",
                f"tea colored turbid water with R channel higher than G",
                f"ochre yellow water from soil runoff with warm tone",
                f"coffee brown murky water with earth color tint",
            ],
            "negative": [
                "clear transparent water without sediment",
                "bright green algae bloom with G dominant",
                "black opaque water with all channels low",
                "white milky foam water with high brightness",
            ],
        }

    # red_water
    if "red_water" in stats:
        s = stats["red_water"]
        prompts["red_water"] = {
            "positive": [
                f"bright vivid red rust colored water with R channel above {int(s['bgr_mean'][2])}",
                f"reddish pink contaminated water with R much higher than G and B",
                f"crimson scarlet tinted sewage with saturated red color",
                f"rusty red water with R channel clearly dominant",
            ],
            "negative": [
                "yellow brown turbid water with earth tone",
                "clear transparent normal water",
                "dark black gray opaque water",
                "white milky foam water with low saturation",
            ],
        }

    # green_water
    if "green_water" in stats:
        s = stats["green_water"]
        prompts["green_water"] = {
            "positive": [
                f"thick bright green algae bloom with G channel around {int(s['bgr_mean'][1])}",
                f"dark green eutrophic water where G channel exceeds B by more than 30",
                f"green algae scum layer with visible green tint on water",
                f"emerald green turbid water with G channel clearly above R and B",
            ],
            "negative": [
                "clear transparent river water without algae",
                "yellow brown muddy water with R dominant",
                "black opaque sewage water",
                "white milky foam water with balanced RGB",
            ],
        }

    # milky_foam_water
    if "milky_foam_water" in stats:
        s = stats["milky_foam_water"]
        prompts["milky_foam_water"] = {
            "positive": [
                f"milky white gray turbid water with brightness above {int(s['brightness'])}",
                f"thick white foam bubbles clustered on water surface",
                f"cloudy opaque water body with RGB channels all high around {int(s['brightness'])}",
                f"dense frothy white patches with low saturation high brightness",
            ],
            "negative": [
                "clear transparent water with high visibility",
                "dark black opaque water with low brightness",
                "green algae bloom with obvious color tint",
                "red rust water with dominant R channel",
            ],
        }

    # dam_seepage (特殊处理 - 包含结构和材质特征)
    prompts["dam_seepage"] = {
        "positive": [
            # 强调材质和结构
            "dark wet water seepage stain on gray concrete dam or wall surface",
            "fresh water leakage mark on concrete structure with visible wet patch",
            "damp dark patch on cement dam wall indicating active seepage through crack",
            "water stain spreading from crack or joint in concrete embankment",
            "moisture streak running down vertical concrete surface of dam",
            "wet discolored area on stone or concrete channel wall near water",
            # 强调位置特征 (不在水中)
            "seepage on man-made concrete structure above water level",
            "water infiltration visible on dam face or channel wall",
        ],
        "negative": [
            "water body in river channel with flowing water",
            "clear transparent lake water surface",
            "green algae bloom floating on water",
            "milky foam on water surface",
            # 强调与水体的区别
            "submerged underwater scene",
            "water reflection on calm lake",
        ],
    }

    return prompts


def main():
    print("=" * 70)
    print("数据集分析和颜色提示词优化")
    print("=" * 70)

    # 分析数据集
    class_counts, class_colors, class_samples = analyze_dataset()

    print("\n类别分布:")
    print("-" * 70)
    for cls_name, count in sorted(class_counts.items(), key=lambda x: -x[1]):
        samples = class_samples.get(cls_name, [])[:3]
        print(f"  {cls_name}: {count} 样本")
        if samples:
            print(f"    示例: {', '.join(samples[:3])}")

    # 计算颜色统计
    stats = compute_color_stats(class_colors)

    print("\n" + "=" * 70)
    print("颜色统计 (BGR 顺序)")
    print("=" * 70)

    for cls_name in ["normal_water", "black_water", "turbid_water", "red_water",
                     "green_water", "milky_foam_water", "dam_seepage"]:
        if cls_name not in stats:
            continue

        s = stats[cls_name]
        b, g, r = s["bgr_mean"]
        print(f"\n{cls_name} ({s['count']} 样本):")
        print(f"  BGR: ({b:.0f}, {g:.0f}, {r:.0f}) ± ({s['bgr_std'][0]:.0f}, {s['bgr_std'][1]:.0f}, {s['bgr_std'][2]:.0f})")
        print(f"  亮度: {s['brightness']:.0f}, RGB范围: {s['rgb_range']:.0f}")
        print(f"  R-G: {s['r_g_diff']:+.0f}, G-B: {s['g_b_diff']:+.0f}, R-B: {s['r_b_diff']:+.0f}")

    # 生成推荐的 color_hint
    print("\n" + "=" * 70)
    print("推荐的 color_hint 配置 (BGR 顺序)")
    print("=" * 70)

    recommended_hints = {}
    for cls_name, s in stats.items():
        b, g, r = s["bgr_mean"]
        recommended_hints[cls_name] = [int(b), int(g), int(r)]
        print(f"  {cls_name}: [{int(b)}, {int(g)}, {int(r)}]")

    # 生成优化的提示词
    print("\n" + "=" * 70)
    print("优化的提示词 (特别是 dam_seepage)")
    print("=" * 70)

    prompts = generate_optimized_prompts(stats)

    for cls_name, cls_prompts in prompts.items():
        print(f"\n{cls_name}:")
        print("  Positive:")
        for p in cls_prompts.get("positive", [])[:3]:
            print(f"    - {p}")
        print("  Negative:")
        for p in cls_prompts.get("negative", [])[:2]:
            print(f"    - {p}")

    # 保存配置
    output_dir = Path("data/diagnosis")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存推荐的 color_hint
    hints_output = output_dir / "recommended_color_hints.json"
    with open(hints_output, "w", encoding="utf-8") as f:
        json.dump(recommended_hints, f, indent=2, ensure_ascii=False)
    print(f"\n推荐的 color_hint 已保存: {hints_output}")

    # 保存优化的提示词
    prompts_output = output_dir / "optimized_prompts.yaml"
    with open(prompts_output, "w", encoding="utf-8") as f:
        yaml.dump(prompts, f, allow_unicode=True, default_flow_style=False)
    print(f"优化的提示词已保存: {prompts_output}")


if __name__ == "__main__":
    main()
