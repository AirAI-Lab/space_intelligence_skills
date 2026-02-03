"""
Edge Infer Cloud - 训练服务
提供 YOLOv8 模型训练、转换和 MLflow 集成
"""

import logging
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from edge_train.trainer import YOLOTrainer
from edge_train.converter import ModelConverter
from edge_train.config import TrainingConfig

# 配置日志 - 确保所有模块的日志都能被输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # 强制重新配置，覆盖之前的设置
)
# 确保根 logger 也被正确配置
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for handler in root_logger.handlers:
    handler.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 加载配置
config = TrainingConfig()

# 初始化训练器和转换器
trainer = YOLOTrainer(config)
converter = ModelConverter(config)


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'service': 'training-service',
        'version': '1.0.0'
    })


@app.route('/train', methods=['POST'])
def start_training():
    """
    启动训练任务

    请求体:
    {
        "job_id": "JOBxxx",
        "dataset_id": "DSxxx",
        "dataset_source": "backend",  // backend, url, local
        "dataset_url": "...",         // url 时使用
        "dataset_path": "...",        // local 时使用
        "dataset_name": "...",        // url/local 时使用
        "epochs": 100,
        "batch_size": 16,
        "img_size": 640,
        "use_gpu": true,
        "base_model": "yolov8n.pt",
        "hyperparameters": {...},
        "resume": false,              // 是否继续之前的训练
        "resume_job_id": "JOBxxx"     // 要继续的任务ID
    }
    """
    try:
        data = request.get_json()

        job_id = data.get('job_id')
        dataset_id = data.get('dataset_id')
        dataset_source = data.get('dataset_source', 'backend')
        dataset_url = data.get('dataset_url')
        dataset_path = data.get('dataset_path')
        dataset_storage_path = data.get('dataset_storage_path')
        dataset_name = data.get('dataset_name')
        epochs = data.get('epochs', 100)
        batch_size = data.get('batch_size', 16)
        img_size = data.get('img_size', 640)
        use_gpu = data.get('use_gpu', True)
        base_model = data.get('base_model', 'yolov8n.pt')
        hyperparameters = data.get('hyperparameters', {})
        resume = data.get('resume', False)
        resume_job_id = data.get('resume_job_id')
        enable_smart_optimization = data.get('enable_smart_optimization', True)  # 是否启用智能参数优化

        # 使用 print 确保输出（不依赖 logger）
        print(f"[DEBUG] 收到训练请求: job_id={job_id}, resume={resume}, resume_job_id={resume_job_id}")
        print(f"[DEBUG] 收到训练请求: hyperparameters = {hyperparameters}")
        print(f"[DEBUG] 收到训练请求: base_model = {base_model}, epochs = {epochs}")
        logger.info(f"收到训练请求: job_id={job_id}, dataset_id={dataset_id}, dataset_source={dataset_source}, resume={resume}, resume_job_id={resume_job_id}")

        # 如果是续训任务，先读取原任务的实际进度并上报给后端
        if resume and resume_job_id:
            try:
                resume_output_path = Path('/app/runs') / resume_job_id
                results_csv = resume_output_path / 'train' / 'results.csv'

                if results_csv.exists():
                    df = pd.read_csv(results_csv)
                    if not df.empty and 'epoch' in df.columns:
                        actual_epoch = int(df['epoch'].iloc[-1]) + 1  # 已完成的轮次
                        actual_progress = min(actual_epoch / epochs, 1.0)

                        # 上报实际进度给后端
                        try:
                            backend_api_url = os.environ.get('BACKEND_API_URL', 'http://backend:8080')
                            progress_url = f"{backend_api_url}/api/v1/training/internal/{resume_job_id}/progress"
                            requests.post(progress_url, params={
                                'current_epoch': actual_epoch,
                                'progress': actual_progress
                            }, timeout=5)
                            logger.info(f"续训任务: 已上报原任务实际进度 epoch={actual_epoch}, progress={actual_progress:.2%}")
                        except Exception as e:
                            logger.warning(f"上报原任务进度失败: {e}")
            except Exception as e:
                logger.warning(f"读取原任务进度失败: {e}")

        # 异步启动训练
        result = trainer.start_training(
            job_id=job_id,
            dataset_id=dataset_id,
            dataset_source=dataset_source,
            dataset_url=dataset_url,
            dataset_path=dataset_path,
            dataset_storage_path=dataset_storage_path,
            dataset_name=dataset_name,
            epochs=epochs,
            batch_size=batch_size,
            img_size=img_size,
            use_gpu=use_gpu,
            base_model=base_model,
            hyperparameters=hyperparameters,
            resume=resume,
            resume_job_id=resume_job_id,
            enable_smart_optimization=enable_smart_optimization
        )

        return jsonify({
            'status': 'success',
            'message': 'Training started' + (' (resume)' if resume else ''),
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"启动训练失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/train/<job_id>/stop', methods=['POST'])
def stop_training(job_id: str):
    """停止训练任务"""
    try:
        trainer.stop_training(job_id)
        return jsonify({
            'status': 'success',
            'message': f'Training {job_id} stopped'
        }), 200
    except Exception as e:
        logger.error(f"停止训练失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/train/<job_id>/status', methods=['GET'])
def get_training_status(job_id: str):
    """获取训练状态"""
    try:
        status = trainer.get_status(job_id)
        return jsonify({
            'status': 'success',
            'data': status
        }), 200
    except Exception as e:
        logger.error(f"获取训练状态失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/train/<job_id>/actual-progress', methods=['GET'])
def get_actual_progress(job_id: str):
    """
    获取任务的实际进度（从 results.csv 读取）

    用于续训时获取原任务的实际训练轮次
    """
    try:
        output_path = Path('/app/runs') / job_id
        results_csv = output_path / 'train' / 'results.csv'

        if not results_csv.exists():
            return jsonify({
                'status': 'success',
                'data': {
                    'current_epoch': 0,
                    'exists': False
                }
            }), 200

        df = pd.read_csv(results_csv)
        if df.empty or 'epoch' not in df.columns:
            return jsonify({
                'status': 'success',
                'data': {
                    'current_epoch': 0,
                    'exists': True
                }
            }), 200

        current_epoch = int(df['epoch'].iloc[-1]) + 1  # 已完成的轮次

        return jsonify({
            'status': 'success',
            'data': {
                'current_epoch': current_epoch,
                'exists': True
            }
        }), 200

    except Exception as e:
        logger.error(f"获取实际进度失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/train/<job_id>/logs', methods=['GET'])
def get_training_logs(job_id: str):
    """获取训练日志"""
    try:
        # 获取日志参数
        tail_lines = request.args.get('tail', 100, type=int)

        # 从训练器获取日志
        result = trainer.get_training_logs(job_id, tail_lines)

        if result.get('status') == 'error':
            return jsonify(result), 404

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"获取训练日志失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/convert', methods=['POST'])
def start_conversion():
    """
    启动模型转换

    请求体:
    {
        "task_id": "CONVxxx",
        "model_id": "Mxxx",
        "conversion_type": "PT_TO_ONNX" | "ONNX_TO_ENGINE_FP16" | "ONNX_TO_ENGINE_INT8"
    }
    """
    try:
        data = request.get_json()

        task_id = data.get('task_id')
        model_id = data.get('model_id')
        conversion_type = data.get('conversion_type')

        logger.info(f"收到转换请求: task_id={task_id}, model_id={model_id}, type={conversion_type}")

        # 启动转换
        result = converter.start_conversion(
            task_id=task_id,
            model_id=model_id,
            conversion_type=conversion_type
        )

        return jsonify({
            'status': 'success',
            'message': 'Conversion started',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"启动转换失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/convert/<task_id>/status', methods=['GET'])
def get_conversion_status(task_id: str):
    """获取转换状态"""
    try:
        status = converter.get_status(task_id)
        return jsonify({
            'status': 'success',
            'data': status
        }), 200
    except Exception as e:
        logger.error(f"获取转换状态失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def main():
    """启动服务"""
    port = int(os.environ.get('TRAINING_SERVICE_PORT', 5002))
    debug = os.environ.get('TRAINING_SERVICE_DEBUG', 'false').lower() == 'true'

    logger.info(f"启动训练服务: port={port}, debug={debug}")

    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == '__main__':
    main()
