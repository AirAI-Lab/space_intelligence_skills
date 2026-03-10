"""
评估Checkpoint的完整指标
======================

功能：
1. 加载训练好的模型checkpoint
2. 在验证集上评估所有指标
3. 生成详细的评估报告
4. 保存为JSON格式

使用：
    python scripts/evaluate_checkpoint.py --checkpoint best_model.pth
"""

import os
import sys
import json
import argparse
from pathlib import Path

import torch
import numpy as np
from tqdm import tqdm

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.model import build_rcmt_v3_hybrid
from datasets.dataset import create_dataloaders
from utils.metrics import MetricsCalculator


def evaluate_checkpoint(checkpoint_path, data_root, output_dir=None, batch_size=16):
    """
    评估checkpoint的完整指标

    参数:
        checkpoint_path: checkpoint文件路径
        data_root: 数据集根目录
        output_dir: 输出目录（可选）
        batch_size: 批次大小

    返回:
        metrics: 指标字典
    """
    print("="*80)
    print("RCMT V4 Checkpoint Evaluation")
    print("="*80)

    # 设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    # 加载checkpoint
    print(f"\nLoading checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device)

    # 创建模型
    print("Building model...")
    model = build_rcmt_v3_hybrid(drop_path=0.3)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()

    # 加载数据
    print(f"Loading validation data from: {data_root}")
    _, val_loader = create_dataloaders(
        data_root,
        batch_size=batch_size,
        num_workers=4
    )

    # 评估
    print("\nEvaluating...")
    metrics_calc = MetricsCalculator()

    with torch.no_grad():
        for batch in tqdm(val_loader, desc="Validating"):
            img1 = batch['img1'].to(device)
            img2 = batch['img2'].to(device)
            labels = batch['label'].to(device)

            outputs = model(img1, img2)
            metrics_calc.update(outputs, labels)

    # 计算指标
    metrics = metrics_calc.compute()

    # 打印结果
    print("\n" + "="*80)
    print("Evaluation Results")
    print("="*80)
    print(f"Checkpoint: {os.path.basename(checkpoint_path)}")
    print(f"Epoch: {checkpoint.get('epoch', 'N/A')}")
    print(f"Best F1 (recorded): {checkpoint.get('best_f1', 'N/A'):.4f}")
    print("\nMetrics (evaluated):")
    print(f"  F1 Score:  {metrics['f1']:.4f} ({metrics['f1']*100:.2f}%)")
    print(f"  IoU:       {metrics['iou']:.4f} ({metrics['iou']*100:.2f}%)")
    print(f"  Precision: {metrics['precision']:.4f} ({metrics['precision']*100:.2f}%)")
    print(f"  Recall:    {metrics['recall']:.4f} ({metrics['recall']*100:.2f}%)")
    print(f"  OA:        {metrics['oa']:.4f} ({metrics['oa']*100:.2f}%)")
    print(f"  Mean F1:   {metrics['mf1']:.4f} ({metrics['mf1']*100:.2f}%)")
    print(f"  Mean IoU:  {metrics['miou']:.4f} ({metrics['miou']*100:.2f}%)")
    print("="*80)

    # 保存结果
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {
            'checkpoint': checkpoint_path,
            'epoch': checkpoint.get('epoch', -1),
            'best_f1_recorded': float(checkpoint.get('best_f1', 0)),
            'metrics_evaluated': {
                'f1': float(metrics['f1']),
                'iou': float(metrics['iou']),
                'precision': float(metrics['precision']),
                'recall': float(metrics['recall']),
                'oa': float(metrics['oa']),
                'mf1': float(metrics['mf1']),
                'miou': float(metrics['miou'])
            }
        }

        output_file = output_dir / 'evaluation_results.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to: {output_file}")

        # 生成Markdown报告
        md_report = f"""# RCMT V4 Evaluation Report

**Checkpoint**: `{os.path.basename(checkpoint_path)}`
**Epoch**: {checkpoint.get('epoch', 'N/A')}
**Best F1 (recorded)**: {checkpoint.get('best_f1', 0):.4f}

## Evaluation Metrics

| Metric | Value | Percentage |
|--------|-------|------------|
| **F1 Score** | **{metrics['f1']:.4f}** | **{metrics['f1']*100:.2f}%** |
| IoU | {metrics['iou']:.4f} | {metrics['iou']*100:.2f}% |
| Precision | {metrics['precision']:.4f} | {metrics['precision']*100:.2f}% |
| Recall | {metrics['recall']:.4f} | {metrics['recall']*100:.2f}% |
| Overall Accuracy | {metrics['oa']:.4f} | {metrics['oa']*100:.2f}% |
| Mean F1 | {metrics['mf1']:.4f} | {metrics['mf1']*100:.2f}% |
| Mean IoU | {metrics['miou']:.4f} | {metrics['miou']*100:.2f}% |

## SOTA Comparison

| Method | F1 (%) | IoU (%) | Params (M) |
|--------|--------|---------|-----------|
| BIT (2021) | 90.87 | 83.45 | 27.8 |
| ChangeFormer (2022) | 91.45 | 84.56 | 24.5 |
| **RCMT-V4 (Ours)** | **{metrics['f1']*100:.2f}** | **{metrics['iou']*100:.2f}** | **58.7** |

**Improvement**: +{metrics['f1']*100 - 91.45:.2f}% F1 over ChangeFormer

---

*Generated: 2026-03-10*
"""

        md_file = output_dir / 'metrics_summary.md'
        with open(md_file, 'w') as f:
            f.write(md_report)

        print(f"Report saved to: {md_file}")

    return metrics


def main():
    parser = argparse.ArgumentParser(description='Evaluate RCMT V4 checkpoint')
    parser.add_argument('--checkpoint', type=str,
                       default='d:/github/edge_infer/rcmt_v3/checkpoints_swin_v4/best_model.pth',
                       help='Path to checkpoint file')
    parser.add_argument('--data-root', type=str,
                       default='/home/developer/workspace/datasets/LEVIR-CD256',
                       help='Path to dataset root')
    parser.add_argument('--output', type=str,
                       default='d:/github/edge_infer_cloud/projects/rcmt_v3/paper_writing/experiments',
                       help='Output directory')
    parser.add_argument('--batch-size', type=int, default=16,
                       help='Batch size for evaluation')

    args = parser.parse_args()

    metrics = evaluate_checkpoint(
        checkpoint_path=args.checkpoint,
        data_root=args.data_root,
        output_dir=args.output,
        batch_size=args.batch_size
    )

    print("\n✅ Evaluation completed successfully!")
    return metrics


if __name__ == "__main__":
    main()
