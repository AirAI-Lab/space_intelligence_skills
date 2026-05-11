# edge_infer_cloud API 文档

## 基础信息

- **Base URL**: `http://{HOST}:8081/api/v1`
- **Content-Type**: `application/json`
- **认证方式**: Bearer Token（即将支持）

> 端口说明：后端 API 映射在 8081（容器内 8080），前端在 3000，MQTT 在 1883。

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

---

## 推理结果 API

### 查询推理结果

```http
GET /api/v1/inference/results?page=1&page_size=20&device_id=jetson_orin_001&source=edge&has_alert=true
```

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码，默认 1 |
| `page_size` | int | 否 | 每页数量，默认 20 |
| `device_id` | string | 否 | 设备ID过滤 |
| `source` | string | 否 | 来源：`edge` / `cloud` |
| `alert_level` | string | 否 | 告警级别：`warning` / `critical` / `info` |
| `has_alert` | bool | 否 | `true`=仅返回有告警的记录 |
| `start_time` | datetime | 否 | 开始时间（ISO 格式） |
| `end_time` | datetime | 否 | 结束时间（ISO 格式） |

**响应**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1288,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "id": 43748,
        "time": "2026-05-08T09:15:28",
        "device_id": "jetson_orin_001",
        "channel_id": "cam1",
        "source": "edge",
        "model_name": "helmet_detect",
        "task_type": "detect",
        "frame_id": 4106,
        "image_url": "/api/v1/files/download?key=inference/xxx.jpg",
        "result_json": {
          "channel_id": "cam1",
          "model_id": "helmet_detect",
          "model_version": "1.0.0",
          "frame_width": 2554,
          "frame_height": 1422,
          "detections": [
            {
              "class_id": 0,
              "class_name": "person",
              "confidence": 0.77,
              "bbox": [925, 211, 122, 191],
              "is_alert": true
            },
            {
              "class_id": 10,
              "class_name": "helmet",
              "confidence": 0.73,
              "bbox": [795, 560, 18, 17],
              "is_alert": false
            }
          ]
        },
        "alert_level": "warning",
        "alert_message": "person 检出 (置信度: 0.77)",
        "inference_time_ms": 19.0,
        "detection_count": 3,
        "summary_text": "边缘检测: 3个目标"
      }
    ]
  }
}
```

### 获取推理结果详情

```http
GET /api/v1/inference/results/{id}
```

### 查询告警列表

```http
GET /api/v1/inference/alerts?levels=warning,critical&page=1&page_size=20
```

### 推理统计（最近24小时）

```http
GET /api/v1/inference/stats
```

**响应**：

```json
{
  "code": 200,
  "data": {
    "totalResults": 2540,
    "totalAlerts": 1213,
    "edgeResults": 2399,
    "cloudResults": 141,
    "alertsByLevel": {
      "warning": 1073,
      "info": 140
    },
    "deviceStats": [
      {
        "deviceId": "jetson_orin_001",
        "count": 2399,
        "avgInferenceMs": 25.2
      }
    ]
  }
}
```

### 推理趋势（按小时聚合，最近24小时）

```http
GET /api/v1/inference/trend
```

### 导出推理结果

```http
GET /api/v1/inference/export?format=csv&start_time=2026-05-08T00:00:00&end_time=2026-05-08T23:59:59
```

支持 `csv`（含 BOM，兼容 Excel）和 `json` 格式。

### 清空所有推理结果

```http
DELETE /api/v1/inference/results
```

### 云端推理结果上报

```http
POST /api/v1/cloud/inference/result
Content-Type: application/json

{
  "device_id": "cloud_gpu",
  "frame_id": 12345,
  "inference_time_ms": 1200.5,
  "segments": { ... },
  "alerts": [ ... ],
  "image_base64": "..."
}
```

### 边缘推理结果上报

```http
POST /api/v1/edge/inference/result
Content-Type: application/json

{
  "device_id": "jetson_orin_001",
  "channel_id": "cam1",
  "model_id": "helmet_detect",
  "model_version": "1.0.0",
  "inference_time_ms": 25,
  "frame_count": 12345,
  "frame_width": 2554,
  "frame_height": 1422,
  "detections": [
    {
      "class_id": 0,
      "class_name": "person",
      "confidence": 0.77,
      "bbox": [925, 211, 122, 191],
      "is_alert": true
    }
  ],
  "timestamp": "2026-05-08T09:15:28",
  "image_base64": "..."
}
```

---

## Webhook 管理 API

### 创建 Webhook

```http
POST /api/v1/webhooks
Content-Type: application/json

{
  "name": "告警推送",
  "url": "http://your-server.com/api/alerts",
  "secret": "your-secret-key",
  "events": "alert.warning,alert.critical",
  "enabled": true
}
```

**事件类型**：

| 事件 | 说明 |
|------|------|
| `alert.warning` | 警告级告警 |
| `alert.critical` | 严重级告警 |
| `alert.info` | 信息级告警 |
| `alert.*` | 所有告警 |
| `result.edge` | 边缘推理结果 |
| `result.cloud` | 云端推理结果 |
| `*` | 所有事件 |

### 获取 Webhook 列表

```http
GET /api/v1/webhooks
```

### 更新 Webhook

```http
PUT /api/v1/webhooks/{id}
Content-Type: application/json

{
  "enabled": false
}
```

### 删除 Webhook

```http
DELETE /api/v1/webhooks/{id}
```

---

## 文件存储 API

### 下载推理图片

```http
GET /api/v1/files/download?key=inference/xxx.jpg
```

### 上传文件

```http
POST /api/v1/files/upload
Content-Type: multipart/form-data

file: <binary>
prefix: inference
```

---

## 设备管理 API

### 注册设备

```http
POST /api/v1/edge/register
Content-Type: application/json

{
  "device_id": "EDGE_DEVICE_001",
  "device_name": "边缘设备1",
  "device_type": "jetson_orin",
  "ip": "192.168.0.107",
  "cpu_usage": 45.5,
  "gpu_usage": 60.0,
  "memory_usage": 12.5
}
```

### 设备心跳

```http
POST /api/v1/edge/heartbeat
Content-Type: application/json

{
  "device_id": "EDGE_DEVICE_001",
  "cpu_usage": 45.5,
  "gpu_usage": 60.0,
  "memory_usage": 12.5,
  "gpu_temperature": 53.0,
  "current_model_id": "helmet_detect",
  "current_model_version": "1.0.0",
  "inference_fps": 25.0,
  "timestamp": "2026-05-08T09:15:28"
}
```

**响应**：

```json
{
  "status": "SUCCESS",
  "commands": []
}
```

### 获取设备列表

```http
GET /api/v1/device/list?page=1&page_size=20&status=ONLINE
```

### 获取设备状态

```http
GET /api/v1/edge/commands?device_id=EDGE_DEVICE_001
```

### 按设备类型查询

```http
GET /api/v1/devices/by-type?type=JETSON_ORIN
```

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 设备类型：`JETSON_ORIN` / `JETSON_XAVIER` / `JETSON_NANO` / `EDGE_BOX` / `DRONE` / `ROBOT_DOG` / `VEHICLE` / `SENSOR` / `CAMERA` |

### 按设备类别查询

```http
GET /api/v1/devices/by-category?category=EDGE_COMPUTE
```

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `category` | string | 是 | 设备类别：`EDGE_COMPUTE` / `UAV` / `ROBOTIC` / `VEHICLE` / `SENSOR` / `CAMERA` |

### 设备标签管理

```http
# 添加标签
POST /api/v1/devices/{deviceId}/tags
Content-Type: application/json

{"tagKey": "location", "tagValue": "工地A区"}

# 查询设备所有标签
GET /api/v1/devices/{deviceId}/tags

# 删除标签
DELETE /api/v1/devices/{deviceId}/tags/{tagKey}

# 按标签查找设备
GET /api/v1/devices/by-tag?tagKey=location&tagValue=工地A区
```

### 查询设备命令历史

```http
GET /api/v1/devices/{deviceId}/commands
```

**响应**：

```json
{
  "code": 200,
  "data": [
    {
      "commandId": "uuid-xxx",
      "commandType": "OTA_UPDATE",
      "status": "ACK",
      "params": {"model_id": "v2"},
      "createdAt": "2026-05-11T10:00:00",
      "acknowledgedAt": "2026-05-11T10:00:05"
    }
  ]
}
```

---

## OTA 管理 API

### 创建升级任务

```http
POST /api/v1/ota/create
Content-Type: application/json

{
  "task_name": "安全帽模型升级v2.0",
  "model_id": "helmet_detect_v2",
  "target_version": "2.0.0",
  "strategy": "rolling",
  "target_devices": ["jetson_orin_001"]
}
```

### 获取升级进度

```http
GET /api/v1/ota/{task_id}/progress
```

### 上报 OTA 状态（边缘设备调用）

```http
POST /api/v1/edge/ota/status
Content-Type: application/json

{
  "task_id": "OTA_001",
  "device_id": "jetson_orin_001",
  "status": "DOWNLOADING",
  "progress": 45
}
```

---

## WebSocket API

### 连接地址

```
ws://{HOST}:8081/ws
```

### 订阅主题（STOMP 协议）

| 主题 | 说明 |
|------|------|
| `/topic/inference/{device_id}/results` | 指定设备的推理结果 |
| `/topic/inference/alerts` | 所有设备的告警 |

### JavaScript 示例

```javascript
import SockJS from 'sockjs-client';
import { Stomp } from '@stomp/stompjs';

const socket = new SockJS('http://192.168.0.103:8081/ws');
const stompClient = Stomp.over(socket);

stompClient.connect({}, () => {
  // 订阅指定设备的推理结果
  stompClient.subscribe('/topic/inference/jetson_orin_001/results', (msg) => {
    const result = JSON.parse(msg.body);
    console.log('推理结果:', result.device_id, result.detection_count);
  });

  // 订阅所有告警
  stompClient.subscribe('/topic/inference/alerts', (msg) => {
    const alert = JSON.parse(msg.body);
    console.log('告警:', alert.alert_level, alert.alert_message);
  });
});
```

---

## MQTT API

边缘设备通过 MQTT 上报推理结果，第三方也可订阅相同主题获取实时数据。

**Broker**: `tcp://{HOST}:1883`

| 主题 | 方向 | 说明 |
|------|------|------|
| `device/{device_id}/inference/results` | 设备→云端 | 推理结果上报 |
| `device/{device_id}/ota/command` | 云端→设备 | OTA 升级命令 |
| `device/{device_id}/ota/status` | 设备→云端 | OTA 状态反馈 |
| `device/{device_id}/config/update` | 云端→设备 | 配置下发 |

### EMQX 规则引擎统一 Topic（推荐）

第三方通过 EMQX 规则引擎归一化后的统一 topic 订阅推理结果和告警：

| 统一 Topic | 说明 |
|------------|------|
| `results/{device_id}/{channel_id}/edge` | 边缘推理结果（归一化） |
| `results/{device_id}/{channel_id}/cloud` | 云端推理结果（归一化） |
| `alerts/{device_id}/edge` | 边缘告警 |
| `alerts/{device_id}/cloud` | 云端告警 |

> 详细对接方式见 [第三方对接指南](../THIRD_PARTY_INTEGRATION.md)

---

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

---

## curl 示例

```bash
# 查询推理结果
curl "http://192.168.0.103:8081/api/v1/inference/results?page=1&page_size=5"

# 查询告警
curl "http://192.168.0.103:8081/api/v1/inference/alerts?levels=warning,critical"

# 查询统计
curl "http://192.168.0.103:8081/api/v1/inference/stats"

# 导出 CSV
curl -o results.csv "http://192.168.0.103:8081/api/v1/inference/export?format=csv"

# 注册 Webhook
curl -X POST http://192.168.0.103:8081/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{"name":"test","url":"http://your-server/webhook","events":"alert.*","enabled":true}'

# 边缘推理结果上报
curl -X POST http://192.168.0.103:8081/api/v1/edge/inference/result \
  -H "Content-Type: application/json" \
  -d '{"device_id":"test_device","model_id":"helmet_detect","detections":[{"class_id":0,"class_name":"person","confidence":0.95,"bbox":[100,200,50,100],"is_alert":true}]}'
```
