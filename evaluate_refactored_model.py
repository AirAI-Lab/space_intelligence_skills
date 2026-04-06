#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重构后水质检测模型评估脚本

在容器中运行，评估:
1. RADIO分割IoU (基于GT masks)
2. 分类准确率 (6类异常水质)
3. 可视化效果验证

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
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple
import logging

# 设置路径
sys.path.insert(0, '/app/water_inspection')

from models.open_vocab.core.segmentor import WaterQualitySegmentor
from models.open_vocab.utils.evaluation import WaterQualityEvaluator
from models.open_vocab.utils.visualization import WaterQualityVisualizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def evaluate_refactored_model():
    """评估重构后的模型"""
    
    # 配置路径
    data_dir = Path('/app/water_inspection/data/datasets/images')
    gt_dir = Path('/app/water_inspection/data/datasets/masks')
    meta_dir = Path('/app/water_inspection/data/datasets/meta')
    output_dir = Path('/app/water_inspection/data/evaluation_results')
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # 1. 加载模型
    logger.info("="*80)
    logger.info("步骤1: 加载重构后的水质检测模型")
    logger.info("="*80)
    
    try:
        segmentor = WaterQualitySegmentor(
            checkpoint_path='/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar',
            radio_code_dir='/app/models/NVlabs_RADIO',
            siglip2_dir='/app/models/siglip2-giant-opt-patch16-384',
            device='cuda' if torch.cuda.is_available() else 'cpu',
            input_size=896,
            mode='single_stage'
        )
        logger.info("✅ 模型加载成功")
    except Exception as e:
        logger.error(f"❌ 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. 初始化评估器
    logger.info("\n" + "="*80)
    logger.info("步骤2: 初始化评估器")
    logger.info("="*80)
    
    evaluator = WaterQualityEvaluator(
        data_dir=str(data_dir),
        gt_dir=str(gt_dir),
        meta_path=None  # TODO: 需要整合meta数据
    )
    
    # 3. 批量评估
    logger.info("\n" + "="*80)
    logger.info("步骤3: 批量评估 (109张图片)")
    logger.info("="*80)
    
    image_files = list(data_dir.glob('*.jpg')) + list(data_dir.glob('*.jpeg')) + list(data_dir.glob('*.png'))
    logger.info(f"找到 {len(image_files)} 张图片")
    
    eval_results = []  # 评估结果列表
    class_stats = {
        'black_water': {'total': 0, 'correct': 0, 'iou_sum': 0.0},
        'turbid_water': {'total': 0, 'correct': 0, 'iou_sum': 0.0},
        'red_water': {'total': 0, 'correct': 0, 'iou_sum': 0.0},
        'green_water': {'total': 0, 'correct': 0, 'iou_sum': 0.0},
        'milky_foam_water': {'total': 0, 'correct': 0, 'iou_sum': 0.0},
        'dam_seepage': {'total': 0, 'correct': 0, 'iou_sum': 0.0},
        'normal_water': {'total': 0, 'correct': 0, 'iou_sum': 0.0},
    }
    
    for idx, img_path in enumerate(image_files[:109]):  # 评估所有109张图片
        logger.info(f"\n[{idx+1}/{min(10, len(image_files))}] 处理: {img_path.name}")
        
        try:
            # 读取图像
            image = cv2.imread(str(img_path))
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 推理
            results = segmentor.segment(image)
            
            # 查找对应的GT
            gt_mask_path = gt_dir / f"{img_path.stem}_*.png"
            gt_masks = list(gt_dir.glob(f"{img_path.stem}_*.png"))
            
            if gt_masks and results:
                # 获取主要结果（面积最大的）
                main_result = max(results.values(), key=lambda r: r.area_ratio if hasattr(r, 'mask') and r.mask is not None else 0)
                
                # 读取GT
                gt_mask = cv2.imread(str(gt_masks[0]), cv2.IMREAD_GRAYSCALE)
                
                # 计算IoU
                if main_result.mask is not None:
                    intersection = np.logical_and(main_result.mask, gt_mask > 0).sum()
                    union = np.logical_or(main_result.mask, gt_mask > 0).sum()
                    iou = intersection / (union + 1e-6)
                else:
                    iou = 0.0
                
                # 统计
                eval_results.append({
                    'image': img_path.name,
                    'pred_class': main_result.class_name,
                    'score': main_result.score,
                    'iou': iou,
                    'color_ok': main_result.color_ok
                })
                
                logger.info(f"  预测: {main_result.class_name} (score={main_result.score:.3f}, iou={iou:.3f})")
            
        except Exception as e:
            logger.error(f"  ❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 4. 汇总统计
    logger.info("\n" + "="*80)
    logger.info("步骤4: 评估统计")
    logger.info("="*80)
    
    if eval_results:
        avg_iou = np.mean([r['iou'] for r in eval_results])
        avg_score = np.mean([r['score'] for r in eval_results])
        color_ok_rate = sum([r['color_ok'] for r in eval_results]) / len(eval_results)
        
        logger.info(f"\n📊 整体性能:")
        logger.info(f"  平均IoU: {avg_iou:.3f}")
        logger.info(f"  平均置信度: {avg_score:.3f}")
        logger.info(f"  颜色验证通过率: {color_ok_rate:.1%}")
        
        # 保存结果
        report_path = output_dir / 'evaluation_report.json'
        with open(report_path, 'w') as f:
            json.dump({
                'total_images': len(eval_results),
                'avg_iou': float(avg_iou),
                'avg_score': float(avg_score),
                'color_ok_rate': float(color_ok_rate),
                'results': eval_results
            }, f, indent=2)
        
        logger.info(f"\n✅ 评估报告已保存: {report_path}")
    else:
        logger.warning("⚠️ 没有有效的评估结果")
    
    # 5. 可视化验证 (选择3张图片)
    logger.info("\n" + "="*80)
    logger.info("步骤5: 可视化验证 (3张样本)")
    logger.info("="*80)
    
    vis_dir = output_dir / 'visualizations'
    vis_dir.mkdir(exist_ok=True)
    
    for idx, img_path in enumerate(image_files[:3]):
        logger.info(f"\n[{idx+1}/3] 可视化: {img_path.name}")
        
        try:
            image = cv2.imread(str(img_path))
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            results_dict = segmentor.segment(image)
            
            if not results_dict:
                logger.warning(f"  ⚠️ 无分割结果")
                continue
            
            # 可视化
            visualizer = WaterQualityVisualizer()
            
            vis_image = visualizer.visualize_segmentation(
                cv2.cvtColor(image, cv2.COLOR_RGB2BGR),
                results_dict,
                show_label=True
            )
            
            # 保存
            vis_path = vis_dir / f"{img_path.stem}_vis.jpg"
            cv2.imwrite(str(vis_path), vis_image)
            
            logger.info(f"  ✅ 可视化已保存: {vis_path}")
            
        except Exception as e:
            logger.error(f"  ❌ 可视化失败: {e}")
    
    logger.info("\n" + "="*80)
    logger.info("评估完成！")
    logger.info("="*80)
    logger.info(f"结果目录: {output_dir}")
    logger.info(f"  - evaluation_report.json")
    logger.info(f"  - visualizations/")


if __name__ == '__main__':
    evaluate_refactored_model()
