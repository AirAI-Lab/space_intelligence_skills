"""
AutoTrain - 自动化训练
参考: https://docs.ultralytics.com/modes/train/
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import yaml

from .trainer import YOLOTrainer
from .config import TrainingConfig

logger = logging.getLogger(__name__)


class AutoTrainer:
    """自动化训练器 - 实现端到端的自动化训练流程"""

    # 任务类型到模型的映射
    TASK_MODEL_MAP = {
        "detect": "yolov8n.pt",
        "classify": "yolov8n-cls.pt",
        "segment": "yolov8n-seg.pt",
        "pose": "yolov8n-pose.pt"
    }

    # 默认超参数搜索空间
    DEFAULT_SEARCH_SPACE = {
        "lr0": (1e-5, 1e-2),
        "lrf": (0.01, 1.0),
        "momentum": (0.6, 0.98),
        "weight_decay": (1e-5, 1e-2),
        "warmup_epochs": (1, 5),
        "box": (1.0, 20.0),
        "cls": (0.2, 10.0),
        "hsv_h": (0.0, 0.02),
        "hsv_s": (0.0, 0.9),
        "hsv_v": (0.0, 0.9),
        "degrees": (0.0, 30.0),
        "translate": (0.0, 0.2),
        "scale": (0.1, 2.0),
        "shear": (0.0, 15.0),
        "perspective": (0.0, 0.001),
        "flipud": (0.0, 1.0),
        "fliplr": (0.0, 1.0),
        "mosaic": (0.0, 1.0),
        "mixup": (0.0, 1.0),
    }

    def __init__(self, config: TrainingConfig, trainer: YOLOTrainer):
        """
        初始化AutoTrainer

        Args:
            config: 训练配置
            trainer: YOLO训练器实例
        """
        self.config = config
        self.trainer = trainer

    def auto_train(
        self,
        job_id: str,
        dataset_id: str,
        task_type: str = "detect",
        optimization_target: str = "map50_95",
        max_epochs: int = 100,
        max_trials: int = 10,
        quick_test: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        AutoTrain 主流程

        步骤：
        1. 数据验证
        2. 模型选择（基于任务类型）
        3. 超参数搜索
        4. 完整训练
        5. 结果验证

        Args:
            job_id: 训练任务ID
            dataset_id: 数据集ID
            task_type: 任务类型 (detect/classify/segment/pose)
            optimization_target: 优化目标 (map50_95/map50/precision/recall)
            max_epochs: 最大训练轮次
            max_trials: 超参数搜索试验次数
            quick_test: 是否快速测试模式（减少训练轮次用于验证）

        Returns:
            训练结果字典
        """
        logger.info(f"启动 AutoTrain: job_id={job_id}, task={task_type}, target={optimization_target}")

        # 1. 验证数据集
        dataset_path = self._validate_dataset(dataset_id)
        logger.info(f"数据集验证通过: {dataset_path}")

        # 2. 选择基础模型
        base_model = self._select_base_model(task_type)
        logger.info(f"选择基础模型: {base_model}")

        # 3. 超参数搜索
        logger.info(f"开始超参数搜索，最多 {max_trials} 次试验")
        best_params = self._hyperparameter_search(
            job_id=job_id,
            dataset_id=dataset_id,
            dataset_path=dataset_path,
            base_model=base_model,
            optimization_target=optimization_target,
            n_trials=max_trials,
            max_epochs=max_epochs,
            quick_test=quick_test
        )
        logger.info(f"最佳超参数: {best_params}")

        # 4. 使用最佳参数完整训练
        final_job_id = f"{job_id}_final"
        logger.info(f"开始最终训练: {final_job_id}")

        # 合并最佳参数和用户提供的额外参数
        final_params = {**best_params, **kwargs}

        result = self.trainer.start_training(
            job_id=final_job_id,
            dataset_id=dataset_id,
            epochs=max_epochs,
            batch_size=final_params.pop('batch_size', 16),
            img_size=final_params.pop('img_size', 640),
            use_gpu=final_params.pop('use_gpu', True),
            base_model=base_model,
            hyperparameters=final_params
        )

        # 5. 返回结果
        return {
            'job_id': final_job_id,
            'base_model': base_model,
            'best_params': best_params,
            'status': result.get('status', 'running')
        }

    def _validate_dataset(self, dataset_id: str) -> Path:
        """
        验证数据集格式

        检查：
        - data.yaml 是否存在
        - 图像目录是否存在
        - 标注目录是否存在
        - 数据格式是否正确
        """
        dataset_path = self.config.get_dataset_path(dataset_id)

        # 检查 data.yaml
        data_yaml = dataset_path / "data.yaml"
        if not data_yaml.exists():
            raise FileNotFoundError(f"data.yaml not found in {dataset_path}")

        # 验证 YAML 格式
        try:
            with open(data_yaml, 'r') as f:
                data_config = yaml.safe_load(f)

            required_keys = ['path', 'train', 'val']
            for key in required_keys:
                if key not in data_config:
                    raise ValueError(f"Missing required key '{key}' in data.yaml")

            # 验证路径
            train_path = dataset_path.parent / data_config['train'] if not Path(data_config['train']).is_absolute() else Path(data_config['train'])
            val_path = dataset_path.parent / data_config['val'] if not Path(data_config['val']).is_absolute() else Path(data_config['val'])

            if not train_path.exists():
                logger.warning(f"训练路径不存在: {train_path}")
            if not val_path.exists():
                logger.warning(f"验证路径不存在: {val_path}")

            logger.info(f"数据集验证通过: {data_config.get('nc', 'unknown')} 类")

        except Exception as e:
            raise ValueError(f"数据集配置验证失败: {e}")

        return dataset_path

    def _select_base_model(self, task_type: str) -> str:
        """根据任务类型选择基础模型"""
        return self.TASK_MODEL_MAP.get(task_type, "yolov8n.pt")

    def _hyperparameter_search(
        self,
        job_id: str,
        dataset_id: str,
        dataset_path: Path,
        base_model: str,
        optimization_target: str,
        n_trials: int,
        max_epochs: int,
        quick_test: bool
    ) -> Dict[str, Any]:
        """
        超参数搜索

        使用网格搜索或随机搜索（如果Optuna不可用）
        """
        try:
            import optuna
            return self._optuna_search(
                job_id, dataset_id, base_model, optimization_target,
                n_trials, max_epochs, quick_test
            )
        except ImportError:
            logger.warning("Optuna未安装，使用默认参数")
            return self._get_default_hyperparameters()

    def _optuna_search(
        self,
        job_id: str,
        dataset_id: str,
        base_model: str,
        optimization_target: str,
        n_trials: int,
        max_epochs: int,
        quick_test: bool
    ) -> Dict[str, Any]:
        """使用Optuna进行超参数搜索"""
        import optuna

        def objective(trial):
            # 从搜索空间采样
            params = {}
            for param_name, (low, high) in self.DEFAULT_SEARCH_SPACE.items():
                if isinstance(low, int) and isinstance(high, int):
                    params[param_name] = trial.suggest_int(param_name, low, high)
                else:
                    params[param_name] = trial.suggest_float(param_name, low, high)

            # 快速测试模式：使用较少的轮次
            trial_epochs = min(20, max_epochs) if quick_test else max_epochs

            # 执行训练
            trial_job_id = f"{job_id}_trial_{trial.number}"
            try:
                self.trainer.start_training(
                    job_id=trial_job_id,
                    dataset_id=dataset_id,
                    epochs=trial_epochs,
                    batch_size=params.pop('batch_size', 16),
                    img_size=params.pop('img_size', 640),
                    use_gpu=params.pop('use_gpu', True),
                    base_model=base_model,
                    hyperparameters=params
                )

                # 等待训练完成
                import time
                max_wait = 3600 if quick_test else 7200  # 1-2小时超时
                start_wait = time.time()

                while time.time() - start_wait < max_wait:
                    status = self.trainer.get_status(trial_job_id)
                    if status['status'] in ['completed', 'failed', 'cancelled']:
                        break
                    time.sleep(10)

                # 获取结果
                result = self.trainer.get_status(trial_job_id)
                if result['status'] == 'completed':
                    # 返回优化目标值
                    return result.get('metrics', {}).get(optimization_target, 0.0)
                else:
                    return 0.0

            except Exception as e:
                logger.warning(f"试验 {trial.number} 失败: {e}")
                return 0.0

        # 创建研究并优化
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

        logger.info(f"最佳参数: {study.best_params}")
        logger.info(f"最佳得分: {study.best_value}")

        return study.best_params

    def _get_default_hyperparameters(self) -> Dict[str, Any]:
        """获取默认超参数"""
        return {
            'lr0': 0.01,
            'lrf': 0.01,
            'momentum': 0.937,
            'weight_decay': 0.0005,
            'warmup_epochs': 3.0,
            'box': 7.5,
            'cls': 0.5,
            'hsv_h': 0.015,
            'hsv_s': 0.7,
            'hsv_v': 0.4,
            'degrees': 0.0,
            'translate': 0.1,
            'scale': 0.5,
            'shear': 0.0,
            'perspective': 0.0,
            'flipud': 0.0,
            'fliplr': 0.5,
            'mosaic': 1.0,
            'mixup': 0.0,
        }
