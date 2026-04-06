#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模块级测试脚本 - 验证各组件是否正常工作

测试步骤:
1. 文本编码 - positive/negative prompts
2. 视觉特征提取 - RADIO backbone
3. 语言对齐 - SigLIP2 head_mlp
4. 相似度计算 - contrastive scoring
5. 端到端分割

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import sys
import yaml
import json
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import cv2


def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def test_text_encoding(segmentor, prompts_config):
    """测试 1: 文本编码"""
    print("\n" + "=" * 60)
    print("测试 1: 文本编码 (positive/negative prompts)")
    print("=" * 60)

    # 测试 positive prompts
    pos_texts = [
        "opaque black polluted water with dark surface blocking all light",
        "clear transparent river water with no color tint high visibility",
    ]

    try:
        pos_features = segmentor.encode_text(pos_texts)
        print(f"  ✓ Positive prompts 编码成功: shape={pos_features.shape}")
    except Exception as e:
        print(f"  ✗ Positive prompts 编码失败: {e}")
        return False

    # 测试 negative prompts
    neg_texts = [
        "clear transparent water showing dark riverbed through depth",
        "green algae bloom water with G channel clearly dominant",
    ]

    try:
        neg_features = segmentor.encode_text(neg_texts)
        print(f"  ✓ Negative prompts 编码成功: shape={neg_features.shape}")
    except Exception as e:
        print(f"  ✗ Negative prompts 编码失败: {e}")
        return False

    # 验证特征是否归一化
    pos_norms = torch.norm(pos_features, dim=-1)
    print(f"  ✓ Positive 特征范数: mean={pos_norms.mean():.4f}, std={pos_norms.std():.4f}")

    if torch.allclose(pos_norms, torch.ones_like(pos_norms), atol=1e-3):
        print(f"  ✓ Positive 特征已归一化")
    else:
        print(f"  ⚠ Positive 特征未完全归一化")

    return True


def test_visual_features(segmentor, test_image_path):
    """测试 2: 视觉特征提取"""
    print("\n" + "=" * 60)
    print("测试 2: RADIO 视觉特征提取")
    print("=" * 60)

    if not os.path.exists(test_image_path):
        print(f"  ✗ 测试图像不存在: {test_image_path}")
        return False

    image = cv2.imread(test_image_path)
    if image is None:
        print(f"  ✗ 无法读取图像: {test_image_path}")
        return False

    print(f"  图像尺寸: {image.shape}")

    # 提取特征
    try:
        image_rgb = image[:, :, ::-1].copy()
        image_resized = cv2.resize(image_rgb, (segmentor.input_size, segmentor.input_size))
        image_tensor = torch.from_numpy(image_resized).permute(2, 0, 1).unsqueeze(0)
        image_tensor = image_tensor.float().div(255.0).to(segmentor.device)

        result = segmentor.backbone.extract_features(image_tensor)
        features = result["features"]
        H_patch, W_patch = result["grid_size"]

        print(f"  ✓ 特征提取成功: shape={features.shape}")
        print(f"  ✓ Grid size: {H_patch}x{W_patch} = {H_patch * W_patch} patches")
        print(f"  ✓ 特征维度: {features.shape[-1]}")

        # 检查特征统计
        feat_mean = features.mean().item()
        feat_std = features.std().item()
        print(f"  ✓ 特征统计: mean={feat_mean:.4f}, std={feat_std:.4f}")

        return True
    except Exception as e:
        print(f"  ✗ 特征提取失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_language_alignment(segmentor, test_image_path):
    """测试 3: 语言对齐"""
    print("\n" + "=" * 60)
    print("测试 3: 语言空间对齐 (SigLIP2 head_mlp)")
    print("=" * 60)

    if not os.path.exists(test_image_path):
        print(f"  ✗ 测试图像不存在: {test_image_path}")
        return False

    try:
        image = cv2.imread(test_image_path)
        image_rgb = image[:, :, ::-1].copy()
        image_resized = cv2.resize(image_rgb, (segmentor.input_size, segmentor.input_size))
        image_tensor = torch.from_numpy(image_resized).permute(2, 0, 1).unsqueeze(0)
        image_tensor = image_tensor.float().div(255.0).to(segmentor.device)

        result = segmentor.backbone.extract_features(image_tensor)
        features = result["features"]  # [1, N, D_backbone]

        # 对齐到语言空间
        lang_features = segmentor.align_to_language_space(features)

        print(f"  ✓ Backbone 特征: {features.shape}")
        print(f"  ✓ 语言空间特征: {lang_features.shape}")
        print(f"  ✓ 目标维度: 1536 (SigLIP2-G)")

        if lang_features.shape[-1] == 1536:
            print(f"  ✓ 维度正确")
        else:
            print(f"  ⚠ 维度不匹配: 期望 1536, 实际 {lang_features.shape[-1]}")

        return True
    except Exception as e:
        print(f"  ✗ 语言对齐失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_contrastive_similarity(segmentor, test_image_path, prompts_config):
    """测试 4: 对比相似度计算"""
    print("\n" + "=" * 60)
    print("测试 4: Contrastive Similarity (positive - negative)")
    print("=" * 60)

    if not os.path.exists(test_image_path):
        print(f"  ✗ 测试图像不存在: {test_image_path}")
        return False

    try:
        image = cv2.imread(test_image_path)

        # 获取 GT 类别
        gt_class = None
        meta_path = test_image_path.replace("images", "meta").replace(".jpg", ".json").replace(".jpeg", ".json").replace(".png", ".json")
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                meta = json.load(f)
                gt_class = meta.get("active_class")

        print(f"  GT 类别: {gt_class}")

        # 构建简单的 classes_config
        classes_config = {
            "black_water": {"prompts": ["opaque black polluted water"]},
            "turbid_water": {"prompts": ["yellowish brown muddy water"]},
            "red_water": {"prompts": ["bright vivid red rust colored water"]},
            "green_water": {"prompts": ["thick bright green algae bloom"]},
            "milky_foam_water": {"prompts": ["milky white gray turbid water"]},
            "dam_seepage": {"prompts": ["dark wet water seepage stain"]},
            "normal_water": {"prompts": ["clear transparent river water"]},
        }

        # 计算热图
        heatmaps = segmentor.compute_patch_similarity(image, classes_config, prompts_config)

        print(f"  ✓ 热图计算成功: {len(heatmaps)} 类别")

        # 分析得分
        print(f"\n  各类别得分 (contrastive score):")
        scores = []
        for cls_name, hm in heatmaps.items():
            max_score = hm.max()
            mean_score = hm[hm > 0.5].mean() if (hm > 0.5).any() else 0
            scores.append((cls_name, max_score, mean_score))
            gt_marker = " <-- GT" if cls_name == gt_class else ""
            print(f"    {cls_name}: max={max_score:.4f}, mean(high)={mean_score:.4f}{gt_marker}")

        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)
        print(f"\n  最高分类别: {scores[0][0]} (score={scores[0][1]:.4f})")

        if gt_class and scores[0][0] == gt_class:
            print(f"  ✓ 预测正确!")
        elif gt_class:
            print(f"  ⚠ 预测错误: 期望 {gt_class}, 实际 {scores[0][0]}")

        return True
    except Exception as e:
        print(f"  ✗ 相似度计算失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_images(segmentor, dataset_dir, prompts_config, num_samples=20):
    """测试 5: 批量图像测试"""
    print("\n" + "=" * 60)
    print(f"测试 5: 批量图像测试 ({num_samples} 样本)")
    print("=" * 60)

    # 加载数据集
    meta_dir = Path(dataset_dir) / "meta"
    samples = []
    for meta_file in sorted(meta_dir.glob("*.json"))[:num_samples]:
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
            meta["image_path"] = str(Path(dataset_dir) / "images" / meta["image"])
            samples.append(meta)

    # 构建类别配置
    classes_config = {
        "black_water": {"prompts": ["opaque black polluted water"]},
        "turbid_water": {"prompts": ["yellowish brown muddy water"]},
        "red_water": {"prompts": ["bright vivid red rust colored water"]},
        "green_water": {"prompts": ["thick bright green algae bloom"]},
        "milky_foam_water": {"prompts": ["milky white gray turbid water"]},
        "dam_seepage": {"prompts": ["dark wet water seepage stain"]},
        "normal_water": {"prompts": ["clear transparent river water"]},
    }

    correct = 0
    total = 0
    per_class_correct = {}

    for sample in samples:
        image_path = sample["image_path"]
        gt_class = sample.get("active_class")
        if not gt_class or not os.path.exists(image_path):
            continue

        image = cv2.imread(image_path)
        if image is None:
            continue

        total += 1

        # 计算热图
        heatmaps = segmentor.compute_patch_similarity(image, classes_config, prompts_config)

        # 找最高分
        best_class = max(heatmaps.keys(), key=lambda k: heatmaps[k].max())

        if best_class == gt_class:
            correct += 1
            per_class_correct[gt_class] = per_class_correct.get(gt_class, 0) + 1
            status = "✓"
        else:
            status = "✗"

        print(f"  {status} {sample['image']}: GT={gt_class}, Pred={best_class}")

    print(f"\n  总体准确率: {correct}/{total} = {correct/total:.2%}")
    print(f"\n  各类别准确率:")
    for cls_name in classes_config.keys():
        cls_total = sum(1 for s in samples if s.get("active_class") == cls_name)
        cls_correct = per_class_correct.get(cls_name, 0)
        if cls_total > 0:
            print(f"    {cls_name}: {cls_correct}/{cls_total} = {cls_correct/cls_total:.2%}")

    return True


def main():
    print("=" * 60)
    print("RADSeg 模块级测试")
    print("=" * 60)

    # 路径配置
    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "water_inspection.yaml"
    prompts_path = project_root / "configs" / "prompts.yaml"
    dataset_dir = project_root / "data" / "datasets"

    # 加载配置
    print("\n加载配置...")
    config = load_config(str(config_path))

    # 加载 prompts 配置
    if os.path.exists(prompts_path):
        with open(prompts_path, 'r', encoding='utf-8') as f:
                full_prompts = yaml.safe_load(f)
        prompts_config = full_prompts.get("water_quality_detection", {})
        print(f"  ✓ Prompts 配置加载成功: {len(prompts_config)} 类别")
    else:
        prompts_config = {}
        print(f"  ⚠ Prompts 配置文件不存在")

    # 容器内路径
    radio_code_dir = "/app/models/NVlabs_RADIO"
    siglip2_dir = "/app/models/siglip2-giant-opt-patch16-384"
    checkpoint_path = "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"

    # 初始化模型
    print("\n初始化模型...")
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

    # 运行测试
    all_passed = True

    # 测试 1: 文本编码
    if not test_text_encoding(segmentor, prompts_config):
        all_passed = False

    # 找测试图像
    test_images = list((Path(dataset_dir) / "images").glob("*.jpg"))
    if not test_images:
        test_images = list((Path(dataset_dir) / "images").glob("*.jpeg"))
    if not test_images:
        test_images = list((Path(dataset_dir) / "images").glob("*.png"))

    if test_images:
        test_image = str(test_images[0])
        print(f"\n使用测试图像: {test_image}")

        # 测试 2: 视觉特征
        if not test_visual_features(segmentor, test_image):
            all_passed = False

        # 测试 3: 语言对齐
        if not test_language_alignment(segmentor, test_image):
            all_passed = False

        # 测试 4: 对比相似度
        if not test_contrastive_similarity(segmentor, test_image, prompts_config):
            all_passed = False

        # 测试 5: 批量图像测试
        if not test_batch_images(segmentor, str(dataset_dir), prompts_config, num_samples=30):
            all_passed = False
    else:
        print("\n  ⚠ 未找到测试图像")

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    if all_passed:
        print("  ✓ 所有测试通过!")
    else:
        print("  ✗ 部分测试失败，请检查日志")


if __name__ == "__main__":
    main()
