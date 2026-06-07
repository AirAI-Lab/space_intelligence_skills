# 云边协同推理管线 — 实现与部署文档

> 面向后续开发/运维人员，涵盖架构设计、数据流、关键实现、部署步骤和常见问题排查。

---

## 1. 系统架构概览

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        边缘设备 (Jetson Orin)                            │
│  ┌─────────┐   ┌──────────────┐   ┌──────────────────────────────────┐  │
│  │ 相机/RTMP │──▶│ YOLOv8 推理   │──▶│ ReportInferenceResult()        │  │
│  └─────────┘   │ + 插件链过滤  │   │  ├─ REST POST /edge/inference/  │  │
│                └──────────────┘   │  ├─ MQTT  device/{id}/inference/  │  │
│                                   │  └─ 标注框绘制 + 图片上传        │  │
│                                   └──────────────────────────────────┘  │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ REST + MQTT 双通道
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     云端后端 (Spring Boot 3.x)                           │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────────────────────┐  │
│  │ MqttService  │  │ InferenceResult  │  │ WebSocketMessageService   │  │
│  │ 订阅推理结果  │─▶│ Service          │─▶│ 推送到前端 + Webhook      │  │
│  │ 订阅OTA状态  │  │ 存储 + 告警 +    │  └────────────────────────────┘  │
│  │ 触发云端推理  │  │ 规则匹配 + 导出  │                                   │
│  └─────────────┘  └──────────────────┘                                    │
│         │                                        │                        │
│         │ MQTT: device/{id}/cloud/frame          │ REST                   │
│         ▼                                        ▼                        │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │              云端推理服务 (C-RADIOv4 零样本分割)                   │    │
│  │  ┌───────────────┐   ┌─────────────┐   ┌──────────────────────┐ │    │
│  │  │ MQTT 模式      │   │ 流式模式     │   │ _report_to_backend() │ │    │
│  │  │ 订阅边缘推帧   │   │ RTMP 采样   │──▶│ POST /cloud/infer/   │ │    │
│  │  └───────────────┘   └─────────────┘   └──────────────────────┘ │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌──────────────────┐               ┌─────────────────────┐
│ PostgreSQL       │               │ SeaweedFS (S3)      │
│ TimescaleDB 超表  │               │ 推理图片存储         │
└──────────────────┘               └─────────────────────┘
```

---

## 2. 数据流详解

### 2.1 边缘端 → 云端（推理结果上报）

边缘端同时通过 **REST API** 和 **MQTT** 两条通道上报：

| 通道 | 地址 | 触发条件 |
|------|------|----------|
| REST | `POST /api/v1/edge/inference/result` | 有告警立即上报，无告警每 30 帧上报一次 |
| MQTT | `device/{device_id}/inference/results` | 同上 |

后端两个入口最终都调用 `InferenceResultService.saveEdgeResult()`，保证数据一致性。

### 2.2 云端推理服务 → 后端

`radio_infer_server.py` 推理完成后通过 REST 上报：

```
POST /api/v1/cloud/inference/result
```

同时也通过 MQTT 发布到 `device/{device_id}/cloud/result` 供边缘端直接接收。

### 2.3 后端 → 前端（实时推送）

```
WebSocket 订阅主题:
  /topic/inference/{device_id}/results  — 设备级结果流
  /topic/inference/alerts               — 全局告警流
```

### 2.4 告警规则 → 触发云端推理

当边缘端告警满足规则条件（`trigger_cloud_infer = true`）时：

1. `AlertRuleService.shouldTriggerCloudInfer()` 匹配规则
2. `MqttService.triggerCloudInference()` 发送 MQTT 消息到 `device/{id}/cloud/frame`
3. 边缘设备收到后推送当前帧到云端
4. 云端 C-RADIOv4 执行零样本分割

---

## 3. 数据库设计

### 3.1 inference_results 表

位置：`backend/src/main/resources/schema.sql`

```sql
CREATE TABLE IF NOT EXISTS inference_results (
    id BIGSERIAL,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id VARCHAR(50) NOT NULL,
    source VARCHAR(20) NOT NULL,           -- 'edge' | 'cloud'
    model_name VARCHAR(200),
    task_type VARCHAR(50),                 -- 'detect' | 'segment' | 'classify'
    frame_id BIGINT,
    image_url VARCHAR(500),
    result_json JSONB,                     -- 完整检测结果或分割结果
    alert_level VARCHAR(20),              -- NULL | 'info' | 'warning' | 'critical'
    alert_message TEXT,
    inference_time_ms FLOAT,
    detection_count INT DEFAULT 0,
    summary_text VARCHAR(500),
    PRIMARY KEY (time, id)
);

SELECT create_hypertable('inference_results', 'time', if_not_exists => TRUE);

CREATE INDEX idx_ir_device_time ON inference_results(device_id, time DESC);
CREATE INDEX idx_ir_alert_time ON inference_results(alert_level, time DESC)
    WHERE alert_level IS NOT NULL;
CREATE INDEX idx_ir_source ON inference_results(source);
CREATE INDEX idx_ir_result_json ON inference_results USING gin(result_json);
```

**设计要点**：

- 使用 TimescaleDB 超表按 `time` 自动分区，适合时序数据高频写入
- `result_json` 使用 JSONB 类型，支持 GIN 索引的灵活查询
- `source` 区分边缘检测结果（`edge`）和云端分割结果（`cloud`）
- 部分索引 `idx_ir_alert_time` 仅索引有告警的行，节省空间

---

## 4. REST API 接口

### 4.1 云端推理结果上报

```
POST /api/v1/cloud/inference/result
Content-Type: application/json
```

请求体（CloudInferenceResultRequest）：

```json
{
  "device_id": "cloud_gpu_103",
  "frame_id": 636,
  "timestamp": "2026-04-24T21:47:44",
  "inference_time_ms": 1194.4,
  "segments": {
    "bare_soil_uncovered": {
      "area": 0.7205,
      "score": 0.5576,
      "bbox": [0, 0, 2553, 1421],
      "class_name_cn": "裸土未覆盖"
    }
  },
  "alerts": [
    {
      "class_name": "bare_soil_uncovered",
      "class_name_cn": "裸土未覆盖",
      "level": "warning",
      "message": "裸土未覆盖，面积占比 72.0%",
      "area": 0.7205
    }
  ],
  "image_base64": "..."
}
```

### 4.2 边缘端推理结果上报

```
POST /api/v1/edge/inference/result
```

请求体（InferenceResultRequest）：

```json
{
  "device_id": "jetson_orin_001",
  "model_id": "helmet_detect",
  "model_version": "v1.0",
  "inference_time_ms": 45.2,
  "frame_count": 1234,
  "frame_width": 1920,
  "frame_height": 1080,
  "timestamp": "2026-04-24T10:30:00",
  "image_base64": "...",
  "detections": [
    {
      "class_id": 0,
      "class_name": "person",
      "confidence": 0.95,
      "bbox": [100, 200, 300, 400],
      "is_alert": true
    }
  ]
}
```

**关键字段说明**：

- `is_alert`：由边缘端插件链（plugin_config.json）判断是否为告警目标，后端不做二次阈值判断
- `image_base64`：带标注框的 JPEG 图片（边缘端在 C++ 中用 OpenCV 绘制后编码）

### 4.3 推理结果查询

```
GET /api/v1/inference/results?page=1&page_size=20
    &device_id=xxx          # 可选，设备过滤
    &source=edge|cloud      # 可选，来源过滤
    &alert_level=critical   # 可选，告警级别
    &has_alert=true         # 仅返回有告警的记录
    &start_time=...&end_time=...  # 时间范围
```

### 4.4 其他端点一览

| 方法 | 端点 | 用途 |
|------|------|------|
| GET | `/api/v1/inference/results/{id}` | 单条详情 |
| GET | `/api/v1/inference/alerts?levels=critical,warning` | 告警列表 |
| GET | `/api/v1/inference/stats` | 24 小时统计（总数、告警数、按设备统计） |
| GET | `/api/v1/inference/trend` | 24 小时趋势（按小时聚合、类别分布） |
| GET | `/api/v1/inference/export?format=csv|json` | 导出为 CSV 或 JSON |

---

## 5. MQTT Topic 清单

| Topic | 方向 | 用途 |
|-------|------|------|
| `device/+/inference/results` | 边缘→云端 | 边缘推理结果上报 |
| `device/{id}/cloud/frame` | 云端→边缘 | 触发云端推理请求 |
| `device/{id}/cloud/result` | 云端→边缘 | 云端分割结果返回 |
| `device/+/ota/status` | 边缘→云端 | OTA 升级进度上报 |
| `device/{id}/ota/command` | 云端→边缘 | OTA 升级命令下发 |
| `device/{id}/config/update` | 云端→边缘 | 配置推送 |
| `device/{id}/command/restart` | 云端→边缘 | 重启命令 |

---

## 6. 关键实现细节

### 6.1 边缘端标注框绘制（C++）

位置：`edge_infer/src/framework.cpp` — `ReportInferenceResult()` 方法

```cpp
// 在原始帧上绘制标注框
cv::Mat annotated = frame.clone();
for (const auto& det : detections) {
    // 告警目标用红色，正常目标用绿色
    cv::Scalar color = det.is_alert
        ? cv::Scalar(0, 0, 255)    // 红色 = 告警
        : cv::Scalar(0, 255, 0);   // 绿色 = 正常
    cv::rectangle(annotated,
        cv::Point(int(det.x1), int(det.y1)),
        cv::Point(int(det.x2), int(det.y2)), color, 2);
    // 标签: 类别名 + 置信度
    std::string label = det.class_name + " " +
        std::to_string(int(det.confidence * 100)) + "%";
    cv::putText(annotated, label,
        cv::Point(int(det.x1), int(det.y1) - 5),
        cv::FONT_HERSHEY_SIMPLEX, 0.5, color, 1);
}

// JPEG 编码 + base64
std::vector<uchar> buf;
cv::imencode(".jpg", annotated, buf, {cv::IMWRITE_JPEG_QUALITY, 70});
std::string b64 = base64_encode(buf.data(), buf.size());
```

### 6.2 云端推理背景类过滤

**问题**：场景配置中 `background` 类（`is_background: true`）的 prompt 信号过强，会抢占所有目标类的检测概率，导致「无检出」。

**修复**：在 `radio_infer_server.py` 加载配置后过滤掉背景类：

```python
# 过滤掉 background 类（is_background=true），避免抢占目标类
self._classes_config = {
    k: v for k, v in self._classes_config.items()
    if not v.get("is_background", False)
}
```

**位置**：`models/cloud_inference/plugin_base.py` — `ScenarioPlugin.load_config()` 自动过滤 `is_background` 类

### 6.3 Spring Boot 循环依赖处理

`MqttService` → `InferenceResultService` → `MqttService` 形成循环依赖。

**解决方案**：在 `MqttService` 中使用 `@Autowired @Lazy` 字段注入：

```java
@Autowired
@Lazy
private InferenceResultService inferenceResultService;
```

同时在 `application.yml` 中添加：

```yaml
spring:
  main:
    allow-circular-references: true
```

**注意**：不能使用构造器注入（`@RequiredArgsConstructor`）处理循环依赖的字段，需要将该字段从 `final` 中移除，改用 `@Autowired`。

### 6.4 图片上传与显示

**上传流程**：

1. 边缘端/云端推理后，JPEG 图片通过 `image_base64` 字段上传
2. 后端 Base64 解码后调用 `StorageService.uploadBytes()` 上传到 SeaweedFS
3. 返回 S3 key 对应的 URL 存入数据库 `image_url` 字段

**显示流程**：

1. 前端通过 `/api/v1/files/download?key=inference/xxx.jpg` 获取图片
2. `FileController` 根据文件扩展名设置正确的 `Content-Type`（如 `image/jpeg`）
3. `Content-Disposition` 设为 `inline`，允许浏览器直接渲染图片

### 6.5 告警判断机制

边缘端和云端使用不同的告警判断方式：

| 来源 | 告警判断方式 | 说明 |
|------|-------------|------|
| 边缘端 | `is_alert` 字段 | 由边缘端插件链（plugin_config.json）配置规则决定 |
| 云端 | 面积阈值 `ALERT_MIN_AREA` | 分割面积占比超过阈值即触发告警 |

后端不重复判断阈值，边缘端的 `is_alert` 标志直接作为是否产生告警的依据。

---

## 7. 云端推理服务（radio_infer_server.py）

### 7.1 双模式运行

| 模式 | 启用条件 | 输入来源 | 适用场景 |
|------|----------|----------|----------|
| MQTT 模式 | 默认（不设 STREAM_URL） | 边缘设备推帧 `device/+/cloud/frame` | 按需推理 |
| 流式模式 | 设置 `STREAM_URL` | RTMP/RTSP 视频流持续采样 | 主动巡检 |

两种模式共享同一套模型加载、推理、告警、上报逻辑。

### 7.2 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `STREAM_URL` | 空 | 设置后启用流式模式（RTMP/RTSP 地址） |
| `STREAM_INTERVAL` | 3 | 流式模式采样间隔（秒） |
| `STREAM_DEVICE_ID` | cloud_gpu | 流式模式的设备标识 |
| `MQTT_BROKER_URL` | tcp://emqx:1883 | MQTT Broker 地址 |
| `MQTT_USERNAME` | 空 | MQTT 认证用户名 |
| `MQTT_PASSWORD` | 空 | MQTT 认证密码 |
| `CONFIG_PATH` | water_inspection.yaml | 场景配置文件 |
| `RADIO_CHECKPOINT_PATH` | /app/models/C-RADIOv4-H/... | C-RADIOv4 模型权重路径 |
| `RADIO_CODE_DIR` | /app/models/NVlabs_RADIO | RADIO 官方代码路径 |
| `SIGLIP2_DIR` | /app/models/siglip2-giant-... | SigLIP2 模型路径 |
| `BACKEND_API_URL` | http://backend:8080 | 后端 API 地址 |
| `DEVICE` | cuda | 推理设备（cuda / cpu） |
| `INPUT_SIZE` | 896 | 输入图像尺寸 |
| `ALERT_MIN_AREA` | 0.01 | 告警最小面积阈值 |

### 7.3 告警映射表

服务内置了各场景的告警级别映射：

```python
alert_map = {
    # 水利巡检场景
    "black_water":        ("critical", "黑水污染"),
    "brown_water":        ("critical", "褐色水体"),
    "yellow_water":       ("warning",  "黄色水体"),
    "green_water":        ("warning",  "藻类爆发"),
    "red_water":          ("critical", "化学污染"),
    "milky_water":        ("warning",  "水体浑浊"),
    "foam_water":         ("warning",  "水面泡沫"),
    "dam_seepage":        ("critical", "坝体渗水"),
    # 施工安全场景
    "bare_soil_uncovered":    ("warning",  "裸土未覆盖"),
    "dust_pollution":         ("critical", "扬尘污染"),
    "pit_water_accumulation": ("warning",  "坑内积水"),
    "material_near_pit":      ("warning",  "基坑边材料堆放"),
}
```

### 7.4 标注图绘制

云端分割结果在图像上绘制半透明 mask + 标签：

```python
# 半透明覆盖
overlay = annotated.copy()
overlay[mask] = color  # 每个类别不同颜色
cv2.addWeighted(overlay, 0.4, annotated, 0.6, 0, annotated)

# 中心点标签
label = f"{seg.class_name_cn} {seg.area_ratio:.1%}"
cv2.putText(annotated, label, (cx, cy), font, 0.6, (255, 255, 255), 1)
```

输出 JPEG 缩放至 960px 宽以减小传输体积。

---

## 8. 前端页面

### 8.1 推理结果列表页（/inference）

文件：`frontend/src/views/inference/InferenceResultList.vue`

功能：
- 顶部过滤栏：设备ID、来源（边缘/云端）、告警级别、时间范围
- 结果表格：图片缩略图、时间、设备ID、来源标签、模型名称、任务类型、检出数、告警级别、推理耗时、摘要
- 点击行弹出详情对话框，显示完整 `result_json`
- 默认仅显示有告警的记录（`has_alert = true`）
- 支持分页（10/20/50 条/页）

### 8.2 告警中心页（/alerts）

文件：`frontend/src/views/inference/AlertCenter.vue`

功能：
- 统计卡片：critical / warning / info 各级告警数量
- 24 小时告警趋势图（ECharts 柱状图）
- 告警列表表格（含图片预览和详情弹窗）
- 支持按告警级别多选 + 时间范围过滤

### 8.3 告警规则管理页（/alert-rules）

文件：`frontend/src/views/inference/AlertRuleManage.vue`

功能：
- 配置字段：规则名称、设备ID、来源、类别名、模型名
- 条件类型：面积阈值 / 数量阈值 / 置信度阈值
- 关键开关：`trigger_cloud_infer`（满足条件时是否触发云端推理）、`enabled`
- 支持创建、编辑、删除规则

### 8.4 首页仪表盘

文件：`frontend/src/views/Home.vue`

新增内容：
- 「今日告警」统计卡片
- 推理趋势 24 小时折线+柱状组合图（总数量 + 告警数量）
- 最近告警列表（最近 10 条，含级别标签和告警消息）

---

## 9. 部署指南

### 9.1 环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Docker | 24+ | 容器运行时 |
| Docker Compose | v2+ | 容器编排工具 |
| NVIDIA Runtime | - | GPU 容器支持 |
| CUDA | 12.1+ | 云端推理 GPU 驱动 |
| 磁盘空间 | 50GB+ | 模型权重 + 图片存储 |

### 9.2 模型权重准备

```bash
# 项目根目录下的 models/ 目录结构
models/
├── C-RADIOv4-H/
│   └── c-radio_v4-h_half.pth.tar      # 1.68 GB，C-RADIOv4 权重
├── NVlabs_RADIO/                        # RADIO 官方代码
├── siglip2-giant-opt-patch16-384/       # 7.5 GB，SigLIP2 模型
├── water_inspection/                    # 水利巡检场景代码和配置
│   └── configs/water_inspection.yaml
└── construction_safety/                 # 施工安全场景代码和配置
    └── configs/construction_safety.yaml
```

### 9.3 启动基础服务

```bash
cd deployment/docker

# 1. 启动基础设施（数据库、缓存、消息队列、对象存储）
docker compose up -d postgres redis emqx seaweedfs mlflow portal

# 2. 等待服务就绪
sleep 15

# 3. 启动后端和前端
docker compose up -d backend frontend
```

### 9.4 启动云端推理服务

**方式一：独立容器（推荐生产使用）**

```bash
# 水利巡检场景（MQTT 模式，等待边缘推帧）
docker compose --profile gpu up -d cloud_infer

# 施工安全场景（流式模式，主动采样 RTMP 流）
CONFIG_PATH=/app/models/construction_safety/configs/construction_safety.yaml \
STREAM_URL=rtmp://192.168.0.103:1935/stream/safety_cam \
STREAM_INTERVAL=3 \
STREAM_DEVICE_ID=cloud_gpu \
docker compose --profile gpu up -d cloud_infer
```

**方式二：在 training 容器内运行（复用已有 GPU 环境，节省资源）**

```bash
docker exec -d edge_cloud_training bash -c "\
cd /app && \
export PYTHONPATH=/app/water_inspection:\$PYTHONPATH && \
export STREAM_URL=rtmp://192.168.0.103:1935/stream/safety_cam && \
export STREAM_INTERVAL=3 && \
export STREAM_DEVICE_ID=cloud_gpu_103 && \
export MQTT_BROKER_URL=tcp://emqx:1883 && \
export MQTT_USERNAME=admin && \
export MQTT_PASSWORD=admin123456 && \
export CONFIG_PATH=/app/models/construction_safety/configs/construction_safety.yaml && \
export BACKEND_API_URL=http://backend:8080 && \
export RADIO_CODE_DIR=/app/models/NVlabs_RADIO && \
export RADIO_CHECKPOINT_PATH=/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar && \
export SIGLIP2_DIR=/app/models/siglip2-giant-opt-patch16-384 && \
export DEVICE=cuda && \
python3 /app/models/cloud_inference/radio_infer_server.py > /tmp/cloud_infer.log 2>&1"

# 查看运行日志
docker exec edge_cloud_training tail -f /tmp/cloud_infer.log
```

> **注意**：`models/cloud_inference/` 已通过 volume 挂载到容器 `/app/models/cloud_inference/`，修改宿主机代码后容器内立即可用，无需手动同步。

### 9.5 边缘设备配置

在 Jetson 设备上配置 `config/cloud_config.json`：

```json
{
  "cloud": {
    "enabled": true,
    "api_base_url": "http://192.168.0.103:8081/api/v1",
    "device_id": "jetson_orin_001",
    "device_name": "Jetson Orin 边缘设备",
    "device_type": "JETSON_ORIN"
  },
  "mqtt": {
    "enabled": true,
    "broker_host": "192.168.0.103",
    "broker_port": 1883,
    "client_id": "jetson_orin_001",
    "username": "nvidia",
    "password": "nvidia",
    "keep_alive": 120,
    "qos": 1,
    "clean_session": false,
    "auto_reconnect": true
  }
}
```

---

## 10. 验证测试

### 10.1 数据库验证

```bash
docker exec -it edge_cloud_postgres psql -U edge_user -d edge_cloud

-- 确认表结构
\d inference_results

-- 查看最新云端结果
SELECT id, time, device_id, source, alert_level, detection_count, inference_time_ms
FROM inference_results
WHERE source = 'cloud'
ORDER BY time DESC LIMIT 5;

-- 查看告警统计
SELECT alert_level, COUNT(*) FROM inference_results
WHERE alert_level IS NOT NULL AND time > NOW() - INTERVAL '1 day'
GROUP BY alert_level;
```

### 10.2 API 验证

```bash
# 模拟云端结果上报
curl -X POST http://localhost:8081/api/v1/cloud/inference/result \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-001",
    "frame_id": 1,
    "inference_time_ms": 150.5,
    "segments": {
      "bare_soil_uncovered": {
        "area": 0.05, "score": 0.8,
        "bbox": [10, 20, 100, 200],
        "class_name_cn": "裸土未覆盖"
      }
    },
    "alerts": [{
      "class_name": "bare_soil_uncovered",
      "level": "warning",
      "message": "裸土未覆盖，面积占比 5.0%",
      "area": 0.05
    }]
  }'

# 查询结果
curl "http://localhost:8081/api/v1/inference/results?page=1&page_size=10"

# 查询告警
curl "http://localhost:8081/api/v1/inference/alerts?levels=critical,warning"

# 统计信息
curl http://localhost:8081/api/v1/inference/stats

# 趋势数据
curl http://localhost:8081/api/v1/inference/trend
```

### 10.3 前端验证

| 页面 | 地址 | 验证内容 |
|------|------|----------|
| 推理结果 | `http://localhost:3000/inference` | 列表展示、过滤、图片预览、详情弹窗 |
| 告警中心 | `http://localhost:3000/alerts` | 统计卡片、趋势图、告警列表 |
| 告警规则 | `http://localhost:3000/alert-rules` | 规则 CRUD |
| 首页仪表盘 | `http://localhost:3000/` | 告警统计卡片、趋势图、最近告警 |

---

## 11. 常见问题排查

### 问题一：云端推理显示「无检出」

**可能原因**：场景配置中的 `background` 类（`is_background: true`）信号过强，抢占所有目标类的检测概率。

**排查步骤**：

```bash
# 查看加载的分割类别是否包含 background
docker exec edge_cloud_training grep "分割类别" /tmp/cloud_infer.log
# 如果输出包含 "background"，说明过滤未生效
```

**解决方法**：确认 `radio_infer_server.py` 包含背景类过滤逻辑（约第 146-150 行）：

```python
self._classes_config = {
    k: v for k, v in self._classes_config.items()
    if not v.get("is_background", False)
}
```

代码已通过 volume 挂载，无需手动同步：

```bash
# models/ 目录已挂载到容器 /app/models/，修改宿主机代码后立即生效
# 只需重启容器内的推理进程即可
```

### 问题二：MQTT 连接失败 / 边缘结果未入库

**排查步骤**：

```bash
# 检查 EMQX 是否运行
docker ps | grep emqx

# 检查后端 MQTT 连接日志
docker logs edge_cloud_backend 2>&1 | grep -i mqtt | tail -20

# 查看 EMQX 管理面板（浏览器访问）
# http://localhost:18083 （账号：admin / admin123456）
# 检查 Connections 和 Subscriptions 页面
```

### 问题三：推理图片不显示

**排查步骤**：

1. 确认 SeaweedFS 运行正常：`curl http://localhost:8333/`
2. 确认图片 URL 可访问：
   ```bash
   curl -I "http://localhost:8081/api/v1/files/download?key=inference/xxx.jpg"
   ```
3. 检查响应头：
   - `Content-Type` 应为 `image/jpeg`（不是 `application/octet-stream`）
   - `Content-Disposition` 应为 `inline`（不是 `attachment`）

### 问题四：Spring Boot 启动报循环依赖错误

**错误信息**：`The dependencies of some of the beans in the application context form a cycle`

**解决方法**：

1. `application.yml` 添加配置：
   ```yaml
   spring:
     main:
       allow-circular-references: true
   ```
2. 在 `MqttService` 中使用 `@Autowired @Lazy` 注入 `InferenceResultService`
3. 不要使用构造器注入处理循环依赖的字段

### 问题五：training 容器内运行推理但代码未更新

**原因**：training 容器挂载的是 `training/` 目录，而 `cloud/` 目录位于项目根目录，两者是独立副本。

**解决方法**：

```bash
# 代码已通过 volume 挂载，无需同步
# 重启容器内的推理进程
docker exec edge_cloud_training pkill -f radio_infer_server
# 然后按 9.4 节的方式二重新启动
```

---

## 12. 文件索引

### 后端（Java）

| 文件路径 | 职责 |
|----------|------|
| `entity/InferenceResult.java` | JPA 实体，映射 inference_results 表 |
| `repository/InferenceResultRepository.java` | 数据访问层，自定义查询 |
| `dto/InferenceResultRequest.java` | 边缘端上报 DTO |
| `dto/CloudInferenceResultRequest.java` | 云端结果上报 DTO |
| `dto/InferenceResultDTO.java` | 返回前端 DTO |
| `dto/InferenceStatsDTO.java` | 统计信息 DTO |
| `dto/InferenceTrendDTO.java` | 趋势数据 DTO |
| `service/InferenceResultService.java` | 核心业务：存储、查询、告警、导出 |
| `service/MqttService.java` | MQTT 连接管理、消息收发 |
| `service/AlertRuleService.java` | 告警规则匹配 |
| `service/WebhookService.java` | Webhook 推送 |
| `service/WebSocketMessageService.java` | WebSocket 实时推送 |
| `service/StorageServiceFacade.java` | 文件存储门面（本地/S3 切换） |
| `controller/InferenceResultController.java` | REST API 端点 |
| `controller/AlertRuleController.java` | 告警规则 CRUD |
| `controller/WebhookController.java` | Webhook 配置 CRUD |
| `controller/FileController.java` | 文件上传下载 |

### 前端（Vue 3 + TypeScript）

| 文件路径 | 职责 |
|----------|------|
| `api/index.ts` | Axios 封装，inferenceResultApi / alertRuleApi |
| `router/index.ts` | 路由：/inference, /alerts, /alert-rules, /webhooks |
| `App.vue` | 侧边栏菜单 + 告警计数 |
| `views/Home.vue` | 首页仪表盘：告警统计 + 趋势图 |
| `views/inference/InferenceResultList.vue` | 推理结果列表页 |
| `views/inference/AlertCenter.vue` | 告警中心页 |
| `views/inference/AlertRuleManage.vue` | 告警规则管理页 |
| `views/inference/WebhookManage.vue` | Webhook 管理页 |
| `views/device/DeviceDetail.vue` | 设备详情页（含推理结果 Tab） |

### 云端推理（Python）

| 文件路径 | 职责 |
|----------|------|
| `models/cloud_inference/radio_infer_server.py` | 云端推理主服务（MQTT/流式双模式，插件化） |
| `models/cloud_inference/plugin_base.py` | 插件基类 — 从 YAML 动态读取告警规则 |
| `models/cloud_inference/engine.py` | 推理引擎 — 模型加载、推理、标注绘制 |
| `deployment/docker/docker-compose.dev.yml` | 容器编排配置（含 profiles 多模式部署） |
| `deployment/emqx/init_rules.sh` | EMQX 规则引擎初始化脚本 |
| `models/water_inspection/` | 水利巡检场景代码和配置 |
| `models/construction_safety/` | 施工安全场景代码和配置 |

### 边缘端（C++）

| 文件路径 | 职责 |
|----------|------|
| `src/framework.cpp` | 推理框架主循环 + ReportInferenceResult() |
| `include/framework.h` | 框架头文件 |
| `config/cloud_config.json` | 云端连接配置 |

---

## 13. 技术栈总结

| 层级 | 技术选型 |
|------|----------|
| 边缘端运行时 | C++17、OpenCV、Paho MQTT C++、TensorRT |
| 边缘→云端通信 | MQTT v3.1.1 + REST API（HTTP） |
| 云端后端 | Java 21、Spring Boot 3.x、PostgreSQL 16 + TimescaleDB |
| 云端推理 | Python 3.10、PyTorch 2.5.1、C-RADIOv4、CUDA 12.1 |
| 对象存储 | SeaweedFS（S3 兼容，Apache 2.0） |
| 消息队列 | EMQX 5.5.0（MQTT Broker） |
| 实时推送 | WebSocket（STOMP over SockJS） |
| 前端 | Vue 3、TypeScript、Element Plus、ECharts |
| 容器化 | Docker、Docker Compose、NVIDIA Runtime |
