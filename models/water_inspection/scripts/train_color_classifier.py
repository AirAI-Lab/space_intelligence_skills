#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
两阶段水质分割器训练和评估脚本

训练:
1. 从数据集提取颜色特征
2. 训练小型分类器

评估:
1. 阶段1: 水体提取 IoU
2. 阶段2: 水质分类准确率
3. 端到端性能

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import sys
import json
import yaml
import numpy as np
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import cv2


class WaterColorDataset(Dataset):
    """水质颜色特征数据集"""

    CLASS_NAMES = [
        "black_water",
        "turbid_water",
        "red_water",
        "green_water",
        "milky_foam_water",
        "dam_seepage",
    ]

    def __init__(self, samples: list, dataset_dir: str):
        self.samples = []
        self.dataset_dir = dataset_dir

        for sample in samples:
            gt_class = sample.get("active_class")
            if gt_class not in self.CLASS_NAMES:
                continue

            image_path = os.path.join(dataset_dir, "images", sample["image"])
            if not os.path.exists(image_path):
                continue

            self.samples.append({
                "image_path": image_path,
                "class_name": gt_class,
                "class_idx": self.CLASS_NAMES.index(gt_class),
            })

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]

        image = cv2.imread(sample["image_path"])
        if image is None:
            return None

        # 提取颜色特征
        features = self._extract_color_features(image)

        return {
            "features": torch.tensor(features, dtype=torch.float32),
            "label": sample["class_idx"],
            "class_name": sample["class_name"],
        }

    def _extract_color_features(self, image: np.ndarray) -> list:
        """提取整张图像的颜色特征"""
        h, w = image.shape[:2]

        # 中心裁剪
        cy, cx = h // 2, w // 2
        crop_size = min(h, w) // 3
        y1 = max(0, cy - crop_size)
        y2 = min(h, cy + crop_size)
        x1 = max(0, cx - crop_size)
        x2 = min(w, cx + crop_size)

        crop = image[y1:y2, x1:x2]
        pixels = crop.reshape(-1, 3).astype(np.float32)

        # 采样
        if len(pixels) > 1000:
            idx = np.random.choice(len(pixels), 1000, replace=False)
            pixels = pixels[idx]

        b_mean = pixels[:, 0].mean()
        g_mean = pixels[:, 1].mean()
        r_mean = pixels[:, 2].mean()
        brightness = (b_mean + g_mean + r_mean) / 3
        rgb_range = max(r_mean, g_mean, b_mean) - min(r_mean, g_mean, b_mean)

        return [
            b_mean / 255.0,
            g_mean / 255.0,
            r_mean / 255.0,
            brightness / 255.0,
            rgb_range / 255.0,
            (r_mean - g_mean) / 255.0,
            (r_mean - b_mean) / 255.0,
            (g_mean - b_mean) / 255.0,
            (g_mean - r_mean) / 255.0,
            (b_mean - r_mean) / 255.0,
            (b_mean - g_mean) / 255.0,
            rgb_range / max(r_mean, g_mean, b_mean, 1) if max(r_mean, g_mean, b_mean) > 0 else 0,
        ]


def collate_fn(batch):
    """过滤 None 样本"""
    batch = [b for b in batch if b is not None]
    if not batch:
        return None
    return {
        "features": torch.stack([b["features"] for b in batch]),
        "labels": torch.tensor([b["label"] for b in batch]),
        "class_names": [b["class_name"] for b in batch],
    }


def train_classifier(
    train_loader: DataLoader,
    val_loader: DataLoader,
    num_epochs: int = 50,
    lr: float = 0.001,
):
    """训练分类器"""
    from models.open_vocab.two_stage_segmentor import WaterColorClassifier

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = WaterColorClassifier(input_dim=12, hidden_dim=64, num_classes=6).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    best_acc = 0
    best_model_state = None

    print("训练颜色分类器...")
    print(f"  设备: {device}")
    print(f"  训练样本: {len(train_loader.dataset)}")
    print(f"  验证样本: {len(val_loader.dataset)}")

    for epoch in range(num_epochs):
        # 训练
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0

        for batch in train_loader:
            if batch is None:
                continue

            features = batch["features"].to(device)
            labels = batch["labels"].to(device)

            optimizer.zero_grad()
            outputs = model(features)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            _, predicted = outputs.max(1)
            train_total += labels.size(0)
            train_correct += predicted.eq(labels).sum().item()

        # 验证
        model.eval()
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for batch in val_loader:
                if batch is None:
                    continue

                features = batch["features"].to(device)
                labels = batch["labels"].to(device)

                outputs = model(features)
                _, predicted = outputs.max(1)
                val_total += labels.size(0)
                val_correct += predicted.eq(labels).sum().item()

        train_acc = train_correct / train_total if train_total > 0 else 0
        val_acc = val_correct / val_total if val_total > 0 else 0

        if val_acc > best_acc:
            best_acc = val_acc
            best_model_state = model.state_dict().copy()

        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1}: train_loss={train_loss:.4f}, train_acc={train_acc:.2%}, val_acc={val_acc:.2%}")

    # 恢复最佳模型
    model.load_state_dict(best_model_state)

    return model, best_acc


def evaluate_two_stage(
    segmentor,
    samples: list,
    dataset_dir: str,
):
    """评估两阶段分割器"""
    print("\n评估两阶段分割器...")
    print("-" * 60)

    results = {
        "water_extraction": {"iou": [], "precision": [], "recall": []},
        "water_classification": {"correct": 0, "total": 0, "per_class": defaultdict(lambda: {"correct": 0, "total": 0})},
        "end_to_end": {"correct": 0, "total": 0, "fp": 0, "fn": 0},
    }

    CLASS_NAMES = [
        "black_water", "turbid_water", "red_water",
        "green_water", "milky_foam_water", "dam_seepage",
    ]

    for sample in samples[:50]:
        gt_class = sample.get("active_class")
        if not gt_class:
            continue

        image_path = os.path.join(dataset_dir, "images", sample["image"])
        if not os.path.exists(image_path):
            continue

        image = cv2.imread(image_path)
        if image is None:
            continue

        # 获取 GT 水体掩码
        gt_mask = get_water_gt_mask(sample, dataset_dir)

        # 执行分割
        try:
            results_dict = segmentor.segment(image)

            if results_dict:
                pred_result = list(results_dict.values())[0]
                pred_class = pred_result.class_name
                pred_mask = pred_result.water_mask
            else:
                pred_class = None
                pred_mask = np.zeros(image.shape[:2], dtype=bool)

            # 评估水体提取
            if gt_mask is not None:
                iou = compute_iou(pred_mask, gt_mask)
                precision, recall = compute_precision_recall(pred_mask, gt_mask)
                results["water_extraction"]["iou"].append(iou)
                results["water_extraction"]["precision"].append(precision)
                results["water_extraction"]["recall"].append(recall)

            # 评估水质分类
            is_normal = (gt_class == "normal_water")

            if not is_normal:
                results["water_classification"]["total"] += 1
                results["water_classification"]["per_class"][gt_class]["total"] += 1

                if pred_class == gt_class:
                    results["water_classification"]["correct"] += 1
                    results["water_classification"]["per_class"][gt_class]["correct"] += 1

            # 端到端评估
            results["end_to_end"]["total"] += 1

            if is_normal:
                if pred_class is not None:
                    results["end_to_end"]["fp"] += 1
            else:
                if pred_class is None:
                    results["end_to_end"]["fn"] += 1
                elif pred_class == gt_class:
                    results["end_to_end"]["correct"] += 1

        except Exception as e:
            print(f"  ✗ {sample['image']}: {e}")
            continue

    # 打印结果
    print("\n阶段1: 水体提取")
    if results["water_extraction"]["iou"]:
        print(f"  IoU: {np.mean(results['water_extraction']['iou']):.3f}")
        print(f"  Precision: {np.mean(results['water_extraction']['precision']):.3f}")
        print(f"  Recall: {np.mean(results['water_extraction']['recall']):.3f}")

    print("\n阶段2: 水质分类")
    total = results["water_classification"]["total"]
    correct = results["water_classification"]["correct"]
    print(f"  准确率: {correct}/{total} = {correct/total:.2%}" if total > 0 else "  准确率: N/A")

    print("\n各类别准确率:")
    for cls_name in CLASS_NAMES:
        c = results["water_classification"]["per_class"][cls_name]["correct"]
        t = results["water_classification"]["per_class"][cls_name]["total"]
        if t > 0:
            print(f"  {cls_name}: {c}/{t} = {c/t:.2%}")

    print("\n端到端:")
    total = results["end_to_end"]["total"]
    correct = results["end_to_end"]["correct"]
    fp = results["end_to_end"]["fp"]
    fn = results["end_to_end"]["fn"]
    print(f"  正确: {correct}/{total} = {correct/total:.2%}" if total > 0 else "  正确: N/A")
    print(f"  误检 (normal→anomaly): {fp}")
    print(f"  漏检 (anomaly→none): {fn}")

    return results


def get_water_gt_mask(sample: dict, dataset_dir: str) -> np.ndarray:
    """获取水体 GT 掩码"""
    mask_dir = os.path.join(dataset_dir, "masks")
    image_path = os.path.join(dataset_dir, "images", sample["image"])

    image = cv2.imread(image_path)
    if image is None:
        return None
    h, w = image.shape[:2]

    water_mask = np.zeros((h, w), dtype=bool)

    for cls_info in sample.get("classes", []):
        mask_file = cls_info.get("mask_file")
        if mask_file:
            mask_path = os.path.join(mask_dir, mask_file)
            if os.path.exists(mask_path):
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                if mask is not None:
                    if mask.shape != (h, w):
                        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
                    water_mask = water_mask | (mask > 127)

    return water_mask


def compute_iou(mask1: np.ndarray, mask2: np.ndarray) -> float:
    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()
    return intersection / union if union > 0 else 1.0


def compute_precision_recall(pred: np.ndarray, gt: np.ndarray) -> Tuple[float, float]:
    tp = np.logical_and(pred, gt).sum()
    fp = np.logical_and(pred, ~gt).sum()
    fn = np.logical_and(~pred, gt).sum()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0

    return precision, recall


def main():
    print("=" * 70)
    print("两阶段水质分割器训练和评估")
    print("=" * 70)

    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "water_inspection.yaml"
    dataset_dir = project_root / "data" / "datasets"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 加载数据集
    meta_dir = Path(dataset_dir) / "meta"
    samples = []
    for meta_file in sorted(meta_dir.glob("*.json")):
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        samples.append(meta)

    print(f"\n数据集: {len(samples)} 样本")

    # 划分训练/验证集
    anomaly_samples = [s for s in samples if s.get("active_class") in WaterColorDataset.CLASS_NAMES]
    np.random.seed(42)
    np.random.shuffle(anomaly_samples)

    split = int(len(anomaly_samples) * 0.8)
    train_samples = anomaly_samples[:split]
    val_samples = anomaly_samples[split:]

    print(f"  训练集: {len(train_samples)} 异常样本")
    print(f"  验证集: {len(val_samples)} 异常样本")

    # 创建数据集
    train_dataset = WaterColorDataset(train_samples, str(dataset_dir))
    val_dataset = WaterColorDataset(val_samples, str(dataset_dir))

    train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_dataset, batch_size=8, shuffle=False, collate_fn=collate_fn)

    # 训练分类器
    print("\n" + "=" * 70)
    print("训练颜色分类器")
    print("=" * 70)

    classifier, best_val_acc = train_classifier(train_loader, val_loader, num_epochs=50)

    print(f"\n最佳验证准确率: {best_val_acc:.2%}")

    # 保存模型
    model_path = project_root / "checkpoints" / "water_color_classifier.pt"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(classifier.state_dict(), model_path)
    print(f"模型已保存: {model_path}")

    # 初始化 RADIO 分割器
    print("\n" + "=" * 70)
    print("初始化 RADIO 分割器")
    print("=" * 70)

    radio_code_dir = "/app/models/NVlabs_RADIO"
    siglip2_dir = "/app/models/siglip2-giant-opt-patch16-384"
    checkpoint_path = "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"

    from models.open_vocab.radseg_segmentor import RADSegWaterSegmentor

    radio_segmentor = RADSegWaterSegmentor(
        checkpoint_path=checkpoint_path,
        radio_code_dir=radio_code_dir,
        siglip2_dir=siglip2_dir,
        device="cuda",
        input_size=config["cloud"]["radio"]["inference"]["input_size"],
        config=config,
        use_scra=True,
        use_dino=False,
        use_sam=False,
    )

    # 创建两阶段分割器
    from models.open_vocab.two_stage_segmentor import TwoStageWaterSegmentor

    classes_config = config["cloud"]["radio"]["classes"]

    two_stage_segmentor = TwoStageWaterSegmentor(
        radio_segmentor=radio_segmentor,
        classes_config=classes_config,
        classifier=classifier,
        water_threshold=0.5,
    )

    # 评估
    print("\n" + "=" * 70)
    print("评估两阶段分割器")
    print("=" * 70)

    results = evaluate_two_stage(two_stage_segmentor, samples, str(dataset_dir))


if __name__ == "__main__":
    main()
