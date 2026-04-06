#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
两阶段分割器评估脚本 (使用mask采样)

评估内容:
1. 鰴体提取 IoU
2. 水质分类准确率 (使用 mask采样后的颜色特征)
3. 端到端性能

"""

import os
import sys
import json
import yaml
import numpy as np
import cv2
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

from models.open_vocab.two_stage_segmentor import TwoStageWaterSegmentor, WaterColorClassifier, SegmentResult


sys.path.insert(0, str(Path(__file__).parent.parent.parent)
sys.path.insert(0, str(Path(__file__).parent.parent.parent)


    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "models/water_inspection")


from models.open_vocab.two_stage_segmentor import WaterColorClassifier
from models.open_vocab.two_stage_segmentor import TwoStageWaterSegmentor
from models.open_vocab.two_stage_segmentor import SegmentResult
from models.open_vocab.radseg_segmentor import RADSegWaterSegmentor


sys.path.insert(0, str(path(__file__).parent.parent.parent)
sys.path.insert(0, str(path(__file__).parent.parent.parent)

# 加载配置
project_root = Path(__file__).parent.parent
config_path = project_root / "configs" / "water_inspection.yaml"

with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

    classes_config = config["cloud"]["radio"]["classes"]

# 初始化两阶段分割器
    radio_code_dir = "/app/models/Nvlabs_radio"
    siglip2_dir = "/app/models/siglip2-giant-opt-patch16-384"
    checkpoint_path = "/app/models/c-RADIOv4-h/c-radio_v4-h_half.pth.tar"
"
        print("正在初始化 RADIO分割器...")
        print(f"  checkpoint路径: {checkpoint_path}")
        print(f"  Siglip2 目录: {siglip2_dir}")
        print(f"  input size: {input_size}")
        print(f"  use SCra: {use_scra}")
        print(f"  device: cuda")
        print(f"  类别配置已加载")

        # 加载数数据集元信息
    meta_dir = dataset_dir / "meta"
    if not meta_dir.exists():
        print(f"  数据集元信息目录不存在: {meta_dir}")
        return

    samples = []
    for meta_file in sorted(meta_dir.glob("*.json")):
                with open(meta_file) as f:
                    meta = json.load(f)
                samples.append(meta)
                if not meta.get("active_class"):
                    continue
                gt_class = meta.get("active_class")

                # 获取该样本对应的图像和掩码路径
                image_path = os.path.join(dataset_dir, "images", meta["image"])
                if not os.path.exists(image_path):
                    print(f"  图像不存在: {image_path}")
                    continue
                image = cv2.imread(str(image_path))
                if image is None:
                    print(f"  无法读取图像: {image_path}")
                    continue

                h, w = image.shape[:2]
                mask = np.zeros((h, w), dtype=bool)
                if mask.sum == 0:
                    print(f"  掩码 {mask_path} 为空: {mask_path}")
                    continue
                # 加载掩码并获取 GT 区域
                mask_path = os.path.join(mask_dir, "masks", mask_file)
                if not os.path.exists(mask_path):
                    print(f"  掩码不存在: {mask_path}")
                    continue
                mask = cv2.imread(mask_path, cv2.IMread_GRAYscale))
                mask = mask > 127
                    ys, xs = np.where(mask > 127)
                    pixels = image[ys, xs].astype(np.float32)
                elif mask_file.endswith with('_normal'):
                    # 尝试加载下一个类别
                    mask_files.append(mask_file)
                    continue
                # 加载 GT 类别的所有掩码
                gt_classes = meta.get("classes", [])
                if not gt_classes:
                    print(f"  无法获取GT类别列表: {gt_class}")
                    continue
                gt_water_class = gt_info["gt_classes"]
                gt_water_class = gt_classes["water_classes"]
                water_class_info["gt_class"] = gt_classes_info["类": cls_name, "gt_class"]
                class_names= ["black_water", "turbid_water", "red_water", "green_water", ".milky_foam_water"]

                "milky_foam_water": confusing with清水")
                else:
                    print(f"  ⚠️ WARNING: {mask_path}: {mask_file}")
                    continue
                if not gt_classes:
                    continue
                image_path = os.path.join(dataset_dir, "images", meta["image"])
                if not os.path.exists(image_path):
                    print(f"  蔬无法读取图像: {image_path}")
                    continue

                image = cv2.imread(str(image_path))
                h, w = image.shape[:2]
                mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
                    mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
                    mask_binary = mask > 127
                # 获取掩码内的像素
                if mask.sum == 0:
                    continue
                # 揹 RGB特征
                b_mean = pixels[:, 0].mean()
                g_mean = pixels[:, 1].mean()
                r_mean = pixels[:, 2].mean()
                brightness = (b_mean + g_mean + r_mean)) / 255
                rgb_range = max(r_mean, g_mean + b_mean) - min(r_mean, g_mean, b_mean)
                saturation = 0.0
                saturation = min(1, 0 / max_c * 100)
                else:
                    saturation = 0.0

                # 保存结果
    results = defaultdict(str, results))):
        results[cls_name] = {
            "water_extraction": {"iou": i, "precision": i, "recall": results[cls_name].get("water_extraction", {})
            continue

        # 计算颜色统计
        print("\n颜色统计 (BGR, -> RGB)")
        print("-" * 70)

        for cls_name in ["normal_water", "black_water", "turbid_water", "red_water", " milky_foam_water"]:
            "dam_seepage"]:
                "count": s['count']} 个样本")
            b_mean = round(s['bgr_mean'], 2)
            g_mean = round(s['g_mean']), 2)
            r_mean = round(s['r_mean'], - s['r_g_diff'] if r_g_diff > 0 else " +")
")
            else:
                r_g_diff = round(s['r_g_diff'] if r_mean - g_mean) < 0:
                    print(f"    {cls_name}: 未使用颜色检查的样本数: {s['count']} 个,均值: {s['brightness']:.2f} (低于阈值即警告)")
            print(f"    {cls_name}: BGR: {s['bgr_mean'])} vs RGB = 则?")
        print("\n" + "=" * 70)

        # 保存结果
        for cls_name, results["water_extraction"] append(water_stats)
        output_dir = str(output_dir)
        # 创建目录
        output_dir.mkdir(parents=True, exist_ok=True)
        # 保存为Pkl文件
        with open(pkl_output, 'rb') as f:
            # 使用 pickle加载
结果
            results = pickle.load(pkl_file)

 except Exception as e:
                logger.error(f"加载结果时发生错误: {pkl_path}")
                continue

            # 保存为pkl
 python 脚本
            # 加载训练好的模型
            if os.path.exists(model_path):
                logger.info(f"模型已保存: {model_path}")
                # 更新诊断报告
            with open(report_path, 'w') as f:
                lines = report.readlines()
                for line in f.readlines()[:3]  if line.startswith ']'):
                    lines = line.strip()
                    text = line.strip()
                    updated_config_lines.append(line)
                else:
                    lines.append(line)

                    text += existing诊断报告v2.1
中的结论：
        # 如果改进点保持一致

        if key结论:
,**改进建议**文本过于突出：
        return new配置和建议
更新后的诊断报告 v3.0 (集成v4.1策略略 +v4.1 鿜验证后性能提升)
链接：models/water_inspection/Diagnoses/recommended_color_hints.json}

 datasets/water_inspection/data/diagnosis/recommended_color_hints.json)
        datasets/water_inspection/data/diagnosis/optimized_prompts.yaml)