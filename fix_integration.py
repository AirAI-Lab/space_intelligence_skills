#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复集成调用bug"""

segmentor_path = '/app/water_inspection/models/open_vocab/core/segmentor.py'

with open(segmentor_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到错误的__init__并删除
new_lines = []
skip_until_next_def = False
init_count = 0

for i, line in enumerate(lines):
    # 检测第一个__init__方法（错误添加的）
    if '    def __init__(self, *args, **kwargs):' in line and init_count == 0:
        skip_until_next_def = True
        init_count += 1
        continue
    
    # 跳过直到下一个def
    if skip_until_next_def:
        if line.strip().startswith('def ') and 'def __init__' not in line:
            skip_until_next_def = False
            new_lines.append(line)
        continue
    
    new_lines.append(line)

# 保存
with open(segmentor_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ 修复完成 - 删除了错误的__init__方法")
