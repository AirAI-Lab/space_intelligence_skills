#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
云端推理插件基类

插件从场景 YAML 配置中动态读取告警规则，替代硬编码 alert_map。
新增场景只需创建 YAML 配置（含 cloud.radio.classes.*.alert），
无需修改任何 Python 代码。

用法:
  from models.cloud_inference.plugin_base import ScenarioPlugin
  plugin = ScenarioPlugin("models/water_inspection/configs/water_inspection.yaml")
  alerts = plugin.generate_alerts(segments)
"""

import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger("radio_server")


class InferencePlugin(ABC):
    """云端推理插件抽象基类"""

    @abstractmethod
    def load_config(self, config_path: str) -> None:
        """加载场景 YAML 配置"""

    @abstractmethod
    def get_classes_config(self) -> dict:
        """返回过滤后的类别配置 (排除 is_background)"""

    @abstractmethod
    def get_thresholds(self) -> tuple:
        """返回 (threshold, min_area)"""

    @abstractmethod
    def get_system_name(self) -> str:
        """返回 system.name"""

    @abstractmethod
    def is_multi_class(self) -> bool:
        """是否多类同时检测模式"""

    @abstractmethod
    def generate_alerts(self, segments: dict, min_area: float = 0.01) -> list:
        """根据分割结果和 YAML 告警规则生成告警"""


class ScenarioPlugin(InferencePlugin):
    """
    通用场景插件：从 YAML 配置中读取所有参数和告警规则。

    支持的 YAML 结构:
      cloud.radio.classes:
        class_name:
          zh: "中文名"
          alert: {enabled: true, level: warning, description: "描述"}
      或:
      deployment.cloud.radio.classes: (同上)

    告警规则直接从每个 class 的 alert 字段读取，不再需要硬编码。
    """

    def __init__(self, config_path: str):
        self.config_path = config_path
        self._config: dict = {}
        self._classes_config: dict = {}
        self._threshold: float = 0.3
        self._min_area: float = 0.01
        self._system_name: str = ""
        self._multi_class: bool = False
        self._alert_rules: dict = {}
        self.load_config(config_path)

    def load_config(self, config_path: str) -> None:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        logger.info("插件加载配置: %s", config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

        # 兼容两种 YAML 结构: cloud.radio 或 deployment.cloud.radio
        radio_config = self._config.get("cloud", {}).get("radio", {})
        if not radio_config.get("classes"):
            radio_config = self._config.get("deployment", {}).get("cloud", {}).get("radio", {})

        raw_classes = radio_config.get("classes", {})
        # 过滤掉 background 类
        self._classes_config = {
            k: v for k, v in raw_classes.items()
            if not v.get("is_background", False)
        }

        # 读取阈值: 优先 inference → model → segmentation
        infer_config = radio_config.get("inference", {}) or radio_config.get("model", {})
        seg_config = radio_config.get("segmentation", {})
        self._threshold = float(infer_config.get("threshold", seg_config.get("threshold", 0.3)))
        self._min_area = float(infer_config.get("min_area", seg_config.get("min_change_area", 0.01)))

        self._system_name = self._config.get("system", {}).get("name", "")
        self._multi_class = self._system_name in ("change_detection",)

        # 从 classes_config 提取告警规则
        self._alert_rules = self._build_alert_rules()

        logger.info("插件就绪: 类别=%s, 阈值=%.2f, 最小面积=%.3f, 多类模式=%s",
                     list(self._classes_config.keys()), self._threshold,
                     self._min_area, self._multi_class)

    def _build_alert_rules(self) -> dict:
        """从每个 class 的 alert 字段构建告警规则映射"""
        rules = {}
        for class_name, class_config in self._classes_config.items():
            alert_cfg = class_config.get("alert", {})
            if alert_cfg.get("enabled", False):
                rules[class_name] = {
                    "level": alert_cfg.get("level", "warning"),
                    "description": alert_cfg.get("description", class_config.get("zh", class_name)),
                }
        logger.info("告警规则: %s", {k: v["level"] for k, v in rules.items()})
        return rules

    def get_classes_config(self) -> dict:
        return self._classes_config

    def get_thresholds(self) -> tuple:
        return self._threshold, self._min_area

    def get_system_name(self) -> str:
        return self._system_name

    def is_multi_class(self) -> bool:
        return self._multi_class

    def get_alert_rules(self) -> dict:
        return self._alert_rules

    def generate_alerts(self, segments: dict, min_area: float = 0.01) -> list:
        """
        根据分割结果和 YAML 告警规则生成告警。

        segments: {"class_name": {"area": 0.15, "score": 0.8, "class_name_cn": "中文名"}}
        min_area: 最小面积阈值 (由调用方传入，通常使用 self._min_area)
        """
        effective_min_area = min_area if min_area > 0 else self._min_area
        alerts = []
        for class_name, info in segments.items():
            area = info.get("area", 0)
            if area < effective_min_area:
                continue

            # 优先从 alert_rules 查找，否则使用默认值
            rule = self._alert_rules.get(class_name)
            if rule:
                level = rule["level"]
                desc = rule["description"]
            else:
                # 该类别没有配置告警规则，跳过不告警
                continue

            alerts.append({
                "class_name": class_name,
                "class_name_cn": info.get("class_name_cn", desc),
                "level": level,
                "message": f"{desc}，面积占比 {area:.1%}",
                "area": area,
            })
        return alerts
