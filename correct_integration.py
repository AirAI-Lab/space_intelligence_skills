#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
正确集成轻量化分类器到segmentor
"""

segmentor_path = '/app/water_inspection/models/open_vocab/core/segmentor.py'

with open(segmentor_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在WaterQualitySegmentor的__init__末尾添加分类器加载
old_init_end = '''        # 初始化文本分类器
        self.text_classifier = TextClassifier(
            backbone=self.backbone,
            siglip2_dir=siglip2_dir,
            device=device,
            temperature=self.temperature,
            negative_weight=self.negative_weight,
        )'''

new_init_end = '''        # 初始化文本分类器
        self.text_classifier = TextClassifier(
            backbone=self.backbone,
            siglip2_dir=siglip2_dir,
            device=device,
            temperature=self.temperature,
            negative_weight=self.negative_weight,
        )
        
        # 加载轻量化分类器 (方案3)
        self._load_lightweight_classifier()'''

content = content.replace(old_init_end, new_init_end)

# 添加_load_lightweight_classifier方法
insert_code = '''
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
'''

# 在segment方法之前插入
insert_pos = content.find('    def segment(')
if insert_pos > 0:
    content = content[:insert_pos] + insert_code + "\n" + content[insert_pos:]

# 修改segment_with_color_classify使用轻量分类器
old_classify = "        # Step 2: 颜色分类 (增强版)\n        pred_class, confidence = self.classify_by_enhanced_features(image, water_mask)"
new_classify = "        # Step 2: 轻量化分类器 (方案3)\n        pred_class, confidence = self.classify_by_lightweight_clf(image, water_mask)"

content = content.replace(old_classify, new_classify)

# 保存
with open(segmentor_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 轻量化分类器正确集成完成:")
print("  1. 在__init__末尾添加加载逻辑")
print("  2. 添加_load_lightweight_classifier()方法")
print("  3. segment_with_color_classify使用轻量分类器")
