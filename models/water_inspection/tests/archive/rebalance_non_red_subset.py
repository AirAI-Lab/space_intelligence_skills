#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将指定编号区间替换为非 red_water 的均衡样本（直接读取 tt.v6i.sam2 标注）。
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np


CLASS_ZH = {
    "black_water": "黑水",
    "brown_water": "褐色水",
    "yellow_water": "黄色水",
    "green_water": "绿水/藻类",
    "red_water": "红水",
    "milky_water": "浑浊水",
    "foam_water": "泡沫水",
    "dam_seepage": "坝体渗水",
    "normal_water": "正常水质",
}

TARGET_NON_RED = ["green_water", "brown_water", "black_water", "milky_water", "dam_seepage"]


def decode_rle(seg: dict) -> np.ndarray:
    from pycocotools import mask as mask_utils

    rle = {"size": seg["size"], "counts": seg["counts"]}
    m = mask_utils.decode(rle)
    if m.ndim == 3:
        m = m[:, :, 0]
    return (m > 0).astype(np.uint8) * 255


def compute_bbox(mask_u8: np.ndarray):
    ys, xs = np.where(mask_u8 > 127)
    if len(ys) == 0:
        return [0, 0, 0, 0]
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--source-root", required=True)
    ap.add_argument("--start-index", type=int, default=91)
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260404)
    args = ap.parse_args()

    random.seed(args.seed)

    project_root = Path(args.project_root)
    source_root = Path(args.source_root)

    test_results = project_root / "data" / "test_results"
    gt_meta = project_root / "data" / "evaluation" / "manual_gt" / "meta"
    gt_masks = project_root / "data" / "evaluation" / "manual_gt" / "masks"

    test_results.mkdir(parents=True, exist_ok=True)
    gt_meta.mkdir(parents=True, exist_ok=True)
    gt_masks.mkdir(parents=True, exist_ok=True)

    by_cls = defaultdict(list)
    for split in ["train", "valid"]:
        for ann_path in (source_root / split).glob("*.json"):
            try:
                ann = json.loads(ann_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            anns = ann.get("annotations", [])
            classes = [a.get("class_name") for a in anns if a.get("class_name")]
            if not classes:
                continue
            uniq = set(classes)
            # 仅要非红样本，避免混入 red_water
            if "red_water" in uniq:
                continue
            usable = [c for c in uniq if c in TARGET_NON_RED]
            if not usable:
                continue
            key = usable[0]
            by_cls[key].append((split, ann_path.stem + ".jpg", ann_path))

    quotas = {
        "green_water": max(2, args.count // 4),
        "brown_water": 2,
        "black_water": 2,
        "milky_water": 2,
        "dam_seepage": 2,
    }

    picked = []
    used = set()
    for c in TARGET_NON_RED:
        pool = by_cls.get(c, [])
        random.shuffle(pool)
        take = min(len(pool), quotas.get(c, 1))
        for item in pool[:take]:
            k = (item[0], item[1])
            if k not in used:
                picked.append(item)
                used.add(k)

    if len(picked) < args.count:
        all_pool = []
        for c in TARGET_NON_RED:
            all_pool.extend(by_cls.get(c, []))
        random.shuffle(all_pool)
        for item in all_pool:
            if len(picked) >= args.count:
                break
            k = (item[0], item[1])
            if k in used:
                continue
            picked.append(item)
            used.add(k)

    picked = picked[: args.count]

    idx = args.start_index
    manifest = []
    for split, img_name, ann_path in picked:
        src_img = source_root / split / img_name
        if not src_img.exists():
            continue

        out_img_name = f"{idx}.jpg"
        out_img = test_results / out_img_name

        img = cv2.imread(str(src_img))
        if img is None:
            continue
        cv2.imwrite(str(out_img), img)

        ann = json.loads(ann_path.read_text(encoding="utf-8"))
        classes = []
        class_counter = defaultdict(int)
        for a in ann.get("annotations", []):
            cname = a.get("class_name")
            if cname not in TARGET_NON_RED:
                continue
            seg = a.get("segmentation")
            if not seg or "counts" not in seg:
                continue

            mk = decode_rle(seg)
            if mk.shape[:2] != img.shape[:2]:
                mk = cv2.resize(mk, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)

            class_counter[cname] += 1
            suffix = class_counter[cname]
            mask_file = f"{idx}__{cname}__{suffix}.png"
            cv2.imwrite(str(gt_masks / mask_file), mk)

            classes.append(
                {
                    "class": cname,
                    "class_zh": CLASS_ZH.get(cname, cname),
                    "area_ratio": float((mk > 127).sum()) / float(mk.size),
                    "bbox": compute_bbox(mk),
                    "mask_file": mask_file,
                }
            )

        if not classes:
            idx += 1
            continue

        meta = {
            "image": out_img_name,
            "active_class": classes[0]["class"],
            "classes": classes,
        }
        (gt_meta / f"{idx}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        manifest.append(
            {
                "index": idx,
                "source_split": split,
                "source_file": img_name,
                "target_image": out_img_name,
                "labels": sorted(list({c["class"] for c in classes})),
            }
        )
        idx += 1

    end_index = args.start_index + max(len(manifest), 0) - 1
    out_report = project_root / "data" / "evaluation" / f"rebalanced_{args.start_index}_{end_index}_manifest.json"
    out_report.write_text(json.dumps({"generated": len(manifest), "manifest": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"generated": len(manifest), "report": str(out_report)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
