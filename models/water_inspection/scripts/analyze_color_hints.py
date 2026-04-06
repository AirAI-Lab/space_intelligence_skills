#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析GT样本的颜色统计，优化color_hint值
"""

import sys
import yaml
import json
import cv2
import numpy as np
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

def analyze_gt_colors():
    """分析GT样本的BGR颜色统计"""
    
    # 数据集路径
    data_dir = Path(__file__).parent.parent / "data" / "datasets"
    images_dir = data_dir / "images"
    masks_dir = data_dir / "masks"
    meta_dir = data_dir / "meta"
    
    # 加载配置
    config_path = Path(__file__).parent.parent / "configs" / "water_inspection.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    classes_config = config.get("cloud", {}).get("radio", {}).get("classes", {})
    
    # 收集每个类别的颜色统计
    class_colors = defaultdict(list)
    
    images = sorted(list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.jpeg")) + list(images_dir.glob("*.png")))
    
    for img_path in images:
        # 加载图像
        image = cv2.imread(str(img_path))
        if image is None:
            continue
        
        h, w = image.shape[:2]
        
        # 加载 meta
        meta_path = meta_dir / f"{img_path.stem}.json"
        if not meta_path.exists():
            continue
        
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        
        gt_class = meta.get("active_class")
        if not gt_class:
            continue
        
        # 加载 GT mask
        gt_mask_file = None
        for cls_info in meta.get("classes", []):
            if cls_info.get("class") == gt_class:
                gt_mask_file = cls_info.get("mask_file")
                break
        
        if gt_mask_file:
            mask_path = masks_dir / gt_mask_file
            if mask_path.exists():
                gt_mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                if gt_mask is not None:
                    if gt_mask.shape != (h, w):
                        gt_mask = cv2.resize(gt_mask, (w, h), interpolation=cv2.INTER_NEAREST)
                    
                    gt_mask_bool = gt_mask > 127
                    if gt_mask_bool.any():
                        # 提取GT区域的BGR均值
                        gt_pixels = image[gt_mask_bool].astype(np.float32)
                        mean_bgr = gt_pixels.mean(axis=0)
                        class_colors[gt_class].append(mean_bgr)
    
    # 计算每个类别的颜色统计
    print("=" * 80)
    print("GT样本颜色统计分析")
    print("=" * 80)
    
    optimized_hints = {}
    
    for class_name in sorted(class_colors.keys()):
        colors = np.array(class_colors[class_name])
        
        if len(colors) == 0:
            continue
        
        # 计算统计量
        mean_color = colors.mean(axis=0)
        std_color = colors.std(axis=0)
        min_color = colors.min(axis=0)
        max_color = colors.max(axis=0)
        
        # 当前配置中的color_hint
        current_hint = classes_config.get(class_name, {}).get("color_hint", [0, 0, 0])
        
        print(f"\n{class_name}:")
        print(f"  样本数: {len(colors)}")
        print(f"  当前color_hint: {current_hint}")
        print(f"  GT统计均值BGR: [{mean_color[0]:.1f}, {mean_color[1]:.1f}, {mean_color[2]:.1f}]")
        print(f"  GT统计标准差: [{std_color[0]:.1f}, {std_color[1]:.1f}, {std_color[2]:.1f}]")
        print(f"  GT颜色范围B: [{min_color[0]:.1f}, {max_color[0]:.1f}]")
        print(f"  GT颜色范围G: [{min_color[1]:.1f}, {max_color[1]:.1f}]")
        print(f"  GT颜色范围R: [{min_color[2]:.1f}, {max_color[2]:.1f}]")
        
        # 建议的color_hint (使用整数)
        optimized_hint = [int(mean_color[0]), int(mean_color[1]), int(mean_color[2])]
        optimized_hints[class_name] = optimized_hint
        
        # 计算与当前hint的距离
        if current_hint and len(current_hint) == 3:
            dist = np.sqrt(
                (mean_color[0] - current_hint[0])**2 +
                (mean_color[1] - current_hint[1])**2 +
                (mean_color[2] - current_hint[2])**2
            )
            print(f"  与当前hint距离: {dist:.1f}")
            print(f"  建议color_hint: {optimized_hint}")
    
    print("\n" + "=" * 80)
    print("优化后的color_hint配置 (YAML格式)")
    print("=" * 80)
    
    for class_name in sorted(optimized_hints.keys()):
        hint = optimized_hints[class_name]
        print(f"      {class_name}:")
        print(f"        color_hint: [{hint[0]}, {hint[1]}, {hint[2]}]")
    
    return optimized_hints

if __name__ == "__main__":
    analyze_gt_colors()
