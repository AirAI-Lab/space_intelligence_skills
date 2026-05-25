# SkyEdge AI Cloud Platform — 第三方对接指南

## 1. 概述

SkyEdge AI Cloud Platform 提供四种第三方对接方式：

| 方式 | 场景 | 延迟 |
|------|------|------|
| **REST API** | 主动查询设备、推理结果、告警 | 请求-响应 |
| **Webhook** | 被动接收告警/推理结果推送 | 实时 |
| **MQTT** | 实时订阅推理结果、设备状态 | 毫秒级 |
| **WebSocket** | 前端实时展示训练进度、推理结果 | 实时 |

### 部署模式与对接方式

| 部署模式 | 容器数 | 可用对接方式 | 适用场景 |
|----------|--------|-------------|----------|
| **A: 纯推理** `--profile gpu` | 2 | MQTT | 第三方只需 MQTT 推理结果，无需管理界面 |
| **B: 推理+管理** `--profile standard` | 8 | REST API、Webhook、MQTT、WebSocket | 有管理需求但无 GPU |
| **C: 完整平台** `--profile standard --profile gpu` | 10 | 全部 | 全功能部署 |

## 2. 认证

> **模式 A（纯推理）** 无 REST API，仅通过 MQTT 订阅获取结果，无需认证。
> **模式 B/C** 的 REST API 需要认证。

所有 REST API 请求需要携带 `X-API-Key` header：

```bash
curl -H "X-API-Key: your-api-key" http://<HOST>/api/v1/devices
```

API Key 在部署时通过 `.env` 文件的 `API_KEY` 字段配置。

Swagger UI 地址：`http://<HOST>/swagger-ui.html`（无需认证即可浏览文档）

## 3. REST API

### 3.1 推理结果查询

```bash
# 分页查询推理结果
GET /api/v1/inference-results?page=1&page_size=20

# 按设备过滤
GET /api/v1/inference-results?device_id=jetson-001

# 按来源过滤（edge/cloud）
GET /api/v1/inference-results?source=cloud

# 按告警级别过滤
GET /api/v1/inference-results?alert_level=critical

# 时间范围
GET /api/v1/inference-results?start_time=2025-01-01T00:00:00&end_time=2025-01-02T00:00:00
```

响应示例：
```json
{
  "items": [
    {
      "id": 1,
      "device_id": "jetson-001",
      "source": "edge",
      "model_name": "yolov8n",
      "task_type": "detect",
      "time": "2025-01-15T10:30:00",
      "detection_count": 3,
      "alert_level": "warning",
      "alert_message": "检测到3个目标",
      "inference_time_ms": 45.2,
      "image_url": "/api/v1/files/download?key=inference/xxx.jpg",
      "summary_text": "person:2, helmet:1"
    }
  ],
  "total": 100
}
```

### 3.2 告警查询

```bash
GET /api/v1/inference-results/alerts?page=1&page_size=20&levels=critical,warning
```

### 3.3 统计数据

```bash
GET /api/v1/inference-results/stats
```

### 3.4 设备管理

```bash
# 设备列表
GET /api/v1/devices

# 设备详情
GET /api/v1/devices/{deviceId}

# 设备配置下发
PUT /api/v1/devices/{deviceId}/config
```

### 3.5 文件下载

推理结果中的图片通过文件服务访问：

```bash
GET /api/v1/files/download?key=inference/2025/01/15/result_xxx.jpg
```

## 4. Webhook 回调

配置 Webhook 后，平台会在事件发生时主动推送到指定 URL。

### 4.1 注册 Webhook

```bash
POST /api/v1/webhooks
Content-Type: application/json
X-API-Key: your-api-key

{
  "name": "告警通知",
  "url": "https://your-server.com/webhook/alert",
  "events": ["alert.critical", "alert.warning"],
  "headers": {
    "Authorization": "Bearer your-token"
  },
  "secret": "webhook-secret-for-signature",
  "enabled": true
}
```

### 4.2 支持的事件

| 事件 | 说明 |
|------|------|
| `alert.critical` | 严重告警 |
| `alert.warning` | 警告告警 |
| `alert.info` | 信息告警 |
| `alert.*` | 所有告警 |
| `inference.result` | 推理结果 |

### 4.3 回调格式

```json
{
  "event": "alert.critical",
  "timestamp": "2025-01-15T10:30:00",
  "data": {
    "device_id": "jetson-001",
    "alert_level": "critical",
    "alert_message": "检测到异常",
    "image_url": "/api/v1/files/download?key=inference/xxx.jpg",
    "model_name": "water_inspection",
    "inference_time_ms": 45.2
  }
}
```

### 4.4 签名验证

如果配置了 `secret`，回调会携带 `X-Webhook-Secret` header，用于验证请求来源。

## 5. MQTT 实时订阅

### 5.1 连接信息

| 参数 | 值 |
|------|-----|
| Broker | `tcp://<HOST>:1883` |
| WebSocket | `ws://<HOST>/mqtt/ws` |
| 用户名 | admin |
| 密码 | .env 中 `EMQX_PASSWORD` |

### 5.2 Topic 格式

| Topic | 方向 | 说明 |
|-------|------|------|
| `device/{deviceId}/inference/results` | 边缘→云端 | 边缘推理结果上报 |
| `results/unified` | 平台内部 | EMQX 规则引擎统一转发 |
| `device/{deviceId}/config/update` | 云端→边缘 | 配置下发 |
| `device/{deviceId}/ota/command` | 云端→边缘 | OTA 升级命令 |
| `device/{deviceId}/cloud/frame` | 云端→边缘 | 触发云端推理 |

### 5.3 推理结果 Payload

```json
{
  "device_id": "jetson-001",
  "frame_id": 12345,
  "channel_id": "cam1",
  "timestamp": "2025-01-15T10:30:00.123",
  "source": "edge",
  "segments": {
    "water_stain": {
      "area": 0.0523,
      "score": 0.89,
      "bbox": [100, 200, 300, 400],
      "class_name_cn": "水渍"
    }
  },
  "alerts": [
    {
      "level": "warning",
      "message": "水渍面积超标: 5.2%"
    }
  ],
  "inference_time_ms": 45.2
}
```

## 6. WebSocket 实时推送

### 6.1 连接

STOMP over WebSocket：

```javascript
const socket = new SockJS('http://<HOST>/ws');
const stompClient = Stomp.over(socket);
stompClient.connect({}, () => {
  // 订阅推理结果
  stompClient.subscribe('/topic/inference/{deviceId}/results', (msg) => {
    console.log(JSON.parse(msg.body));
  });

  // 订阅训练进度
  stompClient.subscribe('/topic/training/{jobId}/progress', (msg) => {
    console.log(JSON.parse(msg.body));
  });
});
```

### 6.2 推送 Topic

| Topic | 数据 |
|-------|------|
| `/topic/inference/{deviceId}/results` | 推理结果（含图片URL） |
| `/topic/training/{jobId}/progress` | 训练进度和日志 |
| `/topic/ota/{taskId}/progress` | OTA 升级进度 |
