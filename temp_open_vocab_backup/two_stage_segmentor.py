#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
两阶段水质分割器 v1.0

策略:
1. 阶段1: 使用 RADIO 提取水体区域 (二分类: water vs non-water)
2. 阶段2: 在水体区域内使用颜色特征 + 训练头进行水质分类

优点:
- 解耦水体定位和水质分类
- 每个阶段可以独立优化
- 第二阶段可以训练小型分类器

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import torch
import torch.nn as nn
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
    water_mask: np.ndarray  # 水体区域掩码
    area_ratio: float
    score: float
    water_iou: float  # 水体提取 IoU
    color_ok: bool = True  # 颜色验证是否通过
    color_score: float = 0.0  # 颜色验证得分


class WaterColorClassifier(nn.Module):
    """
    水质颜色分类器

    基于颜色特征的小型神经网络分类器
    输入: 水体区域的颜色统计特征
    输出: 水质类别概率
    """

    def __init__(
        self,
        input_dim: int = 12,  # 颜色特征维度
        hidden_dim: int = 64,
        num_classes: int = 6,  # 异常水质类别数
    ):
        super().__init__()

        self.classifier = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, num_classes),
        )

        # 类别名称
        self.class_names = [
            "black_water",
            "turbid_water",
            "red_water",
            "green_water",
            "milky_foam_water",
            "dam_seepage",
        ]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, input_dim] 颜色特征

        Returns:
            [B, num_classes] 类别 logits
        """
        return self.classifier(x)

    def predict(self, color_features: Dict[str, float], device: str = "cuda") -> Tuple[str, float]:
        """
        预测水质类别

        Args:
            color_features: 颜色特征字典
            device: 设备

        Returns:
            (类别名, 置信度)
        """
        # 转换为张量
        feat_list = [
            color_features.get("b_mean", 0),
            color_features.get("g_mean", 0),
            color_features.get("r_mean", 0),
            color_features.get("brightness", 0),
            color_features.get("rgb_range", 0),
            color_features.get("r_g_diff", 0),
            color_features.get("r_b_diff", 0),
            color_features.get("g_b_diff", 0),
            color_features.get("g_r_diff", 0),
            color_features.get("b_r_diff", 0),
            color_features.get("b_g_diff", 0),
            color_features.get("saturation", 0),
        ]

        x = torch.tensor([feat_list], dtype=torch.float32).to(device)

        with torch.no_grad():
            logits = self.forward(x)
            probs = F.softmax(logits, dim=-1)

            pred_idx = probs.argmax(dim=-1).item()
            confidence = probs[0, pred_idx].item()

        return self.class_names[pred_idx], confidence


class TwoStageWaterSegmentor:
    """
    两阶段水质分割器

    阶段1: RADIO 水体区域提取
    阶段2: 颜色特征 + 分类器进行水质分类
    """

    # 水体提取提示词
    WATER_PROMPTS = {
        "water": [
            "water surface in natural river or lake",
            "flowing water in channel or stream",
            "standing water body in reservoir",
        ],
        "background": [
            "concrete embankment and walls",
            "land vegetation and grass",
            "sky and clouds",
            "buildings and structures",
            "rocks and stones on ground",
        ]
    }

    # 颜色特征规则 (用于无训练数据时的回退)
    COLOR_RULES = {
        "red_water": {
            "rules": [("r_g_diff", ">", 20), ("r_channel", ">", 150)],
            "min_confidence": 0.5,
        },
        "green_water": {
            "rules": [("g_b_diff", ">", 15), ("g_r_diff", ">", 0)],
            "min_confidence": 0.3,
        },
        "turbid_water": {
            "rules": [("r_g_diff", ">", 0), ("g_b_diff", ">", 8)],
            "min_confidence": 0.3,
        },
        "milky_foam_water": {
            "rules": [("brightness", ">", 140), ("rgb_range", "<", 40)],
            "min_confidence": 0.3,
        },
        "black_water": {
            "rules": [("rgb_range", "<", 25), ("brightness", "<", 130)],
            "min_confidence": 0.3,
        },
    }

    def __init__(
        self,
        radio_segmentor,
        classes_config: Dict[str, dict],
        classifier: Optional[WaterColorClassifier] = None,
        water_threshold: float = 0.5,
    ):
        """
        Args:
            radio_segmentor: RADIO 分割器
            classes_config: 类别配置
            classifier: 可选的训练好的分类器
            water_threshold: 水体提取阈值
        """
        self.radio_segmentor = radio_segmentor
        self.classes_config = classes_config
        self.classifier = classifier
        self.water_threshold = water_threshold
        self.device = getattr(radio_segmentor, 'device', 'cuda')  # 获取设备

        # 异常类别
        self.anomaly_classes = {
            k for k, v in classes_config.items()
            if not v.get("is_background", False)
        }

        # 类别中文名
        self.class_names_cn = {
            k: v.get("zh", k) for k, v in classes_config.items()
        }

        logger.info(f"两阶段分割器初始化:")
        logger.info(f"  水体阈值: {water_threshold}")
        logger.info(f"  异常类别: {len(self.anomaly_classes)}")

    def extract_water_region(
        self,
        image: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        阶段1: 提取水体区域

        Args:
            image: BGR 图像

        Returns:
            (water_mask, water_prob_map, avg_confidence)
        """
        # 构建配置
        classes_config = {
            "water": {"prompts": self.WATER_PROMPTS["water"]},
            "background": {"prompts": self.WATER_PROMPTS["background"]},
        }

        # 计算热图
        heatmaps = self.radio_segmentor.compute_patch_similarity(
            image, classes_config
        )

        if "water" not in heatmaps or "background" not in heatmaps:
            return None, None, 0.0

        # 计算 softmax 概率
        water_heatmap = heatmaps["water"]
        bg_heatmap = heatmaps["background"]

        # Softmax: water_prob = exp(water) / (exp(water) + exp(bg))
        combined = np.stack([water_heatmap, bg_heatmap], axis=-1)
        combined_max = combined.max(axis=-1, keepdims=True)
        exp_combined = np.exp(combined - combined_max)
        probs = exp_combined / exp_combined.sum(axis=-1, keepdims=True)

        water_prob = probs[..., 0]

        # 阈值化
        water_mask = water_prob > self.water_threshold

        # 形态学后处理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        water_mask = cv2.morphologyEx(
            water_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel
        )
        water_mask = cv2.morphologyEx(
            water_mask, cv2.MORPH_OPEN, kernel
        ).astype(bool)

        avg_conf = float(water_prob[water_mask].mean()) if water_mask.any() else 0.0

        return water_mask, water_prob, avg_conf

    def extract_color_features(
        self,
        image: np.ndarray,
        mask: np.ndarray,
    ) -> Dict[str, float]:
        """
        提取区域的颜色特征

        Args:
            image: BGR 图像
            mask: 区域掩码

        Returns:
            颜色特征字典
        """
        ys, xs = np.where(mask)
        if len(ys) == 0:
            return {}

        pixels = image[ys, xs].astype(np.float32)

        b_mean = pixels[:, 0].mean()
        g_mean = pixels[:, 1].mean()
        r_mean = pixels[:, 2].mean()
        brightness = (b_mean + g_mean + r_mean) / 3

        features = {
            "b_mean": b_mean,
            "g_mean": g_mean,
            "r_mean": r_mean,
            "brightness": brightness,
            "max_rgb": max(r_mean, g_mean, b_mean),
            "min_rgb": min(r_mean, g_mean, b_mean),
            "rgb_range": max(r_mean, g_mean, b_mean) - min(r_mean, g_mean, b_mean),
            "r_g_diff": r_mean - g_mean,
            "r_b_diff": r_mean - b_mean,
            "g_b_diff": g_mean - b_mean,
            "g_r_diff": g_mean - r_mean,
            "b_r_diff": b_mean - r_mean,
            "b_g_diff": b_mean - g_mean,
            "saturation": 0.0,
        }

        max_c = max(r_mean, g_mean, b_mean)
        if max_c > 0:
            features["saturation"] = features["rgb_range"] / max_c * 100

        return features

    def validate_color_consistency(
        self,
        class_name: str,
        class_prob: float,
        region_bgr: np.ndarray,
        classes_config: Dict[str, dict],
    ) -> Tuple[bool, float]:
        """
        验证颜色一致性 (借鉴 v4.1 策略)

        Args:
            class_name: 分类类别名
            class_prob: 分类置信度
            region_bgr: 区域平均 BGR 颜色
            classes_config: 类别配置

        Returns:
            (is_valid, adjusted_prob): (是否通过颜色校验, 调整后的置信度)
        """
        if region_bgr is None:
            return True, class_prob

        cls_cfg = classes_config.get(class_name, {})

        # 获取颜色提示
        color_hint = cls_cfg.get("color_hint")
        if color_hint is None or len(color_hint) != 3:
            return True, class_prob

        # 计算颜色距离 (归一化)
        region_bgr = np.asarray(region_bgr, dtype=np.float32)
        color_hint = np.asarray(color_hint, dtype=np.float32)
        color_dist = np.linalg.norm(region_bgr - color_hint) / 441.67  # max dist = sqrt(255^2 * 3) ≈ 441.67

        # 阈值 (借鉴 v4.1: 100 / 441.67 ≈ 0.226)
        threshold = 100 / 441.67

        # 如果颜色距离超过阈值，降低置信度
        if color_dist > threshold:
            # 动态惩罚 (借鉴 v4.1)
            penalty = min(0.5, (color_dist - threshold) * 2)
            adjusted_prob = class_prob * (1.0 - penalty)
            return False, adjusted_prob

        return True, class_prob

    def classify_water_by_rules(
        self,
        color_features: Dict[str, float],
    ) -> Tuple[str, float]:
        """
        使用颜色规则分类 (无训练模型时的回退)

        Args:
            color_features: 颜色特征

        Returns:
            (类别名, 置信度)
        """
        best_class = "normal_water"
        best_score = 0.0

        for cls_name, config in self.COLOR_RULES.items():
            rules = config.get("rules", [])
            min_conf = config.get("min_confidence", 0.3)

            if not rules:
                continue

            # 检查所有规则
            rule_scores = []
            for feat_name, op, threshold in rules:
                if feat_name not in color_features:
                    rule_scores.append(0)
                    continue

                value = color_features[feat_name]

                if op == ">":
                    if value <= threshold:
                        rule_scores.append(0)
                    else:
                        score = min(1.0, (value - threshold) / threshold)
                        rule_scores.append(score)
                elif op == "<":
                    if value >= threshold:
                        rule_scores.append(0)
                    else:
                        score = min(1.0, (threshold - value) / threshold)
                        rule_scores.append(score)

            if not rule_scores:
                continue

            avg_score = np.mean(rule_scores)

            if all(s > 0 for s in rule_scores) and avg_score > best_score:
                best_score = avg_score
                best_class = cls_name

        return best_class, best_score

    def classify_water(
        self,
        image: np.ndarray,
        water_mask: np.ndarray,
    ) -> Tuple[str, float, Dict[str, float]]:
        """
        阶段2: 在水体区域内进行水质分类

        Args:
            image: BGR 图像
            water_mask: 水体掩码

        Returns:
            (类别名, 置信度, 所有颜色特征)
        """
        if not water_mask.any():
            return "normal_water", 0.0, {}

        # 提取颜色特征
        color_features = self.extract_color_features(image, water_mask)

        if not color_features:
            return "normal_water", 0.0, {}

        # 如果有训练好的分类器，使用分类器
        if self.classifier is not None:
            device = getattr(self, 'device', 'cuda')
            pred_class, confidence = self.classifier.predict(color_features, device=device)
            return pred_class, confidence, color_features

        # 否则使用规则
        pred_class, confidence = self.classify_water_by_rules(color_features)
        return pred_class, confidence, color_features

    def segment(
        self,
        image: np.ndarray,
        min_area: float = 0.005,
        min_confidence: float = 0.3,
    ) -> Dict[str, SegmentResult]:
        """
        执行两阶段水质分割

        Args:
            image: BGR 图像
            min_area: 最小面积比例
            min_confidence: 最小置信度

        Returns:
            分割结果字典
        """
        h, w = image.shape[:2]

        # 阶段1: 提取水体区域
        water_mask, water_prob, water_conf = self.extract_water_region(image)

        if water_mask is None or not water_mask.any():
            return {}

        # 阶段2: 水质分类
        pred_class, confidence, color_features = self.classify_water(image, water_mask)

        # 检查是否为异常类别
        if pred_class not in self.anomaly_classes:
            return {}

        # 阶段2.5: 颜色一致性验证 (借鉴 v4.1)
        region_bgr = [
            color_features.get("b_mean", 0),
            color_features.get("g_mean", 0),
            color_features.get("r_mean", 0),
        ]
        color_ok, adjusted_confidence = self.validate_color_consistency(
            pred_class, confidence, region_bgr, self.classes_config
        )

        # 如果颜色验证失败，使用调整后的置信度
        if not color_ok:
            confidence = adjusted_confidence

        # 检查置信度
        if confidence < min_confidence:
            return {}

        # 计算面积
        area = water_mask.sum() / water_mask.size
        if area < min_area:
            return {}

        # 后处理
        water_mask = self._postprocess_mask(water_mask)

        zh_name = self.class_names_cn.get(pred_class, pred_class)

        return {
            pred_class: SegmentResult(
                class_name=pred_class,
                class_name_cn=zh_name,
                mask=water_mask,
                water_mask=water_mask,
                area_ratio=float(area),
                score=float(confidence),
                water_iou=float(water_conf),
                color_ok=color_ok,
                color_score=adjusted_confidence,
            )
        }

    def _postprocess_mask(self, mask: np.ndarray) -> np.ndarray:
        """后处理掩码"""
        if not mask.any():
            return mask

        # 保留最大连通域
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
        result: SegmentResult,
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        """可视化结果"""
        vis = image.copy()

        # 颜色映射
        CLASS_COLORS = {
            "black_water": (64, 64, 64),
            "turbid_water": (139, 90, 43),
            "red_water": (0, 0, 255),
            "green_water": (0, 255, 0),
            "milky_foam_water": (200, 200, 200),
            "dam_seepage": (128, 128, 128),
        }

        color = CLASS_COLORS.get(result.class_name, (128, 128, 128))

        # 半透明覆盖
        mask_uint8 = result.mask.astype(np.uint8) * 255
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
                label = f"{result.class_name_cn} ({result.score:.2f})"
                cv2.putText(vis, label, (cx - 50, cy), cv2.FONT_HERSHEY_SIMPLEX,
                           0.7, (255, 255, 255), 2)

        if output_path:
            cv2.imwrite(output_path, vis)

        return vis
