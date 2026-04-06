#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SAM3 对比评估 - 本地运行版

在本地Windows环境运行的评估脚本
评估RADIO only和RADIO + SAM3两种配置

作者: 空中智能体团队
日期: 2026-04-06
"""

import os
import sys
import json
import numpy as np
import cv2
from pathlib import Path
from datetime import datetime

def main():
    print("="*80)
    print("SAM3 对比评估 - 本地运行版")
    print("="*80)
    
    # 设置路径
    project_root = Path(__file__).parent.parent
    dataset_dir = project_root / 'data' / 'datasets'
    meta_dir = dataset_dir / 'meta'
    
    if not meta_dir.exists():
        print(f"❌ 数据集meta目录不存在: {meta_dir}")
        return
    
    # 加载样本
    samples = []
    for meta_file in sorted(meta_dir.glob('*.json'))[:20]:  # 只评估20个样本
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
            meta['image_path'] = str(dataset_dir / 'images' / meta['image'])
            meta['mask_dir'] = str(dataset_dir / 'masks')
            samples.append(meta)
    
    print(f"✅ 加载 {len(samples)} 个样本")
    
    # 检查模型文件
    checkpoint = project_root / 'models' / 'C-RADIOv4-H' / 'c-radio_v4-h_half.pth.tar'
    radio_code = project_root / 'models' / 'NVlabs_RADIO'
    siglip2 = project_root / 'models' / 'siglip2-giant-opt-patch16-384'
    
    print(f"\n检查模型文件...")
    print(f"  Checkpoint: {checkpoint.exists()}")
    print(f"  RADIO代码: {radio_code.exists()}")
    print(f"  SigLIP2: {siglip2.exists()}")
    
    if not checkpoint.exists():
        print(f"❌ Checkpoint不存在: {checkpoint}")
        return
    
    if not radio_code.exists():
        print(f"❌ RADIO代码不存在: {radio_code}")
        return
    
    if not siglip2.exists():
        print(f"❌ SigLIP2模型不存在: {siglip2}")
        return
    
    print("✅ 所有模型文件就绪")
    
    # 尝试加载模型
    try:
        sys.path.insert(0, str(project_root))
        from models.open_vocab.inference import OpenVocabSegmentor
        
        print("\n加载模型 (RADIO only)...")
        segmentor_radio = OpenVocabSegmentor(
            checkpoint_path=str(checkpoint),
            radio_code_dir=str(radio_code),
            siglip2_dir=str(siglip2),
            adaptor_names=['siglip2-g'],
            device='cuda',
            input_size=896,
        )
        print("✅ RADIO only 模型加载完成")
        
        print("\n加载模型 (RADIO + SAM3)...")
        segmentor_sam3 = OpenVocabSegmentor(
            checkpoint_path=str(checkpoint),
            radio_code_dir=str(radio_code),
            siglip2_dir=str(siglip2),
            adaptor_names=['siglip2-g', 'sam'],
            device='cuda',
            input_size=896,
        )
        print("✅ RADIO + SAM3 模型加载完成")
        
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 评估配置
    classes_config = {
        "water": {
            "prompts": [
                "water surface in natural river",
                "water body in lake or reservoir",
                "flowing water in channel",
            ]
        }
    }
    
    # 评估函数
    def evaluate_segmentor(segmentor, samples, name):
        print(f"\n评估配置: {name}")
        print("-" * 60)
        
        ious = []
        precisions = []
        recalls = []
        
        for i, sample in enumerate(samples):
            image_path = sample['image_path']
            if not os.path.exists(image_path):
                continue
            
            image = cv2.imread(image_path)
            if image is None:
                continue
            
            # 获取GT mask
            gt_mask = None
            mask_dir = Path(sample['mask_dir'])
            for cls_info in sample.get('classes', []):
                mask_file = cls_info.get('mask_file')
                if mask_file:
                    mask_path = mask_dir / mask_file
                    if mask_path.exists():
                        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                        if mask is not None:
                            if gt_mask is None:
                                gt_mask = np.zeros(mask.shape, dtype=bool)
                            gt_mask = gt_mask | (mask > 127)
            
            if gt_mask is None or not gt_mask.any():
                continue
            
            # 执行分割
            try:
                result = segmentor.segment(image, threshold=0.1)
                
                # 获取预测mask
                if result:
                    # 合并所有预测的mask
                    pred_mask = None
                    for cls_name, seg_result in result.items():
                        if hasattr(seg_result, 'mask'):
                            mask = seg_result.mask
                        elif isinstance(seg_result, dict):
                            mask = seg_result.get('mask')
                        else:
                            continue
                        
                        if mask is not None:
                            if pred_mask is None:
                                pred_mask = np.zeros(mask.shape, dtype=bool)
                            pred_mask = pred_mask | mask
                
                if pred_mask is not None:
                    # 调整尺寸
                    if pred_mask.shape != gt_mask.shape:
                        pred_mask = cv2.resize(
                            pred_mask.astype(np.uint8),
                            (gt_mask.shape[1], gt_mask.shape[0]),
                            interpolation=cv2.INTER_NEAREST
                        ).astype(bool)
                    
                    # 计算指标
                    tp = np.logical_and(pred_mask, gt_mask).sum()
                    fp = np.logical_and(pred_mask, ~gt_mask).sum()
                    fn = np.logical_and(~pred_mask, gt_mask).sum()
                    
                    intersection = tp
                    union = tp + fp + fn
                    iou = intersection / (union + 1e-6)
                    precision = tp / (tp + fp + 1e-6)
                    recall = tp / (tp + fn + 1e-6)
                    
                    ious.append(iou)
                    precisions.append(precision)
                    recalls.append(recall)
                    
                    if i < 10:
                        status = "✓" if iou > 0.5 else "✗"
                        print(f"  {status} {sample['image']}: IoU={iou:.3f}, P={precision:.3f}, R={recall:.3f}")
            
            except Exception as e:
                if i < 5:
                    print(f"  ✗ {sample['image']}: {e}")
                continue
        
        if not ious:
            return None
        
        avg_iou = np.mean(ious)
        avg_precision = np.mean(precisions)
        avg_recall = np.mean(recalls)
        avg_f1 = 2 * avg_precision * avg_recall / (avg_precision + avg_recall + 1e-6)
        
        print(f"\n平均指标 ({len(ious)} 样本):")
        print(f"  IoU: {avg_iou:.3f}")
        print(f"  Precision: {avg_precision:.3f}")
        print(f"  Recall: {avg_recall:.3f}")
        print(f"  F1: {avg_f1:.3f}")
        
        return {
            'avg_iou': float(avg_iou),
            'avg_precision': float(avg_precision),
            'avg_recall': float(avg_recall),
            'avg_f1': float(avg_f1),
            'num_samples': len(ious),
        }
    
    # 评估两种配置
    radio_results = evaluate_segmentor(segmentor_radio, samples, "RADIO only")
    sam3_results = evaluate_segmentor(segmentor_sam3, samples, "RADIO + SAM3")
    
    # 保存对比结果
    if radio_results and sam3_results:
        iou_improvement = (sam3_results['avg_iou'] - radio_results['avg_iou']) / radio_results['avg_iou'] * 100
        precision_improvement = (sam3_results['avg_precision'] - radio_results['avg_precision']) / radio_results['avg_precision'] * 100
        f1_improvement = (sam3_results['avg_f1'] - radio_results['avg_f1']) / radio_results['avg_f1'] * 100
        
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'radio_only': radio_results,
            'radio_sam3': sam3_results,
            'improvement': {
                'iou_percent': float(iou_improvement),
                'precision_percent': float(precision_improvement),
                'f1_percent': float(f1_improvement),
            }
        }
        
        output_dir = project_root / 'outputs'
        output_dir.mkdir(exist_ok=True, parents=True)
        
        output_file = output_dir / 'sam3_comparison_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'=' * 80}")
        print("对比结果")
        print("=" * 80)
        print(f"\nRADIO only:")
        print(f"  IoU: {radio_results['avg_iou']:.3f}")
        print(f"  Precision: {radio_results['avg_precision']:.3f}")
        print(f"  Recall: {radio_results['avg_recall']:.3f}")
        print(f"  F1: {radio_results['avg_f1']:.3f}")
        print(f"\nRADIO + SAM3:")
        print(f"  IoU: {sam3_results['avg_iou']:.3f}")
        print(f"  Precision: {sam3_results['avg_precision']:.3f}")
        print(f"  Recall: {sam3_results['avg_recall']:.3f}")
        print(f"  F1: {sam3_results['avg_f1']:.3f}")
        print(f"\n性能提升:")
        print(f"  IoU: {iou_improvement:+.1f}%")
        print(f"  Precision: {precision_improvement:+.1f}%")
        print(f"  F1: {f1_improvement:+.1f}%")
        print(f"\n✅ 结果已保存: {output_file}")
    
    print("\n" + "="*80)
    print("评估完成!")
    print("="*80)

if __name__ == "__main__":
    main()
