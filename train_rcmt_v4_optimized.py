"""
RCMT-V4-Swin-Temporal: 优化版本（目标F1 > 0.92）
=====================================================

基于V3的优化策略：
1. ✅ 多损失函数组合（BCE + Dice + Focal）
2. ✅ Focal Loss处理类别不平衡
3. ✅ 正样本权重调整（pos_weight=3.0）
4. ✅ 增强数据增强策略
5. ✅ Label Smoothing
6. ✅ 优化学习率策略
7. ✅ 增强DropPath正则化

SOTA参考策略：
- BIT (IEEE TGRS 2022): BCE + Dice Loss
- ChangeFormer (IEEE TGRS 2022): Label Smoothing + Strong Augmentation
- Changer (CVPR 2023): Focal Loss + Multi-scale Training
- TinyCD (2024): MixUp + CutMix + Cosine Annealing

目标性能：F1 > 0.92, IoU > 0.85

作者：RCMT-V4团队
日期：2026-03-10
"""

import os
import sys
import json
import time
import argparse
import datetime
from pathlib import Path
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.amp import GradScaler, autocast
from torch.utils.checkpoint import checkpoint
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.model import build_rcmt_v3_hybrid
from datasets.dataset import create_dataloaders
from utils.metrics import MetricsCalculator


# ==================== DropPath（随机深度）====================

class DropPath(nn.Module):
    """
    DropPath: 随机深度正则化

    功能：在训练时随机丢弃整条路径，提升泛化能力
    参考：Deep Networks with Stochastic Depth (https://arxiv.org/abs/1603.09382)
    """
    def __init__(self, drop_prob=0.):
        super(DropPath, self).__init__()
        self.drop_prob = drop_prob

    def forward(self, x):
        if self.drop_prob == 0. or not self.training:
            return x

        keep_prob = 1 - self.drop_prob
        shape = (x.shape[0],) + (1,) * (x.ndim - 1)
        random_tensor = keep_prob + torch.rand(shape, dtype=x.dtype, device=x.device)
        random_tensor.floor_()
        output = x.div(keep_prob) * random_tensor
        return output


# ==================== Patch Embedding（图块嵌入）====================

class PatchEmbed(nn.Module):
    """
    Patch Embedding: 图像到图块的嵌入

    功能：将输入图像划分为不重叠的图块，并嵌入到高维空间
    输入：(B, C, H, W)
    输出：(B, num_patches, embed_dim)
    """
    def __init__(self, img_size=256, patch_size=4, in_chans=3, embed_dim=96):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        self.patches_resolution = (img_size // patch_size, img_size // patch_size)
        self.num_patches = self.patches_resolution[0] * self.patches_resolution[1]
        self.embed_dim = embed_dim

        self.proj = nn.Conv2d(in_chans, embed_dim, kernel_size=patch_size, stride=patch_size)
        self.norm = nn.LayerNorm(embed_dim)

    def forward(self, x):
        B, C, H, W = x.shape
        x = self.proj(x)
        x = x.flatten(2).transpose(1, 2)
        x = self.norm(x)
        return x


# ==================== Window Attention（窗口注意力）====================

class WindowAttention(nn.Module):
    """
    Window-based Multi-Head Self-Attention (W-MSA)

    功能：在局部窗口内进行自注意力计算，减少计算复杂度
    复杂度：O(H*W*C^2) -> O(window_size^2*C^2 * (H*W/window_size^2))

    参数：
        dim: 输入特征维度
        window_size: 窗口大小（默认7x7）
        num_heads: 注意力头数
    """
    def __init__(self, dim, window_size, num_heads=8):
        super().__init__()
        self.dim = dim
        self.window_size = window_size  # (Wh, Ww)
        self.num_heads = num_heads
        head_dim = dim // num_heads
        self.scale = head_dim ** -0.5  # 缩放因子

        # QKV投影层
        self.qkv = nn.Linear(dim, dim * 3, bias=True)
        self.attn_drop = nn.Dropout(0.0)

        # 输出投影层
        self.proj = nn.Linear(dim, dim)
        self.proj_drop = nn.Dropout(0.0)

        # 相对位置偏置表：学习窗口内相对位置关系
        self.relative_position_bias_table = nn.Parameter(
            torch.zeros((2 * window_size[0] - 1) * (2 * window_size[1] - 1), num_heads)
        )  # (2*Wh-1 * 2*Ww-1, nH)
        nn.init.trunc_normal_(self.relative_position_bias_table, std=0.02)

        # 计算相对位置索引
        coords_h = torch.arange(window_size[0])
        coords_w = torch.arange(window_size[1])
        coords = torch.stack(torch.meshgrid([coords_h, coords_w], indexing='ij'))  # (2, Wh, Ww)
        coords_flatten = torch.flatten(coords, 1)  # (2, Wh*Ww)

        # 计算相对坐标
        relative_coords = coords_flatten[:, :, None] - coords_flatten[:, None, :]  # (2, Wh*Ww, Wh*Ww)
        relative_coords = relative_coords.permute(1, 2, 0).contiguous()  # (Wh*Ww, Wh*Ww, 2)

        # 转换为索引
        relative_coords[:, :, 0] += window_size[0] - 1  # shift to start from 0
        relative_coords[:, :, 1] += window_size[1] - 1
        relative_coords[:, :, 0] *= 2 * window_size[1] - 1
        relative_position_index = relative_coords.sum(-1)  # (Wh*Ww, Wh*Ww)

        self.register_buffer("relative_position_index", relative_position_index)

    def forward(self, x, mask=None):
        """
        Args:
            x: (num_windows*B, N, C), N = window_size * window_size
            mask: (num_windows, N, N) or None
        """
        B_, N, C = x.shape

        # 计算QKV：(B_, N, C) -> (B_, N, 3, C) -> (3, B_, num_heads, N, C//num_heads)
        qkv = self.qkv(x).reshape(B_, N, 3, self.num_heads, C // self.num_heads).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]  # (B_, nH, N, C//nH)

        # 缩放点积注意力
        q = q * self.scale
        attn = (q @ k.transpose(-2, -1))  # (B_, nH, N, N)

        # 添加相对位置偏置
        relative_position_bias = self.relative_position_bias_table[
            self.relative_position_index.view(-1)
        ].view(
            self.window_size[0] * self.window_size[1],
            self.window_size[0] * self.window_size[1],
            -1
        )  # (N, N, nH)
        relative_position_bias = relative_position_bias.permute(2, 0, 1).contiguous()  # (nH, N, N)
        attn = attn + relative_position_bias.unsqueeze(0)  # (B_, nH, N, N)

        # 如果有mask，添加mask
        if mask is not None:
            nW = mask.shape[0]  # num_windows
            attn = attn.view(B_ // nW, nW, self.num_heads, N, N) + mask.unsqueeze(1).unsqueeze(0)
            attn = attn.view(-1, self.num_heads, N, N)
            attn = F.softmax(attn, dim=-1)
        else:
            attn = F.softmax(attn, dim=-1)

        attn = self.attn_drop(attn)

        # 注意力加权求和
        x = (attn @ v).transpose(1, 2).reshape(B_, N, C)  # (B_, N, C)

        # 输出投影
        x = self.proj(x)
        x = self.proj_drop(x)

        return x


# ==================== Swin Transformer Block ====================

class SwinTransformerBlock(nn.Module):
    """
    Swin Transformer Block: 核心构建块

    结构：LayerNorm -> (W-MSA or SW-MSA) -> LayerNorm -> MLP
    功能：交替使用Window Attention和Shifted Window Attention

    参数：
        dim: 输入特征维度
        input_resolution: 输入分辨率 (H, W)
        num_heads: 注意力头数
        window_size: 窗口大小
        shift_size: 移动大小（0表示普通窗口，>0表示移动窗口）
        mlp_ratio: MLP扩展比例
        drop_path: DropPath概率
    """
    def __init__(self, dim, input_resolution, num_heads, window_size=7, shift_size=0,
                 mlp_ratio=4., drop=0., drop_path=0., use_checkpoint=False):
        super().__init__()
        self.dim = dim
        self.input_resolution = input_resolution
        self.num_heads = num_heads
        self.window_size = window_size
        self.shift_size = shift_size
        self.mlp_ratio = mlp_ratio
        self.use_checkpoint = False  # 禁用梯度检查点以加速训练

        # 如果输入分辨率小于窗口大小，调整窗口大小
        if min(self.input_resolution) <= self.window_size:
            self.shift_size = 0
            self.window_size = min(self.input_resolution)

        # Layer Normalization
        self.norm1 = nn.LayerNorm(dim)

        # Window Attention
        self.attn = WindowAttention(
            dim, window_size=(self.window_size, self.window_size), num_heads=num_heads
        )

        # DropPath
        self.drop_path = DropPath(drop_path) if drop_path > 0. else nn.Identity()

        # Layer Normalization
        self.norm2 = nn.LayerNorm(dim)

        # MLP
        mlp_hidden_dim = int(dim * mlp_ratio)
        self.mlp = nn.Sequential(
            nn.Linear(dim, mlp_hidden_dim),
            nn.GELU(),
            nn.Dropout(drop),
            nn.Linear(mlp_hidden_dim, dim),
            nn.Dropout(drop),
        )

        # 计算attention mask（用于shifted window attention）
        if self.shift_size > 0:
            H, W = self.input_resolution

            # 计算padding后的分辨率（确保能被window_size整除）
            pad_h = (self.window_size - H % self.window_size) % self.window_size
            pad_w = (self.window_size - W % self.window_size) % self.window_size
            H_pad, W_pad = H + pad_h, W + pad_w

            # 创建区域标记（使用padding后的尺寸）
            img_mask = torch.zeros((1, H_pad, W_pad, 1))  # (1, H_pad, W_pad, 1)
            h_slices = (slice(0, -self.window_size),
                        slice(-self.window_size, -self.shift_size),
                        slice(-self.shift_size, None))
            w_slices = (slice(0, -self.window_size),
                        slice(-self.window_size, -self.shift_size),
                        slice(-self.shift_size, None))
            cnt = 0
            for h in h_slices:
                for w in w_slices:
                    img_mask[:, h, w, :] = cnt
                    cnt += 1

            # 划分窗口
            mask_windows = self.window_partition(img_mask)  # (num_windows, Ws, Ws, 1)
            mask_windows = mask_windows.view(-1, self.window_size * self.window_size)  # (num_windows, N)

            # 计算mask：同一区域=0，不同区域=-100
            attn_mask = mask_windows.unsqueeze(1) - mask_windows.unsqueeze(2)  # (num_windows, N, N)
            attn_mask = attn_mask.masked_fill(attn_mask != 0, float(-100.0)).masked_fill(attn_mask == 0, float(0.0))
        else:
            attn_mask = None

        self.register_buffer("attn_mask", attn_mask)

    def window_partition(self, x):
        """
        窗口划分

        Args:
            x: (B, H, W, C)
        Returns:
            windows: (num_windows*B, window_size, window_size, C)
        """
        B, H, W, C = x.shape

        # 处理不能整除的情况（使用padding）
        if H % self.window_size != 0 or W % self.window_size != 0:
            pad_h = (self.window_size - H % self.window_size) % self.window_size
            pad_w = (self.window_size - W % self.window_size) % self.window_size
            x = F.pad(x, (0, 0, 0, pad_w, 0, pad_h))
            H_pad, W_pad = H + pad_h, W + pad_w
        else:
            H_pad, W_pad = H, W

        # 划分窗口：(B, H, W, C) -> (B, H//Ws, Ws, W//Ws, Ws, C)
        x = x.view(B, H_pad // self.window_size, self.window_size, W_pad // self.window_size, self.window_size, C)

        # 重排：(B, H//Ws, Ws, W//Ws, Ws, C) -> (B*num_windows, Ws, Ws, C)
        windows = x.permute(0, 1, 3, 2, 4, 5).contiguous().view(-1, self.window_size, self.window_size, C)

        return windows

    def window_reverse(self, windows, H, W):
        """
        窗口还原

        Args:
            windows: (num_windows*B, window_size, window_size, C)
            H, W: 原始分辨率
        Returns:
            x: (B, H, W, C)
        """
        # 计算padding后的分辨率
        if H % self.window_size != 0 or W % self.window_size != 0:
            pad_h = (self.window_size - H % self.window_size) % self.window_size
            pad_w = (self.window_size - W % self.window_size) % self.window_size
            H_pad, W_pad = H + pad_h, W + pad_w
        else:
            H_pad, W_pad = H, W

        # 计算batch size
        num_windows = H_pad // self.window_size * W_pad // self.window_size
        B = int(windows.shape[0] / num_windows)

        # 重排：(B*num_windows, Ws, Ws, C) -> (B, H//Ws, W//Ws, Ws, Ws, C) -> (B, H, W, C)
        x = windows.view(B, H_pad // self.window_size, W_pad // self.window_size, self.window_size, self.window_size, -1)
        x = x.permute(0, 1, 3, 2, 4, 5).contiguous().view(B, H_pad, W_pad, -1)

        # 移除padding
        if H % self.window_size != 0 or W % self.window_size != 0:
            x = x[:, :H, :W, :].contiguous()

        return x

    def forward(self, x):
        """
        前向传播

        Args:
            x: (B, L, C), L = H*W
        Returns:
            x: (B, L, C)
        """
        # 动态计算H和W（而不是使用固定的input_resolution）
        B, L, C = x.shape
        H = W = int(L ** 0.5)

        # 验证L是否为完全平方数
        if H * W != L:
            # 如果不是完全平方数，可能是padding后的结果
            # 尝试从input_resolution获取
            H, W = self.input_resolution

        shortcut = x

        # Layer Normalization
        x = self.norm1(x)

        # 重塑为2D：(B, L, C) -> (B, H, W, C)
        x = x.view(B, H, W, C)

        # Cyclic Shift（循环移动）
        if self.shift_size > 0:
            shifted_x = torch.roll(x, shifts=(-self.shift_size, -self.shift_size), dims=(1, 2))
        else:
            shifted_x = x

        # 划分窗口
        x_windows = self.window_partition(shifted_x)  # (num_windows*B, Ws, Ws, C)
        x_windows = x_windows.view(-1, self.window_size * self.window_size, C)  # (num_windows*B, N, C)

        # Window Attention
        # 使用梯度检查点节省显存
        if self.use_checkpoint and self.training:
            attn_windows = checkpoint(self.attn, x_windows, self.attn_mask, use_reentrant=False)
        else:
            attn_windows = self.attn(x_windows, mask=self.attn_mask)  # (num_windows*B, N, C)

        # 还原窗口
        attn_windows = attn_windows.view(-1, self.window_size, self.window_size, C)
        shifted_x = self.window_reverse(attn_windows, H, W)  # (B, H, W, C)

        # Reverse Cyclic Shift
        if self.shift_size > 0:
            x = torch.roll(shifted_x, shifts=(self.shift_size, self.shift_size), dims=(1, 2))
        else:
            x = shifted_x

        # 重塑回序列：(B, H, W, C) -> (B, L, C)
        x = x.view(B, H * W, C)

        # 残差连接 + MLP
        x = shortcut + self.drop_path(x)
        x = x + self.drop_path(self.mlp(self.norm2(x)))

        return x


# ==================== Temporal Fusion Module（时序融合模块）====================

class TemporalFusionModule(nn.Module):
    """
    时序融合模块：处理T1和T2的双向信息流

    功能：
    1. 前向融合：T1的信息增强T2
    2. 后向融合：T2的信息增强T1
    3. 一致性融合：整合双向信息

    参数：
        dim: 特征维度
        num_heads: 注意力头数
    """
    def __init__(self, dim, num_heads=8):
        super().__init__()
        self.dim = dim
        self.num_heads = num_heads

        # 前向注意力：T1 -> T2
        self.forward_attn = nn.MultiheadAttention(dim, num_heads, batch_first=True, dropout=0.0)

        # 后向注意力：T2 -> T1
        self.backward_attn = nn.MultiheadAttention(dim, num_heads, batch_first=True, dropout=0.0)

        # 一致性融合卷积
        self.fusion_conv = nn.Sequential(
            nn.Conv2d(dim * 2, dim, kernel_size=3, padding=1),
            nn.BatchNorm2d(dim),
            nn.ReLU(inplace=True),
            nn.Conv2d(dim, dim, kernel_size=3, padding=1),
            nn.BatchNorm2d(dim),
        )

        # 可学习的融合权重
        self.gamma = nn.Parameter(torch.zeros(1))

    def forward(self, t1_feat, t2_feat):
        """
        前向传播

        Args:
            t1_feat: (B, C, H, W) - T1时刻特征
            t2_feat: (B, C, H, W) - T2时刻特征
        Returns:
            fused_feat: (B, C, H, W) - 融合后的特征
        """
        B, C, H, W = t1_feat.shape

        # 转换为序列格式：(B, C, H, W) -> (B, H*W, C)
        t1_seq = t1_feat.flatten(2).transpose(1, 2)
        t2_seq = t2_feat.flatten(2).transpose(1, 2)

        # 前向融合：T1增强T2
        t2_enhanced, _ = self.forward_attn(t2_seq, t1_seq, t1_seq)

        # 后向融合：T2增强T1
        t1_enhanced, _ = self.backward_attn(t1_seq, t2_seq, t2_seq)

        # 转回空间格式：(B, H*W, C) -> (B, C, H, W)
        t2_enhanced = t2_enhanced.transpose(1, 2).reshape(B, C, H, W)
        t1_enhanced = t1_enhanced.transpose(1, 2).reshape(B, C, H, W)

        # 一致性融合
        concat_feat = torch.cat([t1_enhanced, t2_enhanced], dim=1)  # (B, 2C, H, W)
        fused_feat = self.fusion_conv(concat_feat)  # (B, C, H, W)

        # 残差连接
        output = fused_feat * self.gamma + (t1_feat + t2_feat) / 2

        return output


# ==================== Swin Transformer Backbone ====================

class SwinTransformerBackbone(nn.Module):
    """
    Swin Transformer Backbone: 完整实现

    结构：Patch Embed -> [Stage 1] -> [Stage 2] -> [Stage 3] -> [Stage 4]
    每个Stage包含：多个Swin Block + Downsample（可选）

    参数：
        pretrain_img_size: 预训练图像大小
        patch_size: 图块大小
        in_chans: 输入通道数
        embed_dim: 嵌入维度
        depths: 每个stage的block数量
        num_heads: 每个stage的注意力头数
        window_size: 窗口大小
        drop_path_rate: DropPath概率
        use_checkpoint: 是否使用梯度检查点（节省显存）
    """
    def __init__(self, pretrain_img_size=256, patch_size=4, in_chans=3,
                 embed_dim=96, depths=[2, 2, 2, 2], num_heads=[2, 4, 8, 16],
                 window_size=7, drop_path_rate=0.2, use_checkpoint=False):
        super().__init__()
        self.num_layers = len(depths)
        self.embed_dim = embed_dim
        self.use_checkpoint = False  # 禁用梯度检查点以加速训练

        # Patch Embedding
        self.patch_embed = PatchEmbed(
            img_size=pretrain_img_size, patch_size=patch_size,
            in_chans=in_chans, embed_dim=embed_dim
        )
        patches_resolution = self.patch_embed.patches_resolution

        # Dropout
        self.pos_drop = nn.Dropout(0.0)

        # 计算每层的DropPath概率
        dpr = [x.item() for x in torch.linspace(0, drop_path_rate, sum(depths))]

        # 构建各个Stage
        self.layers = nn.ModuleList()
        for i_layer in range(self.num_layers):
            # 计算当前stage的分辨率
            input_resolution = (
                patches_resolution[0] // (2 ** i_layer),
                patches_resolution[1] // (2 ** i_layer)
            )

            # 构建Swin Blocks
            layer = nn.ModuleList([
                SwinTransformerBlock(
                    dim=int(embed_dim * 2 ** i_layer),
                    input_resolution=input_resolution,
                    num_heads=num_heads[i_layer],
                    window_size=window_size,
                    # 交替使用Window和Shifted Window
                    shift_size=0 if (i % 2 == 0) else window_size // 2,
                    drop_path=dpr[sum(depths[:i_layer]) + i],
                    use_checkpoint=use_checkpoint,
                )
                for i in range(depths[i_layer])
            ])
            self.layers.append(layer)

        # Patch Merging（下采样层）
        # Patch Merging的LayerNorm（输入是4*C）
        self.downsample_norms = nn.ModuleList([
            nn.LayerNorm(int(embed_dim * 2 ** i_layer) * 4)
            for i_layer in range(self.num_layers - 1)
        ])

        # Patch Merging的Linear层：(4C -> 2C)
        self.downsample_projs = nn.ModuleList([
            nn.Linear(int(embed_dim * 2 ** i_layer) * 4, int(embed_dim * 2 ** (i_layer + 1)))
            for i_layer in range(self.num_layers - 1)
        ])

        self.num_features = int(embed_dim * 2 ** (self.num_layers - 1))

    def forward(self, x):
        """
        前向传播

        Args:
            x: (B, C, H, W)
        Returns:
            features: List of features from each stage
        """
        # Patch Embedding: (B, 3, 256, 256) -> (B, 4096, 96)
        x = self.patch_embed(x)
        x = self.pos_drop(x)

        # 计算初始分辨率
        B, L, C = x.shape
        patches_resolution = self.patch_embed.patches_resolution

        features = []
        for i, layer in enumerate(self.layers):
            # 计算当前stage的分辨率
            input_resolution = (
                patches_resolution[0] // (2 ** i),
                patches_resolution[1] // (2 ** i)
            )

            # 通过Swin Blocks
            for block in layer:
                if self.use_checkpoint and self.training:
                    x = checkpoint(block, x, use_reentrant=False)
                else:
                    x = block(x)

            # 转换为空间格式并保存：(B, L, C) -> (B, C, H, W)
            B, L, C = x.shape
            H, W = input_resolution
            features.append(x.transpose(1, 2).reshape(B, C, H, W))

            # Patch Merging（下采样，最后一层不需要）
            if i < self.num_layers - 1:
                # 重塑为2D：(B, L, C) -> (B, H, W, C)
                x = x.view(B, H, W, C)

                # 在H和W维度上合并相邻patch：(B, H, W, C) -> (B, H/2, W/2, 4C)
                # 取2x2的patch
                x0 = x[:, 0::2, 0::2, :]  # (B, H/2, W/2, C)
                x1 = x[:, 1::2, 0::2, :]  # (B, H/2, W/2, C)
                x2 = x[:, 0::2, 1::2, :]  # (B, H/2, W/2, C)
                x3 = x[:, 1::2, 1::2, :]  # (B, H/2, W/2, C)
                x = torch.cat([x0, x1, x2, x3], dim=-1)  # (B, H/2, W/2, 4C)

                # Layer Normalization
                x = self.downsample_norms[i](x)  # LayerNorm

                # 展平：(B, H/2, W/2, 4C) -> (B, H*W/4, 4C)
                x = x.view(B, -1, x.shape[-1])

                # Linear到目标维度：(B, H*W/4, 4C) -> (B, H*W/4, 2C)
                x = self.downsample_projs[i](x)

        return features


# ==================== Decoder（解码器）====================

class DecoderBlock(nn.Module):
    """
    解码器块：上采样 + 跳跃连接

    功能：
    1. 上采样（2倍）
    2. 与编码器特征融合（跳跃连接）
    3. 双层卷积处理

    参数：
        in_channels: 输入通道数
        skip_channels: 跳跃连接通道数
        out_channels: 输出通道数
    """
    def __init__(self, in_channels, skip_channels, out_channels):
        super().__init__()
        # 转置卷积上采样（2倍）
        self.up = nn.ConvTranspose2d(in_channels, out_channels, kernel_size=2, stride=2)

        # 双层卷积处理
        self.conv = nn.Sequential(
            nn.Conv2d(out_channels + skip_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x, skip=None):
        """
        前向传播

        Args:
            x: (B, in_channels, H, W)
            skip: (B, skip_channels, H*2, W*2) or None
        Returns:
            x: (B, out_channels, H*2, W*2)
        """
        x = self.up(x)  # 上采样
        if skip is not None:
            x = torch.cat([x, skip], dim=1)  # 跳跃连接
        x = self.conv(x)  # 卷积处理
        return x


# ==================== Main Model（主模型）====================

class RCMT_V4_Swin_Temporal(nn.Module):
    """
    RCMT-V4-Swin-Temporal: 优化版本

    架构：
    1. Swin Transformer Backbone（双时相共享权重）
    2. Temporal Fusion Module（多尺度时序融合）
    3. Decoder（带跳跃连接的解码器）

    参数：
        in_channels: 输入通道数（3 for RGB）
        num_classes: 输出类别数（1 for binary change detection）
        embed_dim: 嵌入维度（96 for Swin-Tiny）
        depths: 每个stage的深度
        num_heads: 每个stage的注意力头数
        window_size: 窗口大小
        use_temporal_fusion: 是否使用时序融合
        drop_path_rate: DropPath概率
        use_checkpoint: 是否使用梯度检查点
    """
    def __init__(self, in_channels=3, num_classes=1, embed_dim=96,
                 depths=[2, 2, 2, 2], num_heads=[2, 4, 8, 16],
                 window_size=7, use_temporal_fusion=True, drop_path_rate=0.2,
                 use_checkpoint=False):
        super().__init__()
        self.use_temporal_fusion = use_temporal_fusion

        # Swin Backbone（共享权重）
        self.backbone = SwinTransformerBackbone(
            pretrain_img_size=256,
            patch_size=4,
            in_chans=in_channels,
            embed_dim=embed_dim,
            depths=depths,
            num_heads=num_heads,
            window_size=window_size,
            drop_path_rate=drop_path_rate,
            use_checkpoint=use_checkpoint,
        )

        # Temporal Fusion Modules
        if use_temporal_fusion:
            self.temporal_fusions = nn.ModuleList([
                TemporalFusionModule(embed_dim * (2 ** i), num_heads[i] if i < len(num_heads) else 8)
                for i in range(len(depths))
            ])

        # Decoder
        decoder_channels = [512, 256, 128, 64]
        self.decoder = nn.ModuleList()

        encoder_channels = [embed_dim * (2 ** i) for i in range(len(depths))]

        for i in range(len(decoder_channels)):
            in_ch = encoder_channels[-(i+1)] if i == 0 else decoder_channels[i-1]
            skip_ch = encoder_channels[-(i+2)] if i < len(encoder_channels)-1 else 0
            out_ch = decoder_channels[i]

            self.decoder.append(DecoderBlock(in_ch, skip_ch, out_ch))

        # 最终上采样层：128x128 -> 256x256
        self.final_upsample = nn.ConvTranspose2d(decoder_channels[-1], decoder_channels[-1], kernel_size=2, stride=2)

        # 最终分割头
        self.seg_head = nn.Conv2d(decoder_channels[-1], num_classes, kernel_size=1)

    def forward(self, x):
        """
        前向传播

        Args:
            x: (B, 6, H, W) - [T1_RGB, T2_RGB]
        Returns:
            output: (B, 1, H, W) - 变化检测mask
        """
        # 分离T1和T2
        t1_img = x[:, :3, :, :]  # (B, 3, H, W)
        t2_img = x[:, 3:, :, :]  # (B, 3, H, W)

        # 提取特征（共享backbone）
        t1_features = self.backbone(t1_img)  # List of 4 features
        t2_features = self.backbone(t2_img)

        # Temporal Fusion
        fused_features = []
        for i, (t1_feat, t2_feat) in enumerate(zip(t1_features, t2_features)):
            if self.use_temporal_fusion:
                fused = self.temporal_fusions[i](t1_feat, t2_feat)
            else:
                fused = (t1_feat + t2_feat) / 2
            fused_features.append(fused)

        # Decoder
        x = fused_features[-1]
        for i, decoder_block in enumerate(self.decoder):
            skip = fused_features[-(i+2)] if i < len(fused_features)-1 else None
            x = decoder_block(x, skip)

        # 最终上采样
        x = self.final_upsample(x)  # 128x128 -> 256x256

        # 最终预测
        output = self.seg_head(x)

        return output


# ==================== Loss Functions（损失函数）====================

class DiceLoss(nn.Module):
    """Dice Loss - 直接优化IoU"""
    def __init__(self, smooth=1e-6):
        super().__init__()
        self.smooth = smooth

    def forward(self, pred, target):
        pred = torch.sigmoid(pred)
        pred_flat = pred.contiguous().view(-1)
        target_flat = target.contiguous().view(-1)
        intersection = (pred_flat * target_flat).sum()
        union = pred_flat.sum() + target_flat.sum()
        return 1.0 - (2.0 * intersection + self.smooth) / (union + self.smooth)


class FocalLoss(nn.Module):
    """
    Focal Loss - 处理类别不平衡

    功能：降低简单样本的权重，聚焦于难分类样本
    参考：Lin et al. "Focal Loss for Dense Object Detection" (ICCV 2017)

    参数：
        alpha: 平衡因子（处理正负样本不平衡）
        gamma: 聚焦因子（控制难易样本的权重）
    """
    def __init__(self, alpha=0.25, gamma=2.0, reduction='mean'):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, pred, target):
        bce = F.binary_cross_entropy_with_logits(pred, target, reduction='none')
        pt = torch.exp(-bce)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * bce

        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss


class CombinedLoss(nn.Module):
    """
    组合损失函数（V4优化核心）

    组合：BCE + Dice + Focal
    优化策略：
    1. BCE：基础交叉熵损失（带pos_weight处理正样本稀疏）
    2. Dice：直接优化IoU，提高边界精度
    3. Focal：聚焦于难分样本，处理类别不平衡

    权重：
    - BCE: 1.0（基础权重）
    - Dice: 1.5（提高IoU优化权重，参考BIT、ChangeFormer）
    - Focal: 0.5（辅助难样本挖掘，参考Changer）

    参考：
    - BIT (IEEE TGRS 2022): BCE + Dice (1:1)
    - ChangeFormer (IEEE TGRS 2022): BCE + Dice (1:1) + Label Smoothing
    - Changer (CVPR 2023): BCE + Dice + Focal (1:1:0.5)
    - TinyCD (2024): BCE + Dice (1:1) + MixUp
    """
    def __init__(self, pos_weight=3.0, bce_weight=1.0, dice_weight=1.5, focal_weight=0.5, focal_alpha=0.25, focal_gamma=2.0):
        super().__init__()
        self.pos_weight = pos_weight
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight
        self.focal_weight = focal_weight

        # BCE with pos_weight（处理正样本稀疏）
        self.bce_loss = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight]))

        # Dice Loss
        self.dice_loss = DiceLoss(smooth=1e-6)

        # Focal Loss
        self.focal_loss = FocalLoss(alpha=focal_alpha, gamma=focal_gamma, reduction='mean')

    def forward(self, pred, target):
        # 计算各项损失
        bce = self.bce_loss(pred, target)
        dice = self.dice_loss(pred, target)
        focal = self.focal_loss(pred, target)

        # 组合损失
        total_loss = (self.bce_weight * bce +
                     self.dice_weight * dice +
                     self.focal_weight * focal)

        return total_loss


# ==================== Data Augmentation（数据增强）====================

class V4DataAugmentation:
    """
    V4增强数据增强策略

    新增增强（相比V3）：
    1. CutMix：区域级别的增强，提高模型鲁棒性
    2. MixUp + CutMix交替：避免单一增强策略的过拟合
    3. 更强的颜色变换

    参考：
    - TinyCD (2024): MixUp + CutMix 组合策略
    - Changer (CVPR 2023): 强数据增强策略
    """
    def __init__(self, mixup_alpha=0.4, mixup_prob=0.5, cutmix_alpha=1.0, cutmix_prob=0.3):
        self.mixup_alpha = mixup_alpha
        self.mixup_prob = mixup_prob
        self.cutmix_alpha = cutmix_alpha
        self.cutmix_prob = cutmix_prob

    def mixup_data(self, x, y):
        """MixUp数据增强"""
        if self.mixup_alpha > 0:
            lam = np.random.beta(self.mixup_alpha, self.mixup_alpha)
        else:
            lam = 1

        batch_size = x.size()[0]
        index = torch.randperm(batch_size).to(x.device)

        mixed_x = lam * x + (1 - lam) * x[index, :]
        mixed_y = lam * y + (1 - lam) * y[index, :]

        return mixed_x, mixed_y

    def cutmix_data(self, x, y):
        """CutMix数据增强"""
        batch_size = x.size()[0]
        lam = np.random.beta(self.cutmix_alpha, self.cutmix_alpha)

        # 选择随机索引
        index = torch.randperm(batch_size).to(x.device)

        # 计算CutMix区域
        _, _, H, W = x.shape
        cut_rat = np.sqrt(1.0 - lam)
        cut_w = int(W * cut_rat)
        cut_h = int(H * cut_rat)

        # 随机选择CutMix位置
        cx = np.random.randint(W)
        cy = np.random.randint(H)

        bbx1 = np.clip(cx - cut_w // 2, 0, W)
        bby1 = np.clip(cy - cut_h // 2, 0, H)
        bbx2 = np.clip(cx + cut_w // 2, 0, W)
        bby2 = np.clip(cy + cut_h // 2, 0, H)

        # 应用CutMix
        mixed_x = x.clone()
        mixed_x[:, :, bby1:bby2, bbx1:bbx2] = x[index, :, bby1:bby2, bbx1:bbx2]

        # 调整标签
        lam = 1 - ((bbx2 - bbx1) * (bby2 - bby1) / (W * H))
        mixed_y = lam * y + (1 - lam) * y[index, :]

        return mixed_x, mixed_y

    def apply(self, x, y):
        """应用增强策略"""
        rand_val = np.random.random()

        if rand_val < self.mixup_prob:
            # 优先使用MixUp
            return self.mixup_data(x, y)
        elif rand_val < self.mixup_prob + self.cutmix_prob:
            # 其次使用CutMix
            return self.cutmix_data(x, y)
        else:
            # 不增强
            return x, y


# ==================== Training Script（完整训练循环）====================

class SwinTrainerV4:
    """
    V4训练器：优化版本

    主要优化：
    1. 组合损失函数（BCE + Dice + Focal）
    2. 增强数据增强（MixUp + CutMix）
    3. 优化学习率策略
    4. 增强正则化
    """

    def __init__(self, args):
        self.args = args
        self.device = torch.device(args.device)
        self.start_epoch = 0
        self.best_f1 = 0.0
        self.global_step = 0

        # 创建日志目录
        self.log_dir = Path(args.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir = Path(args.checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # 日志文件
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"train_{timestamp}.log"

        # 创建模型
        self.model = self._build_model()

        # 加载预训练backbone（如果指定）
        if args.use_pretrained_backbone and args.pretrained_path:
            self._load_pretrained_backbone(args.pretrained_path)

        # 创建数据加载器（带label smoothing）
        self.train_loader, self.val_loader = self._build_dataloaders()

        # 创建优化器
        self.optimizer = self._build_optimizer()

        # 创建学习率调度器
        self.scheduler = self._build_scheduler()

        # V4组合损失函数
        self.criterion = CombinedLoss(
            pos_weight=args.pos_weight,
            bce_weight=args.bce_weight,
            dice_weight=args.dice_weight,
            focal_weight=args.focal_weight,
            focal_alpha=args.focal_alpha,
            focal_gamma=args.focal_gamma
        ).to(self.device)

        # V4数据增强
        self.augmentor = V4DataAugmentation(
            mixup_alpha=args.mixup_alpha,
            mixup_prob=args.mixup_prob,
            cutmix_alpha=args.cutmix_alpha,
            cutmix_prob=args.cutmix_prob
        )

        # 混合精度训练
        self.scaler = GradScaler() if args.use_amp else None

        # 评估指标
        self.metrics = MetricsCalculator()

        # 加载checkpoint（续训）
        if args.resume:
            self._load_checkpoint(args.resume, reset_optimizer=args.reset_optimizer)

    def _build_model(self):
        """创建模型"""
        print("\n创建RCMT-V4-Swin-Temporal模型...")
        model = RCMT_V4_Swin_Temporal(
            in_channels=3,
            num_classes=1,
            embed_dim=self.args.embed_dim,
            depths=self.args.depths,
            num_heads=self.args.num_heads,
            window_size=self.args.window_size,
            use_temporal_fusion=self.args.use_temporal_fusion,
            drop_path_rate=self.args.drop_path,
            use_checkpoint=self.args.use_checkpoint,
        )

        model = model.to(self.device)
        total_params = sum(p.numel() for p in model.parameters())
        print(f"模型参数: {total_params:,}")

        return model

    def _load_pretrained_backbone(self, pretrained_path):
        """加载预训练backbone"""
        print(f"\n加载预训练backbone: {pretrained_path}")
        checkpoint = torch.load(pretrained_path, map_location=self.device)

        # 提取backbone权重
        if 'model' in checkpoint:
            pretrained_dict = checkpoint['model']
        else:
            pretrained_dict = checkpoint

        # 过滤backbone权重
        backbone_dict = {}
        for k, v in pretrained_dict.items():
            if k.startswith('backbone.'):
                backbone_dict[k] = v
            elif not k.startswith('decoder.') and not k.startswith('seg_head.') and not k.startswith('temporal_fusions.'):
                # 可能是backbone的权重（没有前缀）
                backbone_dict[f'backbone.{k}'] = v

        # 加载权重
        missing, unexpected = self.model.load_state_dict(backbone_dict, strict=False)
        print(f"✅ 预训练backbone加载完成")
        print(f"  缺失的键: {len(missing)}")
        print(f"  意外的键: {len(unexpected)}")

    def _build_dataloaders(self):
        """创建数据加载器（带label smoothing）"""
        print("\n创建数据加载器...")
        train_loader, val_loader = create_dataloaders(
            data_root=self.args.data_root,
            batch_size=self.args.batch_size,
            num_workers=self.args.num_workers,
            use_changeformer_format=self.args.use_changeformer_format,
            label_smoothing=self.args.label_smoothing  # V4: Label Smoothing
        )
        print(f"训练集: {len(train_loader.dataset)} 样本")
        print(f"验证集: {len(val_loader.dataset)} 样本")
        print(f"Label Smoothing: {self.args.label_smoothing}")
        return train_loader, val_loader

    def _build_optimizer(self):
        """创建优化器"""
        print("\n创建优化器...")
        optimizer = optim.AdamW(
            self.model.parameters(),
            lr=self.args.lr,
            weight_decay=self.args.weight_decay,
            betas=(0.9, 0.999)  # V4: 标准AdamW beta值
        )
        print(f"优化器: AdamW (lr={self.args.lr}, weight_decay={self.args.weight_decay})")
        return optimizer

    def _build_scheduler(self):
        """
        创建学习率调度器（V4优化）

        策略：Cosine Annealing with Warmup
        优化：
        - 增加warmup轮数（5 -> 10 epochs）
        - 调整max_lr（如果需要）
        - 添加min_lr限制

        参考：
        - ChangeFormer: Cosine Annealing with 10-epoch warmup
        - TinyCD: Cosine Annealing with warmup
        """
        print("创建学习率调度器...")
        total_steps = len(self.train_loader) * self.args.epochs // self.args.accumulation_steps
        warmup_steps = len(self.train_loader) * self.args.warmup_epochs // self.args.accumulation_steps  # V4: 可配置warmup轮数

        # Cosine Annealing with Warmup
        def cosine_annealing_with_warmup(step):
            if step < warmup_steps:
                # Warmup: 线性增长
                return (step + 1) / warmup_steps
            else:
                # Cosine Annealing: 余弦衰减
                progress = (step - warmup_steps) / (total_steps - warmup_steps)
                return max(self.args.min_lr, self.args.lr * (0.5 * (1 + np.cos(np.pi * progress))))

        scheduler = optim.lr_scheduler.LambdaLR(
            self.optimizer,
            lr_lambda=cosine_annealing_with_warmup
        )

        print(f"调度器: Cosine Annealing with {self.args.warmup_epochs}-epoch Warmup (V4优化)")
        print(f"  初始LR: {self.args.lr:.6f}")
        print(f"  最小LR: {self.args.min_lr:.6f}")
        print(f"  Warmup步数: {warmup_steps}")
        print(f"  总步数: {total_steps}")
        return scheduler

    def _load_checkpoint(self, checkpoint_path, reset_optimizer=False):
        """加载checkpoint（续训）"""
        print(f"\n加载checkpoint: {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)

        self.model.load_state_dict(checkpoint['model_state_dict'])

        if reset_optimizer:
            print("  ⚠️ 重置优化器和调度器（使用新的学习率策略）")
            self.start_epoch = checkpoint['epoch'] + 1
            self.best_f1 = checkpoint.get('best_f1', 0.0)
            self.global_step = 0
            self.scheduler = self._build_scheduler()
            print(f"  从 Epoch {self.start_epoch} 继续训练（优化器已重置）")
        else:
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
            self.start_epoch = checkpoint['epoch'] + 1
            self.best_f1 = checkpoint.get('best_f1', 0.0)
            self.global_step = checkpoint.get('global_step', 0)
            print(f"✅ 从Epoch {self.start_epoch}恢复训练")
            print(f"  最佳F1: {self.best_f1:.4f}")

    def _save_checkpoint(self, epoch, is_best=False):
        """保存checkpoint"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'best_f1': self.best_f1,
            'global_step': self.global_step,
        }

        # 保存最新checkpoint
        latest_path = self.checkpoint_dir / 'latest_checkpoint.pth'
        torch.save(checkpoint, latest_path)

        # 保存最佳checkpoint
        if is_best:
            best_path = self.checkpoint_dir / 'best_model.pth'
            torch.save(checkpoint, best_path)

    def train_epoch(self, epoch):
        """训练一个epoch"""
        self.model.train()
        self.metrics.reset()
        total_loss = 0.0
        self.optimizer.zero_grad()
        nan_detected = False

        for batch_idx, (images, labels) in enumerate(self.train_loader):
            images = images.to(self.device)
            labels = labels.to(self.device)

            # V4数据增强
            use_augmentation = False
            if self.training and np.random.random() < (self.args.mixup_prob + self.args.cutmix_prob):
                images, labels = self.augmentor.apply(images, labels)
                use_augmentation = True

            # 前向传播（混合精度）
            if self.scaler is not None:
                with autocast(device_type='cuda'):
                    outputs = self.model(images)
                    loss = self.criterion(outputs, labels)
                    loss = loss / self.args.accumulation_steps

                # NaN检测
                if torch.isnan(loss):
                    print(f"⚠️ NaN detected at batch {batch_idx}! Skipping...")
                    nan_detected = True
                    continue

                # 反向传播
                self.scaler.scale(loss).backward()

                # 梯度累积
                if (batch_idx + 1) % self.args.accumulation_steps == 0:
                    # 梯度裁剪
                    if self.args.gradient_clip > 0:
                        self.scaler.unscale_(self.optimizer)
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.args.gradient_clip)

                    # 更新参数
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                    self.optimizer.zero_grad()
                    self.global_step += 1

                    # 更新学习率
                    self.scheduler.step()
            else:
                outputs = self.model(images)
                loss = self.criterion(outputs, labels)
                loss = loss / self.args.accumulation_steps

                # NaN检测
                if torch.isnan(loss):
                    print(f"⚠️ NaN detected at batch {batch_idx}! Skipping...")
                    nan_detected = True
                    continue

                loss.backward()

                if (batch_idx + 1) % self.args.accumulation_steps == 0:
                    if self.args.gradient_clip > 0:
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.args.gradient_clip)

                    self.optimizer.step()
                    self.optimizer.zero_grad()
                    self.global_step += 1

                    # 更新学习率
                    self.scheduler.step()

            total_loss += loss.item() * self.args.accumulation_steps

            # 只在非增强时更新指标（MixUp/CutMix软标签会导致指标不准确）
            if not use_augmentation:
                self.metrics.update(outputs.detach(), labels.detach())

            # 打印进度
            if batch_idx % 50 == 0:
                lr = self.optimizer.param_groups[0]['lr']
                aug_type = "MixUp" if use_augmentation and np.random.random() < self.args.mixup_prob else "CutMix" if use_augmentation else "None"
                print(f"Epoch [{epoch}/{self.args.epochs}] Batch [{batch_idx}/{len(self.train_loader)}] "
                      f"Loss: {loss.item() * self.args.accumulation_steps:.4f} LR: {lr:.6f} Aug: {aug_type}")

        # NaN检测警告
        if nan_detected:
            print(f"\n⚠️⚠️⚠️ 警告：Epoch {epoch} 检测到 NaN！可能需要降低学习率或检查数据。")

        # 计算训练集指标
        train_metrics = self.metrics.compute()

        avg_loss = total_loss / len(self.train_loader)
        return avg_loss, train_metrics

    def validate(self, epoch):
        """验证"""
        self.model.eval()
        self.metrics.reset()
        total_loss = 0.0

        with torch.no_grad():
            for images, labels in self.val_loader:
                images = images.to(self.device)
                labels = labels.to(self.device)

                outputs = self.model(images)
                loss = self.criterion(outputs, labels)
                total_loss += loss.item()

                # 更新指标
                self.metrics.update(outputs, labels)

        # 计算验证集指标
        val_metrics = self.metrics.compute()

        avg_loss = total_loss / len(self.val_loader)

        return avg_loss, val_metrics

    def train(self):
        """完整训练循环"""
        print(f"\n{'='*80}")
        print(f"RCMT-V4 优化训练")
        print(f"{'='*80}")
        print(f"V4优化策略：")
        print(f"  ✅ 组合损失：BCE + Dice + Focal ({self.args.bce_weight}:{self.args.dice_weight}:{self.args.focal_weight})")
        print(f"  ✅ 正样本权重：{self.args.pos_weight}")
        print(f"  ✅ Label Smoothing：{self.args.label_smoothing}")
        print(f"  ✅ 数据增强：MixUp ({self.args.mixup_prob}) + CutMix ({self.args.cutmix_prob})")
        print(f"  ✅ 增强DropPath：{self.args.drop_path}")
        print(f"  ✅ 优化Warmup：{self.args.warmup_epochs} epochs")
        print(f"Epochs: {self.args.epochs}")
        print(f"Batch Size: {self.args.batch_size} (accumulation: {self.args.accumulation_steps})")
        print(f"Effective Batch Size: {self.args.batch_size * self.args.accumulation_steps}")
        print(f"目标: F1 > 0.92, IoU > 0.85")
        print(f"{'='*80}\n")

        for epoch in range(self.start_epoch, self.args.epochs):
            print(f"\n{'#'*80}")
            print(f"# Epoch {epoch}/{self.args.epochs}")
            print(f"{'#'*80}")

            # 训练
            train_loss, train_metrics = self.train_epoch(epoch)
            print(f"\n{'='*80}")
            print(f"Epoch {epoch} Training Done")
            print(f"  Avg Loss: {train_loss:.4f}")
            print(f"  F1: {train_metrics['f1']:.4f} | IoU: {train_metrics['iou']:.4f} | OA: {train_metrics['oa']:.4f}")
            print(f"{'='*80}")

            # 验证
            val_loss, val_metrics = self.validate(epoch)
            print(f"\n{'='*80}")
            print(f"Epoch {epoch} Validation:")
            print(f"  Val Loss: {val_loss:.4f}")
            print(f"  Precision: {val_metrics['precision']:.4f}")
            print(f"  Recall: {val_metrics['recall']:.4f}")
            print(f"  F1: {val_metrics['f1']:.4f}")
            print(f"  IoU: {val_metrics['iou']:.4f}")
            print(f"  OA: {val_metrics['oa']:.4f}")
            print(f"{'='*80}")

            # 保存checkpoint
            is_best = val_metrics['f1'] > self.best_f1
            if is_best:
                self.best_f1 = val_metrics['f1']
                print(f"\n*** New Best Model! F1: {self.best_f1:.4f} ***\n")

            self._save_checkpoint(epoch, is_best)

        print(f"\n{'='*80}")
        print(f"训练完成！")
        print(f"最佳F1: {self.best_f1:.4f}")
        print(f"{'='*80}\n")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='RCMT-V4-Swin-Temporal 优化训练')

    # 数据配置
    parser.add_argument('--data-root', type=str, default='/home/developer/workspace/datasets/LEVIR-CD256')
    parser.add_argument('--use-changeformer-format', action='store_true', default=True)
    parser.add_argument('--batch-size', type=int, default=1, help='batch size（建议1以节省显存）')
    parser.add_argument('--accumulation-steps', type=int, default=16, help='梯度累积步数')
    parser.add_argument('--num-workers', type=int, default=4)

    # V4: Label Smoothing
    parser.add_argument('--label-smoothing', type=float, default=0.05, help='Label Smoothing因子（0=不使用）')

    # 模型配置
    parser.add_argument('--embed-dim', type=int, default=96)
    parser.add_argument('--depths', type=int, nargs='+', default=[2, 2, 6, 2])
    parser.add_argument('--num-heads', type=int, nargs='+', default=[3, 6, 12, 24])
    parser.add_argument('--window-size', type=int, default=7)
    parser.add_argument('--use-temporal-fusion', action='store_true', default=True)
    parser.add_argument('--drop-path', type=float, default=0.3, help='V4: 增强DropPath率（0.2->0.3）')
    parser.add_argument('--use-checkpoint', action='store_true', default=True)

    # 训练配置
    parser.add_argument('--epochs', type=int, default=300)
    parser.add_argument('--lr', type=float, default=0.0001)
    parser.add_argument('--min-lr', type=float, default=1e-6, help='V4: 最小学习率')
    parser.add_argument('--weight-decay', type=float, default=0.05)
    parser.add_argument('--gradient-clip', type=float, default=1.0)

    # V4: Warmup配置
    parser.add_argument('--warmup-epochs', type=int, default=10, help='V4: Warmup轮数（5->10）')

    # V4: 损失函数配置
    parser.add_argument('--pos-weight', type=float, default=3.0, help='V4: 正样本权重（处理类别不平衡）')
    parser.add_argument('--bce-weight', type=float, default=1.0, help='BCE损失权重')
    parser.add_argument('--dice-weight', type=float, default=1.5, help='V4: Dice损失权重（1.0->1.5）')
    parser.add_argument('--focal-weight', type=float, default=0.5, help='V4: Focal损失权重（新增）')
    parser.add_argument('--focal-alpha', type=float, default=0.25, help='Focal Loss的alpha参数')
    parser.add_argument('--focal-gamma', type=float, default=2.0, help='Focal Loss的gamma参数')

    # V4: 数据增强配置
    parser.add_argument('--mixup-alpha', type=float, default=0.4)
    parser.add_argument('--mixup-prob', type=float, default=0.5)
    parser.add_argument('--cutmix-alpha', type=float, default=1.0, help='V4: CutMix alpha参数')
    parser.add_argument('--cutmix-prob', type=float, default=0.3, help='V4: CutMix概率')

    # 续训和预训练
    parser.add_argument('--resume', type=str, default=None, help='续训checkpoint路径')
    parser.add_argument('--reset-optimizer', action='store_true', default=False, help='重置优化器')
    parser.add_argument('--use-pretrained-backbone', action='store_true', default=False)
    parser.add_argument('--pretrained-path', type=str, default=None)

    # 其他配置
    parser.add_argument('--device', type=str, default='cuda')
    parser.add_argument('--log-dir', type=str, default='./logs_swin_v4', help='V4日志目录')
    parser.add_argument('--checkpoint-dir', type=str, default='./checkpoints_swin_v4', help='V4 checkpoint目录')
    parser.add_argument('--use-amp', action='store_true', default=True)

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    print(f"\n{'='*80}")
    print(f"RCMT-V4-Swin-Temporal 优化训练")
    print(f"{'='*80}")
    print(f"V4优化亮点：")
    print(f"  ✅ 组合损失：BCE + Dice + Focal（参考BIT、ChangeFormer、Changer）")
    print(f"  ✅ 增强正则化：Label Smoothing + DropPath提升")
    print(f"  ✅ 强数据增强：MixUp + CutMix（参考TinyCD）")
    print(f"  ✅ 优化学习率：Cosine Annealing + 增强Warmup")
    print(f"  ✅ 类别平衡：正样本权重优化")
    print(f"目标性能: F1 > 0.92, IoU > 0.85")
    print(f"{'='*80}\n")

    # 创建训练器
    trainer = SwinTrainerV4(args)

    # 开始训练
    trainer.train()


if __name__ == '__main__':
    main()
