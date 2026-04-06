#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复：在分类前过滤背景类"""

segmentor_path = '/app/water_inspection/models/open_vocab/core/segmentor.py'

with open(segmentor_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修改classify_image调用
old_classify = """        # ━━━ 第 1 步: 图像级分类 ━━━
        class_probs = self.text_classifier.classify_image(
            image, classes_config, prompts_config
        )"""

new_classify = """        # ━━━ 第 1 步: 图像级分类 (排除背景类) ━━━
        detection_config = {k: v for k, v in classes_config.items() if not v.get("is_background", False)}
        detection_prompts = {k: v for k, v in prompts_config.items() if k in detection_config} if prompts_config else None
        class_probs = self.text_classifier.classify_image(
            image, detection_config, detection_prompts
        )"""

content = content.replace(old_classify, new_classify)

# 修改compute_patch_similarity调用
old_patch = """        # ━━━ 第 2 步: Patch 级相似度计算 ━━━
        class_heatmaps = self.text_classifier.compute_patch_similarity(
            image, classes_config, prompts_config, self.input_size
        )"""

new_patch = """        # ━━━ 第 2 步: Patch 级相似度计算 (排除背景类) ━━━
        class_heatmaps = self.text_classifier.compute_patch_similarity(
            image, detection_config, detection_prompts, self.input_size
        )"""

content = content.replace(old_patch, new_patch)

with open(segmentor_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 修复完成:")
print("  - 分类时完全排除normal_water")
print("  - 只使用6个异常检测类别")
print("\n这将显著提升分类准确率！")
