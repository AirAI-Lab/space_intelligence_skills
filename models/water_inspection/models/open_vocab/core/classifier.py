#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分类器模块

包含:
1. SigLIP2文本分类器 - 使用RADIO的SigLIP2 adaptor进行零样本分类
2. 颜色校验器 - 基于颜色特征的水质分类和一致性校验

作者: 空中智能体团队
日期: 2026-04-05
"""

import torch
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SigLIP2Classifier:
    """
    SigLIP2 文本分类器

    使用 RADIO 的 SigLIP2 adaptor 进行零样本分类
    支持正负提示词的对比学习
    """

    def __init__(
        self,
        backbone,  # RadioBackbone 实例
        temperature: float = 6.0,
        negative_weight: float = 0.35,
    ):
        """
        Args:
            backbone: RadioBackbone 实例
            temperature: 温度缩放系数
            negative_weight: 负提示词权重
        """
        self.backbone = backbone
        self.temperature = temperature
        self.negative_weight = negative_weight
        self.device = backbone.device

    @torch.no_grad()
    def encode_text(self, texts: List[str]) -> torch.Tensor:
        """编码文本为特征向量"""
        return self.backbone.encode_text(texts)

    @torch.no_grad()
    def classify_image(
        self,
        image: np.ndarray,
        classes_config: Dict[str, dict],
        prompts_config: Optional[Dict[str, dict]] = None,
    ) -> Dict[str, float]:
        """
        图像级分类

        Args:
            image: BGR 图像
            classes_config: 类别配置
            prompts_config: 提示词配置 (含 positive 和 negative)

        Returns:
            {class_name: probability}
        """
        import cv2

        # 准备图像张量
        image_rgb = image[:, :, ::-1].copy()
        image_resized = cv2.resize(image_rgb, (self.backbone.input_size if hasattr(self.backbone, 'input_size') else 896,
                                     self.backbone.input_size if hasattr(self.backbone, 'input_size') else 896))
        image_tensor = torch.from_numpy(image_resized).permute(2, 0, 1).unsqueeze(0)
        image_tensor = image_tensor.float().div(255.0).to(self.device)

        # 构建文本列表 (支持正负提示词)
        pos_texts = []
        neg_texts = []
        pos_class_names = []
        neg_class_names = []

        for cls_name, cfg in classes_config.items():
            cls_prompt_cfg = (prompts_config or {}).get(cls_name, {})
            pos_prompts = cls_prompt_cfg.get("positive") or cfg.get("prompts", [cls_name.replace("_", " ")])
            neg_prompts = cls_prompt_cfg.get("negative") or []

            pos_texts.extend(pos_prompts)
            pos_class_names.extend([cls_name] * len(pos_prompts))
            neg_texts.extend(neg_prompts)
            neg_class_names.extend([cls_name] * len(neg_prompts))

        texts = pos_texts + neg_texts

        # 使用 backbone 的 compute_similarity 方法
        try:
            similarity = self.backbone.compute_similarity(image_tensor, texts)  # [B, num_texts]
            probs = torch.sigmoid(similarity)[0]  # [num_texts]
        except Exception as e:
            logger.warning(f"compute_similarity 失败: {e}")
            return {}

        # 聚合: 正提示取最大, 负提示作为抑制
        class_probs = {cls_name: 0.0 for cls_name in classes_config.keys()}
        class_neg = {cls_name: 0.0 for cls_name in classes_config.keys()}

        for i, cls_name in enumerate(pos_class_names):
            p = probs[i].item()
            if p > class_probs[cls_name]:
                class_probs[cls_name] = p

        offset = len(pos_texts)
        for i, cls_name in enumerate(neg_class_names):
            p = probs[offset + i].item()
            if p > class_neg[cls_name]:
                class_neg[cls_name] = p

        if neg_texts:
            for cls_name in class_probs.keys():
                class_probs[cls_name] = max(
                    0.0,
                    class_probs[cls_name] - self.negative_weight * class_neg[cls_name],
                )

        return class_probs

    @torch.no_grad()
    def compute_patch_similarity(
        self,
        image: np.ndarray,
        classes_config: Dict[str, dict],
        prompts_config: Optional[Dict[str, dict]] = None,
        input_size: int = 896,
    ) -> Dict[str, np.ndarray]:
        """
        计算每个 patch 与各类别的相似度

        Args:
            image: BGR 图像 [H, W, 3]
            classes_config: 类别配置
            prompts_config: 提示词配置
            input_size: 输入尺寸

        Returns:
            class_heatmaps: {class_name: heatmap [H, W]}
        """
        import cv2

        orig_h, orig_w = image.shape[:2]

        # 准备图像张量
        image_rgb = image[:, :, ::-1].copy()
        image_resized = cv2.resize(image_rgb, (input_size, input_size))
        image_tensor = torch.from_numpy(image_resized).permute(2, 0, 1).unsqueeze(0)
        image_tensor = image_tensor.float().div(255.0).to(self.device)

        # 构建文本列表 (支持正负提示词)
        class_order = list(classes_config.keys())
        class_to_idx = {cls_name: i for i, cls_name in enumerate(class_order)}

        pos_texts = []
        neg_texts = []
        pos_class_names = []
        neg_class_names = []

        for cls_name in class_order:
            cfg = classes_config.get(cls_name, {})
            cls_prompt_cfg = (prompts_config or {}).get(cls_name, {})
            pos_prompts = cls_prompt_cfg.get("positive") or cfg.get("prompts", [cls_name.replace("_", " ")])
            neg_prompts = cls_prompt_cfg.get("negative") or []

            pos_texts.extend(pos_prompts)
            pos_class_names.extend([cls_name] * len(pos_prompts))
            neg_texts.extend(neg_prompts)
            neg_class_names.extend([cls_name] * len(neg_prompts))

        texts = pos_texts + neg_texts

        # 检查空文本列表
        if not texts:
            logger.warning("没有有效的提示词文本，返回默认分类")
            return {cls_name: 1.0/len(classes_config) for cls_name in classes_config.keys()}

        # 使用 backbone 的 SigLIP2 adaptor
        adaptor = self.backbone._get_siglip_adaptor()
        if adaptor is None:
            return {}

        # 编码文本
        text_tokens = adaptor.tokenizer(texts).to(self.device)
        text_features = adaptor.encode_text(text_tokens, normalize=True)

        # 提取特征
        result = self.backbone.extract_features(image_tensor, output_spatial=True)
        features = result["features"]  # [1, N_patches, D]
        H_patch, W_patch = result["grid_size"]

        # 获取 adaptor 特征 (与文本空间对齐)
        adaptor_features = result.get("adaptor_features", features)

        # 确保 adaptor_features 是 tensor
        if not isinstance(adaptor_features, torch.Tensor):
            adaptor_features = features

        # 对每个 patch 计算与文本的相似度
        B, N, D = adaptor_features.shape
        patch_features = adaptor_features.view(B * N, D)  # [N, D]
        patch_features_norm = F.normalize(patch_features.float(), dim=-1)

        # 计算相似度并做对比聚合
        similarity = patch_features_norm @ text_features.T
        probs = torch.sigmoid(similarity)

        pos_probs = torch.zeros(N, len(class_order), device=self.device)
        neg_probs = torch.zeros(N, len(class_order), device=self.device)

        for i, cls_name in enumerate(pos_class_names):
            cls_idx = class_to_idx[cls_name]
            pos_probs[:, cls_idx] = torch.maximum(pos_probs[:, cls_idx], probs[:, i])

        offset = len(pos_texts)
        for i, cls_name in enumerate(neg_class_names):
            cls_idx = class_to_idx[cls_name]
            neg_probs[:, cls_idx] = torch.maximum(neg_probs[:, cls_idx], probs[:, offset + i])

        raw_scores = pos_probs - self.negative_weight * neg_probs
        # 使用逐类 sigmoid, 避免多类 softmax 把异常类别压成接近均匀分布
        class_probs = torch.sigmoid(raw_scores * self.temperature)

        # 构建热图
        class_heatmaps = {}
        for cls_name, idx in class_to_idx.items():
            heatmap = class_probs[:, idx].view(1, H_patch, W_patch)
            heatmap_up = F.interpolate(
                heatmap.unsqueeze(0), size=(orig_h, orig_w),
                mode="bilinear", align_corners=False
            ).squeeze().cpu().numpy()
            class_heatmaps[cls_name] = heatmap_up

        return class_heatmaps


class ColorValidator:
    """
    颜色校验器

    基于颜色特征进行水质分类和一致性校验
    支持 7 类水质: 黑水、浑浊水、红水、绿水、乳白水、坝体渗水、正常水质
    """

    # 颜色特征定义 (BGR 顺序) - 基于 100 样本实际数据集分析
    COLOR_PROFILES = {
        "red_water": {
            "description": "红水 - R 明显高于 G",
            "rules": [
                ("r_g_diff", ">", 20),      # R - G > 20 (实际: 41)
                ("r_channel", ">", 150),    # R > 150 (实际: 198)
            ],
            "color_hint": [132, 157, 198],  # BGR
            "priority": 1,  # 最高优先级
            "min_confidence": 0.5,
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
            "description": "乳白水 - 高亮度, 低饱和度",
            "rules": [
                ("brightness", ">", 140),   # 亮度 > 140 (实际: 154)
                ("rgb_range", "<", 40),     # RGB 范围 < 40 (实际: 15)
            ],
            "color_hint": [154, 154, 153],  # BGR
            "priority": 4,
            "min_confidence": 0.3,
        },
        "black_water": {
            "description": "黑水 - RGB 接近, 亮度低",
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
            classes_config: 可选的类别配置, 覆盖默认颜色配置
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

    def extract_color_features_from_mask(
        self,
        image: np.ndarray,
        mask: np.ndarray,
    ) -> Dict[str, float]:
        """
        从掩码区域提取颜色特征

        Args:
            image: BGR 图像
            mask: 布尔掩码

        Returns:
            特征字典
        """
        ys, xs = np.where(mask)
        if len(ys) == 0:
            return {}

        pixels = image[ys, xs]
        return self.extract_color_features(pixels)

    def compute_color_distance(
        self,
        region_bgr: np.ndarray,
        color_hint: List[int],
    ) -> float:
        """
        计算区域颜色与提示颜色的距离

        Args:
            region_bgr: 区域平均 BGR 值 [B, G, R]
            color_hint: 颜色提示 [B, G, R]

        Returns:
            颜色距离 (归一化 0-1)
        """
        if region_bgr is None or color_hint is None:
            return 1.0  # 最大距离

        # 计算欧氏距离
        dist = np.sqrt(
            (region_bgr[0] - color_hint[0]) ** 2 +
            (region_bgr[1] - color_hint[1]) ** 2 +
            (region_bgr[2] - color_hint[2]) ** 2
        )

        # 归一化到 0-1 范围
        max_dist = np.sqrt(255 ** 2 * 3)  # 441.67
        normalized_dist = dist / max_dist

        return normalized_dist

    def validate_color_consistency(
        self,
        class_name: str,
        class_prob: float,
        region_bgr: Optional[np.ndarray],
        classes_config: Dict[str, dict],
        max_dist: float = 100,
    ) -> Tuple[bool, float]:
        """
        验证颜色一致性

        Args:
            class_name: 分类类别名
            class_prob: 分类置信度
            region_bgr: GT 区域平均 BGR 颜色
            classes_config: 类别配置
            max_dist: 最大颜色距离阈值

        Returns:
            (is_valid, adjusted_prob): (是否通过颜色校验, 调整后的置信度)
        """
        # 如果没有颜色信息或未启用颜色校验, 直接返回
        if region_bgr is None:
            return True, class_prob

        cls_cfg = classes_config.get(class_name, {})

        # 检查是否启用颜色校验
        if not cls_cfg.get("use_color_check", False):
            return True, class_prob

        # 获取颜色提示
        color_hint = cls_cfg.get("color_hint")
        if color_hint is None or len(color_hint) != 3:
            return True, class_prob

        # 计算颜色距离
        color_dist = self.compute_color_distance(region_bgr, color_hint)

        # 如果颜色距离超过阈值, 降低置信度
        threshold = max_dist / 441.67  # 归一化阈值
        if color_dist > threshold:
            # 根据距离严重程度降低置信度
            penalty = min(0.5, (color_dist - threshold) * 2)
            adjusted_prob = class_prob * (1.0 - penalty)
            return False, adjusted_prob

        return True, class_prob

    def classify_by_color(
        self,
        bgr_region: np.ndarray,
        exclude_classes: Optional[set] = None,
    ) -> Tuple[str, float, Dict[str, float]]:
        """
        对一个区域进行水质颜色分类

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

            # 如果没有规则 (normal_water, dam_seepage), 跳过
            if not rules:
                continue

            # 检查所有规则是否都满足 (至少 > 0)
            rule_scores = [self._evaluate_rule(features, r) for r in rules]

            # 所有规则必须都得分 > 0 才算匹配
            if all(s > 0 for s in rule_scores):
                avg_score = np.mean(rule_scores)
                class_scores[cls_name] = avg_score

                # 高优先级类别匹配成功, 直接返回
                if profile.get("priority", 99) < 5:
                    return cls_name, avg_score, class_scores

        # 如果没有匹配的类别, 返回 normal_water
        if not class_scores:
            return "normal_water", 0.0, {}

        # 返回得分最高的类别
        best_class = max(class_scores.keys(), key=lambda k: class_scores[k])
        best_score = class_scores[best_class]

        return best_class, best_score, class_scores

    def _evaluate_rule(self, features: Dict[str, float], rule: Tuple) -> float:
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
            # 超过阈值越多, 得分越高
            if value <= threshold:
                return 0.0
            return min(1.0, (value - threshold) / threshold)
        elif op == "<":
            # 低于阈值越多, 得分越高
            if value >= threshold:
                return 0.0
            return min(1.0, (threshold - value) / threshold)
        elif op == "==":
            return 1.0 if abs(value - threshold) < 10 else 0.0

        return 0.0

    def classify_mask_by_color(
        self,
        image: np.ndarray,
        mask: np.ndarray,
    ) -> Tuple[str, float, Dict[str, float]]:
        """
        对掩码区域进行颜色分类

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
        return self.classify_by_color(pixels)
