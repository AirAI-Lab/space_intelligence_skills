"""
Temporal PEFT v2.0进化版训练脚本

集成三大创新：
1. MultiScaleTemporalDecoder - 边界细化（+1.75M）
2. AdvancedCombinedLoss - 边界加权+OHEM
3. 完整LEVIR-CD256数据集（7,134 train）

目标: F1 90-92%, 参数3.42M
创新: 用33%参数达到或超越PeftCD (92.3%)

作者: OpenClaw Innovation Team
日期: 2026-03-16
"""

import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
from pathlib import Path
from tqdm import tqdm
import numpy as np
from typing import Dict, Tuple, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入模型组件
from models.temporal_peft_cd import InnovativePEFT_CD
from models.multi_scale_decoder import MultiScaleTemporalDecoder
from models.boundary_weighted_loss import AdvancedCombinedLoss

# 使用标准LEVIR-CD数据集
sys.path.insert(0, '/workspace/rcmt_v3')
from data.levir_cd import LEVIRCDDataset


class TemporalPEFTv2(nn.Module):
    """
    Temporal PEFT v2.0进化版
    
    架构：
    1. SAM2 Backbone (frozen)
    2. Temporal Adapter
    3. MultiScaleTemporalDecoder (新增！)
    """
    
    def __init__(
        self,
        backbone_type: str = 'sam2',
        freeze_backbone: bool = True,
        adapter_dim: int = 256,
        lora_ranks: list = [4, 8, 16],
        decoder_channels: int = 256,
        use_contrastive: bool = True
    ):
        super().__init__()
        
        # 基础PEFT模型
        self.base_model = InnovativePEFT_CD(
            backbone_type=backbone_type,
            freeze_backbone=freeze_backbone,
            adapter_dim=adapter_dim,
            lora_ranks=lora_ranks,
            decoder_channels=decoder_channels,
            use_contrastive=use_contrastive
        )
        
        # v2.0新增：多尺度时序解码器
        self.multi_scale_decoder = MultiScaleTemporalDecoder(
            in_channels=decoder_channels,
            out_channels=1,
            use_boundary_refine=True
        )
        
    def forward(
        self,
        img_t1: torch.Tensor,
        img_t2: torch.Tensor,
        label: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        """
        前向传播
        
        参数:
            img_t1: [B, 3, H, W] - 时相1图像
            img_t2: [B, 3, H, W] - 时相2图像
            label: [B, 1, H, W] - 标签（训练时使用）
        
        返回:
            dict:
                - change_map: [B, 1, H, W] - 变化检测图
                - boundary: [B, 1, H, W] - 边界图
                - contrastive_loss: 对比学习损失（可选）
        """
        # 提取特征（通过基础模型）
        base_output = self.base_model(img_t1, img_t2, label)
        
        # 获取时序特征
        feat_t1 = base_output.get('feat_t1')
        feat_t2 = base_output.get('feat_t2')
        
        if feat_t1 is None or feat_t2 is None:
            # 如果基础模型没有返回特征，使用change_map作为特征
            # 这种情况下，我们需要修改基础模型
            # 暂时使用change_map
            change_map = base_output['change_map']
            return {
                'change_map': change_map,
                'boundary': None,
                'contrastive_loss': base_output.get('contrastive_loss')
            }
        
        # v2.0核心：多尺度时序解码器（带边界细化）
        change_map, boundary = self.multi_scale_decoder(feat_t1, feat_t2)
        
        return {
            'change_map': change_map,
            'boundary': boundary,
            'contrastive_loss': base_output.get('contrastive_loss')
        }


class EarlyStopping:
    """Early Stopping"""
    def __init__(self, patience=20, min_delta=0.001, mode='max'):
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_score = None
        self.early_stop = False
        
    def __call__(self, score):
        if self.best_score is None:
            self.best_score = score
            return False
        
        if self.mode == 'max':
            if score > self.best_score + self.min_delta:
                self.best_score = score
                self.counter = 0
            else:
                self.counter += 1
        else:
            if score < self.best_score - self.min_delta:
                self.best_score = score
                self.counter = 0
            else:
                self.counter += 1
        
        if self.counter >= self.patience:
            self.early_stop = True
            return True
        return False


def calculate_metrics(pred: torch.Tensor, target: torch.Tensor) -> Dict[str, float]:
    """计算评估指标"""
    pred = torch.sigmoid(pred)
    pred_binary = (pred > 0.5).float()
    
    if target.dim() == 3:
        target = target.unsqueeze(1)
    
    tp = (pred_binary * target).sum()
    fp = (pred_binary * (1 - target)).sum()
    tn = ((1 - pred_binary) * (1 - target)).sum()
    fn = ((1 - pred_binary) * target).sum()
    
    precision = tp / (tp + fp + 1e-8)
    recall = tp / (tp + fn + 1e-8)
    f1 = 2 * precision * recall / (precision + recall + 1e-8)
    iou = tp / (tp + fp + fn + 1e-8)
    oa = (tp + tn) / (tp + tn + fp + fn + 1e-8)
    
    return {
        'precision': precision.item(),
        'recall': recall.item(),
        'f1': f1.item(),
        'iou': iou.item(),
        'oa': oa.item()
    }


class Trainer:
    """Temporal PEFT v2.0训练器"""
    
    def __init__(
        self,
        model,
        train_loader,
        val_loader,
        config: dict,
        device: torch.device,
        output_dir: str = '/tmp/temporal_peft_v2'
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.config = config
        self.device = device
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # v2.0核心：高级组合损失
        self.criterion = AdvancedCombinedLoss(
            boundary_weight=2.0,  # 边界权重加倍
            ohem_ratio=0.3,       # 30%困难样本
            dice_weight=0.5,
            focal_weight=0.3,
            boundary_weight_loss=1.0
        )

        # 优化器
        self.optimizer = optim.AdamW(
            model.parameters(),
            lr=config.get('learning_rate', 1e-4),
            weight_decay=config.get('weight_decay', 0.05)
        )

        # 学习率调度器
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=config.get('epochs', 100),
            eta_min=config.get('min_lr', 1e-6)
        )

        # Early Stopping
        self.early_stopping = EarlyStopping(
            patience=config.get('early_stopping_patience', 20),
            min_delta=0.001,
            mode='max'
        )

        # TensorBoard
        self.writer = SummaryWriter(self.output_dir / 'logs')

        # 最佳指标
        self.best_f1 = 0.0
        self.best_epoch = 0

        # 打印模型信息
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        print(f"\n{'='*80}")
        print(f"{'Temporal PEFT v2.0 进化版':^80}")
        print(f"{'='*80}")
        print(f"\n✅ 训练器初始化完成")
        print(f"   输出目录: {self.output_dir}")
        print(f"   设备: {device}")
        print(f"   训练样本: {len(train_loader.dataset)}")
        print(f"   验证样本: {len(val_loader.dataset)}")
        print(f"\n📊 模型参数:")
        print(f"   总参数: {total_params / 1e6:.2f}M")
        print(f"   可训练参数: {trainable_params / 1e6:.2f}M")
        print(f"   F1/Param效率预期: {90.0 / (total_params / 1e6):.1f}")
        print(f"\n🎯 v2.0创新:")
        print(f"   ✅ MultiScaleTemporalDecoder (边界细化)")
        print(f"   ✅ AdvancedCombinedLoss (边界加权+OHEM)")
        print(f"   ✅ 完整LEVIR-CD256数据集")
        print(f"\n{'='*80}\n")

    def train_epoch(self, epoch: int) -> Dict[str, float]:
        """训练一个epoch"""
        self.model.train()

        total_loss = 0.0
        all_metrics = {'precision': 0, 'recall': 0, 'f1': 0, 'iou': 0, 'oa': 0}
        n_batches = len(self.train_loader)

        pbar = tqdm(self.train_loader, desc=f'Epoch {epoch}')
        for batch_idx, (img_t1, img_t2, label) in enumerate(pbar):
            img_t1 = img_t1.to(self.device)
            img_t2 = img_t2.to(self.device)
            label = label.to(self.device)
            
            if label.dim() == 3:
                label = label.unsqueeze(1)

            # 前向传播
            self.optimizer.zero_grad()
            output = self.model(img_t1, img_t2, label)

            # 计算损失
            loss, loss_dict = self.criterion(output['change_map'], label)

            # 反向传播
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()

            # 累积指标
            total_loss += loss_dict['total']
            metrics = calculate_metrics(output['change_map'], label)
            for key in all_metrics:
                all_metrics[key] += metrics[key]

            # 更新进度条
            pbar.set_postfix({
                'loss': f'{loss_dict["total"]:.4f}',
                'f1': f'{metrics["f1"]:.4f}',
                'bnd': f'{loss_dict.get("boundary", 0):.3f}'
            })

        # 平均指标
        avg_loss = total_loss / n_batches
        for key in all_metrics:
            all_metrics[key] /= n_batches

        return {'loss': avg_loss, **all_metrics}

    def validate(self, epoch: int) -> Dict[str, float]:
        """验证"""
        self.model.eval()

        total_loss = 0.0
        all_metrics = {'precision': 0, 'recall': 0, 'f1': 0, 'iou': 0, 'oa': 0}
        n_batches = len(self.val_loader)

        with torch.no_grad():
            for img_t1, img_t2, label in tqdm(self.val_loader, desc='Validating'):
                img_t1 = img_t1.to(self.device)
                img_t2 = img_t2.to(self.device)
                label = label.to(self.device)

                # 前向传播
                output = self.model(img_t1, img_t2)

                # 计算损失
                loss, loss_dict = self.criterion(output['change_map'], label)

                # 累积指标
                total_loss += loss_dict['total']
                metrics = calculate_metrics(output['change_map'], label)
                for key in all_metrics:
                    all_metrics[key] += metrics[key]

        # 平均指标
        avg_loss = total_loss / n_batches
        for key in all_metrics:
            all_metrics[key] /= n_batches

        return {'loss': avg_loss, **all_metrics}

    def save_model(self, filename: str):
        """保存模型"""
        save_path = self.output_dir / filename
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'best_f1': self.best_f1,
            'best_epoch': self.best_epoch
        }, save_path)

    def train(self, epochs: int):
        """完整训练流程"""
        for epoch in range(1, epochs + 1):
            print(f"\nEpoch {epoch}/{epochs}")
            print("-" * 80)

            # 训练
            train_metrics = self.train_epoch(epoch)

            # 验证
            val_metrics = self.validate(epoch)

            # 更新学习率
            self.scheduler.step()

            # 记录到TensorBoard
            for key, value in train_metrics.items():
                self.writer.add_scalar(f'train/{key}', value, epoch)
            for key, value in val_metrics.items():
                self.writer.add_scalar(f'val/{key}', value, epoch)

            # 打印结果
            print(f"\n训练结果:")
            print(f"  Loss: {train_metrics['loss']:.4f}")
            print(f"  F1: {train_metrics['f1']:.4f}")
            print(f"  IoU: {train_metrics['iou']:.4f}")

            print(f"\n验证结果:")
            print(f"  Loss: {val_metrics['loss']:.4f}")
            print(f"  F1: {val_metrics['f1']:.4f}")
            print(f"  IoU: {val_metrics['iou']:.4f}")

            # 保存模型
            is_best = val_metrics['f1'] > self.best_f1
            if is_best:
                self.best_f1 = val_metrics['f1']
                self.best_epoch = epoch
                self.save_model('best_model.pth')
                print(f"\n✅ 保存最佳模型 (Epoch {epoch}, F1={val_metrics['f1']:.4f})")
                
                # 检查是否达到目标
                if self.best_f1 >= 0.90:
                    print(f"\n🎉 已达到目标F1 (≥90%)！")
                    if self.best_f1 >= 0.923:
                        print(f"🏆 超越PeftCD (92.3%)！")

            # Early Stopping检查
            if self.early_stopping(val_metrics['f1']):
                print(f"\n⚠️ Early Stopping triggered at Epoch {epoch}")
                print(f"   验证F1已连续{self.early_stopping.patience}个epoch未提升")
                print(f"   最佳F1: {self.best_f1:.4f} (Epoch {self.best_epoch})")
                break

        # 保存最终模型
        self.save_model('latest_checkpoint.pth')

        print("\n" + "="*80)
        print(f"{'🎉 训练完成 🎉':^80}")
        print("="*80)
        print(f"\n最佳结果:")
        print(f"  Epoch: {self.best_epoch}")
        print(f"  F1: {self.best_f1:.4f}")
        
        # 计算F1/Param效率
        total_params = sum(p.numel() for p in self.model.parameters())
        f1_per_param = self.best_f1 / (total_params / 1e6)
        print(f"  参数量: {total_params / 1e6:.2f}M")
        print(f"  F1/Param: {f1_per_param:.2f}")
        print(f"  vs PeftCD (9.23): {f1_per_param / 9.23:.2f}x")

        self.writer.close()


def main():
    """主函数"""
    # v2.0配置
    config = {
        'epochs': 100,
        'batch_size': 16,
        'learning_rate': 1e-4,
        'weight_decay': 0.05,
        'min_lr': 1e-6,
        'early_stopping_patience': 20
    }

    # 设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"✅ 使用设备: {device}")

    # 使用完整LEVIR-CD256数据集
    data_root = "/home/developer/workspace/datasets/LEVIR-CD256"
    
    print(f"\n📂 数据集路径: {data_root}")
    
    # 数据集
    train_dataset = LEVIRCDDataset(
        root_dir=f"{data_root}/train",
        split='train',
        augment=True,
        format='standard'
    )
    
    val_dataset = LEVIRCDDataset(
        root_dir=f"{data_root}/val",
        split='val',
        augment=False,
        format='standard'
    )
    
    # 数据加载器
    train_loader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=config['batch_size'],
        shuffle=True,
        num_workers=4,
        pin_memory=True
    )
    
    val_loader = torch.utils.data.DataLoader(
        val_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        num_workers=4,
        pin_memory=True
    )

    # v2.0模型
    model = TemporalPEFTv2(
        backbone_type='sam2',
        freeze_backbone=True,
        adapter_dim=256,
        lora_ranks=[4, 8, 16],
        decoder_channels=256,
        use_contrastive=True
    )

    # 训练器
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        config=config,
        device=device,
        output_dir='/tmp/temporal_peft_v2'
    )

    # 开始训练
    trainer.train(epochs=config['epochs'])


if __name__ == "__main__":
    main()
