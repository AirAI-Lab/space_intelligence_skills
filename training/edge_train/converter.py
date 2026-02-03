"""
模型转换器
支持 .pt -> .onnx -> .engine 转换
"""

import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Any

import requests
from ultralytics import YOLO

from .config import TrainingConfig

logger = logging.getLogger(__name__)


class ModelConverter:
    """模型格式转换器"""

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.conversion_tasks: Dict[str, Dict[str, Any]] = {}
        self.conversion_threads: Dict[str, threading.Thread] = {}

    def start_conversion(
            self,
            task_id: str,
            model_id: str,
            conversion_type: str
    ) -> Dict[str, Any]:
        """启动转换任务"""

        if task_id in self.conversion_tasks:
            raise ValueError(f"Conversion task {task_id} already exists")

        # 创建任务记录
        self.conversion_tasks[task_id] = {
            'task_id': task_id,
            'model_id': model_id,
            'conversion_type': conversion_type,
            'status': 'running',
            'progress': 0.0,
            'start_time': time.time()
        }

        # 启动转换线程
        thread = threading.Thread(
            target=self._conversion_worker,
            args=(task_id, model_id, conversion_type)
        )
        self.conversion_threads[task_id] = thread
        thread.start()

        return {
            'task_id': task_id,
            'status': 'running'
        }

    def _conversion_worker(self, task_id: str, model_id: str, conversion_type: str):
        """转换工作线程"""
        try:
            logger.info(f"开始转换: task_id={task_id}, type={conversion_type}")

            # 从 S3 下载模型
            model_dir = self.config.get_model_path(model_id)
            model_path = model_dir / 'best.pt'
            s3_model_key = f"models/{model_id}/best.pt"

            if not model_path.exists():
                logger.info(f"从 S3 下载模型: {s3_model_key}")
                if not self.config.download_from_s3(s3_model_key, model_path):
                    raise FileNotFoundError(f"无法下载模型: {model_id}")

            output_path = self.config.get_output_path(task_id)

            # 加载模型
            model = YOLO(str(model_path))

            # 根据转换类型执行转换
            if conversion_type == 'PT_TO_ONNX':
                output_file = self._convert_to_onnx(model, output_path)
                # 上传 ONNX 文件到 S3
                model_id = self.conversion_tasks[task_id]['model_id']
                s3_onnx_key = f"models/{model_id}/best.onnx"
                if self.config.upload_to_s3(output_file, s3_onnx_key):
                    logger.info(f"ONNX 模型已上传到 S3: {s3_onnx_key}")
                else:
                    logger.warning(f"ONNX 模型上传到 S3 失败")
                # 上传 ONNX 配置文件（使用不同的文件名）
                onnx_config_file = output_file.parent / 'onnx_config.json'
                if onnx_config_file.exists():
                    s3_onnx_config_key = f"models/{model_id}/onnx_config.json"
                    if self.config.upload_to_s3(onnx_config_file, s3_onnx_config_key):
                        logger.info(f"ONNX 配置已上传到 S3: {s3_onnx_config_key}")
            elif conversion_type in ['ONNX_TO_ENGINE_FP16', 'ONNX_TO_ENGINE_INT8', 'ONNX_TO_ENGINE_FP32']:
                output_file = self._convert_to_engine(model, output_path, conversion_type)
            else:
                raise ValueError(f"Unsupported conversion type: {conversion_type}")

            # 获取文件大小
            file_size = output_file.stat().st_size

            # TODO: 上传到 S3
            # s3_path = self._upload_to_s3(output_file)

            # 计算转换时间
            conversion_time = int(time.time() - self.conversion_tasks[task_id]['start_time'])

            # 更新状态
            self.conversion_tasks[task_id]['status'] = 'completed'
            self.conversion_tasks[task_id]['progress'] = 1.0

            # 通知后端
            self._report_completion(task_id, str(output_file), file_size, conversion_time)

            logger.info(f"转换完成: task_id={task_id}, output={output_file}")

        except Exception as e:
            logger.error(f"转换失败: task_id={task_id}", exc_info=True)
            self.conversion_tasks[task_id]['status'] = 'failed'
            self.conversion_tasks[task_id]['error'] = str(e)
            self._report_failure(task_id, str(e))

    def _convert_to_onnx(self, model: YOLO, output_path: Path) -> Path:
        """转换为 ONNX 格式，包含完整的网络结构和元数据"""
        output_path.mkdir(parents=True, exist_ok=True)
        output_file = output_path / 'best.onnx'

        self._report_progress(self._get_current_task_id(), 0.5)

        # 获取模型文件所在的目录
        task_id = self._get_current_task_id()
        model_id = self.conversion_tasks[task_id]['model_id']
        model_dir = self.config.get_model_path(model_id)

        # 尝试读取训练配置（如果存在）
        training_config = {}
        training_config_path = model_dir / 'model_config.json'
        if training_config_path.exists():
            try:
                import json
                with open(training_config_path, 'r', encoding='utf-8') as f:
                    training_config = json.load(f)
                logger.info(f"读取训练配置: {training_config_path}")
            except Exception as e:
                logger.warning(f"读取训练配置失败: {e}")

        # 构建 ONNX 配置（与训练配置分开）
        onnx_config = {
            'model_id': model_id,
            'model_type': 'YOLOv8',
            'input_size': training_config.get('architecture', {}).get('input_size', [640, 640]),
            'num_classes': len(model.names) if hasattr(model, 'names') else 3,
            'classes': model.names if hasattr(model, 'names') else {},
            'format': 'onnx',
            'opset_version': 12,
            'dynamic': True,
            'simplified': True,
            'export_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'onnx_compatible': True
        }

        # 导出 ONNX，包含完整的计算图
        # dynamic=True 允许动态输入尺寸
        # simplify=True 简化计算图
        # half=False 保持 FP32 精度（可根据需要改为 True）
        model.export(
            format='onnx',
            imgsz=640,
            simplify=True,
            opset=12,
            dynamic=True,  # 支持动态输入尺寸
            half=False,    # FP32 精度
            verbose=False
        )

        # YOLO export 保存 ONNX 到模型目录
        exported_onnx = model_dir / 'best.onnx'

        if exported_onnx.exists():
            import shutil
            import json
            import onnx

            # 移动 ONNX 文件到输出目录
            shutil.move(str(exported_onnx), str(output_file))
            logger.info(f"ONNX 文件已移动到: {output_file}")

            # 添加元数据到 ONNX 模型
            try:
                onnx_model = onnx.load(str(output_file))

                # 添加自定义元数据
                meta = onnx_model.metadata_props
                meta.add("model_id", model_id)
                meta.add("model_type", "YOLOv8")
                meta.add("input_size", str(onnx_config['input_size']))
                meta.add("num_classes", str(onnx_config['num_classes']))
                meta.add("classes", json.dumps(onnx_config['classes'], ensure_ascii=False))
                meta.add("export_date", onnx_config['export_date'])
                meta.add("format", "onnx")

                # 保存更新后的 ONNX 模型
                onnx.save(onnx_model, str(output_file))
                logger.info(f"ONNX 元数据已添加到模型文件")
            except Exception as e:
                logger.warning(f"添加 ONNX 元数据失败: {e}")

            # 保存 ONNX 配置文件（使用不同的文件名，避免覆盖训练配置）
            onnx_config_file = output_path / 'onnx_config.json'
            with open(onnx_config_file, 'w', encoding='utf-8') as f:
                json.dump(onnx_config, f, indent=2, ensure_ascii=False)
            logger.info(f"ONNX 配置已保存: {onnx_config_file}")

        else:
            # 搜索可能的 ONNX 文件位置
            import shutil
            search_paths = [
                Path.cwd() / 'best.onnx',
                Path.cwd() / f'{model_id}.onnx',
                model_dir / f'{model_id}.onnx',
            ]
            found = False
            for search_path in search_paths:
                if search_path.exists():
                    shutil.move(str(search_path), str(output_file))
                    logger.info(f"在 {search_path} 找到 ONNX 文件，已移动到: {output_file}")
                    found = True
                    break

            if not found:
                # 列出模型目录的所有文件用于调试
                model_dir_files = list(model_dir.glob('*')) if model_dir.exists() else []
                cwd_files = list(Path.cwd().glob('*.onnx'))
                logger.error(f"未找到 ONNX 文件。搜索路径: {search_paths}")
                logger.error(f"模型目录文件: {model_dir_files}")
                logger.error(f"当前目录 ONNX: {cwd_files}")
                raise FileNotFoundError(f"ONNX 导出失败，未找到导出的文件")

        return output_file

    def _convert_to_engine(self, model: YOLO, output_path: Path, conversion_type: str) -> Path:
        """转换为 TensorRT Engine 格式"""
        output_path.mkdir(parents=True, exist_ok=True)
        output_file = output_path / 'best.engine'

        # 确定精度
        half = False
        int8 = False
        precision_suffix = "fp32"

        if conversion_type == 'ONNX_TO_ENGINE_FP16':
            half = True
            precision_suffix = "fp16"
        elif conversion_type == 'ONNX_TO_ENGINE_INT8':
            int8 = True
            precision_suffix = "int8"

        self._report_progress(self._get_current_task_id(), 0.3)

        # 首先导出为 ONNX
        onnx_path = output_path / 'best.onnx'
        model.export(format='onnx', imgsz=640, simplify=True, opset=12)

        self._report_progress(self._get_current_task_id(), 0.6)

        # 使用 trtexec 转换为 TensorRT Engine
        try:
            # 构建 trtexec 命令
            trtexec_cmd = [
                'trtexec',
                '--onnx=' + str(onnx_path),
                '--saveEngine=' + str(output_file),
                '--fp16' if half else '',
                '--int8' if int8 else '',
            ]
            # 过滤空参数
            trtexec_cmd = [arg for arg in trtexec_cmd if arg]

            logger.info(f"执行 TensorRT 转换: {' '.join(trtexec_cmd)}")

            # 执行转换
            result = subprocess.run(
                trtexec_cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )

            if result.returncode != 0:
                raise RuntimeError(f"trtexec 失败: {result.stderr}")

            logger.info(f"TensorRT 转换完成: {output_file}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("TensorRT 转换超时")
        except FileNotFoundError:
            # 如果 trtexec 不可用，尝试使用 Python API
            logger.warning("trtexec 未找到，尝试使用 Python TensorRT API")
            self._convert_to_engine_python_api(onnx_path, output_file, half, int8)

        # 上传到 S3
        task_id = self._get_current_task_id()
        s3_key = f"models/{self.conversion_tasks[task_id]['model_id']}/best.engine.{precision_suffix}"
        if self.config.upload_to_s3(output_file, s3_key):
            logger.info(f"Engine 文件已上传到 S3: {s3_key}")

        return output_file

    def _convert_to_engine_python_api(self, onnx_path: Path, output_file: Path, half: bool, int8: bool):
        """使用 Python TensorRT API 转换"""
        try:
            import tensorrt as trt
            import onnx
            import onnx_graphsurgeon as gs

            # 创建 TensorRT logger
            TRT_LOGGER = trt.Logger(trt.Logger.INFO)

            # 创建 builder
            builder = trt.Builder(TRT_LOGGER)
            network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
            parser = trt.OnnxParser(network, TRT_LOGGER)

            # 解析 ONNX 模型
            with open(onnx_path, 'rb') as model:
                if not parser.parse(model.read()):
                    raise RuntimeError(f"ONNX 解析失败: {parser.get_error(0).desc()}")

            # 创建配置
            config = builder.create_builder_config()
            if half:
                config.set_flag(trt.BuilderFlag.FP16)
            if int8:
                config.set_flag(trt.BuilderFlag.INT8)

            # 设置最大工作空间
            config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 4 << 30)  # 4GB

            # 构建引擎
            engine = builder.build_serialized_network(network, config)

            # 保存引擎
            with open(output_file, 'wb') as f:
                f.write(engine)

            logger.info(f"TensorRT Python API 转换完成: {output_file}")

        except ImportError:
            raise RuntimeError("TensorRT Python API 未安装且 trtexec 不可用")

    def get_status(self, task_id: str) -> Dict[str, Any]:
        """获取转换状态"""
        if task_id not in self.conversion_tasks:
            raise ValueError(f"Conversion task {task_id} not found")

        return self.conversion_tasks[task_id]

    def _report_progress(self, task_id: str, progress: float):
        """上报转换进度"""
        try:
            url = f"{self.config.backend_api_url}/api/v1/conversion/internal/{task_id}/progress"
            requests.post(url, params={'progress': progress}, timeout=5)
        except Exception as e:
            logger.warning(f"上报进度失败: {e}")

    def _report_completion(self, task_id: str, output_path: str, file_size: int, time_seconds: int):
        """上报转换完成"""
        try:
            url = f"{self.config.backend_api_url}/api/v1/conversion/internal/{task_id}/complete"
            requests.post(url, params={
                'output_path': output_path,
                'file_size_bytes': file_size,
                'optimization_time_seconds': time_seconds
            }, timeout=5)
        except Exception as e:
            logger.warning(f"上报完成失败: {e}")

    def _report_failure(self, task_id: str, error: str):
        """上报转换失败"""
        try:
            url = f"{self.config.backend_api_url}/api/v1/conversion/internal/{task_id}/fail"
            requests.post(url, params={'error_message': error}, timeout=5)
        except Exception as e:
            logger.warning(f"上报失败失败: {e}")

    def _get_current_task_id(self) -> str:
        """获取当前任务ID（用于线程内部）"""
        # 从线程名或调用栈获取
        for task_id, thread in self.conversion_threads.items():
            if thread.ident == threading.current_thread().ident:
                return task_id
        return "unknown"
