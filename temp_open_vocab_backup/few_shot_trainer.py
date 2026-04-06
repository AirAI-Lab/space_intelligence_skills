#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
开放词汇分割 - 少样本训练器

作者: 空中智能体团队
日期: 2026-03-25
"""

import os
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from PIL import Image
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import yaml
from tqdm import tqdm

# 假设的DINOv3和SAM3导入
# 实际实现需要根据具体库调整


class PromptEncoder(nn.Module):
    """可训练的提示编码器"""
    
    def __init__(
        self,
        embed_dim: int = 256,
        num_prompts: int = 10,
        prompt_length: int = 10
    ):
        super().__init__()
        
        self.embed_dim = embed_dim
        self.num_prompts = num_prompts
        self.prompt_length = prompt_length
        
        # 可学习的提示向量
        self.prompt_embeddings = nn.Parameter(
            torch.randn(num_prompts, prompt_length, embed_dim)
        )
        
        # 类别投影
        self.class_proj = nn.Linear(embed_dim, embed_dim)
    
    def forward(self, class_idx: int):
        """获取指定类别的提示嵌入"""
        return self.prompt_embeddings[class_idx]


class MaskDecoderAdapter(nn.Module):
    """Mask解码器适配器（用于微调）"""
    
    def __init__(
        self,
        input_dim: int = 256,
        hidden_dim: int = 256,
        num_classes: int = 10
    ):
        super().__init__()
        
        self.conv1 = nn.Conv2d(input_dim, hidden_dim, 3, padding=1)
        self.conv2 = nn.Conv2d(hidden_dim, hidden_dim, 3, padding=1)
        self.conv3 = nn.Conv2d(hidden_dim, num_classes, 1)
        
        self.bn1 = nn.BatchNorm2d(hidden_dim)
        self.bn2 = nn.BatchNorm2d(hidden_dim)
    
    def forward(self, x):
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.conv3(x)
        return x


class FewShotTrainer:
    """少样本训练器"""
    
    def __init__(
        self,
        config_path: str,
        device: str = "cuda"
    ):
        """
        初始化训练器
        
        Args:
            config_path: 配置文件路径
            device: 训练设备
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.device = device
        
        # 初始化模型
        self._init_models()
        
        # 初始化数据
        self._init_data()
        
        # 初始化训练参数
        training_config = self.config.get("training", {})
        self.epochs = training_config.get("epochs", 50)
        self.batch_size = training_config.get("batch_size", 4)
        self.lr = training_config.get("lr", 0.001)
        
        # 损失函数
        self.loss_fn = self._get_loss_fn(training_config.get("losses", {}))
    
    def _init_models(self):
        """初始化模型"""
        model_config = self.config.get("model", {})
        
        # 加载预训练backbone（DINOv3/RADIO）
        # 这里简化，实际需要加载真实模型
        print("加载预训练backbone...")
        self.backbone = None  # placeholder
        
        # 加载SAM
        print("加载SAM...")
        self.sam = None  # placeholder
        
        # 初始化可训练模块
        training_config = self.config.get("training", {})
        
        if training_config.get("method") == "prompt_tuning":
            print("初始化提示编码器（可训练）...")
            self.prompt_encoder = PromptEncoder(
                embed_dim=model_config.get("prompt_dim", 256),
                num_prompts=sum(len(v) for v in self.config["open_vocab_classes"].values())
            )
        
        # Mask解码器适配器
        num_classes = sum(len(v) for v in self.config["open_vocab_classes"].values())
        self.mask_decoder = MaskDecoderAdapter(num_classes=num_classes)
        
        # 冻结策略
        if training_config.get("freeze_backbone", True):
            print("冻结backbone参数...")
            # for param in self.backbone.parameters():
            #     param.requires_grad = False
        
        if training_config.get("freeze_sam_encoder", True):
            print("冻结SAM编码器参数...")
            # for param in self.sam.encoder.parameters():
            #     param.requires_grad = False
    
    def _init_data(self):
        """初始化数据"""
        data_config = self.config.get("data", {})
        self.data_root = Path(data_config.get("root", "data/few_shot/"))
        
        # 加载少样本数据
        self.train_data = self._load_few_shot_data("train")
        self.val_data = self._load_few_shot_data("val")
    
    def _load_few_shot_data(self, split: str) -> List[Dict]:
        """加载少样本数据"""
        data_dir = self.data_root / split
        
        samples = []
        
        # 遍历每个类别
        for category, class_list in self.config["open_vocab_classes"].items():
            for class_info in class_list:
                class_name = class_info["name"]
                class_dir = data_dir / category / class_name
                
                if not class_dir.exists():
                    continue
                
                # 加载图像和mask
                image_files = list(class_dir.glob("*.jpg")) + list(class_dir.glob("*.png"))
                
                for img_path in image_files:
                    mask_path = class_dir / f"{img_path.stem}_mask.png"
                    
                    if mask_path.exists():
                        samples.append({
                            "image_path": str(img_path),
                            "mask_path": str(mask_path),
                            "class_name": class_name,
                            "category": category
                        })
        
        print(f"加载 {split} 数据: {len(samples)} 个样本")
        return samples
    
    def _get_loss_fn(self, loss_config: Dict):
        """获取损失函数"""
        mask_loss_type = loss_config.get("mask_loss", "dice")
        
        if mask_loss_type == "dice":
            return self._dice_loss
        elif mask_loss_type == "bce":
            return nn.BCEWithLogitsLoss()
        elif mask_loss_type == "focal":
            return self._focal_loss
        else:
            return self._dice_loss
    
    def _dice_loss(self, pred, target):
        """Dice损失"""
        smooth = 1.0
        pred = torch.sigmoid(pred)
        
        pred_flat = pred.view(-1)
        target_flat = target.view(-1)
        
        intersection = (pred_flat * target_flat).sum()
        
        return 1 - (2.0 * intersection + smooth) / (
            pred_flat.sum() + target_flat.sum() + smooth
        )
    
    def _focal_loss(self, pred, target, alpha=0.25, gamma=2):
        """Focal损失"""
        bce = F.binary_cross_entropy_with_logits(pred, target, reduction='none')
        pt = torch.exp(-bce)
        focal = alpha * (1 - pt) ** gamma * bce
        return focal.mean()
    
    def train(self):
        """训练"""
        print("=" * 60)
        print("开始少样本训练")
        print("=" * 60)
        
        # 优化器
        trainable_params = []
        if hasattr(self, 'prompt_encoder'):
            trainable_params += list(self.prompt_encoder.parameters())
        trainable_params += list(self.mask_decoder.parameters())
        
        optimizer = torch.optim.AdamW(trainable_params, lr=self.lr)
        
        # 学习率调度器
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=self.epochs
        )
        
        # 训练循环
        for epoch in range(self.epochs):
            # 训练
            train_loss = self._train_epoch(epoch, optimizer)
            
            # 验证
            val_loss, val_iou = self._validate_epoch(epoch)
            
            # 更新学习率
            scheduler.step()
            
            # 打印
            print(f"Epoch {epoch+1}/{self.epochs}")
            print(f"  Train Loss: {train_loss:.4f}")
            print(f"  Val Loss: {val_loss:.4f}, Val IoU: {val_iou:.4f}")
        
        print("\n训练完成！")
    
    def _train_epoch(self, epoch: int, optimizer) -> float:
        """训练一个epoch"""
        self.mask_decoder.train()
        if hasattr(self, 'prompt_encoder'):
            self.prompt_encoder.train()
        
        total_loss = 0.0
        
        # 简化实现：随机采样batch
        for i in tqdm(range(len(self.train_data) // self.batch_size)):
            # 获取batch数据
            batch = self._get_batch(self.train_data, self.batch_size)
            
            # 前向传播
            loss = self._forward_batch(batch)
            
            # 反向传播
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        return total_loss / (len(self.train_data) // self.batch_size)
    
    def _validate_epoch(self, epoch: int) -> Tuple[float, float]:
        """验证一个epoch"""
        self.mask_decoder.eval()
        if hasattr(self, 'prompt_encoder'):
            self.prompt_encoder.eval()
        
        total_loss = 0.0
        total_iou = 0.0
        
        with torch.no_grad():
            for i in range(len(self.val_data) // self.batch_size):
                batch = self._get_batch(self.val_data, self.batch_size)
                
                loss = self._forward_batch(batch)
                total_loss += loss.item()
                
                # 计算IoU（简化）
                # actual_iou = compute_iou(pred, target)
                # total_iou += actual_iou
        
        avg_loss = total_loss / (len(self.val_data) // self.batch_size)
        avg_iou = total_iou / (len(self.val_data) // self.batch_size)
        
        return avg_loss, avg_iou
    
    def _get_batch(self, data: List[Dict], batch_size: int) -> List[Dict]:
        """获取一个batch"""
        indices = np.random.choice(len(data), batch_size, replace=False)
        batch = [data[i] for i in indices]
        return batch
    
    def _forward_batch(self, batch: List[Dict]) -> torch.Tensor:
        """前向传播一个batch"""
        # 简化实现
        # 实际需要：
        # 1. 加载图像和mask
        # 2. 通过backbone提取特征
        # 3. 使用SAM编码器
        # 4. 使用可训练模块
        # 5. 计算损失
        
        # Placeholder
        loss = torch.tensor(0.5, requires_grad=True)
        return loss
    
    def save_checkpoint(self, output_path: str):
        """保存checkpoint"""
        checkpoint = {
            "config": self.config,
            "mask_decoder": self.mask_decoder.state_dict(),
        }
        
        if hasattr(self, 'prompt_encoder'):
            checkpoint["prompt_encoder"] = self.prompt_encoder.state_dict()
        
        torch.save(checkpoint, output_path)
        print(f"✓ Checkpoint保存到: {output_path}")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="开放词汇少样本训练")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/dinov3_sam3_water.yaml",
        help="配置文件路径"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="训练设备"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/open_vocab/checkpoint.pth",
        help="输出checkpoint路径"
    )
    
    args = parser.parse_args()
    
    # 初始化训练器
    trainer = FewShotTrainer(
        config_path=args.config,
        device=args.device
    )
    
    # 训练
    trainer.train()
    
    # 保存
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    trainer.save_checkpoint(args.output)


if __name__ == "__main__":
    main()
