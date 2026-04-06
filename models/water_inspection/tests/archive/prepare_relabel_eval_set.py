#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从 relabel_report + tt.v6i.sam2 生成评估补充集：
- 分层抽样 N 张（尽量覆盖不同异常类）
- 复制到 data/test_results，重命名为 start_index..start_index+N-1
- 生成 manual_gt/meta 与 manual_gt/masks 对应文件
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


def decode_rle(seg: dict) -> np.ndarray:
    try:
        from pycocotools import mask as mask_utils
    except Exception as e:
        raise RuntimeError("pycocotools is required to decode RLE masks") from e

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


def stratified_pick(entries, n, seed=42):
    random.seed(seed)
    by_cls = defaultdict(list)
    for e in entries:
        by_cls[e["new_class"]].append(e)

    classes = sorted(by_cls.keys(), key=lambda c: len(by_cls[c]))
    picked = []

    # 先保障稀有类尽量覆盖
    for c in classes:
        if len(picked) >= n:
            break
        pool = by_cls[c]
        if not pool:
            continue
        take = 1 if len(pool) >= 1 else 0
        if c in {"black_water", "milky_water", "dam_seepage", "brown_water"}:
            take = min(2, len(pool))
        random.shuffle(pool)
        for it in pool[:take]:
            if len(picked) < n:
                picked.append(it)

    # 剩余按类内均匀补齐
    cls_cycle = []
    for c in sorted(by_cls.keys(), key=lambda x: -len(by_cls[x])):
        tmp = by_cls[c][:]
        random.shuffle(tmp)
        cls_cycle.extend(tmp)

    used = {(x["split"], x["file"]) for x in picked}
    for it in cls_cycle:
        if len(picked) >= n:
            break
        k = (it["split"], it["file"])
        if k in used:
            continue
        picked.append(it)
        used.add(k)

    return picked[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=str, required=True)
    ap.add_argument("--source-root", type=str, required=True)
    ap.add_argument("--relabel-report", type=str, required=True)
    ap.add_argument("--count", type=int, default=50)
    ap.add_argument("--start-index", type=int, default=51)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    project_root = Path(args.project_root)
    source_root = Path(args.source_root)

    test_results = project_root / "data" / "test_results"
    gt_meta = project_root / "data" / "evaluation" / "manual_gt" / "meta"
    gt_masks = project_root / "data" / "evaluation" / "manual_gt" / "masks"

    for p in [test_results, gt_meta, gt_masks]:
        p.mkdir(parents=True, exist_ok=True)

    rep = json.loads(Path(args.relabel_report).read_text(encoding="utf-8"))
    entries = [x for x in rep.get("results", []) if x.get("changed", True)]
    picked = stratified_pick(entries, args.count, seed=args.seed)

    out_manifest = []

    idx = args.start_index
    for e in picked:
        split = e["split"]
        fname = e["file"]
        src_img = source_root / split / fname
        src_ann = source_root / split / (Path(fname).stem + ".json")
        if (not src_img.exists()) or (not src_ann.exists()):
            continue

        out_img_name = f"{idx}.jpg"
        out_img = test_results / out_img_name

        img = cv2.imread(str(src_img))
        if img is None:
            continue
        cv2.imwrite(str(out_img), img)

        ann = json.loads(src_ann.read_text(encoding="utf-8"))
        classes = []
        ann_list = ann.get("annotations", [])
        for ai, a in enumerate(ann_list):
            cname = a.get("class_name") or e.get("new_class")
            if not cname:
                continue
            seg = a.get("segmentation")
            if not seg or "counts" not in seg:
                continue

            mk = decode_rle(seg)
            if mk.shape[:2] != img.shape[:2]:
                mk = cv2.resize(mk, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)

            mask_file = f"{idx}__{cname}.png"
            mask_path = gt_masks / mask_file
            cv2.imwrite(str(mask_path), mk)

            area_ratio = float((mk > 127).sum()) / float(mk.size)
            bbox = compute_bbox(mk)
            classes.append(
                {
                    "class": cname,
                    "class_zh": CLASS_ZH.get(cname, cname),
                    "area_ratio": area_ratio,
                    "bbox": bbox,
                    "mask_file": mask_file,
                }
            )

        if not classes:
            # 没有可解码异常时按重标类别兜底，mask 用空
            cname = e.get("new_class", "normal_water")
            mask_file = f"{idx}__{cname}.png"
            empty = np.zeros(img.shape[:2], dtype=np.uint8)
            cv2.imwrite(str(gt_masks / mask_file), empty)
            classes = [
                {
                    "class": cname,
                    "class_zh": CLASS_ZH.get(cname, cname),
                    "area_ratio": 0.0,
                    "bbox": [0, 0, 0, 0],
                    "mask_file": mask_file,
                }
            ]

        meta = {
            "image": out_img_name,
            "active_class": classes[0]["class"],
            "classes": classes,
        }
        (gt_meta / f"{idx}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        out_manifest.append(
            {
                "index": idx,
                "source_split": split,
                "source_file": fname,
                "target_image": out_img_name,
                "labels": [c["class"] for c in classes],
            }
        )
        idx += 1

    summary = {
        "requested": args.count,
        "generated": len(out_manifest),
        "start_index": args.start_index,
        "end_index": args.start_index + len(out_manifest) - 1 if out_manifest else args.start_index - 1,
        "manifest": out_manifest,
    }

    out_report = project_root / "data" / "evaluation" / "sampled_51_100_manifest.json"
    out_report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "generated": len(out_manifest),
        "report": str(out_report),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
