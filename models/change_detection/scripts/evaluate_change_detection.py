#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
变换检测评估脚本

支持两种模式:
  1. 单帧检测: 对指定目录的图像逐张检测
  2. 对比检测: 对 earlier/later 配对图像进行变化检测

使用方法:
  # 对比检测
  python evaluate_change_detection.py --mode compare \\
      --data_dir /app/data/change_detection \\
      --config models/change_detection/configs/change_detection.yaml

  # 单帧检测
  python evaluate_change_detection.py --mode single \\
      --data_dir /app/data/images \\
      --config models/change_detection/configs/change_detection.yaml

作者: 空中智能体团队
日期: 2026-04-07
"""

import os
import sys
import json
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

# 路径设置
sys.path.insert(0, '/app/models/water_inspection')
sys.path.insert(0, '/app/water_inspection')
sys.path.insert(0, '/app/models')

from change_detection.models.unified import ChangeDetector, ALERT_CLASSES


def find_pairs(data_dir: str) -> list:
    """查找配对的 earlier/later 图像 (按序号匹配)"""
    earlier_dir = Path(data_dir) / "earlier"
    later_dir = Path(data_dir) / "later"
    if not earlier_dir.exists() or not later_dir.exists():
        raise FileNotFoundError(f"需要 earlier/ 和 later/ 子目录: {data_dir}")

    exts = {'.jpg', '.jpeg', '.png', '.bmp'}

    def get_seq(f):
        """提取文件名中的序号 (如 0001, 0003)"""
        import re
        m = re.search(r'_(\d{4})_', f.stem)
        return m.group(1) if m else f.stem

    later_map = {get_seq(f): f for f in later_dir.iterdir() if f.suffix.lower() in exts}

    pairs = []
    for f in sorted(earlier_dir.iterdir()):
        if f.suffix.lower() not in exts:
            continue
        seq = get_seq(f)
        if seq in later_map:
            pairs.append((str(f), str(later_map[seq])))
        else:
            print(f"  ⚠️ 未找到配对: {f.name}")
    return pairs


def find_images(data_dir: str) -> list:
    """查找目录下所有图像"""
    p = Path(data_dir)
    exts = {'.jpg', '.jpeg', '.png', '.bmp'}
    return sorted([str(f) for f in p.iterdir() if f.suffix.lower() in exts])


def run_compare(detector, data_dir, output_dir):
    """对比检测模式"""
    pairs = find_pairs(data_dir)
    print(f"\n找到 {len(pairs)} 对配对图像\n")

    all_results = []
    for i, (ep, lp) in enumerate(pairs, 1):
        name = Path(ep).stem
        print(f"[{i}/{len(pairs)}] {name}")

        e = cv2.imread(ep)
        l = cv2.imread(lp)
        if e is None or l is None:
            print("  ⚠️ 无法读取，跳过")
            continue

        result = detector.detect_changes(e, l)
        vis_path = str(output_dir / "visualizations" / f"{name}_change.jpg")
        detector.visualize_changes(e, l, result, vis_path)

        print(f"  变化: {len(result.change_regions)} 个区域")
        for r in result.change_regions:
            print(f"    {r.change_type}: {r.class_name_cn} ({r.area_ratio*100:.1f}%)")

        all_results.append({
            "name": name, "has_change": result.has_change,
            "change_count": len(result.change_regions),
            "inference_time_ms": result.inference_time_ms,
            "changes": [{
                "class": r.class_name, "class_cn": r.class_name_cn,
                "type": r.change_type, "area_ratio": r.area_ratio,
            } for r in result.change_regions],
            "summary": result.change_summary,
        })
        print()

    return all_results


def run_single(detector, data_dir, output_dir):
    """单帧检测模式"""
    images = find_images(data_dir)
    print(f"\n找到 {len(images)} 张图像\n")

    all_results = []
    for i, img_path in enumerate(images, 1):
        name = Path(img_path).stem
        print(f"[{i}/{len(images)}] {name}")

        img = cv2.imread(img_path)
        if img is None:
            print("  ⚠️ 无法读取，跳过")
            continue

        result = detector.detect_single(img)
        vis_path = str(output_dir / "visualizations" / f"{name}_detect.jpg")
        detector.visualize_single(img, result, vis_path)

        alerts = [d for d in result.detections if d.class_name in ALERT_CLASSES]
        print(f"  检测: {len(result.detections)} 个目标, {len(alerts)} 个告警")
        for d in result.detections:
            mark = "⚠️ " if d.class_name in ALERT_CLASSES else "  "
            print(f"    {mark}{d.class_name_cn}: {d.area_ratio*100:.1f}%")

        all_results.append({
            "name": name,
            "detections": len(result.detections),
            "alerts": len(alerts),
            "inference_time_ms": result.inference_time_ms,
            "items": [{
                "class": d.class_name, "class_cn": d.class_name_cn,
                "area_ratio": d.area_ratio, "is_alert": d.class_name in ALERT_CLASSES,
            } for d in result.detections],
        })
        print()

    return all_results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="变换检测评估")
    parser.add_argument("--config", default="models/change_detection/configs/change_detection.yaml")
    parser.add_argument("--mode", choices=["single", "compare"], default="compare")
    parser.add_argument("--data_dir", default="/app/data/change_detection")
    parser.add_argument("--output_dir", default="outputs/change_detection")
    args = parser.parse_args()

    print("=" * 70)
    print(f"变换检测评估 ({args.mode} 模式)")
    print("=" * 70)
    print(f"时间: {datetime.now().isoformat()}")
    print(f"数据: {args.data_dir}")
    print()

    output_dir = Path(args.output_dir)
    (output_dir / "visualizations").mkdir(parents=True, exist_ok=True)

    detector = ChangeDetector(config_path=args.config)
    print()

    if args.mode == "compare":
        results = run_compare(detector, args.data_dir, output_dir)
    else:
        results = run_single(detector, args.data_dir, output_dir)

    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": args.mode,
        "total": len(results),
        "results": results,
    }

    report_path = str(output_dir / "report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"{'='*70}")
    print(f"评估完成: {len(results)} 张, 报告: {report_path}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
