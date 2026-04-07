#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
轻量标注工具: 水质异常 GT 标注（容器内可运行）

功能:
- 浏览图片目录并逐张标注
- 鼠标左键涂抹异常区域，右键擦除
- 键盘选择类别（1-9，含正常水质）
- 保存每张图的二值 mask + metadata

输出:
- output_dir/masks/<image_stem>__<class>.png
- output_dir/meta/<image_stem>.json

用法:
python tests/annotate_water_quality_gt.py \
  --input-dir data/test_results \
  --output-dir data/evaluation/manual_gt
"""

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

CLASSES = {
    "1": "black_water",
    "2": "turbid_water",
    "3": "red_water",
    "4": "green_water",
    "5": "milky_foam_water",
    "6": "dam_seepage",
    "7": "normal_water",
}

CLASS_ZH = {
    "black_water": "黑水",
    "turbid_water": "浑浊水",
    "red_water": "红水",
    "green_water": "绿水/藻类",
    "milky_foam_water": "乳白水/泡沫",
    "dam_seepage": "坝体渗水",
    "normal_water": "正常水质",
}

CLASS_COLORS = {
    "black_water": (20, 20, 20),
    "turbid_water": (42, 42, 165),       # 棕黄色
    "red_water": (0, 0, 255),
    "green_water": (0, 200, 0),
    "milky_foam_water": (180, 180, 255),
    "dam_seepage": (120, 120, 120),
    "normal_water": (255, 120, 0),
}

# 旧类别到新类别的映射（用于迁移旧标注）
OLD_TO_NEW_CLASS = {
    "black_water": "black_water",
    "brown_water": "turbid_water",
    "yellow_water": "turbid_water",
    "green_water": "green_water",
    "red_water": "red_water",
    "milky_water": "turbid_water",
    "foam_water": "milky_foam_water",
    "dam_seepage": "dam_seepage",
    "normal_water": "normal_water",
}


def natural_sort_key(path: Path):
    """自然排序key，让数字按数值排序（101在99之后）"""
    s = path.stem
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def list_images(input_dir: Path) -> List[Path]:
    """列出图片文件，使用set去重避免Windows大小写重复"""
    files = set()
    for f in input_dir.iterdir():
        if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
            files.add(f)
    return sorted(files, key=natural_sort_key)


def ensure_dirs(out_dir: Path) -> Dict[str, Path]:
    masks = out_dir / "masks"
    meta = out_dir / "meta"
    masks.mkdir(parents=True, exist_ok=True)
    meta.mkdir(parents=True, exist_ok=True)
    return {"masks": masks, "meta": meta}


def find_chinese_font() -> str:
    candidates = [
        "C:/windows/Fonts/msyh.ttc",
        "C:/windows/Fonts/simhei.ttf",
        "C:/windows/Fonts/simsun.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return ""


def load_all_class_masks(mask_dir: Path, stem: str, shape_hw: tuple, classes: List[str]) -> Dict[str, np.ndarray]:
    h, w = shape_hw
    masks: Dict[str, np.ndarray] = {c: np.zeros((h, w), dtype=np.uint8) for c in classes}

    # 先加载新类别
    for c in classes:
        p = mask_dir / f"{stem}__{c}.png"
        if p.exists():
            m = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if m is not None and m.shape == (h, w):
                masks[c] = (m > 127).astype(np.uint8) * 255

    # 迁移旧类别标注到新类别
    for old_cls, new_cls in OLD_TO_NEW_CLASS.items():
        if old_cls == new_cls:
            continue  # 跳过名称未变的类别
        old_p = mask_dir / f"{stem}__{old_cls}.png"
        if old_p.exists():
            old_m = cv2.imread(str(old_p), cv2.IMREAD_GRAYSCALE)
            if old_m is not None and old_m.shape == (h, w):
                # 将旧标注合并到新类别
                masks[new_cls] = np.maximum(masks[new_cls], (old_m > 127).astype(np.uint8) * 255)
                print(f"  迁移旧类别 '{old_cls}' -> '{new_cls}'")
                # 可选：删除旧mask文件（取消注释以启用）
                # old_p.unlink()

    return masks


def save_all_class_masks(mask_dir: Path, stem: str, class_masks: Dict[str, np.ndarray]):
    for cls_name, m in class_masks.items():
        p = mask_dir / f"{stem}__{cls_name}.png"
        if m.any():
            cv2.imwrite(str(p), m)
        elif p.exists():
            p.unlink()


def migrate_old_masks(mask_dir: Path, meta_dir: Path, dry_run: bool = True):
    """批量迁移旧类别mask到新类别"""
    print("\n=== 开始迁移旧类别标注 ===\n")

    # 找到所有旧类别的mask文件
    old_classes = set(OLD_TO_NEW_CLASS.keys()) - set(OLD_TO_NEW_CLASS.values())
    old_masks = []
    for old_cls in old_classes:
        old_masks.extend(mask_dir.glob(f"*__{old_cls}.png"))

    if not old_masks:
        print("未找到需要迁移的旧类别mask文件")
        return

    print(f"找到 {len(old_masks)} 个旧类别mask文件")

    # 按图片分组处理
    img_masks: Dict[str, Dict[str, Path]] = {}
    for mp in old_masks:
        # 文件名格式: <stem>__<class>.png
        parts = mp.stem.rsplit("__", 1)
        if len(parts) != 2:
            continue
        stem, old_cls = parts
        if old_cls not in OLD_TO_NEW_CLASS:
            continue
        if stem not in img_masks:
            img_masks[stem] = {}
        img_masks[stem][old_cls] = mp

    migrated_count = 0
    for stem, old_cls_paths in img_masks.items():
        new_masks: Dict[str, np.ndarray] = {}

        # 读取所有旧mask
        for old_cls, mp in old_cls_paths.items():
            new_cls = OLD_TO_NEW_CLASS[old_cls]
            m = cv2.imread(str(mp), cv2.IMREAD_GRAYSCALE)
            if m is None:
                continue

            if new_cls not in new_masks:
                new_masks[new_cls] = np.zeros_like(m)
            # 合并到新类别
            new_masks[new_cls] = np.maximum(new_masks[new_cls], m)

        # 保存新mask
        for new_cls, m in new_masks.items():
            new_path = mask_dir / f"{stem}__{new_cls}.png"
            if dry_run:
                print(f"  [DRY] {stem}: 合并 {list(old_cls_paths.keys())} -> {new_cls}")
            else:
                cv2.imwrite(str(new_path), m)
                print(f"  [OK] {stem}: 合并 {list(old_cls_paths.keys())} -> {new_cls}")

        # 删除旧mask文件（只执行一次）
        if not dry_run:
            for old_cls, mp in old_cls_paths.items():
                if mp.exists():
                    mp.unlink()
                    print(f"       删除旧文件: {mp.name}")

            # 更新meta文件
            meta_path = meta_dir / f"{stem}.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                # 更新classes列表
                new_classes = []
                seen = set()
                for item in meta.get("classes", []):
                    old_c = item["class"]
                    if old_c in OLD_TO_NEW_CLASS:
                        new_c = OLD_TO_NEW_CLASS[old_c]
                        if new_c not in seen:
                            item["class"] = new_c
                            item["class_zh"] = CLASS_ZH.get(new_c, new_c)
                            new_classes.append(item)
                            seen.add(new_c)
                meta["classes"] = new_classes
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        migrated_count += 1

    print(f"\n迁移完成: {migrated_count} 张图片")
    if dry_run:
        print("\n*** 这是预览模式，未实际修改文件 ***")
        print("使用 --migrate-run 参数执行实际迁移")


def main():
    parser = argparse.ArgumentParser(description="水质异常轻量标注工具")
    parser.add_argument("--input-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, required=True)
    parser.add_argument("--brush-size", type=int, default=16)
    parser.add_argument("--start-index", type=int, default=0, help="起始图片索引（0-based）")
    parser.add_argument("--start-file", type=str, default="", help="起始图片文件名（如 101.jpg）")
    parser.add_argument("--max-view-width", type=int, default=1600, help="显示窗口最大宽度")
    parser.add_argument("--max-view-height", type=int, default=900, help="显示窗口最大高度")
    parser.add_argument("--show-all-classes", action="store_true", help="显示全部类别叠加（默认仅显示当前类别，速度更快）")
    parser.add_argument("--migrate", action="store_true", help="预览迁移旧类别标注（dry-run）")
    parser.add_argument("--migrate-run", action="store_true", help="执行迁移旧类别标注（实际修改文件）")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    dirs = ensure_dirs(out_dir)

    # 迁移模式
    if args.migrate or args.migrate_run:
        migrate_old_masks(dirs["masks"], dirs["meta"], dry_run=args.migrate)
        return

    input_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    dirs = ensure_dirs(out_dir)

    images = list_images(input_dir)
    if not images:
        print(f"未找到图片: {input_dir}")
        return

    # 支持按文件名启动
    start_idx = args.start_index
    if args.start_file:
        for i, img in enumerate(images):
            if img.name == args.start_file:
                start_idx = i
                print(f"从文件 {args.start_file} 开始 (索引 {i})")
                break
        else:
            print(f"未找到文件 {args.start_file}，使用索引 {start_idx}")
    idx = max(0, min(start_idx, len(images) - 1))
    brush = max(1, args.brush_size)
    current_class = "black_water"
    class_legend = " | ".join([f"{k}:{CLASS_ZH[v]}" for k, v in sorted(CLASSES.items(), key=lambda x: x[0])])
    class_names = list(CLASSES.values())

    font_path = find_chinese_font()
    def load_font(font_size: int):
        try:
            if font_path:
                return ImageFont.truetype(font_path, font_size)
        except Exception:
            pass
        return ImageFont.load_default()

    font = load_font(24)

    drawing = False
    erasing = False
    mode = "brush"  # brush | contour
    contour_points: List[tuple] = []
    show_contours = True

    win = "water_gt_annotator"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    base = None
    class_masks: Dict[str, np.ndarray] = {}
    view_scale = 1.0
    view_w, view_h = 0, 0

    def update_view_params(h: int, w: int):
        nonlocal view_scale, view_w, view_h, font
        sx = args.max_view_width / max(w, 1)
        sy = args.max_view_height / max(h, 1)
        view_scale = min(1.0, sx, sy)
        view_w = max(1, int(w * view_scale))
        view_h = max(1, int(h * view_scale))
        # 视图越大字号越大，保证可读性
        dynamic_size = max(18, int(view_h * 0.035))
        font = load_font(dynamic_size)

    def load_state(img_path: Path):
        nonlocal base, class_masks, current_class
        base = cv2.imread(str(img_path))
        if base is None:
            return False
        h, w = base.shape[:2]
        update_view_params(h, w)
        meta_path = dirs["meta"] / f"{img_path.stem}.json"
        if meta_path.exists():
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            saved_class = data.get("active_class", current_class)
            # 迁移旧类别名称
            if saved_class in OLD_TO_NEW_CLASS:
                saved_class = OLD_TO_NEW_CLASS[saved_class]
            # 确保类别在当前类别列表中
            if saved_class in class_names:
                current_class = saved_class
        class_masks = load_all_class_masks(dirs["masks"], img_path.stem, (h, w), class_names)
        return True

    def render(img_path: Path):
        if view_scale < 1.0:
            vis = cv2.resize(base, (view_w, view_h), interpolation=cv2.INTER_AREA)
        else:
            vis = base.copy()

        # 默认仅显示当前类别以提升速度，可选显示全部类别
        if args.show_all_classes:
            cls_iter = list(class_masks.items())
        else:
            cls_iter = [(current_class, class_masks[current_class])]

        for cls_name, m in cls_iter:
            if not m.any():
                continue
            if view_scale < 1.0:
                m_show = cv2.resize(m, (view_w, view_h), interpolation=cv2.INTER_NEAREST)
            else:
                m_show = m
            color = CLASS_COLORS.get(cls_name, (128, 128, 128))
            alpha = 0.35 if cls_name == current_class else 0.18
            overlay = np.zeros_like(vis)
            overlay[m_show > 0] = color
            vis = cv2.addWeighted(vis, 1.0, overlay, alpha, 0)

            if show_contours and cls_name == current_class:
                contours, _ = cv2.findContours((m_show > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(vis, contours, -1, color, 2)

        # 轮廓点模式：显示待闭合轮廓
        if mode == "contour" and contour_points:
            pts = np.array(
                [[int(px * view_scale), int(py * view_scale)] for px, py in contour_points],
                dtype=np.int32,
            )
            if len(pts) >= 2:
                cv2.polylines(vis, [pts], isClosed=False, color=(0, 255, 255), thickness=2)
            for p in pts:
                cv2.circle(vis, tuple(p), 4, (0, 255, 255), -1)

        class_zh = CLASS_ZH.get(current_class, current_class)
        active_pixels = int((class_masks[current_class] > 0).sum())
        active_area = float((class_masks[current_class] > 0).mean())

        tagged = [CLASS_ZH[c] for c, m in class_masks.items() if m.any()]
        tagged_text = "已标注: " + ("、".join(tagged) if tagged else "无")

        text = [
            f"[{idx+1}/{len(images)}] {img_path.name}",
            f"view: {view_w}x{view_h} (scale={view_scale:.2f})",
            f"class: {current_class} ({class_zh})",
            f"mode: {mode} | pending contour pts: {len(contour_points)}",
            f"active area: {active_area:.2%} ({active_pixels} px)",
            f"brush: {brush}",
            "Brush: L-draw R-erase | Contour: L-add pt R-undo pt",
            "M-switch mode | F-fill contour | U-clear contour pts | O-toggle contour",
            "N-next B-back S-save C-clear(当前类) X-clear-all Q-quit | 1-7 class",
            tagged_text,
            class_legend,
        ]
        vis_pil = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(vis_pil)
        y = 20
        for t in text:
            draw.text((20, y), t, font=font, fill=(20, 255, 20))
            y += int(getattr(font, "size", 24) * 1.35)
        return cv2.cvtColor(np.array(vis_pil), cv2.COLOR_RGB2BGR)

    def save_current(img_path: Path):
        save_all_class_masks(dirs["masks"], img_path.stem, class_masks)

        classes_meta = []
        for cls_name, m in class_masks.items():
            ys, xs = np.where(m > 0)
            if len(ys) == 0:
                continue
            bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
            classes_meta.append({
                "class": cls_name,
                "class_zh": CLASS_ZH.get(cls_name, cls_name),
                "area_ratio": float((m > 0).mean()),
                "bbox": bbox,
                "mask_file": f"{img_path.stem}__{cls_name}.png",
            })

        data = {
            "image": img_path.name,
            "active_class": current_class,
            "classes": classes_meta,
        }
        meta_path = dirs["meta"] / f"{img_path.stem}.json"
        meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已保存: {meta_path}")

    def on_mouse(event, x, y, flags, param):
        nonlocal drawing, erasing
        if base is None:
            return
        h, w = base.shape[:2]
        ox = int(x / max(view_scale, 1e-6))
        oy = int(y / max(view_scale, 1e-6))
        ox = max(0, min(w - 1, ox))
        oy = max(0, min(h - 1, oy))
        if mode == "brush":
            if event == cv2.EVENT_LBUTTONDOWN:
                drawing = True
                cv2.circle(class_masks[current_class], (ox, oy), brush, 255, -1)
            elif event == cv2.EVENT_RBUTTONDOWN:
                erasing = True
                cv2.circle(class_masks[current_class], (ox, oy), brush, 0, -1)
            elif event == cv2.EVENT_MOUSEMOVE:
                if drawing:
                    cv2.circle(class_masks[current_class], (ox, oy), brush, 255, -1)
                elif erasing:
                    cv2.circle(class_masks[current_class], (ox, oy), brush, 0, -1)
            elif event == cv2.EVENT_LBUTTONUP:
                drawing = False
            elif event == cv2.EVENT_RBUTTONUP:
                erasing = False
        else:
            # contour 点选模式
            if event == cv2.EVENT_LBUTTONDOWN:
                contour_points.append((ox, oy))
            elif event == cv2.EVENT_RBUTTONDOWN and contour_points:
                contour_points.pop()

    def fill_contour_to_mask():
        if len(contour_points) < 3:
            print("轮廓点不足3个，无法闭合填充")
            return
        pts = np.array(contour_points, dtype=np.int32).reshape((-1, 1, 2))
        cv2.fillPoly(class_masks[current_class], [pts], 255)
        contour_points.clear()
        print(f"已填充轮廓到类别: {current_class}")

    sample = cv2.imread(str(images[idx]))
    if sample is None:
        print("无法读取首张图片")
        return
    h, w = sample.shape[:2]
    class_masks = {c: np.zeros((h, w), dtype=np.uint8) for c in class_names}

    cv2.setMouseCallback(win, on_mouse)

    if not load_state(images[idx]):
        print(f"无法读取图片: {images[idx]}")
        return

    while True:
        vis = render(images[idx])
        cv2.imshow(win, vis)
        key = cv2.waitKey(20) & 0xFF
        key_char = ""
        try:
            key_char = chr(key).lower()
        except Exception:
            key_char = ""

        if key_char == "q":
            break
        elif key_char == "[":
            brush = max(1, brush - 1)
        elif key_char == "]":
            brush = min(128, brush + 1)
        elif key_char == "c":
            class_masks[current_class][:] = 0
            contour_points.clear()
        elif key_char == "x":
            for c in class_names:
                class_masks[c][:] = 0
            contour_points.clear()
        elif key_char == "s":
            save_current(images[idx])
        elif key_char == "n":
            save_current(images[idx])
            idx = min(len(images) - 1, idx + 1)
            contour_points.clear()
            load_state(images[idx])
        elif key_char == "b":
            save_current(images[idx])
            idx = max(0, idx - 1)
            contour_points.clear()
            load_state(images[idx])
        elif key_char == "m":
            mode = "contour" if mode == "brush" else "brush"
            drawing = False
            erasing = False
        elif key_char == "f":
            fill_contour_to_mask()
        elif key_char == "u":
            contour_points.clear()
        elif key_char == "o":
            show_contours = not show_contours
        else:
            ch = key_char
            if ch in CLASSES:
                current_class = CLASSES[ch]
                # 切换编辑类别，不清空其他类别标注

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
