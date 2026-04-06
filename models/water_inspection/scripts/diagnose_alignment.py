#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SigLIP2 文本对齐 + Patch分类 诊断分析 v3.0

使用C-RADIOv4内置的SigLIP2 adaptor进行诊断
"""

import sys
import yaml
import json
import cv2
import numpy as np
from pathlib import Path
from collections import defaultdict

# 设置路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_diagnosis():
    # 加载配置
    config_path = Path(__file__).parent.parent / "configs" / "water_inspection.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    ckpt = "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"
    radio = "/app/models/NVlabs_RADIO"
    siglip = "/app/models/siglip2-giant-opt-patch16-384"

    from models.open_vocab.radio_segmentor import WaterQualitySegmentor

    print("=" * 80)
    print("SigLIP2 文本对齐 + Patch分类 诊断分析 v3.0")
    print("使用C-RADIOv4内置SigLIP2 adaptor")
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

    # 获取所有异常类别 (排除背景)
    anomaly_classes = [k for k, v in classes_config.items() if not v.get("is_background", False)]
    background_classes = [k for k, v in classes_config.items() if v.get("is_background", False)]

    print(f"异常类别: {anomaly_classes}")
    print(f"背景类别: {background_classes}\n")

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

        # ━━━ 第1步: SigLIP2 文本对齐分析 ━━━
        # 1.1 整图分类
        full_image_probs = segmentor.classify_image(image, classes_config)

        # 1.2 加载 GT mask 并提取区域
        gt_mask_file = None
        for cls_info in meta.get("classes", []):
            if cls_info.get("class") == gt_class:
                gt_mask_file = cls_info.get("mask_file")
                break

        gt_region_probs = {}
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
                        # GT 区域颜色
                        gt_pixels = image[gt_mask_bool].astype(np.float32)
                        gt_mean_bgr = gt_pixels.mean(axis=0).tolist()

                        # GT 区域裁剪
                        ys, xs = np.where(gt_mask_bool)
                        pad = 5
                        y1, y2 = max(0, int(ys.min()) - pad), min(h, int(ys.max()) + pad)
                        x1, x2 = max(0, int(xs.min()) - pad), min(w, int(xs.max()) + pad)
                        gt_crop = image[y1:y2, x1:x2]

                        if gt_crop.shape[0] >= 32 and gt_crop.shape[1] >= 32:
                            gt_region_probs = segmentor.classify_image(gt_crop, classes_config)

        # ━━━ 第2步: Patch分类与GT重叠分析 ━━━
        best_patch_overlap = 0.0

        if gt_mask_bool is not None:
            # 使用新的compute_patch_similarity方法
            class_heatmaps = segmentor.compute_patch_similarity(image, classes_config)

            if class_heatmaps and gt_class in class_heatmaps:
                gt_heatmap = class_heatmaps[gt_class]
                high_conf_mask = gt_heatmap > 0.3

                # 计算高置信度区域与GT的IoU
                if high_conf_mask.any():
                    intersection = (high_conf_mask & gt_mask_bool).sum()
                    union = (high_conf_mask | gt_mask_bool).sum()
                    if union > 0:
                        best_patch_overlap = intersection / union

        # ━━━ 输出诊断结果 ━━━
        gt_cn = classes_config.get(gt_class, {}).get("zh", gt_class)

        # SigLIP2 分析
        full_top_class = max(full_image_probs, key=full_image_probs.get) if full_image_probs else "-"
        full_top_score = full_image_probs.get(full_top_class, 0)
        full_gt_score = full_image_probs.get(gt_class, 0)

        region_top_class = max(gt_region_probs, key=gt_region_probs.get) if gt_region_probs else "-"
        region_top_score = gt_region_probs.get(region_top_class, 0)
        region_gt_score = gt_region_probs.get(gt_class, 0)

        print(f"\n{'='*70}")
        print(f"图像: {img_path.name} | GT: {gt_cn}")
        print(f"{'='*70}")

        print(f"\n[1] SigLIP2 文本对齐分析:")
        print(f"    整图分类: {full_top_class} ({full_top_score:.1%}) | GT类别得分: {full_gt_score:.1%}")
        print(f"    GT区域分类: {region_top_class} ({region_top_score:.1%}) | GT类别得分: {region_gt_score:.1%}")

        # 判断文本对齐问题
        if region_gt_score < 0.3:
            align_status = "严重问题: GT区域分类得分过低"
            align_ok = False
        elif region_top_class != gt_class:
            align_status = f"问题: GT区域被误分类为 {region_top_class}"
            align_ok = False
        else:
            align_status = "正常: GT区域分类正确"
            align_ok = True
        print(f"    诊断: {align_status}")

        print(f"\n[2] Patch分类分析:")
        print(f"    GT区域颜色 BGR: {gt_mean_bgr}")
        print(f"    最佳Patch与GT重叠(IoU): {best_patch_overlap:.1%}")

        # 判断分割问题
        if best_patch_overlap < 0.2:
            seg_status = "严重问题: 无法找到与GT重叠的Patch"
            seg_ok = False
        elif best_patch_overlap < 0.4:
            seg_status = "问题: Patch与GT重叠不足"
            seg_ok = False
        else:
            seg_status = "正常: 存在与GT重叠良好的Patch"
            seg_ok = True
        print(f"    诊断: {seg_status}")

        # 综合诊断
        print(f"\n[3] 综合诊断:")
        if align_ok and seg_ok:
            conclusion = "文本和视觉都正常"
        elif align_ok and not seg_ok:
            conclusion = "视觉特征问题: Patch未能正确覆盖GT区域"
        elif not align_ok and seg_ok:
            conclusion = "提示词问题: 需要优化文本描述"
        else:
            conclusion = "文本和视觉都有问题"
        print(f"    {conclusion}")

        diagnosis_results.append({
            "image": img_path.name,
            "gt_class": gt_class,
            "full_gt_score": float(full_gt_score),
            "region_gt_score": float(region_gt_score),
            "region_top_class": region_top_class,
            "region_top_score": float(region_top_score),
            "best_patch_overlap": float(best_patch_overlap),
            "align_ok": align_ok,
            "seg_ok": seg_ok,
            "conclusion": conclusion,
            "gt_mean_bgr": gt_mean_bgr,
        })

    # ━━━ 汇总统计 ━━━
    print("\n" + "=" * 80)
    print("汇总统计")
    print("=" * 80)

    align_ok_count = sum(1 for r in diagnosis_results if r["align_ok"])
    seg_ok_count = sum(1 for r in diagnosis_results if r["seg_ok"])
    both_ok_count = sum(1 for r in diagnosis_results if r["align_ok"] and r["seg_ok"])

    total = len(diagnosis_results)
    print(f"\n文本对齐正常: {align_ok_count}/{total} ({align_ok_count/max(total,1):.0%})")
    print(f"Patch分类正常: {seg_ok_count}/{total} ({seg_ok_count/max(total,1):.0%})")
    print(f"两者都正常: {both_ok_count}/{total} ({both_ok_count/max(total,1):.0%})")

    # 按类别统计
    print("\n按GT类别统计:")
    class_stats = defaultdict(lambda: {"total": 0, "align_ok": 0, "seg_ok": 0, "region_scores": []})
    for r in diagnosis_results:
        cls = r["gt_class"]
        class_stats[cls]["total"] += 1
        if r["align_ok"]:
            class_stats[cls]["align_ok"] += 1
        if r["seg_ok"]:
            class_stats[cls]["seg_ok"] += 1
        class_stats[cls]["region_scores"].append(r["region_gt_score"])

    for cls, stats in sorted(class_stats.items()):
        t = stats["total"]
        a = stats["align_ok"]
        s = stats["seg_ok"]
        avg_score = np.mean(stats["region_scores"])
        cls_cn = classes_config.get(cls, {}).get("zh", cls)
        print(f"  {cls_cn:<10} ({t}张): 文本对齐 {a}/{t}, Patch分类 {s}/{t}, 平均得分 {avg_score:.0%}")

    # 需要优化提示词的类别
    print("\n" + "-" * 50)
    print("需要优化提示词的类别 (文本对齐率<70%):")
    for cls, stats in sorted(class_stats.items()):
        if stats["total"] > 0 and stats["align_ok"] / stats["total"] < 0.7:
            cls_cn = classes_config.get(cls, {}).get("zh", cls)
            avg_score = np.mean(stats["region_scores"])
            print(f"  - {cls_cn}: {stats['align_ok']}/{stats['total']} ({stats['align_ok']/max(stats['total'],1):.0%}), 平均得分 {avg_score:.0%}")

    print("\n需要优化Patch分类的类别 (Patch分类率<70%):")
    for cls, stats in sorted(class_stats.items()):
        if stats["total"] > 0 and stats["seg_ok"] / stats["total"] < 0.7:
            cls_cn = classes_config.get(cls, {}).get("zh", cls)
            print(f"  - {cls_cn}: {stats['seg_ok']}/{stats['total']} ({stats['seg_ok']/max(stats['total'],1):.0%})")

    # 保存诊断结果
    result_path = output_dir / "diagnosis_results.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(diagnosis_results, f, indent=2, ensure_ascii=False)
    print(f"\n诊断结果已保存: {result_path}")


if __name__ == "__main__":
    run_diagnosis()
