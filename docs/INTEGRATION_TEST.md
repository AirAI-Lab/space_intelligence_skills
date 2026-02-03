# 云边协同联调测试方案

## 项目概述

本方案用于 edge_infer_cloud（云平台）与 edge_infer（边缘推理端）的联调测试。

## 一、环境准备

### 1.1 云端环境 (edge_infer_cloud)

**位置**: `d:\github\edge_infer_cloud`

**服务组件**:
- 后端: Spring Boot (端口 8081)
- 前端: Vue 3 (端口 3000)
- 训练服务: Flask (端口 5000)
- MQTT Broker: EMQX (端口 1883)
- S3存储: SeaweedFS (端口 8333)

**启动命令**:
```bash
cd d:\github\edge_infer_cloud

# 启动后端
cd backend
mvn spring-boot:run

# 启动前端
cd frontend
npm run dev

# 启动训练服务
cd training
python app.py

# 使用 Docker Compose 启动所有服务
docker-compose up -d
```

### 1.2 边缘端环境 (edge_infer)

**位置**: `D:\github\edge_infer`

**Docker GPU 环境**:
```bash
cd D:\github\edge_infer

# 构建 GPU Docker 镜像
docker build -f Dockerfile.dev.gpu -t edge-infer:gpu .

# 运行容器
docker run -d --gpus all \
  --name edge-infer-test \
  -p 1884:1883 \
  -p 8554:8554 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/models:/app/models \
  edge-infer:gpu
```

**Windows 本地运行**:
```bash
# 使用 Visual Studio 2022
# 打开解决方案并编译运行
```

### 1.3 MQTT 测试工具

**MQTTX** (推荐): https://mqttx.app/zh

**MQTT Explorer**: https://mqtt-explorer.com/

---

## 二、通信协议

### 2.1 MQTT 主题定义

| 主题 | 方向 | 用途 |
|------|------|------|
| `device/{device_id}/heartbeat` | 边缘→云 | 设备心跳 |
| `device/{device_id}/status` | 边缘→云 | 设备状态上报 |
| `device/{device_id}/inference/result` | 边缘→云 | 推理结果上报 |
| `device/{device_id}/ota/status` | 边缘→云 | OTA状态反馈 |
| `device/{device_id}/ota/update` | 云→边缘 | OTA更新推送 |
| `device/{device_id}/config/update` | 云→边缘 | 配置更新 |
| `device/{device_id}/command/restart` | 云→边缘 | 重启命令 |

### 2.2 消息格式示例

**设备注册消息**:
```json
{
  "device_id": "EDGE_001",
  "device_name": "边缘设备1号",
  "device_type": "EDGE_BOX",
  "ip": "192.168.1.100",
  "mac": "00:11:22:33:44:55",
  "os_version": "Ubuntu 22.04",
  "agent_version": "1.0.0",
  "gpu_model": "NVIDIA RTX 3060",
  "gpu_memory": 12288,
  "status": "online"
}
```

**OTA 更新推送**:
```json
{
  "task_id": "OTA001",
  "upgrade_type": "MODEL",
  "model_id": "M001",
  "model_name": "安全帽检测v2",
  "model_version": "2.1.0",
  "download_url": "http://192.168.1.10:8333/edge-cloud/models/M001/best.engine",
  "file_size": 25600000,
  "md5": "abc123def456...",
  "target_path": "/app/models/helmet_detect/",
  "reload": true
}
```

**OTA 状态反馈**:
```json
{
  "task_id": "OTA001",
  "device_id": "EDGE_001",
  "status": "DOWNLOADING",
  "progress": 45,
  "error": null,
  "timestamp": "2026-01-27T10:30:00Z"
}
```

---

## 三、端到端测试流程

### 测试场景1: 设备注册与心跳

**步骤**:
1. 启动 edge_infer 边缘端
2. 边缘端自动连接 MQTT Broker
3. 发送设备注册消息
4. 云平台接收并存储设备信息

**验证**:
- 云平台设备列表显示新设备
- 设备状态为"在线"
- 设备信息正确显示

**MQTT 主题**:
```
发送: device/EDGE_001/heartbeat
订阅: device/+/heartbeat
```

---

### 测试场景2: 模型训练与下发

**步骤**:
1. 云平台创建数据集
2. 创建训练任务
3. 训练完成后生成模型
4. 创建 OTA 任务推送模型
5. 边缘端接收并下载模型
6. 边缘端应用新模型

**验证**:
- 训练任务正常完成
- 模型文件正确上传到 S3
- OTA 任务创建成功
- 边缘端成功下载模型
- 模型 MD5 校验通过
- 推理结果使用新模型

**相关文件**:
- 云端: `frontend/src/views/training/TrainingJob.vue`
- 云端: `backend/src/main/java/com/edge/cloud/controller/TrainingController.java`
- 云端: `backend/src/main/java/com/edge/cloud/service/MqttService.java`
- 边缘: `D:/github/edge_infer/src/mqtt/ota_handler.h`

---

### 测试场景3: 实时推理与结果上报

**步骤**:
1. 边缘端加载模型
2. 连接 RTSP 视频流
3. 执行推理
4. 上报推理结果到云端

**验证**:
- 推理 FPS 正常
- 检测结果准确
- 云平台接收结果

**MQTT 主题**:
```
发送: device/EDGE_001/inference/result
订阅: device/+/inference/result
```

---

### 测试场景4: OTA 升级失败回滚

**步骤**:
1. 推送损坏的模型文件
2. 边缘端检测校验失败
3. 自动回滚到旧版本
4. 上报失败状态

**验证**:
- MD5 校验失败被检测
- 回滚成功
- 云平台显示失败状态
- 推理继续正常工作

---

## 四、测试工具与脚本

### 4.1 MQTT 测试脚本

创建 `scripts/test/mqtt_test.py`:

```python
import paho.mqtt.client as mqtt
import json
import time

# MQTT 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe("device/#")

def on_message(client, userdata, msg):
    print(f"\n[{msg.topic}]")
    print(json.dumps(json.loads(msg.payload.decode()), indent=2, ensure_ascii=False))

# 创建客户端
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# 连接
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# 发送设备注册
device_id = "EDGE_TEST_001"
register_msg = {
    "device_id": device_id,
    "device_name": "测试设备",
    "device_type": "EDGE_BOX",
    "status": "online"
}
client.publish(f"device/{device_id}/heartbeat", json.dumps(register_msg))

# 循环监听
client.loop_forever()
```

### 4.2 模拟边缘端脚本

创建 `scripts/test/mock_edge_client.py`:

```python
"""
模拟边缘端客户端，用于测试云平台功能
"""
import paho.mqtt.client as mqtt
import json
import time
import hashlib
import random
from datetime import datetime

DEVICE_ID = "EDGE_MOCK_001"
BROKER = "localhost"
PORT = 1883

class MockEdgeClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.current_model = "v1.0.0"

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected: {rc}")
        # 订阅 OTA 相关主题
        client.subscribe(f"device/{DEVICE_ID}/ota/update")
        client.subscribe(f"device/{DEVICE_ID}/config/update")
        client.subscribe(f"device/{DEVICE_ID}/command/restart")

    def on_message(self, client, userdata, msg):
        print(f"\n[Received] {msg.topic}")
        payload = json.loads(msg.payload.decode())
        print(json.dumps(payload, indent=2))

        # 处理 OTA 更新
        if "ota/update" in msg.topic:
            self.handle_ota_update(payload)

    def handle_ota_update(self, payload):
        """模拟 OTA 更新流程"""
        task_id = payload.get("task_id")
        print(f"\n[OTA Update] Task: {task_id}")

        # 发送进度更新
        for progress in range(0, 101, 20):
            self.send_ota_status(task_id, "DOWNLOADING", progress)
            time.sleep(1)

        # 完成
        self.send_ota_status(task_id, "COMPLETED", 100)
        self.current_model = payload.get("model_version")

    def send_ota_status(self, task_id, status, progress):
        """发送 OTA 状态"""
        msg = {
            "task_id": task_id,
            "device_id": DEVICE_ID,
            "status": status,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        }
        self.client.publish(
            f"device/{DEVICE_ID}/ota/status",
            json.dumps(msg)
        )
        print(f"[OTA Status] {status}: {progress}%")

    def send_heartbeat(self):
        """发送心跳"""
        msg = {
            "device_id": DEVICE_ID,
            "device_name": "模拟边缘设备",
            "device_type": "EDGE_BOX",
            "status": "online",
            "cpu_usage": random.randint(20, 80),
            "gpu_usage": random.randint(30, 90),
            "memory_usage": random.randint(40, 70),
            "model_version": self.current_model,
            "inference_fps": random.randint(20, 30)
        }
        self.client.publish(
            f"device/{DEVICE_ID}/heartbeat",
            json.dumps(msg)
        )

    def start(self):
        """启动客户端"""
        self.client.connect(BROKER, PORT, 60)
        self.client.loop_start()

        # 定时发送心跳
        while True:
            self.send_heartbeat()
            time.sleep(5)

if __name__ == "__main__":
    client = MockEdgeClient()
    client.start()
```

### 4.3 API 测试脚本

创建 `scripts/test/api_test.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8081/api/v1"

echo "=== 测试设备列表 ==="
curl -X GET "$BASE_URL/devices?page=1&page_size=10"

echo -e "\n\n=== 测试创建 OTA 任务 ==="
curl -X POST "$BASE_URL/ota/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "测试OTA任务",
    "upgrade_type": "MODEL",
    "model_id": "M001",
    "device_ids": ["EDGE_MOCK_001"],
    "strategy": "IMMEDIATE"
  }'

echo -e "\n\n=== 测试启动 OTA 任务 ==="
curl -X POST "$BASE_URL/ota/tasks/OTA001/start"
```

---

## 五、阶段三功能实施

### 5.1 灰度发布服务

创建 `backend/src/main/java/com/edge/cloud/service/GradualRolloutService.java`

### 5.2 自动回滚服务

创建 `backend/src/main/java/com/edge/cloud/service/AutoRollbackService.java`

### 5.3 设备健康监控

创建 `backend/src/main/java/com/edge/cloud/service/DeviceHealthMonitorService.java`

---

## 六、常见问题排查

### 6.1 MQTT 连接失败

**检查**:
- EMQX 是否运行: `docker ps | grep emqx`
- 端口是否开放: `netstat -an | grep 1883`
- 防火墙设置

**解决方案**:
```bash
# 重启 EMQX
docker-compose restart emqx

# 查看日志
docker logs emqx
```

### 6.2 模型下载失败

**检查**:
- S3 存储是否可访问
- 网络连接
- 文件权限

**解决方案**:
```bash
# 测试 S3 连接
curl http://localhost:8333/edge-cloud/

# 检查 SeaweedFS 日志
docker logs seaweedfs
```

### 6.3 推理无结果

**检查**:
- 模型文件是否正确加载
- 视频流是否正常
- 日志输出

**解决方案**:
```bash
# 查看边缘端日志
docker logs edge-infer-test

# 进入容器检查
docker exec -it edge-infer-test bash
ls -la /app/models/
```

---

## 七、测试检查清单

- [ ] 云端服务正常启动（后端、前端、训练服务）
- [ ] MQTT Broker 可连接
- [ ] S3 存储可访问
- [ ] 边缘端容器正常运行
- [ ] 设备心跳正常
- [ ] 设备列表显示正确
- [ ] 数据集上传成功
- [ ] 训练任务创建成功
- [ ] 训练正常完成
- [ ] 模型上传到 S3
- [ ] OTA 任务创建成功
- [ ] 边缘端接收 OTA 消息
- [ ] 模型下载成功
- [ ] MD5 校验通过
- [ ] 模型加载成功
- [ ] 推理正常工作
- [ ] 结果上报到云端
- [ ] WebSocket 实时更新正常
