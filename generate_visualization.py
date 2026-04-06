#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成可视化评估结果

功能:
1. 在图片上绘制分割区域、类别、置信度、IoU
2. 保存到outputs目录
3. 生成完整评估报告

作者: 空中智能体团队
日期: 2026-04-06
"""

import sys
import json
import random
from pathlib import Path
from collections import Counter
import numpy as np
import cv2
import pickle
from datetime import datetime

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

# 7类定义和颜色
CLASS_NAMES = [
    "black_water", "turbid_water", "red_water",
    "green_water", "milky_foam_water", "dam_seepage", "normal_water"
]

CLASS_COLORS_BGR = {
    "black_water": (85, 95, 90),        # 深灰蓝
    "turbid_water": (130, 140, 119),    # 浑浊黄
    "red_water": (140, 80, 100),        # 红褐
    "green_water": (130, 156, 117),     # 绿色
    "milky_foam_water": (195, 190, 180),# 乳白
    "dam_seepage": (140, 135, 130),     # 灰色
    "normal_water": (107, 124, 118),    # 正常蓝
}

CLASS_COLORS_RGB = {k: (v[2], v[1], v[0]) for k, v in CLASS_COLORS_BGR.items()}

def extract_features(image):
    """提取特征"""
    bgr_mean = image.mean(axis=(0, 1))
    bgr_std = image.std(axis=(0, 1))
    
    img_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv_mean = img_hsv.mean(axis=(0, 1))
    hsv_std = img_hsv.std(axis=(0, 1))
    
    hist_b = cv2.calcHist([image], [0], None, [16], [0, 256]).flatten()
    hist_g = cv2.calcHist([image], [1], None, [16], [0, 256]).flatten()
    hist_r = cv2.calcHist([image], [2], None, [16], [0, 256]).flatten()
    
    hist_b = hist_b / (hist_b.sum() + 1e-6)
    hist_g = hist_g / (hist_g.sum() + 1e-6)
    hist_r = hist_r / (hist_r.sum() + 1e-6)
    
    color_dists = []
    for cls_name in CLASS_NAMES:
        std_color = np.array(CLASS_COLORS_BGR[cls_name])
        dist = np.linalg.norm(bgr_mean - std_color)
        color_dists.append(dist)
    
    features = np.concatenate([
        bgr_mean, bgr_std, hsv_mean, hsv_std,
        hist_b, hist_g, hist_r,
        np.array(color_dists)
    ])
    
    return features

def get_water_mask(image):
    """简单水体分割（基于颜色）"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 水体范围（H: 80-120, S: 30-255, V: 50-200）
    lower = np.array([70, 20, 40])
    upper = np.array([130, 255, 220])
    mask = cv2.inRange(hsv, lower, upper)
    
    # 形态学操作
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    
    return mask

def calculate_iou(mask1, mask2):
    """计算IoU"""
    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()
    return intersection / (union + 1e-6)

def visualize_result(image, gt_class, pred_class, confidence, iou, mask):
    """生成可视化结果"""
    h, w = image.shape[:2]
    
    # 复制图像
    vis = image.copy()
    
    # 绘制分割区域（半透明）
    overlay = vis.copy()
    pred_color = CLASS_COLORS_BGR[pred_class]
    overlay[mask > 0] = pred_color
    cv2.addWeighted(overlay, 0.3, vis, 0.7, 0, vis)
    
    # 绘制分割轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(vis, contours, -1, pred_color, 2)
    
    # 绘制信息面板
    panel_height = 120
    panel = np.zeros((panel_height, w, 3), dtype=np.uint8) + 40
    vis = np.vstack([vis, panel])
    
    # 文本信息
    y_offset = h + 30
    
    # GT标签
    gt_color = (0, 255, 0) if gt_class == pred_class else (0, 0, 255)
    cv2.putText(vis, f"GT: {gt_class}", (10, y_offset), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, gt_color, 2)
    
    # 预测标签
    pred_color_rgb = CLASS_COLORS_RGB[pred_class]
    cv2.putText(vis, f"Pred: {pred_class}", (10, y_offset + 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, pred_color_rgb, 2)
    
    # 置信度
    cv2.putText(vis, f"Confidence: {confidence:.1%}", (10, y_offset + 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # IoU
    iou_color = (0, 255, 0) if iou > 0.5 else (255, 255, 0) if iou > 0.3 else (0, 0, 255)
    cv2.putText(vis, f"IoU: {iou:.1%}", (10, y_offset + 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, iou_color, 2)
    
    # 结果标记
    result = "✓ CORRECT" if gt_class == pred_class else "✗ WRONG"
    result_color = (0, 255, 0) if gt_class == pred_class else (0, 0, 255)
    cv2.putText(vis, result, (w - 200, y_offset + 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, result_color, 3)
    
    return vis

# 加载数据集
dataset_dir = Path('/app/water_inspection/data/datasets')
meta_dir = dataset_dir / "meta"
output_dir = Path('/app/water_inspection/outputs/lightweight_classifier_vis')
output_dir.mkdir(exist_ok=True, parents=True)

# 加载GT mask目录
mask_dir = dataset_dir / "masks"

results = []
correct = 0
total = 0

print("\n" + "="*80)
print("生成可视化评估结果")
print("="*80)

for meta_file in sorted(meta_dir.glob("*.json")):
    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    image_path = dataset_dir / "images" / meta["image"]
    gt_class = meta.get("active_class")
    
    if not image_path.exists() or gt_class not in CLASS_NAMES:
        continue
    
    # 读取图像
    image = cv2.imread(str(image_path))
    if image is None:
        continue
    
    # 提取特征并预测
    features = extract_features(image)
    features_scaled = scaler.transform(features.reshape(1, -1))
    pred_idx = clf.predict(features_scaled)[0]
    pred_class = CLASS_NAMES[pred_idx]
    
    # 获取置信度
    if hasattr(clf, 'predict_proba'):
        proba = clf.predict_proba(features_scaled)[0]
        confidence = proba[pred_idx]
    elif hasattr(clf, 'decision_function'):
        from scipy.special import softmax
        decision = clf.decision_function(features_scaled)[0]
        proba = softmax(decision)
        confidence = proba[pred_idx]
    else:
        confidence = 0.85
    
    # 获取水体分割mask
    pred_mask = get_water_mask(image)
    
    # 加载GT mask
    gt_mask = np.zeros(image.shape[:2], dtype=np.uint8)
    for cls_info in meta.get("classes", []):
        mask_file = cls_info.get("mask_file")
        if mask_file:
            mask_path = mask_dir / mask_file
            if mask_path.exists():
                mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                if mask is not None:
                    gt_mask = np.maximum(gt_mask, mask)
    
    # 计算IoU
    iou = calculate_iou(pred_mask, gt_mask)
    
    # 生成可视化
    vis = visualize_result(image, gt_class, pred_class, confidence, iou, pred_mask)
    
    # 保存
    output_name = f"{meta['image'].rsplit('.', 1)[0]}_gt-{gt_class}_pred-{pred_class}.jpg"
    output_path = output_dir / output_name
    cv2.imwrite(str(output_path), vis, [cv2.IMWRITE_JPEG_QUALITY, 95])
    
    # 统计
    total += 1
    is_correct = (gt_class == pred_class)
    if is_correct:
        correct += 1
    
    results.append({
        'image': meta["image"],
        'gt': gt_class,
        'pred': pred_class,
        'confidence': float(confidence),
        'iou': float(iou),
        'correct': is_correct
    })
    
    if total <= 10:
        symbol = "✅" if is_correct else "❌"
        print(f"[{total:3d}] {meta['image']:20s} GT: {gt_class:20s} | Pred: {pred_class:20s} {symbol}")

print(f"\n✅ 生成 {total} 张可视化图片")
print(f"   保存位置: {output_dir}")

# 生成评估报告
report = {
    'timestamp': datetime.now().isoformat(),
    'total_samples': total,
    'correct': correct,
    'accuracy': correct / total,
    'classifier': clf_name,
    'class_stats': {},
    'results': results
}

# 各类别统计
for cls in CLASS_NAMES:
    cls_results = [r for r in results if r['gt'] == cls]
    if cls_results:
        cls_correct = sum(1 for r in cls_results if r['correct'])
        report['class_stats'][cls] = {
            'total': len(cls_results),
            'correct': cls_correct,
            'accuracy': cls_correct / len(cls_results)
        }

# 保存报告
report_path = output_dir / 'visualization_report.json'
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f"\n📊 整体性能:")
print(f"  总样本数: {total}")
print(f"  分类正确: {correct} ({correct/total*100:.1f}%)")
print(f"\n✅ 可视化报告已保存: {report_path}")

# 随机选择3张图片（包含正确和错误的样本）
random.seed(42)
correct_samples = [r for r in results if r['correct']]
wrong_samples = [r for r in results if not r['correct']]

selected = []
if correct_samples:
    selected.extend(random.sample(correct_samples, min(2, len(correct_samples))))
if wrong_samples:
    selected.extend(random.sample(wrong_samples, min(1, len(wrong_samples))))

print(f"\n📸 随机选择3张图片用于展示:")
for i, r in enumerate(selected[:3], 1):
    output_name = f"{r['image'].rsplit('.', 1)[0]}_gt-{r['gt']}_pred-{r['pred']}.jpg"
    print(f"  {i}. {output_name}")
    print(f"     GT: {r['gt']}, Pred: {r['pred']}, Conf: {r['confidence']:.1%}, IoU: {r['iou']:.1%}")

print("\n" + "="*80)
print("可视化生成完成！")
print("="*80)
