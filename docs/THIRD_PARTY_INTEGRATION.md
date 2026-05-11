# 第三方平台对接指南

本文档面向第三方平台开发人员，介绍如何接收 SkyEdge AI 平台的告警信息、查询推理结果、获取推理图片和视频流。

## 目录

- [1. 概述](#1-概述)
- [2. 对接方式总览](#2-对接方式总览)
- [3. 方式一：Webhook 主动推送（推荐）](#3-方式一webhook-主动推送推荐)
- [4. 方式二：REST API 主动查询](#4-方式二rest-api-主动查询)
- [5. 方式三：MQTT 消息订阅](#5-方式三mqtt-消息订阅)
- [6. 推理结果数据结构](#6-推理结果数据结构)
- [7. 视频流接入](#7-视频流接入)
- [8. 推理图片获取](#8-推理图片获取)
- [9. 完整对接示例（Python）](#9-完整对接示例python)

---

## 1. 概述

SkyEdge AI 平台采用 **边缘-云协同** 架构：

```
摄像头 → 边缘设备(Jetson) → 云端平台 → 第三方系统
            ↓                    ↓           ↓
       实时推理+推流        数据存储+转发   告警/结果/视频
```

- **边缘设备**：运行 TensorRT 推理，支持多路视频并行（多通道），检测目标并产生告警
- **云端平台**：汇聚所有边缘设备的推理结果，提供 REST API、Webhook、MQTT 三种对接方式
- **推理输出**：RTMP 推流（实时带框视频）、告警截图、结构化检测结果

### 服务地址

| 服务 | 端口 | 说明 |
|------|------|------|
| REST API | `8081` | 后端 API 服务 |
| 前端平台 | `3000` | Web 管理界面 |
| MQTT Broker | `1883` | EMQX 消息服务 |
| RTMP 推流 | `1935` | 流媒体服务 |
| 文件存储 | `8333` | S3 兼容文件服务 |

以下所有示例使用 `{HOST}` 表示平台服务器 IP 地址。

---

## 2. 对接方式总览

| 方式 | 方向 | 适用场景 | 实时性 |
|------|------|----------|--------|
| **Webhook** | 平台 → 第三方 | 接收告警推送、结果推送 | 准实时（<1s） |
| **REST API** | 第三方 → 平台 | 查询历史结果、统计数据、导出数据 | 按需 |
| **MQTT** | 双向 | 实时订阅推理结果、控制设备 | 实时（<100ms） |
| **RTMP** | 平台 → 第三方 | 播放带检测框的实时视频流 | 实时 |

**推荐组合**：Webhook（告警推送） + REST API（按需查询） + RTMP（视频展示）

---

## 3. 方式一：Webhook 主动推送（推荐）

平台在产生告警或推理结果时，主动向第三方配置的 HTTP 地址推送数据。

### 3.1 注册 Webhook

在平台管理界面（Webhook 配置页）或通过 API 注册：

```http
POST http://{HOST}:8081/api/v1/webhooks
Content-Type: application/json

{
  "name": "智飞系统告警接收",
  "url": "http://your-server.com/api/alerts",
  "secret": "your-secret-key",
  "events": "alert.warning,alert.critical",
  "enabled": true
}
```

### 3.2 事件类型

| 事件 | 说明 |
|------|------|
| `alert.warning` | 警告级告警（如人员未戴安全帽） |
| `alert.critical` | 严重级告警 |
| `alert.info` | 信息级告警 |
| `alert.*` | 所有告警事件 |
| `result.edge` | 边缘推理结果（每次上报） |
| `result.cloud` | 云端推理结果 |
| `*` | 所有事件 |

### 3.3 Webhook 推送格式

平台向第三方 URL 发送 POST 请求：

```http
POST http://your-server.com/api/alerts
Content-Type: application/json
X-Webhook-Secret: your-secret-key

{
  "event": "alert.warning",
  "timestamp": "2026-05-08T09:15:30.123",
  "data": {
    "id": 43748,
    "time": "2026-05-08T09:15:28",
    "device_id": "jetson_orin_001",
    "channel_id": "cam1",
    "source": "edge",
    "model_name": "helmet_detect",
    "task_type": "detect",
    "frame_id": 4106,
    "image_url": "/api/v1/files/download?key=inference/70162973-xxx.jpg",
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
          "class_id": 12,
          "class_name": "head",
          "confidence": 0.57,
          "bbox": [946, 234, 52, 52],
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
}
```

### 3.4 安全验证

第三方收到 Webhook 后，应验证 `X-Webhook-Secret` 请求头：

```python
import hmac

def verify_webhook(request):
    secret = request.headers.get("X-Webhook-Secret", "")
    if secret != "your-secret-key":
        return False
    return True
```

### 3.5 响应要求

第三方服务需返回 HTTP `200` 确认接收，否则平台会记录失败信息。

---

## 4. 方式二：REST API 主动查询

### 4.1 查询推理结果

```http
GET http://{HOST}:8081/api/v1/inference/results?page=1&page_size=20&device_id=jetson_orin_001&source=edge&has_alert=true
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码，默认 1 |
| `page_size` | int | 否 | 每页数量，默认 20 |
| `device_id` | string | 否 | 设备ID过滤 |
| `source` | string | 否 | 来源：`edge`（边缘）/ `cloud`（云端） |
| `alert_level` | string | 否 | 告警级别：`warning` / `critical` / `info` |
| `has_alert` | bool | 否 | `true`=仅返回有告警的记录 |
| `start_time` | datetime | 否 | 开始时间，ISO 格式 |
| `end_time` | datetime | 否 | 结束时间，ISO 格式 |

**响应示例**：

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
        "image_url": "/api/v1/files/download?key=inference/70162973-xxx.jpg",
        "result_json": { ... },
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

### 4.2 查询单条结果详情

```http
GET http://{HOST}:8081/api/v1/inference/results/{id}
```

### 4.3 查询告警列表

```http
GET http://{HOST}:8081/api/v1/inference/alerts?levels=warning,critical&page=1&page_size=20
```

### 4.4 统计数据（最近24小时）

```http
GET http://{HOST}:8081/api/v1/inference/stats
```

**响应示例**：

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

### 4.5 推理趋势（按小时聚合）

```http
GET http://{HOST}:8081/api/v1/inference/trend
```

### 4.6 导出数据

```http
GET http://{HOST}:8081/api/v1/inference/export?format=csv&start_time=2026-05-08T00:00:00&end_time=2026-05-08T23:59:59
```

支持 `csv` 和 `json` 两种格式。CSV 包含 BOM 头，兼容 Excel 直接打开。

---

## 5. 方式三：MQTT 消息订阅

适用于需要毫秒级实时性的场景。

### 5.1 连接信息

| 参数 | 值 |
|------|-----|
| Broker | `tcp://{HOST}:1883` |
| 用户名 | `admin` |
| 密码 | `admin123456` |
| 协议 | MQTT v3.1.1 |

### 5.2 订阅主题

**原始主题**（边缘/云端直接发布）：

| 主题 | 说明 |
|------|------|
| `device/+/inference/results` | 所有设备的边缘推理结果 |
| `device/{device_id}/inference/results` | 指定设备的边缘推理结果 |
| `device/+/cloud/result` | 所有设备的云端推理结果 |

**统一主题**（EMQX 规则引擎自动路由，推荐第三方使用）：

| 主题 | 说明 |
|------|------|
| `results/{device_id}/{channel_id}/edge` | 归一化后的边缘推理结果 |
| `results/{device_id}/{channel_id}/cloud` | 归一化后的云端推理结果 |
| `alerts/{device_id}/edge` | 边缘告警（仅含触发告警的结果） |
| `alerts/{device_id}/cloud` | 云端告警（仅含触发告警的结果） |

> **推荐**：第三方系统订阅 `results/#` 或 `alerts/#` 即可获取所有设备的归一化结果，无需关注原始 topic 格式。

### 5.3 消息格式

边缘推理结果消息（发布到 `device/jetson_orin_001/inference/results`）：

```json
{
  "device_id": "jetson_orin_001",
  "channel_id": "cam1",
  "model_id": "helmet_detect",
  "model_version": "1.0.0",
  "inference_time_ms": 25,
  "frame_count": 12345,
  "frame_width": 2554,
  "frame_height": 1422,
  "timestamp": "2026-05-08T09:15:28",
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
  ],
  "image_base64": "..."
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `device_id` | string | 边缘设备标识 |
| `channel_id` | string | 视频通道标识（cam1/cam2/cam3） |
| `model_id` | string | 推理模型标识 |
| `inference_time_ms` | int | 本次推理耗时（毫秒） |
| `detections` | array | 检测目标列表 |
| `detections[].class_name` | string | 目标类别名称 |
| `detections[].confidence` | float | 置信度（0.0-1.0） |
| `detections[].bbox` | int[4] | 边界框 [x, y, width, height] |
| `detections[].is_alert` | bool | 是否为告警目标 |
| `image_base64` | string | 可选，告警时的 JPEG 图片 Base64 |

### 5.4 Python 订阅示例

```python
import paho.mqtt.client as mqtt
import json

def on_connect(client, userdata, flags, rc):
    print(f"Connected: rc={rc}")
    # 订阅统一 topic（EMQX 规则引擎自动路由）
    client.subscribe("results/#")   # 所有设备的归一化推理结果
    client.subscribe("alerts/#")    # 所有设备的告警

def on_message(client, userdata, msg):
    result = json.loads(msg.payload.decode())
    device_id = result.get("device_id", "")
    channel_id = result.get("channel_id", "")

    if msg.topic.startswith("alerts/"):
        # 告警消息 — 优先处理
        print(f"[ALERT] {device_id}/{channel_id}: {result}")
    else:
        # 普通推理结果
        detections = result.get("detections", [])
        alerts = [d for d in detections if d.get("is_alert")]
        if alerts:
            for a in alerts:
                print(f"[ALERT] {device_id}/{channel_id}: "
                      f"{a['class_name']} conf={a['confidence']:.2f}")

client = mqtt.Client(client_id="third_party_subscriber")
client.username_pw_set("admin", "admin123456")
client.on_connect = on_connect
client.on_message = on_message
client.connect("192.168.0.103", 1883)
client.loop_forever()
```

---

## 6. 推理结果数据结构

### 检测类别（construction_safety 模型示例）

| class_id | class_name | 说明 |
|----------|------------|------|
| 0 | person | 人员 |
| 1 | bicycle | 自行车 |
| 2 | car | 汽车 |
| 3 | motorcycle | 摩托车 |
| 5 | bus | 公共汽车 |
| 7 | truck | 卡车 |
| 9 | traffic_light | 交通灯 |
| 10 | helmet | 安全帽（已佩戴） |
| 11 | no_helmet | 未佩戴安全帽 |
| 12 | head | 头部 |
| 13 | vest | 反光背心 |

> 实际类别取决于部署的模型，通过 `model_id` 字段区分不同模型的结果。

### 告警机制

告警由边缘侧 **插件链** 决定，不是简单的置信度阈值。当前规则：

| 触发条件 | 告警级别 | 说明 |
|----------|----------|------|
| 检测到 `person` 且 `is_alert=true` | warning | 人员进入检测区域 |
| 检测到 `no_helmet` 且 `is_alert=true` | warning | 未佩戴安全帽 |
| 其他配置规则 | info/warning/critical | 由告警规则表配置 |

`is_alert` 字段标识该检测是否触发告警，第三方系统应优先关注 `is_alert=true` 的检测结果。

### 多通道（channel_id）

一个边缘设备可接入多路摄像头，通过 `channel_id` 区分：

| channel_id | 说明 |
|------------|------|
| `cam1` | 第1路摄像头 |
| `cam2` | 第2路摄像头 |
| `cam3` | 第3路摄像头 |

---

## 7. 视频流接入

### 7.1 推理输出视频流（RTMP）

每路摄像头推理后的带检测框视频通过 RTMP 推流输出，第三方可直接播放：

| 通道 | RTMP 地址 | 说明 |
|------|-----------|------|
| cam1 | `rtmp://{HOST}:1935/stream/cam1_output` | 第1路推理结果流 |
| cam2 | `rtmp://{HOST}:1935/stream/cam2_output` | 第2路推理结果流 |
| cam3 | `rtmp://{HOST}:1935/stream/cam3_output` | 第3路推理结果流 |

> `{HOST}` 为边缘设备 IP（如 `192.168.0.107`），非云端服务器。

### 7.2 播放方式

**VLC 播放器**：
```
打开 VLC → 媒体 → 打开网络串流 → 输入 rtmp://192.168.0.107:1935/stream/cam1_output
```

**Web 播放（flv.js）**：

```html
<script src="https://cdn.jsdelivr.net/npm/flv.js/dist/flv.min.js"></script>
<video id="player" controls></video>
<script>
if (flvjs.isSupported()) {
  const player = flvjs.createPlayer({
    type: 'flv',
    url: 'http://192.168.0.107:8080/live/cam1_output.flv',  // 需要流媒体转封装
    isLive: true
  });
  player.attachMediaElement(document.getElementById('player'));
  player.load();
  player.play();
}
</script>
```

**FFplay 命令行**：

```bash
ffplay -fflags nobuffer rtmp://192.168.0.107:1935/stream/cam1_output
```

### 7.3 视频流规格

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 编码 | H.264 | 软编码 libx264（Jetson 时可能回退） |
| 分辨率 | 与输入一致 | 保持原始分辨率 |
| 帧率 | 跟随输入 | 通常 25-30fps |
| 关键帧间隔 | 15 | 低延迟优化 |
| 画框内容 | 实时检测框 | 包含类别名、置信度、边界框 |

---

## 8. 推理图片获取

每次告警或定期上报时，平台会存储推理截图。

### 8.1 通过结果中的 image_url 获取

推理结果的 `image_url` 字段提供图片下载路径：

```
/api/v1/files/download?key=inference/70162973-4352-4ff9-9bea-f9aaee8bff3c.jpg
```

完整 URL：

```
http://{HOST}:8081/api/v1/files/download?key=inference/70162973-xxx.jpg
```

### 8.2 直接访问文件存储

文件存储使用 S3 兼容协议（SeaweedFS），也可通过 S3 SDK 访问：

| 参数 | 值 |
|------|-----|
| Endpoint | `http://{HOST}:8333` |
| Bucket | `edge-cloud-files` |
| Key 前缀 | `inference/` |

---

## 9. 完整对接示例（Python）

以下是一个完整的第三方接收服务示例，展示如何通过 Webhook 和 MQTT 两种方式接收告警，并提供 REST API 查询。

```python
"""
第三方平台对接示例 - 智飞系统告警接收服务
依赖: pip install flask paho-mqtt requests
"""

from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import requests
import json
import threading

app = Flask(__name__)

# ========== 配置 ==========
PLATFORM_HOST = "192.168.0.103"     # SkyEdge 平台地址
PLATFORM_PORT = 8081                # API 端口
MQTT_HOST = PLATFORM_HOST           # MQTT Broker 地址
MQTT_PORT = 1883
MQTT_USER = "admin"
MQTT_PASS = "admin123456"
WEBHOOK_SECRET = "your-secret-key"  # 与平台注册时一致

# ========== Webhook 接收端 ==========

@app.route("/api/alerts", methods=["POST"])
def receive_webhook():
    """接收平台推送的告警/结果 Webhook"""
    # 1. 验证安全性
    secret = request.headers.get("X-Webhook-Secret", "")
    if secret != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    # 2. 解析数据
    payload = request.json
    event_type = payload.get("event", "")
    data = payload.get("data", {})

    device_id = data.get("device_id", "")
    channel_id = data.get("channel_id", "")
    alert_level = data.get("alert_level", "")
    alert_message = data.get("alert_message", "")
    detections = data.get("result_json", {}).get("detections", [])
    image_url = data.get("image_url", "")

    # 3. 过滤告警目标
    alert_targets = [d for d in detections if d.get("is_alert")]

    print(f"[Webhook] {event_type} | {device_id}/{channel_id} "
          f"| {alert_level}: {alert_message}")
    for t in alert_targets:
        print(f"  -> {t['class_name']} conf={t['confidence']:.2f} bbox={t['bbox']}")

    # 4. 构建第三方系统需要的格式并转发
    zhifei_alert = {
        "source": "skyedge_ai",
        "device_id": device_id,
        "camera_id": channel_id,
        "alert_type": alert_level,
        "alert_time": data.get("time", ""),
        "description": alert_message,
        "targets": [
            {
                "type": t["class_name"],
                "confidence": round(t["confidence"], 4),
                "bbox": t["bbox"]
            }
            for t in alert_targets
        ],
        "image_url": f"http://{PLATFORM_HOST}:{PLATFORM_PORT}{image_url}" if image_url else None,
        "video_url": f"rtmp://192.168.0.107:1935/stream/{channel_id}_output"
    }

    # TODO: 转发到智飞系统 API
    # requests.post("http://zhifei-server/api/alerts", json=zhifei_alert)

    return jsonify({"status": "ok"}), 200


# ========== REST API 主动查询 ==========

def query_recent_alerts(device_id=None, hours=1):
    """查询最近 N 小时的告警"""
    from datetime import datetime, timedelta
    end_time = datetime.now().isoformat()
    start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

    params = {
        "has_alert": "true",
        "start_time": start_time,
        "end_time": end_time,
        "page": 1,
        "page_size": 50
    }
    if device_id:
        params["device_id"] = device_id

    resp = requests.get(
        f"http://{PLATFORM_HOST}:{PLATFORM_PORT}/api/v1/inference/results",
        params=params
    )
    return resp.json()


def get_inference_stats():
    """获取推理统计数据"""
    resp = requests.get(
        f"http://{PLATFORM_HOST}:{PLATFORM_PORT}/api/v1/inference/stats"
    )
    return resp.json()


# ========== MQTT 实时订阅 ==========

def start_mqtt_subscriber():
    """后台线程：订阅 MQTT 实时推理结果"""
    def on_connect(client, userdata, flags, rc):
        print(f"[MQTT] Connected: rc={rc}")
        client.subscribe("device/+/inference/results")

    def on_message(client, userdata, msg):
        try:
            result = json.loads(msg.payload.decode())
            alerts = [d for d in result.get("detections", []) if d.get("is_alert")]
            if not alerts:
                return

            device_id = result.get("device_id", "")
            channel_id = result.get("channel_id", "")
            print(f"[MQTT] ALERT {device_id}/{channel_id}: "
                  f"{len(alerts)} target(s)")
            for a in alerts:
                print(f"  -> {a['class_name']} {a['confidence']:.2f}")

            # TODO: 转发到智飞系统
        except Exception as e:
            print(f"[MQTT] Error: {e}")

    client = mqtt.Client(client_id="zhifei_subscriber")
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_forever()

# 启动 MQTT 订阅线程
mqtt_thread = threading.Thread(target=start_mqtt_subscriber, daemon=True)
mqtt_thread.start()

if __name__ == "__main__":
    print("智飞系统对接服务启动...")
    print(f"Webhook 接收地址: http://your-server:5000/api/alerts")
    print(f"请将此地址注册到 SkyEdge 平台 Webhook 配置中")
    app.run(host="0.0.0.0", port=5000)
```

### 运行

```bash
pip install flask paho-mqtt requests
python zhifei_integration.py
```

---

## 附录

### A. 网络要求

| 方向 | 端口 | 协议 | 用途 |
|------|------|------|------|
| 第三方 → 平台 | 8081 | HTTP | REST API 查询 |
| 第三方 → 平台 | 1883 | MQTT | 消息订阅 |
| 平台 → 第三方 | 自定义 | HTTP | Webhook 推送 |
| 第三方 → 边缘 | 1935 | RTMP | 视频流播放 |

### B. 常见问题

**Q: Webhook 收不到推送？**
- 确认第三方服务的 URL 可从平台服务器访问（非内网地址）
- 检查平台 Webhook 配置中 `events` 是否包含目标事件类型
- 确认 `enabled` 为 `true`

**Q: MQTT 连接失败？**
- 检查用户名密码是否正确
- 确认 1883 端口可访问
- 使用 MQTTX 等工具先测试连通性

**Q: 视频流无法播放？**
- RTMP 地址中的 HOST 是边缘设备 IP（如 192.168.0.107），不是云端服务器
- 确认边缘设备上的 RTMP 服务正在运行
- 使用 VLC 或 ffplay 测试

**Q: 如何获取完整的检测结果列表（不只是告警）？**
- 使用 REST API `/api/v1/inference/results` 查询全部结果
- Webhook 注册时 `events` 设为 `result.edge` 可接收每次推理上报
