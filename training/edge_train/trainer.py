"""
YOLO 训练器
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import mlflow
import mlflow.pytorch
import requests
from ultralytics import YOLO

from .config import TrainingConfig

logger = logging.getLogger(__name__)


class YOLOTrainer:
    """YOLOv8 训练器"""

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.training_jobs: Dict[str, Dict[str, Any]] = {}
        self.training_threads: Dict[str, threading.Thread] = {}

        # 设置 MLflow
        mlflow.set_tracking_uri(config.mlflow_tracking_uri)
        logger.info(f"MLflow tracking URI: {config.mlflow_tracking_uri}")

    def start_training(
            self,
            job_id: str,
            dataset_id: str,
            epochs: int,
            batch_size: int,
            img_size: int,
            use_gpu: bool,
            base_model: str,
            hyperparameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """启动训练任务"""

        if job_id in self.training_jobs:
            raise ValueError(f"Training job {job_id} already exists")

        # 创建任务记录
        self.training_jobs[job_id] = {
            'job_id': job_id,
            'dataset_id': dataset_id,
            'status': 'running',
            'epoch': 0,
            'progress': 0.0,
            'start_time': time.time(),
            'stop_requested': False
        }

        # 启动训练线程
        thread = threading.Thread(
            target=self._training_worker,
            args=(job_id, dataset_id, epochs, batch_size, img_size, use_gpu, base_model, hyperparameters)
        )
        self.training_threads[job_id] = thread
        thread.start()

        return {
            'job_id': job_id,
            'status': 'running'
        }

    def _training_worker(
            self,
            job_id: str,
            dataset_id: str,
            epochs: int,
            batch_size: int,
            img_size: int,
            use_gpu: bool,
            base_model: str,
            hyperparameters: Dict[str, Any]
    ):
        """训练工作线程"""
        try:
            logger.info(f"开始训练: job_id={job_id}")

            # 从 S3 下载数据集
            dataset_path = self.config.get_dataset_path(dataset_id)
            s3_dataset_key = f"datasets/{dataset_id}/dataset.zip"
            local_zip = dataset_path.parent / f"{dataset_id}.zip"

            if not dataset_path.exists():
                logger.info(f"从 S3 下载数据集: {s3_dataset_key}")
                if self.config.download_from_s3(s3_dataset_key, local_zip):
                    # 解压数据集
                    import zipfile
                    with zipfile.ZipFile(local_zip, 'r') as zip_ref:
                        zip_ref.extractall(dataset_path.parent)
                    os.remove(local_zip)  # 删除压缩包
                    logger.info(f"数据集解压完成: {dataset_path}")
                else:
                    raise FileNotFoundError(f"无法下载数据集: {dataset_id}")

            # 准备输出目录
            output_path = self.config.get_output_path(job_id)
            output_path.mkdir(parents=True, exist_ok=True)

            # 创建 MLflow 实验
            experiment_name = f"yolov8_{dataset_id}"
            mlflow.set_experiment(experiment_name)

            # 开始 MLflow run
            with mlflow.start_run(run_name=job_id) as run:
                mlflow.log_params({
                    'epochs': epochs,
                    'batch_size': batch_size,
                    'img_size': img_size,
                    'base_model': base_model,
                    **hyperparameters
                })

                # 加载基础模型
                model = YOLO(base_model)

                # 训练回调
                def on_train_epoch_end(trainer):
                    epoch = trainer.epoch + 1
                    progress = epoch / epochs

                    # 更新状态
                    self.training_jobs[job_id]['epoch'] = epoch
                    self.training_jobs[job_id]['progress'] = progress

                    # 记录指标
                    metrics = trainer.metrics
                    mlflow.log_metrics({
                        'train_loss': metrics.get('train/loss', 0),
                        'val_loss': metrics.get('val/loss', 0),
                        'map50': metrics.get('metrics/mAP50(B)', 0),
                        'map50_95': metrics.get('metrics/mAP50-95(B)', 0),
                        'precision': metrics.get('metrics/precision(B)', 0),
                        'recall': metrics.get('metrics/recall(B)', 0),
                    }, step=epoch)

                    # 上报进度到后端
                    self._report_progress(job_id, epoch, progress)

                    # 检查是否停止
                    if self.training_jobs[job_id].get('stop_requested'):
                        raise KeyboardInterrupt("Stop requested")

                # 启动训练
                # 注意：这里需要数据集已经准备好 YOLO 格式
                # dataset_path/data.yaml 应该包含数据集配置
                results = model.train(
                    data=str(dataset_path / 'data.yaml'),
                    epochs=epochs,
                    batch=batch_size,
                    imgsz=img_size,
                    device=self.config.device if use_gpu else 'cpu',
                    project=str(output_path),
                    name='train',
                    exist_ok=True,
                    **hyperparameters
                )

                # 保存最佳模型
                best_model_path = output_path / 'train' / 'weights' / 'best.pt'

                # 训练完成
                final_metrics = {
                    'map50_95': results.box.map,
                    'map50': results.box.map50,
                    'precision': results.box.mp,
                    'recall': results.box.mr
                }

                mlflow.log_metrics(final_metrics)

                # 上传模型到 S3
                model_id = "M_" + job_id
                s3_model_key = f"models/{model_id}/best.pt"
                if self.config.upload_to_s3(best_model_path, s3_model_key):
                    logger.info(f"模型已上传到 S3: {s3_model_key}")
                else:
                    logger.warning(f"模型上传到 S3 失败，但训练已完成")

                # 通知后端训练完成
                self._report_completion(job_id, model_id, final_metrics)

                self.training_jobs[job_id]['status'] = 'completed'
                logger.info(f"训练完成: job_id={job_id}, mAP={final_metrics['map50_95']}")

        except KeyboardInterrupt:
            logger.info(f"训练被中断: job_id={job_id}")
            self.training_jobs[job_id]['status'] = 'cancelled'

        except Exception as e:
            logger.error(f"训练失败: job_id={job_id}", exc_info=True)
            self.training_jobs[job_id]['status'] = 'failed'
            self.training_jobs[job_id]['error'] = str(e)
            self._report_failure(job_id, str(e))

    def stop_training(self, job_id: str):
        """停止训练"""
        if job_id not in self.training_jobs:
            raise ValueError(f"Training job {job_id} not found")

        self.training_jobs[job_id]['stop_requested'] = True

    def get_status(self, job_id: str) -> Dict[str, Any]:
        """获取训练状态"""
        if job_id not in self.training_jobs:
            raise ValueError(f"Training job {job_id} not found")

        return self.training_jobs[job_id]

    def _report_progress(self, job_id: str, epoch: int, progress: float):
        """上报训练进度"""
        try:
            url = f"{self.config.backend_api_url}/api/v1/training/internal/{job_id}/progress"
            requests.post(url, params={
                'current_epoch': epoch,
                'progress': progress
            }, timeout=5)
        except Exception as e:
            logger.warning(f"上报进度失败: {e}")

    def _report_completion(self, job_id: str, model_id: str, metrics: Dict[str, float]):
        """上报训练完成"""
        try:
            url = f"{self.config.backend_api_url}/api/v1/training/internal/{job_id}/complete"
            requests.post(url, params={
                'output_model_id': model_id,
                'final_map': metrics.get('map50_95', 0),
                'final_loss': 0,  # 从 results 中获取
                'best_epoch': 0  # 从训练历史中获取
            }, timeout=5)
        except Exception as e:
            logger.warning(f"上报完成失败: {e}")

    def _report_failure(self, job_id: str, error: str):
        """上报训练失败"""
        try:
            url = f"{self.config.backend_api_url}/api/v1/training/internal/{job_id}/fail"
            requests.post(url, params={'error_message': error}, timeout=5)
        except Exception as e:
            logger.warning(f"上报失败失败: {e}")
