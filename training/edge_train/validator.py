"""
高级验证与可视化
参考: https://docs.ultralytics.com/modes/val/
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


class AdvancedValidator:
    """高级验证器 - 生成详细的验证结果和可视化"""

    def __init__(self, config):
        """
        初始化验证器

        Args:
            config: TrainingConfig 实例
        """
        self.config = config

    def validate_and_visualize(
        self,
        model_path: Path,
        dataset_path: Path,
        output_dir: Path,
        task_type: str = "detect"
    ) -> Dict[str, Any]:
        """
        执行验证并生成可视化

        生成内容：
        1. 混淆矩阵
        2. PR曲线
        3. F1置信度曲线
        4. 验证结果预测图
        5. 详细指标JSON

        Args:
            model_path: 模型文件路径
            dataset_path: 数据集路径
            output_dir: 输出目录
            task_type: 任务类型

        Returns:
            验证结果字典
        """
        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError("Ultralytics 未安装")

        logger.info(f"开始验证: model={model_path}, dataset={dataset_path}")

        # 加载模型
        model = YOLO(str(model_path))

        # 创建输出目录
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 执行验证
        data_yaml = dataset_path / "data.yaml"
        results = model.val(
            data=str(data_yaml),
            project=str(output_dir),
            name="validation",
            exist_ok=True,
            plots=True,  # 自动生成图表
            save_json=True  # 保存JSON结果
        )

        # 提取指标
        metrics_dict = self._extract_metrics(results, task_type)

        # 生成额外可视化
        confusion_matrix_path = self._plot_confusion_matrix(
            results, output_dir / "confusion_matrix.png"
        )
        metrics_dict["confusion_matrix_path"] = str(confusion_matrix_path)

        pr_curve_path = self._plot_pr_curve(
            results, output_dir / "pr_curve.png"
        )
        metrics_dict["pr_curve_path"] = str(pr_curve_path)

        # 保存详细指标
        metrics_path = output_dir / "metrics.json"
        self._save_detailed_metrics(results, metrics_path)
        metrics_dict["metrics_path"] = str(metrics_path)

        logger.info(f"验证完成: mAP50-95={metrics_dict.get('map50_95', 0):.4f}")

        return metrics_dict

    def _extract_metrics(self, results, task_type: str) -> Dict[str, Any]:
        """从验证结果中提取指标"""
        metrics = {}

        if task_type == "detect":
            # 目标检测指标
            metrics["map50"] = float(results.box.map50)
            metrics["map50_95"] = float(results.box.map)
            metrics["precision"] = float(results.box.mp)
            metrics["recall"] = float(results.box.mr)

            # 计算F1分数
            p = metrics["precision"]
            r = metrics["recall"]
            metrics["f1"] = float(2 * p * r / (p + r)) if (p + r) > 0 else 0.0

            # 每个类别的AP
            if hasattr(results.box, 'maps'):
                metrics["maps_per_class"] = [float(m) for m in results.box.maps]

        elif task_type == "classify":
            # 分类指标
            metrics["accuracy"] = float(results.top1)
            metrics["accuracy_top5"] = float(results.top5)

        elif task_type == "segment":
            # 分割指标
            metrics["map50"] = float(results.box.map50)
            metrics["map50_95"] = float(results.box.map)
            metrics["mask_map"] = float(results.masks.map)

        return metrics

    def _plot_confusion_matrix(
        self,
        results,
        output_path: Path
    ) -> Path:
        """绘制并保存混淆矩阵"""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
        except ImportError:
            logger.warning("matplotlib 或 seaborn 未安装，跳过混淆矩阵绘制")
            return output_path

        try:
            # 获取混淆矩阵
            if hasattr(results, 'confusion_matrix'):
                cm = results.confusion_matrix.matrix
            else:
                logger.warning("验证结果中没有混淆矩阵数据")
                return output_path

            # 归一化
            cm_normalized = cm.astype('float') / (
                cm.sum(axis=1)[:, np.newaxis] + 1e-10
            )

            # 绘制
            plt.figure(figsize=(12, 10))

            sns.heatmap(
                cm_normalized,
                annot=True,
                fmt='.2%',
                cmap='Blues',
                xticklabels=[f"Class {i}" for i in range(cm.shape[0])],
                yticklabels=[f"Class {i}" for i in range(cm.shape[0])],
                cbar_kws={'label': 'Normalized Count'}
            )

            plt.title('Normalized Confusion Matrix', fontsize=16)
            plt.ylabel('True Label', fontsize=12)
            plt.xlabel('Predicted Label', fontsize=12)
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()

            logger.info(f"混淆矩阵已保存: {output_path}")

        except Exception as e:
            logger.error(f"绘制混淆矩阵失败: {e}")

        return output_path

    def _plot_pr_curve(
        self,
        results,
        output_path: Path
    ) -> Path:
        """绘制并保存PR曲线"""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib 未安装，跳过PR曲线绘制")
            return output_path

        try:
            plt.figure(figsize=(10, 8))

            # 获取precision和recall数据
            if hasattr(results, 'curves') and results.curves:
                # 使用 Ultralytics 结果中的曲线数据
                curves = results.curves
                precision = curves.get('precision', [])
                recall = curves.get('recall', [])
            else:
                # 从 metrics 中提取
                precision = []
                recall = []

            # 绘制每个类别的PR曲线
            for i in range(len(precision)):
                plt.plot(
                    recall[i],
                    precision[i],
                    linewidth=2,
                    label=f"Class {i}"
                )

            plt.xlabel('Recall', fontsize=12)
            plt.ylabel('Precision', fontsize=12)
            plt.title('Precision-Recall Curve', fontsize=16)
            plt.legend(loc='lower left')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()

            logger.info(f"PR曲线已保存: {output_path}")

        except Exception as e:
            logger.error(f"绘制PR曲线失败: {e}")

        return output_path

    def _save_detailed_metrics(
        self,
        results,
        output_path: Path
    ):
        """保存详细指标到JSON文件"""
        try:
            detailed_metrics = {}

            # 基础指标
            if hasattr(results, 'box'):
                box = results.box
                detailed_metrics["map50"] = float(box.map50)
                detailed_metrics["map50_95"] = float(box.map)
                detailed_metrics["precision"] = float(box.mp)
                detailed_metrics["recall"] = float(box.mr)
                detailed_metrics["f1"] = float(
                    2 * box.mp * box.mr / (box.mp + box.mr)
                ) if (box.mp + box.mr) > 0 else 0.0

                # 每个类别的指标
                if hasattr(box, 'maps'):
                    detailed_metrics["maps_per_class"] = {
                        f"class_{i}": float(m) for i, m in enumerate(box.maps)
                    }
                if hasattr(box, 'p'):
                    detailed_metrics["precision_per_class"] = {
                        f"class_{i}": float(p) for i, p in enumerate(box.p)
                    }
                if hasattr(box, 'r'):
                    detailed_metrics["recall_per_class"] = {
                        f"class_{i}": float(r) for i, r in enumerate(box.r)
                    }

            # 分割指标
            if hasattr(results, 'masks'):
                detailed_metrics["mask_map"] = float(results.masks.map)

            # 保存
            with open(output_path, 'w') as f:
                json.dump(detailed_metrics, f, indent=2)

            logger.info(f"详细指标已保存: {output_path}")

        except Exception as e:
            logger.error(f"保存详细指标失败: {e}")


def validate_model(
    config,
    model_path: Path,
    dataset_path: Path,
    output_dir: Optional[Path] = None,
    task_type: str = "detect"
) -> Dict[str, Any]:
    """
    验证模型的便捷函数

    Args:
        config: TrainingConfig 实例
        model_path: 模型文件路径
        dataset_path: 数据集路径
        output_dir: 输出目录（可选）
        task_type: 任务类型

    Returns:
        验证结果字典
    """
    validator = AdvancedValidator(config)

    if output_dir is None:
        output_dir = model_path.parent / "validation"

    return validator.validate_and_visualize(
        model_path=model_path,
        dataset_path=dataset_path,
        output_dir=output_dir,
        task_type=task_type
    )
