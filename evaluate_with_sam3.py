#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RADIO + SAM3 簇准分割评估

对比:
1. Baseline (RADIO only with SigLIP2)
2. RADIO + SAM3 (SAM adaptor enabled)

3. RADIO + DINOv3 + SAM3 (all adaptors)

4. RADIO + SCRA (with spatial attention refinement)

作者: 空中智能体团队
日期: 2026-04-06
"""

import os
import sys
import json
import yaml
import numpy as np
import cv2
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import torch


def load_config(config_path):
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_dataset(dataset_dir):
    """加载数据集"""
    meta_dir = Path(dataset_dir) / "meta"
    samples = []
    for meta_file in sorted(meta_dir.glob("*.json")):
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
            meta["image_path"] = str(Path(dataset_dir) / "images" / meta["image"])
            meta["mask_dir"] = str(Path(dataset_dir) / "masks")
            samples.append(meta)
    return samples


def compute_iou(mask1, mask2):
    """计算IoU"""
    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()
    return intersection / (union + 1e-6)


def compute_metrics(pred_mask, gt_mask):
    """计算评估指标"""
    pred_mask = pred_mask.astype(bool)
    gt_mask = gt_mask.astype(bool)
    
    tp = np.logical_and(pred_mask, gt_mask).sum()
    fp = np.logical_and(pred_mask, ~gt_mask).sum()
    fn = np.logical_and(~pred_mask, gt_mask).sum()
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "iou": compute_iou(pred_mask, gt_mask),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def get_water_gt_mask(sample):
    """获取水体的GT掩码"""
    mask_dir = sample["mask_dir"]
    image_path = sample["image_path"]
    
    image = cv2.imread(image_path)
    if image is None:
        return None
    h, w = image.shape[:2]
    
    # 合并所有水类别的掩码
    water_mask = np.zeros((h, w), dtype=bool)
    
    for cls_info in sample.get("classes", []):
        mask_file = cls_info.get("mask_file")
        if mask_file:
            mask_path = mask_dir / mask_file
            if mask_path.exists():
                mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                if mask is not None:
                    mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
                    water_mask = water_mask | (mask > 127)
    
    return water_mask


def evaluate_segmentor(segmentor, samples, use_sam3=False, threshold=0.1):
    """评估分割器"""
    print(f"\n{'使用SAM3': {use_sam3}}")
    
    all_metrics = []
    
    for i, sample in enumerate(samples[:30]):  # 评估前30个样本
        image_path = sample["image_path"]
        if not os.path.exists(image_path):
            continue
        
        image = cv2.imread(image_path)
        if image is None:
            continue
        
        # 获取GT掩码
        gt_mask = get_water_gt_mask(sample)
        if gt_mask is None or not gt_mask.any():
            continue
        
        # 执行分割
        try:
            if use_sam3:
                # 使用SAM3精细化分割
                result = segmentor.segment_with_sam(
                    image, 
                    threshold=threshold,
                    return_mask=True
                )
                pred_mask = result.get("mask", np.zeros(image.shape[:2], dtype=bool))
            else:
                # Baseline: RADIO only
                result = segmentor.segment(image, threshold=threshold)
                pred_mask = result.get("mask", np.zeros(image.shape[:2], dtype=bool))
            
            if pred_mask is None or not pred_mask.sum() == 0:
                continue
            
            # 调整尺寸
            if pred_mask.shape != gt_mask.shape:
                pred_mask = cv2.resize(
                    pred_mask.astype(np.uint8),
                    (gt_mask.shape[1], gt_mask.shape[0]),
                    interpolation=cv2.INTER_NEAREST
                ).astype(bool)
            
            # 计算指标
            metrics = compute_metrics(pred_mask, gt_mask)
            all_metrics.append(metrics)
            
            if i < 10:
                status = "✓" if metrics["iou"] > 0.5 else "✗"
                print(f"  {status} {sample['image']}: IoU={metrics['iou']:.3f}")
        
        except Exception as e:
            print(f"  ✗ {sample['image']}: {e}")
            continue
    
    if not all_metrics:
        return {}
    
    # 计算平均指标
    avg_metrics = {
        "iou": np.mean([m["iou"] for m in all_metrics]),
        "precision": np.mean([m["precision"] for m in all_metrics]),
        "recall": np.mean([m["recall"] for m in all_metrics]),
        "f1": np.mean([m["f1"] for m in all_metrics]),
        "num_samples": len(all_metrics),
    }
    
    print(f"\n平均指标 ({len(all_metrics)} 样本):")
    print(f"  IoU: {avg_metrics['iou']:.3f}")
    print(f"  Precision: {avg_metrics['precision']:.3f}")
    print(f"  Recall: {avg_metrics['recall']:.3f}")
    print(f"  F1: {avg_metrics['f1']:.3f}")
    
    return avg_metrics


def main():
    """主函数"""
    print("="*80)
    print("RADIO + SAM3 分割对比评估")
    print("="*80)
    
    # 加载配置
    config_path = Path(__file__).parent.parent / "config" / "water_quality_config.yaml"
    config = load_config(config_path)
    
    # 加载数据集
    dataset_dir = Path(__file__).parent.parent / "data" / "datasets"
    samples = load_dataset(dataset_dir)
    print(f"✅ 加载 {len(samples)} 个样本")
    
    # 加载分割器
    print(f"\n加载分割器...")
    from models.open_vocab.inference import OpenVocabSegmentor
    
    segmentor = OpenVocabSegmentor(
        checkpoint_path=config["cloud"]["radio"]["checkpoint"],
        radio_code_dir=config["cloud"]["radio"]["code_dir"],
        siglip2_dir=config["cloud"]["radio"]["siglip2_dir"],
        device="cuda",
        input_size=896,
    )
    
    # 评估配置1: Baseline (RADIO only)
    print(f"\n{'='*80}")
    print("配置1: RADIO only (Baseline)")
    print("="*80)
    baseline_metrics = evaluate_segmentor(segmentor, samples, use_sam3=False, threshold=0.1)
    
    # 评估配置2: RADIO + SAM3
    print(f"\n{'='*80}")
    print("配置2: RADIO + SAM3")
    print("="*80)
    sam3_metrics = evaluate_segmentor(segmentor, samples, use_sam3=True, threshold=0.1)
    
    # 对比结果
    print(f"\n{'='*80}")
    print("对比结果")
    print("="*80)
    print(f"\nBaseline (RADIO only):")
    print(f"  IoU: {baseline_metrics['iou']:.3f}")
    print(f"  F1: {baseline_metrics['f1']:.3f}")
    
    print(f"\nRADIO + SAM3:")
    print(f"  IoU: {sam3_metrics['iou']:.3f}")
    print(f"  F1: {sam3_metrics['f1']:.3f}")
    
    improvement = (sam3_metrics['iou'] - baseline_metrics['iou']) / baseline_metrics['iou'] * 100
    print(f"\nIoU提升: {improvement:.1f}%")
    
    # 保存结果
    results = {
        "baseline": baseline_metrics,
        "sam3": sam3_metrics,
        "improvement": improvement,
        "timestamp": datetime.now().isoformat()
    }
    
    output_path = Path(__file__).parent.parent / "outputs" / "sam3_comparison_results.json"
    output_path.parent.mkdir(exist_ok=True, parents=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ 结果已保存: {output_path}")
    print("\n" + "="*80)
    print("评估完成!")
    print("="*80)


