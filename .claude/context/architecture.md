# edge_infer_cloud 项目架构

## 项目概述

**定位**：云边协同管理平台，为 edge_infer 边缘推理框架提供云端管理能力。

**与 edge_infer 的关系**：
- edge_infer_cloud（云端）：管理平台，负责设备管理、数据管理、模型训练、OTA 升级
- edge_infer（边缘端）：推理框架，负责模型加载、推理执行、状态上报

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      edge_infer_cloud (云端)                     │
├─────────────────────────────────────────────────────────────────┤
│  前端层 (Vue 3)                                                  │
│  ├─ 设备管理页面    ─────────────────────────────────────────┐   │
│  ├─ 数据集管理页面  ─────────────────────────────────────────┤   │
│  ├─ 训练任务页面    ────────────┐                            │   │
│  ├─ 模型管理页面    ───────────┐  │                            │   │
│  └─ OTA 升级页面     ────────┐  │  │                            │   │
│                            │  │  │                            │
│  后端层 (Spring Boot)        │  │  │                            │
│  ├─ DeviceController       │  │  │                            │
│  ├─ DatasetController ──────┘  │                            │
│  ├─ TrainingController ───────┘  │                            │
│  ├─ ModelController ───────────┘                            │
│  ├─ OtaController ──────────────────────┐                   │
│  └─ MqttService ─────────────────────────┘                   │
│                                                      │           │
│  数据层                             │           │               │
│  ├─ PostgreSQL (业务数据)             │           │               │
│  ├─ TimescaleDB (时序数据)            │           │               │
│  ├─ Redis (缓存)                     │           │               │
│  ├─ SeaweedFS (文件存储)              │           │               │
│  └─ EMQX (MQTT Broker)                │           │               │
│                                         │           │               │
│  训练服务 (Python)                      │           │               │
│  ├─ trainer.py (YOLOv8 训练)           │           │               │
│  ├─ converter.py (模型转换)            │           │               │
│  └─ MLflow (实验跟踪)                  │           │               │
│                                         │           │               │
│  云端推理服务 (C-RADIOv4)               │           │               │
│  ├─ radio_infer_server.py              │           │               │
│  ├─ SigLIP2-g 特征提取器              │           │               │
│  └─ 零样本语义分割 (裸土/扬尘等)       │           │               │
└─────────────────────────────────────────┼───────────┴───────────────┘
                                           │
                            ┌──────────────▼────────────────┐
                            │   MQTT Broker (EMQX)          │
                            └──────────────┬────────────────┘
                                           │ MQTT
┌──────────────────────────────────────────▼─────────────────────────┐
│                    edge_infer (边缘端)                           │
├─────────────────────────────────────────────────────────────────┤
│  C++ 推理引擎                                                       │
│  ├─ MQTT Client (订阅 OTA 更新)                                 │
│  ├─ Model Manager (热更新 .engine 文件)                          │
│  ├─ Plugin Engine (TensorRT 推理)                                │
│  ├─ CUDA Preprocessor (GPU 融合预处理)                          │
│  ├─ Async Output Thread (异步推流/上报/转发)                    │
│  └─ Cloud Forward (原始帧转发云端推理)                           │
└─────────────────────────────────────────────────────────────────┘
```

## 微服务职责

### 后端服务 (backend:8081)
| 包 | 职责 |
|-----|------|
| `controller/` | REST API 入口 |
| `service/` | 业务逻辑处理 |
| `repository/` | 数据访问层 |
| `entity/` | JPA 实体类 |
| `dto/` | 数据传输对象 |

### 前端服务 (frontend:3000)
| 目录 | 职责 |
|------|------|
| `views/device/` | 设备管理界面 |
| `views/dataset/` | 数据集管理界面 |
| `views/training/` | 训练任务界面 |
| `views/model/` | 模型管理界面 |
| `views/ota/` | OTA 升级界面 |

### 训练服务 (training:5002)
| 文件 | 职责 |
|------|------|
| `trainer.py` | YOLOv8 训练逻辑 |
| `converter.py` | 模型格式转换 |
| `config.py` | 配置和 S3 客户端 |

### 云端推理服务 (插件化架构)
| 文件 | 职责 |
|------|------|
| `models/cloud_inference/radio_infer_server.py` | 推理主服务（MQTT/RTMP 模式管理） |
| `models/cloud_inference/plugin_base.py` | 插件基类 — YAML 驱动告警规则 |
| `models/cloud_inference/engine.py` | 推理引擎 — 模型加载、分割、标注 |
| 模型 | C-RADIOv4-H (1412.4M 参数) + SigLIP2-g 特征提取器 |
| 输入 | MQTT 订阅边缘设备转发的原始帧 |
| 输出 | 分割结果 + YAML 驱动告警 → HTTP POST 后端 + EMQX 统一 topic |

## 核心数据流

### 1. 模型训练和部署流程
```
用户上传数据集 → SeaweedFS 存储
        ↓
创建训练任务 → backend:8081/training
        ↓
调用训练服务 → training:5002/train
        ↓
下载 S3 数据集 → YOLOv8 训练
        ↓
上传模型 → S3 存储
        ↓
模型转换 → .pt → .onnx → .engine
        ↓
创建 OTA 任务 → backend:8081/ota/tasks
        ↓
MQTT 推送 → EMQX:1883
        ↓
边缘设备接收 → edge_infer MQTT Client
        ↓
下载模型 → S3 下载
        ↓
热更新 → edge_infer 重载插件
        ↓
状态上报 → MQTT 上报进度
```

### 2. 云端推理流程
```
边缘设备采集帧 → CUDA 预处理 → TensorRT 推理
        ↓
异步输出管道: 推流 + MQTT 上报 + 原始帧转发
        ↓
MQTT publish → device/{id}/cloud/frame (JPEG Base64)
        ↓
radio_infer_server.py 订阅 → InferenceEngine → C-RADIOv4 零样本分割
        ↓
ScenarioPlugin.generate_alerts() (YAML 驱动) → EMQX 规则引擎 → results/# + alerts/#
        ↓
分割结果 + 可视化图像 → HTTP POST backend:8080
        ↓
后端存储 → 前端展示
```

### 2. API 调用关系
```
前端 → 后端 API (8081)
     → 训练服务 (5002)
     → SeaweedFS (8333)
     → EMQX (1883/18083)
     → MLflow (5001)
```

## 关键依赖关系

### Spring Bean 依赖
```
MqttService ────@RequiredArgsConstructor───→ OtaService
   │                                              │
   └────────────── setter 注入 ──────────────────┘
```

**注意**：存在循环依赖，通过 setter 注入解决。

### JPA 实体关系
```
OtaTask (1) ←─── (N) DeviceUpgradeStatus
  │
  └──→ 关联查询时使用 @ManyToOne(fetch = FetchType.LAZY)
```

## 编译和构建

### 后端编译
```bash
cd deployment/docker
docker-compose build backend
```

### 前端构建
```bash
cd deployment/docker
docker-compose build frontend
```

### 训练服务构建
```bash
cd deployment/docker
docker-compose build training
```

## 常见问题排查

### 后端启动失败
1. 检查数据库连接：`docker logs edge_cloud_postgres`
2. 检查环境变量：`docker-compose config`
3. 检查编译错误：`docker logs edge_cloud_backend`

### MQTT 连接失败
1. 检查 EMQX 状态：`curl http://localhost:18083`
2. 检查网络：`docker network inspect edge-cloud-network`
3. 检查订阅主题：`mosquitto_sub -h localhost -t "device/#" -v`

### 训练服务无响应
1. 检查健康状态：`curl http://localhost:5002/health`
2. 检查 GPU：`docker exec edge_cloud_training nvidia-smi`
3. 查看日志：`docker logs edge_cloud_training`
