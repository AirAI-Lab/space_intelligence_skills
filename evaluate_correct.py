#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
正确的评估脚本 - 读取meta信息并正确计算IoU

修复问题:
1. 读取meta/*.json获取真实类别
2. 正确加载对应的GT mask
3. 正确计算IoU（按类别）
4. 统计分类准确率

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import sys
import json
import torch
import numpy as np
import cv2
from pathlib import Path
import logging

sys.path.insert(0, '/app/water_inspection')

from models.open_vocab.core.segmentor import WaterQualitySegmentor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def evaluate_with_gt():
    """使用GT信息进行正确评估"""
    
    # 配置路径
    data_dir = Path('/app/water_inspection/data/datasets/images')
    gt_dir = Path('/app/water_inspection/data/datasets/masks')
    meta_dir = Path('/app/water_inspection/data/datasets/meta')
    output_dir = Path('/app/water_inspection/data/evaluation_results')
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # 1. 加载模型
    logger.info("="*80)
    logger.info("加载重构后的水质检测模型")
    logger.info("="*80)
    
    segmentor = WaterQualitySegmentor(
        checkpoint_path='/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar',
        radio_code_dir='/app/models/NVlabs_RADIO',
        siglip2_dir='/app/models/siglip2-giant-opt-patch16-384',
        device='cuda',
        input_size=896,
        mode='single_stage'
    )
    
    logger.info("✅ 模型加载成功\n")
    
    # 2. 获取所有图片
    image_files = sorted(list(data_dir.glob('*.jpg')) + list(data_dir.glob('*.jpeg')) + list(data_dir.glob('*.png')))
    logger.info(f"找到 {len(image_files)} 张图片")
    
    # 3. 评估
    results = []
    class_correct = {}  # 每个类别的正确数
    class_total = {}    # 每个类别的总数
    class_iou = {}       # 每个类别的IoU累计
    
    for idx, img_path in enumerate(image_files[:20]):  # 先评估20张
        logger.info(f"\n[{idx+1}/{len(image_files[:20])}] 处理: {img_path.name}")
        
        try:
            # 读取meta信息
            meta_path = meta_dir / f"{img_path.stem}.json"
            if not meta_path.exists():
                logger.warning(f"  ⚠️ 没有找到meta: {meta_path}")
                continue
            
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            gt_classes = {c['class'] for c in meta.get('classes', [])}
            active_class = meta.get('active_class', list(gt_classes)[0] if gt_classes else None)
            
            if not active_class:
                logger.warning(f"  ⚠️ 没有GT类别")
                continue
            
            # 读取图像
            image = cv2.imread(str(img_path))
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 推理
            pred_results = segmentor.segment(image)
            
            if not pred_results:
                logger.warning(f"  ⚠️ 无预测结果")
                continue
            
            # 获取主要预测结果
            main_pred = max(pred_results.values(), key=lambda r: r.area_ratio)
            pred_class = main_pred.class_name
            
            # 读取GT mask
            gt_mask_file = f"{img_path.stem}__{active_class}.png"
            gt_mask_path = gt_dir / gt_mask_file
            
            if not gt_mask_path.exists():
                logger.warning(f"  ⚠️ GT mask不存在: {gt_mask_path}")
                continue
            
            gt_mask = cv2.imread(str(gt_mask_path), cv2.IMREAD_GRAYSCALE)
            gt_mask_bool = gt_mask > 0
            
            # 计算IoU
            if main_pred.mask is not None:
                pred_mask_bool = main_pred.mask
                intersection = np.logical_and(pred_mask_bool, gt_mask_bool).sum()
                union = np.logical_or(pred_mask_bool, gt_mask_bool).sum()
                iou = intersection / (union + 1e-6)
            else:
                iou = 0.0
            
            # 分类是否正确
            is_correct = (pred_class == active_class)
            
            # 统计
            results.append({
                'image': img_path.name,
                'gt_class': active_class,
                'pred_class': pred_class,
                'correct': is_correct,
                'iou': iou,
                'score': main_pred.score
            })
            
            # 按类别统计
            if active_class not in class_total:
                class_total[active_class] = 0
                class_correct[active_class] = 0
                class_iou[active_class] = []
            
            class_total[active_class] += 1
            if is_correct:
                class_correct[active_class] += 1
            class_iou[active_class].append(iou)
            
            status = "✅" if is_correct else "❌"
            logger.info(f"  {status} GT: {active_class} | 预测: {pred_class} | IoU: {iou:.3f} | Score: {main_pred.score:.3f}")
            
        except Exception as e:
            logger.error(f"  ❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 4. 汇总统计
    logger.info("\n" + "="*80)
    logger.info("评估统计")
    logger.info("="*80)
    
    if results:
        total = len(results)
        correct = sum(1 for r in results if r['correct'])
        overall_acc = correct / total
        avg_iou = np.mean([r['iou'] for r in results])
        
        logger.info(f"\n📊 整体性能:")
        logger.info(f"  总样本数: {total}")
        logger.info(f"  分类正确: {correct} ({overall_acc:.1%})")
        logger.info(f"  平均IoU: {avg_iou:.3f}")
        
        logger.info(f"\n📊 各类别性能:")
        for cls_name in sorted(class_total.keys()):
            total_cls = class_total[cls_name]
            correct_cls = class_correct.get(cls_name, 0)
            acc_cls = correct_cls / total_cls if total_cls > 0 else 0
            avg_iou_cls = np.mean(class_iou[cls_name]) if class_iou[cls_name] else 0
            
            logger.info(f"  {cls_name}: {correct_cls}/{total_cls} ({acc_cls:.1%}) | IoU: {avg_iou_cls:.3f}")
        
        # 保存结果
        report = {
            'total_samples': total,
            'correct_predictions': correct,
            'overall_accuracy': float(overall_acc),
            'average_iou': float(avg_iou),
            'class_stats': {
                cls: {
                    'total': class_total[cls],
                    'correct': class_correct.get(cls, 0),
                    'accuracy': float(class_correct.get(cls, 0) / class_total[cls]),
                    'avg_iou': float(np.mean(class_iou[cls]))
                }
                for cls in class_total.keys()
            },
            'results': results
        }
        
        report_path = output_dir / 'correct_evaluation_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✅ 评估报告已保存: {report_path}")
    else:
        logger.warning("⚠️ 没有有效的评估结果")


if __name__ == '__main__':
    evaluate_with_gt()
