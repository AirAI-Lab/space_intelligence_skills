#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复方案1的调用逻辑"""

segmentor_path = '/app/water_inspection/models/open_vocab/core/segmentor.py'

with open(segmentor_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复segment方法的开始部分
old_code = '''        classes_config = classes_config or self.get_classes_config()

        # 过滤背景类，只保留检测类
        detection_config = {k: v for k, v in classes_config.items() if not v.get("is_background", False)}'''

new_code = '''        classes_config = classes_config or self.get_classes_config()

        # 方案1: RADIO分割 + 颜色分类器 (推荐)
        if use_color_classifier:
            logger.info("使用方案1: RADIO分割 + 颜色分类")
            return self.segment_with_color_classify(
                image, classes_config, prompts_config, threshold
            )

        # 方案2: 原始SigLIP2流程 (不推荐)
        logger.info("使用方案2: SigLIP2文本对齐 (不推荐)")

        # 过滤背景类，只保留检测类
        detection_config = {k: v for k, v in classes_config.items() if not v.get("is_background", False)}'''

content = content.replace(old_code, new_code)

# 添加logger导入
if "import logging" in content and "logger = logging.getLogger(__name__)" not in content:
    content = content.replace(
        "import logging",
        "import logging\\nlogger = logging.getLogger(__name__)"
    )

with open(segmentor_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 方案1调用逻辑修复完成")
print("  - 添加use_color_classifier判断")
print("  - 默认使用颜色分类器")
print("  - 添加日志输出")
