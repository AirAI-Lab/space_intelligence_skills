"""
训练服务配置
"""

import os
import boto3
from botocore.client import Config as BotoConfig
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class TrainingConfig:
    """训练服务配置"""

    # 存储配置
    s3_endpoint: str = field(default_factory=lambda: os.environ.get(
        'S3_ENDPOINT', 'http://seaweedfs:8333'
    ))
    s3_access_key: str = field(default_factory=lambda: os.environ.get(
        'S3_ACCESS_KEY', 'admin'
    ))
    s3_secret_key: str = field(default_factory=lambda: os.environ.get(
        'S3_SECRET_KEY', 'admin123456'
    ))
    s3_bucket: str = field(default_factory=lambda: os.environ.get(
        'S3_BUCKET', 'edge-cloud'
    ))

    # MLflow 配置
    mlflow_tracking_uri: str = field(default_factory=lambda: os.environ.get(
        'MLFLOW_TRACKING_URI', 'http://mlflow:5001'
    ))

    # 后端 API 配置
    backend_api_url: str = field(default_factory=lambda: os.environ.get(
        'BACKEND_API_URL', 'http://backend:8081'
    ))

    # MQTT 配置
    mqtt_broker_url: str = field(default_factory=lambda: os.environ.get(
        'MQTT_BROKER_URL', 'tcp://emqx:1883'
    ))
    mqtt_username: str = field(default_factory=lambda: os.environ.get(
        'MQTT_USERNAME', 'admin'
    ))
    mqtt_password: str = field(default_factory=lambda: os.environ.get(
        'MQTT_PASSWORD', 'admin123456'
    ))

    # 训练配置
    work_dir: Path = field(default_factory=lambda: Path('/app/work'))
    dataset_dir: Path = field(default_factory=lambda: Path('/app/work/datasets'))
    model_dir: Path = field(default_factory=lambda: Path('/app/work/models'))
    output_dir: Path = field(default_factory=lambda: Path('/app/work/outputs'))

    # GPU 配置
    use_gpu: bool = field(default_factory=lambda: os.environ.get(
        'USE_GPU', 'true'
    ).lower() == 'true')

    # 设备配置
    device: str = field(default='cuda')

    def __post_init__(self):
        """初始化后处理"""
        if not self.use_gpu:
            self.device = 'cpu'

        # 创建工作目录
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_dataset_path(self, dataset_id: str) -> Path:
        """获取数据集路径"""
        return self.dataset_dir / dataset_id

    def get_model_path(self, model_id: str) -> Path:
        """获取模型路径"""
        return self.model_dir / model_id

    def get_output_path(self, job_id: str) -> Path:
        """获取输出路径"""
        return self.output_dir / job_id

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            's3_endpoint': self.s3_endpoint,
            's3_bucket': self.s3_bucket,
            'mlflow_tracking_uri': self.mlflow_tracking_uri,
            'backend_api_url': self.backend_api_url,
            'mqtt_broker_url': self.mqtt_broker_url,
            'use_gpu': self.use_gpu,
            'device': self.device,
            'work_dir': str(self.work_dir),
        }

    def get_s3_client(self):
        """获取 S3 客户端"""
        return boto3.client(
            's3',
            endpoint_url=self.s3_endpoint,
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key,
            config=BotoConfig(signature_version='s3v4'),
            region_name='us-east-1'
        )

    def download_from_s3(self, s3_key: str, local_path: Path) -> bool:
        """从 S3 下载文件"""
        try:
            s3 = self.get_s3_client()
            local_path.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(self.s3_bucket, s3_key, str(local_path))
            return True
        except Exception as e:
            print(f"S3 下载失败: {e}")
            return False

    def upload_to_s3(self, local_path: Path, s3_key: str) -> bool:
        """上传文件到 S3"""
        try:
            s3 = self.get_s3_client()
            s3.upload_file(str(local_path), self.s3_bucket, s3_key)
            return True
        except Exception as e:
            print(f"S3 上传失败: {e}")
            return False
