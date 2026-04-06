#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试脚本：检查提示词加载和SigLIP2分类"""

from pathlib import Path
import yaml
import sys

sys.path.insert(0, '/app/water_inspection')

print("="*80)
print("步骤1: 检查提示词文件加载")
print("="*80)

prompts_path = Path('/app/water_inspection/models/open_vocab/prompts/water_quality.yaml')
with open(prompts_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

water_quality = config.get('water_quality_detection', {})
print(f"\n找到 {len(water_quality)} 个类别:")
for cls_name in water_quality.keys():
    print(f"  - {cls_name}")

# 检查red_water的提示词
print("\n" + "="*80)
print("red_water 提示词检查")
print("="*80)
red_cfg = water_quality.get('red_water', {})
pos_prompts = red_cfg.get('positive', [])
neg_prompts = red_cfg.get('negative', [])
print(f"正样本提示词: {len(pos_prompts)}")
for i, p in enumerate(pos_prompts[:3], 1):
    print(f"  {i}. {p}")
print(f"\n负样本提示词: {len(neg_prompts)}")
for i, p in enumerate(neg_prompts[:3], 1):
    print(f"  {i}. {p}")

# 检查turbid_water的提示词
print("\n" + "="*80)
print("turbid_water 提示词检查")
print("="*80)
turbid_cfg = water_quality.get('turbid_water', {})
pos_prompts = turbid_cfg.get('positive', [])
neg_prompts = turbid_cfg.get('negative', [])
print(f"正样本提示词: {len(pos_prompts)}")
for i, p in enumerate(pos_prompts[:3], 1):
    print(f"  {i}. {p}")
print(f"\n负样本提示词: {len(neg_prompts)}")
for i, p in enumerate(neg_prompts[:3], 1):
    print(f"  {i}. {p}")

print("\n" + "="*80)
print("步骤2: 测试SigLIP2分类器")
print("="*80)

from models.open_vocab.core.segmentor import WaterQualitySegmentor
import numpy as np
import cv2

# 加载模型
segmentor = WaterQualitySegmentor(
    checkpoint_path='/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar',
    radio_code_dir='/app/models/NVlabs_RADIO',
    siglip2_dir='/app/models/siglip2-giant-opt-patch16-384',
    device='cuda',
    input_size=896,
    mode='single_stage'
)

print("\n✅ 模型加载成功")

# 测试red_water图片
test_image_path = Path('/app/water_inspection/data/datasets/images/101.jpg')
image = cv2.imread(str(test_image_path))
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

print(f"\n测试图片: {test_image_path.name}")
print(f"图片尺寸: {image.shape}")

# 获取分类配置
classes_config = segmentor.get_classes_config()
print(f"\n类别配置数: {len(classes_config)}")
for cls_name, cls_cfg in classes_config.items():
    prompts = cls_cfg.get('prompts', [])
    is_bg = cls_cfg.get('is_background', False)
    print(f"  {cls_name}: {len(prompts)} prompts, background={is_bg}")

# 测试分类
print("\n进行分类测试...")
results = segmentor.segment(image)

if results:
    print(f"\n预测结果:")
    for cls_name, result in sorted(results.items(), key=lambda x: x[1].score, reverse=True)[:3]:
        print(f"  {cls_name}: score={result.score:.3f}, area={result.area_ratio:.3f}")
else:
    print("\n❌ 无预测结果！")

print("\n" + "="*80)
print("调试完成")
print("="*80)
