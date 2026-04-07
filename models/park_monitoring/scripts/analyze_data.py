#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据集工具脚本 - 水利巡检系统

功能：
1. 数据集统计和分析
2. 标注质量检查
3. 可视化工具
4. 格式验证

作者: 空中智能体团队
日期: 2026-03-26
"""

import os
import sys
import json
import yaml
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict, Counter

import cv2
import numpy as np
from tqdm import tqdm


class DatasetAnalyzer:
    """数据集分析器"""
    
    CATEGORIES = {
        0: "person", 1: "fishing_person", 2: "swimming_person", 3: "playing_person",
        4: "water_gauge", 5: "outlet_pipe", 6: "outlet_active", 7: "pipe_damaged",
        8: "dam_seepage", 9: "boat", 10: "floating_debris",
        11: "water_surface", 12: "warning_line",
        13: "black_water", 14: "red_water", 15: "green_water", 16: "milky_water",
        17: "water_level_mark"
    }
    
    def __init__(self, data_dir: str):
        """
        初始化分析器
        
        Args:
            data_dir: 数据目录
        """
        self.data_dir = Path(data_dir)
        self.stats = {
            "total_images": 0,
            "total_labels": 0,
            "empty_images": 0,
            "missing_labels": 0,
            "class_distribution": defaultdict(int),
            "bbox_sizes": [],
            "aspect_ratios": [],
            "invalid_labels": []
        }
    
    def analyze(self) -> Dict:
        """分析数据集"""
        print("=" * 60)
        print("分析数据集")
        print("=" * 60)
        print(f"数据目录: {self.data_dir}")
        
        # 检查目录结构
        splits = ["train", "val", "test"]
        for split in splits:
            images_dir = self.data_dir / "images" / split
            labels_dir = self.data_dir / "labels" / split
            
            if images_dir.exists():
                images = list(images_dir.glob("*.jpg"))
                labels = list(labels_dir.glob("*.txt"))
                
                print(f"\n{split}:")
                print(f"  图像: {len(images)}")
                print(f"  标注: {len(labels)}")
                
                self.stats[f"{split}_images"] = len(images)
                self.stats[f"{split}_labels"] = len(labels)
        
        # 分析标注内容
        self._analyze_labels(labels_dir)
        
        return self.stats
    
    def _analyze_labels(self, labels_dir: Path):
        """分析标注文件"""
        print("\n分析标注内容...")
        
        for label_path in tqdm(list(labels_dir.glob("*.txt")), desc="  检查标注"):
            try:
                with open(label_path, 'r') as f:
                    lines = f.readlines()
                
                if not lines:
                    self.stats["empty_labels"] += 1
                    continue
                
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        self.stats["invalid_labels"].append(str(label_path))
                        continue
                    
                    class_id = int(parts[0])
                    cx, cy, w, h = map(float, parts[1:5])
                    
                    # 检查范围
                    if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 <= w <= 1 and 0 <= h <= 1):
                        self.stats["invalid_labels"].append(str(label_path))
                        continue
                    
                    # 检查尺寸
                    area = w * h
                    if area < 0.001:  # 太小
                        self.stats["tiny_objects"] += 1
                    
                    self.stats["class_distribution"][class_id] += 1
                    self.stats["bbox_sizes"].append((w, h))
                    
            except Exception as e:
                print(f"  错误: {label_path}: {e}")
        
        # 统计
        print("\n类别分布:")
        for class_id, count in sorted(self.stats["class_distribution"].items()):
            class_name = self.CATEGORIES.get(class_id, f"class_{class_id}")
            print(f"  {class_name}: {count}")
        
        # 检查不平衡
        max_count = max(self.stats["class_distribution"].values())
        min_count = min(self.stats["class_distribution"].values())
        
        if max_count / min_count > 10:
            print(f"\n⚠️ 类别不平衡严重! 最大/最小 = {max_count/min_count}")
        
        return self.stats
    
    def generate_visualizations(self, output_dir: str):
        """生成可视化"""
        import matplotlib.pyplot as plt
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 类别分布
        fig, plt.figure(figsize=(12, 6))
        classes = sorted(self.stats["class_distribution"].keys())
        counts = [self.stats["class_distribution"][c] for c in classes]
        names = [self.CATEGORIES.get(c, f"cls_{c}")laser(c) for c in classes]
        
        plt.bar(names, counts)
        plt.xticks(rotation=45)
        plt.xlabel("类别")
        plt.ylabel("数量")
        plt.title("类别分布")
        plt.tight_layout()
        plt.savefig(output_dir / "class_distribution.png")
        
        # 2. 边界框尺寸分布
        fig, plt.figure(figsize=(10, 8))
        widths = [s[0] for s in self.stats["bbox_sizes"]]
        heights = [s[1] for s in self.stats["bbox_sizes"]]
        plt.scatter(widths, heights, alpha=0.5, s=1)
        plt.xlabel("宽度")
        plt.ylabel("高度")
        plt.title("边界框尺寸分布")
        plt.savefig(output_dir / "bbox_sizes.png")
        
        print(f"\n可视化已保存到 {output_dir}")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="数据集分析")
    
    parser.add_argument(
        "--data",
        type=str,
        required=True,
        help="数据目录"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="analysis",
        help="输出目录"
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="生成可视化"
    )
    
    args = parser.parse_args()
    
    analyzer = DatasetAnalyzer(args.data)
    stats = analyzer.analyze()
    
    if args.visualize:
        analyzer.generate_visualizations(args.output)
    
    print("\n分析完成!")


if __name__ == "__main__":
    main()
