#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一水质分割器评估脚本

在标注数据集上评估重构后的分割器性能:
- 评估 RADIO 分割 IoU
- 评估分类准确率
- 统计颜色分布

数据集位置: /app/water_inspection/data/datasets/
图片: 109 张
GT masks: 127 个
元数据: JSON 格式（包含类别、bbox 等)

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import sys
import argparse
import yaml
import json
import numpy as np
import cv2
from pathlib import Path
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "models"))
sys.path.insert(0, str(Path(__file__).parent.parent / "temp_configs_backup"))

sys.path.insert(0, str(Path(__file__).parent.parent / "temp_open_vocab_backup"))

sys.path.insert(0, str(Path(__file__).parent / "models/open_vocab")

sys.path.insert(0, str(Path(__file__).parent / "temp_open_vocab_backup"))

sys.path.insert(0, str(Path(__file__).parent / "temp_open_vocab_backup")
sys.path.insert(0, str(Path(__file__).parent / "temp_configs_backup")

sys.path.insert(0, str(Path(__file__).parent / "temp_open_vocab_backup")

sys.path.insert(0, str(Path(__file__).parent / "temp_open_vocab_backup")

from models.open_vocab import WaterQualitySegmentor
from models.open_vocab.utils import WaterQualityEvaluator
from models.open_vocab.utils import WaterQualityVisualizer


from models.open_vocab.prompts import load_prompts, get_water_quality_prompts


print(f"当前工作目录: {os.getcwd()}")
print(f"输出目录: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="评估统一水质分割器")
    parser.add_argument("--data-dir", type=str, default="/app/water_inspection/data/datasets/images",
    parser.add_argument("--gt-dir", type=str, default="/app/water_inspection/data/datasets/masks")
    parser.add_argument("--meta", type=str, default="/app/water_inspection/data/datasets/meta.json")
    parser.add_argument("--config", type=str, default="/app/configs/water_inspection.yaml")
    parser.add_argument("--prompts", type=str, default="/app/configs/prompts.yaml")
    parser.add_argument("--output", type=str, default="./eval_output")
    parser.add_argument("--max-samples", type=int, default=-1)
    parser.add_argument("--device", type=str, default="cuda")
    args = parser.parse_args()

    # 加载配置
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    print(f"配置加载完成")
    print(f"  类别: {list(config.get('cloud', {}).get('radio', {}).get('classes', {}).keys())}")
    # 加载提示词
    prompts_config = load_prompts(args.prompts)
    print(f"提示词加载完成")
    print(f"  类别: {list(prompts_config.get('water_quality_detection', {}).keys())}")

    # 初始化分割器
    segmentor = WaterQualitySegmentor(
        config=config,
        device=args.device,
    )
    print(f"分割器初始化完成")

    # 初始化评估器
    evaluator = WaterQualityEvaluator(
        data_dir=args.data_dir,
        gt_dir=args.gt_dir,
        meta_path=args.meta,
    )
    print(f"评估器初始化完成")
    print(f"  样本数: {len(list(Path(args.data_dir).glob('*.jpg')))}")
    # 执行评估
    print("\n开始评估...")
    metrics = evaluator.evaluate(
        segmentor=segmentor,
        classes_config=config.get('cloud', {}).get('radio', {}).get('classes', {}),
        prompts_config=prompts_config.get('water_quality_detection', {}),
        max_samples=args.max_samples,
        save_visualizations=True,
        output_dir=args.output,
    )
    # 打印结果
    print("\n" + "=" * 60)
    print("评估结果:")
    print("=" * 60)
    for cls_name in evaluator.CLASS_NAMES:
        m = metrics[cls_name]
        print(f"\n{cls_name}:")
        print(f"  IoU: {m.iou:.4f}")
        print(f"  Dice: {m.dice:.4f}")
        print(f"  Pixel Accuracy: {m.pixel_accuracy:.4f}")
        print(f"  Class Accuracy: {m.class_accuracy:.4f}")
        print(f"  Precision: {m.precision:.4f}")
        print(f"  Recall: {m.recall:.4f}")
        print(f"  F1 Score: {m.f1_score:.4f}")
        print(f"  TP: {m.true_positives}")
        print(f"  FP: {m.false_positives}")
        print(f"  TN: {m.true_negatives}")
        print(f"  FN: {m.false_negatives}")
    print("=" * 60)

    print(f"\n可视化结果已保存到: {args.output}")


if __name__ == "__main__":
    main()
