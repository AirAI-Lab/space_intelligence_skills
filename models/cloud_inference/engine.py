#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
云端推理引擎

从 radio_infer_server.py 中提取的推理核心逻辑：
  - 模型加载 (RADSegWaterSegmentor)
  - 图像推理 + 分割结果格式化
  - 标注绘制
  - 告警生成 (委托给 plugin)

Server 层只负责 MQTT/RTMP 模式管理，推理逻辑全部在此。
"""

import os
import sys
import json
import base64
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent.parent
if not (PROJECT_ROOT / "models").exists():
    PROJECT_ROOT = _HERE.parent

logger = logging.getLogger("radio_server")

_COLORS = [
    (0, 255, 0), (0, 0, 255), (0, 255, 255), (255, 0, 255),
    (255, 255, 0), (255, 128, 0), (128, 0, 255), (0, 128, 255),
]


class InferenceEngine:
    """
    云端推理引擎：持有模型和插件，执行推理 + 告警生成。

    Usage:
        plugin = ScenarioPlugin(config_path)
        engine = InferenceEngine(plugin)
        engine.load_model(checkpoint, radio_code, siglip2, device, input_size)
        payload = engine.infer_image(image, device_id, frame_id, channel_id, source)
    """

    def __init__(self, plugin):
        self._plugin = plugin
        self._segmentor = None
        self._FONT = None

    @property
    def plugin(self):
        return self._plugin

    def load_model(self, checkpoint_path: str, radio_code_dir: str,
                   siglip2_dir: str, device: str, input_size: int) -> None:
        """加载 C-RADIOv4 模型"""
        sys.path.insert(0, str(PROJECT_ROOT / "models" / "water_inspection"))
        from models.open_vocab import RADSegWaterSegmentor

        logger.info("加载 C-RADIOv4 模型...")
        self._segmentor = RADSegWaterSegmentor(
            checkpoint_path=checkpoint_path,
            radio_code_dir=radio_code_dir,
            siglip2_dir=siglip2_dir,
            device=device,
            input_size=input_size,
        )
        logger.info("模型加载完成")

    def infer_image(self, image: np.ndarray, device_id: str, frame_id: int,
                    channel_id: str = "default", source: str = "cloud",
                    report_counter: int = 0) -> Optional[dict]:
        """
        执行推理并返回标准 payload dict，无有效结果时返回 None。

        返回值可直接用于 MQTT 发布和 REST 上报。
        """
        threshold, min_area = self._plugin.get_thresholds()
        classes_config = self._plugin.get_classes_config()

        t0 = time.time()
        results = self._segmentor.segment(
            image, classes_config,
            threshold=threshold,
            min_area=min_area,
            multi_class=self._plugin.is_multi_class(),
        )
        inference_ms = (time.time() - t0) * 1000

        # 格式化分割结果
        segments = {}
        for name, seg in results.items():
            ys, xs = np.where(seg.mask)
            bbox = (
                [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
                if len(ys) > 0 else [0, 0, 0, 0]
            )
            segments[name] = {
                "area": round(seg.area_ratio, 4),
                "score": round(seg.score, 4),
                "bbox": bbox,
                "class_name_cn": seg.class_name_cn,
            }

        # 颜色通道差过滤：排除与目标色调不符的误检
        segments = self._filter_by_color(image, results, segments, classes_config)

        # 使用插件生成告警
        alerts = self._plugin.generate_alerts(segments, min_area)

        seg_names = list(segments.keys()) or ["无检出"]
        logger.info(
            "[%d] %s frame=%d ch=%s (%s): %s, %d alerts, %.0fms",
            report_counter, device_id, frame_id, channel_id,
            source, seg_names, len(alerts), inference_ms,
        )

        if not alerts and not segments:
            return None

        # 绘制标注
        image_b64 = None
        if segments:
            try:
                img_bytes = self._draw_annotations(image, results)
                image_b64 = base64.b64encode(img_bytes).decode("ascii")
            except Exception as e:
                logger.warning("绘制标注失败: %s", e)

        payload = {
            "device_id": device_id,
            "frame_id": frame_id,
            "channel_id": channel_id,
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "segments": segments,
            "alerts": alerts,
            "inference_time_ms": round(inference_ms, 1),
        }
        if image_b64:
            payload["image_base64"] = image_b64

        return payload

    # ── 颜色过滤 ──

    def _filter_by_color(self, image: np.ndarray, results: dict,
                         segments: dict, classes_config: dict) -> dict:
        """
        基于颜色通道差的误检过滤。

        YAML 配置示例:
          dust_pollution:
            color_filter:
              min_rb_diff: 15   # R 通道均值 - B 通道均值 > 15 (暖色调)
        """
        to_remove = []
        for name, seg in results.items():
            if name not in segments:
                continue
            cfg = classes_config.get(name, {})
            color_filter = cfg.get("color_filter")
            if not color_filter:
                continue

            mask = seg.mask.astype(bool)
            if not mask.any():
                continue

            pixels = image[mask].astype(np.float32)
            mean_b = pixels[:, 0].mean()
            mean_g = pixels[:, 1].mean()
            mean_r = pixels[:, 2].mean()

            min_rb = color_filter.get("min_rb_diff", 0)
            if min_rb and (mean_r - mean_b) < min_rb:
                logger.info(
                    "颜色过滤 %s: R-B=%.1f < min_rb_diff=%.1f, 排除",
                    name, mean_r - mean_b, min_rb,
                )
                to_remove.append(name)

        for name in to_remove:
            del segments[name]

        return segments

    # ── 标注绘制 ──

    def _get_font(self, size: int = 20):
        if self._FONT is not None and self._FONT.size == size:
            return self._FONT
        font_paths = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    self._FONT = ImageFont.truetype(
                        fp, size, index=3 if fp.endswith(".ttc") else 0
                    )
                    return self._FONT
                except Exception:
                    continue
        self._FONT = ImageFont.load_default()
        return self._FONT

    def _draw_annotations(self, image: np.ndarray, results: dict) -> bytes:
        annotated = image.copy()
        h, w = annotated.shape[:2]
        font_size = max(24, min(w, h) // 25)

        for i, (name, seg) in enumerate(results.items()):
            if not hasattr(seg, 'mask') or seg.mask is None:
                continue
            color = _COLORS[i % len(_COLORS)]
            mask = seg.mask.astype(bool)
            if mask.any():
                overlay = annotated.copy()
                overlay[mask] = color
                cv2.addWeighted(overlay, 0.4, annotated, 0.6, 0, annotated)
                ys, xs = np.where(mask)
                if len(ys) > 0:
                    cx, cy = int(xs.mean()), int(ys.mean())
                    label = f"{seg.class_name_cn or name} {seg.area_ratio:.1%}"

                    font = self._get_font(font_size)
                    pil_img = Image.fromarray(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(pil_img)
                    bbox = draw.textbbox((0, 0), label, font=font)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

                    pad = 10
                    tx = max(pad, min(w - tw - pad, cx - tw // 2))
                    ty = max(pad, min(h - th - pad, cy - th // 2))

                    draw.rectangle([tx - pad, ty - pad, tx + tw + pad, ty + th + pad],
                                   fill=(color[2], color[1], color[0]))
                    draw.text((tx, ty), label, fill=(255, 255, 255), font=font)
                    annotated = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        if w > 960:
            scale = 960 / w
            annotated = cv2.resize(annotated, (960, int(h * scale)))
        _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes()
