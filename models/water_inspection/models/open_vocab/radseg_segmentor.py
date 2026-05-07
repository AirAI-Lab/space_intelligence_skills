#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RADSeg 水质异常分割器 v1.0

借鉴 RADSeg (https://github.com/RADSeg-OVSS/RADSeg) 的核心思想:
  1. 使用 RADIO backbone + SigLIP2 语言对齐 + SAM adaptor
  2. SCRA (Self-Correlating Recursive Attention) 增强特征
  3. SCGA (Self-Correlating Global Aggregation) 全局聚合
  4. 可选的 SAM 边界精细化

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

from .core.backbone import RadioBackbone

logger = logging.getLogger(__name__)


@dataclass
class SegmentResult:
    """分割结果数据类"""
    class_name: str           # 类别英文名
    class_name_cn: str        # 类别中文名
    mask: np.ndarray          # 分割掩码 [H, W]
    area_ratio: float         # 面积占比
    score: float              # 置信度分数
    patch_scores: Optional[np.ndarray] = None  # patch级别分数


class SelfCorrelatingAttention(nn.Module):
    """
    自相关注意力模块 (借鉴 RADSeg 的 SCRA)

    通过计算 token 之间的自相关矩阵来增强特征表示。
    这有助于捕获图像中相似区域的全局上下文信息。
    """

    def __init__(self, dim: int, num_heads: int = 16, scaling: float = 10.0):
        """
        初始化自相关注意力模块

        Args:
            dim: 特征维度
            num_heads: 注意力头数
            scaling: 相似度缩放因子
        """
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim ** -0.5
        self.scaling = scaling

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播

        Args:
            x: [B, N, C] patch 特征

        Returns:
            enhanced: [B, N, C] 增强后的特征
        """
        B, N, C = x.shape

        # 计算自相关矩阵 (归一化后的余弦相似度)
        x_norm = F.normalize(x, dim=-1)
        sim_matrix = torch.bmm(x_norm, x_norm.transpose(1, 2)) * self.scaling

        # 负值设为 0 (只保留正相关)
        sim_matrix = sim_matrix.clamp(min=0)
        sim_matrix = F.softmax(sim_matrix, dim=-1)

        # 加权聚合
        enhanced = torch.bmm(sim_matrix, x)

        return enhanced


class GlobalAggregation(nn.Module):
    """
    全局聚合模块 (借鉴 RADSeg 的 SCGA)

    在全局范围内聚合相似特征，增强特征的判别能力。
    """

    def __init__(self, scaling: float = 10.0):
        """
        初始化全局聚合模块

        Args:
            scaling: 相似度缩放因子
        """
        super().__init__()
        self.scaling = scaling

    def forward(self, feat_map: torch.Tensor) -> torch.Tensor:
        """
        前向传播

        Args:
            feat_map: [B, C, H, W] 空间特征图

        Returns:
            aggregated: [B, C, H, W] 聚合后的特征图
        """
        B, C, H, W = feat_map.shape

        # 展平为 tokens
        tokens = feat_map.flatten(2).transpose(1, 2)  # [B, N, C]

        # 计算自相关矩阵
        tokens_norm = F.normalize(tokens, dim=-1)
        sim_matrix = torch.bmm(tokens_norm, tokens_norm.transpose(1, 2))

        # 中心化并缩放
        sim_matrix = (sim_matrix - sim_matrix.mean(dim=-1, keepdim=True)) * self.scaling
        sim_matrix = sim_matrix.clamp(min=0)
        sim_matrix = F.softmax(sim_matrix, dim=-1)

        # 加权聚合
        aggregated = torch.bmm(sim_matrix, tokens)

        return aggregated.transpose(1, 2).view(B, C, H, W)


class DINOEnhancer(nn.Module):
    """
    DINO 特征增强器

    使用 DINOv3 的视觉特征来增强 RADIO backbone 的特征表示。
    通过门控机制融合两种特征，提升语义理解能力。
    """

    def __init__(self, dino_dim: int = 4096, backbone_dim: int = 1280, init_weight: float = 0.1):
        """
        初始化 DINO 增强器

        Args:
            dino_dim: DINO 特征维度 (DINOv3-7B 为 4096)
            backbone_dim: Backbone 特征维度 (ViT-H 为 1280)
            init_weight: 全局融合权重初始值
        """
        super().__init__()

        # DINO 特征投影层
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

        # 可学习的全局融合权重
        self.global_weight = nn.Parameter(torch.tensor(init_weight))

    def forward(
        self,
        backbone_features: torch.Tensor,
        dino_features: torch.Tensor,
    ) -> torch.Tensor:
        """
        前向传播

        Args:
            backbone_features: [B, N, D_bb] backbone patch 特征
            dino_features: [B, N, D_dino] DINO patch 特征

        Returns:
            enhanced: [B, N, D_bb] 增强后的特征
        """
        # 投影 DINO 特征到 backbone 维度
        dino_proj = self.dino_proj(dino_features)  # [B, N, D_bb]

        # 计算门控权重
        concat = torch.cat([backbone_features, dino_proj], dim=-1)
        gate = self.gate(concat)

        # 门控融合
        fused = backbone_features + gate * dino_proj

        # 全局残差连接
        global_w = torch.sigmoid(self.global_weight)
        output = backbone_features + global_w * (fused - backbone_features)

        return output


class SAMBoundaryRefiner:
    """
    SAM 边界精细化模块

    支持三种模式:
      1. radio_sam3: 使用 C-RADIOv4 内置的 SAM3 特征
      2. segment_anything: 使用 segment_anything 库
      3. morphological: 形态学精细化 (默认)
    """

    def __init__(
        self,
        sam_adaptor=None,
        device: str = "cuda",
        mode: str = "morphological",
        config: Optional[Dict] = None,
    ):
        """
        初始化 SAM 边界精细化模块

        Args:
            sam_adaptor: SAM adaptor 对象 (仅 radio_sam3 模式需要)
            device: 计算设备
            mode: 精细化模式 ("morphological", "radio_sam3", "segment_anything")
            config: 配置字典
        """
        self.sam_adaptor = sam_adaptor
        self.device = device
        self.mode = mode
        self.config = config or {}

        # 延迟加载精细化器
        self._refiner = None

    def _get_refiner(self):
        """延迟加载精细化器"""
        if self._refiner is not None:
            return self._refiner

        from .sam_refinement import (
            MorphologicalRefiner,
            RadioSAM3Refiner,
            SegmentAnythingRefiner,
            RefinementConfig,
        )

        cfg = RefinementConfig(
            enabled=True,
            mode=self.mode,
            checkpoint_path=self.config.get("checkpoint_path", ""),
            coarse_thresh=self.config.get("coarse_thresh", 0.1),
            minimal_area=self.config.get("minimal_area", 225),
            sam_iou_thresh=self.config.get("sam_iou_thresh", 0.9),
        )

        if self.mode == "radio_sam3":
            self._refiner = RadioSAM3Refiner(cfg, self.sam_adaptor, self.device)
        elif self.mode == "segment_anything":
            self._refiner = SegmentAnythingRefiner(cfg, self.device)
        else:
            self._refiner = MorphologicalRefiner(cfg)

        return self._refiner

    def refine_mask(
        self,
        coarse_mask: np.ndarray,
        sam_features: Optional[torch.Tensor] = None,
        original_image: Optional[np.ndarray] = None,
        threshold: float = 0.5,
    ) -> np.ndarray:
        """
        精细化粗分割掩码

        Args:
            coarse_mask: 粗分割掩码 [H, W]
            sam_features: SAM 特征 (仅 radio_sam3 模式需要)
            original_image: 原始图像 (仅 segment_anything 模式需要)
            threshold: 分割阈值 (未使用)

        Returns:
            refined_mask: 精细化后的掩码
        """
        if not coarse_mask.any():
            return coarse_mask

        try:
            refiner = self._get_refiner()

            if self.mode == "radio_sam3" and sam_features is not None:
                return refiner.refine_mask(coarse_mask, sam_features)
            elif self.mode == "segment_anything" and original_image is not None:
                return refiner.refine_mask(coarse_mask, original_image)
            else:
                return refiner.refine_mask(coarse_mask)
        except Exception as e:
            logger.warning(f"SAM refinement failed: {e}, returning original mask")
            return coarse_mask


class RADSegWaterSegmentor:
    """
    RADSeg 水质异常分割器

    基于 RADIO backbone 和 SigLIP2 语言模型实现的零样本分割器。
    支持多种水质异常类别的检测，包括:
    - 黑臭水 (black_water)
    - 浑浊水 (turbid_water)
    - 绿藻水 (green_water)
    - 乳白泡沫水 (milky_foam_water)
    - 坝体渗水 (dam_seepage)
    - 正常水 (normal_water)
    """

    # 类别颜色映射 (用于可视化)
    CLASS_COLORS = {
        "black_water": (0, 0, 180),           # 深红色
        "turbid_water": (42, 100, 170),       # 棕黄色
        "green_water": (0, 200, 0),           # 绿色
        "milky_foam_water": (200, 200, 200),  # 浅灰色
        "dam_seepage": (100, 100, 100),       # 深灰色
        "normal_water": (200, 200, 100),      # 浅黄色
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
        use_scga: bool = False,
        scga_scaling: float = 10.0,
        use_dino: bool = False,
        use_sam: bool = False,
        temperature: float = 50.0,
    ):
        """
        初始化分割器

        Args:
            checkpoint_path: RADIO checkpoint 路径
            radio_code_dir: RADIO 代码目录
            siglip2_dir: SigLIP2 模型目录
            device: 计算设备
            input_size: 输入图像尺寸
            config: 配置字典
            use_scra: 是否使用自相关注意力增强
            use_scga: 是否使用全局聚合模块
            scga_scaling: SCGA 缩放因子
            use_dino: 是否使用 DINO 特征增强
            use_sam: 是否使用 SAM 边界精细化
            temperature: 温度参数
        """
        self.device = device
        self.input_size = input_size
        self.config = config or {}
        self.use_scra = use_scra
        self.use_scga = use_scga
        self.use_dino = use_dino
        self.use_sam = use_sam
        self.temperature = temperature

        # 构建 adaptor 列表
        adaptor_names = ["siglip2-g"]
        if use_dino:
            adaptor_names.append("dino_v3_7b")
        if use_sam:
            adaptor_names.append("sam3")

        print(f"  Adaptors: {adaptor_names}")

        # 初始化 backbone
        self.backbone = RadioBackbone(
            checkpoint_path=checkpoint_path,
            radio_code_dir=radio_code_dir,
            siglip2_dir=siglip2_dir,
            adaptor_names=adaptor_names,
            device=device,
        )

        # 获取 SigLIP2 adaptor (必须存在)
        self.siglip_adaptor = self.backbone._get_siglip_adaptor()
        if self.siglip_adaptor is None:
            raise RuntimeError("SigLIP2 adaptor 未找到，但它是必需的")

        # 记录 backbone 维度
        self.backbone_dim = self.backbone.embed_dim  # 1280 for ViT-H

        # 初始化自相关注意力模块
        if use_scra:
            self.scra = SelfCorrelatingAttention(
                dim=self.backbone_dim,
                num_heads=16,
                scaling=scga_scaling
            ).to(device)
        else:
            self.scra = None

        # 初始化全局聚合模块
        if use_scga:
            self.scga = GlobalAggregation(scaling=scga_scaling).to(device)
        else:
            self.scga = None

        # 初始化 DINO 增强器
        self.dino_enhancer = None
        if use_dino and "dino_v3_7b" in adaptor_names:
            self.dino_enhancer = DINOEnhancer(
                dino_dim=4096,  # DINOv3-7B 特征维度
                backbone_dim=self.backbone_dim,
            ).to(device)

        # 初始化 SAM 边界精细化模块
        self.sam_refiner = None
        self.sam_refinement_config = {}
        if use_sam and "sam3" in adaptor_names:
            # 从配置加载 SAM 参数
            radio_cfg = self.config.get("cloud", {}).get("radio", {})
            sam_cfg = radio_cfg.get("sam_refinement", {})
            self.sam_refinement_config = sam_cfg

            # 获取 SAM adaptor (如果可用)
            sam_adaptor = self.backbone._get_sam_adaptor() if hasattr(self.backbone, '_get_sam_adaptor') else None

            self.sam_refiner = SAMBoundaryRefiner(
                sam_adaptor=sam_adaptor,
                device=device,
                mode=sam_cfg.get("mode", "morphological"),
                config=sam_cfg,
            )
            logger.info(f"SAM refinement enabled: mode={sam_cfg.get('mode', 'morphological')}")

        # 加载配置参数
        self._load_config()

    def _load_config(self):
        """从配置文件加载参数"""
        radio_cfg = self.config.get("cloud", {}).get("radio", {})
        infer_cfg = radio_cfg.get("inference", {})

        # 基本分割参数
        self.threshold = infer_cfg.get("threshold", 0.30)
        self.min_area = infer_cfg.get("min_area", 0.005)
        self.image_gate = infer_cfg.get("image_gate", 0.08)

        # 聚类参数
        cluster_cfg = infer_cfg.get("cluster", {})
        self.min_prob = cluster_cfg.get("min_prob", 0.35)
        self.vs_normal_margin = cluster_cfg.get("vs_normal_margin", 0.01)
        self.vs_background_margin = cluster_cfg.get("vs_background_margin", 0.02)

        # 颜色校验参数
        color_cfg = infer_cfg.get("color", {})
        self.color_max_dist = color_cfg.get("max_dist", 100)
        self.color_strict_prob = color_cfg.get("strict_prob", 0.65)

    def encode_text(self, texts: List[str]) -> torch.Tensor:
        """
        使用 SigLIP2 编码文本

        Args:
            texts: 文本列表

        Returns:
            text_features: [N, D] 文本特征
        """
        text_tokens = self.siglip_adaptor.tokenizer(texts).to(self.device)
        text_features = self.siglip_adaptor.encode_text(text_tokens, normalize=True)
        return text_features

    def align_to_language_space(self, features: torch.Tensor) -> torch.Tensor:
        """
        将 backbone 特征对齐到语言空间

        使用 SigLIP2 adaptor 的 head_mlp 将 RADIO backbone 特征
        投影到与文本特征相同的语言空间。

        Args:
            features: [B, N, D_backbone] backbone patch 特征

        Returns:
            lang_features: [B, N, D_lang] 语言对齐的特征
        """
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
        计算每个 patch 与类别提示的相似度 (对比式提示匹配)

        分数计算方式: score = positive_score - negative_score
        这种对比式方法可以提高模型对不同类别的区分能力。

        Args:
            image: BGR 图像 [H, W, 3]
            classes_config: 类别配置字典
            prompts_config: 提示词配置 (包含正样本和负样本提示)

        Returns:
            class_heatmaps: {class_name: heatmap [H, W]}
        """
        orig_h, orig_w = image.shape[:2]

        # 预处理图像
        image_rgb = image[:, :, ::-1].copy()
        image_resized = cv2.resize(image_rgb, (self.input_size, self.input_size))
        image_tensor = torch.from_numpy(image_resized).permute(2, 0, 1).unsqueeze(0)
        image_tensor = image_tensor.float().div(255.0).to(self.device)

        # 准备文本提示 (正样本 + 负样本)
        pos_texts = []
        neg_texts = []
        pos_class_names = []
        neg_class_names = []

        for cls_name, cfg in classes_config.items():
            # 正样本提示
            if prompts_config and cls_name in prompts_config:
                pos_prompts = prompts_config[cls_name].get("positive", cfg.get("prompts", []))
                neg_prompts = prompts_config[cls_name].get("negative", [])
            else:
                pos_prompts = cfg.get("prompts", [cls_name.replace("_", " ")])
                neg_prompts = []

            pos_texts.extend(pos_prompts)
            pos_class_names.extend([cls_name] * len(pos_prompts))

            # 负样本提示 (用于对比学习)
            neg_texts.extend(neg_prompts)
            neg_class_names.extend([cls_name] * len(neg_prompts))

        # 编码所有文本
        all_texts = pos_texts + neg_texts
        all_features = self.encode_text(all_texts)  # [N_text, D]

        # 分离正负样本特征
        n_pos = len(pos_texts)
        pos_features = all_features[:n_pos]
        neg_features = all_features[n_pos:] if n_pos < len(all_texts) else None

        # 提取 backbone 特征
        result = self.backbone.extract_features(image_tensor)
        features = result["features"]  # [1, N_patches, D_backbone]
        H_patch, W_patch = result["grid_size"]

        B, N, D = features.shape

        # SCRA 特征增强
        if self.scra is not None:
            enhanced = self.scra(features)
            features = enhanced

        # DINO 特征增强
        if self.dino_enhancer is not None and "adaptor_outputs" in result:
            dino_out = result["adaptor_outputs"].get("dino_v3_7b")
            if dino_out is not None and hasattr(dino_out, 'features'):
                dino_features = dino_out.features
                if dino_features.shape[1] == N:
                    features = self.dino_enhancer(features, dino_features)

        # 将特征对齐到语言空间
        lang_features = self.align_to_language_space(features)  # [1, N, D_lang]
        lang_features = lang_features.view(B * N, -1)  # [N, D_lang]
        lang_features_norm = F.normalize(lang_features.float(), dim=-1)

        # 计算相似度分数
        pos_similarity = lang_features_norm @ pos_features.T  # [N, n_pos]
        neg_similarity = lang_features_norm @ neg_features.T if neg_features is not None else None  # [N, n_neg]

        # 聚合正样本分数 (取每个类别的最大值)
        pos_scores = torch.zeros(N, len(classes_config), device=self.device)
        for i, cls_name in enumerate(pos_class_names):
            cls_idx = list(classes_config.keys()).index(cls_name)
            pos_scores[:, cls_idx] = torch.maximum(pos_scores[:, cls_idx], pos_similarity[:, i])

        # 聚合负样本分数 (取每个类别的最大值，用于对比学习)
        neg_scores = torch.zeros(N, len(classes_config), device=self.device)
        if neg_similarity is not None:
            for i, cls_name in enumerate(neg_class_names):
                cls_idx = list(classes_config.keys()).index(cls_name)
                neg_scores[:, cls_idx] = torch.maximum(neg_scores[:, cls_idx], neg_similarity[:, i])

        # 对比分数: positive - negative
        # 让每个类别更具排他性
        contrastive_scores = pos_scores - neg_scores * 0.5  # negative 权重 0.5

        # 使用 softmax 进行相对排名
        # 温度参数: 值越大，概率分布越尖锐，区分度越高
        # 对于 2 类问题，需要较高的温度来创建足够区分
        temperature = self.temperature if hasattr(self, 'temperature') else 50.0
        contrastive_scores_scaled = contrastive_scores * temperature
        class_probs = torch.softmax(contrastive_scores_scaled, dim=-1)

        # 上采样到原始图像尺寸
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
        multi_class: bool = False,
    ) -> Dict[str, SegmentResult]:
        """
        执行分割检测

        Args:
            image: BGR 图像 [H, W, 3]
            classes_config: 类别配置字典
            threshold: 置信度阈值
            min_area: 最小面积比例
            prompts_config: 提示词配置
            multi_class: 多类模式 — 返回所有超过阈值的类别 (用于变换检测等)

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

        # 计算 patch 相似度 (使用对比式提示匹配)
        heatmaps = self.compute_patch_similarity(image, classes_config, prompts_config)

        # 获取正常基准得分
        normal_baseline = 0.0
        for normal_cls in normal_classes:
            if normal_cls in heatmaps:
                normal_baseline = float(heatmaps[normal_cls].max())
                break

        if multi_class:
            # 多类模式: 返回所有超过阈值的类别
            return self._segment_multi_class(
                image, heatmaps, anomaly_classes, classes_config,
                threshold, min_area, normal_baseline,
            )

        # 单类模式 (原始逻辑, 水质检测用): 只返回 margin 最大的类别
        return self._segment_single_class(
            image, heatmaps, anomaly_classes, classes_config,
            threshold, min_area, normal_baseline,
        )

    def _segment_multi_class(
        self,
        image: np.ndarray,
        heatmaps: Dict[str, np.ndarray],
        anomaly_classes: set,
        classes_config: Dict[str, dict],
        threshold: float,
        min_area: float,
        normal_baseline: float,
    ) -> Dict[str, SegmentResult]:
        """多类模式: 每个类别独立判断，返回所有超过阈值的类别"""
        results = {}

        for cls_name in anomaly_classes:
            if cls_name not in heatmaps:
                continue

            heatmap = heatmaps[cls_name]
            cfg = classes_config.get(cls_name, {})
            cls_threshold = float(cfg.get("min_prob", threshold))

            # 阈值化生成掩码
            mask = heatmap > cls_threshold

            if not mask.any():
                continue

            # 面积检查
            area = mask.sum() / mask.size
            if area < min_area:
                continue

            # 颜色校验
            color_hint = cfg.get("color_hint")
            if color_hint and isinstance(color_hint, list) and len(color_hint) == 3:
                color_dist = self._compute_color_distance(image, mask, color_hint)
                max_score = float(heatmap.max())
                if max_score > self.color_strict_prob and color_dist > self.color_max_dist * 1.5:
                    continue

            # margin 检查 (宽松: 允许 margin 接近 0)
            score = float(heatmap[mask].mean())
            margin = score - normal_baseline
            if margin < -0.1:
                continue

            # 后处理掩码
            mask = self._postprocess_mask(mask)
            area = mask.sum() / mask.size
            if area < min_area:
                continue

            zh_name = cfg.get("zh", cls_name)
            results[cls_name] = SegmentResult(
                class_name=cls_name,
                class_name_cn=zh_name,
                mask=mask,
                area_ratio=float(area),
                score=float(score),
            )

        return results

    def _segment_single_class(
        self,
        image: np.ndarray,
        heatmaps: Dict[str, np.ndarray],
        anomaly_classes: set,
        classes_config: Dict[str, dict],
        threshold: float,
        min_area: float,
        normal_baseline: float,
    ) -> Dict[str, SegmentResult]:
        """单类模式 (原始逻辑, 水质检测): 只返回 margin 最大的一个类别"""
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

            mask = heatmap > cls_threshold
            if not mask.any():
                continue

            area = mask.sum() / mask.size
            if area < min_area:
                continue

            color_hint = cfg.get("color_hint")
            if color_hint and isinstance(color_hint, list) and len(color_hint) == 3:
                color_dist = self._compute_color_distance(image, mask, color_hint)
                max_score = float(heatmap.max())
                if max_score > self.color_strict_prob and color_dist > self.color_max_dist * 1.5:
                    continue

            score = float(heatmap[mask].mean())
            margin = score - normal_baseline

            if margin > best_margin:
                best_margin = margin
                best_score = score
                best_class = cls_name
                best_mask = mask

        if best_margin < -0.05:
            return {}

        if best_class is None or best_mask is None:
            return {}

        best_mask = self._postprocess_mask(best_mask)

        # SAM 边界精细化 (如果启用)
        if self.sam_refiner is not None:
            try:
                sam_features = None
                if hasattr(self, '_last_sam_features'):
                    sam_features = self._last_sam_features
                best_mask = self.sam_refiner.refine_mask(
                    coarse_mask=best_mask,
                    sam_features=sam_features,
                    original_image=image,
                )
            except Exception as e:
                logger.warning(f"SAM refinement failed: {e}")

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
        """
        计算掩码区域的平均颜色与提示颜色的距离

        Args:
            image: BGR 图像
            mask: 分割掩码
            color_hint: 颜色提示 [B, G, R]

        Returns:
            颜色距离 (欧氏距离)
        """
        ys, xs = np.where(mask)
        if len(ys) == 0:
            return 1e9
        pixels = image[ys, xs].astype(np.float32)
        mean_bgr = pixels.mean(axis=0)
        hint = np.asarray(color_hint, dtype=np.float32)
        return float(np.linalg.norm(mean_bgr - hint))

    def _postprocess_mask(self, mask: np.ndarray) -> np.ndarray:
        """
        后处理掩码: 形态学操作

        包括腐蚀、开运算和保留最大连通域。

        Args:
            mask: 原始掩码

        Returns:
            处理后的掩码
        """
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
        """
        可视化分割结果

        Args:
            image: 原始图像
            segments: 分割结果字典
            output_path: 输出路径 (可选)

        Returns:
            可视化图像
        """
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

            # 绘制轮廓
            contours, _ = cv2.findContours(
                mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(vis, contours, -1, color, 2)

        if output_path:
            cv2.imwrite(output_path, vis)

        return vis


# 别名
WaterQualitySegmentorV2 = RADSegWaterSegmentor
