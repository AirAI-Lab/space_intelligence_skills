"""
Temporal PEFT v2.1 - 支持续训的200 epoch版本

关键改进：
1. ✅ 支持从checkpoint续训
2. ✅ 200 epochs（对齐SOTA文献）
3. ✅ 每10 epochs保存checkpoint
4. ✅ 完整状态保存（model + optimizer + scheduler）

基于v2.0架构：
- MultiScaleTemporalDecoder (1.75M)
- AdvancedCombinedLoss (边界加权+OHEM)
- 完整LEVIR-CD256数据集 (7,134 train)

目标: F1 90-92% (vs PeftCD 92.3%)
时间: 16-20小时（可续训）

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
import argparse

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入v2.0模型
from train_v2 import TemporalPEFTv2, AdvancedCombinedLoss, calculate_metrics

# 使用标准LEVIR-CD数据集
sys.path.insert(0, '/workspace/rcmt_v3')
from data.levir_cd import LEVIRCDDataset


class EarlyStopping:
    """Early Stopping with checkpoint support"""
    def __init__(self, patience=30, min_delta=0.001, mode='max'):
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


class TrainerV21:
    """Temporal PEFT v2.1 - 支持续训"""
    
    def __init__(
        self,
        model,
        train_loader,
        val_loader,
        config: dict,
        device: torch.device,
        output_dir: str = '/tmp/temporal_peft_v2_200ep'
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.config = config
        self.device = device
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 损失函数
        self.criterion = AdvancedCombinedLoss(
            boundary_weight=2.0,
            ohem_ratio=0.3,
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
            T_max=config.get('epochs', 200),
            eta_min=config.get('min_lr', 1e-6)
        )

        # Early Stopping（增加到30）
        self.early_stopping = EarlyStopping(
            patience=config.get('early_stopping_patience', 30),
            min_delta=0.001,
            mode='max'
        )

        # TensorBoard
        self.writer = SummaryWriter(self.output_dir / 'logs')

        # 训练状态
        self.start_epoch = 1
        self.best_f1 = 0.0
        self.best_epoch = 0
        self.global_step = 0

        # 打印模型信息
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        print(f"\n{'='*80}")
        print(f"{'Temporal PEFT v2.1 - 支持续训的200 epoch版本':^80}")
        print(f"{'='*80}")
        print(f"\n✅ 训练器初始化完成")
        print(f"   输出目录: {self.output_dir}")
        print(f"   设备: {device}")
        print(f"   训练样本: {len(train_loader.dataset)}")
        print(f"   验证样本: {len(val_loader.dataset)}")
        print(f"   总Epochs: {config.get('epochs', 200)}")
        print(f"   Early Stopping: patience={config.get('early_stopping_patience', 30)}")
        print(f"\n📊 模型参数:")
        print(f"   总参数: {total_params / 1e6:.2f}M")
        print(f"   可训练参数: {trainable_params / 1e6:.2f}M")
        print(f"\n🎯 v2.1改进:")
        print(f"   ✅ 支持从checkpoint续训")
        print(f"   ✅ 200 epochs（对齐SOTA文献）")
        print(f"   ✅ 每10 epochs保存checkpoint")
        print(f"\n{'='*80}\n")

    def save_checkpoint(self, epoch: int, is_best: bool = False):
        """保存checkpoint（支持续训）"""
        checkpoint = {
            'epoch': epoch,
            'global_step': self.global_step,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'best_f1': self.best_f1,
            'best_epoch': self.best_epoch,
            'config': self.config
        }
        
        # 保存最新checkpoint
        latest_path = self.output_dir / 'checkpoint_latest.pth'
        torch.save(checkpoint, latest_path)
        
        # 每10 epochs保存一次
        if epoch % 10 == 0:
            epoch_path = self.output_dir / f'checkpoint_epoch_{epoch}.pth'
            torch.save(checkpoint, epoch_path)
            print(f"   ✅ Checkpoint saved: epoch_{epoch}.pth")
        
        # 保存最佳模型
        if is_best:
            best_path = self.output_dir / 'best_model.pth'
            torch.save(checkpoint, best_path)
            print(f"   🏆 Best model saved: F1={self.best_f1:.4f}")

    def load_checkpoint(self, checkpoint_path: str) -> int:
        """加载checkpoint（续训）"""
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.best_f1 = checkpoint['best_f1']
        self.best_epoch = checkpoint['best_epoch']
        self.global_step = checkpoint.get('global_step', 0)
        self.start_epoch = checkpoint['epoch'] + 1
        
        print(f"\n✅ Checkpoint loaded from: {checkpoint_path}")
        print(f"   Resume from epoch: {self.start_epoch}")
        print(f"   Best F1 so far: {self.best_f1:.4f} (Epoch {self.best_epoch})")
        
        return self.start_epoch

    def train_epoch(self, epoch: int) -> dict:
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

            self.global_step += 1

        # 平均指标
        avg_loss = total_loss / n_batches
        for key in all_metrics:
            all_metrics[key] /= n_batches

        return {'loss': avg_loss, **all_metrics}

    def validate(self, epoch: int) -> dict:
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

    def train(self, epochs: int):
        """完整训练流程（支持续训）"""
        for epoch in range(self.start_epoch, epochs + 1):
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
                print(f"\n✅ 新Best F1: {self.best_f1:.4f}")
                
                # 检查是否达到目标
                if self.best_f1 >= 0.90:
                    print(f"\n🎉 已达到目标F1 (≥90%)！")
                if self.best_f1 >= 0.923:
                    print(f"🏆 超越PeftCD (92.3%)！")

            # 保存checkpoint
            self.save_checkpoint(epoch, is_best)

            # Early Stopping检查
            if self.early_stopping(val_metrics['f1']):
                print(f"\n⚠️ Early Stopping triggered at Epoch {epoch}")
                print(f"   验证F1已连续{self.early_stopping.patience}个epoch未提升")
                print(f"   最佳F1: {self.best_f1:.4f} (Epoch {self.best_epoch})")
                break

        # 训练完成
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
    parser = argparse.ArgumentParser(description='Temporal PEFT v2.1 Training')
    parser.add_argument('--resume', type=str, default=None, 
                       help='Resume from checkpoint path')
    parser.add_argument('--epochs', type=int, default=200,
                       help='Total epochs (default: 200)')
    args = parser.parse_args()

    # v2.1配置（200 epochs）
    config = {
        'epochs': args.epochs,
        'batch_size': 16,
        'learning_rate': 1e-4,
        'weight_decay': 0.05,
        'min_lr': 1e-6,
        'early_stopping_patience': 30
    }

    # 设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"✅ 使用设备: {device}")

    # 数据集
    data_root = "/home/developer/workspace/datasets/LEVIR-CD256"
    
    print(f"\n📂 数据集路径: {data_root}")
    
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
        use_contrastive=True
    )

    # 训练器
    trainer = TrainerV21(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        config=config,
        device=device,
        output_dir='/tmp/temporal_peft_v2_200ep'
    )

    # 加载checkpoint（续训）
    if args.resume:
        trainer.load_checkpoint(args.resume)

    # 开始训练
    trainer.train(epochs=config['epochs'])


if __name__ == "__main__":
    main()
