#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
施工安全 RADIO 零样本检测 - 端到端验证脚本 v2.0

验证数据:
  - dust/  (扬尘, 50张)
  - soi/   (裸土, 49张)
  - water/ (积水, 49张)

可视化 (参考水质检测风格):
  1. segmentation/  — 分割叠加 + GT框 + 类别标签
  2. heatmap/       — JET 热力图
  3. comparison/    — GT(绿) vs Pred(红) 交集(黄)
  4. summary/       — 每类最佳/最差样例拼图

用法:
  python scripts/eval_radio_zero_shot.py \
      --data-dir data \
      --save-vis

作者: 空中智能体团队
日期: 2026-04-23
"""

import sys
import cv2
import yaml
import json
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# 数据集类别 -> RADIO 提示词类别 映射
DATASET_TO_RADIO = {
    "dust": "dust_pollution",
    "soi": "bare_soil_uncovered",
    "water": "pit_water_accumulation",
}

DATASET_ZH = {
    "dust": "扬尘",
    "soi": "裸土",
    "water": "积水",
}

# 每个类别的可视化颜色 (BGR)
CLASS_COLORS = {
    "dust_pollution": (0, 200, 255),        # 橙色
    "bare_soil_uncovered": (0, 200, 200),    # 黄色
    "pit_water_accumulation": (200, 150, 0), # 蓝绿
}


def load_classes_config(config_path: str) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    if 'cloud' in config:
        return config['cloud']['radio']['classes']
    elif 'deployment' in config and 'cloud' in config['deployment']:
        return config['deployment']['cloud']['radio']['classes']
    raise KeyError("找不到 cloud.radio.classes 配置路径")


def build_prompts(classes_config: dict, target_classes: List[str]) -> dict:
    prompts = {}
    for cls_name in target_classes:
        cls_cfg = classes_config.get(cls_name, {})
        entry = {"prompts": cls_cfg.get("prompts", [])}
        if "prompts_negative" in cls_cfg:
            entry["negative"] = cls_cfg["prompts_negative"]
        prompts[cls_name] = entry
    bg_cfg = classes_config.get("background", {})
    if bg_cfg:
        prompts["background"] = {"prompts": bg_cfg.get("prompts", [
            "normal construction site without anomaly",
        ])}
    return prompts


def bbox_to_mask(bbox_yolo, h, w):
    cx, cy, bw, bh = bbox_yolo
    x1, y1 = int((cx - bw/2)*w), int((cy - bh/2)*h)
    x2, y2 = int((cx + bw/2)*w), int((cy + bh/2)*h)
    mask = np.zeros((h, w), dtype=bool)
    mask[max(0,y1):min(h,y2), max(0,x1):min(w,x2)] = True
    return mask


# ==============================================================================
# 可视化函数 (参考水质检测 WaterQualityVisualizer)
# ==============================================================================

def draw_segmentation(
    image: np.ndarray,
    pred_mask: np.ndarray,
    gt_bbox: Optional[list],
    class_name: str,
    class_name_cn: str,
    score: float,
    area_ratio: float,
    iou: float,
    is_correct: bool,
) -> np.ndarray:
    """
    分割可视化: 半透明 mask + GT 框 + 类别标签 + 置信度
    风格参考 WaterQualityVisualizer.visualize_segmentation
    """
    vis = image.copy()
    h, w = vis.shape[:2]
    color = CLASS_COLORS.get(class_name, (128, 128, 128))

    # 半透明 mask 叠加
    mask_uint8 = pred_mask.astype(np.uint8) * 255
    overlay = np.zeros_like(vis)
    overlay[mask_uint8 > 0] = color
    vis = cv2.addWeighted(vis, 0.6, overlay, 0.4, 0)

    # 轮廓
    contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(vis, contours, -1, color, 2)

    # GT 框 (绿色)
    if gt_bbox is not None:
        gx1 = int((gt_bbox[0] - gt_bbox[2]/2) * w)
        gy1 = int((gt_bbox[1] - gt_bbox[3]/2) * h)
        gx2 = int((gt_bbox[0] + gt_bbox[2]/2) * w)
        gy2 = int((gt_bbox[1] + gt_bbox[3]/2) * h)
        cv2.rectangle(vis, (gx1, gy1), (gx2, gy2), (0, 255, 0), 2)
        cv2.putText(vis, "GT", (gx1, gy1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

    # 状态标签
    status = "OK" if is_correct else "WRONG"
    status_color = (0, 200, 0) if is_correct else (0, 0, 255)

    # 信息面板 (顶部)
    info_lines = [
        f"[{status}] {class_name_cn}  score:{score:.2f}  area:{area_ratio:.1%}  IoU:{iou:.3f}",
    ]
    panel_h = 35
    cv2.rectangle(vis, (0, 0), (w, panel_h), (0, 0, 0), -1)
    cv2.putText(vis, info_lines[0], (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

    return vis


def draw_heatmap(
    image: np.ndarray,
    heatmap: np.ndarray,
    class_name: str,
) -> np.ndarray:
    """热力图可视化 (参考 WaterQualityVisualizer.visualize_heatmap)"""
    heatmap_norm = ((heatmap - heatmap.min()) / (heatmap.max() - heatmap.min() + 1e-8) * 255).astype(np.uint8)
    heatmap_colored = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)
    vis = cv2.addWeighted(image, 0.6, heatmap_colored, 0.4, 0)
    cv2.putText(vis, f"Heatmap: {class_name}", (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
    return vis


def draw_comparison(
    image: np.ndarray,
    pred_mask: np.ndarray,
    gt_mask: np.ndarray,
    iou: float,
) -> np.ndarray:
    """
    对比可视化: GT=绿色, Pred=红色, 交集=黄色
    参考 WaterQualityVisualizer.visualize_comparison
    """
    h, w = image.shape[:2]
    vis = np.zeros((h, w, 3), dtype=np.uint8)
    vis[gt_mask, 1] = 255       # GT: 绿
    vis[pred_mask, 2] = 255     # Pred: 红
    intersection = gt_mask & pred_mask
    vis[intersection] = [0, 255, 255]  # 交集: 黄
    vis = cv2.addWeighted(image, 0.5, vis, 0.5, 0)

    cv2.putText(vis, f"IoU: {iou:.3f}", (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
    cv2.putText(vis, "Green=GT  Red=Pred  Yellow=Overlap", (8, h-12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
    return vis


def create_summary_grid(
    images_with_labels: List[Tuple[np.ndarray, str]],
    title: str,
    cols: int = 5,
) -> np.ndarray:
    """将多张图像拼成网格"""
    if not images_with_labels:
        return np.zeros((100, 300, 3), dtype=np.uint8)

    target_h, target_w = 200, 200
    resized = []
    for img, label in images_with_labels:
        r = img.copy()
        r = cv2.resize(r, (target_w, target_h))
        cv2.putText(r, label, (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,255,255), 1)
        resized.append(r)

    n = len(resized)
    rows = (n + cols - 1) // cols
    # 填充空白
    while len(resized) < rows * cols:
        resized.append(np.zeros((target_h, target_w, 3), dtype=np.uint8))

    grid_rows = []
    for r in range(rows):
        row = np.hstack(resized[r*cols:(r+1)*cols])
        grid_rows.append(row)
    grid = np.vstack(grid_rows)

    # 标题栏
    title_bar = np.zeros((30, grid.shape[1], 3), dtype=np.uint8)
    cv2.putText(title_bar, title, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
    grid = np.vstack([title_bar, grid])

    return grid


# ==============================================================================
# 主函数
# ==============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="施工安全 RADIO 零样本检测验证 v2.0")
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--config", type=str, default="configs/construction_safety.yaml")
    parser.add_argument("--checkpoint", type=str,
                        default="/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar")
    parser.add_argument("--radio-code-dir", type=str, default="/app/models/NVlabs_RADIO")
    parser.add_argument("--siglip2-dir", type=str,
                        default="/app/models/siglip2-giant-opt-patch16-384")
    parser.add_argument("--threshold", type=float, default=0.25)
    parser.add_argument("--min-area", type=float, default=0.003)
    parser.add_argument("--max-images", type=int, default=0, help="0=全部")
    parser.add_argument("--save-vis", action="store_true", help="保存可视化")
    parser.add_argument("--output-dir", type=str, default="outputs/radio_eval_v2")

    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)

    # 创建可视化子目录
    if args.save_vis:
        for sub in ["segmentation", "heatmap", "comparison", "summary"]:
            (output_dir / sub).mkdir(parents=True, exist_ok=True)

    # 加载配置
    classes_config = load_classes_config(args.config)

    # 加载 RADIO 分割器
    logger.info("加载 C-RADIOv4 分割器...")
    app_dir = Path(__file__).resolve().parent.parent.parent.parent
    for p in [str(app_dir), str(app_dir/"models"), str(app_dir/"water_inspection")]:
        if p not in sys.path:
            sys.path.insert(0, p)

    segmentor_cls = None
    for import_path in [
        "models.open_vocab.radseg_segmentor:RADSegWaterSegmentor",
        "models.water_inspection.models.open_vocab.radseg_segmentor:RADSegWaterSegmentor",
    ]:
        module_path, cls_name = import_path.rsplit(":", 1)
        try:
            mod = __import__(module_path, fromlist=[cls_name])
            segmentor_cls = getattr(mod, cls_name)
            break
        except (ImportError, ModuleNotFoundError):
            continue
    if segmentor_cls is None:
        raise ImportError("无法导入 RADSegWaterSegmentor")

    segmentor = segmentor_cls(
        checkpoint_path=args.checkpoint,
        radio_code_dir=args.radio_code_dir,
        siglip2_dir=args.siglip2_dir,
        device='cuda', use_scra=True, use_dino=False, use_sam=False,
        temperature=50.0,
    )
    logger.info("  分割器加载完成")

    radio_classes = ["dust_pollution", "bare_soil_uncovered", "pit_water_accumulation"]
    prompts_config = build_prompts(classes_config, radio_classes)

    print("\n" + "=" * 70)
    print("施工安全 RADIO 零样本检测 - 端到端验证 v2.0")
    print("=" * 70)
    print(f"  阈值: {args.threshold}, 最小面积: {args.min_area}")

    all_results = {}
    per_class_stats = defaultdict(lambda: {
        "total": 0, "detected": 0, "correct": 0,
        "ious": [], "scores": [], "times": [],
        "best_samples": [], "worst_samples": [],
    })

    for dataset_name, radio_class in DATASET_TO_RADIO.items():
        img_dir = data_dir / dataset_name / "images"
        lbl_dir = data_dir / dataset_name / "labels"
        if not img_dir.exists():
            continue

        images = sorted(list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png")))
        if args.max_images > 0:
            images = images[:args.max_images]

        print(f"\n{'─'*70}")
        print(f"类别: {DATASET_ZH[dataset_name]} ({dataset_name}) → {radio_class}")
        print(f"  图像数: {len(images)}")
        print(f"{'─'*70}")

        class_results = []

        for idx, img_path in enumerate(images):
            image = cv2.imread(str(img_path))
            if image is None:
                continue
            h, w = image.shape[:2]

            # GT bbox
            lbl_path = lbl_dir / f"{img_path.stem}.txt"
            gt_bbox = None
            if lbl_path.exists():
                with open(lbl_path) as f:
                    lines = f.read().strip().split('\n')
                if lines and lines[0]:
                    parts = lines[0].split()
                    if len(parts) >= 5:
                        gt_bbox = [float(x) for x in parts[1:5]]

            # RADIO 推理
            t0 = time.time()
            heatmaps = segmentor.compute_patch_similarity(image, prompts_config)
            elapsed = time.time() - t0

            # 找最佳类别
            best_class, best_score, best_area = None, 0, 0
            class_scores = {}
            for cls_name in radio_classes:
                hm = heatmaps.get(cls_name, np.zeros((h, w)))
                mask = hm > args.threshold
                area = float(mask.sum() / (h * w))
                mean_score = float(hm[mask].mean()) if mask.any() else 0.0
                class_scores[cls_name] = {
                    "mean": round(mean_score, 4),
                    "max": round(float(hm.max()), 4),
                    "area": round(area, 4),
                }
                if mean_score > best_score:
                    best_score = mean_score
                    best_class = cls_name
                    best_area = area

            is_detected = best_class is not None and best_area >= args.min_area
            is_correct = best_class == radio_class

            # IoU
            iou = 0.0
            if is_detected and gt_bbox is not None:
                pred_hm = heatmaps.get(best_class, np.zeros((h, w)))
                pred_mask = pred_hm > args.threshold
                gt_mask = bbox_to_mask(gt_bbox, h, w)
                intersection = np.logical_and(pred_mask, gt_mask).sum()
                union = np.logical_or(pred_mask, gt_mask).sum()
                iou = float(intersection / union) if union > 0 else 0.0

            # 统计
            stats = per_class_stats[dataset_name]
            stats["total"] += 1
            if is_detected:
                stats["detected"] += 1
            if is_correct:
                stats["correct"] += 1
            if iou > 0:
                stats["ious"].append(iou)
            stats["scores"].append(best_score)
            stats["times"].append(elapsed)

            # 收集 best/worst 样例
            sample_info = (image.copy(), heatmaps.copy(), gt_bbox, best_class,
                          best_score, best_area, iou, is_correct, img_path.name)
            if is_correct:
                if len(stats["best_samples"]) < 5:
                    stats["best_samples"].append(sample_info)
            else:
                if len(stats["worst_samples"]) < 5:
                    stats["worst_samples"].append(sample_info)

            status = "✓" if is_correct else ("?" if is_detected else "✗")
            pred_cn = classes_config.get(best_class, {}).get("zh", best_class) if best_class else "—"
            print(f"  [{status}] {img_path.name[:35]:<36} "
                  f"GT={DATASET_ZH[dataset_name]:<4} Pred={pred_cn:<6} "
                  f"score={best_score:.3f} area={best_area:.3f} IoU={iou:.3f} {elapsed:.2f}s")

            result = {
                "image": img_path.name, "gt_class": dataset_name,
                "pred_class": best_class, "correct": is_correct,
                "score": round(best_score, 4), "area": round(best_area, 4),
                "iou": round(iou, 4), "elapsed": round(elapsed, 2),
                "class_scores": class_scores,
            }
            class_results.append(result)

            # 可视化
            if args.save_vis:
                pred_cn_name = classes_config.get(best_class, {}).get("zh", best_class or "?")
                base = f"{dataset_name}_{img_path.stem}"

                # 1. 分割叠加
                if is_detected:
                    pred_hm = heatmaps.get(best_class, np.zeros((h, w)))
                    pred_mask = pred_hm > args.threshold
                    vis_seg = draw_segmentation(
                        image, pred_mask, gt_bbox,
                        best_class, pred_cn_name, best_score, best_area, iou, is_correct)
                    cv2.imwrite(str(output_dir / "segmentation" / f"{base}.jpg"), vis_seg)

                    # 2. 热力图 (只对 GT 对应的类别)
                    gt_hm = heatmaps.get(radio_class, np.zeros((h, w)))
                    vis_hm = draw_heatmap(image, gt_hm, classes_config.get(radio_class, {}).get("zh", radio_class))
                    cv2.imwrite(str(output_dir / "heatmap" / f"{base}.jpg"), vis_hm)

                    # 3. 对比图
                    if gt_bbox is not None:
                        gt_mask = bbox_to_mask(gt_bbox, h, w)
                        vis_cmp = draw_comparison(image, pred_mask, gt_mask, iou)
                        cv2.imwrite(str(output_dir / "comparison" / f"{base}.jpg"), vis_cmp)

        all_results[dataset_name] = class_results

    # ================================================================
    # 生成 summary 拼图
    # ================================================================
    if args.save_vis:
        for dataset_name in DATASET_TO_RADIO:
            stats = per_class_stats[dataset_name]
            zh = DATASET_ZH[dataset_name]

            # 正确样例拼图
            best_imgs = []
            for (img, heatmaps, gt_bbox, pred_cls, score, area, iou, correct, name) in stats["best_samples"]:
                pred_cn = classes_config.get(pred_cls, {}).get("zh", pred_cls)
                label = f"OK {pred_cn} s:{score:.2f} IoU:{iou:.2f}"
                pred_hm = heatmaps.get(pred_cls, np.zeros(img.shape[:2]))
                vis = draw_segmentation(img, pred_hm > args.threshold, gt_bbox,
                                        pred_cls, pred_cn, score, area, iou, True)
                best_imgs.append((vis, label))

            if best_imgs:
                grid = create_summary_grid(best_imgs, f"{zh} - Correct ({len(best_imgs)})")
                cv2.imwrite(str(output_dir / "summary" / f"{dataset_name}_correct.jpg"), grid)

            # 错误样例拼图
            worst_imgs = []
            for (img, heatmaps, gt_bbox, pred_cls, score, area, iou, correct, name) in stats["worst_samples"]:
                pred_cn = classes_config.get(pred_cls, {}).get("zh", pred_cls)
                label = f"WRONG {pred_cn} s:{score:.2f}"
                pred_hm = heatmaps.get(pred_cls, np.zeros(img.shape[:2]))
                vis = draw_segmentation(img, pred_hm > args.threshold, gt_bbox,
                                        pred_cls, pred_cn, score, area, iou, False)
                worst_imgs.append((vis, label))

            if worst_imgs:
                grid = create_summary_grid(worst_imgs, f"{zh} - Wrong ({len(worst_imgs)})")
                cv2.imwrite(str(output_dir / "summary" / f"{dataset_name}_wrong.jpg"), grid)

    # ================================================================
    # 汇总报告
    # ================================================================
    print("\n" + "=" * 70)
    print("验证结果汇总 v2.0")
    print("=" * 70)

    total_all, correct_all = 0, 0
    confusion = defaultdict(lambda: defaultdict(int))

    for dataset_name in DATASET_TO_RADIO:
        stats = per_class_stats[dataset_name]
        if stats["total"] == 0:
            continue
        total_all += stats["total"]
        correct_all += stats["correct"]

        precision = stats["correct"] / stats["detected"] if stats["detected"] > 0 else 0
        recall = stats["correct"] / stats["total"]
        f1 = 2*precision*recall / (precision+recall) if (precision+recall) > 0 else 0
        mean_iou = np.mean(stats["ious"]) if stats["ious"] else 0
        mean_time = np.mean(stats["times"]) if stats["times"] else 0

        # 混淆矩阵统计
        for r in all_results.get(dataset_name, []):
            confusion[dataset_name][r["pred_class"]] += 1

        print(f"\n  [{DATASET_ZH[dataset_name]}] ({dataset_name} → {DATASET_TO_RADIO[dataset_name]})")
        print(f"    样本数:    {stats['total']}")
        print(f"    正确数:    {stats['correct']}")
        print(f"    精确率:    {precision:.2%}")
        print(f"    召回率:    {recall:.2%}")
        print(f"    F1:        {f1:.2%}")
        print(f"    平均IoU:   {mean_iou:.4f}")
        print(f"    平均耗时:  {mean_time:.2f}s")

        # 混淆详情
        print(f"    混淆分布:")
        for pred_cls, cnt in sorted(confusion[dataset_name].items(), key=lambda x: -x[1]):
            pred_cn = classes_config.get(pred_cls, {}).get("zh", pred_cls or "未检出")
            mark = "  ←" if pred_cls == DATASET_TO_RADIO[dataset_name] else ""
            print(f"      → {pred_cn}: {cnt}{mark}")

    overall_acc = correct_all / total_all if total_all > 0 else 0
    print(f"\n  总体准确率: {correct_all}/{total_all} = {overall_acc:.2%}")

    # 保存 JSON
    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {"threshold": args.threshold, "min_area": args.min_area},
        "overall_accuracy": round(overall_acc, 4),
        "per_class": {},
        "confusion": {k: dict(v) for k, v in confusion.items()},
    }
    for dataset_name in DATASET_TO_RADIO:
        stats = per_class_stats[dataset_name]
        if stats["total"] == 0:
            continue
        p = stats["correct"] / stats["detected"] if stats["detected"] > 0 else 0
        r = stats["correct"] / stats["total"]
        f = 2*p*r/(p+r) if (p+r) > 0 else 0
        summary["per_class"][dataset_name] = {
            "zh": DATASET_ZH[dataset_name],
            "radio_class": DATASET_TO_RADIO[dataset_name],
            "total": stats["total"], "correct": stats["correct"],
            "precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4),
            "mean_iou": round(float(np.mean(stats["ious"])) if stats["ious"] else 0, 4),
        }
    summary["details"] = all_results

    result_path = output_dir / "eval_results.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {result_path}")
    if args.save_vis:
        print(f"可视化目录: {output_dir}")
        print(f"  segmentation/  — 分割叠加 + GT框")
        print(f"  heatmap/       — JET热力图")
        print(f"  comparison/    — GT(绿) vs Pred(红) 交集(黄)")
        print(f"  summary/       — 每类正确/错误拼图")
    print("=" * 70)


if __name__ == "__main__":
    main()
