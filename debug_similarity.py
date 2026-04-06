#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""深度调试：查看每个类别的相似度分数"""

from pathlib import Path
import sys
import json
import numpy as np
import cv2

sys.path.insert(0, '/app/water_inspection')

from models.open_vocab.core.segmentor import WaterQualitySegmentor

# 加载模型
print("加载模型...")
segmentor = WaterQualitySegmentor(
    checkpoint_path='/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar',
    radio_code_dir='/app/models/NVlabs_RADIO',
    siglip2_dir='/app/models/siglip2-giant-opt-patch16-384',
    device='cuda',
    input_size=896,
    mode='single_stage'
)

# 测试几张典型误判的图片
test_cases = [
    ('101.jpg', 'red_water'),
    ('102.jpg', 'red_water'),
    ('12.jpg', 'turbid_water'),
    ('100.jpeg', 'turbid_water'),
]

print("\n" + "="*80)
print("深度调试：查看各类别相似度分数")
print("="*80)

for img_name, expected_class in test_cases:
    img_path = Path(f'/app/water_inspection/data/datasets/images/{img_name}')
    
    if not img_path.exists():
        print(f"\n⚠️ 图片不存在: {img_name}")
        continue
    
    # 读取图片
    image = cv2.imread(str(img_path))
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # 获取分类配置
    classes_config = segmentor.get_classes_config()
    prompts_config_path = Path('/app/water_inspection/models/open_vocab/prompts/water_quality.yaml')
    import yaml
    with open(prompts_config_path) as f:
        prompts_config = yaml.safe_load(f).get('water_quality_detection', {})
    
    # 测试分类器
    print(f"\n图片: {img_name} (GT: {expected_class})")
    print("-" * 80)
    
    # 获取图像分类概率
    class_probs = segmentor.text_classifier.classify_image(
        image, classes_config, prompts_config
    )
    
    # 按分数排序
    sorted_probs = sorted(class_probs.items(), key=lambda x: x[1], reverse=True)
    
    print("各类别相似度分数:")
    for i, (cls_name, prob) in enumerate(sorted_probs, 1):
        marker = "✅" if cls_name == expected_class else "  "
        print(f"  {marker} {i}. {cls_name}: {prob:.4f}")
    
    # 检查是否正确
    pred_class = sorted_probs[0][0] if sorted_probs else None
    is_correct = pred_class == expected_class
    status = "✅ 正确" if is_correct else "❌ 错误"
    print(f"\n结果: {status} (预测: {pred_class})")

print("\n" + "="*80)
print("分析完成")
print("="*80)
