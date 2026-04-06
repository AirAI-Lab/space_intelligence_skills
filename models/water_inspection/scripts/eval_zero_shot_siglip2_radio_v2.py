#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SigLIP2 + RADIO 零样本评估脚本 v2

新增能力:
1. 按类别阈值自动搜索（工程口径）
2. 颜色先验软融合（避免硬规则误杀）
3. 失败样本诊断表（按类别输出典型错误）
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.open_vocab.radio_segmentor import WaterQualitySegmentor


def _find_existing_path(candidates: List[Path]) -> Optional[Path]:
    for path in candidates:
        if path.exists():
            return path
    return None


def resolve_model_paths(project_root: Path) -> Tuple[Path, Path, Path]:
    models_root = project_root.parent

    checkpoint = _find_existing_path(
        [
            models_root / "C-RADIOv4-H" / "c-radio_v4-h_half.pth.tar",
            Path("/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"),
        ]
    )
    radio_code = _find_existing_path(
        [
            models_root / "NVlabs_RADIO",
            Path("/app/models/NVlabs_RADIO"),
        ]
    )
    siglip_dir = _find_existing_path(
        [
            models_root / "siglip2-giant-opt-patch16-384",
            Path("/app/models/siglip2-giant-opt-patch16-384"),
        ]
    )

    if checkpoint is None or radio_code is None or siglip_dir is None:
        raise FileNotFoundError("无法定位本地模型目录，请检查 models 目录。")

    return checkpoint, radio_code, siglip_dir


def load_dataset(dataset_dir: Path) -> List[dict]:
    meta_dir = dataset_dir / "meta"
    samples: List[dict] = []
    for meta_file in sorted(meta_dir.glob("*.json"), key=lambda p: int(p.stem)):
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["meta_file"] = str(meta_file)
        meta["image_path"] = str(dataset_dir / "images" / meta["image"])
        samples.append(meta)
    return samples


def load_gt_mask(sample: dict, masks_dir: Path, image_shape: Tuple[int, int]) -> np.ndarray:
    h, w = image_shape
    gt_class = sample.get("active_class")
    for item in sample.get("classes", []):
        if item.get("class") != gt_class:
            continue
        mask_file = item.get("mask_file")
        if not mask_file:
            break
        mask_path = masks_dir / mask_file
        if not mask_path.exists():
            break
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            break
        if mask.shape != (h, w):
            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
        return mask > 127
    return np.zeros((h, w), dtype=bool)


def compute_iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    if union == 0:
        return 1.0 if inter == 0 else 0.0
    return float(inter) / float(union)


def draw_overlay(
    image: np.ndarray,
    gt_mask: np.ndarray,
    pred_mask: np.ndarray,
    gt_class: str,
    pred_class: str,
    score: float,
    iou: float,
) -> np.ndarray:
    vis = image.copy()

    if gt_mask.any():
        gt_overlay = np.zeros_like(vis)
        gt_overlay[gt_mask] = (0, 255, 0)
        vis = cv2.addWeighted(vis, 0.78, gt_overlay, 0.22, 0)
        contours, _ = cv2.findContours(gt_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, contours, -1, (0, 255, 0), 2)

    if pred_mask.any():
        pred_overlay = np.zeros_like(vis)
        pred_overlay[pred_mask] = (0, 0, 255)
        vis = cv2.addWeighted(vis, 0.78, pred_overlay, 0.22, 0)
        contours, _ = cv2.findContours(pred_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, contours, -1, (0, 0, 255), 2)

    lines = [
        f"GT: {gt_class}",
        f"Pred: {pred_class}",
        f"Score: {score:.3f}",
        f"IoU: {iou:.3f}",
    ]
    y = 28
    for text in lines:
        cv2.putText(vis, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(vis, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
        y += 30

    return vis


def collect_score_cache(
    segmentor: WaterQualitySegmentor,
    classes_config: Dict[str, dict],
    prompts_config: Dict[str, dict],
    samples: List[dict],
    color_fusion_alpha: float,
) -> List[dict]:
    cache = []
    anomaly_classes = [
        c for c, cfg in classes_config.items()
        if (not cfg.get("is_background", False)) and c != "normal_water"
    ]

    for sample in samples:
        image = cv2.imread(sample["image_path"])
        if image is None:
            continue

        heatmaps = segmentor.compute_patch_similarity(image, classes_config, prompts_config)
        heatmaps = segmentor._apply_color_soft_fusion(
            image=image,
            class_heatmaps=heatmaps,
            classes_config=classes_config,
            alpha=float(color_fusion_alpha),
        )
        water_mask = segmentor._identify_water_region(heatmaps, image.shape[0], image.shape[1])

        peaks = {}
        for cls in anomaly_classes:
            hm = heatmaps.get(cls)
            if hm is None:
                peaks[cls] = 0.0
                continue
            if water_mask.any():
                peaks[cls] = float(hm[water_mask].max())
            else:
                peaks[cls] = float(hm.max())

        cache.append(
            {
                "image": Path(sample["image_path"]).name,
                "gt_class": sample.get("active_class", "normal_water"),
                "peaks": peaks,
            }
        )

    return cache


def _f1(precision: float, recall: float) -> float:
    if precision + recall <= 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def search_class_thresholds(
    cache: List[dict],
    anomaly_classes: List[str],
    candidates: List[float],
) -> Dict[str, dict]:
    best = {}
    for cls in anomaly_classes:
        best_item = {"threshold": 0.20, "f1": -1.0, "precision": 0.0, "recall": 0.0}
        for thr in candidates:
            tp = fp = fn = 0
            for item in cache:
                gt_pos = item["gt_class"] == cls
                pred_pos = item["peaks"].get(cls, 0.0) >= thr
                if gt_pos and pred_pos:
                    tp += 1
                elif (not gt_pos) and pred_pos:
                    fp += 1
                elif gt_pos and (not pred_pos):
                    fn += 1

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = _f1(precision, recall)
            if f1 > best_item["f1"]:
                best_item = {
                    "threshold": float(thr),
                    "f1": float(f1),
                    "precision": float(precision),
                    "recall": float(recall),
                }
        best[cls] = best_item

    return best


def evaluate(
    segmentor: WaterQualitySegmentor,
    classes_config: Dict[str, dict],
    prompts_config: Dict[str, dict],
    samples: List[dict],
    dataset_dir: Path,
    vis_dir: Path,
    max_visualizations: int,
    class_thresholds: Optional[Dict[str, float]] = None,
    color_fusion_alpha: float = 0.20,
) -> dict:
    anomaly_classes = [
        cls_name
        for cls_name, cfg in classes_config.items()
        if (not cfg.get("is_background", False)) and cls_name != "normal_water"
    ]

    per_class = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "ious": []})
    confusion = defaultdict(Counter)
    detailed = []

    vis_saved = 0
    masks_dir = dataset_dir / "masks"

    for idx, sample in enumerate(samples, 1):
        image_path = Path(sample["image_path"])
        image = cv2.imread(str(image_path))
        if image is None:
            continue

        gt_class = sample.get("active_class", "normal_water")
        gt_mask = load_gt_mask(sample, masks_dir, image.shape[:2])

        segments = segmentor.segment(
            image,
            classes_config,
            prompts_config=prompts_config,
            class_thresholds=class_thresholds,
            color_fusion_alpha=color_fusion_alpha,
        )

        pred_class = "normal_water"
        pred_mask = np.zeros(image.shape[:2], dtype=bool)
        pred_score = 0.0

        if segments:
            best_seg = max(segments.values(), key=lambda x: x.score)
            pred_class = best_seg.class_name
            pred_mask = best_seg.mask if best_seg.mask is not None else pred_mask
            pred_score = float(best_seg.score)

        confusion[gt_class][pred_class] += 1

        if gt_class in anomaly_classes:
            if pred_class == gt_class:
                per_class[gt_class]["tp"] += 1
            else:
                per_class[gt_class]["fn"] += 1
                if pred_class in anomaly_classes:
                    per_class[pred_class]["fp"] += 1
        else:
            if pred_class in anomaly_classes:
                per_class[pred_class]["fp"] += 1

        iou = compute_iou(pred_mask, gt_mask)
        if gt_class in anomaly_classes and pred_class == gt_class:
            per_class[gt_class]["ious"].append(iou)

        is_error = pred_class != gt_class
        vis_name = None
        if vis_saved < max_visualizations and (is_error or vis_saved < max_visualizations // 3):
            vis = draw_overlay(image, gt_mask, pred_mask, gt_class, pred_class, pred_score, iou)
            vis_name = f"{idx:03d}_{image_path.stem}_gt-{gt_class}_pred-{pred_class}.jpg"
            cv2.imwrite(str(vis_dir / vis_name), vis)
            vis_saved += 1

        detailed.append(
            {
                "image": image_path.name,
                "gt_class": gt_class,
                "pred_class": pred_class,
                "pred_score": pred_score,
                "iou": iou,
                "is_correct": bool(pred_class == gt_class),
                "visualization": vis_name,
            }
        )

    metrics = {}
    macro_f1 = 0.0
    for cls_name in anomaly_classes:
        tp = per_class[cls_name]["tp"]
        fp = per_class[cls_name]["fp"]
        fn = per_class[cls_name]["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = _f1(precision, recall)
        miou = float(np.mean(per_class[cls_name]["ious"])) if per_class[cls_name]["ious"] else 0.0
        metrics[cls_name] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "miou": miou,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
        macro_f1 += f1

    macro_f1 = macro_f1 / max(len(anomaly_classes), 1)

    total = len(detailed)
    correct = sum(1 for x in detailed if x["is_correct"])
    accuracy = correct / max(total, 1)

    normal_total = sum(1 for x in detailed if x["gt_class"] == "normal_water")
    normal_fp = sum(1 for x in detailed if x["gt_class"] == "normal_water" and x["pred_class"] != "normal_water")
    normal_fp_rate = normal_fp / max(normal_total, 1)

    return {
        "summary": {
            "total_samples": total,
            "accuracy": accuracy,
            "macro_f1_anomaly": macro_f1,
            "normal_false_positive_rate": normal_fp_rate,
            "visualizations_saved": vis_saved,
            "pred_distribution": dict(Counter(x["pred_class"] for x in detailed)),
        },
        "metrics": metrics,
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "details": detailed,
        "class_thresholds": class_thresholds or {},
        "color_fusion_alpha": float(color_fusion_alpha),
    }


def build_failure_diagnosis(details: List[dict], top_k: int = 5) -> Dict[str, List[dict]]:
    by_gt = defaultdict(list)
    for item in details:
        if item["is_correct"]:
            continue
        reason = ""
        if item["pred_class"] == "normal_water" and item["pred_score"] < 0.2:
            reason = "文本对齐偏弱（分类分数低）"
        elif item["pred_class"] == "normal_water" and item["iou"] <= 0.01:
            reason = "分割视觉特征提取偏弱（掩码基本为空）"
        elif item["pred_class"] != "normal_water":
            reason = "类别混淆（提示词可分性不足）"
        else:
            reason = "综合误差（需联合调参）"

        enriched = dict(item)
        enriched["reason"] = reason
        by_gt[item["gt_class"]].append(enriched)

    output = {}
    for gt_class, rows in by_gt.items():
        rows.sort(key=lambda x: (x["iou"], -x["pred_score"]))
        output[gt_class] = rows[:top_k]
    return output


def write_markdown_report(result: dict, diagnosis: Dict[str, List[dict]], output_md: Path) -> None:
    summary = result["summary"]
    metrics = result["metrics"]

    lines = []
    lines.append("# SigLIP2 + RADIO 零样本评估报告 v2")
    lines.append("")
    lines.append("## 总览")
    lines.append(f"- 样本数: {summary['total_samples']}")
    lines.append(f"- 总体准确率: {summary['accuracy']:.2%}")
    lines.append(f"- 异常类 Macro-F1: {summary['macro_f1_anomaly']:.2%}")
    lines.append(f"- 正常水误检率: {summary['normal_false_positive_rate']:.2%}")
    lines.append(f"- 颜色软融合 alpha: {result['color_fusion_alpha']:.3f}")
    lines.append(f"- 预测分布: {summary['pred_distribution']}")
    lines.append("")

    lines.append("## 类别阈值")
    if result["class_thresholds"]:
        for cls_name, thr in result["class_thresholds"].items():
            lines.append(f"- {cls_name}: {float(thr):.3f}")
    else:
        lines.append("- 未启用自动搜索，使用配置默认阈值")
    lines.append("")

    lines.append("## 异常类别指标")
    for cls_name, m in metrics.items():
        lines.append(
            f"- {cls_name}: P={m['precision']:.2%}, R={m['recall']:.2%}, F1={m['f1']:.2%}, mIoU={m['miou']:.4f}, TP/FP/FN={m['tp']}/{m['fp']}/{m['fn']}"
        )
    lines.append("")

    lines.append("## 失败样本诊断")
    if not diagnosis:
        lines.append("- 无失败样本")
    else:
        for gt_cls, rows in diagnosis.items():
            lines.append(f"- GT={gt_cls}")
            for row in rows:
                vis_name = row.get("visualization") or ""
                lines.append(
                    f"  - image={row['image']}, pred={row['pred_class']}, score={row['pred_score']:.3f}, iou={row['iou']:.3f}, reason={row['reason']}, vis={vis_name}"
                )

    with open(output_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="SigLIP2 + RADIO 零样本评估 v2")
    parser.add_argument("--config", type=str, default=str(PROJECT_ROOT / "configs" / "water_inspection.yaml"))
    parser.add_argument("--dataset", type=str, default=str(PROJECT_ROOT / "data" / "datasets"))
    parser.add_argument("--prompts", type=str, default=str(PROJECT_ROOT / "data" / "diagnosis" / "optimized_prompts.yaml"))
    parser.add_argument("--output-dir", type=str, default=str(PROJECT_ROOT / "outputs" / "zero_shot_eval_v2"))
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--max-visualizations", type=int, default=80)
    parser.add_argument("--color-fusion-alpha", type=float, default=0.20)
    parser.add_argument("--search-thresholds", action="store_true")
    parser.add_argument("--search-max-samples", type=int, default=48)
    args = parser.parse_args()

    config_path = Path(args.config)
    dataset_dir = Path(args.dataset)
    prompts_path = Path(args.prompts)
    output_dir = Path(args.output_dir)
    vis_dir = output_dir / "visualizations"

    output_dir.mkdir(parents=True, exist_ok=True)
    vis_dir.mkdir(parents=True, exist_ok=True)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    prompts_config: Dict[str, dict] = {}
    if prompts_path.exists():
        with open(prompts_path, "r", encoding="utf-8") as f:
            prompts_config = yaml.safe_load(f) or {}

    classes_config = config.get("cloud", {}).get("radio", {}).get("classes", {})
    anomaly_classes = [
        c for c, cfg in classes_config.items()
        if (not cfg.get("is_background", False)) and c != "normal_water"
    ]

    checkpoint, radio_code, siglip_dir = resolve_model_paths(PROJECT_ROOT)

    print("=" * 80)
    print("SigLIP2 + RADIO 零样本评估 v2")
    print("=" * 80)
    print(f"checkpoint: {checkpoint}")
    print(f"radio code: {radio_code}")
    print(f"siglip2: {siglip_dir}")
    print(f"dataset: {dataset_dir}")
    print(f"prompts: {prompts_path if prompts_path.exists() else '未提供，使用 config prompts'}")

    segmentor = WaterQualitySegmentor(
        checkpoint_path=str(checkpoint),
        radio_code_dir=str(radio_code),
        siglip2_dir=str(siglip_dir),
        device=args.device,
        input_size=int(config.get("cloud", {}).get("radio", {}).get("inference", {}).get("input_size", 896)),
        config=config,
    )

    samples = load_dataset(dataset_dir)
    if args.max_samples > 0:
        samples = samples[: args.max_samples]
    print(f"samples: {len(samples)}")

    class_thresholds = {}
    threshold_search_report = {}

    if args.search_thresholds:
        search_samples = samples[: min(len(samples), args.search_max_samples)]
        print(f"threshold-search samples: {len(search_samples)}")
        cache = collect_score_cache(
            segmentor=segmentor,
            classes_config=classes_config,
            prompts_config=prompts_config,
            samples=search_samples,
            color_fusion_alpha=float(args.color_fusion_alpha),
        )

        candidates = [round(x, 3) for x in np.linspace(0.10, 0.45, 8)]
        threshold_search_report = search_class_thresholds(cache, anomaly_classes, candidates)
        class_thresholds = {k: v["threshold"] for k, v in threshold_search_report.items()}
        print(f"searched thresholds: {class_thresholds}")

    result = evaluate(
        segmentor=segmentor,
        classes_config=classes_config,
        prompts_config=prompts_config,
        samples=samples,
        dataset_dir=dataset_dir,
        vis_dir=vis_dir,
        max_visualizations=args.max_visualizations,
        class_thresholds=class_thresholds if class_thresholds else None,
        color_fusion_alpha=float(args.color_fusion_alpha),
    )

    diagnosis = build_failure_diagnosis(result["details"], top_k=5)

    result_json = output_dir / "zero_shot_eval_results_v2.json"
    result_md = output_dir / "zero_shot_eval_report_v2.md"
    diagnosis_json = output_dir / "failure_diagnosis_v2.json"
    thresholds_json = output_dir / "class_thresholds_v2.json"

    with open(result_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    with open(diagnosis_json, "w", encoding="utf-8") as f:
        json.dump(diagnosis, f, indent=2, ensure_ascii=False)

    with open(thresholds_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "class_thresholds": class_thresholds,
                "search_report": threshold_search_report,
                "color_fusion_alpha": float(args.color_fusion_alpha),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    write_markdown_report(result, diagnosis, result_md)

    print("\n--- 评估完成 ---")
    print(f"结果 JSON: {result_json}")
    print(f"阈值 JSON: {thresholds_json}")
    print(f"诊断 JSON: {diagnosis_json}")
    print(f"结果报告: {result_md}")
    print(f"可视化目录: {vis_dir}")
    print(f"Accuracy: {result['summary']['accuracy']:.2%}")
    print(f"Macro-F1(anomaly): {result['summary']['macro_f1_anomaly']:.2%}")


if __name__ == "__main__":
    main()
