#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水质检测开放词汇分割模块

提供统一的水质分割器实现，支持零样本分割和评估。

使用方法:
    from models.open_vocab import WaterQualitySegmentor

    segmentor = WaterQualitySegmentor(config=config)
    results = segmentor.segment(image, classes_config)

作者: 空中智能体团队
日期: 2026-04-05
"""
