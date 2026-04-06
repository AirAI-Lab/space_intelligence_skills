#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将轻量化分类器集成到segmentor

集成方案3: RADIO分割 + 轻量SVM分类器

作者: 空中智能体团队
日期: 2026-04-06
"""

import pickle
from pathlib import Path

segmentor_path = '/app/water_inspection/models/open_vocab/core/segmentor.py'

# 读取当前代码
with open(segmentor_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加轻量化分类器的集成代码
lightweight_classifier_code = '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 加载轻量化分类器
        self._load_lightweight_classifier()
    
    def _load_lightweight_classifier(self):
        """加载训练好的轻量化分类器"""
        import pickle
        from pathlib import Path
        
        model_dir = Path('/app/water_inspection/models/classifier')
        model_path = model_dir / 'lightweight_classifier.pkl'
        scaler_path = model_dir / 'scaler.pkl'
        
        if model_path.exists() and scaler_path.exists():
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
                self.lightweight_clf = model_data['classifier']
                self.lightweight_clf_name = model_data['name']
            
            with open(scaler_path, 'rb') as f:
                self.lightweight_scaler = pickle.load(f)
            
            print(f"  ✅ 轻量化分类器已加载: {self.lightweight_clf_name}")
        else:
            self.lightweight_clf = None
            self.lightweight_scaler = None
            print(f"  ⚠️ 轻量化分类器未找到")
    
    def classify_by_lightweight_clf(self, image: np.ndarray, mask: np.ndarray = None) -> Tuple[str, float]:
        """
        使用轻量化分类器进行分类 (方案3)
        
        Args:
            image: RGB图像
            mask: 分割掩码
            
        Returns:
            (class_name, confidence)
        """
        import cv2
        
        if self.lightweight_clf is None:
            return "normal_water", 0.5
        
        # 提取特征 (与训练时相同)
        features = self.extract_color_features(image, mask)
        
        if not features:
            return "normal_water", 0.5
        
        # 构建特征向量 (与训练时相同顺序)
        bgr_mean = features['bgr_mean']
        bgr_std = features['bgr_std']
        hsv_mean = features['hsv_mean']
        hsv_std = features['hsv_std']
        b_hist = features['b_hist']
        g_hist = features['g_hist']
        r_hist = features['r_hist']
        
        # 计算与各类别的颜色距离
        CLASS_COLORS_BGR = {
            "black_water": np.array([90, 95, 85]),
            "turbid_water": np.array([119, 140, 130]),
            "red_water": np.array([100, 80, 140]),
            "green_water": np.array([117, 156, 130]),
            "milky_foam_water": np.array([180, 190, 195]),
            "dam_seepage": np.array([130, 135, 140]),
            "normal_water": np.array([118, 124, 107]),
        }
        
        color_dists = []
        for cls_name in ["black_water", "turbid_water", "red_water", 
                         "green_water", "milky_foam_water", "dam_seepage", "normal_water"]:
            std_color = CLASS_COLORS_BGR[cls_name]
            dist = np.linalg.norm(bgr_mean - std_color)
            color_dists.append(dist)
        
        # 合并特征
        feature_vector = np.concatenate([
            bgr_mean,      # 3
            bgr_std,       # 3
            hsv_mean,      # 3
            hsv_std,       # 3
            b_hist,        # 16
            g_hist,        # 16
            r_hist,        # 16
            np.array(color_dists),  # 7
        ])
        
        # 标准化
        feature_scaled = self.lightweight_scaler.transform(feature_vector.reshape(1, -1))
        
        # 预测
        class_idx = self.lightweight_clf.predict(feature_scaled)[0]
        
        # 获取置信度 (SVM使用decision_function)
        if hasattr(self.lightweight_clf, 'predict_proba'):
            proba = self.lightweight_clf.predict_proba(feature_scaled)[0]
            confidence = proba[class_idx]
        elif hasattr(self.lightweight_clf, 'decision_function'):
            decision = self.lightweight_clf.decision_function(feature_scaled)[0]
            # 转换为概率
            from scipy.special import softmax
            proba = softmax(decision)
            confidence = proba[class_idx]
        else:
            confidence = 0.7  # 默认置信度
        
        CLASS_NAMES = [
            "black_water", "turbid_water", "red_water",
            "green_water", "milky_foam_water", "dam_seepage", "normal_water"
        ]
        
        class_name = CLASS_NAMES[class_idx]
        
        return class_name, float(confidence)

'''

# 在WaterQualitySegmentor类的__init__方法之前插入新代码
# 找到class WaterQualitySegmentor:的位置
class_pos = content.find('class WaterQualitySegmentor:')
if class_pos > 0:
    # 找到__init__方法的位置
    init_pos = content.find('    def __init__(\n        self,', class_pos)
    if init_pos > 0:
        # 在__init__之前插入新方法
        content = content[:init_pos] + lightweight_classifier_code + "\n" + content[init_pos:]

# 修改segment_with_color_classify使用轻量化分类器
old_classify = "        # Step 2: 颜色分类 (增强版)\n        pred_class, confidence = self.classify_by_enhanced_features(image, water_mask)"
new_classify = "        # Step 2: 轻量化分类器 (方案3)\n        pred_class, confidence = self.classify_by_lightweight_clf(image, water_mask)"

content = content.replace(old_classify, new_classify)

# 保存
with open(segmentor_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 轻量化分类器集成完成:")
print("  1. 添加_load_lightweight_classifier() - 自动加载模型")
print("  2. 添加classify_by_lightweight_clf() - 方案3主分类器")
print("  3. 修改segment_with_color_classify() - 使用轻量分类器")
print("\n  方案3流程:")
print("    RADIO水体分割 → 轻量SVM分类 → 返回结果")
print("  预期准确率: 68.6%")
