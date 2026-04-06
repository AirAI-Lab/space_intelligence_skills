#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YOLO数据集类

作者: 空中智能体团队
日期: 2026-03-25
"""

import os
import cv2
import torch
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from torch.utils.data import Dataset
import albumentations as A
from albumentations.pytorch import ToTensorV2


class WaterInspectionDataset(Dataset):
    """水利巡检数据集"""
    
    def __init__(
        self,
        root_dir: str,
        split: str = "train",
        img_size: int = 640,
        augment: bool = False,
        transform=None
    ):
        """
        初始化数据集
        
        Args:
            root_dir: 数据根目录
            split: 数据划分 (train/val/test)
            img_size: 图像尺寸
            augment: 是否数据增强
            transform: 自定义变换
        """
        self.root_dir = Path(root_dir)
        self.split = split
        self.img_size = img_size
        self.augment = augment
        self.transform = transform
        
        # 加载图像列表
        self.image_dir = self.root_dir / "images" / split
        self.label_dir = self.root_dir / "labels" / split
        
        self.image_files = sorted(list(self.image_dir.glob("*.jpg")) + 
                                 list(self.image_dir.glob("*.png")))
        
        print(f"加载 {split} 数据集: {len(self.image_files)} 张图像")
        
        # 默认数据增强
        if augment and transform is None:
            self.transform = self._default_augment()
    
    def _default_augment(self):
        """默认数据增强"""
        return A.Compose([
            A.HorizontalFlip(p=0.5),
            A.ShiftScaleRotate(
                shift_limit=0.1,
                scale_limit=0.2,
                rotate_limit=15,
                p=0.5
            ),
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
            A.GaussNoise(var_limit=(10, 50), p=0.2),
            A.GaussianBlur(blur_limit=7, p=0.2),
            A.CoarseDropout(
                max_holes=8,
                max_height=32,
                max_width=32,
                p=0.2
            ),
            A.Resize(self.img_size, self.img_size),
            ToTensorV2()
        ], bbox_params=A.BboxParams(
            format='yolo',
            label_fields=['class_labels']
        ))
    
    def __len__(self):
        return len(self.image_files)
    
    def __getitem__(self, idx):
        # 读取图像
        img_path = self.image_files[idx]
        image = cv2.imread(str(img_path))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 读取标签
        label_path = self.label_dir / (img_path.stem + ".txt")
        bboxes = []
        class_labels = []
        
        if label_path.exists():
            with open(label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_id = int(parts[0])
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                        
                        class_labels.append(class_id)
                        bboxes.append([x_center, y_center, width, height])
        
        # 数据增强
        if self.transform:
            transformed = self.transform(
                image=image,
                bboxes=bboxes,
                class_labels=class_labels
            )
            image = transformed['image']
            bboxes = transformed['bboxes']
            class_labels = transformed['class_labels']
        else:
            # 默认处理
            image = cv2.resize(image, (self.img_size, self.img_size))
            image = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0
        
        # 转换为tensor
        bboxes = torch.tensor(bboxes, dtype=torch.float32)
        class_labels = torch.tensor(class_labels, dtype=torch.long)
        
        return {
            "image": image,
            "bboxes": bboxes,
            "class_labels": class_labels,
            "image_path": str(img_path)
        }
    
    @staticmethod
    def collate_fn(batch):
        """自定义batch整理函数"""
        images = []
        bboxes = []
        class_labels = []
        image_paths = []
        
        for item in batch:
            images.append(item["image"])
            bboxes.append(item["bboxes"])
            class_labels.append(item["class_labels"])
            image_paths.append(item["image_path"])
        
        return {
            "images": torch.stack(images),
            "bboxes": bboxes,
            "class_labels": class_labels,
            "image_paths": image_paths
        }


class WaterInspectionDataModule:
    """数据模块（管理训练/验证/测试数据）"""
    
    def __init__(
        self,
        root_dir: str,
        img_size: int = 640,
        batch_size: int = 16,
        num_workers: int = 4,
        augment_config: Optional[Dict] = None
    ):
        """
        初始化数据模块
        
        Args:
            root_dir: 数据根目录
            img_size: 图像尺寸
            batch_size: batch大小
            num_workers: 数据加载线程数
            augment_config: 数据增强配置
        """
        self.root_dir = root_dir
        self.img_size = img_size
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.augment_config = augment_config
    
    def train_dataloader(self):
        """训练数据加载器"""
        dataset = WaterInspectionDataset(
            self.root_dir,
            split="train",
            img_size=self.img_size,
            augment=True
        )
        
        return torch.utils.data.DataLoader(
            dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers,
            collate_fn=WaterInspectionDataset.collate_fn,
            pin_memory=True
        )
    
    def val_dataloader(self):
        """验证数据加载器"""
        dataset = WaterInspectionDataset(
            self.root_dir,
            split="val",
            img_size=self.img_size,
            augment=False
        )
        
        return torch.utils.data.DataLoader(
            dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            collate_fn=WaterInspectionDataset.collate_fn,
            pin_memory=True
        )
    
    def test_dataloader(self):
        """测试数据加载器"""
        dataset = WaterInspectionDataset(
            self.root_dir,
            split="test",
            img_size=self.img_size,
            augment=False
        )
        
        return torch.utils.data.DataLoader(
            dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            collate_fn=WaterInspectionDataset.collate_fn,
            pin_memory=True
        )


def main():
    """测试数据集"""
    # 示例
    dataset = WaterInspectionDataset(
        root_dir="data/processed/",
        split="train",
        img_size=640,
        augment=True
    )
    
    print(f"数据集大小: {len(dataset)}")
    
    # 测试加载
    sample = dataset[0]
    print(f"\n样本形状:")
    print(f"  图像: {sample['image'].shape}")
    print(f"  边界框: {sample['bboxes'].shape}")
    print(f"  类别标签: {sample['class_labels'].shape}")


if __name__ == "__main__":
    main()
