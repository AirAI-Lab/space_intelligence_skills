"""
YOLO 训练器
"""

import json
import logging
import os
import shutil
import subprocess
import threading
import time
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

import mlflow
import mlflow.pytorch
import pandas as pd
import requests
import torch
from ultralytics import YOLO

from .config import TrainingConfig
from .optimizer import IntelligentParameterOptimizer, get_training_summary

logger = logging.getLogger(__name__)


class YOLOTrainer:
    """YOLOv8 训练器"""

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.training_jobs: Dict[str, Dict[str, Any]] = {}
        self.training_threads: Dict[str, threading.Thread] = {}
        self.progress_monitor_threads: Dict[str, threading.Thread] = {}
        self.progress_stop_events: Dict[str, threading.Event] = {}

        # 智能参数优化器
        self.param_optimizer = IntelligentParameterOptimizer(analysis_window=10)

        # 设置 MLflow
        mlflow.set_tracking_uri(config.mlflow_tracking_uri)
        logger.info(f"MLflow tracking URI: {config.mlflow_tracking_uri}")

    def start_training(
            self,
            job_id: str,
            dataset_id: str,
            dataset_source: str = "backend",
            dataset_url: str = None,
            dataset_path: str = None,
            dataset_storage_path: str = None,
            dataset_name: str = None,
            epochs: int = 100,
            batch_size: int = 16,
            img_size: int = 640,
            use_gpu: bool = True,
            base_model: str = "yolov8n.pt",
            hyperparameters: Dict[str, Any] = None,
            resume: bool = False,
            resume_job_id: str = None,
            enable_smart_optimization: bool = True
    ) -> Dict[str, Any]:
        """启动训练任务

        Args:
            resume: 是否继续之前的训练
            resume_job_id: 要继续的任务ID（用于加载之前的权重）
            enable_smart_optimization: 是否启用智能参数优化（续训时）
        """
        # 使用 print 确保输出
        print(f"========== start_training called: job_id={job_id}, resume={resume}, resume_job_id={resume_job_id} ==========")
        logger.info(f"========== start_training 被调用: job_id={job_id}, resume={resume}, resume_job_id={resume_job_id} ==========")

        # 续训时：如果 job_id 已存在，需要先清理旧记录
        if job_id in self.training_jobs:
            if resume and resume_job_id == job_id:
                # 续训同一个任务：清理旧记录，准备重新启动
                logger.info(f"续训任务：清理旧的任务记录 {job_id}，准备重新启动")
                del self.training_jobs[job_id]
            else:
                raise ValueError(f"Training job {job_id} already exists")

        if hyperparameters is None:
            hyperparameters = {}

        # 确定起始epoch
        start_epoch = 0
        if resume and resume_job_id:
            # 检查之前的任务输出
            resume_output_path = self.config.get_output_path(resume_job_id)
            resume_weights = resume_output_path / 'train' / 'weights' / 'last.pt'
            if resume_weights.exists():
                # 尝试从results.csv读取已训练的epoch数
                resume_results_csv = resume_output_path / 'train' / 'results.csv'
                if resume_results_csv.exists():
                    try:
                        df = pd.read_csv(resume_results_csv)
                        if not df.empty and 'epoch' in df.columns:
                            start_epoch = int(df['epoch'].iloc[-1]) + 1
                            logger.info(f"从任务 {resume_job_id} 恢复训练，起始epoch: {start_epoch}")
                    except Exception as e:
                        logger.warning(f"读取results.csv失败: {e}")
                        start_epoch = 0

        # 创建任务记录
        self.training_jobs[job_id] = {
            'job_id': job_id,
            'dataset_id': dataset_id,
            'dataset_source': dataset_source,
            'status': 'running',
            'epoch': start_epoch,
            'progress': 0.0,
            'start_time': time.time(),
            'stop_requested': False,
            'resume': resume,
            'resume_job_id': resume_job_id,
            'enable_smart_optimization': enable_smart_optimization
        }

        # 启动训练线程
        thread = threading.Thread(
            target=self._training_worker,
            args=(job_id, dataset_id, dataset_source, dataset_url, dataset_path, dataset_storage_path, dataset_name,
                  epochs, batch_size, img_size, use_gpu, base_model, hyperparameters, resume, resume_job_id, enable_smart_optimization)
        )
        self.training_threads[job_id] = thread
        thread.start()

        # 启动进度监控线程
        stop_event = threading.Event()
        self.progress_stop_events[job_id] = stop_event
        monitor_thread = threading.Thread(
            target=self._progress_monitor,
            args=(job_id, epochs, stop_event)
        )
        self.progress_monitor_threads[job_id] = monitor_thread
        monitor_thread.start()

        return {
            'job_id': job_id,
            'status': 'running'
        }

    def _training_worker(
            self,
            job_id: str,
            dataset_id: str,
            dataset_source: str,
            dataset_url: str,
            dataset_path: str,
            dataset_storage_path: str,
            dataset_name: str,
            epochs: int,
            batch_size: int,
            img_size: int,
            use_gpu: bool,
            base_model: str,
            hyperparameters: Dict[str, Any],
            resume: bool = False,
            resume_job_id: str = None,
            enable_smart_optimization: bool = True
    ):
        """训练工作线程

        Args:
            resume: 是否继续之前的训练
            resume_job_id: 要继续的任务ID
            enable_smart_optimization: 是否启用智能参数优化
        """
        try:
            print(f"[DEBUG] 开始训练: job_id={job_id}, resume={resume}, resume_job_id={resume_job_id}, enable_smart_optimization={enable_smart_optimization}")
            print(f"[DEBUG] hyperparameters = {hyperparameters}")
            logger.info(f"开始训练: job_id={job_id}, dataset_source={dataset_source}, resume={resume}, resume_job_id={resume_job_id}, enable_smart_optimization={enable_smart_optimization}")

            # 统一的工作目录
            work_dir = Path('/app/work')
            work_dir.mkdir(parents=True, exist_ok=True)

            # 准备数据集 - 对于本地路径，直接使用源路径
            if dataset_source == "backend" and dataset_storage_path and dataset_storage_path.startswith('/app/data/datasets/'):
                # 直接使用源路径，避免复制
                final_dataset_path = Path(dataset_storage_path)
                logger.info(f"直接使用数据集路径: {final_dataset_path}")
            elif dataset_source == "local":
                # 对于本地路径，直接使用用户提供的路径
                final_dataset_path = Path(dataset_path)
                logger.info(f"使用本地数据集路径: {final_dataset_path}")
            else:
                # 其他情况，使用工作目录
                final_dataset_path = work_dir / 'datasets' / dataset_id
                final_dataset_path.mkdir(parents=True, exist_ok=True)

            # 根据数据集来源进行处理
            if dataset_source == "backend":
                # 如果已经直接使用源路径（/app/data/datasets/），跳过准备步骤
                if dataset_storage_path and str(final_dataset_path) == dataset_storage_path:
                    logger.info(f"直接使用数据集，跳过准备: {final_dataset_path}")
                else:
                    # 从后端共享存储读取数据集
                    self._prepare_backend_dataset(dataset_id, final_dataset_path, dataset_storage_path)
            elif dataset_source == "url":
                # 从 URL 下载数据集到 /app/data/datasets/
                final_dataset_path = Path('/app/data/datasets') / (dataset_name or dataset_id)
                self._prepare_url_dataset(dataset_url, dataset_name or dataset_id, final_dataset_path)
            elif dataset_source == "local":
                # 使用本地路径数据集 - 不需要复制，直接使用
                logger.info(f"本地数据集路径已验证: {final_dataset_path}")
                if not (final_dataset_path / 'data.yaml').exists():
                    raise FileNotFoundError(f"本地数据集缺少 data.yaml 文件: {final_dataset_path}/data.yaml")
            else:
                raise ValueError(f"不支持的数据集来源: {dataset_source}")

            # 验证数据集格式
            data_yaml_path = final_dataset_path / 'data.yaml'
            if not data_yaml_path.exists():
                raise FileNotFoundError(f"数据集缺少 data.yaml 文件: {data_yaml_path}")

            # 准备输出目录
            output_path = self.config.get_output_path(job_id)
            output_path.mkdir(parents=True, exist_ok=True)

            # 创建 MLflow 实验
            experiment_name = f"yolov8_{dataset_id}"
            mlflow.set_experiment(experiment_name)

            # 开始 MLflow run
            with mlflow.start_run(run_name=job_id) as run:
                mlflow.log_params({
                    'dataset_source': dataset_source,
                    'epochs': epochs,
                    'batch_size': batch_size,
                    'img_size': img_size,
                    'base_model': base_model,
                    'resume': resume,
                    'resume_job_id': resume_job_id if resume else None,
                    **hyperparameters
                })

                # 处理 resume 逻辑（方案B：直接在原任务目录续训）
                # 续训时直接使用原任务的检查点文件，不需要拷贝
                resume_weights_in_output = None
                if resume and resume_job_id:
                    # 方案B：续训即继续原任务，使用原任务的目录和检查点
                    resume_output_path = self.config.get_output_path(resume_job_id)
                    source_weights = resume_output_path / 'train' / 'weights' / 'last.pt'
                    backup_weights = resume_output_path / 'train' / 'weights' / 'best.pt'

                    logger.info(f"续训：检查源权重文件: {source_weights}, 存在: {source_weights.exists()}")

                    # 验证 last.pt 的完整性
                    weights_valid = False
                    if source_weights.exists():
                        try:
                            checkpoint = torch.load(str(source_weights), map_location='cpu', weights_only=False)
                            # 验证检查点包含必要字段
                            if 'model' in checkpoint and 'train_args' in checkpoint:
                                weights_valid = True
                                logger.info(f"✓ 续训：last.pt 完整性验证成功，epoch={checkpoint.get('epoch', 'unknown')}")
                            else:
                                logger.warning(f"✗ 续训：last.pt 缺少必要字段")
                        except Exception as e:
                            logger.warning(f"✗ 续训：last.pt 加载失败: {e}")

                    # 如果 last.pt 无效，尝试使用 best.pt
                    if not weights_valid:
                        if backup_weights.exists():
                            try:
                                checkpoint = torch.load(str(backup_weights), map_location='cpu', weights_only=False)
                                if 'model' in checkpoint and 'train_args' in checkpoint:
                                    source_weights = backup_weights
                                    weights_valid = True
                                    logger.info(f"✓ 续训：last.pt 损坏，使用 best.pt 作为备用")
                                else:
                                    logger.warning(f"✗ 续训：best.pt 也缺少必要字段")
                            except Exception as e:
                                logger.warning(f"✗ 续训：best.pt 加载失败: {e}")

                    if source_weights.exists() and weights_valid:
                        # 方案B：直接使用原任务的检查点，不需要拷贝
                        # 输出也使用原任务目录，避免文件被覆盖
                        resume_weights_in_output = str(source_weights)
                        print(f"[DEBUG] 续训：resume_weights_in_output = {resume_weights_in_output}")
                        logger.info(f"✓ 续训：使用原任务检查点 {source_weights}")

                        # 方案B：输出使用原任务目录，这样 results.csv 会自然追加
                        # 修改 output_path 指向原任务目录
                        output_path = resume_output_path
                        logger.info(f"✓ 续训：使用原任务目录 {output_path}")

                        # 关键修复：修改检查点文件中的 project 路径和训练参数
                        # YOLOv8 的 resume 功能会从检查点读取这些参数，需要提前修改
                        try:
                            checkpoint = torch.load(str(source_weights), map_location='cpu', weights_only=False)
                            # 修改检查点中的 project 路径
                            if 'train_args' in checkpoint:
                                old_project = checkpoint['train_args'].get('project', '')
                                checkpoint['train_args']['project'] = str(output_path)

                                # 关键修复：同时修改 save_dir 字段，确保输出到正确目录
                                expected_save_dir = str(output_path / 'train')
                                old_save_dir = checkpoint['train_args'].get('save_dir', '')
                                checkpoint['train_args']['save_dir'] = expected_save_dir
                                logger.info(f"修改检查点 project 路径: {old_project} -> {output_path}")
                                logger.info(f"修改检查点 save_dir 路径: {old_save_dir} -> {expected_save_dir}")

                                # ============ 智能参数优化 ============
                                # 分析当前训练状态并优化续训参数
                                results_csv = output_path / 'train' / 'results.csv'

                                # 获取原始训练参数（从检查点读取）
                                original_params = {
                                    'lr0': checkpoint['train_args'].get('lr0', 0.01),
                                    'lrf': checkpoint['train_args'].get('lrf', 0.01),
                                    'patience': checkpoint['train_args'].get('patience', 30),
                                    'weight_decay': checkpoint['train_args'].get('weight_decay', 0.0005),
                                    'optimizer': checkpoint['train_args'].get('optimizer', 'auto'),
                                    'warmup_epochs': checkpoint['train_args'].get('warmup_epochs', 3),
                                    'mosaic': checkpoint['train_args'].get('mosaic', 1.0),
                                    'mixup': checkpoint['train_args'].get('mixup', 0.0),
                                }

                                if enable_smart_optimization:
                                    # ============ 启用智能优化：完全基于训练状态 ============
                                    logger.info("智能参数优化已启用：基于训练状态和原始参数优化，忽略用户指定的 lr0/patience 等参数")

                                    # 使用智能优化器分析训练状态
                                    training_state = self.param_optimizer.analyze_training_state(
                                        results_csv=results_csv,
                                        checkpoint_epoch=start_epoch
                                    )

                                    if training_state:
                                        # 根据训练状态生成参数优化建议（只基于原始参数和训练状态）
                                        recommendation = self.param_optimizer.optimize_parameters(
                                            state=training_state,
                                            user_params=original_params,  # 使用原始参数作为基础
                                            original_params=original_params
                                        )

                                        # 应用优化建议（得到完全优化的参数）
                                        optimized_params = self.param_optimizer.apply_recommendation(
                                            user_params=original_params,  # 从原始参数开始
                                            recommendation=recommendation
                                        )

                                        # 保留用户指定的非优化参数（batch_size、img_size、optimizer等）
                                        optimized_params['batch_size'] = hyperparameters.get('batch_size', 16)
                                        optimized_params['img_size'] = hyperparameters.get('img_size', 640)
                                        optimized_params['optimizer'] = hyperparameters.get('optimizer', 'AdamW')
                                        optimized_params['workers'] = hyperparameters.get('workers', 8)
                                        optimized_params['save_period'] = hyperparameters.get('save_period', 10)

                                        if not recommendation.should_continue:
                                            logger.warning(f"智能优化建议停止训练: {recommendation.reason}")

                                        logger.info(f"✓ 智能参数优化完成: {recommendation.reason}")
                                        logger.info(f"优化后参数: {optimized_params}")
                                    else:
                                        # 分析失败，使用原始参数
                                        optimized_params = original_params.copy()
                                        optimized_params['batch_size'] = hyperparameters.get('batch_size', 16)
                                        optimized_params['img_size'] = hyperparameters.get('img_size', 640)
                                        optimized_params['optimizer'] = hyperparameters.get('optimizer', 'AdamW')
                                        optimized_params['workers'] = hyperparameters.get('workers', 8)
                                        logger.warning("训练状态分析失败，使用原始参数")
                                else:
                                    # ============ 禁用智能优化：使用用户指定参数 ============
                                    logger.info("智能参数优化已禁用：使用用户指定的训练参数")
                                    optimized_params = hyperparameters.copy()

                                # 更新检查点中的训练参数
                                old_epochs = checkpoint['train_args'].get('epochs', '')
                                old_optimizer = checkpoint['train_args'].get('optimizer', '')
                                old_patience = checkpoint['train_args'].get('patience', '')
                                old_lr0 = checkpoint['train_args'].get('lr0', '')

                                checkpoint['train_args']['epochs'] = epochs
                                checkpoint['train_args']['optimizer'] = optimized_params.get('optimizer', hyperparameters.get('optimizer', 'AdamW'))
                                checkpoint['train_args']['patience'] = optimized_params.get('patience', 50)

                                # 更新学习率相关参数
                                if 'lr0' in optimized_params:
                                    checkpoint['train_args']['lr0'] = optimized_params['lr0']
                                if 'lrf' in optimized_params:
                                    checkpoint['train_args']['lrf'] = optimized_params['lrf']
                                if 'weight_decay' in optimized_params:
                                    checkpoint['train_args']['weight_decay'] = optimized_params['weight_decay']
                                if 'warmup_epochs' in optimized_params:
                                    checkpoint['train_args']['warmup_epochs'] = optimized_params['warmup_epochs']
                                if 'mosaic' in optimized_params:
                                    checkpoint['train_args']['mosaic'] = optimized_params['mosaic']
                                if 'mixup' in optimized_params:
                                    checkpoint['train_args']['mixup'] = optimized_params['mixup']
                                if 'close_mosaic' in optimized_params:
                                    checkpoint['train_args']['close_mosaic'] = optimized_params['close_mosaic']

                                new_lr0 = checkpoint['train_args'].get('lr0', '')
                                logger.info(f"修改检查点训练参数: epochs={old_epochs} -> {epochs}, "
                                           f"optimizer={old_optimizer} -> {checkpoint['train_args']['optimizer']}, "
                                           f"patience={old_patience} -> {checkpoint['train_args']['patience']}, "
                                           f"lr0={old_lr0} -> {new_lr0}")

                            # 保存修改后的检查点
                            torch.save(checkpoint, str(source_weights))
                            logger.info(f"✓ 检查点文件已更新（project + save_dir + 训练参数），确保续训输出到正确目录")
                        except Exception as e:
                            logger.warning(f"修改检查点文件失败: {e}，续训可能输出到错误目录")
                    else:
                        # 回退到基础模型
                        logger.warning(f"✗ 恢复权重文件不存在或损坏，将回退到基础模型")

                # 加载模型
                # 对于续训，直接使用检查点初始化模型（避免 YOLO 替换 resume 路径）
                if resume_weights_in_output:
                    # 续训：直接用检查点初始化模型
                    logger.info(f"续训训练：直接使用检查点初始化模型 {resume_weights_in_output}")
                    model = YOLO(str(resume_weights_in_output))
                    # 不使用 resume 参数，而是让 YOLO 从已加载的检查点继续
                    # 注意：需要从检查点中读取当前 epoch 并更新
                    checkpoint = torch.load(str(resume_weights_in_output), map_location='cpu', weights_only=False)
                    start_epoch = checkpoint.get('epoch', 0)
                    logger.info(f"续训训练：检查点显示已完成 {start_epoch} 轮，将训练到 {epochs} 轮")
                else:
                    # 普通训练：加载基础模型
                    logger.info(f"加载基础模型: {base_model}")
                    local_model_path = Path('/app/models') / base_model
                    if local_model_path.exists():
                        model = YOLO(str(local_model_path))
                        logger.info(f"✓ 使用本地模型: {local_model_path}")
                    else:
                        model = YOLO(base_model)
                        logger.info(f"✓ 使用在线模型: {base_model}")

                # 启动训练
                # 注意：YOLOv8 8.4.9 不支持 BaseCallback
                # 进度报告将在后续版本通过其他方式实现
                # amp=False 避免 AMP 检查下载额外模型
                # plots=False 禁用绘图以避免下载字体文件

                # 确保 plots、amp 参数不会重复传递（从 hyperparameters 中移除）
                # 续训时，排除一些会覆盖续训设置的参数
                excluded_keys = ['plots', 'amp', 'resume']
                if resume_weights_in_output:
                    # 续训时，只排除 epochs（从检查点读取）
                    # optimizer、lr0 等参数使用新任务的值
                    excluded_keys.extend(['epochs'])

                hyperparameters_for_train = {k: v for k, v in hyperparameters.items() if k not in excluded_keys}

                # 构建训练参数
                train_args = {
                    'data': str(data_yaml_path),
                    'epochs': epochs,
                    'batch': batch_size,
                    'imgsz': img_size,
                    'device': self.config.device if use_gpu else 'cpu',
                    'project': str(output_path),
                    'name': 'train',
                    'exist_ok': True,
                    'amp': False,        # 禁用 AMP，避免下载额外模型
                    'plots': False,      # 禁用绘图，避免下载字体
                    **hyperparameters_for_train
                }

                # 续训时设置 resume=True，让 YOLO 从检查点恢复训练状态
                # 由于我们直接用检查点初始化了模型，ckpt_path 已是 last.pt
                # 所以即使 YOLO 执行 args["resume"] = self.ckpt_path，也会保持为 last.pt
                if resume_weights_in_output:
                    train_args['resume'] = True
                    logger.info(f"续训训练：设置 resume=True，让 YOLO 从检查点恢复训练状态")
                    logger.info(f"续训训练：输出目录 {output_path}，results.csv 会自然追加")
                    logger.info(f"续训训练：传递给 YOLO 的 epochs 参数: {train_args.get('epochs')}")
                    logger.info(f"续训训练：传递给 YOLO 的 optimizer 参数: {train_args.get('optimizer')}")
                    print(f"[DEBUG] 续训：设置 resume=True")
                    print(f"[DEBUG] 续训：train_args['epochs'] = {train_args.get('epochs')}")
                    print(f"[DEBUG] 续训：train_args['optimizer'] = {train_args.get('optimizer')}")

                results = model.train(**train_args)

                # 保存最佳模型
                best_model_path = output_path / 'train' / 'weights' / 'best.pt'

                # 训练完成 - 从 results.csv 读取最终指标
                results_csv = output_path / 'train' / 'results.csv'
                final_loss = 0.0
                best_epoch = epochs

                if results_csv.exists():
                    try:
                        df = pd.read_csv(results_csv)
                        if not df.empty:
                            # 获取最后一行的loss值
                            last_row = df.iloc[-1]
                            final_loss = last_row.get('train/box_loss', 0) + last_row.get('train/cls_loss', 0) + last_row.get('train/dfl_loss', 0)
                            # 找到mAP50-95最大的epoch
                            if 'metrics/mAP50-95(B)' in df.columns:
                                best_idx = df['metrics/mAP50-95(B)'].idxmax()
                                best_epoch = int(df.iloc[best_idx].get('epoch', 0)) + 1
                            else:
                                best_epoch = epochs
                    except Exception as e:
                        logger.warning(f"读取results.csv失败: {e}")
                        best_epoch = epochs

                final_metrics = {
                    'map50_95': results.box.map,
                    'map50': results.box.map50,
                    'precision': results.box.mp,
                    'recall': results.box.mr,
                    'final_loss': final_loss,
                    'best_epoch': best_epoch
                }

                mlflow.log_metrics({k: v for k, v in final_metrics.items() if k not in ['final_loss', 'best_epoch']})

                # 保存模型配置文件（包含完整的信息）
                model_config = {
                    'model_id': "M_" + job_id,
                    'model_type': 'YOLOv8',
                    'base_model': base_model,
                    'architecture': {
                        'type': 'YOLOv8 Detection',
                        'input_size': [img_size, img_size],
                        'num_classes': len(results.names) if hasattr(results, 'names') else 3,
                        'classes': results.names if hasattr(results, 'names') else {},
                        'task': 'detection'
                    },
                    'training': {
                        'epochs': epochs,
                        'batch_size': batch_size,
                        'img_size': img_size,
                        'optimizer': hyperparameters.get('optimizer', 'SGD'),
                        'lr0': hyperparameters.get('lr0', 0.01),
                        'dataset_id': dataset_id,
                        'dataset_source': dataset_source
                    },
                    'metrics': {
                        'map50_95': float(final_metrics['map50_95']),
                        'map50': float(final_metrics['map50']),
                        'precision': float(final_metrics['precision']),
                        'recall': float(final_metrics['recall']),
                        'final_loss': float(final_loss),
                        'best_epoch': best_epoch
                    },
                    'files': {
                        'pytorch': 'best.pt',
                        'onnx': 'best.onnx',  # 如果导出
                        'config': 'model_config.json'
                    },
                    'usage': {
                        'inference': 'from ultralytics import YOLO; model = YOLO("best.pt"); results = model("image.jpg")',
                        'export': 'model.export(format="onnx")',
                        'requirements': 'ultralytics>=8.0.0'
                    },
                    'export_date': time.strftime('%Y-%m-%d %H:%M:%S')
                }

                config_path = output_path / 'train' / 'weights' / 'model_config.json'
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(model_config, f, indent=2, ensure_ascii=False)
                logger.info(f"模型配置已保存: {config_path}")

                # 保存类别名称配置文件（便于直接使用）
                names_path = output_path / 'train' / 'weights' / 'classes.txt'
                with open(names_path, 'w', encoding='utf-8') as f:
                    if hasattr(results, 'names'):
                        for idx, name in results.names.items():
                            f.write(f"{idx} {name}\n")
                logger.info(f"类别配置已保存: {names_path}")

                # 复制数据集配置（data.yaml）到模型目录
                if data_yaml_path.exists():
                    data_yaml_dest = output_path / 'train' / 'weights' / 'data.yaml'
                    shutil.copy(str(data_yaml_path), str(data_yaml_dest))
                    logger.info(f"数据集配置已复制: {data_yaml_dest}")

                # 上传模型文件到 S3
                model_id = "M_" + job_id
                s3_model_key = f"models/{model_id}/best.pt"
                if self.config.upload_to_s3(best_model_path, s3_model_key):
                    logger.info(f"模型已上传到 S3: {s3_model_key}")
                else:
                    logger.warning(f"模型上传到 S3 失败，但训练已完成")

                # 上传配置文件到 S3
                s3_config_key = f"models/{model_id}/model_config.json"
                if self.config.upload_to_s3(config_path, s3_config_key):
                    logger.info(f"模型配置已上传到 S3: {s3_config_key}")

                s3_classes_key = f"models/{model_id}/classes.txt"
                if self.config.upload_to_s3(names_path, s3_classes_key):
                    logger.info(f"类别配置已上传到 S3: {s3_classes_key}")

                # 上传 data.yaml 到 S3
                data_yaml_dest = output_path / 'train' / 'weights' / 'data.yaml'
                if data_yaml_dest.exists():
                    s3_data_key = f"models/{model_id}/data.yaml"
                    if self.config.upload_to_s3(data_yaml_dest, s3_data_key):
                        logger.info(f"数据集配置已上传到 S3: {s3_data_key}")

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

        finally:
            # 停止进度监控线程
            if job_id in self.progress_stop_events:
                self.progress_stop_events[job_id].set()
            if job_id in self.progress_monitor_threads:
                monitor_thread = self.progress_monitor_threads[job_id]
                if monitor_thread.is_alive():
                    monitor_thread.join(timeout=2)
                del self.progress_monitor_threads[job_id]
            if job_id in self.progress_stop_events:
                del self.progress_stop_events[job_id]

    def _prepare_backend_dataset(self, dataset_id: str, dataset_path: Path, dataset_storage_path: str = None):
        """准备后端数据集"""
        # 如果存储路径就是目标路径，说明是直接使用模式，无需复制
        if dataset_storage_path and str(dataset_path) == dataset_storage_path:
            logger.info(f"数据集路径相同，跳过复制: {dataset_path}")
            # 验证 data.yaml 存在
            if not (dataset_path / 'data.yaml').exists():
                raise FileNotFoundError(f"数据集缺少 data.yaml: {dataset_path}/data.yaml")
            return

        # 如果提供了存储路径且是本地路径数据集
        if dataset_storage_path and dataset_storage_path.startswith('/app/data/datasets/'):
            source_path = Path(dataset_storage_path)
            if source_path.exists():
                logger.info(f"使用本地路径数据集: {dataset_storage_path}")
                # 复制数据集到工作目录
                if dataset_path.exists():
                    # 使用更安全的方式删除目录
                    def handle_remove_readonly(func, path, exc):
                        os.chmod(path, 0o777)
                        func(path)
                    shutil.rmtree(dataset_path, onerror=handle_remove_readonly)
                shutil.copytree(source_path, dataset_path)
                logger.info(f"本地数据集复制完成: {dataset_path}")
                return

        shared_data_dir = Path('/app/data/files/datasets')
        local_zip = None

        # 查找数据集压缩文件
        if shared_data_dir.exists():
            # 查找与数据集ID相关的压缩文件
            for zip_file in shared_data_dir.glob('*.zip'):
                # 尝试从后端API获取数据集信息来匹配文件
                try:
                    response = requests.get(
                        f"{self.config.backend_api_url}/api/v1/datasets/{dataset_id}",
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()['data']
                        storage_filename = Path(data['storagePath']).name
                        if zip_file.name == storage_filename:
                            local_zip = zip_file
                            break
                except:
                    pass

            # 如果没有找到匹配的，尝试使用数据集ID命名
            if not local_zip:
                candidate = shared_data_dir / f"{dataset_id}.zip"
                if candidate.exists():
                    local_zip = candidate

        # 如果在共享卷中找到了数据集
        if local_zip and local_zip.exists():
            logger.info(f"从共享卷读取数据集: {local_zip}")
            # 解压数据集
            with zipfile.ZipFile(local_zip, 'r') as zip_ref:
                zip_ref.extractall(dataset_path.parent)
            logger.info(f"数据集解压完成: {dataset_path}")
        elif not dataset_path.exists():
            # 尝试从 S3 下载数据集
            s3_dataset_key = f"datasets/{dataset_id}/dataset.zip"
            local_zip = dataset_path.parent / f"{dataset_id}.zip"

            logger.info(f"从 S3 下载数据集: {s3_dataset_key}")
            if self.config.download_from_s3(s3_dataset_key, local_zip):
                # 解压数据集
                with zipfile.ZipFile(local_zip, 'r') as zip_ref:
                    zip_ref.extractall(dataset_path.parent)
                os.remove(local_zip)  # 删除压缩包
                logger.info(f"数据集解压完成: {dataset_path}")
            else:
                raise FileNotFoundError(f"无法找到数据集: {dataset_id}")

    def _prepare_url_dataset(self, dataset_url: str, dataset_name: str, dataset_path: Path):
        """从 URL 准备数据集"""
        logger.info(f"从 URL 下载数据集: {dataset_url}")

        parsed_url = urllib.parse.urlparse(dataset_url)
        download_path = dataset_path.parent / f"{dataset_name}.zip"

        # 判断 URL 类型
        if dataset_url.endswith('.git') or parsed_url.path.startswith('/') and 'git' in dataset_url.lower():
            # Git 仓库
            logger.info("使用 git clone 下载仓库")
            try:
                subprocess.run(
                    ['git', 'clone', dataset_url, str(dataset_path)],
                    check=True,
                    capture_output=True,
                    timeout=600
                )
                logger.info(f"Git 仓库克隆完成: {dataset_path}")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Git 克隆失败: {e.stderr.decode()}")
        else:
            # 直接下载
            logger.info("使用 wget/curl 下载数据集")
            try:
                # 优先使用 wget，fallback 到 curl
                if subprocess.run(['which', 'wget'], capture_output=True).returncode == 0:
                    subprocess.run(
                        ['wget', '-O', str(download_path), dataset_url],
                        check=True,
                        capture_output=True,
                        timeout=600
                    )
                else:
                    subprocess.run(
                        ['curl', '-L', '-o', str(download_path), dataset_url],
                        check=True,
                        capture_output=True,
                        timeout=600
                    )

                # 解压
                logger.info(f"解压数据集: {download_path}")
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    zip_ref.extractall(dataset_path.parent)
                os.remove(download_path)
                logger.info(f"数据集解压完成: {dataset_path}")

            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"下载数据集失败: {e.stderr.decode()}")

    def _prepare_local_dataset(self, local_path: str, dataset_path: Path):
        """准备本地路径数据集"""
        source_path = Path(local_path)
        if not source_path.exists():
            raise FileNotFoundError(f"本地路径不存在: {local_path}")

        logger.info(f"使用本地路径数据集: {local_path}")

        # 如果本地路径已经是 YOLO 格式的根目录（包含 data.yaml）
        if (source_path / 'data.yaml').exists():
            # 直接使用该路径
            logger.info(f"本地路径包含 data.yaml，直接使用")
            # 创建符号链接或复制文件
            if dataset_path.exists():
                shutil.rmtree(dataset_path)
            shutil.copytree(source_path, dataset_path)
        else:
            # 假设本地路径是数据集的父目录
            logger.info(f"本地路径作为数据集根目录")
            if dataset_path.exists():
                shutil.rmtree(dataset_path)
            shutil.copytree(source_path, dataset_path)

        logger.info(f"本地数据集准备完成: {dataset_path}")

    def stop_training(self, job_id: str):
        """安全停止训练，等待检查点保存完成"""
        if job_id not in self.training_jobs:
            raise ValueError(f"Training job {job_id} not found")

        logger.info(f"停止训练请求: {job_id}，等待当前 epoch 完成...")

        # 设置停止标志
        self.training_jobs[job_id]['stop_requested'] = True

        # 等待训练线程停止（最多等待 30 秒）
        # 这给 YOLOv8 时间来完成当前 epoch 的保存
        max_wait = 30
        waited = 0
        while waited < max_wait:
            if job_id not in self.training_threads:
                break
            thread = self.training_threads.get(job_id)
            if thread and not thread.is_alive():
                logger.info(f"训练线程已停止: {job_id}")
                break
            time.sleep(1)
            waited += 1

        if waited >= max_wait:
            logger.warning(f"停止训练超时: {job_id}，但已发送停止请求")

        # 验证 last.pt 的完整性
        try:
            output_path = self.config.get_output_path(job_id)
            last_pt = output_path / 'train' / 'weights' / 'last.pt'
            if last_pt.exists():
                checkpoint = torch.load(str(last_pt), map_location='cpu', weights_only=False)
                logger.info(f"✓ last.pt 完整性验证成功: {job_id}, epoch={checkpoint.get('epoch', 'unknown')}")
            else:
                logger.warning(f"⚠ last.pt 不存在: {last_pt}")
        except Exception as e:
            logger.error(f"✗ last.pt 完整性验证失败: {e}")
            logger.warning(f"续训时可能会使用 best.pt 或回退到基础模型")

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

    def _progress_monitor(self, job_id: str, total_epochs: int, stop_event: threading.Event):
        """进度监控线程 - 定期读取 results.csv 并上报进度"""
        output_path = self.config.get_output_path(job_id)
        results_csv = output_path / 'train' / 'results.csv'

        last_reported_epoch = 0

        while not stop_event.is_set():
            try:
                # 检查任务是否还在运行
                if job_id not in self.training_jobs:
                    break

                job_status = self.training_jobs[job_id].get('status')
                if job_status in ['completed', 'failed', 'cancelled']:
                    break

                # 读取 results.csv
                if results_csv.exists():
                    try:
                        df = pd.read_csv(results_csv)
                        if not df.empty and 'epoch' in df.columns:
                            current_epoch = int(df['epoch'].iloc[-1]) + 1
                            progress = min(current_epoch / total_epochs, 1.0)

                            # 只在 epoch 变化时上报
                            if current_epoch != last_reported_epoch:
                                logger.info(f"上报训练进度: job_id={job_id}, epoch={current_epoch}/{total_epochs}, progress={progress*100:.1f}%")
                                self._report_progress(job_id, current_epoch, progress)

                                # 更新内存中的进度
                                self.training_jobs[job_id]['epoch'] = current_epoch
                                self.training_jobs[job_id]['progress'] = progress

                                last_reported_epoch = current_epoch
                    except Exception as e:
                        logger.warning(f"读取 results.csv 失败: {e}")

                # 每5秒检查一次
                time.sleep(5)

            except Exception as e:
                logger.error(f"进度监控线程错误: {e}")
                time.sleep(5)

        logger.info(f"进度监控线程退出: job_id={job_id}")

    def _report_completion(self, job_id: str, model_id: str, metrics: Dict[str, float]):
        """上报训练完成"""
        try:
            url = f"{self.config.backend_api_url}/api/v1/training/internal/{job_id}/complete"
            requests.post(url, params={
                'output_model_id': model_id,
                'final_map': metrics.get('map50_95', 0),
                'final_map50': metrics.get('map50', 0),
                'final_loss': metrics.get('final_loss', 0),
                'best_epoch': metrics.get('best_epoch', 0)
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

    def get_training_logs(self, job_id: str, tail_lines: int = 100) -> Dict[str, Any]:
        """获取训练日志"""
        if job_id not in self.training_jobs:
            return {
                'status': 'error',
                'message': f'Training job {job_id} not found'
            }

        job_info = self.training_jobs[job_id]
        logs = []

        # 获取输出路径
        output_path = self.config.get_output_path(job_id)
        train_dir = output_path / 'train'

        # 1. 读取 results.csv（训练指标）
        results_csv = train_dir / 'results.csv'
        current_epoch = 0
        if results_csv.exists():
            try:
                df = pd.read_csv(results_csv)
                # 获取最后 tail_lines 行
                recent_df = df.tail(min(tail_lines, len(df)))
                # 更新当前 epoch
                if 'epoch' in df.columns:
                    current_epoch = int(df['epoch'].iloc[-1]) + 1
                    job_info['epoch'] = current_epoch
                # 计算进度
                if 'epochs' in df.columns:
                    total_epochs = int(df['epochs'].iloc[0]) if len(df) > 0 else 100
                else:
                    total_epochs = 100
                job_info['progress'] = current_epoch / total_epochs

                for _, row in recent_df.iterrows():
                    epoch = int(row.get('epoch', 0)) + 1
                    metrics = []
                    for col in df.columns:
                        if col != 'epoch' and col != 'epochs':
                            val = row.get(col)
                            if val is not None and not pd.isna(val):
                                if isinstance(val, float):
                                    metrics.append(f"{col}={val:.4f}")
                                else:
                                    metrics.append(f"{col}={val}")
                    logs.append({
                        'time': '',  # results.csv 没有时间戳
                        'level': 'INFO',
                        'message': f"Epoch {epoch}/{total_epochs}: " + ", ".join(metrics)
                    })
            except Exception as e:
                logger.warning(f"读取 results.csv 失败: {e}")

        # 2. 尝试读取训练日志文件（如果存在）
        log_files = [
            train_dir / 'train.log',
            output_path / 'training.log',
        ]

        log_found = False
        for log_file in log_files:
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        # 获取最后 tail_lines 行
                        recent_lines = lines[-tail_lines:] if len(lines) > tail_lines else lines
                        for line in recent_lines:
                            line = line.strip()
                            if line:
                                # 解析日志级别
                                level = 'INFO'
                                if 'ERROR' in line or 'error' in line.lower():
                                    level = 'ERROR'
                                elif 'WARNING' in line or 'warning' in line.lower():
                                    level = 'WARNING'
                                elif 'DEBUG' in line or 'debug' in line.lower():
                                    level = 'DEBUG'

                                logs.append({
                                    'time': '',
                                    'level': level,
                                    'message': line
                                })
                    log_found = True
                    break
                except Exception as e:
                    logger.warning(f"读取日志文件 {log_file} 失败: {e}")

        # 3. 如果没有找到日志，添加状态信息
        # 使用内存中的 epoch（对于续训任务，这可能更准确）
        memory_epoch = job_info.get('epoch', current_epoch)
        if not logs and not log_found:
            logs.append({
                'time': '',
                'level': 'INFO',
                'message': f"训练状态: {job_info.get('status')}, Epoch: {memory_epoch}, 进度: {job_info.get('progress', 0) * 100:.1f}%"
            })

        return {
            'status': 'success',
            'data': {
                'job_id': job_id,
                'status': job_info.get('status'),
                'epoch': memory_epoch,
                'progress': job_info.get('progress', 0.0),
                'logs': logs,
                'log_count': len(logs),
                'output_path': str(output_path)
            }
        }
