#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
v4.1 综合诊断分析 - 集成Patch分类 + 颜色校验
"""

import sys
import yaml
import json
import cv2
import numpy as np
from pathlib import Path

# 设置路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_v41_diagnosis():
    # 加载配置
    config_path = Path(__file__).parent.parent / "configs" / "water_inspection.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    ckpt = "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"
    radio = "/app/models/NVlabs_RADIO"
    siglip = "/app/models/siglip2-giant-opt-patch16-384"

    from models.open_vocab.radio_segmentor import WaterQualitySegmentor

    print("=" * 80)
    print("v4.1 综合诊断分析 - Patch分类 + 颜色校验")
    print("=" * 80)

    # 初始化分割器
    print("\n初始化模型...")
    segmentor = WaterQualitySegmentor(
        checkpoint_path=ckpt,
        radio_code_dir=radio,
        siglip2_dir=siglip,
        device="cuda",
        config=config,
    )
    print("OK\n")

    # 数据集路径
    data_dir = Path(__file__).parent.parent / "data" / "datasets"
    images_dir = data_dir / "images"
    masks_dir = data_dir / "masks"
    meta_dir = data_dir / "meta"
    output_dir = Path(__file__).parent.parent / "data" / "diagnosis"
    output_dir.mkdir(parents=True, exist_ok=True)

    classes_config = config.get("cloud", {}).get("radio", {}).get("classes", {})

    # 诊断结果
    diagnosis_results = []

    images = sorted(list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.jpeg")) + list(images_dir.glob("*.png")))

    for img_path in images:
        # 加载图像
        image = cv2.imread(str(img_path))
        if image is None:
            continue

        h, w = image.shape[:2]

        # 加载 meta
        meta_path = meta_dir / f"{img_path.stem}.json"
        if not meta_path.exists():
            continue

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        gt_class = meta.get("active_class")
        if not gt_class:
            continue

        # ━━━ 第1步: SigLIP2 文本对齐 ━━━
        full_image_probs = segmentor.classify_image(image, classes_config)

        # 加载 GT mask
        gt_mask_file = None
        for cls_info in meta.get("classes", []):
            if cls_info.get("class") == gt_class:
                gt_mask_file = cls_info.get("mask_file")
                break

        gt_mean_bgr = None
        gt_mask_bool = None

        if gt_mask_file:
            mask_path = masks_dir / gt_mask_file
            if mask_path.exists():
                gt_mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                if gt_mask is not None:
                    if gt_mask.shape != (h, w):
                        gt_mask = cv2.resize(gt_mask, (w, h), interpolation=cv2.INTER_NEAREST)

                    gt_mask_bool = gt_mask > 127
                    if gt_mask_bool.any():
                        gt_pixels = image[gt_mask_bool].astype(np.float32)
                        gt_mean_bgr = gt_pixels.mean(axis=0).tolist()

        # ━━━ 第2步: Patch分类 (v4.1) ━━━
        class_heatmaps = segmentor.compute_patch_similarity(image, classes_config)

        best_patch_overlap = 0.0
        if class_heatmaps and gt_class in class_heatmaps and gt_mask_bool is not None:
            gt_heatmap = class_heatmaps[gt_class]
            high_conf_mask = gt_heatmap > 0.3

            if high_conf_mask.any():
                intersection = (high_conf_mask & gt_mask_bool).sum()
                union = (high_conf_mask | gt_mask_bool).sum()
                if union > 0:
                    best_patch_overlap = intersection / union

        # ━━━ 第3步: 颜色校验 (v4.1) ━━━
        color_validation_ok = True
        color_adjusted_score = 0.0

        if gt_mean_bgr is not None:
            # 获取GT类别的基础得分
            base_score = full_image_probs.get(gt_class, 0.0)

            # 应用颜色校验
            is_valid, adjusted_prob = segmentor._validate_color_consistency(
                gt_class,
                base_score,
                gt_mean_bgr,
                classes_config
            )
            color_validation_ok = is_valid
            color_adjusted_score = adjusted_prob

        # ━━━ 综合判断 ━━━
        align_ok = full_image_probs.get(gt_class, 0.0) > 0.5
        seg_ok = best_patch_overlap > 0.4

        # 如果颜色校验失败，降低对齐判定
        if not color_validation_ok:
            align_ok = False

        both_ok = align_ok and seg_ok

        diagnosis_results.append({
            "image": img_path.name,
            "gt_class": gt_class,
            "align_ok": bool(align_ok),
            "seg_ok": bool(seg_ok),
            "both_ok": bool(both_ok),
            "patch_overlap": float(best_patch_overlap),
            "color_ok": bool(color_validation_ok),
            "color_score": float(color_adjusted_score),
            "gt_mean_bgr": gt_mean_bgr,
        })

    # ━━━ 汇总统计 ━━━
    print("\n" + "=" * 80)
    print("v4.1 汇总统计")
    print("=" * 80)

    align_ok_count = sum(1 for r in diagnosis_results if r["align_ok"])
    seg_ok_count = sum(1 for r in diagnosis_results if r["seg_ok"])
    both_ok_count = sum(1 for r in diagnosis_results if r["both_ok"])
    color_ok_count = sum(1 for r in diagnosis_results if r["color_ok"])

    total = len(diagnosis_results)

    print(f"\n文本对齐正常: {align_ok_count}/{total} ({align_ok_count/total*100:.0f}%)")
    print(f"Patch分类正常: {seg_ok_count}/{total} ({seg_ok_count/total*100:.0f}%)")
    print(f"颜色校验通过: {color_ok_count}/{total} ({color_ok_count/total*100:.0f}%)")
    print(f"三者都正常: {both_ok_count}/{total} ({both_ok_count/total*100:.0f}%)")

    # 保存结果
    output_file = output_dir / "v4.1_integrated_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(diagnosis_results, f, indent=2, ensure_ascii=False)

    print(f"\n诊断结果已保存: {output_file}")


if __name__ == "__main__":
    run_v41_diagnosis()
