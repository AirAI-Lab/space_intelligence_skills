#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RADSeg 风格水质异常分割器 v1.0

借鉴 RADSeg (https://github.com/RADSeg-OVSS/RADSeg) 的核心思想:
  1. 使用 RADIO backbone + SigLIP2 语言对齐 + SAM adaptor
  2. SCRA (Self-Correlating Recursive Attention) 增强特征
  3. SCGA (Self-Correlating Global Aggregation) 全局聚合
  4. 可选的 SAM 边界精化

适配水利巡检场景:
  - 针对水质异常类别优化
  - 集成颜色校验和区域过滤
  - 轻量级实现，无需 mmseg 依赖

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
from pathlib import Path
import logging

from .radio_backbone import RadioBackbone

logger = logging.getLogger(__name__)


@dataclass
class SegmentResult:
    """分割结果"""
    class_name: str
    class_name_cn: str
    mask: np.ndarray
    area_ratio: float
    score: float
    patch_scores: Optional[np.ndarray] = None


class SelfCorrelatingAttention(nn.Module):
    """
    自相关注意力模块 (借鉴 RADSeg 的 SCRA)

    通过计算 token 之间的自相关矩阵来增强特征
    """
    def __init__(self, dim: int, num_heads: int = 16, scaling: float = 10.0):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim ** -0.5
        self.scaling = scaling

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [B, N, C] patch features
        Returns:
            enhanced: [B, N, C] enhanced features
        """
        B, N, C = x.shape

        # 计算自相关矩阵
        x_norm = F.normalize(x, dim=-1)
        sim_matrix = torch.bmm(x_norm, x_norm.transpose(1, 2)) * self.scaling

        # 负值设为 -inf
        sim_matrix = sim_matrix.clamp(min=0)
        sim_matrix = F.softmax(sim_matrix, dim=-1)

        # 加权聚合
        enhanced = torch.bmm(sim_matrix, x)

        return enhanced


class GlobalAggregation(nn.Module):
    """
    全局聚合模块 (借鉴 RADSeg 的 SCGA)

    在全局范围内聚合相似特征
    """
    def __init__(self, scaling: float = 10.0):
        super().__init__()
        self.scaling = scaling

    def forward(self, feat_map: torch.Tensor) -> torch.Tensor:
        """
        Args:
            feat_map: [B, C, H, W] spatial features
        Returns:
            aggregated: [B, C, H, W] aggregated features
        """
        B, C, H, W = feat_map.shape

        # 展平为 tokens
        tokens = feat_map.flatten(2).transpose(1, 2)  # [B, N, C]

        # 计算相似度
        tokens_norm = F.normalize(tokens, dim=-1)
        sim_matrix = torch.bmm(tokens_norm, tokens_norm.transpose(1, 2))

        # 中心化 + 缩放
        sim_matrix = (sim_matrix - sim_matrix.mean(dim=-1, keepdim=True)) * self.scaling
        sim_matrix = sim_matrix.clamp(min=0)
        sim_matrix = F.softmax(sim_matrix, dim=-1)

        # 聚合
        aggregated = torch.bmm(sim_matrix, tokens)

        # 恢复空间形状
        return aggregated.transpose(1, 2).view(B, C, H, W)


class DINOEnhancer(nn.Module):
    """
    DINOv3-7B 特征增强模块 v2.0

    使用 DINO 的视觉特征增强边界和纹理
    DINOv3-7B 输出维度: 4096

    优化策略:
    1. 门控融合机制 (Gated Fusion)
    2. 分层投影 (先降维再融合)
    3. 低初始权重 (避免破坏原有特征)
    """
    def __init__(self, dino_dim: int = 4096, backbone_dim: int = 1280, init_weight: float = 0.1):
        super().__init__()
        # DINO 特征降维 (4096 -> backbone_dim)
        self.dino_proj = nn.Sequential(
            nn.Linear(dino_dim, backbone_dim),
            nn.LayerNorm(backbone_dim),
            nn.GELU(),
        )

        # 门控融合网络
        self.gate = nn.Sequential(
            nn.Linear(backbone_dim * 2, backbone_dim),
            nn.LayerNorm(backbone_dim),
            nn.SiLU(),
            nn.Linear(backbone_dim, backbone_dim),
            nn.Sigmoid(),
        )

        # 可学习的全局权重 (初始化为低值)
        self.global_weight = nn.Parameter(torch.tensor(init_weight))

    def forward(
        self,
        backbone_features: torch.Tensor,
        dino_features: torch.Tensor,
    ) -> torch.Tensor:
        """
        门控融合 backbone 和 DINO 特征

        Args:
            backbone_features: [B, N, D_bb]
            dino_features: [B, N, D_dino]

        Returns:
            enhanced: [B, N, D_bb]
        """
        # 1. DINO 降维
        dino_proj = self.dino_proj(dino_features)  # [B, N, D_bb]

        # 2. 计算门控权重 (基于特征相似度)
        concat = torch.cat([backbone_features, dino_proj], dim=-1)
        gate = self.gate(concat)  # [B, N, D_bb] 范围 [0, 1]

        # 3. 门控融合
        fused = backbone_features + gate * dino_proj

        # 4. 全局权重残差 (确保稳定性)
        global_w = torch.sigmoid(self.global_weight)  # sigmoid(0.1) ≈ 0.525
        output = backbone_features + global_w * (fused - backbone_features)

        return output


class SAMBoundaryRefiner:
    """
    SAM3 边界精化模块

    使用 SAM 的 mask 特征精化分割边界
    """
    def __init__(self, sam_adaptor, device: str = "cuda"):
        self.sam_adaptor = sam_adaptor
        self.device = device

    def refine_mask(
        self,
        coarse_mask: np.ndarray,
        sam_features: torch.Tensor,
        threshold: float = 0.5,
    ) -> np.ndarray:
        """精化粗分割 mask"""
        # TODO: 实现 SAM 边界精化
        return coarse_mask


class RADSegWaterSegmentor:
    """
    RADSeg 风格水质异常分割器

    核心流程:
      1. RADIO 提取 patch 特征
      2. SigLIP2 adaptor 对齐到语言空间
      3. 自相关注意力增强
      4. 与文本嵌入计算相似度
      5. 全局聚合
      6. 后处理 (形态学 + 颜色校验)
    """

    CLASS_COLORS = {
        "black_water": (0, 0, 180),           # 深蓝色 - 黑水
        "turbid_water": (42, 100, 170),       # 茶色 - 浑浊水
        "red_water": (0, 0, 255),             # 红色 - 红水
        "green_water": (0, 200, 0),           # 绿色 - 绿水/藻类
        "milky_foam_water": (200, 200, 200),  # 浅灰色 - 乳白水/泡沫水
        "dam_seepage": (100, 100, 100),       # 深灰色 - 坝体渗水
        "normal_water": (200, 200, 100),      # 淡黄色 - 正常水质
    }

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        radio_code_dir: Optional[str] = None,
        siglip2_dir: Optional[str] = None,
        device: str = "cuda",
        input_size: int = 896,
        config: Optional[Dict] = None,
        use_scra: bool = True,
        use_scga: bool = False,  # 默认禁用，容易过度平滑
        scra_scaling: float = 10.0,
        scga_scaling: float = 10.0,
        use_dino: bool = False,  # DINOv3-7B 增强模块
        use_sam: bool = False,   # SAM3 边界精化模块
        temperature: float = 10.0,  # 温度缩放系数
    ):
        self.device = device
        self.input_size = input_size
        self.config = config or {}
        self.use_scra = use_scra
        self.use_scga = use_scga
        self.use_dino = use_dino
        self.use_sam = use_sam
        self.temperature = temperature

        # 确定 adaptor 列表
        adaptor_names = ["siglip2-g"]
        if use_dino:
            adaptor_names.append("dino_v3_7b")
        if use_sam:
            adaptor_names.append("sam3")

        print(f"加载 Adaptors: {adaptor_names}")

        # 加载 RADIO backbone (根据配置加载多个 adaptor)
        self.backbone = RadioBackbone(
            checkpoint_path=checkpoint_path,
            radio_code_dir=radio_code_dir,
            siglip2_dir=siglip2_dir,
            adaptor_names=adaptor_names,
            device=device,
        )

        # 获取 SigLIP2 adaptor
        self.siglip_adaptor = self.backbone._get_siglip_adaptor()
        if self.siglip_adaptor is None:
            raise RuntimeError("SigLIP2 adaptor 加载失败")

        # 获取 adaptor 的 MLP head 维度
        # siglip2-g: 1536 维
        self.lang_dim = 1536
        self.backbone_dim = self.backbone.embed_dim  # 1280 for ViT-H

        # 自相关模块 (在 backbone 特征上)
        if use_scra:
            self.scra = SelfCorrelatingAttention(
                dim=self.backbone_dim,
                num_heads=16,
                scaling=scra_scaling
            ).to(device)
        else:
            self.scra = None

        # 全局聚合模块
        if use_scga:
            self.scga = GlobalAggregation(scaling=scga_scaling).to(device)
        else:
            self.scga = None

        # DINO 增强器 (需要 dino_v3_7b adaptor)
        self.dino_enhancer = None
        if use_dino and "dino_v3_7b" in adaptor_names:
            self.dino_enhancer = DINOEnhancer(
                dino_dim=4096,  # DINOv3-7B 特征维度
                backbone_dim=self.backbone_dim,
            ).to(device)

        # SAM 精化器 (需要 sam3 adaptor)
        self.sam_refiner = None
        if use_sam and "sam3" in adaptor_names:
            # SAM3 特征维度: 1024
            self.sam_refiner = SAMBoundaryRefiner(
                sam_adaptor=None,  # 暂不使用
                device=device,
            )

        # 加载推理配置
        self._load_config()

    def _load_config(self):
        """加载推理配置"""
        radio_cfg = self.config.get("cloud", {}).get("radio", {})
        infer_cfg = radio_cfg.get("inference", {})

        self.threshold = infer_cfg.get("threshold", 0.30)
        self.min_area = infer_cfg.get("min_area", 0.005)
        self.image_gate = infer_cfg.get("image_gate", 0.08)

        # 聚类/分割参数
        cluster_cfg = infer_cfg.get("cluster", {})
        self.min_prob = cluster_cfg.get("min_prob", 0.35)
        self.vs_normal_margin = cluster_cfg.get("vs_normal_margin", 0.01)
        self.vs_background_margin = cluster_cfg.get("vs_background_margin", 0.02)

        # 颜色校验
        color_cfg = infer_cfg.get("color", {})
        self.color_max_dist = color_cfg.get("max_dist", 100)
        self.color_strict_prob = color_cfg.get("strict_prob", 0.65)

    def encode_text(self, texts: List[str]) -> torch.Tensor:
        """
        使用 SigLIP2 编码文本

        Args:
            texts: 文本列表

        Returns:
            text_features: [N, D] 归一化文本特征
        """
        text_tokens = self.siglip_adaptor.tokenizer(texts).to(self.device)
        text_features = self.siglip_adaptor.encode_text(text_tokens, normalize=True)
        return text_features

    def align_to_language_space(self, features: torch.Tensor) -> torch.Tensor:
        """
        将 backbone 特征对齐到语言空间

        Args:
            features: [B, N, D_backbone] backbone patch features

        Returns:
            lang_features: [B, N, D_lang] 语言空间特征
        """
        # 使用 SigLIP2 adaptor 的 head_mlp 投影到语言空间
        # 这是 RADSeg 的关键步骤: backbone 特征 → 语言对齐空间
        with torch.autocast("cuda", dtype=torch.float16):
            lang_features = self.siglip_adaptor.head_mlp(features)
        return lang_features

    @torch.no_grad()
    def compute_patch_similarity(
        self,
        image: np.ndarray,
        classes_config: Dict[str, dict],
        prompts_config: Optional[Dict] = None,
    ) -> Dict[str, np.ndarray]:
        """
        计算每个 patch 与各类别的相似度 (Contrastive Prompt Matching)

        核心改进：使用 positive 和 negative prompts 进行对比学习
        score = positive_score - negative_score

        Args:
            image: BGR 图像 [H, W, 3]
            classes_config: 类别配置
            prompts_config: 提示词配置 (含 positive 和 negative)

        Returns:
            class_heatmaps: {class_name: heatmap [H, W]}
        """
        orig_h, orig_w = image.shape[:2]

        # 准备图像张量
        image_rgb = image[:, :, ::-1].copy()
        image_resized = cv2.resize(image_rgb, (self.input_size, self.input_size))
        image_tensor = torch.from_numpy(image_resized).permute(2, 0, 1).unsqueeze(0)
        image_tensor = image_tensor.float().div(255.0).to(self.device)

        # 构建文本列表 (positive + negative)
        pos_texts = []
        neg_texts = []
        pos_class_names = []
        neg_class_names = []

        for cls_name, cfg in classes_config.items():
            # Positive prompts
            if prompts_config and cls_name in prompts_config:
                pos_prompts = prompts_config[cls_name].get("positive", cfg.get("prompts", []))
                neg_prompts = prompts_config[cls_name].get("negative", [])
            else:
                pos_prompts = cfg.get("prompts", [cls_name.replace("_", " ")])
                neg_prompts = []

            pos_texts.extend(pos_prompts)
            pos_class_names.extend([cls_name] * len(pos_prompts))

            # Negative prompts (用于对比学习)
            neg_texts.extend(neg_prompts)
            neg_class_names.extend([cls_name] * len(neg_prompts))

        # 编码所有文本
        all_texts = pos_texts + neg_texts
        all_features = self.encode_text(all_texts)  # [N_text, D]

        # 分离 positive 和 negative 特征
        n_pos = len(pos_texts)
        pos_features = all_features[:n_pos]
        neg_features = all_features[n_pos:] if n_pos < len(all_texts) else None

        # 提取 backbone 特征
        result = self.backbone.extract_features(image_tensor)
        features = result["features"]  # [1, N_patches, D_backbone]
        H_patch, W_patch = result["grid_size"]

        B, N, D = features.shape

        # SCRA 增强
        if self.scra is not None:
            enhanced = self.scra(features)
            features = enhanced

        # DINO 增强
        if self.dino_enhancer is not None and "adaptor_outputs" in result:
            dino_out = result["adaptor_outputs"].get("dino_v3_7b")
            if dino_out is not None and hasattr(dino_out, 'features'):
                dino_features = dino_out.features
                if dino_features.shape[1] == N:
                    features = self.dino_enhancer(features, dino_features)

        # 对齐到语言空间
        lang_features = self.align_to_language_space(features)  # [1, N, D_lang]
        lang_features = lang_features.view(B * N, -1)  # [N, D_lang]
        lang_features_norm = F.normalize(lang_features.float(), dim=-1)

        # 计算相似度
        pos_similarity = lang_features_norm @ pos_features.T  # [N, n_pos]
        neg_similarity = lang_features_norm @ neg_features.T if neg_features is not None else None  # [N, n_neg]

        # 聚合 positive 得分 (取最大)
        pos_scores = torch.zeros(N, len(classes_config), device=self.device)
        for i, cls_name in enumerate(pos_class_names):
            cls_idx = list(classes_config.keys()).index(cls_name)
            pos_scores[:, cls_idx] = torch.maximum(pos_scores[:, cls_idx], pos_similarity[:, i])

        # 聚合 negative 得分 (取最大， 因为最相似的 negative 是最难区分的)
        neg_scores = torch.zeros(N, len(classes_config), device=self.device)
        if neg_similarity is not None:
            for i, cls_name in enumerate(neg_class_names):
                cls_idx = list(classes_config.keys()).index(cls_name)
                neg_scores[:, cls_idx] = torch.maximum(neg_scores[:, cls_idx], neg_similarity[:, i])

        # Contrastive score: positive - negative
        # 这让每个类别更具排他性
        contrastive_scores = pos_scores - neg_scores * 0.5  # negative 权重 0.5

        # 使用 softmax 进行相对排名 (更区分性)
        # 对每个 patch，计算所有类别的 softmax 概率
        contrastive_scores_scaled = contrastive_scores * 2.0  # 增强区分度
        class_probs = torch.softmax(contrastive_scores_scaled, dim=-1)

        # 构建热图
        class_heatmaps = {}
        for cls_idx, cls_name in enumerate(classes_config.keys()):
            heatmap = class_probs[:, cls_idx].view(1, H_patch, W_patch)

            # 上采样到原始尺寸
            heatmap_up = F.interpolate(
                heatmap.unsqueeze(0), size=(orig_h, orig_w),
                mode="bilinear", align_corners=False
            ).squeeze().cpu().numpy()

            class_heatmaps[cls_name] = heatmap_up

        return class_heatmaps

    def segment(
        self,
        image: np.ndarray,
        classes_config: Dict[str, dict],
        threshold: Optional[float] = None,
        min_area: Optional[float] = None,
        prompts_config: Optional[Dict] = None,
    ) -> Dict[str, SegmentResult]:
        """
        执行水质异常分割

        Args:
            image: BGR 图像 [H, W, 3]
            classes_config: 类别配置
            threshold: 置信度阈值
            min_area: 最小面积比例

        Returns:
            {class_name: SegmentResult}
        """
        threshold = threshold if threshold is not None else self.threshold
        min_area = min_area if min_area is not None else self.min_area

        # 获取异常类别 (排除背景)
        anomaly_classes = {
            k for k, v in classes_config.items()
            if not v.get("is_background", False)
        }

        # 获取正常类别
        normal_classes = {
            k for k, v in classes_config.items()
            if v.get("is_background", False) and "zh" in v
        }

        # 计算热图 (使用 contrastive prompt matching)
        heatmaps = self.compute_patch_similarity(image, classes_config, prompts_config)

        # 获取 normal_water 基准得分
        normal_baseline = 0.0
        for normal_cls in normal_classes:
            if normal_cls in heatmaps:
                normal_baseline = float(heatmaps[normal_cls].max())
                break

        # 找最佳异常类 (使用 margin 策略)
        # margin = anomaly_score - normal_baseline
        # 只有当异常得分明显高于正常基准时才预测为异常
        best_class = None
        best_score = 0.0
        best_mask = None
        best_margin = -float('inf')

        for cls_name in anomaly_classes:
            if cls_name not in heatmaps:
                continue

            heatmap = heatmaps[cls_name]
            cfg = classes_config.get(cls_name, {})
            cls_threshold = float(cfg.get("min_prob", threshold))

            # 阈值化
            mask = heatmap > cls_threshold

            if not mask.any():
                continue

            # 面积检查
            area = mask.sum() / mask.size
            if area < min_area:
                continue

            # 颜色校验 (仅用于高置信样本的二次验证)
            color_hint = cfg.get("color_hint")
            if color_hint and isinstance(color_hint, list) and len(color_hint) == 3:
                color_dist = self._compute_color_distance(image, mask, color_hint)
                max_score = float(heatmap.max())
                # 只有在高置信时才严格检查颜色
                if max_score > self.color_strict_prob and color_dist > self.color_max_dist * 1.5:
                    continue

            # 计算得分和 margin
            score = float(heatmap[mask].mean())
            margin = score - normal_baseline

            # 使用 margin 作为排序依据
            if margin > best_margin:
                best_margin = margin
                best_score = score
                best_class = cls_name
                best_mask = mask

        # 如果最好的异常 margin 仍然为负 (异常得分低于正常基准)， 不输出
        if best_margin < -0.05:  # 允许 0.05 的容差
            return {}

        if best_class is None or best_mask is None:
            return {}

        # 后处理
        best_mask = self._postprocess_mask(best_mask)
        area = best_mask.sum() / best_mask.size

        if area < min_area:
            return {}

        cfg = classes_config.get(best_class, {})
        zh_name = cfg.get("zh", best_class)

        return {
            best_class: SegmentResult(
                class_name=best_class,
                class_name_cn=zh_name,
                mask=best_mask,
                area_ratio=float(area),
                score=float(best_score),
            )
        }

    def _compute_color_distance(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        color_hint: List[int],
    ) -> float:
        """计算颜色距离"""
        ys, xs = np.where(mask)
        if len(ys) == 0:
            return 1e9
        pixels = image[ys, xs].astype(np.float32)
        mean_bgr = pixels.mean(axis=0)
        hint = np.asarray(color_hint, dtype=np.float32)
        return float(np.linalg.norm(mean_bgr - hint))

    def _postprocess_mask(self, mask: np.ndarray) -> np.ndarray:
        """后处理: 形态学操作"""
        # 腐蚀
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.erode(mask.astype(np.uint8), kernel).astype(bool)

        if not mask.any():
            return mask

        # 开运算
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel).astype(bool)

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
        """可视化分割结果"""
        from PIL import Image, ImageDraw, ImageFont

        vis = image.copy()
        h, w = image.shape[:2]

        for name, seg in segments.items():
            color = self.CLASS_COLORS.get(name, (128, 128, 128))

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

        if output_path:
            cv2.imwrite(output_path, vis)

        return vis


# 兼容性别名
WaterQualitySegmentorV2 = RADSegWaterSegmentor
