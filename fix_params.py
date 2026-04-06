#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
优化segmentor参数以增强类别区分度

问题: 所有类别分数太接近 (0.32-0.36)，缺乏区分度
解决: 降低温度参数，增加负样本权重
"""

segmentor_path = '/app/water_inspection/models/open_vocab/core/segmentor.py'

with open(segmentor_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修改1: 降低温度参数 (6.0 → 3.0)
# 温度越低，softmax后的分布越尖锐，类别差异越大
content = content.replace(
    'return radio_cfg.get("inference", {}).get("prompt", {}).get("temperature", 6.0)',
    'return radio_cfg.get("inference", {}).get("prompt", {}).get("temperature", 3.0)'
)

# 修改2: 增加负样本权重 (0.35 → 0.6)
# 更强的负样本抑制，帮助区分相似类别
content = content.replace(
    'return radio_cfg.get("inference", {}).get("prompt", {}).get("negative_weight", 0.35)',
    'return radio_cfg.get("inference", {}).get("prompt", {}).get("negative_weight", 0.6)'
)

with open(segmentor_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 参数优化完成:")
print("  - temperature: 6.0 → 3.0 (降低，增强类别差异)")
print("  - negative_weight: 0.35 → 0.6 (提高，增强负样本抑制)")
print("\n现在重新测试分类效果...")
