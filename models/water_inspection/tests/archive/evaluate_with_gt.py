#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基于 GT 标签的分割评估 + 参数优化

使用 SAM2 数据集的 RLE 标签作为 Ground Truth，评估 C-RADIOv4 分割效果，
并通过网格搜索优化 threshold / anomaly_sigma / min_area 三个参数。

数据集格式 (SAM2):
  tt.v6i.sam2/
    train/  (404 张)
    valid/  (62 张)
  每张图片对应同名 JSON 标签文件:
    {
      "image": {"file_name": "...", "height": 960, "width": 960},
      "annotations": [
        {"segmentation": {"counts": "<RLE>", "size": [960, 960]}, "bbox": [...], "area": ...}
      ]
    }

用法:
  # 默认: 随机 20 张图，使用默认参数
  python tests/evaluate_with_gt.py --num-samples 20

  # 网格搜索最优参数
  python tests/evaluate_with_gt.py --num-samples 30 --grid-search

  # 指定分割参数
  python tests/evaluate_with_gt.py --threshold 0.2 --anomaly-sigma 1.0 --min-area 0.005

  # 使用 valid 集
  python tests/evaluate_with_gt.py --split valid --num-samples 30

作者: 空中智能体团队
日期: 2026-04-02
"""

import sys
import os
import json
import time
import random
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import cv2
import numpy as np

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def decode_rle_mask(annotation: dict, height: int, width: int) -> np.ndarray:
    """
    解码 RLE 格式的分割 mask

    支持 pycocotools 和手动解码两种方式。
    """
    segmentation = annotation.get("segmentation", {})
    counts = segmentation.get("counts", "")
    size = segmentation.get("size", [height, width])

    # 方式 1: pycocotools (推荐)
    try:
        from pycocotools import mask as mask_utils
        rle = {"counts": counts, "size": size}
        mask = mask_utils.decode(rle)
        return mask.astype(bool)
    except (ImportError, Exception):
        pass

    # 方式 2: 手动解码 (兼容 bytes 和 string 两种 RLE)
    return _manual_decode_rle(counts, size[0], size[1])


def _manual_decode_rle(counts, h: int, w: int) -> np.ndarray:
    """手动解码 RLE (string 格式的压缩 RLE)"""
    if isinstance(counts, bytes):
        # 二进制 RLE: 每对 (start, length)
        mask = np.zeros(h * w, dtype=np.uint8)
        pos = 0
        for i in range(0, len(counts), 2):
            start = counts[i]
            length = counts[i + 1]
            mask[start:start + length] = 1
        return mask.reshape(h, w).astype(bool)

    if isinstance(counts, str):
        # COCO 压缩 RLE string: 使用 LEB128 变长编码
        mask_flat = np.zeros(h * w, dtype=np.uint8)
        runs = _decode_rle_string(counts)
        pos = 0
        for i, run_len in enumerate(runs):
            if i % 2 == 1:  # 奇数索引是前景
                mask_flat[pos:pos + run_len] = 1
            pos += run_len
        return mask_flat.reshape(h, w).astype(bool)

    # list 格式
    if isinstance(counts, (list, tuple)):
        mask_flat = np.zeros(h * w, dtype=np.uint8)
        pos = 0
        for i, run_len in enumerate(counts):
            if i % 2 == 1:
                mask_flat[pos:pos + run_len] = 1
            pos += run_len
        return mask_flat.reshape(h, w).astype(bool)

    raise ValueError(f"不支持的 RLE 格式: {type(counts)}")


def _decode_rle_string(s: str) -> List[int]:
    """
    解码 COCO 压缩 RLE string (LEB128 编码)

    参考: https://github.com/cocodataset/cocoapi/blob/master/common/maskApi.c
    """
    counts = []
    pos = 0
    n = len(s)
    while pos < n:
        x = 0
        shift = 0
        more = True
        while more:
            c = ord(s[pos]) - 48  # ASCII 偏移
            x |= (c & 0x1f) << (5 * shift)
            more = c > 31
            pos += 1
            shift += 1
        # 首位奇偶性表示符号
        if x & 1:
            x = -(x >> 1)
        else:
            x = x >> 1
        if counts:
            x += counts[-1]
        counts.append(x)
    return counts


def load_gt_masks(json_path: Path, height: int = 960, width: int = 960) -> np.ndarray:
    """
    加载 JSON 标签文件，返回合并后的 GT mask

    Returns:
        gt_mask: [H, W] bool, True = 前景 (异常区域)
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    annotations = data.get("annotations", [])
    if not annotations:
        return np.zeros((height, width), dtype=bool)

    gt_mask = np.zeros((height, width), dtype=bool)
    for ann in annotations:
        mask = decode_rle_mask(ann, height, width)
        gt_mask |= mask

    return gt_mask


def compute_metrics(pred_mask: np.ndarray, gt_mask: np.ndarray) -> Dict[str, float]:
    """
    计算分割指标

    Args:
        pred_mask: [H, W] bool
        gt_mask: [H, W] bool

    Returns:
        dict with iou, precision, recall, f1, accuracy
    """
    pred = pred_mask.astype(bool)
    gt = gt_mask.astype(bool)

    tp = (pred & gt).sum()
    fp = (pred & ~gt).sum()
    fn = (~pred & gt).sum()
    tn = (~pred & ~gt).sum()

    total = pred.size

    iou = tp / max(tp + fp + fn, 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)
    accuracy = (tp + tn) / total

    # 面积比
    pred_area = pred.sum() / total
    gt_area = gt.sum() / total

    return {
        "iou": float(iou),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "accuracy": float(accuracy),
        "pred_area": float(pred_area),
        "gt_area": float(gt_area),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
    }


def get_sample_pairs(
    dataset_dir: Path,
    split: str = "train",
    num_samples: int = 20,
    seed: int = 42,
) -> List[Tuple[Path, Path]]:
    """获取图片-标签文件对"""
    split_dir = dataset_dir / split
    if not split_dir.exists():
        raise FileNotFoundError(f"数据集目录不存在: {split_dir}")

    # 查找所有 jpg 图片
    images = sorted(split_dir.glob("*.jpg"))
    if not images:
        images = sorted(split_dir.glob("*.png"))

    if not images:
        raise FileNotFoundError(f"未找到图片: {split_dir}")

    # 匹配标签
    pairs = []
    for img_path in images:
        json_path = img_path.with_suffix(".json")
        if json_path.exists():
            pairs.append((img_path, json_path))

    print(f"数据集: {split_dir}")
    print(f"  图片总数: {len(images)}")
    print(f"  有标签的: {len(pairs)}")

    # 随机采样
    rng = random.Random(seed)
    if num_samples < len(pairs):
        pairs = rng.sample(pairs, num_samples)

    print(f"  采样: {len(pairs)} 张")
    return pairs


def evaluate_segmentor(
    segmentor,
    pairs: List[Tuple[Path, Path]],
    classes_config: dict,
    threshold: float = 0.3,
    min_area: float = 0.01,
    anomaly_sigma: float = 1.5,
    sim_floor: float = 0.0,
    class_gate: float = 0.0,
    use_siglip_label: bool = True,
) -> Dict[str, float]:
    """
    在给定参数下评估分割器

    Returns:
        平均指标 dict (含 class_accuracy: 类别匹配准确率)
    """
    all_metrics = []
    inference_times = []
    class_correct = 0
    class_total = 0

    for img_path, json_path in pairs:
        # 加载图片
        image = cv2.imread(str(img_path))
        if image is None:
            continue

        h, w = image.shape[:2]

        # 加载 GT mask 和 GT 类别
        gt_mask = load_gt_masks(json_path, h, w)
        gt_class = _get_gt_class(json_path)

        # 推理
        t0 = time.time()
        results = segmentor.segment(
            image, classes_config,
            threshold=threshold,
            min_area=min_area,
            anomaly_sigma=anomaly_sigma,
            sim_floor=sim_floor,
            class_gate=class_gate,
            use_siglip_label=use_siglip_label,
        )
        dt = (time.time() - t0) * 1000
        inference_times.append(dt)

        # 合并所有预测 mask
        pred_mask = np.zeros((h, w), dtype=bool)
        # 找到面积最大的预测类别 (作为该图的预测类别)
        best_pred_class = None
        best_pred_area = 0
        for name, seg in results.items():
            m = seg.mask
            if m.shape != (h, w):
                m = cv2.resize(
                    seg.mask.astype(np.uint8), (w, h),
                    interpolation=cv2.INTER_NEAREST,
                ).astype(bool)
            pred_mask |= m
            if seg.area_ratio > best_pred_area:
                best_pred_area = seg.area_ratio
                best_pred_class = name

        metrics = compute_metrics(pred_mask, gt_mask)
        metrics["pred_class"] = best_pred_class or "none"
        metrics["gt_class"] = gt_class or "unknown"
        all_metrics.append(metrics)

        # 类别匹配
        if gt_class and best_pred_class:
            class_total += 1
            if gt_class == best_pred_class:
                class_correct += 1

    if not all_metrics:
        return {"iou": 0, "f1": 0, "precision": 0, "recall": 0}

    # 平均
    avg = {}
    for key in ["iou", "f1", "precision", "recall", "accuracy", "pred_area", "gt_area"]:
        avg[key] = np.mean([m[key] for m in all_metrics])
    avg["avg_inference_ms"] = np.mean(inference_times)
    avg["num_samples"] = len(all_metrics)
    avg["class_accuracy"] = class_correct / max(class_total, 1)

    return avg


def _get_gt_class(json_path: Path) -> Optional[str]:
    """从 GT JSON 中读取类别名称"""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("class_name")
    except Exception:
        return None


def grid_search(
    segmentor,
    pairs: List[Tuple[Path, Path]],
    classes_config: dict,
    output_path: Optional[str] = None,
) -> Dict[str, dict]:
    """
    网格搜索最优参数

    搜索空间:
      threshold: [0.1, 0.2, 0.3, 0.4, 0.5]
      anomaly_sigma: [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]
      min_area: [0.001, 0.005, 0.01, 0.02]
      sim_floor: [0.0, 0.02, 0.03, 0.05]
      class_gate: [0.0, 0.1, 0.2, 0.3]
    """
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]
    sigmas = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]
    min_areas = [0.001, 0.005, 0.01, 0.02]
    sim_floors = [0.0, 0.02, 0.03, 0.05]
    class_gates = [0.0, 0.1, 0.2, 0.3]

    total = len(thresholds) * len(sigmas) * len(min_areas) * len(sim_floors) * len(class_gates)
    print(f"\n网格搜索: {total} 种参数组合")
    print(f"  threshold: {thresholds}")
    print(f"  anomaly_sigma: {sigmas}")
    print(f"  min_area: {min_areas}")
    print(f"  sim_floor: {sim_floors}")
    print(f"  class_gate: {class_gates}")

    results_list = []
    best_f1 = -1
    best_params = {}
    best_metrics = {}

    count = 0
    for thr in thresholds:
        for sigma in sigmas:
            for min_a in min_areas:
                for sf in sim_floors:
                    for cg in class_gates:
                        count += 1
                        metrics = evaluate_segmentor(
                            segmentor, pairs, classes_config,
                            threshold=thr, anomaly_sigma=sigma, min_area=min_a,
                            sim_floor=sf, class_gate=cg,
                        )
                        f1 = metrics["f1"]

                        result_entry = {
                            "threshold": thr,
                            "anomaly_sigma": sigma,
                            "min_area": min_a,
                            "sim_floor": sf,
                            "class_gate": cg,
                            **metrics,
                        }
                        results_list.append(result_entry)

                        if f1 > best_f1:
                            best_f1 = f1
                            best_params = {
                                "threshold": thr,
                                "anomaly_sigma": sigma,
                                "min_area": min_a,
                                "sim_floor": sf,
                                "class_gate": cg,
                            }
                            best_metrics = metrics

                        if count % 100 == 0 or count == total:
                            print(f"  [{count}/{total}] best F1={best_f1:.4f} @ {best_params}")

    # 输出结果
    print(f"\n{'='*60}")
    print("网格搜索结果")
    print(f"{'='*60}")
    print(f"最优参数: {best_params}")
    print(f"最优 F1: {best_f1:.4f}")
    print(f"  IoU:       {best_metrics.get('iou', 0):.4f}")
    print(f"  Precision: {best_metrics.get('precision', 0):.4f}")
    print(f"  Recall:    {best_metrics.get('recall', 0):.4f}")

    # Top 10
    results_list.sort(key=lambda x: -x["f1"])
    print(f"\nTop 10 参数组合:")
    print(f"{'rank':>4}  {'threshold':>9}  {'sigma':>6}  {'min_area':>8}  {'sim_fl':>6}  {'cls_gt':>6}  {'F1':>6}  {'IoU':>6}  {'Prec':>6}  {'Recall':>6}")
    for i, r in enumerate(results_list[:10]):
        print(f"{i+1:>4}  {r['threshold']:>9.2f}  {r['anomaly_sigma']:>6.1f}  {r['min_area']:>8.3f}  "
              f"{r['sim_floor']:>6.2f}  {r['class_gate']:>6.2f}  "
              f"{r['f1']:>6.4f}  {r['iou']:>6.4f}  {r['precision']:>6.4f}  {r['recall']:>6.4f}")

    # 保存结果
    if output_path:
        output = {
            "best_params": best_params,
            "best_metrics": best_metrics,
            "all_results": results_list,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存: {output_path}")

    return {"best_params": best_params, "best_metrics": best_metrics, "all_results": results_list}


def _find_chinese_font() -> str:
    """查找系统中可用的中文字体"""
    import platform
    candidates = []
    if platform.system() == "Windows":
        candidates = [
            "C:/windows/Fonts/msyh.ttc",
            "C:/windows/Fonts/simhei.ttf",
            "C:/windows/Fonts/simsun.ttc",
        ]
    else:
        candidates = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def visualize_comparison(
    image: np.ndarray,
    results: dict,
    gt_mask: Optional[np.ndarray] = None,
    output_path: Optional[str] = None,
    show_gt: bool = True,
) -> np.ndarray:
    """
    清晰的可视化对比:
      - 预测区域: 类别色半透明覆盖 + 轮廓线 + 中心标签
      - GT 区域: 仅黄色轮廓线 (不填充), 清晰区分
      - 非异常区域: 保持原图 (不叠加任何效果)
      - 左下角: IoU / F1 指标
    """
    from PIL import Image, ImageDraw, ImageFont

    h, w = image.shape[:2]
    vis = image.copy()

    # 类别颜色 (BGR)
    CLASS_COLORS = {
        "black_water": (0, 0, 180),
        "brown_water": (42, 42, 165),
        "yellow_water": (0, 255, 255),
        "green_water": (0, 200, 0),
        "red_water": (0, 0, 255),
        "milky_water": (200, 200, 200),
        "foam_water": (180, 180, 255),
        "dam_seepage": (100, 100, 100),
        "anomaly": (0, 200, 200),
    }

    # ── 1. 预测区域: 类别色半透明覆盖 ──
    for cls_name, seg in results.items():
        color = CLASS_COLORS.get(cls_name, (128, 128, 128))
        mask = seg.mask
        if mask.shape != (h, w):
            mask = cv2.resize(mask.astype(np.uint8), (w, h),
                              interpolation=cv2.INTER_NEAREST).astype(bool)

        # 半透明覆盖 (仅预测区域)
        overlay = np.zeros_like(vis)
        overlay[mask] = color
        vis = cv2.addWeighted(vis, 0.6, overlay, 0.4, 0)

    # ── 2. 预测区域: 轮廓线 (更粗, 类别色) ──
    for cls_name, seg in results.items():
        color = CLASS_COLORS.get(cls_name, (128, 128, 128))
        mask = seg.mask
        if mask.shape != (h, w):
            mask = cv2.resize(mask.astype(np.uint8), (w, h),
                              interpolation=cv2.INTER_NEAREST).astype(bool)
        contours, _ = cv2.findContours(
            mask.astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, contours, -1, color, 3)

    # ── 3. GT: 仅黄色轮廓线 (不填充) ──
    if gt_mask is not None and show_gt:
        gt_uint8 = gt_mask.astype(np.uint8) * 255
        contours_gt, _ = cv2.findContours(gt_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # 用虚线效果: 先画粗黄色再画细黑色内部
        cv2.drawContours(vis, contours_gt, -1, (0, 255, 255), 3)
        cv2.drawContours(vis, contours_gt, -1, (0, 200, 200), 1)

    # ── 4. PIL 渲染中文标签 ──
    vis_rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
    vis_pil = Image.fromarray(vis_rgb)
    draw = ImageDraw.Draw(vis_pil)

    font_path = _find_chinese_font()
    try:
        font = ImageFont.truetype(font_path, 18)
        font_small = ImageFont.truetype(font_path, 13)
    except Exception:
        font = ImageFont.load_default()
        font_small = font

    # ── 5. 每个类别: 区域中心标注 ──
    for cls_name, seg in results.items():
        mask = seg.mask
        if mask.shape != (h, w):
            mask = cv2.resize(mask.astype(np.uint8), (w, h),
                              interpolation=cv2.INTER_NEAREST).astype(bool)

        ys, xs = np.where(mask)
        if len(ys) == 0:
            continue

        cy, cx = int(ys.mean()), int(xs.mean())
        color = CLASS_COLORS.get(cls_name, (128, 128, 128))
        color_rgb = (color[2], color[1], color[0])

        label = f"预测: {seg.class_name_cn} {seg.area_ratio:.0%}"
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        tx = max(5, min(cx - tw // 2, w - tw - 5))
        ty = max(5, min(cy - th // 2, h - th - 5))

        # 白色描边 + 类别色文字
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx or dy:
                    draw.text((tx + dx, ty + dy), label, font=font, fill=(255, 255, 255))
        draw.text((tx, ty), label, font=font, fill=color_rgb)

    # ── 6. 左下角: IoU / F1 ──
    if gt_mask is not None:
        merged_pred = np.zeros((h, w), dtype=bool)
        for cls_name, seg in results.items():
            m = seg.mask
            if m.shape != (h, w):
                m = cv2.resize(m.astype(np.uint8), (w, h),
                               interpolation=cv2.INTER_NEAREST).astype(bool)
            merged_pred |= m
        metrics = compute_metrics(merged_pred, gt_mask)

        metric_text = f"IoU={metrics['iou']:.3f}  F1={metrics['f1']:.3f}"
        bbox = draw.textbbox((0, 0), metric_text, font=font_small)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        mx, my = 10, h - th - 12
        draw.rectangle([mx - 3, my - 2, mx + tw + 3, my + th + 2], fill=(0, 0, 0, 180))
        draw.text((mx, my), metric_text, font=font_small, fill=(255, 255, 255))

    # ── 7. 右下角: 图例 ──
    if gt_mask is not None and show_gt:
        gt_label = "黄线=GT边界  彩色=预测区域"
        bbox2 = draw.textbbox((0, 0), gt_label, font=font_small)
        tw2 = bbox2[2] - bbox2[0]
        th2 = bbox2[3] - bbox2[1]
        gx, gy = w - tw2 - 12, h - th2 - 12
        draw.rectangle([gx - 3, gy - 2, gx + tw2 + 3, gy + th2 + 2], fill=(0, 0, 0, 180))
        draw.text((gx, gy), gt_label, font=font_small, fill=(0, 255, 255))

    vis = cv2.cvtColor(np.array(vis_pil), cv2.COLOR_RGB2BGR)

    if output_path:
        cv2.imwrite(output_path, vis)

    return vis


def main():
    parser = argparse.ArgumentParser(description="GT 评估 + 参数优化")
    parser.add_argument("--num-samples", type=int, default=20, help="采样数量")
    parser.add_argument("--split", type=str, default="train", choices=["train", "valid"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--input-size", type=int, default=896)

    # 分割参数
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--anomaly-sigma", type=float, default=1.5)
    parser.add_argument("--min-area", type=float, default=0.01)
    parser.add_argument("--sim-floor", type=float, default=0.0,
                        help="绝对相似度下限 (0=不过滤)")
    parser.add_argument("--class-gate", type=float, default=0.0,
                        help="SigLIP2 类别门限 (0=不过滤)")
    parser.add_argument("--use-siglip-label", type=lambda x: x.lower() in ("true", "1", "yes"),
                        default=True,
                        help="True=混合模式(patch区域+SigLIP2标签,推荐); "
                             "False=原始patch匹配(支持多区域但标签可能不准)")

    # 检测类别 (逗号分隔, 为空则使用配置文件中的全部类别)
    parser.add_argument("--classes", type=str, default=None,
                        help="指定检测类别, 逗号分隔, 如 green_water,black_water")

    # 网格搜索
    parser.add_argument("--grid-search", action="store_true", help="执行网格搜索")

    # 模型路径
    parser.add_argument("--checkpoint", type=str, default=None)
    parser.add_argument("--radio-code-dir", type=str, default=None)
    parser.add_argument("--siglip2-dir", type=str, default=None)

    # 数据集路径
    parser.add_argument("--dataset-dir", type=str,
                        default=str(PROJECT_ROOT / "data" / "processed" / "tt.v6i.sam2"))

    # 输出
    parser.add_argument("--output-dir", type=str,
                        default=str(PROJECT_ROOT / "data" / "evaluation"))
    parser.add_argument("--visualize", action="store_true", help="生成对比可视化")
    parser.add_argument("--vis-count", type=int, default=5, help="可视化样本数")
    args = parser.parse_args()

    # ── 加载分割器 ──
    print("=" * 60)
    print("C-RADIOv4 GT 评估 + 参数优化")
    print("=" * 60)

    from models.open_vocab.radio_segmentor import CRadioV4Segmentor

    segmentor = CRadioV4Segmentor(
        checkpoint_path=args.checkpoint,
        radio_code_dir=args.radio_code_dir,
        siglip2_dir=args.siglip2_dir,
        device=args.device,
        input_size=args.input_size,
    )

    # ── 加载配置 ──
    import yaml
    config_path = PROJECT_ROOT / "configs" / "water_inspection.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    classes_config = config.get("cloud", {}).get("radio", {}).get("classes", {})
    if not classes_config:
        classes_config = config.get("dinov3_sam3", {}).get("classes", {})

    # 按用户指定的类别过滤
    if args.classes:
        selected = [c.strip() for c in args.classes.split(",")]
        classes_config = {k: v for k, v in classes_config.items() if k in selected}
        print(f"  指定类别: {list(classes_config.keys())}")
    else:
        print(f"  全部类别 ({len(classes_config)} 类): {list(classes_config.keys())}")

    # ── 加载数据 ──
    dataset_dir = Path(args.dataset_dir)
    pairs = get_sample_pairs(dataset_dir, args.split, args.num_samples, args.seed)

    # ── 评估 ──
    print(f"\n评估参数: threshold={args.threshold}, use_siglip_label={args.use_siglip_label}")
    avg_metrics = evaluate_segmentor(
        segmentor, pairs, classes_config,
        threshold=args.threshold,
        anomaly_sigma=args.anomaly_sigma,
        min_area=args.min_area,
        sim_floor=args.sim_floor,
        class_gate=args.class_gate,
        use_siglip_label=args.use_siglip_label,
    )

    print(f"\n评估结果 ({avg_metrics['num_samples']} 张):")
    print(f"  IoU:            {avg_metrics['iou']:.4f}")
    print(f"  F1:             {avg_metrics['f1']:.4f}")
    print(f"  Precision:      {avg_metrics['precision']:.4f}")
    print(f"  Recall:         {avg_metrics['recall']:.4f}")
    print(f"  Class Accuracy: {avg_metrics.get('class_accuracy', 0):.4f}  (预测主类别与GT类别匹配率)")
    print(f"  Avg pred area:  {avg_metrics['pred_area']:.4f}")
    print(f"  Avg GT area:    {avg_metrics['gt_area']:.4f}")
    print(f"  Avg inference:  {avg_metrics['avg_inference_ms']:.1f} ms")

    # ── 网格搜索 ──
    if args.grid_search:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        grid_results = grid_search(
            segmentor, pairs, classes_config,
            output_path=str(output_dir / "grid_search_results.json"),
        )

        # 用最优参数重新评估
        best = grid_results["best_params"]
        print(f"\n用最优参数重新评估: {best}")
        best_metrics = evaluate_segmentor(
            segmentor, pairs, classes_config,
            threshold=best["threshold"],
            anomaly_sigma=best["anomaly_sigma"],
            min_area=best["min_area"],
            sim_floor=best.get("sim_floor", 0.0),
            class_gate=best.get("class_gate", 0.0),
        )
        print(f"  IoU: {best_metrics['iou']:.4f}, F1: {best_metrics['f1']:.4f}")

    # ── 可视化 ──
    if args.visualize:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        vis_pairs = pairs[:args.vis_count]
        print(f"\n生成可视化 ({len(vis_pairs)} 张)...")

        for i, (img_path, json_path) in enumerate(vis_pairs):
            image = cv2.imread(str(img_path))
            if image is None:
                continue

            h, w = image.shape[:2]
            gt_mask = load_gt_masks(json_path, h, w)
            gt_class = _get_gt_class(json_path)

            results = segmentor.segment(
                image, classes_config,
                threshold=args.threshold,
                anomaly_sigma=args.anomaly_sigma,
                min_area=args.min_area,
                sim_floor=args.sim_floor,
                class_gate=args.class_gate,
                use_siglip_label=args.use_siglip_label,
            )

            # 合并预测 mask 用于计算指标
            pred_mask = np.zeros((h, w), dtype=bool)
            best_pred_class = None
            best_pred_area = 0
            for name, seg in results.items():
                if seg.mask.shape != (h, w):
                    pred_mask |= cv2.resize(
                        seg.mask.astype(np.uint8), (w, h),
                        interpolation=cv2.INTER_NEAREST,
                    ).astype(bool)
                else:
                    pred_mask |= seg.mask
                if seg.area_ratio > best_pred_area:
                    best_pred_area = seg.area_ratio
                    best_pred_class = name

            metrics = compute_metrics(pred_mask, gt_mask)
            out_path = str(output_dir / f"compare_{i:02d}_iou{metrics['iou']:.3f}.jpg")

            # 按类别可视化 (每个类别用不同颜色)
            visualize_comparison(
                image, results, gt_mask, out_path, show_gt=True,
            )

            # 同步原图到输出目录，方便对比
            orig_dst = str(output_dir / f"original_{i:02d}_{img_path.name}")
            shutil.copy2(str(img_path), orig_dst)

            gt_cn = classes_config.get(gt_class, {}).get("zh", gt_class or "?")
            match_str = "✓" if gt_class == best_pred_class else "✗"
            print(f"  [{i}] IoU={metrics['iou']:.3f} F1={metrics['f1']:.3f} | "
                  f"GT={gt_class}({gt_cn}) 预测={best_pred_class} {match_str} → {out_path}")

        print(f"\n可视化已保存到 {output_dir}")

    print("\n评估完成!")


if __name__ == "__main__":
    main()
