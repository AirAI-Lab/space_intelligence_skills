#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
合并 prompts.yaml 到 water_inspection.yaml (v3.2.1 混合优化版)
"""
import yaml
from pathlib import Path

# 读取prompts_v3.2.1_optimized.yaml
prompts_file = Path(__file__).parent.parent / "configs" / "prompts_v3.2.1_optimized.yaml"
with open(prompts_file, "r", encoding="utf-8") as f:
    prompts_data = yaml.safe_load(f)

# 读取water_inspection.yaml
config_file = Path(__file__).parent.parent / "configs" / "water_inspection.yaml"
with open(config_file, "r", encoding="utf-8") as f:
    config_data = yaml.safe_load(f)

# 合并prompts到classes
water_quality = prompts_data.get("water_quality_detection", {})

classes_config = config_data["cloud"]["radio"]["classes"]

updated_classes = []
for class_name, class_cfg in classes_config.items():
    if class_name in water_quality:
        # 只替换prompts，保留其他配置如color_hint, min_prob等
        if "positive" in water_quality[class_name]:
            classes_config[class_name]["prompts"] = water_quality[class_name]["positive"]
            updated_classes.append(class_name)

# 保存更新后的配置
with open(config_file, "w", encoding="utf-8") as f:
    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

print(f"[v3.2.1] Updated {len(updated_classes)} classes: {', '.join(updated_classes)}")
