#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
提示词模块

包含水质检测的提示词配置。

作者: 空中智能体团队
日期: 2026-04-05
"""

import yaml
from pathlib import Path
from typing import Dict, Optional

# 提示词文件路径
PROMPTS_DIR = Path(__file__).parent
WATER_QUALITY_PROMPTS_PATH = PROMPTS_DIR / "water_quality.yaml"


def load_prompts(config_name: str = "water_quality") -> Optional[Dict]:
    """
    加载提示词配置

    Args:
        config_name: 配置名称 (不含 .yaml 扩展名)

    Returns:
        提示词配置字典
    """
    prompts_path = PROMPTS_DIR / f"{config_name}.yaml"

    if not prompts_path.exists():
        raise FileNotFoundError(f"提示词配置文件不存在: {prompts_path}")

    with open(prompts_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def get_water_quality_prompts() -> Dict:
    """
    获取水质检测提示词

    Returns:
        水质检测提示词配置
    """
    config = load_prompts("water_quality")
    return config.get("water_quality_detection", {})


__all__ = [
    "load_prompts",
    "get_water_quality_prompts",
    "PROMPTS_DIR",
    "WATER_QUALITY_PROMPTS_PATH",
]
