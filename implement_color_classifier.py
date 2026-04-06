#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
方案1实现: RADIO分割 + 颜色规则分类器

策略:
1. RADIO负责水体分割 (48.8% IoU)
2. 基于颜色的简单规则分类器 (参考v4.1颜色统计)
3. 7类统一: 5异常水质 + 1坝体渗水 + 1背景

作者: 空中智能体团队
日期: 2026-04-06
"""

segmentor_path = '/app/water_inspection/models/open_vocab/core/segmentor.py'

with open(segmentor_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加基于颜色的简单分类器
color_classifier_code = """
    def classify_by_color(self, image: np.ndarray, mask: np.ndarray = None) -> Tuple[str, float]:
        \"\"\"
        基于颜色的简单规则分类器 (方案1)
        
        策略:
        1. 计算区域平均颜色
        2. 与7类标准颜色比较
        3. 返回最匹配的类别
        
        Args:
            image: RGB图像
            mask: 分割掩码 (可选)
            
        Returns:
            (class_name, confidence)
        \"\"\"
        import cv2
        
        # 转换为BGR
        if image.shape[2] == 3:
            img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = image
        
        # 计算平均颜色
        if mask is not None and mask.any():
            mean_color = cv2.mean(img_bgr, mask.astype(np.uint8))[:3]
        else:
            mean_color = cv2.mean(img_bgr)[:3]
        
        mean_bgr = np.array(mean_color)
        
        # 7类标准颜色 (BGR) - 基于109张样本统计
        CLASS_COLORS_BGR = {
            "black_water": np.array([90, 95, 85]),
            "turbid_water": np.array([119, 140, 130]),
            "red_water": np.array([100, 80, 140]),
            "green_water": np.array([117, 156, 130]),
            "milky_foam_water": np.array([180, 190, 195]),
            "dam_seepage": np.array([130, 135, 140]),
            "normal_water": np.array([118, 124, 107]),
        }
        
        # 计算与各类别的颜色距离
        distances = {}
        for cls_name, std_color in CLASS_COLORS_BGR.items():
            dist = np.linalg.norm(mean_bgr - std_color)
            distances[cls_name] = dist
        
        # 找到最接近的类别
        best_class = min(distances.keys(), key=lambda k: distances[k])
        best_dist = distances[best_class]
        
        # 转换为置信度 (距离越小置信度越高)
        max_dist = 150.0  # 假设最大距离
        confidence = max(0.0, 1.0 - best_dist / max_dist)
        
        return best_class, confidence
    
    def segment_with_color_classify(
        self,
        image: np.ndarray,
        classes_config: Optional[Dict[str, dict]] = None,
        prompts_config: Optional[Dict[str, dict]] = None,
        threshold: Optional[float] = None,
    ) -> Dict[str, 'SegmentResult']:
        \"\"\"
        方案1主流程: RADIO分割 + 颜色分类
        
        流程:
        1. RADIO提取水体区域
        2. 颜色规则分类水质
        3. 返回分割+分类结果
        
        Args:
            image: BGR图像
            classes_config: 类别配置
            prompts_config: 提示词配置
            threshold: 分割阈值
            
        Returns:
            {class_name: SegmentResult}
        \"\"\"
        import cv2
        
        orig_h, orig_w = image.shape[:2]
        
        # 过滤背景类
        classes_config = classes_config or self.get_classes_config()
        detection_config = {k: v for k, v in classes_config.items() if not v.get("is_background", False)}
        detection_prompts = None
        if prompts_config:
            detection_prompts = {k: v for k, v in prompts_config.items() if k in detection_config}
        
        # Step 1: RADIO水体分割 (使用water vs background对比)
        # 简化为water提取
        water_prompts = {
            "water": {
                "prompts": [
                    "water surface in natural environment",
                    "river or lake water body",
                    "flowing or standing water",
                ]
            }
        }
        
        # 计算水体热图
        heatmaps = self.text_classifier.compute_patch_similarity(
            image, {"water": {"prompts": water_prompts["water"]["prompts"]}}, None, self.input_size
        )
        
        if "water" not in heatmaps:
            return {}
        
        water_heatmap = heatmaps["water"]
        
        # 阈值化得到水体mask
        threshold = threshold or 0.35
        water_mask = water_heatmap > threshold
        
        # 后处理
        water_mask = self._postprocess_mask(water_mask, min_area=0.01)
        
        if not water_mask.any():
            return {}
        
        # Step 2: 颜色分类
        pred_class, confidence = self.classify_by_color(image, water_mask)
        
        # Step 3: 构造结果
        result = SegmentResult(
            class_name=pred_class,
            class_name_cn=self.CLASS_COLORS.get(pred_class, pred_class),
            mask=water_mask,
            area_ratio=water_mask.sum() / water_mask.size,
            score=confidence,
            water_iou=0.0,
            color_ok=True
        )
        
        return {pred_class: result}

"""

# 在segmentor.py的WaterQualitySegmentor类中添加新方法
# 找到class WaterQualitySegmentor的末尾位置
insert_pos = content.find("    def visualize(")
if insert_pos > 0:
    # 在visualize方法之前插入新方法
    content = content[:insert_pos] + color_classifier_code + "\n" + content[insert_pos:]

# 修改segment方法，添加方案1的调用选项
old_segment_doc = '''    def segment(
        self,
        image: np.ndarray,
        classes_config: Optional[Dict[str, dict]] = None,
        prompts_config: Optional[Dict[str, dict]] = None,
        class_thresholds: Optional[Dict[str, float]] = None,
        threshold: Optional[float] = None,
        min_area: Optional[float] = None,
    ) -> Dict[str, SegmentResult]:
        """
        水质异常分割

        Args:
            image: BGR 图像 [H, W, 3]
            classes_config: 类别配置 (可选, 默认使用配置文件)
            prompts_config: 提示词配置
            threshold: 百分位阈值
            min_area: 最小面积占比

        Returns:
            {class_name: SegmentResult}
        """'''

new_segment_doc = '''    def segment(
        self,
        image: np.ndarray,
        classes_config: Optional[Dict[str, dict]] = None,
        prompts_config: Optional[Dict[str, dict]] = None,
        class_thresholds: Optional[Dict[str, float]] = None,
        threshold: Optional[float] = None,
        min_area: Optional[float] = None,
        use_color_classifier: bool = True,  # 方案1: 使用颜色分类器
    ) -> Dict[str, SegmentResult]:
        """
        水质异常分割
        
        方案1 (推荐): RADIO分割 + 颜色规则分类

        Args:
            image: BGR 图像 [H, W, 3]
            classes_config: 类别配置 (可选, 默认使用配置文件)
            prompts_config: 提示词配置
            threshold: 百分位阈值
            min_area: 最小面积占比
            use_color_classifier: 是否使用颜色分类器 (方案1)

        Returns:
            {class_name: SegmentResult}
        """'''

content = content.replace(old_segment_doc, new_segment_doc)

# 在segment方法开始处添加方案1判断
old_segment_start = '''        classes_config = classes_config or self.get_classes_config()

        # 过滤背景类，只保留检测类
        detection_config = {k: v for k, v in classes_config.items() if not v.get("is_background", False)}'''

new_segment_start = '''        classes_config = classes_config or self.get_classes_config()

        # 方案1: RADIO分割 + 颜色分类器 (推荐)
        if use_color_classifier:
            return self.segment_with_color_classify(
                image, classes_config, prompts_config, threshold
            )

        # 方案2: 原始SigLIP2文本对齐流程 (分类性能差，不推荐)
        # 过滤背景类，只保留检测类
        detection_config = {k: v for k, v in classes_config.items() if not v.get("is_background", False)}'''

content = content.replace(old_segment_start, new_segment_start)

# 保存修改
with open(segmentor_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 方案1实现完成:")
print("  1. 添加classify_by_color() - 基于颜色的简单分类器")
print("  2. 添加segment_with_color_classify() - 方案1主流程")
print("  3. 修改segment() - 默认使用颜色分类器")
print("\n  方案1流程:")
print("    RADIO水体分割 → 颜色规则分类 → 返回结果")
print("\n  7类统一:")
print("    - 5类异常水质: black, turbid, red, green, milky_foam")
print("    - 1类坝体渗水: dam_seepage")
print("    - 1类背景: normal_water")
print("\n开始评估...")
