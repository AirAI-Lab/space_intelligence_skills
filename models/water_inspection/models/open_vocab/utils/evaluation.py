#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水质检测评估工具

评估零样本分割器在标注数据集上的性能:
- RADIO 分割 IoU
- 分类准确率
- 颜色分布统计

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import json
import numpy as np
import cv2
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """评估指标"""
    # 分割指标
    iou: float = 0.0
    dice: float = 0.0
    pixel_accuracy: float = 0.0

    # 分类指标
    class_accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0

    # 统计信息
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0


class WaterQualityEvaluator:
    """
    水质检测评估器

    在标注数据集上评估零样本分割器的性能
    """

    # 7 类水质定义
    CLASS_NAMES = [
        "black_water",
        "turbid_water",
        "red_water",
        "green_water",
        "milky_foam_water",
        "dam_seepage",
        "normal_water",
    ]

    def __init__(
        self,
        data_dir: str,
        gt_dir: str,
        meta_path: Optional[str] = None,
    ):
        """
        Args:
            data_dir: 图像数据目录
            gt_dir: GT 掩码目录
            meta_path: 元数据 JSON 路径 (可选)
        """
        self.data_dir = Path(data_dir)
        self.gt_dir = Path(gt_dir)
        self.meta_path = Path(meta_path) if meta_path else None

        # 加载元数据
        self.metadata = {}
        if self.meta_path and self.meta_path.exists():
            with open(self.meta_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)

        # 验证路径
        if not self.data_dir.exists():
            raise ValueError(f"数据目录不存在: {data_dir}")
        if not self.gt_dir.exists():
            raise ValueError(f"GT 目录不存在: {gt_dir}")

        logger.info(f"评估器初始化完成:")
        logger.info(f"  数据目录: {data_dir}")
        logger.info(f"  GT 目录: {gt_dir}")
        logger.info(f"  样本数: {len(list(self.data_dir.glob('*.jpg')))}")

    def evaluate(
        self,
        segmentor,
        classes_config: Dict,
        prompts_config: Optional[Dict] = None,
        max_samples: int = -1,
        save_visualizations: bool = True,
        output_dir: Optional[str] = None,
    ) -> Dict[str, EvaluationMetrics]:
        """
        评估分割器

        Args:
            segmentor: WaterQualitySegmentor 实例
            classes_config: 类别配置
            prompts_config: 提示词配置
            max_samples: 最大评估样本数 (-1 表示全部)
            save_visualizations: 是否保存可视化结果
            output_dir: 可视化输出目录

        Returns:
            {class_name: EvaluationMetrics}
        """
        # 收集图像文件
        image_files = sorted(list(self.data_dir.glob("*.jpg")) +
                            list(self.data_dir.glob("*.png")))

        if max_samples > 0:
            image_files = image_files[:max_samples]

        logger.info(f"开始评估 {len(image_files)} 个样本...")

        # 初始化指标
        metrics = {cls: EvaluationMetrics() for cls in self.CLASS_NAMES}

        # 混淆矩阵
        confusion_matrix = np.zeros((len(self.CLASS_NAMES), len(self.CLASS_NAMES)), dtype=int)

        # 创建输出目录
        if save_visualizations and output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

        # 评估每个样本
        for idx, image_file in enumerate(image_files):
            if (idx + 1) % 10 == 0:
                logger.info(f"  处理 {idx + 1}/{len(image_files)}...")

            # 加载图像
            image = cv2.imread(str(image_file))
            if image is None:
                logger.warning(f"无法加载图像: {image_file}")
                continue

            # 查找对应的 GT 掩码
            gt_file = self._find_gt_file(image_file)
            if gt_file is None:
                logger.warning(f"未找到 GT 掩码: {image_file.stem}")
                continue

            # 加载 GT 掩码
            gt_mask = cv2.imread(str(gt_file), cv2.IMREAD_GRAYSCALE)
            if gt_mask is None:
                logger.warning(f"无法加载 GT 掩码: {gt_file}")
                continue

            # 获取 GT 类别 (从元数据或掩码推断)
            gt_class = self._get_gt_class(image_file.stem, gt_mask)

            # 执行分割
            results = segmentor.segment(
                image,
                classes_config,
                prompts_config=prompts_config,
            )

            # 获取预测类别
            pred_class = "normal_water"
            pred_mask = np.zeros_like(gt_mask, dtype=bool)

            if results:
                pred_class = list(results.keys())[0]
                pred_mask = results[pred_class].mask

            # 更新混淆矩阵
            gt_idx = self.CLASS_NAMES.index(gt_class) if gt_class in self.CLASS_NAMES else -1
            pred_idx = self.CLASS_NAMES.index(pred_class) if pred_class in self.CLASS_NAMES else -1

            if gt_idx >= 0 and pred_idx >= 0:
                confusion_matrix[gt_idx, pred_idx] += 1

            # 计算分割指标
            if gt_class == pred_class:
                iou, dice = self._compute_iou_dice(pred_mask, gt_mask > 0)
                metrics[gt_class].iou += iou
                metrics[gt_class].dice += dice

            # 保存可视化
            if save_visualizations and output_dir:
                vis = segmentor.visualize(image, results)
                vis_path = output_path / f"{image_file.stem}_pred.jpg"
                cv2.imwrite(str(vis_path), vis)

        # 聚合指标
        for cls_name in self.CLASS_NAMES:
            cls_metrics = metrics[cls_name]

            # 从混淆矩阵计算分类指标
            cls_idx = self.CLASS_NAMES.index(cls_name)
            tp = confusion_matrix[cls_idx, cls_idx]
            fp = confusion_matrix[:, cls_idx].sum() - tp
            fn = confusion_matrix[cls_idx, :].sum() - tp
            tn = confusion_matrix.sum() - tp - fp - fn

            cls_metrics.true_positives = int(tp)
            cls_metrics.false_positives = int(fp)
            cls_metrics.true_negatives = int(tn)
            cls_metrics.false_negatives = int(fn)

            # 计算精度/召回/F1
            cls_metrics.precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            cls_metrics.recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            cls_metrics.f1_score = (
                2 * cls_metrics.precision * cls_metrics.recall /
                (cls_metrics.precision + cls_metrics.recall)
                if (cls_metrics.precision + cls_metrics.recall) > 0 else 0.0
            )

            # 平均 IoU/Dice
            count = confusion_matrix[cls_idx, :].sum()
            if count > 0:
                cls_metrics.iou /= count
                cls_metrics.dice /= count

        # 计算总体准确率
        total = confusion_matrix.sum()
        correct = np.diag(confusion_matrix).sum()
        overall_accuracy = correct / total if total > 0 else 0.0

        logger.info(f"评估完成!")
        logger.info(f"  总体准确率: {overall_accuracy:.1%}")
        logger.info(f"  总样本数: {int(total)}")

        return metrics

    def analyze_color_distribution(
        self,
        max_samples: int = -1,
    ) -> Dict[str, Dict[str, float]]:
        """
        分析数据集的颜色分布

        Args:
            max_samples: 最大分析样本数 (-1 表示全部)

        Returns:
            {class_name: {"b_mean": ..., "g_mean": ..., "r_mean": ..., ...}}
        """
        # 收集图像文件
        image_files = sorted(list(self.data_dir.glob("*.jpg")) +
                            list(self.data_dir.glob("*.png")))

        if max_samples > 0:
            image_files = image_files[:max_samples]

        logger.info(f"分析 {len(image_files)} 个样本的颜色分布...")

        # 收集颜色统计
        color_stats = {cls: {"b": [], "g": [], "r": []} for cls in self.CLASS_NAMES}

        for image_file in image_files:
            # 加载图像
            image = cv2.imread(str(image_file))
            if image is None:
                continue

            # 查找 GT 掩码
            gt_file = self._find_gt_file(image_file)
            if gt_file is None:
                continue

            # 加载 GT 掩码
            gt_mask = cv2.imread(str(gt_file), cv2.IMREAD_GRAYSCALE)
            if gt_mask is None:
                continue

            # 获取 GT 类别
            gt_class = self._get_gt_class(image_file.stem, gt_mask)

            if gt_class not in self.CLASS_NAMES:
                continue

            # 计算颜色统计
            mask = gt_mask > 0
            if mask.any():
                pixels = image[mask]
                color_stats[gt_class]["b"].append(pixels[:, 0].mean())
                color_stats[gt_class]["g"].append(pixels[:, 1].mean())
                color_stats[gt_class]["r"].append(pixels[:, 2].mean())

        # 聚合统计
        results = {}
        for cls_name, stats in color_stats.items():
            if stats["b"]:
                results[cls_name] = {
                    "b_mean": float(np.mean(stats["b"])),
                    "g_mean": float(np.mean(stats["g"])),
                    "r_mean": float(np.mean(stats["r"])),
                    "brightness": float(np.mean([np.mean(stats["b"]), np.mean(stats["g"]), np.mean(stats["r"])])),
                    "count": len(stats["b"]),
                }

        logger.info(f"颜色分布分析完成!")
        for cls_name, stats in results.items():
            logger.info(f"  {cls_name}: B={stats['b_mean']:.1f}, G={stats['g_mean']:.1f}, R={stats['r_mean']:.1f} (n={stats['count']})")

        return results

    def _find_gt_file(self, image_file: Path) -> Optional[Path]:
        """查找对应的 GT 掩码文件"""
        stem = image_file.stem

        # 尝试多种命名格式
        candidates = [
            self.gt_dir / f"{stem}.png",
            self.gt_dir / f"{stem}_mask.png",
            self.gt_dir / f"{stem}_gt.png",
            self.gt_dir / f"{stem}.jpg",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

    def _get_gt_class(self, image_stem: str, gt_mask: np.ndarray) -> str:
        """获取 GT 类别"""
        # 首先从元数据查找
        if image_stem in self.metadata:
            return self.metadata[image_stem].get("class", "normal_water")

        # 否则从掩码推断 (需要映射)
        # 这里简化处理, 实际应用中需要根据标注规范实现
        return "normal_water"

    def _compute_iou_dice(
        self,
        pred_mask: np.ndarray,
        gt_mask: np.ndarray,
    ) -> Tuple[float, float]:
        """计算 IoU 和 Dice"""
        intersection = (pred_mask & gt_mask).sum()
        union = (pred_mask | gt_mask).sum()

        iou = intersection / union if union > 0 else 0.0
        dice = 2 * intersection / (pred_mask.sum() + gt_mask.sum()) if (pred_mask.sum() + gt_mask.sum()) > 0 else 0.0

        return iou, dice

    def generate_report(
        self,
        metrics: Dict[str, EvaluationMetrics],
        output_path: str,
    ) -> None:
        """
        生成评估报告

        Args:
            metrics: 评估指标
            output_path: 输出路径 (Markdown 格式)
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 水质检测零样本分割评估报告\n\n")
            f.write("## 评估概览\n\n")
            f.write(f"- 评估日期: {self._get_current_time()}\n")
            f.write(f"- 类别数: {len(self.CLASS_NAMES)}\n")
            f.write(f"- 类别列表: {', '.join(self.CLASS_NAMES)}\n\n")

            f.write("## 分类性能\n\n")
            f.write("| 类别 | 精度 | 召回 | F1 | 样本数 |\n")
            f.write("|------|------|------|----|-----------|\n")

            for cls_name in self.CLASS_NAMES:
                m = metrics[cls_name]
                count = m.true_positives + m.false_negatives
                f.write(f"| {cls_name} | {m.precision:.1%} | {m.recall:.1%} | {m.f1_score:.1%} | {count} |\n")

            f.write("\n## 分割性能\n\n")
            f.write("| 类别 | IoU | Dice |\n")
            f.write("|------|-----|------|\n")

            for cls_name in self.CLASS_NAMES:
                m = metrics[cls_name]
                f.write(f"| {cls_name} | {m.iou:.1%} | {m.dice:.1%} |\n")

            f.write("\n## 建议\n\n")
            f.write("1. 检查低召回类别, 可能需要更多提示词\n")
            f.write("2. 检查低精度类别, 可能需要调整阈值\n")
            f.write("3. 使用颜色分布分析结果优化颜色提示\n")

        logger.info(f"评估报告已保存: {output_path}")

    @staticmethod
    def _get_current_time() -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
