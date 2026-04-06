#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水质检测可视化工具

提供分割结果的可视化功能。

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import numpy as np
import cv2
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class WaterQualityVisualizer:
    """
    水质检测可视化工具

    支持:
    - 分割结果可视化
    - 热图可视化
    - 对比可视化
    - 批量可视化
    """

    # 7 类水质颜色映射 (BGR)
    CLASS_COLORS = {
        "black_water": (0, 0, 180),           # 深蓝色
        "turbid_water": (42, 100, 170),       # 茶色
        "red_water": (0, 0, 255),             # 红色
        "green_water": (0, 200, 0),           # 绿色
        "milky_foam_water": (200, 200, 200),  # 浅灰色
        "dam_seepage": (100, 100, 100),       # 深灰色
        "normal_water": (200, 200, 100),      # 淡黄色
    }

    def __init__(self, font_path: Optional[str] = None):
        """
        Args:
            font_path: 中文字体路径
        """
        self.font_path = font_path or self._find_chinese_font()

    def visualize_segmentation(
        self,
        image: np.ndarray,
        segments: Dict,
        output_path: Optional[str] = None,
        alpha: float = 0.4,
        show_label: bool = True,
    ) -> np.ndarray:
        """
        可视化分割结果

        Args:
            image: BGR 图像
            segments: 分割结果字典
            output_path: 输出路径
            alpha: 叠加透明度
            show_label: 是否显示标签

        Returns:
            可视化图像
        """
        from PIL import Image, ImageDraw, ImageFont

        vis = image.copy()
        h, w = image.shape[:2]

        # 加载字体
        try:
            font = ImageFont.truetype(self.font_path, 24) if self.font_path else ImageFont.load_default()
            font_small = ImageFont.truetype(self.font_path, 18) if self.font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
            font_small = font

        for name, seg in segments.items():
            color = self.CLASS_COLORS.get(name, (128, 128, 128))

            # 半透明覆盖
            mask_uint8 = seg.mask.astype(np.uint8) * 255
            overlay = np.zeros_like(vis)
            overlay[mask_uint8 > 0] = color
            vis = cv2.addWeighted(vis, 1 - alpha, overlay, alpha, 0)

            # 轮廓
            contours, _ = cv2.findContours(
                mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(vis, contours, -1, color, 2)

            # 标签
            if show_label and len(contours) > 0:
                ys, xs = np.where(seg.mask)
                if len(ys) > 0:
                    cy, cx = int(ys.mean()), int(xs.mean())
                    label = f"{seg.class_name_cn} {seg.area_ratio:.1%}"
                    score_label = f"conf: {seg.score:.1%}"

                    vis_pil = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(vis_pil)

                    bbox = draw.textbbox((0, 0), label, font=font)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    tx = max(5, min(cx - tw // 2, w - tw - 5))
                    ty = max(5, min(cy - th - 10, h - th - 30))

                    draw.rectangle(
                        [tx - 4, ty - 2, tx + tw + 4, ty + th + 24],
                        fill=(0, 0, 0, 180),
                    )
                    draw.text((tx, ty), label, font=font, fill=(255, 255, 255))
                    draw.text((tx, ty + th + 3), score_label, font=font_small, fill=(200, 200, 200))

                    vis = cv2.cvtColor(np.array(vis_pil), cv2.COLOR_RGB2BGR)

        if output_path:
            cv2.imwrite(output_path, vis)
            logger.info(f"可视化结果已保存: {output_path}")

        return vis

    def visualize_heatmap(
        self,
        image: np.ndarray,
        heatmap: np.ndarray,
        class_name: str,
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        """
        可视化热图

        Args:
            image: BGR 图像
            heatmap: 热图 [H, W]
            class_name: 类别名
            output_path: 输出路径

        Returns:
            可视化图像
        """
        # 归一化热图到 0-255
        heatmap_norm = ((heatmap - heatmap.min()) / (heatmap.max() - heatmap.min() + 1e-8) * 255).astype(np.uint8)

        # 应用颜色映射
        heatmap_colored = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)

        # 叠加到原图
        vis = cv2.addWeighted(image, 0.6, heatmap_colored, 0.4, 0)

        if output_path:
            cv2.imwrite(output_path, vis)

        return vis

    def visualize_comparison(
        self,
        image: np.ndarray,
        pred_mask: np.ndarray,
        gt_mask: np.ndarray,
        class_name: str,
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        """
        对比可视化 (预测 vs GT)

        Args:
            image: BGR 图像
            pred_mask: 预测掩码
            gt_mask: GT 掩码
            class_name: 类别名
            output_path: 输出路径

        Returns:
            可视化图像
        """
        h, w = image.shape[:2]

        # 创建三通道可视化图
        vis = np.zeros((h, w, 3), dtype=np.uint8)

        # GT: 绿色
        vis[gt_mask, 1] = 255

        # 预测: 红色
        vis[pred_mask, 2] = 255

        # 交集: 黄色
        intersection = gt_mask & pred_mask
        vis[intersection] = [0, 255, 255]

        # 叠加到原图
        vis = cv2.addWeighted(image, 0.5, vis, 0.5, 0)

        if output_path:
            cv2.imwrite(output_path, vis)

        return vis

    @staticmethod
    def _find_chinese_font() -> str:
        """查找中文字体"""
        import platform
        candidates = [
            "C:/windows/Fonts/msyh.ttc",
            "C:/windows/Fonts/simhei.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        ] if platform.system() == "Windows" else [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return ""
