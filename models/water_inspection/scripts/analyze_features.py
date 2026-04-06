#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
特征空间分析脚本

分析:
1. 文本嵌入相似度 - 各类别 prompt 之间的语义距离
2. 视觉特征相似度 - 不同水质图像的特征可分性
3. 诊断 normal_water 得分过高的问题

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

sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import cv2


def analyze_text_embeddings(segmentor, prompts_config):
    """分析文本嵌入相似度"""
    print("\n" + "=" * 70)
    print("文本嵌入相似度分析 - 各类别 prompt 之间的语义距离")
    print("=" * 70)

    class_embeddings = {}
    class_samples = {}

    for cls_name, cls_config in prompts_config.items():
        pos_prompts = cls_config.get("positive", [])
        if pos_prompts:
            texts = pos_prompts[:3]
            class_samples[cls_name] = texts
            with torch.no_grad():
                embeds = segmentor.encode_text(texts)
                avg_embed = embeds.mean(dim=0)
                avg_embed = avg_embed / avg_embed.norm()
                class_embeddings[cls_name] = avg_embed
            print(f"\n{cls_name}: {len(pos_prompts)} prompts")
            for t in texts:
                print(f"  - {t[:55]}...")

    # 计算类别间相似度矩阵
    print("\n" + "-" * 70)
    print("类别间语义相似度矩阵 (余弦相似度)")
    print("-" * 70)

    cls_names = list(class_embeddings.keys())
    n = len(cls_names)
    sim_matrix = torch.zeros(n, n)

    for i, name1 in enumerate(cls_names):
        for j, name2 in enumerate(cls_names):
            sim = torch.dot(class_embeddings[name1], class_embeddings[name2]).item()
            sim_matrix[i, j] = sim

    header = " " * 18 + " ".join([f"{n[:6]:>7}" for n in cls_names])
    print(header)
    print("-" * len(header))

    for i, name in enumerate(cls_names):
        row = f"{name[:16]:<16} "
        for j in range(n):
            marker = "*" if i == j else " "
            row += f"{sim_matrix[i,j].item():.3f}{marker} "
        print(row)

    return cls_names, sim_matrix


def analyze_visual_features(segmentor, dataset_dir):
    """分析视觉特征相似度"""
    print("\n" + "=" * 70)
    print("视觉特征分析 - 不同水质类别的特征可分性")
    print("=" * 70)

    meta_dir = Path(dataset_dir) / "meta"
    class_features = {}
    loaded_classes = set()

    for meta_file in sorted(meta_dir.glob("*.json"))[:50]:
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        gt_class = meta.get("active_class", "")
        if not gt_class or gt_class in loaded_classes:
            continue

        image_path = Path(dataset_dir) / "images" / meta["image"]
        if not image_path.exists():
            continue

        image = cv2.imread(str(image_path))
        if image is None:
            continue

        # 提取特征
        image_rgb = image[:, :, ::-1].copy()
        image_resized = cv2.resize(image_rgb, (segmentor.input_size, segmentor.input_size))
        image_tensor = torch.from_numpy(image_resized).permute(2, 0, 1).unsqueeze(0)
        image_tensor = image_tensor.float().div(255.0).to(segmentor.device)

        with torch.no_grad():
            result = segmentor.backbone.extract_features(image_tensor)
            features = result["features"]
            lang_features = segmentor.align_to_language_space(features)
            avg_feat = lang_features.mean(dim=1).squeeze()
            avg_feat = avg_feat / avg_feat.norm()
            class_features[gt_class] = avg_feat.cpu()
            loaded_classes.add(gt_class)

        print(f"  加载 {gt_class}: {meta['image']}")

        if len(class_features) >= 7:
            break

    # 计算特征相似度
    print("\n" + "-" * 70)
    print("视觉特征相似度矩阵 (RADIO + SigLIP2 adaptor)")
    print("-" * 70)

    cls_names = list(class_features.keys())
    n = len(cls_names)
    sim_matrix = torch.zeros(n, n)

    for i, name1 in enumerate(cls_names):
        for j, name2 in enumerate(cls_names):
            sim = torch.dot(class_features[name1], class_features[name2]).item()
            sim_matrix[i, j] = sim

    header = " " * 18 + " ".join([f"{n[:6]:>7}" for n in cls_names])
    print(header)
    print("-" * len(header))

    for i, name in enumerate(cls_names):
        row = f"{name[:16]:<16} "
        for j in range(n):
            marker = "*" if i == j else " "
            row += f"{sim_matrix[i,j].item():.3f}{marker} "
        print(row)

    # 分析视觉可分性
    print("\n各类别与其它类别的平均相似度:")
    for i, name in enumerate(cls_names):
        other_sims = [sim_matrix[i, j].item() for j in range(n) if j != i]
        avg_other = np.mean(other_sims)
        print(f"  {name}: {avg_other:.4f}")

    print("\n最相似的类别对 (最容易混淆):")
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((cls_names[i], cls_names[j], sim_matrix[i, j].item()))
    pairs.sort(key=lambda x: x[2], reverse=True)
    for n1, n2, sim in pairs[:5]:
        print(f"  {n1} <-> {n2}: {sim:.4f}")

    return cls_names, sim_matrix


def diagnose_normal_water_issue(segmentor, dataset_dir, classes_config, prompts_config):
    """诊断 normal_water 得分过高的问题"""
    print("\n" + "=" * 70)
    print("诊断 normal_water 得分过高问题")
    print("=" * 70)

    meta_dir = Path(dataset_dir) / "meta"

    # 找异常样本
    anomaly_samples = []
    normal_samples = []

    for meta_file in sorted(meta_dir.glob("*.json"))[:30]:
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        gt_class = meta.get("active_class", "")
        if not gt_class:
            continue

        image_path = Path(dataset_dir) / "images" / meta["image"]
        if not image_path.exists():
            continue

        meta["image_path"] = str(image_path)

        if gt_class == "normal_water":
            normal_samples.append(meta)
        else:
            anomaly_samples.append(meta)

    print(f"找到 {len(normal_samples)} 个 normal_water 样本")
    print(f"找到 {len(anomaly_samples)} 个异常样本")

    # 分析异常样本
    print("\n分析异常样本的得分分布:")
    print("-" * 70)

    anomaly_scores = defaultdict(list)

    for sample in anomaly_samples[:10]:
        image = cv2.imread(sample["image_path"])
        if image is None:
            continue

        # 计算热图
        heatmaps = segmentor.compute_patch_similarity(image, classes_config, prompts_config)

        # 获取各类别得分
        scores = {}
        for cls_name, hm in heatmaps.items():
            scores[cls_name] = float(hm.max())

        # 找最高得分类别
        best_cls = max(scores.keys(), key=lambda k: scores[k])
        normal_score = scores.get("normal_water", 0)
        gt_score = scores.get(sample["active_class"], 0)
        margin = gt_score - normal_score

        print(f"\n{sample['image']} (GT: {sample['active_class']})")
        print(f"  最高分: {best_cls} ({scores[best_cls]:.4f})")
        print(f"  normal_water: {normal_score:.4f}, GT类别: {gt_score:.4f}, margin: {margin:+.4f}")

        for cls_name in ["normal_water", sample["active_class"]]:
            if cls_name in scores:
                anomaly_scores[cls_name].append(scores[cls_name])

    # 统计
    print("\n" + "-" * 70)
    print("统计汇总:")
    print("-" * 70)

    normal_mean = np.mean(anomaly_scores.get("normal_water", [0]))
    print(f"异常图像上 normal_water 平均得分: {normal_mean:.4f}")

    for cls_name in anomaly_scores:
        if cls_name != "normal_water":
            cls_mean = np.mean(anomaly_scores[cls_name])
            print(f"异常图像上 {cls_name} 平均得分: {cls_mean:.4f}")

    print("\n结论:")
    print("  如果 normal_water 在异常图像上得分持续高于异常类别,")
    print("  说明文本提示词需要重新设计, 减少语义重叠。")


def main():
    print("=" * 70)
    print("RADSeg 特征空间诊断")
    print("=" * 70)

    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "water_inspection.yaml"
    prompts_path = project_root / "configs" / "prompts.yaml"
    dataset_dir = project_root / "data" / "datasets"

    # 加载配置
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with open(prompts_path, "r", encoding="utf-8") as f:
        full_prompts = yaml.safe_load(f)
    prompts_config = full_prompts.get("water_quality_detection", {})

    classes_config = config["cloud"]["radio"]["classes"]

    # 容器内路径
    radio_code_dir = "/app/models/NVlabs_RADIO"
    siglip2_dir = "/app/models/siglip2-giant-opt-patch16-384"
    checkpoint_path = "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"

    # 初始化模型
    from models.open_vocab.radseg_segmentor import RADSegWaterSegmentor

    segmentor = RADSegWaterSegmentor(
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

    # 1. 分析文本嵌入
    analyze_text_embeddings(segmentor, prompts_config)

    # 2. 分析视觉特征
    analyze_visual_features(segmentor, str(dataset_dir))

    # 3. 诊断 normal_water 问题
    diagnose_normal_water_issue(segmentor, str(dataset_dir), classes_config, prompts_config)


if __name__ == "__main__":
    main()
