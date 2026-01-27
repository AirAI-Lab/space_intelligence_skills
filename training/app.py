"""
Edge Infer Cloud - 训练服务
提供 YOLOv8 模型训练、转换和 MLflow 集成
"""

import logging
import os
import sys
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from edge_train.trainer import YOLOTrainer
from edge_train.converter import ModelConverter
from edge_train.config import TrainingConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
        "epochs": 100,
        "batch_size": 16,
        "img_size": 640,
        "use_gpu": true,
        "base_model": "yolov8n.pt",
        "hyperparameters": {...}
    }
    """
    try:
        data = request.get_json()

        job_id = data.get('job_id')
        dataset_id = data.get('dataset_id')
        epochs = data.get('epochs', 100)
        batch_size = data.get('batch_size', 16)
        img_size = data.get('img_size', 640)
        use_gpu = data.get('use_gpu', True)
        base_model = data.get('base_model', 'yolov8n.pt')
        hyperparameters = data.get('hyperparameters', {})

        logger.info(f"收到训练请求: job_id={job_id}, dataset_id={dataset_id}")

        # 异步启动训练
        result = trainer.start_training(
            job_id=job_id,
            dataset_id=dataset_id,
            epochs=epochs,
            batch_size=batch_size,
            img_size=img_size,
            use_gpu=use_gpu,
            base_model=base_model,
            hyperparameters=hyperparameters
        )

        return jsonify({
            'status': 'success',
            'message': 'Training started',
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
