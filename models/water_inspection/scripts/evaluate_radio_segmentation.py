#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
评估RADIO的纯分割能力（不分类，只看能否提取水体）

目标:
1. 测试RADIO能否准确分割出水区域
2. 与GT mask计算IoU
3. 不考虑水质分类，只看分割质量
"""

import sys
from pathlib import Path
import json
import numpy as np
import cv2
import logging

sys.path.insert(0, '/app/water_inspection')

from models.open_vocab.core.segmentor import WaterQualitySegmentor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def evaluate_radio_segmentation():
    """评估RADIO的水体分割能力"""
    
    # 配置路径
    data_dir = Path('/app/water_inspection/data/datasets/images')
    gt_dir = Path('/app/water_inspection/data/datasets/masks')
    meta_dir = Path('/app/water_inspection/data/datasets/meta')
    output_dir = Path('/app/water_inspection/data/evaluation_results')
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # 1. 加载模型
    logger.info("="*80)
    logger.info("加载模型 - 评估RADIO分割能力")
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
    
    # 2. 获取图片列表
    image_files = sorted(list(data_dir.glob('*.jpg')) + list(data_dir.glob('*.jpeg')) + list(data_dir.glob('*.png')))
    logger.info(f"找到 {len(image_files)} 张图片")
    
    # 3. 评估RADIO分割能力
    logger.info("\n" + "="*80)
    logger.info("评估RADIO水体分割能力（不分类）")
    logger.info("="*80)
    
    results = []
    
    for idx, img_path in enumerate(image_files[:30]):  # 评估30张
        logger.info(f"\n[{idx+1}/{len(image_files[:30])}] 处理: {img_path.name}")
        
        try:
            # 读取meta获取GT
            meta_path = meta_dir / f"{img_path.stem}.json"
            if not meta_path.exists():
                continue
            
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            gt_classes = [c['class'] for c in meta.get('classes', [])]
            if not gt_classes:
                continue
            
            # 读取GT masks (所有水体的并集)
            gt_mask_union = None
            for gt_class in gt_classes:
                gt_mask_file = f"{img_path.stem}__{gt_class}.png"
                gt_mask_path = gt_dir / gt_mask_file
                if gt_mask_path.exists():
                    gt_mask = cv2.imread(str(gt_mask_path), cv2.IMREAD_GRAYSCALE)
                    gt_mask_bool = gt_mask > 0
                    if gt_mask_union is None:
                        gt_mask_union = gt_mask_bool
                    else:
                        gt_mask_union = np.logical_or(gt_mask_union, gt_mask_bool)
            
            if gt_mask_union is None:
                continue
            
            # 读取图像
            image = cv2.imread(str(img_path))
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 推理 - 获取所有分割结果的并集
            pred_results = segmentor.segment(image)
            
            if not pred_results:
                logger.warning(f"  ⚠️ 无分割结果")
                continue
            
            # 合并所有预测mask
            pred_mask_union = None
            for cls_name, result in pred_results.items():
                if result.mask is not None:
                    if pred_mask_union is None:
                        pred_mask_union = result.mask
                    else:
                        pred_mask_union = np.logical_or(pred_mask_union, result.mask)
            
            if pred_mask_union is None:
                logger.warning(f"  ⚠️ 预测mask为空")
                continue
            
            # 计算IoU (水体分割质量)
            intersection = np.logical_and(pred_mask_union, gt_mask_union).sum()
            union = np.logical_or(pred_mask_union, gt_mask_union).sum()
            iou = intersection / (union + 1e-6)
            
            # 计算精确率和召回率
            precision = intersection / (pred_mask_union.sum() + 1e-6)
            recall = intersection / (gt_mask_union.sum() + 1e-6)
            f1 = 2 * precision * recall / (precision + recall + 1e-6)
            
            results.append({
                'image': img_path.name,
                'gt_classes': gt_classes,
                'iou': float(iou),
                'precision': float(precision),
                'recall': float(recall),
                'f1': float(f1),
                'pred_area': float(pred_mask_union.sum() / pred_mask_union.size),
                'gt_area': float(gt_mask_union.sum() / gt_mask_union.size)
            })
            
            logger.info(f"  ✅ IoU: {iou:.3f} | P: {precision:.3f} | R: {recall:.3f} | F1: {f1:.3f}")
            logger.info(f"     预测面积: {pred_mask_union.sum()/pred_mask_union.size:.1%} | GT面积: {gt_mask_union.sum()/gt_mask_union.size:.1%}")
            
        except Exception as e:
            logger.error(f"  ❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 4. 汇总统计
    logger.info("\n" + "="*80)
    logger.info("RADIO分割能力评估统计")
    logger.info("="*80)
    
    if results:
        avg_iou = np.mean([r['iou'] for r in results])
        avg_precision = np.mean([r['precision'] for r in results])
        avg_recall = np.mean([r['recall'] for r in results])
        avg_f1 = np.mean([r['f1'] for r in results])
        
        # 分析面积偏差
        avg_pred_area = np.mean([r['pred_area'] for r in results])
        avg_gt_area = np.mean([r['gt_area'] for r in results])
        area_bias = avg_pred_area - avg_gt_area
        
        logger.info(f"\n📊 整体分割性能:")
        logger.info(f"  平均IoU: {avg_iou:.3f} ({avg_iou:.1%})")
        logger.info(f"  平均精确率: {avg_precision:.3f} ({avg_precision:.1%})")
        logger.info(f"  平均召回率: {avg_recall:.3f} ({avg_recall:.1%})")
        logger.info(f"  平均F1: {avg_f1:.3f} ({avg_f1:.1%})")
        logger.info(f"\n📊 面积分析:")
        logger.info(f"  平均预测面积: {avg_pred_area:.1%}")
        logger.info(f"  平均GT面积: {avg_gt_area:.1%}")
        logger.info(f"  面积偏差: {area_bias:+.1%} ({'过分割' if area_bias > 0 else '欠分割'})")
        
        # IoU分布
        ious = [r['iou'] for r in results]
        logger.info(f"\n📊 IoU分布:")
        logger.info(f"  最佳: {max(ious):.3f}")
        logger.info(f"  最差: {min(ious):.3f}")
        logger.info(f"  中位数: {np.median(ious):.3f}")
        logger.info(f"  >0.5: {sum(1 for i in ious if i > 0.5)}/{len(ious)}")
        logger.info(f"  >0.3: {sum(1 for i in ious if i > 0.3)}/{len(ious)}")
        
        # 保存结果
        report = {
            'summary': {
                'total_samples': len(results),
                'avg_iou': float(avg_iou),
                'avg_precision': float(avg_precision),
                'avg_recall': float(avg_recall),
                'avg_f1': float(avg_f1),
                'avg_pred_area': float(avg_pred_area),
                'avg_gt_area': float(avg_gt_area),
                'area_bias': float(area_bias)
            },
            'results': results
        }
        
        report_path = output_dir / 'radio_segmentation_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✅ RADIO分割评估报告已保存: {report_path}")
        
        # 结论
        logger.info(f"\n🎯 结论:")
        if avg_iou > 0.5:
            logger.info(f"  ✅ RADIO分割能力优秀 (IoU>{avg_iou:.1%})")
        elif avg_iou > 0.3:
            logger.info(f"  ⚠️ RADIO分割能力中等 (IoU={avg_iou:.1%})")
        else:
            logger.info(f"  ❌ RADIO分割能力较差 (IoU<{avg_iou:.1%})")
        
        if abs(area_bias) < 0.05:
            logger.info(f"  ✅ 面积估计准确")
        elif area_bias > 0:
            logger.info(f"  ⚠️ 倾向于过分割 (+{area_bias:.1%})")
        else:
            logger.info(f"  ⚠️ 倾向于欠分割 ({area_bias:.1%})")
    else:
        logger.warning("⚠️ 没有有效的评估结果")


if __name__ == '__main__':
    evaluate_radio_segmentation()
