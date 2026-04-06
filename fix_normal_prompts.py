#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
优化normal_water的提示词，使其更严格

问题: normal_water提示词太通用，对所有水质都匹配
解决: 使用更严格的描述，强调"完美清澈"和"无任何异常"
"""

prompts_path = '/app/water_inspection/models/open_vocab/prompts/water_quality.yaml'

with open(prompts_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换normal_water的提示词
old_normal_positive = """  normal_water:
    positive:
      - perfectly clear transparent river water with no color tint high visibility
      - clean unpolluted water showing natural blue gray tone B channel slightly higher
      - crystal clear water surface without green brown or black abnormal coloration
      - fresh river water in pristine condition transparent and clear
      - typical healthy urban river water with balanced RGB no dominant green channel
      - water with natural appearance where B channel equals or exceeds G channel
      - transparent water body reflecting surroundings without colored pollution"""

new_normal_positive = """  normal_water:
    positive:
      - perfectly crystal clear transparent water showing riverbed with high visibility depth
      - absolutely clean pristine water with no color deviation perfectly balanced RGB channels
      - pure transparent drinking water quality with no particles sediment or discoloration
      - perfectly clear water like glass showing deep riverbed without any turbidity or haze"""

content = content.replace(old_normal_positive, new_normal_positive)

with open(prompts_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ normal_water提示词优化完成:")
print("  - 使用更严格的描述")
print("  - 强调'绝对清澈'、'完美平衡'、'无任何颗粒'")
print("  - 减少提示词数量，提高精确度")
print("\n现在normal_water只匹配真正清澈透明的水质")
