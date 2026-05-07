#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
变换检测统一系统 v1.1

支持两种模式:
  1. 单帧检测: 直接检测图像中的目标 (违建、堆放物等)
  2. 对比检测: 前后帧对比发现变化

类别参考: Construction Detection 数据集
  - blue_canopy (蓝色雨棚)
  - green_shack (绿色棚屋)
  - illegal_structure (其他违建)
  - building, vegetation, bare_ground, vehicle, debris, water, road

作者: 空中智能体团队
日期: 2026-04-07
"""

import os
import sys
import cv2
import yaml
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 导入 RADSeg 分割器 (从 water_inspection)
_wi_candidates = [
    '/app/models/water_inspection',
    '/app/water_inspection',
]
_local_wi = str(Path(__file__).resolve().parent.parent.parent / 'water_inspection')
_wi_candidates.append(_local_wi)

for _p in _wi_candidates:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from models.open_vocab.radseg_segmentor import RADSegWaterSegmentor


# ==============================================================================
# 数据类
# ==============================================================================

@dataclass
class Detection:
    """单个检测结果"""
    class_name: str
    class_name_cn: str
    confidence: float
    area_ratio: float
    bbox: List[float]
    mask: Optional[np.ndarray] = None


@dataclass
class ChangeRegion:
    """单个变化区域"""
    class_name: str
    class_name_cn: str
    change_type: str          # "added", "removed"
    area_ratio: float
    confidence: float
    bbox: List[float]
    mask: Optional[np.ndarray] = None


@dataclass
class DetectResult:
    """单帧检测结果"""
    detections: List[Detection]
    class_areas: Dict[str, float]
    inference_time_ms: float = 0.0


@dataclass
class ChangeResult:
    """对比检测结果"""
    has_change: bool
    change_regions: List[ChangeRegion]
    earlier_classes: Dict[str, float]
    later_classes: Dict[str, float]
    change_summary: Dict[str, Dict]
    inference_time_ms: float = 0.0


# ==============================================================================
# 核心检测器
# ==============================================================================

CLASS_ZH = {
    # 违建
    "blue_canopy": "蓝色雨棚", "green_shack": "绿色棚屋",
    "illegal_extension": "违章搭建",
    # 交通
    "vehicle": "机动车辆", "construction_vehicle": "工程车辆",
    # 城市治理
    "debris_dump": "垃圾堆放", "material_stock": "建材堆放",
    "enclosure_fence": "围挡围栏", "scaffolding": "脚手架",
    # 环境
    "building": "建筑物", "vegetation": "植被", "bare_ground": "裸土",
    "farmland": "农田", "water": "水体", "road": "道路",
    "parking_lot": "停车场", "background": "背景",
    # L1 场景
    "urban": "城市区域", "agricultural": "农业区域",
    "water_body": "水域", "mountain_forest": "山林区域",
    "industrial": "工业区域",
}

ALERT_CLASSES = {
    "blue_canopy", "green_shack", "illegal_extension",
    "debris_dump", "material_stock", "enclosure_fence",
    "scaffolding", "bare_ground", "vehicle", "construction_vehicle",
}


class ChangeDetector:
    """变换检测器 (单帧 + 对比)"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        checkpoint_path: Optional[str] = None,
        radio_code_dir: Optional[str] = None,
        siglip2_dir: Optional[str] = None,
        device: str = "cuda",
    ):
        if config_path and Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = self._default_config()

        radio_cfg = self.config['cloud']['radio']
        model_cfg = radio_cfg['model']
        seg_cfg = radio_cfg['segmentation']
        cd_cfg = radio_cfg['change_detection']

        self.threshold = seg_cfg.get('threshold', 0.35)
        self.min_change_area = cd_cfg.get('min_change_area', 0.003)

        # L2 目标类别
        self.classes_config = {}
        for cls_name, cfg in radio_cfg.get('classes', {}).items():
            if not cfg.get('is_background', False) and 'prompts' in cfg:
                self.classes_config[cls_name] = cfg

        # L1 场景类别 (可选)
        self.scene_config = {}
        for cls_name, cfg in radio_cfg.get('scene_classes', {}).items():
            if 'prompts' in cfg:
                self.scene_config[cls_name] = cfg

        print("[Stage 0] 加载分割器...")
        self.segmentor = RADSegWaterSegmentor(
            checkpoint_path=checkpoint_path or model_cfg.get('path'),
            radio_code_dir=radio_code_dir or model_cfg.get('radio_code_dir'),
            siglip2_dir=siglip2_dir or model_cfg.get('siglip2_dir'),
            device=device,
            use_scra=model_cfg.get('use_scra', True),
            use_dino=model_cfg.get('use_dino', True),
            use_sam=model_cfg.get('use_sam', False),
            temperature=model_cfg.get('temperature', 50.0),
        )
        print(f"  ✓ 分割器加载完成, L2 目标 {len(self.classes_config)} 类 + L1 场景 {len(self.scene_config)} 类")

    @staticmethod
    def _default_config():
        return {'cloud': {'radio': {'model': {}, 'segmentation': {'threshold': 0.35},
            'change_detection': {'min_change_area': 0.003}, 'classes': {}}}}

    def _build_prompts(self, classes_config=None):
        cfg = classes_config or self.classes_config
        prompts = {}
        for cls_name, c in cfg.items():
            prompts[cls_name] = {"prompts": c.get("prompts", [])}
        return prompts

    def _segment(self, image: np.ndarray) -> Dict[str, np.ndarray]:
        prompts = self._build_prompts()
        heatmaps = self.segmentor.compute_patch_similarity(image, prompts)
        h, w = image.shape[:2]
        masks = {}
        for cls_name in self.classes_config:
            hm = heatmaps.get(cls_name, np.zeros((h, w)))
            if hm.shape != (h, w):
                hm = cv2.resize(hm, (w, h))
            masks[cls_name] = (hm > self.threshold).astype(np.uint8)
        return masks

    # ------------------------------------------------------------------
    # L1 场景检测
    # ------------------------------------------------------------------
    def detect_scene(self, image: np.ndarray) -> Dict[str, float]:
        """
        L1 场景检测: 快速识别图像的场景类型

        Returns:
            {scene_name: area_ratio} 按面积降序
        """
        if not self.scene_config:
            return {}

        prompts = self._build_prompts(self.scene_config)
        heatmaps = self.segmentor.compute_patch_similarity(image, prompts)
        h, w = image.shape[:2]

        results = {}
        for cls_name in self.scene_config:
            hm = heatmaps.get(cls_name, np.zeros((h, w)))
            if hm.shape != (h, w):
                hm = cv2.resize(hm, (w, h))
            results[cls_name] = float(hm.mean())

        # 按得分降序排列
        return dict(sorted(results.items(), key=lambda x: -x[1]))

    # ------------------------------------------------------------------
    # 单帧检测
    # ------------------------------------------------------------------
    def detect_single(self, image: np.ndarray) -> DetectResult:
        """
        单帧检测: 检测图像中的各类目标

        Args:
            image: BGR 图像

        Returns:
            DetectResult
        """
        t0 = datetime.now()
        h, w = image.shape[:2]
        total_px = h * w

        masks = self._segment(image)
        class_areas = {n: m.sum() / total_px for n, m in masks.items()}

        detections = []
        for cls_name, mask in masks.items():
            area = mask.sum() / total_px
            if area < 0.001:
                continue
            bbox = self._mask_to_bbox(mask)
            if bbox is None:
                continue
            detections.append(Detection(
                class_name=cls_name,
                class_name_cn=CLASS_ZH.get(cls_name, cls_name),
                confidence=min(area * 5, 1.0),
                area_ratio=area,
                bbox=bbox,
                mask=mask,
            ))

        elapsed = (datetime.now() - t0).total_seconds() * 1000
        return DetectResult(
            detections=detections,
            class_areas=class_areas,
            inference_time_ms=elapsed,
        )

    # ------------------------------------------------------------------
    # 对比检测
    # ------------------------------------------------------------------
    def detect_changes(self, earlier: np.ndarray, later: np.ndarray) -> ChangeResult:
        """
        对比检测: 检测前后两帧之间的变化

        Args:
            earlier: 前期图像 (BGR)
            later: 后期图像 (BGR)

        Returns:
            ChangeResult
        """
        t0 = datetime.now()
        h, w = earlier.shape[:2]
        total_px = h * w

        print("  [1/3] 分割前期图像...")
        masks_e = self._segment(earlier)
        print("  [2/3] 分割后期图像...")
        masks_l = self._segment(later)

        areas_e = {n: m.sum() / total_px for n, m in masks_e.items()}
        areas_l = {n: m.sum() / total_px for n, m in masks_l.items()}

        change_regions = []
        change_summary = {}

        print("  [3/3] 计算变化...")
        for cls_name in self.classes_config:
            me = masks_e.get(cls_name, np.zeros((h, w), dtype=np.uint8))
            ml = masks_l.get(cls_name, np.zeros((h, w), dtype=np.uint8))

            added = (ml - me).clip(0, 1)
            removed = (me - ml).clip(0, 1)
            added_area = added.sum() / total_px
            removed_area = removed.sum() / total_px

            change_summary[cls_name] = {
                "added_area": float(added_area),
                "removed_area": float(removed_area),
                "earlier_area": float(areas_e.get(cls_name, 0)),
                "later_area": float(areas_l.get(cls_name, 0)),
                "area_change": float(areas_l.get(cls_name, 0) - areas_e.get(cls_name, 0)),
            }

            if added_area >= self.min_change_area:
                bbox = self._mask_to_bbox(added)
                if bbox:
                    change_regions.append(ChangeRegion(
                        class_name=cls_name,
                        class_name_cn=CLASS_ZH.get(cls_name, cls_name),
                        change_type="added",
                        area_ratio=added_area,
                        confidence=min(added_area * 10, 1.0),
                        bbox=bbox, mask=added,
                    ))

            if removed_area >= self.min_change_area:
                bbox = self._mask_to_bbox(removed)
                if bbox:
                    change_regions.append(ChangeRegion(
                        class_name=cls_name,
                        class_name_cn=CLASS_ZH.get(cls_name, cls_name),
                        change_type="removed",
                        area_ratio=removed_area,
                        confidence=min(removed_area * 10, 1.0),
                        bbox=bbox, mask=removed,
                    ))

        elapsed = (datetime.now() - t0).total_seconds() * 1000
        return ChangeResult(
            has_change=len(change_regions) > 0,
            change_regions=change_regions,
            earlier_classes=areas_e,
            later_classes=areas_l,
            change_summary=change_summary,
            inference_time_ms=elapsed,
        )

    # ------------------------------------------------------------------
    # 可视化
    # ------------------------------------------------------------------
    @staticmethod
    def _mask_to_bbox(mask):
        ys, xs = np.where(mask > 0)
        if len(xs) == 0:
            return None
        return [float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())]

    def visualize_single(
        self, image: np.ndarray, result: DetectResult, output_path: Optional[str] = None
    ) -> np.ndarray:
        """单帧检测可视化"""
        h, w = image.shape[:2]
        overlay = image.copy()

        colors = [
            (255, 100, 0), (0, 200, 0), (0, 0, 255), (200, 200, 0),
            (200, 0, 200), (0, 200, 200), (128, 128, 0), (0, 128, 128),
        ]

        for i, det in enumerate(result.detections):
            color = colors[i % len(colors)]
            if det.mask is not None:
                mask_resized = cv2.resize(det.mask, (w, h)) > 0.5
                colored = np.zeros_like(overlay)
                colored[mask_resized] = color
                overlay = cv2.addWeighted(overlay, 0.7, colored, 0.3, 0)

            x1, y1, x2, y2 = [int(v) for v in det.bbox]
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
            label = f"{det.class_name_cn} {det.area_ratio*100:.1f}%"
            cv2.putText(overlay, label, (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 并排
        vis = np.concatenate([image, overlay], axis=1)
        if output_path:
            cv2.imwrite(output_path, vis)
            print(f"  ✓ 保存: {output_path}")
        return vis

    def visualize_changes(
        self, earlier: np.ndarray, later: np.ndarray,
        result: ChangeResult, output_path: Optional[str] = None,
    ) -> np.ndarray:
        """对比检测可视化: [earlier | later | overlay]"""
        h, w = earlier.shape[:2]

        added_color = (0, 255, 0)
        removed_color = (0, 0, 255)

        diff = np.zeros_like(later)
        for region in result.change_regions:
            if region.mask is not None:
                m = cv2.resize(region.mask, (w, h)) > 0.5
                c = added_color if region.change_type == "added" else removed_color
                diff[m] = c

        overlay = later.copy()
        mask_any = diff.any(axis=2)
        if mask_any.any():
            overlay[mask_any] = cv2.addWeighted(later, 0.5, diff, 0.5, 0)[mask_any]

        label_h = 40
        def add_label(img, text):
            canvas = np.ones((h + label_h, w, 3), dtype=np.uint8) * 240
            canvas[label_h:] = img
            cv2.putText(canvas, text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            return canvas

        panels = [
            add_label(earlier, "Earlier (T1)"),
            add_label(later, "Later (T2)"),
            add_label(overlay, "Change Overlay"),
        ]
        vis = np.concatenate(panels, axis=1)

        if output_path:
            cv2.imwrite(output_path, vis)
            print(f"  ✓ 保存: {output_path}")
        return vis


# ==============================================================================
# CLI
# ==============================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="变换检测 (单帧 + 对比)")
    parser.add_argument("--config", default="configs/change_detection.yaml")
    parser.add_argument("--mode", choices=["single", "compare"], required=True)
    parser.add_argument("--image", help="单帧检测图像")
    parser.add_argument("--earlier", help="对比检测前期图像")
    parser.add_argument("--later", help="对比检测后期图像")
    parser.add_argument("--output", default="output.jpg")
    args = parser.parse_args()

    detector = ChangeDetector(config_path=args.config)

    if args.mode == "single":
        img = cv2.imread(args.image)
        result = detector.detect_single(img)
        detector.visualize_single(img, result, args.output)

        print(f"\n检测结果: {len(result.detections)} 个目标")
        for d in result.detections:
            alert = "⚠️ " if d.class_name in ALERT_CLASSES else "  "
            print(f"  {alert}{d.class_name_cn}: {d.area_ratio*100:.1f}%")

    elif args.mode == "compare":
        e = cv2.imread(args.earlier)
        l = cv2.imread(args.later)
        result = detector.detect_changes(e, l)
        detector.visualize_changes(e, l, result, args.output)

        print(f"\n变化检测: {'有变化' if result.has_change else '无变化'}")
        print(f"变化区域: {len(result.change_regions)}")
        for r in result.change_regions:
            print(f"  {r.change_type}: {r.class_name_cn} ({r.area_ratio*100:.1f}%)")
