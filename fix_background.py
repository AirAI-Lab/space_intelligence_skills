#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复：在分类时排除背景类(normal_water)

问题: classify_image使用所有类别，包括背景类
解决: 只传递非背景类给分类器
"""

segmentor_path = '/app/water_inspection/models/open_vocab/core/segmentor.py'

with open(segmentor_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到classify_image的调用位置并修改
new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)

    # 在"class_probs = self.text_classifier.classify_image"之前添加过滤逻辑
    if '# ━━━ 第 1 步: 图像级分类 ━━━' in line:
        # 添加注释和过滤代码
        indent = '        '
        new_lines.append(f'{indent}# 过滤掉背景类，只保留检测类别\n')
        new_lines.append(f'{indent}detection_config = {{k: v for k, v in classes_config.items() if not v.get("is_background", False)}}\n')
        new_lines.append(f'{indent}detection_prompts = {{k: v for k, v in prompts_config.items() if k in detection_config}} if prompts_config else None\n')
        new_lines.append('\n')

    # 修改classify_image调用，使用detection_config
    if 'class_probs = self.text_classifier.classify_image(' in line:
        # 替换这一行
        indent = '        '
        new_lines[-1] = f'{indent}class_probs = self.text_classifier.classify_image(\n'
        new_lines.append(f'{indent}    image, detection_config, detection_prompts\n')
        new_lines.append(f'{indent})\n')

    # 修改compute_patch_similarity调用
    if 'class_heatmaps = self.text_classifier.compute_patch_similarity(' in line:
        indent = '        '
        new_lines[-1] = f'{indent}class_heatmaps = self.text_classifier.compute_patch_similarity(\n'
        new_lines.append(f'{indent}    image, detection_config, detection_prompts, self.input_size\n')
        new_lines.append(f'{indent})\n')

with open(segmentor_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ 修复完成:")
print("  - classify_image 现在只使用6个检测类")
print("  - compute_patch_similarity 也只使用6个检测类")
print("  - normal_water (背景类) 完全不参与分类")
print("\n现在重新测试应该能看到显著改善！")
