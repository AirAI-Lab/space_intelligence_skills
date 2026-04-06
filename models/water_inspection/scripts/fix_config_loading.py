#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复segmentor.py的配置加载问题

问题: segmentor没有默认的classes_config，导致requested_classes为空
解决: 在__init__中加载默认的7类配置

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import yaml

def fix_segmentor_config():
    """修复segmentor.py的配置加载"""
    segmentor_path = "/app/water_inspection/models/open_vocab/core/segmentor.py"
    prompts_path = "/app/water_inspection/models/open_vocab/prompts/water_quality.yaml"

    with open(segmentor_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 在 __init__ 方法中添加默认配置加载
    old_init_end = """        # 初始化分类器
        self.text_classifier = SigLIP2Classifier(
            backbone=self.backbone,
            temperature=self._get_prompt_temperature(),
            negative_weight=self._get_negative_weight(),
        )

        # 颜色校验器
        self.color_validator = ColorValidator()

        # 后处理参数"""

    new_init_end = """        # 初始化分类器
        self.text_classifier = SigLIP2Classifier(
            backbone=self.backbone,
            temperature=self._get_prompt_temperature(),
            negative_weight=self._get_negative_weight(),
        )

        # 颜色校验器
        self.color_validator = ColorValidator()

        # 加载默认配置（如果未提供）
        if not self.config:
            self._load_default_config()

        # 后处理参数"""

    content = content.replace(old_init_end, new_init_end)

    # 添加 _load_default_config 方法
    old_get_classes = """    def get_classes_config(self) -> Dict[str, dict]:
        \"\"\"获取类别配置\"\"\"
        radio_cfg = self.config.get("cloud", {}).get("radio", {})
        return radio_cfg.get("classes", {})"""

    new_get_classes = """    def _load_default_config(self):
        \"\"\"加载默认的7类水质配置\"\"\"
        # 默认配置文件路径
        prompts_path = Path(__file__).parent.parent / "prompts" / "water_quality.yaml"

        if prompts_path.exists():
            with open(prompts_path, 'r', encoding='utf-8') as f:
                prompts_config = yaml.safe_load(f)

            # 构建 classes_config
            self.config = {
                "cloud": {
                    "radio": {
                        "classes": {
                            cls_name: {
                                "prompts": cfg.get("positive", []),
                                "is_background": cls_name == "normal_water"
                            }
                            for cls_name, cfg in prompts_config.get("water_quality_detection", {}).items()
                        }
                    }
                }
            }
            print(f"  ✓ 加载默认配置: {len(self.config['cloud']['radio']['classes'])} 类")
        else:
            # 硬编码最小配置
            print(f"  ⚠️ 未找到配置文件: {prompts_path}, 使用硬编码配置")
            self.config = {
                "cloud": {
                    "radio": {
                        "classes": {
                            "black_water": {"prompts": ["black water"], "is_background": False},
                            "turbid_water": {"prompts": ["turbid water"], "is_background": False},
                            "red_water": {"prompts": ["red water"], "is_background": False},
                            "green_water": {"prompts": ["green water"], "is_background": False},
                            "milky_foam_water": {"prompts": ["milky water"], "is_background": False},
                            "dam_seepage": {"prompts": ["dam seepage"], "is_background": False},
                            "normal_water": {"prompts": ["normal water"], "is_background": True},
                        }
                    }
                }
            }

    def get_classes_config(self) -> Dict[str, dict]:
        \"\"\"获取类别配置\"\"\"
        radio_cfg = self.config.get("cloud", {}).get("radio", {})
        return radio_cfg.get("classes", {})"""

    content = content.replace(old_get_classes, new_get_classes)

    # 在文件顶部添加Path导入
    if "from pathlib import Path" not in content:
        content = content.replace(
            "from typing import Dict",
            "from pathlib import Path\\nfrom typing import Dict"
        )

    # 在文件顶部添加yaml导入
    if "import yaml" not in content:
        content = content.replace(
            "import logging",
            "import logging\\nimport yaml"
        )

    with open(segmentor_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ segmentor.py 配置加载修复完成")


if __name__ == '__main__':
    print("开始修复segmentor配置加载...")
    print("="*80)

    try:
        fix_segmentor_config()
        print("="*80)
        print("✅ 修复完成！现在可以重新运行评估脚本")
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
