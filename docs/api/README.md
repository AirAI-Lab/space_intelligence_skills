# edge_infer_cloud API 文档

## 基础信息

- **Base URL**: `http://localhost:8080/api/v1`
- **Content-Type**: `application/json`
- **认证方式**: Bearer Token (即将支持)

## 通用响应格式

### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### 错误响应

```json
{
  "code": 400,
  "message": "错误描述",
  "error": "详细错误信息"
}
```

## 设备管理 API

### 注册设备

```http
POST /api/v1/device/register
Content-Type: application/json

{
  "device_id": "EDGE_DEVICE_001",
  "device_name": "边缘设备1",
  "device_type": "jetson_orin",
  "group_id": "group_a",
  "specs": {
    "cpu": "ARM Cortex-A78AE",
    "gpu": "NVIDIA Ampere",
    "memory": "32GB"
  }
}
```

**响应**：

```json
{
  "code": 200,
  "message": "设备注册成功",
  "data": {
    "device_id": "EDGE_DEVICE_001",
    "access_token": "xxx",
    "mqtt_broker": "tcp://localhost:1883",
    "mqtt_topic": "edge/EDGE_DEVICE_001/#"
  }
}
```

### 获取设备列表

```http
GET /api/v1/device/list?page=1&page_size=20&status=online
```

**响应**：

```json
{
  "code": 200,
  "data": {
    "total": 100,
    "items": [
      {
        "device_id": "EDGE_DEVICE_001",
        "device_name": "边缘设备1",
        "status": "online",
        "last_heartbeat": "2025-01-26T10:00:00Z",
        "cpu_usage": 45.5,
        "gpu_usage": 60.2,
        "memory_usage": 12.5
      }
    ]
  }
}
```

### 获取设备状态

```http
GET /api/v1/device/{device_id}/status
```

### 下发配置

```http
PUT /api/v1/device/{device_id}/config
Content-Type: application/json

{
  "model_config": {
    "conf_threshold": 0.5,
    "nms_threshold": 0.45
  }
}
```

## 数据管理 API

### 上传数据

```http
POST /api/v1/data/upload
Content-Type: multipart/form-data

file: <binary>
path: datasets/my_dataset/images/train
```

### 创建数据集

```http
POST /api/v1/data/dataset/create
Content-Type: application/json

{
  "dataset_name": "安全帽检测数据集",
  "dataset_type": "yolo",
  "data_yaml_path": "/datasets/my_dataset/data.yaml",
  "class_names": ["person", "helmet"],
  "nc": 2
}
```

### 启动AI标注

```http
POST /api/v1/data/annotation/ai
Content-Type: application/json

{
  "dataset_id": "DS001",
  "model_id": "yolov8n",
  "target_device": "EDGE_DEVICE_001",
  "conf_threshold": 0.25
}
```

### 获取标注结果

```http
GET /api/v1/data/annotation/{task_id}
```

## 训练管理 API

### 创建训练任务

```http
POST /api/v1/training/job/create
Content-Type: application/json

{
  "job_name": "安全帽检测训练",
  "dataset_id": "DS001",
  "model_id": "yolov8n.pt",
  "config": {
    "epochs": 100,
    "batch": 16,
    "imgsz": 640,
    "lr0": 0.01,
    "optimizer": "AdamW",
    "device": 0
  }
}
```

### 获取训练任务详情

```http
GET /api/v1/training/job/{job_id}
```

**响应**：

```json
{
  "code": 200,
  "data": {
    "job_id": "JOB001",
    "status": "running",
    "progress": 45,
    "metrics": {
      "loss": 0.234,
      "mAP50": 0.85,
      "precision": 0.87,
      "recall": 0.82
    },
    "current_epoch": 45,
    "total_epochs": 100
  }
}
```

### 停止训练任务

```http
POST /api/v1/training/job/{job_id}/stop
```

### 获取训练日志

```http
GET /api/v1/training/job/{job_id}/logs?lines=100
```

### 验证模型

```http
POST /api/v1/training/val
Content-Type: application/json

{
  "model_path": "/runs/train/exp/weights/best.pt",
  "data_yaml": "/datasets/my_dataset/data.yaml",
  "batch": 16,
  "imgsz": 640
}
```

### 导出模型

```http
POST /api/v1/training/export
Content-Type: application/json

{
  "model_path": "/runs/train/exp/weights/best.pt",
  "format": "engine",
  "half": true,
  "int8": false,
  "workspace": 4
}
```

## 模型管理 API

### 上传模型

```http
POST /api/v1/model/upload
Content-Type: multipart/form-data

model_file: <binary>
config_file: <binary>
name: "安全帽检测v2.0"
type: "yolov8"
format: "tensorrt"
```

### 获取模型版本列表

```http
GET /api/v1/model/versions?page=1&page_size=20
```

### 部署模型

```http
POST /api/v1/model/deploy
Content-Type: application/json

{
  "model_id": "M001",
  "device_ids": ["EDGE_001", "EDGE_002"],
  "backup": true,
  "auto_restart": true
}
```

### 获取模型指标

```http
GET /api/v1/model/{model_id}/metrics
```

## 推理 API

### 启动推理

```http
POST /api/v1/inference/start
Content-Type: application/json

{
  "device_id": "EDGE_DEVICE_001",
  "model_id": "M001",
  "input_uri": "rtsp://camera:554/stream"
}
```

### 停止推理

```http
POST /api/v1/inference/stop
Content-Type: application/json

{
  "device_id": "EDGE_DEVICE_001"
}
```

### 获取推理状态

```http
GET /api/v1/inference/status?device_id=EDGE_DEVICE_001
```

### 预测

```http
POST /api/v1/inference/predict
Content-Type: application/json

{
  "device_id": "EDGE_DEVICE_001",
  "image": "base64_encoded_image",
  "conf_threshold": 0.5
}
```

## OTA管理 API

### 创建升级任务

```http
POST /api/v1/ota/create
Content-Type: application/json

{
  "task_name": "Agent升级v1.0.1",
  "package_id": "PKG001",
  "target_devices": ["EDGE_001", "EDGE_002"],
  "strategy": {
    "concurrent": 5,
    "auto_rollback": true,
    "retry": 3
  }
}
```

### 开始升级

```http
POST /api/v1/ota/{task_id}/start
```

### 获取升级进度

```http
GET /api/v1/ota/{task_id}/progress
```

**响应**：

```json
{
  "code": 200,
  "data": {
    "task_id": "OTA001",
    "status": "running",
    "total_devices": 10,
    "completed": 5,
    "failed": 1,
    "progress": 50,
    "devices": [
      {
        "device_id": "EDGE_001",
        "status": "completed",
        "progress": 100
      },
      {
        "device_id": "EDGE_002",
        "status": "running",
        "progress": 60
      }
    ]
  }
}
```

### 回滚

```http
POST /api/v1/ota/{task_id}/rollback
```

## WebSocket API

### 订阅设备状态

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/device/{device_id}/status');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('CPU:', data.cpu_usage);
  console.log('GPU:', data.gpu_usage);
};
```

### 订阅训练进度

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/training/{job_id}/progress');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Epoch:', data.current_epoch);
  console.log('Loss:', data.loss);
};
```

## 错误码

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器错误 |

## 请求示例

### 使用 curl

```bash
# 注册设备
curl -X POST http://localhost:8080/api/v1/device/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "EDGE_DEVICE_001",
    "device_name": "边缘设备1",
    "device_type": "jetson_orin"
  }'

# 获取设备列表
curl http://localhost:8080/api/v1/device/list

# 创建训练任务
curl -X POST http://localhost:8080/api/v1/training/job/create \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "训练任务1",
    "dataset_id": "DS001",
    "model_id": "yolov8n.pt"
  }'
```

### 使用 Python

```python
import requests

# 注册设备
response = requests.post(
    'http://localhost:8080/api/v1/device/register',
    json={
        'device_id': 'EDGE_DEVICE_001',
        'device_name': '边缘设备1',
        'device_type': 'jetson_orin'
    }
)
print(response.json())
```

### 使用 JavaScript

```javascript
// 注册设备
fetch('http://localhost:8080/api/v1/device/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    device_id: 'EDGE_DEVICE_001',
    device_name: '边缘设备1',
    device_type: 'jetson_orin'
  })
})
.then(res => res.json())
.then(data => console.log(data));
```
