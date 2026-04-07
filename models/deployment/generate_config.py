#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置文件生成工具

功能:
- 生成模型配置 JSON
- 生成类别名称文件
- 生成报警规则

作者: 空中智能体团队
日期: 2026-03-26
"""

import os
import sys
import json
import yaml
import argparse
from pathlib import Path
from typing import Dict, List, Any


def generate_model_config(
    project_name: str,
    config_yaml: str,
    output_dir: str
):
    """
    生成模型配置文件

    Args:
        project_name: 项目名称
        config_yaml: YAML 配置文件路径
        output_dir: 输出目录
    """
    print(f"\n{'='*60}")
    print("生成模型配置")
    print(f"{'='*60}")
    print(f"项目: {project_name}")
    print(f"配置: {config_yaml}")
    print(f"输出: {output_dir}")

    # 加载 YAML 配置
    with open(config_yaml, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 生成模型配置 JSON
    print("\n1. 生成模型配置 JSON...")
    model_config = {
        "model_name": project_name,
        "version": config.get('system', {}).get('version', '1.0'),
        "task_type": "detection",

        "input": {
            "width": config['yolo']['model'].get('input_size', 640),
            "height": config['yolo']['model'].get('input_size', 640),
            "channels": 3,
            "format": "BGR",
            "batch_size": 1
        },

        "output": {
            "type": "detection",
            "num_classes": len(config['yolo']['classes']),
            "format": "YOLOv8"
        },

        "classes": []
    }

    # 添加类别信息
    for class_id, class_info in config['yolo']['classes'].items():
        model_config["classes"].append({
            "id": class_id,
            "name": class_info['name'],
            "zh": class_info['zh']
        })

    # 保存
    json_path = output_path / f"{project_name}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(model_config, f, indent=2, ensure_ascii=False)

    print(f"   ✓ {json_path}")

    # 2. 生成类别名称文件
    print("\n2. 生成类别名称文件...")
    names_path = output_path / f"{project_name}.names"

    with open(names_path, 'w', encoding='utf-8') as f:
        for class_id, class_info in sorted(config['yolo']['classes'].items()):
            f.write(f"{class_info['name']}\n")

    print(f"   ✓ {names_path}")

    # 3. 生成报警规则
    print("\n3. 生成报警规则...")
    rules_config = generate_alert_rules(project_name, config)

    rules_path = output_path / f"{project_name}_rules.json"
    with open(rules_path, 'w', encoding='utf-8') as f:
        json.dump(rules_config, f, indent=2, ensure_ascii=False)

    print(f"   ✓ {rules_path}")

    print(f"\n{'='*60}")
    print("✓ 配置生成完成")
    print(f"{'='*60}\n")

    return {
        "model_config": str(json_path),
        "names_file": str(names_path),
        "rules_file": str(rules_path)
    }


def generate_alert_rules(project_name: str, config: Dict) -> Dict:
    """
    生成报警规则

    Args:
        project_name: 项目名称
        config: YAML 配置

    Returns:
        报警规则配置
    """
    # 通用报警规则模板
    rules = {
        "project": project_name,
        "version": "1.0",
        "rules": []
    }

    # 从 YAML 配置中读取报警配置
    alert_config = config.get('alerts', {})

    # 严重报警
    critical_classes = alert_config.get('critical', {}).get('classes', [])
    if critical_classes:
        rules["rules"].append({
            "name": "critical_alert",
            "level": "critical",
            "classes": critical_classes,
            "actions": ["sound_light", "app_push", "sms"],
            "suppress_seconds": 300
        })

    # 警告
    warning_classes = alert_config.get('warning', {}).get('classes', [])
    if warning_classes:
        rules["rules"].append({
            "name": "warning_alert",
            "level": "warning",
            "classes": warning_classes,
            "actions": ["app_push"],
            "suppress_seconds": 600
        })

    # 信息
    info_classes = alert_config.get('info', {}).get('classes', [])
    if info_classes:
        rules["rules"].append({
            "name": "info_alert",
            "level": "info",
            "classes": info_classes,
            "actions": ["log"],
            "suppress_seconds": 900
        })

    return rules


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="配置文件生成工具")

    parser.add_argument("--project", type=str, required=True,
                       choices=["water_inspection", "park_monitoring", "construction_safety"],
                       help="项目名称")
    parser.add_argument("--config", type=str,
                       help="YAML 配置文件路径（默认: configs/{project}.yaml）")
    parser.add_argument("--output", type=str,
                       default="models",
                       help="输出目录（默认: models）")

    args = parser.parse_args()

    # 配置文件路径
    if args.config:
        config_yaml = args.config
    else:
        # 从项目根目录查找
        possible_paths = [
            f"configs/{args.project}.yaml",
            f"../configs/{args.project}.yaml",
            f"../../configs/{args.project}.yaml"
        ]

        config_yaml = None
        for path in possible_paths:
            if Path(path).exists():
                config_yaml = path
                break

        if not config_yaml:
            print(f"错误: 找不到配置文件 {args.project}.yaml")
            sys.exit(1)

    # 生成配置
    generate_model_config(
        project_name=args.project,
        config_yaml=config_yaml,
        output_dir=args.output
    )


if __name__ == "__main__":
    main()
