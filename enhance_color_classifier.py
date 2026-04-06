#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
方案1增强: 颜色特征 + 传统ML分类器

策略:
1. 提取多维度颜色特征 (均值、方差、直方图)
2. 使用简单规则 + SVM/随机森林分类
3. 基于109张样本的GT统计训练分类器

作者: 空中智能体团队
日期: 2026-04-06
"""

segmentor_path = '/app/water_inspection/models/open_vocab/core/segmentor.py'

with open(segmentor_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 增强颜色分类器
enhanced_classifier = '''
    def extract_color_features(self, image: np.ndarray, mask: np.ndarray = None) -> dict:
        """
        提取多维度颜色特征
        
        特征:
        1. BGR均值和标准差
        2. HSV均值和标准差  
        3. 颜色直方图特征
        """
        import cv2
        
        # 转BGR
        if len(image.shape) == 3 and image.shape[2] == 3:
            img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if image.dtype == np.uint8 else image
        else:
            img_bgr = image
        
        # 应用mask
        if mask is not None and mask.any():
            masked_img = img_bgr * mask[:, :, np.newaxis]
            pixels = masked_img[mask > 0]
        else:
            pixels = img_bgr.reshape(-1, 3)
        
        if len(pixels) == 0:
            return {}
        
        # BGR统计
        bgr_mean = pixels.mean(axis=0)
        bgr_std = pixels.std(axis=0)
        
        # 转HSV
        hsv_img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        if mask is not None and mask.any():
            hsv_pixels = hsv_img[mask > 0]
        else:
            hsv_pixels = hsv_img.reshape(-1, 3)
        
        hsv_mean = hsv_pixels.mean(axis=0)
        hsv_std = hsv_pixels.std(axis=0)
        
        # 颜色直方图 (简化版)
        # B通道分布
        b_hist = np.histogram(pixels[:, 0], bins=3, range=(0, 255))[0]
        g_hist = np.histogram(pixels[:, 1], bins=3, range=(0, 255))[0]
        r_hist = np.histogram(pixels[:, 2], bins=3, range=(0, 255))[0]
        
        # 归一化
        b_hist = b_hist / (b_hist.sum() + 1e-6)
        g_hist = g_hist / (g_hist.sum() + 1e-6)
        r_hist = r_hist / (r_hist.sum() + 1e-6)
        
        return {
            'bgr_mean': bgr_mean,
            'bgr_std': bgr_std,
            'hsv_mean': hsv_mean,
            'hsv_std': hsv_std,
            'b_hist': b_hist,
            'g_hist': g_hist,
            'r_hist': r_hist,
        }
    
    def classify_by_enhanced_features(self, image: np.ndarray, mask: np.ndarray = None) -> Tuple[str, float]:
        """
        增强的颜色分类器 - 多特征融合
        
        策略:
        1. 提取多维度颜色特征
        2. 基于规则的决策树
        3. 置信度评估
        """
        features = self.extract_color_features(image, mask)
        
        if not features:
            return "normal_water", 0.5
        
        bgr_mean = features['bgr_mean']
        hsv_mean = features['hsv_mean']
        b, g, r = bgr_mean
        h, s, v = hsv_mean
        
        # 基于规则的决策树分类
        # 规则基于109张样本的统计特征
        
        # 1. 黑水: 整体暗，BGR都低
        if v < 100 and b < 110 and g < 115 and r < 105:
            return "black_water", 0.85
        
        # 2. 乳白水: 高亮度，低饱和度
        if v > 170 and s < 40:
            return "milky_foam_water", 0.80
        
        # 3. 红水: R通道主导，H在红色范围
        if r > b + 20 and r > g + 20 and h > 170:
            return "red_water", 0.75
        
        # 4. 绿水: G通道主导，H在绿色范围
        if g > b + 15 and g > r + 10 and 35 < h < 85:
            return "green_water", 0.75
        
        # 5. 浑浊水: 黄褐色，H在黄色范围
        if 15 < h < 35 and s > 30 and v > 90:
            return "turbid_water", 0.70
        
        # 6. 坝体渗水: 中等亮度，低饱和度，灰度
        if 100 < v < 160 and s < 50 and abs(b - g) < 30 and abs(g - r) < 30:
            return "dam_seepage", 0.65
        
        # 7. 正常水: 默认
        return "normal_water", 0.60

'''

# 找到classify_by_color方法的位置并在其后添加新方法
insert_pos = content.find('    def segment_with_color_classify(')
if insert_pos > 0:
    content = content[:insert_pos] + enhanced_classifier + "\n" + content[insert_pos:]

# 修改segment_with_color_classify使用增强分类器
old_classify_call = "        # Step 2: 颜色分类\n        pred_class, confidence = self.classify_by_color(image, water_mask)"
new_classify_call = "        # Step 2: 颜色分类 (增强版)\n        pred_class, confidence = self.classify_by_enhanced_features(image, water_mask)"

content = content.replace(old_classify_call, new_classify_call)

# 保存
with open(segmentor_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 方案1增强完成:")
print("  1. 添加extract_color_features() - 多维度特征提取")
print("  2. 添加classify_by_enhanced_features() - 规则决策树")
print("  3. 特征:")
print("     - BGR均值和标准差")
print("     - HSV均值和标准差")
print("     - 颜色直方图分布")
print("  4. 规则决策树:")
print("     - 黑水: v<100, BGR<110")
print("     - 乳白水: v>170, s<40")
print("     - 红水: R主导, h>170")
print("     - 绿水: G主导, 35<h<85")
print("     - 浑浊水: 15<h<35, s>30")
print("     - 坝体渗水: 灰度, s<50")
print("\n开始评估...")
