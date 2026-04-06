#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
C-RADIOv4 ViT-H Backbone 封装 (基于官方 NVlabs/RADIO 代码)

本模块是一个薄封装层，直接使用官方 NVlabs/RADIO 代码加载模型，
不做任何自定义模型实现。上层应用（如水利巡检）只需调用本模块 API。

加载方式:
  torch.hub.load() + source='local' — 使用本地下载的官方 RADIO 代码
  无需联网，所有文件均从本地加载

依赖的本地文件:
  1. RADIO 官方代码 (NVlabs/RADIO GitHub 仓库):
     - 包含 hubconf.py + radio/ 包
     - 来源: git clone NVlabs/RADIO 或 torch.hub 缓存
  2. C-RADIOv4 权重:
     - c-radio_v4-h_half.pth.tar (1.6GB, 半精度 checkpoint)
     - 包含 backbone + adaptor 投影层权重
  3. SigLIP2 文本模型:
     - google/siglip2-giant-opt-patch16-384 (HuggingFace 格式)
     - 包含文本编码器 + tokenizer

目录结构:
  models/
    NVlabs_RADIO/          # 官方 RADIO 代码
      hubconf.py
      radio/
        __init__.py
        radio_model.py
        siglip2_adaptor.py
        ...
    C-RADIOv4-H/
      c-radio_v4-h_half.pth.tar
      config.json
      ...
    siglip2-giant-opt-patch16-384/
      config.json
      tokenizer.json
      model-00001-of-00002.safetensors
      ...

作者: 空中智能体团队
日期: 2026-04-02
"""

import os
import sys
import json
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Dict, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 默认路径常量
_PROJECT_ROOT = Path(__file__).resolve(
    "../../../../.."
).resolve(getattr(sys, '_MEIPASS', Path(__file__).parent)) or Path(__file__).parent

DEFAULT_RADIO_CODE_DIR = os.environ.get(
    "RADIO_CODE_DIR",
    str(_PROJECT_ROOT / "models" / "NVlabs_RADIO"),
)
DEFAULT_CHECKPOINT_PATH = os.environ.get(
    "RADIO_CHECKPOINT_PATH",
    str(_PROJECT_ROOT / "models" / "C-RADIOv4-H" / "c-radio_v4-h_half.pth.tar"),
)
DEFAULT_SIGLIP2_DIR = os.environ.get(
    "SIGLIP2_DIR",
    str(_PROJECT_ROOT / "models" / "siglip2-giant-opt-patch16-384"),
)


class RadioBackbone(nn.Module):
    """
    C-RADIOv4 ViT-H Backbone (基于官方 NVlabs/RADIO 代码)

    直接调用官方 RADIO 代码加载模型，不做自定义实现。
    所有上层应用（水利巡检、缺陷检测等）统一使用此封装层。
    """

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        radio_code_dir: Optional[str] = None,
        siglip2_dir: Optional[str] = None,
        version: str = "c-radio_v4-h",
        adaptor_names: Optional[List[str]] = None,
        device: str = "cuda",
    ):
        """
        Args:
            checkpoint_path: C-RADIOv4 checkpoint 路径 (.pth.tar)
            radio_code_dir: NVlabs/RADIO 代码目录 (含 hubconf.py)
            siglip2_dir: SigLIP2 模型目录 (HuggingFace 格式)
            version: 模型版本 (当 checkpoint_path 存在时忽略)
            adaptor_names: 适配器列表，默认 ['siglip2-g']
            device: 推理设备
        """
        super().__init__()
        self.device = device
        self.version = version
        self.adaptor_names = adaptor_names or ["siglip2-g"]

        # 解析路径
        self.checkpoint_path = Path(
            checkpoint_path or DEFAULT_CHECKPOINT_PATH
        )
        self.radio_code_dir = Path(
            radio_code_dir or DEFAULT_RADIO_CODE_DIR
        )
        self.siglip2_dir = Path(
            siglip2_dir or DEFAULT_SIGLIP2_DIR
        )

        self.model = None
        self._load_mode = "unknown"

        # 设置 HF 缓存 (SigLIP2 离线加载)
        self._setup_hf_cache()

        # 加载模型
        self._load_model()

        self.to(device).eval()

        # 特征维度 (从模型获取)
        self.embed_dim = getattr(self.model, "embed_dim", 1280)
        self.num_reg_tokens = getattr(
            self.model, "num_summary_tokens", 10
        )

        total_params = sum(p.numel() for p in self.parameters()) / 1e6
        print(f"C-RADIOv4 Backbone 加载完成 (模式: {self._load_mode})")
        print(f"  设备: {device}, 参数量: {total_params:.1f}M")
        print(f"  Adaptors: {list(self.model.adaptors.keys()) if hasattr(self.model, 'adaptors') else 'none'}")

    # ── 模型加载 ──

    def _load_model(self):
        """使用官方 RADIO 代码加载模型"""
        # 验证路径
        if not self.radio_code_dir.exists():
            raise FileNotFoundError(
                f"RADIO 代码目录不存在: {self.radio_code_dir}\n"
                f"请下载 NVlabs/RADIO 到该目录 (需要包含 hubconf.py + radio/)"
            )

        if not self.checkpoint_path.exists():
            raise FileNotFoundError(
                f"Checkpoint 不存在: {self.checkpoint_path}\n"
                f"请下载 c-radio_v4-h_half.pth.tar 到该路径"
            )

        print(f"加载 C-RADIOv4 模型:")
        print(f"  RADIO 代码: {self.radio_code_dir}")
        print(f"  Checkpoint: {self.checkpoint_path} ({self.checkpoint_path.stat().st_size / 1e9:.2f} GB)")

        try:
            self.model = torch.hub.load(
                str(self.radio_code_dir),
                "radio_model",
                version=str(self.checkpoint_path),
                adaptor_names=self.adaptor_names,
                source="local",
                trust_remote_code=True,
            )
            self._load_mode = "official_local"
            print(f"  ✓ 官方 RADIO 代码加载成功")
        except Exception as e:
            print(f"  ✗ 加载失败: {e}")
            raise RuntimeError(
                f"无法加载 C-RADIOv4 模型: {e}\n"
                f"请确认 RADIO 代码和 Checkpoint 路径正确"
            ) from e

    # ── HF 缓存 (SigLIP2 离线加载) ──

    def _setup_hf_cache(self):
        """
        为 SigLIP2 adaptor 配置本地加载

        RADIO 的 SigLIP2 adaptor 内部调用:
          AutoModel.from_pretrained("google/siglip2-giant-opt-patch16-384")

        由于 HuggingFace 缓存格式复杂 (需要 blob hash + refs + snapshots)，
        本方法使用 monkey-patch 将 from_pretrained 重定向到本地目录。
        """
        if not self.siglip2_dir.exists():
            print(f"  SigLIP2 目录不存在: {self.siglip2_dir}")
            print(f"  SigLIP2 adaptor 将尝试在线下载")
            return

        # 检查关键文件
        if not (self.siglip2_dir / "config.json").exists():
            print(f"  SigLIP2 缺少 config.json")
            return

        index_file = self.siglip2_dir / "model.safetensors.index.json"
        if index_file.exists():
            with open(index_file, "r") as f:
                index = json.load(f)
            shards = set(index.get("weight_map", {}).values())
            for shard in shards:
                if not (self.siglip2_dir / shard).exists():
                    print(f"  SigLIP2 分片缺失: {shard}")
                    return

        # Monkey-patch: 将 HuggingFace from_pretrained 重定向到本地目录
        try:
            from transformers import AutoModel, AutoProcessor
            import transformers

            siglip_local = str(self.siglip2_dir)
            _orig_model = AutoModel.from_pretrained
            _orig_processor = AutoProcessor.from_pretrained

            # SigLIP2 adaptor 使用的 model name → 本地路径映射
            _SIGLIP2_NAMES = {
                "google/siglip2-giant-opt-patch16-384",
                "siglip2-g-384",
            }

            def _patched_model_fp(pretrained_model_name_or_path, *args, **kwargs):
                name = str(pretrained_model_name_or_path)
                if name in _SIGLIP2_NAMES or "siglip2-giant" in name:
                    print(f"    [HF 重定向] {name} → {siglip_local}")
                    return _orig_model(siglip_local, *args, **kwargs)
                return _orig_model(pretrained_model_name_or_path, *args, **kwargs)

            def _patched_processor_fp(pretrained_model_name_or_path, *args, **kwargs):
                name = str(pretrained_model_name_or_path)
                if name in _SIGLIP2_NAMES or "siglip2-giant" in name:
                    print(f"    [HF 重定向] {name} → {siglip_local}")
                    return _orig_processor(siglip_local, *args, **kwargs)
                return _orig_processor(pretrained_model_name_or_path, *args, **kwargs)

            AutoModel.from_pretrained = _patched_model_fp
            AutoProcessor.from_pretrained = _patched_processor_fp

            total_gb = sum(
                f.stat().st_size
                for f in self.siglip2_dir.glob("*.safetensors")
            ) / 1e9
            print(f"  ✓ SigLIP2 本地加载已配置: {siglip_local} ({total_gb:.1f} GB)")
        except ImportError:
            print("  ⚠ transformers 未安装，SigLIP2 文本编码不可用")

    # ── 特征提取 ──

    @torch.no_grad()
    def extract_features(
        self,
        image: torch.Tensor,
        output_spatial: bool = True,
    ) -> dict:
        """
        提取视觉特征

        Args:
            image: [B, 3, H, W] (0-255 uint8 或 0-1 float)
            output_spatial: 是否输出空间特征图

        Returns:
            {
                "features": [B, N_patches, D],           # RADIO backbone 特征 (1280维)
                "adaptor_features": [B, N_patches, D'],  # adaptor 投影特征 (1536维 for siglip2-g)
                "spatial_features": [B, D, H', W'],
                "summary": [B, num_summary, D],
                "grid_size": (H_patch, W_patch),
                "adaptor_outputs": {name: RadioOutput},  # 所有 adaptor 输出 (NEW)
            }
        """
        if image.dtype == torch.uint8:
            image = image.float() / 255.0
        image = image.to(self.device)

        result = self.model(image)

        # 官方 RADIO 返回格式:
        # - 无 adaptor: RadioOutput (summary, features)
        # - 有 adaptor: dict {'backbone': RadioOutput, 'adaptor_name': RadioOutput}
        adaptor_features = None
        adaptor_name = None
        adaptor_outputs = {}

        if isinstance(result, dict):
            # 使用 backbone 输出获取 patch features
            backbone_out = result.get('backbone', result.get(list(result.keys())[0]))
            summary = backbone_out.summary if hasattr(backbone_out, 'summary') else None
            features = backbone_out.features if hasattr(backbone_out, 'features') else backbone_out

            # 获取所有 adaptor 输出
            for name in result.keys():
                if name != 'backbone':
                    adaptor_outputs[name] = result[name]

            # 获取 SigLIP2 adaptor 输出 (与文本嵌入空间对齐)
            for name in ['siglip2-g', 'siglip2-g-384']:
                if name in result:
                    adaptor_out = result[name]
                    adaptor_features = adaptor_out.features if hasattr(adaptor_out, 'features') else None
                    adaptor_name = name
                    break
        elif hasattr(result, 'summary') and hasattr(result, 'features'):
            summary = result.summary
            features = result.features
        elif isinstance(result, tuple):
            summary, features = result[0], result[1]
        else:
            features = result
            summary = None

        B, N, C = features.shape

        # 计算 patch grid
        # RADIO features 已是纯 patch tokens (不含 register tokens)
        # 尝试推断 grid 尺寸
        side = int(N ** 0.5)
        if side * side == N:
            # 完美平方数，N 即为 patch 数量
            H_patch = W_patch = side
            patch_features = features
        else:
            # N 包含 register tokens，需要减去
            num_patches = N - self.num_reg_tokens
            side = int(num_patches ** 0.5)
            H_patch = W_patch = side
            patch_features = features[:, self.num_reg_tokens:]

        result_dict = {
            "features": patch_features,
            "summary": summary,
            "grid_size": (H_patch, W_patch),
        }

        # 添加 adaptor 特征 (与文本嵌入空间对齐)
        if adaptor_features is not None:
            result_dict["adaptor_features"] = adaptor_features

        # 添加所有 adaptor 输出 (NEW: 支持多 adaptor)
        if adaptor_outputs:
            result_dict["adaptor_outputs"] = adaptor_outputs

        if output_spatial:
            patch_tokens = patch_features.reshape(B, H_patch, W_patch, C)
            result_dict["spatial_features"] = patch_tokens.permute(0, 3, 1, 2)

        return result_dict

    # ── 文本编码 (SigLIP2 adaptor) ──

    @torch.no_grad()
    def encode_text(self, text: List[str]) -> torch.Tensor:
        """
        使用 SigLIP2 adaptor 编码文本

        Args:
            text: 文本列表, 如 ["black water pollution", "green algae bloom"]

        Returns:
            text_features: [N, D] 归一化文本特征
        """
        adaptor = self._get_siglip_adaptor()
        if adaptor is None:
            raise RuntimeError(
                "SigLIP2 adaptor 未加载。"
                "请确保 siglip2_dir 路径正确且文件完整"
            )

        text_tokens = adaptor.tokenizer(text).to(self.device)
        text_features = adaptor.encode_text(text_tokens, normalize=True)
        return text_features

    @torch.no_grad()
    def compute_similarity(
        self,
        image: torch.Tensor,
        text: List[str],
    ) -> torch.Tensor:
        """
        计算图像-文本相似度 (零样本分类)

        Args:
            image: [B, 3, H, W]
            text: 文本提示列表

        Returns:
            similarity: [B, len(text)] 相似度矩阵
        """
        adaptor = self._get_siglip_adaptor()
        if adaptor is None:
            raise RuntimeError("SigLIP2 adaptor 未加载")

        # 编码文本
        text_tokens = adaptor.tokenizer(text).to(self.device)
        text_features = adaptor.encode_text(text_tokens, normalize=True)

        # 提取backbone特征
        result = self.model(image)

        # 解析RADIO输出
        if isinstance(result, dict):
            backbone_out = result.get('backbone', result.get(list(result.keys())[0]))
            summary = backbone_out.summary if hasattr(backbone_out, 'summary') else None
            features = backbone_out.features if hasattr(backbone_out, 'features') else backbone_out

            # 获取adaptor输出
            for name in ['siglip2-g', 'siglip2-g-384']:
                if name in result:
                    adaptor_out = result[name]
                    vis_summary = adaptor_out.summary if hasattr(adaptor_out, 'summary') else None
                    if vis_summary is not None:
                        vis_features = F.normalize(vis_summary.float(), dim=-1)
                        similarity = vis_features @ text_features.T
                        return similarity
        elif hasattr(result, 'summary') and hasattr(result, 'features'):
            summary = result.summary
            features = result.features
        else:
            summary = None
            features = result

        # 如果没有直接获取到adaptor输出，使用backbone特征
        if summary is None:
            summary = features.mean(dim=1, keepdim=True) if features is not None else None

        if summary is None:
            raise RuntimeError("无法提取视觉特征")

        # 归一化
        vis_features = F.normalize(summary.squeeze(1).float(), dim=-1)
        similarity = vis_features @ text_features.T
        return similarity

    def _get_siglip_adaptor(self):
        """获取 SigLIP2 adaptor"""
        if not hasattr(self.model, "adaptors"):
            return None
        # adaptor 名称可能是 'siglip2-g' 或 'siglip2-g-384'
        for name in ["siglip2-g", "siglip2-g-384"]:
            if name in self.model.adaptors:
                return self.model.adaptors[name]
        return None

    def get_siglip_adaptor(self):
        """获取 SigLIP2 adaptor (公开接口)"""
        return self._get_siglip_adaptor()

    # ── numpy 便捷接口 ──

    @torch.no_grad()
    def extract_features_numpy(
        self,
        image_bgr: np.ndarray,
        input_size: int = 896,
    ) -> dict:
        """
        从 numpy BGR 图像提取特征

        Args:
            image_bgr: [H, W, 3] BGR 格式
            input_size: 输入尺寸

        Returns:
            同 extract_features
        """
        import cv2
        image_rgb = image_bgr[:, :, ::-1].copy()
        image_resized = cv2.resize(image_rgb, (input_size, input_size))
        image_tensor = (
            torch.from_numpy(image_resized).permute(2, 0, 1).unsqueeze(0)
        )
        image_tensor = image_tensor.float() / 255.0
        return self.extract_features(image_tensor)


# ── 测试入口 ──

def main():
    import argparse
    parser = argparse.ArgumentParser(description="C-RADIOv4 Backbone 测试")
    parser.add_argument("--checkpoint", type=str, default=str(DEFAULT_CHECKPOINT_PATH))
    parser.add_argument("--radio-code", type=str, default=str(DEFAULT_RADIO_CODE_DIR))
    parser.add_argument("--siglip2-dir", type=str, default=str(DEFAULT_SIGLIP2_DIR))
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--input-size", type=int, default=896)
    args = parser.parse_args()

    backbone = RadioBackbone(
        checkpoint_path=args.checkpoint,
        radio_code_dir=args.radio_code,
        siglip2_dir=args.siglip2_dir,
        device=args.device,
    )

    dummy = torch.randn(1, 3, args.input_size, args.input_size)
    dummy = (dummy * 255).clamp(0, 255).to(torch.uint8)

    print(f"\n测试推理 (输入: {args.input_size}x{args.input_size})...")
    result = backbone.extract_features(dummy)
    print(f"  Patch 特征: {result['features'].shape}")
    print(f"  空间特征图: {result.get('spatial_features', 'N/A')}")
    print(f"  Grid 尺寸: {result['grid_size']}")

    print(f"\n测试文本编码...")
    text_feats = backbone.encode_text(["water pollution", "clean water"])
    print(f"  文本特征: {text_feats.shape}")

    sim = backbone.compute_similarity(dummy, ["water pollution", "clean water"])
    print(f"  相似度: {sim}")

    print("\nC-RADIOv4 Backbone 验证通过!")


if __name__ == "__main__":
    main()
