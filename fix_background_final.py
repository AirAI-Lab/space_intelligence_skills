#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复segmentor.py的背景类过滤问题
并参考旧版实现优化分割
"""

segmentor_path = '/app/water_inspection/models/open_vocab/core/segmentor.py'

with open(segmentor_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复1: 在segment方法中添加背景类过滤
old_segment_start = """    def segment(
        self,
        image: np.ndarray,
        classes_config: Optional[Dict[str, dict]] = None,
        prompts_config: Optional[Dict[str, dict]] = None,
        class_thresholds: Optional[Dict[str, float]] = None,
        threshold: Optional[float] = None,
        min_area: Optional[float] = None,
    ) -> Dict[str, SegmentResult]:
        classes_config = classes_config or self.get_classes_config()"""

new_segment_start = """    def segment(
        self,
        image: np.ndarray,
        classes_config: Optional[Dict[str, dict]] = None,
        prompts_config: Optional[Dict[str, dict]] = None,
        class_thresholds: Optional[Dict[str, float]] = None,
        threshold: Optional[float] = None,
        min_area: Optional[float] = None,
    ) -> Dict[str, SegmentResult]:
        classes_config = classes_config or self.get_classes_config()

        # 过滤背景类，只保留检测类
        detection_config = {k: v for k, v in classes_config.items() if not v.get("is_background", False)}
        detection_prompts = None
        if prompts_config:
            detection_prompts = {k: v for k, v in prompts_config.items() if k in detection_config}"""

content = content.replace(old_segment_start, new_segment_start)

# 修复2: 修改classify_image调用使用detection_config
old_classify = """        # ━━━ 第 1 步: 图像级分类 ━━━
        class_probs = self.text_classifier.classify_image(
            image, classes_config, prompts_config
        )"""

new_classify = """        # ━━━ 第 1 步: 图像级分类 (排除背景类) ━━━
        class_probs = self.text_classifier.classify_image(
            image, detection_config, detection_prompts
        )"""

content = content.replace(old_classify, new_classify)

# 修复3: 修改compute_patch_similarity调用使用detection_config
old_patch = """        # ━━━ 第 2 步: Patch 级相似度计算 ━━━
        class_heatmaps = self.text_classifier.compute_patch_similarity(
            image, classes_config, prompts_config, self.input_size
        )"""

new_patch = """        # ━━━ 第 2 步: Patch 级相似度计算 (排除背景类) ━━━
        class_heatmaps = self.text_classifier.compute_patch_similarity(
            image, detection_config, detection_prompts, self.input_size
        )"""

content = content.replace(old_patch, new_patch)

# 修复4: 修改颜色融合调用
old_color = """        # 应用颜色软融合
        class_heatmaps = self._apply_color_soft_fusion(
            image, class_heatmaps, classes_config
        )"""

new_color = """        # 应用颜色软融合 (使用检测类)
        class_heatmaps = self._apply_color_soft_fusion(
            image, class_heatmaps, detection_config
        )"""

content = content.replace(old_color, new_color)

with open(segmentor_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 背景类过滤修复完成:")
print("  - segment()方法现在过滤背景类")
print("  - classify_image只使用6个检测类")
print("  - compute_patch_similarity只使用6个检测类")
print("  - 颜色融合也只使用6个检测类")
print("\n现在normal_water完全不参与分类和分割！")
