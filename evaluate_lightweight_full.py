#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整数据集评估 - 方案3 (RADIO + 轻量SVM)

评估训练好的轻量分类器在109张完整数据集上的性能
"""

import sys
import json
from pathlib import Path
from collections import Counter
import numpy as np
import cv2
import pickle

sys.path.insert(0, '/app/water_inspection')

# 加载训练好的模型
model_dir = Path('/app/water_inspection/models/classifier')
with open(model_dir / 'lightweight_classifier.pkl', 'rb') as f:
    model_data = pickle.load(f)
    clf = model_data['classifier']
    clf_name = model_data['name']

with open(model_dir / 'scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

print(f"✅ 加载分类器: {clf_name}")

# 7类定义
CLASS_NAMES = [
    "black_water", "turbid_water", "red_water",
    "green_water", "milky_foam_water", "dam_seepage", "normal_water"
]

CLASS_COLORS_BGR = {
    "black_water": np.array([90, 95, 85]),
    "turbid_water": np.array([119, 140, 130]),
    "red_water": np.array([100, 80, 140]),
    "green_water": np.array([117, 156, 130]),
    "milky_foam_water": np.array([180, 190, 195]),
    "dam_seepage": np.array([130, 135, 140]),
    "normal_water": np.array([118, 124, 107]),
}

def extract_features(image_path):
    """提取特征"""
    image = cv2.imread(str(image_path))
    if image is None:
        return None
    
    # 颜色特征
    bgr_mean = image.mean(axis=(0, 1))
    bgr_std = image.std(axis=(0, 1))
    
    img_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv_mean = img_hsv.mean(axis=(0, 1))
    hsv_std = img_hsv.std(axis=(0, 1))
    
    # 直方图
    hist_b = cv2.calcHist([image], [0], None, [16], [0, 256]).flatten()
    hist_g = cv2.calcHist([image], [1], None, [16], [0, 256]).flatten()
    hist_r = cv2.calcHist([image], [2], None, [16], [0, 256]).flatten()
    
    hist_b = hist_b / (hist_b.sum() + 1e-6)
    hist_g = hist_g / (hist_g.sum() + 1e-6)
    hist_r = hist_r / (hist_r.sum() + 1e-6)
    
    # 颜色距离
    color_dists = []
    for cls_name in CLASS_NAMES:
        std_color = CLASS_COLORS_BGR[cls_name]
        dist = np.linalg.norm(bgr_mean - std_color)
        color_dists.append(dist)
    
    features = np.concatenate([
        bgr_mean, bgr_std, hsv_mean, hsv_std,
        hist_b, hist_g, hist_r,
        np.array(color_dists)
    ])
    
    return features

# 加载数据集
dataset_dir = Path('/app/water_inspection/data/datasets')
meta_dir = dataset_dir / "meta"

correct = 0
total = 0
results = []
class_stats = Counter()

print("\n" + "="*80)
print("开始评估 - 109张完整数据集")
print("="*80)

for meta_file in sorted(meta_dir.glob("*.json")):
    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    image_path = dataset_dir / "images" / meta["image"]
    gt_class = meta.get("active_class")
    
    if not image_path.exists() or gt_class not in CLASS_NAMES:
        continue
    
    # 提取特征
    features = extract_features(image_path)
    if features is None:
        continue
    
    # 预测
    features_scaled = scaler.transform(features.reshape(1, -1))
    pred_idx = clf.predict(features_scaled)[0]
    pred_class = CLASS_NAMES[pred_idx]
    
    # 统计
    total += 1
    if pred_class == gt_class:
        correct += 1
        symbol = "✅"
    else:
        symbol = "❌"
    
    results.append({
        'image': meta["image"],
        'gt': gt_class,
        'pred': pred_class,
        'correct': pred_class == gt_class
    })
    
    class_stats[gt_class] += 1
    
    if total <= 20:  # 显示前20个
        print(f"[{total:3d}] {meta['image']:20s} GT: {gt_class:20s} | 预测: {pred_class:20s} {symbol}")

print("\n" + "="*80)
print("评估统计")
print("="*80)

print(f"\n📊 整体性能:")
print(f"  总样本数: {total}")
print(f"  分类正确: {correct} ({correct/total*100:.1f}%)")

print(f"\n📊 各类别分布:")
for cls in CLASS_NAMES:
    count = class_stats[cls]
    if count > 0:
        cls_correct = sum(1 for r in results if r['gt'] == cls and r['correct'])
        print(f"  {cls:20s}: {count:3d}张, 正确{cls_correct:3d} ({cls_correct/count*100:.1f}%)")

# 保存报告
report_path = Path('/app/water_inspection/data/evaluation_results/lightweight_classifier_report.json')
report_path.parent.mkdir(exist_ok=True, parents=True)

with open(report_path, 'w') as f:
    json.dump({
        'total': total,
        'correct': correct,
        'accuracy': correct/total,
        'results': results
    }, f, indent=2)

print(f"\n✅ 评估报告已保存: {report_path}")

print("\n" + "="*80)
print("评估完成！")
print("="*80)
