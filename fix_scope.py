#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复变量作用域问题"""

segmentor_path = '/app/water_inspection/models/open_vocab/core/segmentor.py'

with open(segmentor_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到segment方法中detection_config的定义位置
# 确保它在使用之前定义，并且作用域覆盖整个方法
new_lines = []
in_segment = False
defined_detection = False

for i, line in enumerate(lines):
    new_lines.append(line)

    # 在segment方法开始处定义detection_config
    if 'def segment(' in line:
        in_segment = True

    if in_segment and 'classes_config = classes_config or self.get_classes_config()' in line:
        # 在下一行添加detection_config定义
        indent = '        '
        new_lines.append(f'{indent}\n')
        new_lines.append(f'{indent}# 过滤背景类，只保留检测类\n')
        new_lines.append(f'{indent}detection_config = {{k: v for k, v in classes_config.items() if not v.get("is_background", False)}}\n')
        new_lines.append(f'{indent}detection_prompts = None\n')
        new_lines.append(f'{indent}if prompts_config:\n')
        new_lines.append(f'{indent}    detection_prompts = {{k: v for k, v in prompts_config.items() if k in detection_config}}\n')
        new_lines.append('\n')
        defined_detection = True

with open(segmentor_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ 作用域修复完成")
print("  - detection_config现在在方法开始处定义")
print("  - 所有后续调用都可以访问")
