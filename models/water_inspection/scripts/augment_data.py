#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据增强脚本 - 水利巡检系统

功能：
1. 针对水利场景的专门增强
2. 小样本类别过采样
3. 困难样本挖掘
4. 平衡数据集

作者: 空中智能体团队
日期: 2026-03-26
"""

import os
import sys
import json
import yaml
import random
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from tqdm import tqdm

try:
    import albumentations as A
    from albumentations.pytorch import ToTensorV2
    ALBUMENTATIONS_AVAILABLE = True
except ImportError:
    ALBUMENTATIONS_AVAILABLE = False
    print("警告: albumentations未安装，将使用基础增强")


class WaterInspectionAugmentor:
    """水利巡检数据增强器"""
    
    # 水质颜色增强参数
    WATER_COLOR_PARAMS = {
        "black_water": {
            "hsv_h": (-0.05, 0.05),
            "hsv_s": (0.0, 0.3),
            "hsv_v": (-0.4, -0.2),
        },
        "brown_water": {
            "hsv_h": (0.02, 0.08),
            "hsv_s": (0.2, 0.5),
            "hsv_v": (-0.3, -0.1),
        },
        "yellow_water": {
            "hsv_h": (0.08, 0.15),
            "hsv_s": (0.3, 0.6),
            "hsv_v": (0.0, 0.2),
        },
        "green_water": {
            "hsv_h": (0.2, 0.4),
            "hsv_s": (0.4, 0.7),
            "hsv_v": (-0.2, 0.1),
        },
        "red_water": {
            "hsv_h": (0.0, 0.1),
            "hsv_s": (0.3, 0.6),
            "hsv_v": (-0.1, 0.1),
        },
        "milky_water": {
            "hsv_h": (-0.1, 0.1),
            "hsv_s": (-0.5, -0.3),
            "hsv_v": (0.2, 0.4),
        },
        "foam_water": {
            "hsv_h": (-0.05, 0.05),
            "hsv_s": (-0.6, -0.4),
            "hsv_v": (0.3, 0.5),
        },
    }
    
    # 稀有类别（需要过采样）
    RARE_CLASSES = [7, 8, 13, 14, 15, 16]  # pipe_damaged, dam_seepage, 水质异常
    
    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        config_path: Optional[str] = None
    ):
        """
        初始化增强器
        
        Args:
            input_dir: 输入数据目录
            output_dir: 输出数据目录
            config_path: 配置文件路径
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        
        # 加载配置
        if config_path and Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = self._default_config()
        
        # 统计
        self.stats = defaultdict(int)
        
        # 初始化增强管道
        self._init_transforms()
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "augment_ratio": 3,  # 每张图增强3次
            "target_samples_per_class": 500,  # 目标：每类500个样本
            "water_specific": True,  # 启用水利场景特定增强
            "mosaic": True,  # 启用Mosaic增强
            "mixup": True,  # 启用MixUp增强
            "copy_paste": True,  # 启用复制粘贴
            "seed": 42
        }
    
    def _init_transforms(self):
        """初始化增强变换"""
        
        if ALBUMENTATIONS_AVAILABLE:
            # 通用增强
            self.general_transform = A.Compose([
                # 几何变换
                A.HorizontalFlip(p=0.5),
                A.ShiftScaleRotate(
                    shift_limit=0.1,
                    scale_limit=0.2,
                    rotate_limit=15,
                    p=0.5
                ),
                
                # 颜色变换
                A.RandomBrightnessContrast(
                    brightness_limit=0.3,
                    contrast_limit=0.3,
                    p=0.5
                ),
                A.HueSaturationValue(
                    hue_shift_limit=20,
                    sat_shift_limit=30,
                    val_shift_limit=20,
                    p=0.5
                ),
                
                # 模拟摄像头质量
                A.OneOf([
                    A.GaussNoise(var_limit=(10, 50), p=1.0),
                    A.GaussianBlur(blur_limit=7, p=1.0),
                    A.MotionBlur(blur_limit=7, p=1.0),
                ], p=0.3),
                
                # 遮挡
                A.CoarseDropout(
                    max_holes=8,
                    max_height=32,
                    max_width=32,
                    p=0.2
                ),
                
                # 天气模拟
                A.OneOf([
                    A.RandomRain(p=1.0),
                    A.RandomFog(p=1.0),
                    A.RandomSunFlare(p=1.0),
                ], p=0.1),
                
            ], bbox_params=A.BboxParams(
                format='yolo',
                label_fields=['class_labels']
            ))
            
            # 水利场景特定增强
            self.water_transform = A.Compose([
                # 水面反光模拟
                A.RandomSunFlare(
                    flare_roi=(0, 0, 1, 0.5),
                    p=0.2
                ),
                
                # 水波纹效果
                A.ElasticTransform(
                    alpha=50,
                    sigma=5,
                    p=0.1
                ),
                
                # 模拟不同光照
                A.OneOf([
                    A.CLAHE(clip_limit=4.0, p=1.0),
                    A.Equalize(p=1.0),
                ], p=0.3),
            ], bbox_params=A.BboxParams(
                format='yolo',
                label_fields=['class_labels']
            ))
        else:
            self.general_transform = None
            self.water_transform = None
    
    def augment(self) -> Dict:
        """
        执行数据增强
        
        Returns:
            统计信息
        """
        print("=" * 60)
        print("水利巡检数据增强")
        print("=" * 60)
        print(f"输入目录: {self.input_dir}")
        print(f"输出目录: {self.output_dir}")
        print("=" * 60)
        
        # 1. 分析类别分布
        class_dist = self._analyze_class_distribution()
        
        # 2. 创建输出目录
        self._create_output_dirs()
        
        # 3. 基础增强（复制原始数据）
        self._copy_original_data()
        
        # 4. 过采样稀有类别
        self._oversample_rare_classes(class_dist)
        
        # 5. Mosaic增强
        if self.config["mosaic"]:
            self._apply_mosaic_augmentation(class_dist)
        
        # 6. MixUp增强
        if self.config["mixup"]:
            self._apply_mixup_augmentation(class_dist)
        
        # 7. 复制粘贴增强
        if self.config["copy_paste"]:
            self._apply_copy_paste_augmentation(class_dist)
        
        # 8. 生成增强报告
        self._generate_augmentation_report(class_dist)
        
        return dict(self.stats)
    
    def _analyze_class_distribution(self) -> Dict[int, int]:
        """分析类别分布"""
        print("\n分析类别分布...")
        
        labels_dir = self.input_dir / "labels"
        class_count = Counter()
        
        for label_file in labels_dir.glob("*.txt"):
            with open(label_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        class_id = int(parts[0])
                        class_count[class_id] += 1
        
        print("\n类别分布:")
        for class_id, count in sorted(class_count.items()):
            rarity = " ⚠️ 稀有" if class_id in self.RARE_CLASSES else ""
            print(f"  类别 {class_id}: {count}{rarity}")
        
        self.stats["original_samples"] = sum(class_count.values())
        self.stats["class_distribution"] = dict(class_count)
        
        return dict(class_count)
    
    def _create_output_dirs(self):
        """创建输出目录"""
        (self.output_dir / "images").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "labels").mkdir(parents=True, exist_ok=True)
    
    def _copy_original_data(self):
        """复制原始数据"""
        print("\n复制原始数据...")
        
        images_dir = self.input_dir / "images"
        labels_dir = self.input_dir / "labels"
        
        for img_path in tqdm(list(images_dir.glob("*")), desc="复制图像"):
            if img_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                continue
            
            # 复制图像
            shutil.copy(img_path, self.output_dir / "images" / img_path.name)
            self.stats["copied_images"] += 1
            
            # 复制标注
            label_path = labels_dir / f"{img_path.stem}.txt"
            if label_path.exists():
                shutil.copy(label_path, self.output_dir / "labels" / label_path.name)
                self.stats["copied_labels"] += 1
    
    def _oversample_rare_classes(
        self,
        class_dist: Dict[int, int],
        target_count: int = None
    ):
        """过采样稀有类别"""
        print("\n过采样稀有类别...")
        
        target = target_count or self.config["target_samples_per_class"]
        labels_dir = self.input_dir / "labels"
        images_dir = self.input_dir / "images"
        
        # 找出包含稀有类别的样本
        rare_samples = defaultdict(list)
        
        for label_file in labels_dir.glob("*.txt"):
            with open(label_file, 'r') as f:
                lines = f.readlines()
            
            class_ids_in_file = set()
            for line in lines:
                parts = line.strip().split()
                if parts:
                    class_id = int(parts[0])
                    class_ids_in_file.add(class_id)
            
            for class_id in class_ids_in_file:
                if class_id in self.RARE_CLASSES:
                    rare_samples[class_id].append((label_file, lines))
        
        # 过采样
        random.seed(self.config["seed"])
        
        for class_id in self.RARE_CLASSES:
            current_count = class_dist.get(class_id, 0)
            samples_needed = target - current_count
            
            if samples_needed <= 0 or class_id not in rare_samples:
                continue
            
            print(f"\n  类别 {class_id}: 需要 {samples_needed} 个样本")
            
            samples = rare_samples[class_id]
            for i in tqdm(range(samples_needed), desc=f"  过采样类别 {class_id}"):
                # 随机选择一个样本
                label_file, lines = random.choice(samples)
                img_file = images_dir / f"{label_file.stem}.jpg"
                
                if not img_file.exists():
                    img_file = images_dir / f"{label_file.stem}.png"
                
                if not img_file.exists():
                    continue
                
                # 读取图像和标注
                img = cv2.imread(str(img_file))
                
                # 解析标注
                bboxes = []
                class_labels = []
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_labels.append(int(parts[0]))
                        bboxes.append([float(x) for x in parts[1:5]])
                
                # 应用增强
                if self.general_transform and ALBUMENTATIONS_AVAILABLE:
                    try:
                        transformed = self.general_transform(
                            image=img,
                            bboxes=bboxes,
                            class_labels=class_labels
                        )
                        aug_img = transformed["image"]
                        aug_bboxes = transformed["bboxes"]
                        aug_labels = transformed["class_labels"]
                    except Exception as e:
                        print(f"    增强失败: {e}")
                        continue
                else:
                    aug_img = img
                    aug_bboxes = bboxes
                    aug_labels = class_labels
                
                # 保存
                output_name = f"{label_file.stem}_oversample_{i}"
                
                cv2.imwrite(
                    str(self.output_dir / "images" / f"{output_name}.jpg"),
                    aug_img
                )
                
                with open(self.output_dir / "labels" / f"{output_name}.txt", 'w') as f:
                    for label, bbox in zip(aug_labels, aug_bboxes):
                        f.write(f"{label} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\n")
                
                self.stats[f"oversampled_class_{class_id}"] += 1
    
    def _apply_mosaic_augmentation(self, class_dist: Dict[int, int]):
        """Mosaic增强（4张图拼接）"""
        print("\n应用 Mosaic 增强...")
        
        images_dir = self.input_dir / "images"
        labels_dir = self.input_dir / "labels"
        
        # 收集所有样本
        all_samples = []
        for img_path in images_dir.glob("*.jpg"):
            label_path = labels_dir / f"{img_path.stem}.txt"
            if label_path.exists():
                all_samples.append((img_path, label_path))
        
        if len(all_samples) < 4:
            print("  样本数不足，跳过 Mosaic")
            return
        
        # 生成 Mosaic 样本
        n_mosaic = len(all_samples) // 4
        
        for i in tqdm(range(n_mosaic), desc="  生成 Mosaic"):
            # 随机选择4张图
            samples = random.sample(all_samples, 4)
            
            # 创建 Mosaic
            mosaic_img, mosaic_labels = self._create_mosaic(samples)
            
            # 保存
            output_name = f"mosaic_{i}"
            cv2.imwrite(
                str(self.output_dir / "images" / f"{output_name}.jpg"),
                mosaic_img
            )
            
            with open(self.output_dir / "labels" / f"{output_name}.txt", 'w') as f:
                for label, bbox in mosaic_labels:
                    f.write(f"{label} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\n")
            
            self.stats["mosaic_samples"] += 1
    
    def _create_mosaic(
        self,
        samples: List[Tuple[Path, Path]],
        target_size: int = 640
    ) -> Tuple[np.ndarray, List]:
        """创建 Mosaic 图像"""
        # 读取4张图像
        imgs = []
        all_bboxes = []
        all_labels = []
        
        for img_path, label_path in samples:
            img = cv2.imread(str(img_path))
            h, w = img.shape[:2]
            
            # 读取标注
            bboxes = []
            labels = []
            with open(label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        labels.append(int(parts[0]))
                        # YOLO格式转像素坐标
                        cx, cy, bw, bh = [float(x) for x in parts[1:5]]
                        x1 = int((cx - bw/2) * w)
                        y1 = int((cy - bh/2) * h)
                        x2 = int((cx + bw/2) * w)
                        y2 = int((cy + bh/2) * h)
                        bboxes.append([x1, y1, x2, y2])
            
            # 调整尺寸到目标的一半
            img_resized = cv2.resize(img, (target_size // 2, target_size // 2))
            scale_x = (target_size // 2) / w
            scale_y = (target_size // 2) / h
            
            # 调整边界框
            scaled_bboxes = []
            for bbox in bboxes:
                x1, y1, x2, y2 = bbox
                scaled_bboxes.append([
                    int(x1 * scale_x),
                    int(y1 * scale_y),
                    int(x2 * scale_x),
                    int(y2 * scale_y)
                ])
            
            imgs.append(img_resized)
            all_bboxes.append(scaled_bboxes)
            all_labels.append(labels)
        
        # 创建 Mosaic（2x2）
        mosaic = np.zeros((target_size, target_size, 3), dtype=np.uint8)
        mosaic_labels = []
        
        # 位置偏移
        offsets = [(0, 0), (target_size//2, 0), (0, target_size//2), (target_size//2, target_size//2)]
        
        for idx, (img, bboxes, labels) in enumerate(zip(imgs, all_bboxes, all_labels)):
            ox, oy = offsets[idx]
            
            # 放置图像
            mosaic[oy:oy+target_size//2, ox:ox+target_size//2] = img
            
            # 调整标注坐标
            for bbox, label in zip(bboxes, labels):
                x1, y1, x2, y2 = bbox
                # 添加偏移并归一化
                new_x1 = (x1 + ox) / target_size
                new_y1 = (y1 + oy) / target_size
                new_x2 = (x2 + ox) / target_size
                new_y2 = (y2 + oy) / target_size
                
                # 转回YOLO格式
                cx = (new_x1 + new_x2) / 2
                cy = (new_y1 + new_y2) / 2
                bw = new_x2 - new_x1
                bh = new_y2 - new_y1
                
                mosaic_labels.append((label, [cx, cy, bw, bh]))
        
        return mosaic, mosaic_labels
    
    def _apply_mixup_augmentation(self, class_dist: Dict[int, int]):
        """MixUp增强"""
        print("\n应用 MixUp 增强...")
        
        images_dir = self.input_dir / "images"
        labels_dir = self.input_dir / "labels"
        
        # 收集所有样本
        all_samples = []
        for img_path in images_dir.glob("*.jpg"):
            label_path = labels_dir / f"{img_path.stem}.txt"
            if label_path.exists():
                all_samples.append((img_path, label_path))
        
        if len(all_samples) < 2:
            print("  样本数不足，跳过 MixUp")
            return
        
        # 生成 MixUp 样本
        n_mixup = len(all_samples) // 5
        
        for i in tqdm(range(n_mixup), desc="  生成 MixUp"):
            # 随机选择2张图
            sample1, sample2 = random.sample(all_samples, 2)
            
            # 读取图像
            img1 = cv2.imread(str(sample1[0]))
            img2 = cv2.imread(str(sample2[0]))
            
            # 调整尺寸一致
            h, w = img1.shape[:2]
            img2 = cv2.resize(img2, (w, h))
            
            # MixUp
            alpha = random.uniform(0.3, 0.7)
            mix_img = cv2.addWeighted(img1, alpha, img2, 1-alpha, 0)
            
            # 合并标注
            mix_labels = []
            
            with open(sample1[1], 'r') as f:
                for line in f:
                    mix_labels.append(line.strip())
            
            with open(sample2[1], 'r') as f:
                for line in f:
                    mix_labels.append(line.strip())
            
            # 保存
            output_name = f"mixup_{i}"
            cv2.imwrite(
                str(self.output_dir / "images" / f"{output_name}.jpg"),
                mix_img
            )
            
            with open(self.output_dir / "labels" / f"{output_name}.txt", 'w') as f:
                f.write('\n'.join(mix_labels))
            
            self.stats["mixup_samples"] += 1
    
    def _apply_copy_paste_augmentation(self, class_dist: Dict[int, int]):
        """复制粘贴增强（针对小目标）"""
        print("\n应用 Copy-Paste 增强...")
        
        # 简化实现：从其他图像复制目标到当前图像
        # 这里仅实现基础版本，完整版本需要实例分割标注
        
        print("  Copy-Paste 需要实例分割标注，跳过")
        self.stats["copy_paste_skipped"] = 1
    
    def _generate_augmentation_report(self, class_dist: Dict[int, int]):
        """生成增强报告"""
        print("\n" + "=" * 60)
        print("增强完成！")
        print("=" * 60)
        
        print("\n统计信息:")
        for key, value in self.stats.items():
            print(f"  {key}: {value}")
        
        # 保存报告
        report = {
            "input_dir": str(self.input_dir),
            "output_dir": str(self.output_dir),
            "config": self.config,
            "statistics": dict(self.stats),
            "original_distribution": class_dist
        }
        
        report_path = self.output_dir / "augmentation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n报告已保存: {report_path}")


# 导入shutil（上面遗漏了）
import shutil


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="水利巡检数据增强")
    
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="输入数据目录（包含 images/ 和 labels/）"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="输出数据目录"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="配置文件路径"
    )
    parser.add_argument(
        "--target-samples",
        type=int,
        default=500,
        help="目标每类样本数"
    )
    parser.add_argument(
        "--no-mosaic",
        action="store_true",
        help="禁用 Mosaic 增强"
    )
    parser.add_argument(
        "--no-mixup",
        action="store_true",
        help="禁用 MixUp 增强"
    )
    
    args = parser.parse_args()
    
    # 初始化
    augmentor = WaterInspectionAugmentor(
        input_dir=args.input,
        output_dir=args.output,
        config_path=args.config
    )
    
    # 覆盖配置
    augmentor.config["target_samples_per_class"] = args.target_samples
    if args.no_mosaic:
        augmentor.config["mosaic"] = False
    if args.no_mixup:
        augmentor.config["mixup"] = False
    
    # 执行
    stats = augmentor.augment()


if __name__ == "__main__":
    main()
