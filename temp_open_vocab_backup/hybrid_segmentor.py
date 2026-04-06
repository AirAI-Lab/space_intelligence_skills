#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
混合水质分割器 v1.0 - 颜色优先 + RADIO 辅助定位

核心思路:
1. RADIO 擅长: 定位水域区域 (语义理解)
2. 颜色分析擅长: 区分水质类型 (细粒度颜色差异)
3. 组合策略: 先用水域定位，再用颜色分类

水质分类规则 (基于 RGB 分析):
- black_water: RGB 都很低 (<100), 且接近
- turbid_water: R > G > B (黄褐色)
- red_water: R >> G, R >> B (红色)
- green_water: G > R, G > B (绿色)
- milky_foam_water: RGB 都很高 (>150), 低饱和度
- dam_seepage: 深色湿斑，在非水域区域
- normal_water: RGB 均衡，中等亮度

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import torch
import torch.nn.functional as F
import numpy as np
import cv2
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SegmentResult:
    """分割结果"""
    class_name: str
    class_name_cn: str
    mask: np.ndarray
    area_ratio: float
    score: float
    color_score: float = 0.0  # 颜色得分
    radio_score: float = 0.0  # RADIO 得分


class ColorWaterClassifier:
    """
    基于颜色的水质分类器 v2.0

    使用从数据集分析得出的实际颜色分布来区分水质类型

    关键发现 (基于 100 样本分析):
    - turbid_water: R > G > B (暖色调), R-G=7.6, G-B=19.6
    - red_water: R >> G (红色调), R-G=41, R-B=66
    - green_water: G > R, G > B (绿色调), G-B=34
    - milky_foam_water: 高亮度 (154), 低饱和度 (range=15)
    - black_water: RGB 接近 (range=10), 亮度较低 (126)
    - normal_water: RGB 均衡 (range=23), 中等亮度 (135)
    - dam_seepage: 与 normal_water 颜色相似，难以区分
    """

    # 颜色特征定义 (BGR 顺序) - 基于实际数据集分析
    # 使用更宽松的规则 + 置信度评分
    COLOR_PROFILES = {
        "red_water": {
            "description": "红水 - R 明显高于 G",
            "rules": [
                ("r_g_diff", ">", 20),      # R - G > 20 (实际: 41)
                ("r_channel", ">", 150),    # R > 150 (实际: 198)
            ],
            "color_hint": [132, 157, 198],  # BGR
            "priority": 1,  # 最高优先级
            "min_confidence": 0.5,  # 最小置信度
        },
        "green_water": {
            "description": "绿水 - G 明显高于 B 和 R",
            "rules": [
                ("g_b_diff", ">", 15),      # G - B > 15 (实际: 34)
                ("g_r_diff", ">", 0),       # G > R (实际: 13)
            ],
            "color_hint": [104, 138, 125],  # BGR
            "priority": 2,
            "min_confidence": 0.3,
        },
        "turbid_water": {
            "description": "浑浊水 - R > G > B (暖色调)",
            "rules": [
                ("r_g_diff", ">", 0),       # R > G (实际: 7.6)
                ("g_b_diff", ">", 8),       # G > B + 8 (实际: 19.6)
            ],
            "color_hint": [117, 137, 144],  # BGR
            "priority": 3,
            "min_confidence": 0.3,
        },
        "milky_foam_water": {
            "description": "乳白水 - 高亮度，低饱和度",
            "rules": [
                ("brightness", ">", 140),   # 亮度 > 140 (实际: 154)
                ("rgb_range", "<", 40),     # RGB 范围 < 40 (实际: 15)
            ],
            "color_hint": [154, 154, 153],  # BGR
            "priority": 4,
            "min_confidence": 0.3,
        },
        "black_water": {
            "description": "黑水 - RGB 接近，亮度低",
            "rules": [
                ("rgb_range", "<", 25),     # RGB 范围 < 25 (实际: 10)
                ("brightness", "<", 130),   # 亮度 < 130 (实际: 126)
            ],
            "color_hint": [126, 127, 123],  # BGR
            "priority": 5,
            "min_confidence": 0.3,
        },
        "dam_seepage": {
            "description": "坝体渗水 - 与 normal_water 相似",
            "rules": [],  # 无可靠颜色规则 - 需要 RADIO 语义
            "color_hint": [134, 138, 141],  # BGR
            "priority": 10,
            "min_confidence": 0.0,
        },
        "normal_water": {
            "description": "正常水质 - RGB 均衡",
            "rules": [],  # 默认类别
            "color_hint": [138, 140, 126],  # BGR
            "priority": 99,
            "min_confidence": 0.0,
        },
    }

    def __init__(self, classes_config: Optional[Dict] = None):
        """
        Args:
            classes_config: 可选的类别配置，覆盖默认颜色配置
        """
        self.classes_config = classes_config or {}
        self.color_profiles = self.COLOR_PROFILES.copy()

        # 从配置更新颜色提示
        if classes_config:
            for cls_name, cfg in classes_config.items():
                if "color_hint" in cfg and cls_name in self.color_profiles:
                    self.color_profiles[cls_name]["color_hint"] = cfg["color_hint"]

    def extract_color_features(self, bgr_region: np.ndarray) -> Dict[str, float]:
        """
        从 BGR 区域提取颜色特征

        Args:
            bgr_region: [N, 3] BGR 像素值

        Returns:
            特征字典
        """
        if len(bgr_region) == 0:
            return {}

        # 分离通道 (BGR 顺序)
        b = bgr_region[:, 0].astype(np.float32)
        g = bgr_region[:, 1].astype(np.float32)
        r = bgr_region[:, 2].astype(np.float32)

        # 计算均值
        b_mean, g_mean, r_mean = b.mean(), g.mean(), r.mean()

        features = {
            "r_channel": r_mean,
            "g_channel": g_mean,
            "b_channel": b_mean,
            "brightness": (r_mean + g_mean + b_mean) / 3,
            "max_rgb": max(r_mean, g_mean, b_mean),
            "min_rgb": min(r_mean, g_mean, b_mean),
            "rgb_range": max(r_mean, g_mean, b_mean) - min(r_mean, g_mean, b_mean),
            "r_g_diff": r_mean - g_mean,
            "r_b_diff": r_mean - b_mean,
            "g_r_diff": g_mean - r_mean,
            "g_b_diff": g_mean - b_mean,
            "saturation": 0.0,
        }

        # 计算饱和度 (近似)
        max_c = max(r_mean, g_mean, b_mean)
        if max_c > 0:
            features["saturation"] = features["rgb_range"] / max_c * 100

        return features

    def evaluate_rule(self, features: Dict[str, float], rule: Tuple) -> float:
        """
        评估单条规则的匹配程度

        Args:
            features: 颜色特征
            rule: (特征名, 操作符, 阈值)

        Returns:
            匹配得分 [0, 1]
        """
        feat_name, op, threshold = rule

        if feat_name not in features:
            return 0.0

        value = features[feat_name]

        if op == ">":
            # 超过阈值越多，得分越高
            if value <= threshold:
                return 0.0
            return min(1.0, (value - threshold) / threshold)
        elif op == "<":
            # 低于阈值越多，得分越高
            if value >= threshold:
                return 0.0
            return min(1.0, (threshold - value) / threshold)
        elif op == "==":
            return 1.0 if abs(value - threshold) < 10 else 0.0

        return 0.0

    def classify_region(
        self,
        bgr_region: np.ndarray,
        exclude_classes: Optional[set] = None,
    ) -> Tuple[str, float, Dict[str, float]]:
        """
        对一个区域进行水质分类

        Args:
            bgr_region: [N, 3] BGR 像素值
            exclude_classes: 要排除的类别

        Returns:
            (最佳类别, 得分, 所有类别得分)
        """
        features = self.extract_color_features(bgr_region)

        if not features:
            return "normal_water", 0.0, {}

        exclude_classes = exclude_classes or set()
        class_scores = {}

        # 按优先级排序 (低优先级数字 = 高优先级)
        sorted_profiles = sorted(
            self.color_profiles.items(),
            key=lambda x: x[1].get("priority", 99)
        )

        for cls_name, profile in sorted_profiles:
            if cls_name in exclude_classes:
                continue

            rules = profile.get("rules", [])

            # 如果没有规则 (normal_water, dam_seepage)，跳过
            if not rules:
                continue

            # 检查所有规则是否都满足 (至少 > 0)
            rule_scores = [self.evaluate_rule(features, r) for r in rules]

            # 所有规则必须都得分 > 0 才算匹配
            if all(s > 0 for s in rule_scores):
                avg_score = np.mean(rule_scores)
                class_scores[cls_name] = avg_score

                # 高优先级类别匹配成功，直接返回
                if profile.get("priority", 99) < 5:
                    return cls_name, avg_score, class_scores

        # 如果没有匹配的类别，返回 normal_water
        if not class_scores:
            return "normal_water", 0.0, {}

        # 返回得分最高的类别
        best_class = max(class_scores.keys(), key=lambda k: class_scores[k])
        best_score = class_scores[best_class]

        return best_class, best_score, class_scores

    def classify_mask(
        self,
        image: np.ndarray,
        mask: np.ndarray,
    ) -> Tuple[str, float, Dict[str, float]]:
        """
        对掩码区域进行分类

        Args:
            image: BGR 图像
            mask: 布尔掩码

        Returns:
            (最佳类别, 得分, 所有类别得分)
        """
        ys, xs = np.where(mask)
        if len(ys) == 0:
            return "normal_water", 0.0, {}

        pixels = image[ys, xs]
        return self.classify_region(pixels)


class HybridWaterSegmentor:
    """
    混合水质分割器

    策略:
    1. 使用 RADIO 定位水域区域 (粗定位)
    2. 使用颜色分析进行水质分类 (精分类)
    3. 可选: 使用 RADIO 得分进行置信度调整
    """

    def __init__(
        self,
        radio_segmentor,  # RADSegWaterSegmentor 实例
        classes_config: Dict[str, dict],
        use_radio_refinement: bool = True,
        radio_weight: float = 0.3,  # RADIO 得分权重
        color_weight: float = 0.7,  # 颜色得分权重
    ):
        """
        Args:
            radio_segmentor: RADIO 分割器实例
            classes_config: 类别配置
            use_radio_refinement: 是否使用 RADIO 得分优化
            radio_weight: RADIO 得分权重
            color_weight: 颜色得分权重
        """
        self.radio_segmentor = radio_segmentor
        self.classes_config = classes_config
        self.color_classifier = ColorWaterClassifier(classes_config)
        self.use_radio_refinement = use_radio_refinement
        self.radio_weight = radio_weight
        self.color_weight = color_weight

        # 异常类别
        self.anomaly_classes = {
            k for k, v in classes_config.items()
            if not v.get("is_background", False)
        }

        # 背景类别
        self.background_classes = {
            k for k, v in classes_config.items()
            if v.get("is_background", False) and k != "background"
        }

        logger.info(f"混合分割器初始化: {len(self.anomaly_classes)} 异常类别")

    def segment(
        self,
        image: np.ndarray,
        threshold: float = 0.2,
        min_area: float = 0.005,
        min_confidence: float = 0.4,  # 新增：最小置信度阈值
    ) -> Dict[str, SegmentResult]:
        """
        执行水质分割

        Args:
            image: BGR 图像
            threshold: 置信度阈值
            min_area: 最小面积比例
            min_confidence: 最小置信度阈值 (低于此值视为正常水)

        Returns:
            分割结果字典
        """
        h, w = image.shape[:2]

        # 1. 使用 RADIO 获取水域热图 (用于定位)
        radio_heatmaps = self.radio_segmentor.compute_patch_similarity(
            image, self.classes_config
        )

        # 2. 获取水域区域 (合并所有水类别的热图)
        water_mask = self._get_water_mask(radio_heatmaps, threshold=0.1)

        if not water_mask.any():
            return {}

        # 3. 在水域区域内进行颜色分类
        color_result = self._classify_water_region(image, water_mask)

        if color_result is None:
            return {}

        best_class, color_score, all_color_scores = color_result

        # 4. 如果是异常类别，检查置信度
        if best_class not in self.anomaly_classes:
            return {}

        # 新增：检查颜色置信度是否足够高
        # 只有高置信度的异常才报告
        min_cls_confidence = self.color_classifier.COLOR_PROFILES.get(
            best_class, {}
        ).get("min_confidence", 0.3)

        # 提高整体置信度要求
        effective_min_confidence = max(min_cls_confidence, 0.4)  # 至少 40% 置信度

        if color_score < effective_min_confidence:
            # 置信度不足，视为正常水
            return {}

        # 5. 使用颜色分类结果细化掩码
        refined_mask = self._refine_mask_by_color(image, water_mask, best_class)

        if not refined_mask.any():
            return {}

        # 6. 后处理
        refined_mask = self._postprocess_mask(refined_mask)
        area = refined_mask.sum() / refined_mask.size

        if area < min_area:
            return {}

        # 7. 计算综合得分
        radio_score = float(radio_heatmaps.get(best_class, np.zeros((h, w))).max())
        normal_radio_score = float(radio_heatmaps.get("normal_water", np.zeros((h, w))).max())

        # 使用 RADIO 得分差异进行后验证
        # 如果 normal_water 的 RADIO 得分远高于预测类别，可能是误检
        radio_margin = radio_score - normal_radio_score

        # 如果 RADIO 明显更倾向于 normal_water，拒绝预测
        if radio_margin < -0.02 and color_score < 0.5:
            return {}

        combined_score = (
            self.color_weight * color_score +
            self.radio_weight * radio_score
        )

        # 最终置信度检查
        if combined_score < 0.25:
            return {}

        cfg = self.classes_config.get(best_class, {})
        zh_name = cfg.get("zh", best_class)

        return {
            best_class: SegmentResult(
                class_name=best_class,
                class_name_cn=zh_name,
                mask=refined_mask,
                area_ratio=float(area),
                score=float(combined_score),
                color_score=float(color_score),
                radio_score=float(radio_score),
            )
        }

    def _get_water_mask(
        self,
        heatmaps: Dict[str, np.ndarray],
        threshold: float = 0.1,
    ) -> np.ndarray:
        """
        从热图获取水域区域

        合并所有水类别的热图，得到粗略的水域范围
        """
        h, w = next(iter(heatmaps.values())).shape
        combined = np.zeros((h, w), dtype=np.float32)

        # 合并所有水类别 (排除 background)
        for cls_name, heatmap in heatmaps.items():
            if cls_name == "background":
                continue
            combined = np.maximum(combined, heatmap)

        # 阈值化
        water_mask = combined > threshold

        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        water_mask = cv2.morphologyEx(
            water_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel
        ).astype(bool)
        water_mask = cv2.morphologyEx(
            water_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel
        ).astype(bool)

        return water_mask

    def _classify_water_region(
        self,
        image: np.ndarray,
        water_mask: np.ndarray,
    ) -> Optional[Tuple[str, float, Dict[str, float]]]:
        """
        对水域区域进行颜色分类
        """
        # 采样水域像素
        ys, xs = np.where(water_mask)
        if len(ys) < 100:
            return None

        # 随机采样 (避免过多像素)
        if len(ys) > 5000:
            idx = np.random.choice(len(ys), 5000, replace=False)
            ys, xs = ys[idx], xs[idx]

        pixels = image[ys, xs]

        # 颜色分类
        best_class, color_score, all_scores = self.color_classifier.classify_region(
            pixels
        )

        return best_class, color_score, all_scores

    def _refine_mask_by_color(
        self,
        image: np.ndarray,
        water_mask: np.ndarray,
        target_class: str,
    ) -> np.ndarray:
        """
        使用颜色细化掩码

        在水域区域内，只保留符合目标类别颜色的像素
        """
        # 获取目标类别的颜色配置
        profile = self.color_classifier.color_profiles.get(target_class)
        if not profile:
            return water_mask

        color_hint = profile.get("color_hint")
        if not color_hint:
            return water_mask

        # 计算每个像素与目标颜色的距离
        h, w = image.shape[:2]
        color_array = np.array(color_hint, dtype=np.float32)

        # 只在水域区域内计算
        distances = np.ones((h, w), dtype=np.float32) * 255

        # 分块处理 (避免内存溢出)
        block_size = 100
        for y in range(0, h, block_size):
            for x in range(0, w, block_size):
                y2 = min(y + block_size, h)
                x2 = min(x + block_size, w)

                block_mask = water_mask[y:y2, x:x2]
                if not block_mask.any():
                    continue

                block = image[y:y2, x:x2].astype(np.float32)
                block_dist = np.linalg.norm(block - color_array, axis=2)

                distances[y:y2, x:x2] = block_dist

        # 根据类别设置距离阈值
        distance_thresholds = {
            "black_water": 80,
            "turbid_water": 80,
            "red_water": 80,
            "green_water": 80,
            "milky_foam_water": 60,  # 更严格
            "dam_seepage": 100,
        }

        dist_threshold = distance_thresholds.get(target_class, 80)

        # 细化掩码
        refined = (distances < dist_threshold) & water_mask

        return refined

    def _postprocess_mask(self, mask: np.ndarray) -> np.ndarray:
        """后处理"""
        if not mask.any():
            return mask

        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.erode(mask.astype(np.uint8), kernel).astype(bool)

        if not mask.any():
            return mask

        mask = cv2.morphologyEx(
            mask.astype(np.uint8), cv2.MORPH_OPEN, kernel
        ).astype(bool)

        # 保留最大连通域
        if mask.any():
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
                mask.astype(np.uint8), connectivity=8
            )
            if num_labels > 1:
                areas = stats[1:, cv2.CC_STAT_AREA]
                largest = int(np.argmax(areas)) + 1
                mask = labels == largest

        return mask

    def visualize(
        self,
        image: np.ndarray,
        segments: Dict[str, SegmentResult],
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        """可视化结果"""
        vis = image.copy()

        CLASS_COLORS = {
            "black_water": (64, 64, 64),
            "turbid_water": (139, 90, 43),
            "red_water": (0, 0, 255),
            "green_water": (0, 255, 0),
            "milky_foam_water": (200, 200, 200),
            "dam_seepage": (128, 128, 128),
            "normal_water": (200, 200, 128),
        }

        for name, seg in segments.items():
            color = CLASS_COLORS.get(name, (128, 128, 128))

            # 半透明覆盖
            mask_uint8 = seg.mask.astype(np.uint8) * 255
            overlay = np.zeros_like(vis)
            overlay[mask_uint8 > 0] = color
            vis = cv2.addWeighted(vis, 0.6, overlay, 0.4, 0)

            # 轮廓
            contours, _ = cv2.findContours(
                mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(vis, contours, -1, color, 2)

            # 标签
            if contours:
                M = cv2.moments(contours[0])
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    label = f"{seg.class_name_cn} ({seg.score:.2f})"
                    cv2.putText(vis, label, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX,
                               0.6, (255, 255, 255), 2)

        if output_path:
            cv2.imwrite(output_path, vis)

        return vis
