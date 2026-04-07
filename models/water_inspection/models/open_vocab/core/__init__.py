#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水质检测模型核心模块

统一的水质分割器实现，整合了多个先前版本的最佳实践：
- RADSeg风格的对比提示词匹配
- 两阶段分割 (水体定位 + 水质分类)
- 颜色一致性校验
- 多adaptor支持 (SigLIP2, DINOv3, SAM3)

作者: 空中智能体团队
日期: 2026-04-05
"""

from .backbone import RadioBackbone
from .classifier import SigLIP2Classifier, ColorValidator

# 从 radseg_segmentor 导入主分割器
from ..radseg_segmentor import RADSegWaterSegmentor, SegmentResult

# 兼容别名
WaterQualitySegmentor = RADSegWaterSegmentor

__all__ = [
    "RadioBackbone",
    "WaterQualitySegmentor",
    "RADSegWaterSegmentor",
    "SegmentResult",
    "SigLIP2Classifier",
    "ColorValidator",
]
