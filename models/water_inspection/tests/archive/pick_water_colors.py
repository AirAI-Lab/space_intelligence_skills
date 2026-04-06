#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
取色工具: 从测试图中采样水质颜色，辅助校准 color_hint。

功能:
- 鼠标左键点击取样点
- 统计 11x11 邻域 BGR/HSV 均值
- 将采样结果写入 JSON

用法:
python tests/pick_water_colors.py \
  --input-dir data/test_results \
  --output data/evaluation/color_samples.json
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np

CLASSES = {
    "1": "black_water",
    "2": "brown_water",
    "3": "yellow_water",
    "4": "green_water",
    "5": "red_water",
    "6": "milky_water",
    "7": "foam_water",
    "8": "dam_seepage",
    "0": "background",
}


def list_images(input_dir: Path) -> List[Path]:
    files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
        files.extend(input_dir.glob(ext))
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description="水质颜色采样工具")
    parser.add_argument("--input-dir", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--radius", type=int, default=5, help="邻域半径，最终窗口为 (2r+1)x(2r+1)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_file = Path(args.output)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    images = list_images(input_dir)
    if not images:
        print(f"未找到图片: {input_dir}")
        return

    idx = 0
    current_class = "background"
    radius = max(1, args.radius)
    records: List[Dict] = []

    win = "water_color_picker"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    image = None

    def load_img(i: int):
        nonlocal image
        image = cv2.imread(str(images[i]))
        return image is not None

    def sample_at(x: int, y: int):
        h, w = image.shape[:2]
        x1, x2 = max(0, x - radius), min(w, x + radius + 1)
        y1, y2 = max(0, y - radius), min(h, y + radius + 1)
        roi = image[y1:y2, x1:x2]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        bgr_mean = roi.reshape(-1, 3).mean(axis=0)
        hsv_mean = hsv.reshape(-1, 3).mean(axis=0)

        rec = {
            "image": images[idx].name,
            "class": current_class,
            "point": [int(x), int(y)],
            "bgr_mean": [float(bgr_mean[0]), float(bgr_mean[1]), float(bgr_mean[2])],
            "hsv_mean": [float(hsv_mean[0]), float(hsv_mean[1]), float(hsv_mean[2])],
            "radius": radius,
        }
        records.append(rec)
        print(f"采样: {rec}")

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            sample_at(x, y)

    cv2.setMouseCallback(win, on_mouse)

    if not load_img(idx):
        print(f"无法读取图片: {images[idx]}")
        return

    while True:
        vis = image.copy()
        txt = [
            f"[{idx+1}/{len(images)}] {images[idx].name}",
            f"class: {current_class}",
            f"samples: {len(records)} | radius: {radius}",
            "L-click sample | 0-8 class | N-next B-back",
            "[ and ] radius | S-save | Q-quit",
        ]
        y = 30
        for t in txt:
            cv2.putText(vis, t, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 255, 20), 2, cv2.LINE_AA)
            y += 30

        cv2.imshow(win, vis)
        key = cv2.waitKey(20) & 0xFF

        if key == ord("q"):
            break
        elif key == ord("n"):
            idx = min(len(images) - 1, idx + 1)
            load_img(idx)
        elif key == ord("b"):
            idx = max(0, idx - 1)
            load_img(idx)
        elif key == ord("["):
            radius = max(1, radius - 1)
        elif key == ord("]"):
            radius = min(25, radius + 1)
        elif key == ord("s"):
            out_file.write_text(json.dumps({"records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"已保存: {out_file}")
        else:
            try:
                ch = chr(key)
            except Exception:
                ch = ""
            if ch in CLASSES:
                current_class = CLASSES[ch]

    out_file.write_text(json.dumps({"records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"最终保存: {out_file}")
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
