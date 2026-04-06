#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RADSeg 水质分割器完整评估脚本 v2.0

支持:
  1. 可选的 DINOv3-7B 增强模块
  2. 可选的 SAM3 边界精化模块
  3. 配置化对比测试
"""

import sys
import yaml
import json
import cv2
import numpy as np
from pathlib import Path
from collections import defaultdict
import time
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))


def evaluate_dataset(
    segmentor,
    classes_config: dict,
    data_dir: Path,
    verbose: bool = True,
) -> dict:
    """评估完整数据集"""
    images_dir = data_dir / "images"
    meta_dir = data_dir / "meta"

    images = sorted(
        list(images_dir.glob("*.jpg")) +
        list(images_dir.glob("*.jpeg")) +
        list(images_dir.glob("*.png"))
    )

    results = []
    class_stats = defaultdict(lambda: {"total": 0, "detected": 0, "correct": 0})
    confusion = defaultdict(lambda: defaultdict(int))

    total_time = 0

    for img_path in images:
        image = cv2.imread(str(img_path))
        if image is None:
            continue

        meta_path = meta_dir / f"{img_path.stem}.json"
        if not meta_path.exists():
            continue

        with open(meta_path, "r") as f:
            meta = json.load(f)

        gt_class = meta.get("active_class")
        if not gt_class:
            continue

        t0 = time.time()
        seg_results = segmentor.segment(image, classes_config)
        elapsed = time.time() - t0
        total_time += elapsed

        detected_class = None
        detected_score = 0
        for cls_name, seg in seg_results.items():
            if seg.score > detected_score:
                detected_score = seg.score
                detected_class = cls_name

        is_detected = detected_class is not None and detected_class != "normal_water"
        is_correct = detected_class == gt_class

        class_stats[gt_class]["total"] += 1
        if is_detected:
            class_stats[gt_class]["detected"] += 1
        if is_correct:
            class_stats[gt_class]["correct"] += 1

        if detected_class:
            confusion[gt_class][detected_class] += 1

        gt_cn = classes_config.get(gt_class, {}).get("zh", gt_class)
        det_cn = classes_config.get(detected_class, {}).get("zh", detected_class) if detected_class else "-"
        status = "OK" if is_correct else ("?" if is_detected else "X")

        if verbose:
            print(f"[{status}] {img_path.name:<12} GT: {gt_cn:<10} | Pred: {det_cn:<10} ({detected_score:.0%}) | {elapsed:.2f}s")

        results.append({
            "image": img_path.name,
            "gt_class": gt_class,
            "detected_class": detected_class,
            "detected_score": detected_score,
            "is_correct": is_correct,
            "elapsed": elapsed,
        })

    total = len(results)
    detected = sum(1 for r in results if r["detected_class"] and r["detected_class"] != "normal_water")
    correct = sum(1 for r in results if r["is_correct"])

    return {
        "total": total,
        "detected": detected,
        "correct": correct,
        "detection_rate": detected / max(total, 1),
        "accuracy": correct / max(total, 1),
        "precision": correct / max(detected, 1),
        "avg_time": total_time / max(total, 1),
        "class_stats": dict(class_stats),
        "confusion": dict(confusion),
    }


def print_summary(stats: dict, classes_config: dict, title: str = "评估摘要"):
    """打印评估摘要"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    print(f"\n总样本: {stats['total']}")
    print(f"检出数: {stats['detected']} ({stats['detection_rate']:.0%})")
    print(f"正确数: {stats['correct']} ({stats['accuracy']:.0%})")
    print(f"准确率: {stats['precision']:.0%} (正确/检出)")
    print(f"平均推理时间: {stats['avg_time']:.2f}s/张")

    print("\n按类别统计:")
    for cls, s in sorted(stats["class_stats"].items()):
        t, d, c = s["total"], s["detected"], s["correct"]
        cls_cn = classes_config.get(cls, {}).get("zh", cls)
        print(f"  {cls_cn:<10} ({t:>2}张): 检出 {d}/{t}, 正确 {c}/{t}")

    print("\n混淆矩阵 (GT -> Pred):")
    for gt_cls, preds in sorted(stats["confusion"].items()):
        gt_cn = classes_config.get(gt_cls, {}).get("zh", gt_cls)
        pred_strs = []
        for pred_cls, count in sorted(preds.items(), key=lambda x: -x[1]):
            pred_cn = classes_config.get(pred_cls, {}).get("zh", pred_cls)
            pred_strs.append(f"{pred_cn}({count})")
        print(f"  {gt_cn:<10} -> {', '.join(pred_strs)}")


def main():
    parser = argparse.ArgumentParser(description="RADSeg 水质分割器评估")
    parser.add_argument("--use-dino", type=int, default=0, help="启用 DINOv3-7B (1/0)")
    parser.add_argument("--use-sam", type=int, default=0, help="启用 SAM3 (1/0)")
    parser.add_argument("--use-scra", type=int, default=1, help="启用 SCRA (1/0)")
    parser.add_argument("--temperature", type=float, default=10.0, help="温度参数")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    parser.add_argument("--compare", action="store_true", help="对比模式: 测试所有配置")
    args = parser.parse_args()

    # 加载配置
    config_path = Path(__file__).parent.parent / "configs" / "water_inspection.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    ckpt = "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar"
    radio = "/app/models/NVlabs_RADIO"
    siglip = "/app/models/siglip2-giant-opt-patch16-384"

    classes_config = config.get("cloud", {}).get("radio", {}).get("classes", {})
    data_dir = Path(__file__).parent.parent / "data" / "datasets"

    if args.compare:
        # 对比模式: 测试多种配置
        configs_to_test = [
            {"name": "Baseline (SigLIP2 only)", "dino": 0, "sam": 0, "scra": 0},
            {"name": "+SCRA", "dino": 0, "sam": 0, "scra": 1},
            {"name": "+SCRA+DINOv3", "dino": 1, "sam": 0, "scra": 1},
            {"name": "+SCRA+SAM3", "dino": 0, "sam": 1, "scra": 1},
            {"name": "+SCRA+DINO+SAM", "dino": 1, "sam": 1, "scra": 1},
        ]

        results = []
        for cfg in configs_to_test:
            print(f"\n{'='*60}")
            print(f"测试配置: {cfg['name']}")
            print(f"{'='*60}")

            from models.open_vocab.radseg_segmentor import RADSegWaterSegmentor

            segmentor = RADSegWaterSegmentor(
                checkpoint_path=ckpt,
                radio_code_dir=radio,
                siglip2_dir=siglip,
                config=config,
                use_scra=bool(cfg["scra"]),
                use_dino=bool(cfg["dino"]),
                use_sam=bool(cfg["sam"]),
                temperature=args.temperature,
            )

            stats = evaluate_dataset(
                segmentor, classes_config, data_dir, verbose=False
            )
            stats["config"] = cfg["name"]
            results.append(stats)

            print(f"检出率: {stats['detection_rate']:.0%}, 准确率: {stats['accuracy']:.0%}, 精确率: {stats['precision']:.0%}")

        # 打印对比摘要
        print("\n" + "=" * 60)
        print("对比摘要")
        print("=" * 60)
        print(f"{'配置':<25s} | {'检出率':>6s} | {'准确率':>6s} | {'精确率':>6s}")
        print("-" * 60)
        for r in results:
            print(f"{r['config']:<25s} | {r['detection_rate']:>6.0%} | {r['accuracy']:>6.0%} | {r['precision']:>6.0%}")

        # 保存对比结果
        output_dir = Path(__file__).parent.parent / "data" / "evaluation"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "comparison_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n对比结果已保存: {output_file}")

    else:
        # 单次测试
        from models.open_vocab.radseg_segmentor import RADSegWaterSegmentor

        print("=" * 60)
        print(f"RADSeg 水质分割器评估")
        print(f"  DINO: {bool(args.use_dino)}, SAM: {bool(args.use_sam)}, SCRA: {bool(args.use_scra)}")
        print(f"  Temperature: {args.temperature}")
        print("=" * 60)

        segmentor = RADSegWaterSegmentor(
            checkpoint_path=ckpt,
            radio_code_dir=radio,
            siglip2_dir=siglip,
            config=config,
            use_scra=bool(args.use_scra),
            use_dino=bool(args.use_dino),
            use_sam=bool(args.use_sam),
            temperature=args.temperature,
        )

        stats = evaluate_dataset(
            segmentor, classes_config, data_dir, verbose=not args.quiet
        )

        print_summary(stats, classes_config)


if __name__ == "__main__":
    main()
