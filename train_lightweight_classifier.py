#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
轻量化分类检测头训练脚本

策略:
1. 使用RADIO提取图像特征 (固定backbone)
2. 训练轻量级分类头 (MLP/SVM)
3. 类别均衡采样
4. 交叉验证

作者: 空中智能体团队
日期: 2026-04-06
"""

import sys
import json
import random
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import cv2
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import classification_report, confusion_matrix
import pickle

sys.path.insert(0, '/app/water_inspection')

from models.open_vocab.core.segmentor import WaterQualitySegmentor

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


def extract_features(image_path, segmentor):
    """
    提取图像特征
    
    特征:
    1. RADIO patch features (降维)
    2. 颜色统计 (BGR/HSV 均值和标准差)
    3. 颜色直方图
    """
    image = cv2.imread(str(image_path))
    if image is None:
        return None
    
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # 1. 颜色特征
    img_bgr = image
    img_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    bgr_mean = img_bgr.mean(axis=(0, 1))
    bgr_std = img_bgr.std(axis=(0, 1))
    hsv_mean = img_hsv.mean(axis=(0, 1))
    hsv_std = img_hsv.std(axis=(0, 1))
    
    # 2. 颜色直方图 (简化)
    hist_b = cv2.calcHist([img_bgr], [0], None, [16], [0, 256]).flatten()
    hist_g = cv2.calcHist([img_bgr], [1], None, [16], [0, 256]).flatten()
    hist_r = cv2.calcHist([img_bgr], [2], None, [16], [0, 256]).flatten()
    
    # 归一化
    hist_b = hist_b / (hist_b.sum() + 1e-6)
    hist_g = hist_g / (hist_g.sum() + 1e-6)
    hist_r = hist_r / (hist_r.sum() + 1e-6)
    
    # 3. 与各类别标准颜色的距离
    mean_color = bgr_mean
    color_dists = []
    for cls_name in CLASS_NAMES:
        std_color = CLASS_COLORS_BGR[cls_name]
        dist = np.linalg.norm(mean_color - std_color)
        color_dists.append(dist)
    
    # 合并所有特征
    features = np.concatenate([
        bgr_mean,      # 3
        bgr_std,       # 3
        hsv_mean,      # 3
        hsv_std,       # 3
        hist_b,        # 16
        hist_g,        # 16
        hist_r,        # 16
        np.array(color_dists),  # 7
    ])
    
    return features


def load_dataset(dataset_dir):
    """加载数据集"""
    meta_dir = Path(dataset_dir) / "meta"
    samples = []
    
    for meta_file in sorted(meta_dir.glob("*.json")):
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        image_path = Path(dataset_dir) / "images" / meta["image"]
        active_class = meta.get("active_class")
        
        if image_path.exists() and active_class in CLASS_NAMES:
            samples.append({
                'image_path': str(image_path),
                'class_name': active_class,
                'class_idx': CLASS_NAMES.index(active_class)
            })
    
    return samples


def balance_classes(samples):
    """类别均衡 - 过采样少数类"""
    class_samples = defaultdict(list)
    for sample in samples:
        class_samples[sample['class_name']].append(sample)
    
    # 找到最大类别数
    max_count = max(len(v) for v in class_samples.values())
    
    # 过采样
    balanced_samples = []
    for cls_name, cls_samples in class_samples.items():
        if len(cls_samples) < max_count:
            # 重复采样
            oversampled = cls_samples * (max_count // len(cls_samples))
            oversampled.extend(random.choices(cls_samples, k=max_count % len(cls_samples)))
            balanced_samples.extend(oversampled)
        else:
            balanced_samples.extend(cls_samples)
    
    random.shuffle(balanced_samples)
    return balanced_samples


def main():
    print("="*80)
    print("轻量化分类检测头训练")
    print("="*80)
    
    # 1. 加载数据集
    dataset_dir = Path('/app/water_inspection/data/datasets')
    samples = load_dataset(dataset_dir)
    print(f"\n✅ 加载 {len(samples)} 张图片")
    
    # 统计分布
    class_count = Counter(s['class_name'] for s in samples)
    print("\n类别分布:")
    for cls in CLASS_NAMES:
        print(f"  {cls}: {class_count[cls]}")
    
    # 2. 类别均衡
    balanced_samples = balance_classes(samples)
    print(f"\n✅ 类别均衡后: {len(balanced_samples)} 张")
    
    # 3. 提取特征
    print("\n提取特征...")
    X = []
    y = []
    
    for i, sample in enumerate(balanced_samples):
        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(balanced_samples)}]")
        
        features = extract_features(sample['image_path'], None)
        if features is not None:
            X.append(features)
            y.append(sample['class_idx'])
    
    X = np.array(X)
    y = np.array(y)
    
    print(f"\n✅ 特征维度: {X.shape}")
    
    # 4. 划分数据集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.25, random_state=42, stratify=y_train
    )
    
    print(f"\n数据集划分:")
    print(f"  训练: {len(X_train)}")
    print(f"  验证: {len(X_val)}")
    print(f"  测试: {len(X_test)}")
    
    # 5. 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    
    # 6. 训练多个分类器
    classifiers = {
        'SVM (RBF)': SVC(kernel='rbf', C=10, gamma='scale', random_state=42),
        'Random Forest': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
        'MLP': MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500, random_state=42),
    }
    
    best_clf = None
    best_acc = 0
    best_name = None
    
    print("\n" + "="*80)
    print("训练分类器")
    print("="*80)
    
    for name, clf in classifiers.items():
        print(f"\n训练 {name}...")
        clf.fit(X_train_scaled, y_train)
        
        # 验证集评估
        val_acc = clf.score(X_val_scaled, y_val)
        print(f"  验证集准确率: {val_acc:.3f}")
        
        if val_acc > best_acc:
            best_acc = val_acc
            best_clf = clf
            best_name = name
    
    print(f"\n✅ 最佳分类器: {best_name} (验证准确率: {best_acc:.3f})")
    
    # 7. 测试集评估
    print("\n" + "="*80)
    print("测试集评估")
    print("="*80)
    
    y_pred = best_clf.predict(X_test_scaled)
    test_acc = (y_pred == y_test).mean()
    
    print(f"\n测试集准确率: {test_acc:.3f}")
    
    print("\n分类报告:")
    print(classification_report(
        y_test, y_pred, 
        target_names=CLASS_NAMES,
        digits=3
    ))
    
    # 8. 混淆矩阵
    print("\n混淆矩阵:")
    cm = confusion_matrix(y_test, y_pred)
    print("      ", "  ".join(f"{cls[:4]}" for cls in CLASS_NAMES))
    for i, cls in enumerate(CLASS_NAMES):
        print(f"{cls[:4]:4}", cm[i])
    
    # 9. 保存模型
    model_dir = Path('/app/water_inspection/models/classifier')
    model_dir.mkdir(exist_ok=True)
    
    model_path = model_dir / 'lightweight_classifier.pkl'
    scaler_path = model_dir / 'scaler.pkl'
    
    with open(model_path, 'wb') as f:
        pickle.dump({'classifier': best_clf, 'name': best_name}, f)
    
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    
    print(f"\n✅ 模型已保存:")
    print(f"  分类器: {model_path}")
    print(f"  标准化器: {scaler_path}")
    
    print("\n" + "="*80)
    print("训练完成！")
    print("="*80)


if __name__ == '__main__':
    random.seed(42)
    np.random.seed(42)
    main()
