#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
C-RADIOv4 水质异常分割器 v4.1

⭐ v4.1更新 (2026-04-05):
  - 实现Patch分类参数配置 (top-k, overlap_threshold)
  - 添加颜色特征校验功能
  - 优化分割质量

核心流程:
  1. 使用SigLIP2 adaptor进行patch级别的零样本分类
  2. 使用adaptor_features（与文本空间对齐）进行类别匹配
  3. 应用top-k选择和颜色校验
  4. 生成类别热图并阈值分割

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import torch
import torch.nn.functional as F
import numpy as np
import cv2
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

from .radio_backbone import RadioBackbone

logger = logging.getLogger(__name__)


def _odd_kernel(v: int, default: int) -> int:
    """将核大小规范为 >=3 的奇数"""
    try:
        x = max(3, int(v))
        return x + 1 if x % 2 == 0 else x
    except Exception:
        return default


@dataclass
class SegmentResult:
    """分割结果"""
    class_name: str
    class_name_cn: str
    mask: np.ndarray        # [H, W] bool
    area_ratio: float       # 占图像面积比
    score: float            # 置信度
    patch_scores: Optional[np.ndarray] = None


class WaterQualitySegmentor:
    """
    水质异常分割器 (C-RADIOv4) v4.0

    正确利用C-RADIOv4的内置SigLIP2 adaptor进行:
      1. 图像级分类
      2. Patch级分类
      3. 类别热图生成
    """

    # 类别颜色映射 (BGR)
    CLASS_COLORS = {
        "black_water": (0, 0, 180),
        "brown_water": (42, 42, 165),
        "yellow_water": (0, 255, 255),
        "green_water": (0, 200, 0),
        "red_water": (0, 0, 255),
        "milky_water": (200, 200, 200),
        "foam_water": (180, 180, 255),
        "dam_seepage": (100, 100, 100),
        "normal_water": (200, 200, 100),
    }

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        radio_code_dir: Optional[str] = None,
        siglip2_dir: Optional[str] = None,
        device: str = "cuda",
        input_size: int = 896,
        config: Optional[Dict] = None,
    ):
        self.device = device
        self.input_size = input_size
        self.config = config or {}

        # 加载 RADIO backbone (包含 SigLIP2 adaptor)
        self.backbone = RadioBackbone(
            checkpoint_path=checkpoint_path,
            radio_code_dir=radio_code_dir,
            siglip2_dir=siglip2_dir,
            device=device,
        )

        # 加载推理参数
        self._load_inference_config()

    def _load_inference_config(self):
        """加载推理配置参数"""
        radio_cfg = self.config.get("cloud", {}).get("radio", {})
        infer_cfg = radio_cfg.get("inference", {})

        # 基础参数
        self.threshold = infer_cfg.get("threshold", 0.30)
        self.min_area = infer_cfg.get("min_area", 0.005)
        self.image_gate = infer_cfg.get("image_gate", 0.08)
        self.class_thresholds = infer_cfg.get("class_thresholds", {}) or {}

        # 后处理参数
        post_cfg = infer_cfg.get("postprocess", {})
        self.post_erode_kernel = post_cfg.get("erode_kernel", 2)
        self.post_open_kernel = post_cfg.get("open_kernel", 2)
        self.post_max_components = post_cfg.get("max_components", 3)
        self.post_min_component_pixels = post_cfg.get("min_component_pixels", 50)

        # 水体识别参数
        water_cfg = infer_cfg.get("water", {})
        self.water_min_ratio = water_cfg.get("min_ratio", 0.05)
        self.water_erode_kernel = water_cfg.get("erode_kernel", 7)

        # 正常标签输出
        self.emit_normal_label = infer_cfg.get("emit_normal_label", True)
        self.normal_label_min_prob = infer_cfg.get("normal_label_min_prob", 0.45)
        self.normal_label_max_anomaly_prob = infer_cfg.get("normal_label_max_anomaly_prob", 0.35)

        # ⭐ Patch分类参数 (v3.3新增)
        patch_cfg = infer_cfg.get("patch", {})
        self.num_patches = patch_cfg.get("num_patches", 64)
        self.min_overlap_threshold = patch_cfg.get("min_overlap_threshold", 0.50)
        self.patch_selection_strategy = patch_cfg.get("patch_selection_strategy", "top_k")
        self.top_k_patches = patch_cfg.get("top_k_patches", 10)
        self.overlap_weight = patch_cfg.get("overlap_weight", 1.5)

        # ⭐ 颜色校验参数 (v3.3新增)
        color_cfg = infer_cfg.get("color", {})
        self.color_max_dist = color_cfg.get("max_dist", 100)
        self.color_strict_prob = color_cfg.get("strict_prob", 0.65)
        self.color_enable_per_class = color_cfg.get("enable_per_class", True)
        self.color_fusion_alpha = float(color_cfg.get("fusion_alpha", 0.20))

        # 提示词对比参数
        prompt_cfg = infer_cfg.get("prompt", {})
        self.prompt_negative_weight = float(prompt_cfg.get("negative_weight", 0.35))
        self.prompt_temperature = float(prompt_cfg.get("temperature", 6.0))

    def get_classes_config(self) -> Dict[str, dict]:
        """获取类别配置"""
        radio_cfg = self.config.get("cloud", {}).get("radio", {})
        return radio_cfg.get("classes", {})

    # ─────────────────────────────────────────────────────────────────────
    # 颜色特征校验 (v3.3新增)
    # ─────────────────────────────────────────────────────────────────────

    def _compute_color_distance(
        self,
        region_bgr: np.ndarray,
        color_hint: List[int],
    ) -> float:
        """
        计算区域颜色与提示颜色的距离
        
        Args:
            region_bgr: 区域平均BGR值 [B, G, R]
            color_hint: 颜色提示 [B, G, R]
        
        Returns:
            颜色距离 (0-255范围)
        """
        if region_bgr is None or color_hint is None:
            return 0e10  # 最大距离
        
        # 计算欧氏距离
        dist = np.sqrt(
            (region_bgr[0] - color_hint[0])**2 +
            (region_bgr[1] - color_hint[1])**2 +
            (region_bgr[2] - color_hint[2])**2
        )
        
        # 归一化到0-1范围
        max_dist = np.sqrt(255**2 * 3)  # 441.67
        normalized_dist = dist / max_dist
        
        return normalized_dist

    def _validate_color_consistency(
        self,
        class_name: str,
        class_prob: float,
        region_bgr: Optional[np.ndarray],
        classes_config: Dict[str, dict],
    ) -> Tuple[bool, float]:
        """
        验证颜色一致性
        
        Args:
            class_name: 分类类别名
            class_prob: 分类置信度
            region_bgr: GT区域平均BGR颜色
            classes_config: 类别配置
        
        Returns:
            (is_valid, adjusted_prob): (是否通过颜色校验, 调整后的置信度)
        """
        # 如果没有颜色信息或未启用颜色校验，直接返回
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
        color_dist = self._compute_color_distance(region_bgr, color_hint)
        
        # 如果颜色距离超过阈值，降低置信度
        if color_dist > self.color_max_dist / 441.67:  # 归一化阈值
            # 根据距离严重程度降低置信度
            penalty = min(0.5, (color_dist - self.color_max_dist/441.67) * 2)
            adjusted_prob = class_prob * (1.0 - penalty)
            return False, adjusted_prob
        
        return True, class_prob

    # ─────────────────────────────────────────────────────────────────────
    # SigLIP2 分类 (使用C-RADIOv4内置的SigLIP2 adaptor)
    # ─────────────────────────────────────────────────────────────────────

    @torch.no_grad()
    def classify_image(
        self,
        image: np.ndarray,
        classes_config: Dict[str, dict],
        prompts_config: Optional[Dict[str, dict]] = None,
    ) -> Dict[str, float]:
        """
        使用C-RADIOv4的SigLIP2 adaptor进行图像级分类

        Args:
            image: BGR 图像
            classes_config: 类别配置

        Returns:
            {class_name: probability}
        """
        # 准备图像张量
        image_rgb = image[:, :, ::-1].copy()
        image_resized = cv2.resize(image_rgb, (self.input_size, self.input_size))
        image_tensor = torch.from_numpy(image_resized).permute(2, 0, 1).unsqueeze(0)
        image_tensor = image_tensor.float().div(255.0).to(self.device)

        # 构建文本列表（支持正负提示词）
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

        # 使用backbone的compute_similarity方法
        try:
            similarity = self.backbone.compute_similarity(
                image_tensor, texts
            )  # [B, num_texts]
            probs = torch.sigmoid(similarity)[0]  # [num_texts]
        except Exception as e:
            logger.warning(f"compute_similarity失败: {e}")
            return {}

        # 聚合: 正提示取最大，负提示作为抑制
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
                    class_probs[cls_name] - self.prompt_negative_weight * class_neg[cls_name],
                )

        return class_probs

    @torch.no_grad()
    def compute_patch_similarity(
        self,
        image: np.ndarray,
        classes_config: Dict[str, dict],
        prompts_config: Optional[Dict[str, dict]] = None,
    ) -> Dict[str, np.ndarray]:
        """
        计算每个patch与各类别的相似度

        Args:
            image: BGR图像 [H, W, 3]
            classes_config: 类别配置

        Returns:
            class_heatmaps: {class_name: heatmap [H, W]}
        """
        orig_h, orig_w = image.shape[:2]

        # 准备图像张量
        image_rgb = image[:, :, ::-1].copy()
        image_resized = cv2.resize(image_rgb, (self.input_size, self.input_size))
        image_tensor = torch.from_numpy(image_resized).permute(2, 0, 1).unsqueeze(0)
        image_tensor = image_tensor.float().div(255.0).to(self.device)

        # 构建文本列表（支持正负提示词）
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

        # 使用backbone的SigLIP2 adaptor
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

        # 获取adaptor特征 (与文本空间对齐)
        adaptor_features = result.get("adaptor_features", features)

        # 确保adaptor_features是tensor
        if not isinstance(adaptor_features, torch.Tensor):
            adaptor_features = features

        # 对每个patch计算与文本的相似度
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

        raw_scores = pos_probs - self.prompt_negative_weight * neg_probs
        # 使用逐类 sigmoid，避免多类 softmax 把异常类别压成接近均匀分布
        class_probs = torch.sigmoid(raw_scores * self.prompt_temperature)

        # ⭐ v3.3: Top-K Patch选择策略
        if self.patch_selection_strategy == "top_k":
            # 对每个类别选择top-k patches
            for cls_idx in range(len(class_order)):
                class_patch_probs = class_probs[:, cls_idx]
                # 获取top-k个最高概率的patches
                top_k = min(self.top_k_patches, N)
                top_k_values, top_k_indices = torch.topk(class_patch_probs, top_k)
                
                # 创建mask，只保留top-k patches
                mask = torch.zeros(N, device=self.device)
                mask[top_k_indices] = 1.0
                
                # 应用mask
                class_probs[:, cls_idx] = class_probs[:, cls_idx] * mask

        # 构建热图
        class_heatmaps = {}
        for cls_name, idx in class_to_idx.items():
            heatmap = class_probs[:, idx].view(1, H_patch, W_patch)
            
            # ⭐ v3.3: 应用overlap权重
            if self.overlap_weight != 1.0:
                heatmap = heatmap * self.overlap_weight
            
            heatmap_up = F.interpolate(
                heatmap.unsqueeze(0), size=(orig_h, orig_w),
                mode="bilinear", align_corners=False
            ).squeeze().cpu().numpy()
            
            # ⭐ v3.3: 应用最小overlap阈值（低于阈值置零，不抬升低分）
            # softmax 多类场景下，0.5 对类别概率过严，自动映射到可用范围。
            if self.min_overlap_threshold > 0:
                overlap_thr = float(self.min_overlap_threshold)
                if overlap_thr >= 0.5:
                    overlap_thr = max(0.08, 1.0 / max(2, len(class_order)))
                heatmap_up = np.where(heatmap_up >= overlap_thr, heatmap_up, 0.0)
            
            class_heatmaps[cls_name] = heatmap_up

        return class_heatmaps

    # ─────────────────────────────────────────────────────────────────────
    # 水体识别
    # ─────────────────────────────────────────────────────────────────────

    def _identify_water_region(
        self,
        class_heatmaps: Dict[str, np.ndarray],
        orig_h: int,
        orig_w: int,
    ) -> np.ndarray:
        """识别可信水体区域"""
        trusted_water = np.zeros((orig_h, orig_w), dtype=bool)

        # 从 normal_water 热图构建
        if "normal_water" in class_heatmaps:
            normal_heatmap = class_heatmaps["normal_water"]
            trusted_water = normal_heatmap > 0.3

        trusted_ratio = trusted_water.sum() / trusted_water.size

        # 如果没有正常水区域，使用底部启发式
        if trusted_ratio < self.water_min_ratio:
            y_cutoff = int(orig_h * 0.25)
            trusted_water = np.zeros((orig_h, orig_w), dtype=bool)
            trusted_water[y_cutoff:, :] = True

        # 水体边界收缩
        kernel_size = _odd_kernel(self.water_erode_kernel, 7)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        water_eroded = cv2.erode(trusted_water.astype(np.uint8), kernel).astype(bool)

        # 保留最大连通域
        if water_eroded.any():
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
                water_eroded.astype(np.uint8), connectivity=8
            )
            if num_labels > 1:
                areas = stats[1:, cv2.CC_STAT_AREA]
                largest = int(np.argmax(areas)) + 1
                water_eroded = labels == largest

        return water_eroded

    def _build_color_similarity_map(
        self,
        image: np.ndarray,
        color_hint: List[int],
    ) -> np.ndarray:
        """构建像素级颜色相似度图（0-1）。"""
        hint = np.asarray(color_hint, dtype=np.float32).reshape(1, 1, 3)
        img = image.astype(np.float32)
        dist = np.linalg.norm(img - hint, axis=2)
        sigma = max(25.0, float(self.color_max_dist) * 0.8)
        sim = np.exp(-0.5 * (dist / sigma) ** 2)
        return sim.astype(np.float32)

    def _apply_color_soft_fusion(
        self,
        image: np.ndarray,
        class_heatmaps: Dict[str, np.ndarray],
        classes_config: Dict[str, dict],
        alpha: float,
    ) -> Dict[str, np.ndarray]:
        """颜色先验软融合：仅抑制明显颜色不符区域，不做硬剔除。"""
        if alpha <= 0:
            return class_heatmaps

        fused = {}
        for cls_name, heatmap in class_heatmaps.items():
            cfg = classes_config.get(cls_name, {})
            if not cfg.get("use_color_check", False):
                fused[cls_name] = heatmap
                continue

            color_hint = cfg.get("color_hint")
            if color_hint is None or len(color_hint) != 3:
                fused[cls_name] = heatmap
                continue

            color_sim = self._build_color_similarity_map(image, color_hint)
            fused_map = (1.0 - alpha) * heatmap + alpha * (heatmap * color_sim)
            fused[cls_name] = fused_map.astype(np.float32)

        return fused

    # ─────────────────────────────────────────────────────────────────────
    # 核心分割逻辑
    # ─────────────────────────────────────────────────────────────────────

    def segment(
        self,
        image: np.ndarray,
        classes_config: Dict[str, dict],
        prompts_config: Optional[Dict[str, dict]] = None,
        class_thresholds: Optional[Dict[str, float]] = None,
        color_fusion_alpha: Optional[float] = None,
        threshold: Optional[float] = None,
        min_area: Optional[float] = None,
    ) -> Dict[str, SegmentResult]:
        """
        水质异常分割

        Args:
            image: BGR 图像 [H, W, 3]
            classes_config: 类别配置
            threshold: 百分位阈值
            min_area: 最小面积占比

        Returns:
            {class_name: SegmentResult}
        """
        threshold = threshold if threshold is not None else self.threshold
        min_area = min_area if min_area is not None else self.min_area
        class_thresholds = class_thresholds or self.class_thresholds

        orig_h, orig_w = image.shape[:2]

        # 获取请求的异常类别 (排除背景类)
        requested_classes = [
            k for k, v in classes_config.items()
            if not v.get("is_background", False)
        ]

        # ━━━ 第 1 步: 图像级分类 ━━━
        class_probs = self.classify_image(image, classes_config, prompts_config)

        # 图像级门控（弱先验）
        img_anomaly_prob = max(class_probs.get(c, 0.0) for c in requested_classes)
        low_image_conf = img_anomaly_prob < self.image_gate

        # ━━━ 第 2 步: Patch级相似度计算 ━━━
        class_heatmaps = self.compute_patch_similarity(image, classes_config, prompts_config)
        fusion_alpha = self.color_fusion_alpha if color_fusion_alpha is None else float(color_fusion_alpha)
        class_heatmaps = self._apply_color_soft_fusion(
            image=image,
            class_heatmaps=class_heatmaps,
            classes_config=classes_config,
            alpha=fusion_alpha,
        )

        if not class_heatmaps:
            return self._maybe_emit_normal_label(
                class_probs, requested_classes, classes_config, orig_h, orig_w
            )

        # ━━━ 第 3 步: 构建异常热图 ━━━
        anomaly_heatmap = np.zeros((orig_h, orig_w), dtype=np.float32)
        best_class_map = np.zeros((orig_h, orig_w), dtype=np.int32)
        class_list = list(requested_classes)
        class_to_idx = {c: i for i, c in enumerate(class_list)}

        for cls_name in requested_classes:
            if cls_name not in class_heatmaps:
                continue
            heatmap = class_heatmaps[cls_name]

            cls_cfg = classes_config.get(cls_name, {})
            cls_thr = threshold
            if class_thresholds and cls_name in class_thresholds:
                cls_thr = float(class_thresholds[cls_name])
            elif "min_prob" in cls_cfg:
                cls_thr = float(cls_cfg.get("min_prob", threshold))
            heatmap = np.where(heatmap >= cls_thr, heatmap, 0.0)

            # 更新热图 (取最大值)
            better_mask = heatmap > anomaly_heatmap
            anomaly_heatmap = np.where(better_mask, heatmap, anomaly_heatmap)
            best_class_map = np.where(better_mask, class_to_idx[cls_name], best_class_map)

        # ━━━ 第 4 步: 识别水体区域 ━━━
        water_mask = self._identify_water_region(class_heatmaps, orig_h, orig_w)

        water_ratio = water_mask.sum() / water_mask.size
        if water_ratio < self.water_min_ratio:
            return self._maybe_emit_normal_label(
                class_probs, requested_classes, classes_config, orig_h, orig_w
            )

        # ━━━ 第 5 步: 阈值分割异常区域 ━━━
        anomaly_mask = anomaly_heatmap > 0
        anomaly_mask = anomaly_mask & water_mask

        if not anomaly_mask.any():
            return self._maybe_emit_normal_label(
                class_probs, requested_classes, classes_config, orig_h, orig_w
            )

        # ━━━ 第 6 步: 后处理 ━━━
        anomaly_mask = self._postprocess_mask(anomaly_mask, anomaly_heatmap)

        area = anomaly_mask.sum() / anomaly_mask.size
        if area < min_area:
            return self._maybe_emit_normal_label(
                class_probs, requested_classes, classes_config, orig_h, orig_w
            )

        # ━━━ 第 7 步: 确定标签 ━━━
        masked_class_map = best_class_map[anomaly_mask]
        if masked_class_map.size > 0:
            valid_mask = masked_class_map >= 0
            if valid_mask.any():
                valid_classes = masked_class_map[valid_mask]
                class_counts = np.bincount(valid_classes, minlength=len(class_list))
                best_idx = np.argmax(class_counts)
                best_anomaly_class = class_list[best_idx] if class_counts[best_idx] > 0 else None
            else:
                best_anomaly_class = None
        else:
            best_anomaly_class = None

        if best_anomaly_class is None:
            # 使用图像级分类结果
            for cls_name in requested_classes:
                if class_probs.get(cls_name, 0) > class_probs.get("normal_water", 0):
                    best_anomaly_class = cls_name
                    break

        if best_anomaly_class is None:
            if low_image_conf:
                return {}
            return self._maybe_emit_normal_label(
                class_probs, requested_classes, classes_config, orig_h, orig_w
            )

        # 计算置信度
        best_score = float(anomaly_heatmap[anomaly_mask].mean()) if anomaly_mask.any() else 0.0

        cfg = classes_config.get(best_anomaly_class, {})
        zh_name = cfg.get("zh", best_anomaly_class)

        return {
            best_anomaly_class: SegmentResult(
                class_name=best_anomaly_class,
                class_name_cn=zh_name,
                mask=anomaly_mask,
                area_ratio=float(area),
                score=float(best_score),
                patch_scores=anomaly_heatmap,
            )
        }

    def _postprocess_mask(
        self,
        mask: np.ndarray,
        conf_map: np.ndarray,
    ) -> np.ndarray:
        """后处理: 形态学操作 + 保留高分连通域"""
        # 腐蚀
        erode_k = _odd_kernel(self.post_erode_kernel, 2)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_k, erode_k))
        mask = cv2.erode(mask.astype(np.uint8), kernel).astype(bool)

        if not mask.any():
            return mask

        # 开运算
        open_k = _odd_kernel(self.post_open_kernel, 2)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_k, open_k))
        mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel).astype(bool)

        if not mask.any():
            return mask

        # 保留高分连通域
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask.astype(np.uint8), connectivity=8
        )

        if num_labels <= 2:
            return mask

        candidates = []
        for lid in range(1, num_labels):
            comp = labels == lid
            area_px = int(stats[lid, cv2.CC_STAT_AREA])
            if area_px < self.post_min_component_pixels:
                continue
            comp_conf = conf_map[comp]
            if comp_conf.size > 0:
                score = float(comp_conf.mean())
                candidates.append((lid, score, area_px))

        if not candidates:
            areas = stats[1:, cv2.CC_STAT_AREA]
            lid = int(np.argmax(areas)) + 1
            return labels == lid

        candidates.sort(key=lambda x: -x[1])
        top_labels = [lid for lid, _, _ in candidates[:self.post_max_components]]
        return np.isin(labels, top_labels)

    def _maybe_emit_normal_label(
        self,
        class_probs: Dict[str, float],
        requested_classes: set,
        classes_config: Dict[str, dict],
        orig_h: int,
        orig_w: int,
    ) -> Dict[str, SegmentResult]:
        """在无异常时输出正常水体标签"""
        if not self.emit_normal_label:
            return {}

        normal_prob = class_probs.get("normal_water", 0.0)
        max_anomaly_prob = max(class_probs.get(c, 0.0) for c in requested_classes)

        if (normal_prob >= self.normal_label_min_prob and
            max_anomaly_prob <= self.normal_label_max_anomaly_prob):
            cfg = classes_config.get("normal_water", {})
            return {
                "normal_water": SegmentResult(
                    class_name="normal_water",
                    class_name_cn=cfg.get("zh", "正常水体"),
                    mask=np.zeros((orig_h, orig_w), dtype=bool),
                    area_ratio=0.0,
                    score=normal_prob,
                )
            }

        return {}

    # ─────────────────────────────────────────────────────────────────────
    # 批量处理
    # ─────────────────────────────────────────────────────────────────────

    def segment_batch(
        self,
        images: List[np.ndarray],
        classes_config: Dict[str, dict],
        threshold: Optional[float] = None,
        min_area: Optional[float] = None,
    ) -> List[Dict[str, SegmentResult]]:
        """批量分割"""
        return [
            self.segment(
                img,
                classes_config,
                threshold=threshold,
                min_area=min_area,
            )
            for img in images
        ]

    # ─────────────────────────────────────────────────────────────────────
    # 可视化
    # ─────────────────────────────────────────────────────────────────────

    def visualize(
        self,
        image: np.ndarray,
        segments: Dict[str, SegmentResult],
        output_path: Optional[str] = None,
        font_path: Optional[str] = None,
    ) -> np.ndarray:
        """可视化分割结果"""
        from PIL import Image, ImageDraw, ImageFont

        vis = image.copy()
        h, w = image.shape[:2]

        if font_path is None:
            font_path = self._find_chinese_font()
        try:
            font = ImageFont.truetype(font_path, 24)
            font_small = ImageFont.truetype(font_path, 18)
        except Exception:
            font = ImageFont.load_default()
            font_small = font

        for name, seg in segments.items():
            color = self.CLASS_COLORS.get(name, (128, 128, 128))

            mask_uint8 = seg.mask.astype(np.uint8) * 255
            overlay = np.zeros_like(vis)
            overlay[mask_uint8 > 0] = color
            vis = cv2.addWeighted(vis, 0.6, overlay, 0.4, 0)

            contours, _ = cv2.findContours(
                mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(vis, contours, -1, color, 2)

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
                draw.text((tx + 1, ty + 1), label, font=font, fill=(0, 0, 0))
                draw.text((tx, ty), label, font=font, fill=(255, 255, 255))
                draw.text((tx + 1, ty + th + 3), score_label, font=font_small, fill=(200, 200, 200))

                vis = cv2.cvtColor(np.array(vis_pil), cv2.COLOR_RGB2BGR)

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


# ─────────────────────────────────────────────────────────────────────────
# 兼容性别名
# ─────────────────────────────────────────────────────────────────────────

CRadioV4Segmentor = WaterQualitySegmentor


# ─────────────────────────────────────────────────────────────────────────
# 测试入口
# ─────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description="水质异常分割器测试")
    parser.add_argument("--config", type=str, default="configs/water_inspection.yaml")
    parser.add_argument("--image", type=str, default=None)
    parser.add_argument("--output", type=str, default="output_segment.jpg")
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--threshold", type=float, default=None)
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent.parent / "configs" / "water_inspection.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    segmentor = WaterQualitySegmentor(config=config, device=args.device)

    if args.image:
        image = cv2.imread(args.image)
    else:
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        image[:, :, 0] = 200
        image[100:300, 200:400, 1] = 180
        print("使用合成测试图像")

    classes_config = config.get("cloud", {}).get("radio", {}).get("classes", {})
    print(f"类别: {list(classes_config.keys())}")

    results = segmentor.segment(image, classes_config, threshold=args.threshold)

    print(f"\n结果: {len(results)} 个区域")
    for name, seg in results.items():
        print(f"  {seg.class_name_cn} ({name}): 面积={seg.area_ratio:.1%}, 置信度={seg.score:.1%}")

    segmentor.visualize(image, results, args.output)
    print(f"\n已保存: {args.output}")


if __name__ == "__main__":
    main()
