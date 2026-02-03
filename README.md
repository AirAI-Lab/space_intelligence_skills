# edge_infer_cloud - 云边协同管理平台

> 独立部署模式 · 与 edge_infer 完全隔离 · Windows + Linux 跨平台支持

edge_infer 的云边协同管理平台，提供设备管理、数据管理、模型训练、模型部署、OTA升级等完整能力。

## 项目概述

在现有 edge_infer 边缘推理框架基础上，新建独立仓库实现云边协同管理能力。

**部署模式：独立部署**
- 与 edge_infer 生产环境完全隔离
- 独立数据卷：`D:/docker/volumes/edge_cloud`
- 独立网络：`edge-cloud-network`
- 独立端口：避免与 edge_infer 冲突

## 当前实现状态

### ✅ 已完成功能

| 模块 | 功能 | 状态 |
|------|------|------|
| **后端服务** | Spring Boot 3.2 + JPA + PostgreSQL | ✅ 完成 |
| **数据库** | 8 张核心表 + TimescaleDB 时序数据 | ✅ 完成 |
| **前端管理** | Vue 3 + TypeScript + Element Plus | ✅ 完成 |
| **设备管理** | 设备注册、状态监控、分组管理 | ✅ 完成 |
| **数据集管理** | 数据集上传、验证、版本管理 | ✅ 完成 |
| **模型管理** | 模型导入、版本控制、格式转换 | ✅ 完成 |
| **训练服务** | YOLOv8 训练 + 续训功能 + MLflow 集成 | ✅ 完成 |
| **模型转换** | .pt → .onnx → .engine (FP16/INT8) | ✅ 完成 |
| **OTA 升级** | MQTT 通信、任务管理、状态跟踪 | ✅ 完成 |
| **存储服务** | SeaweedFS S3 兼容存储 | ✅ 完成 |
| **消息队列** | EMQX MQTT Broker v5 | ✅ 完成 |

### 🔄 待完善功能

| 模块 | 功能 | 状态 |
|------|------|------|
| **训练服务** | 数据集自动下载/解压 | 🔄 框架完成 |
| **训练服务** | 模型自动上传到 S3 | 🔄 框架完成 |
| **MQTT 集成** | 边缘设备状态上报处理 | 🔄 回调集成完成 |
| **前端 UI** | 实时训练进度图表 | ⏳ 待实现 |
| **OTA 升级** | 边缘设备热更新验证 | ⏳ 待联调 |

## 核心功能

- **设备管理**：设备注册、状态监控、远程配置下发
- **数据管理**：数据上传、数据集管理、AI辅助标注
- **训练管理**：参考YOLOv8的训练流程，支持多种模型训练
  - **续训功能** ⭐：支持从中断处继续训练，保留优化器状态
- **模型管理**：模型版本管理、格式转换、一键部署
- **OTA升级**：差异化升级、灰度发布、自动回滚

## 技术栈

### 云端平台（商业化友好，全免费协议）
| 组件 | 技术 | 版本 | 开源协议 |
|------|------|------|----------|
| 前端 | Vue 3 + TypeScript + Element Plus | 3.4+ | MIT |
| 后端 | Spring Boot 3.x | 3.2+ | Apache 2.0 |
| 数据库 | PostgreSQL + TimescaleDB | PG16 | MIT |
| 缓存 | Redis | 7.x | BSD |
| 存储 | SeaweedFS (S3 API) | latest | Apache 2.0 |
| 消息 | EMQX MQTT Broker | 5.5.0 | Apache 2.0 |
| 模型管理 | MLflow | v2.9.0 | Apache 2.0 |
| 训练 | PyTorch + Ultralytics YOLOv8 | 2.x+ | BSD |

**已移除高风险组件**：
- ❌ MinIO (AGPLv3) → 替换为 SeaweedFS (Apache 2.0)
- ❌ InfluxDB (CLv2) → 替换为 TimescaleDB (MIT)
- ❌ Grafana (AGPLv3) → 使用自研监控面板

### 边缘端
- **推理引擎**：edge_infer (C++)
- **Edge Agent**：Go

## 快速开始

### 前置要求

| 资源 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 8核+ | 16核+ |
| 内存 | 32GB | 64GB |
| 存储 | 100GB 可用空间 | 200GB+ NVMe SSD |
| GPU | - | NVIDIA RTX 4060 Ti 16GB+ |

**软件要求：**
- Windows 10/11 或 Linux
- Docker Desktop 4.30+ (Windows) 或 Docker 24+ (Linux)
- NVIDIA GPU Driver 545+ (如需 GPU 训练)
- Git

### 一键启动（推荐）

```powershell
# Windows PowerShell
cd deployment/docker
.\init.ps1
```

### 手动启动

```powershell
# 1. 创建数据卷目录
New-Item -ItemType Directory -Path "D:\docker\volumes\edge_cloud" -Force

# 2. 配置环境变量
cd deployment/docker
Copy-Item .env.example .env
# 编辑 .env 文件

# 3. 启动服务（管理平台模式）
docker-compose up -d

# 或启动完整平台（含 GPU 训练）
docker-compose --profile gpu up -d
```

### 访问服务

| 服务 | 地址 | 用户名 | 密码 | 说明 |
|------|------|--------|------|------|
| 中文导航门户 ⭐ | http://localhost:8889 | - | - | 统一服务入口 |
| 前端管理平台 | http://localhost:3000 | - | - | Vue3 管理平台 |
| 后端 API | http://localhost:8081 | - | - | Spring Boot API |
| API 文档 | http://localhost:8081/swagger-ui.html | - | - | Swagger UI |
| 训练服务 | http://localhost:5002 | - | - | MLflow 训练管理 |
| SeaweedFS | http://localhost:8888 | - | - | 文件存储管理 |
| EMQX Dashboard | http://localhost:18083 | admin | admin123456 | MQTT 消息队列 |
| MLflow | http://localhost:5001 | - | - | 模型生命周期管理 |

### 端口规划

| 端口 | 服务 | 协议 | 说明 |
|------|------|------|------|
| 8889 | 中文导航门户 | HTTP | 统一服务入口 |
| 3000 | 前端 | HTTP | Vue3 管理平台 |
| 8081 | 后端 API | HTTP | Spring Boot |
| 5001 | MLflow | HTTP | 模型管理 |
| 5432 | PostgreSQL | TCP | 业务数据库 |
| 6379 | Redis | TCP | 缓存 |
| 8333 | SeaweedFS S3 API | HTTP | 对象存储 API |
| 8888 | SeaweedFS UI | HTTP | 存储管理界面 |
| 1883 | EMQX | MQTT | MQTT Broker |
| 18083 | EMQX Dashboard | HTTP | EMQX 管理界面 |

## 项目结构

```
edge_infer_cloud/
├── frontend/              # Vue3前端
│   └── src/
│       ├── views/
│       │   ├── device/   # 设备管理
│       │   ├── dataset/  # 数据集管理
│       │   ├── training/ # 训练任务
│       │   ├── model/    # 模型管理
│       │   └── ota/      # OTA升级
├── backend/               # Spring Boot后端
│   └── src/main/java/com/edge/cloud/
│       ├── entity/       # JPA实体类
│       ├── repository/   # 数据访问层
│       ├── service/      # 业务逻辑层
│       ├── controller/   # REST API
│       └── dto/          # 数据传输对象
├── training/              # Python训练服务
│   └── edge_train/
│       ├── trainer.py    # YOLOv8训练器
│       ├── converter.py  # 模型转换器
│       └── config.py     # 配置管理
├── deployment/           # 部署配置
│   └── docker/
│       ├── docker-compose.yml
│       ├── backend.Dockerfile
│       ├── frontend.Dockerfile
│       └── training.Dockerfile
└── docs/                 # 文档
    ├── 04_training.md   # 训练服务文档
    └── EDGE_REST_API.md  # REST API 文档
```

## 模型导出和存储

### 模型文件结构

训练完成后，模型文件会自动上传到 S3 存储服务，包含完整的网络结构和配置信息：

```
S3: models/{model_id}/
├── best.pt                  # PyTorch 完整模型（网络结构+权重）
├── model_config.json       # 训练配置（训练参数、指标、使用说明）
├── classes.txt             # 类别名称列表
├── data.yaml               # 数据集配置（YOLO格式）
├── best.onnx               # ONNX 模型（计算图+权重+元数据）
└── onnx_config.json        # ONNX 配置（导出参数、格式信息）
```

### 配置文件说明

| 文件 | 保存时机 | 内容 | 用途 |
|------|---------|------|------|
| `model_config.json` | 训练完成 | 训练参数、评估指标、类别信息、使用说明 | PyTorch 推理、模型管理 |
| `onnx_config.json` | ONNX 转换 | ONNX 导出参数、格式兼容信息 | ONNX Runtime、部署参考 |

### model_config.json 示例

```json
{
  "model_id": "M_JOBxxx",
  "model_type": "YOLOv8",
  "base_model": "yolov8n.pt",
  "architecture": {
    "type": "YOLOv8 Detection",
    "input_size": [640, 640],
    "num_classes": 3,
    "classes": {
      "0": "Drowning",
      "1": "Person out of water",
      "2": "Swimming"
    }
  },
  "training": {
    "epochs": 5,
    "batch_size": 16,
    "optimizer": "SGD"
  },
  "metrics": {
    "map50_95": 0.317,
    "map50": 0.633,
    "precision": 0.645,
    "recall": 0.576
  },
  "usage": {
    "inference": "from ultralytics import YOLO; model = YOLO('best.pt'); results = model('image.jpg')",
    "export": "model.export(format='onnx')",
    "requirements": "ultralytics>=8.0.0"
  }
}
```

### ONNX 模型特性

- **完整计算图**：包含完整的网络结构，无需原始代码
- **动态输入**：支持不同输入尺寸（dynamic=True）
- **简化图**：移除冗余节点，优化推理性能
- **元数据嵌入**：模型ID、类别信息直接保存在 ONNX 文件中
- **跨框架兼容**：可在 ONNX Runtime、OpenCV、TensorRT 等框架中使用

### 模型使用示例

```python
# 方式1: PyTorch 推理（使用 best.pt）
from ultralytics import YOLO
model = YOLO('best.pt')
results = model('image.jpg')

# 方式2: ONNX Runtime 推理（使用 best.onnx）
import onnxruntime as ort
session = ort.InferenceSession('best.onnx')
# 读取 onnx_config.json 获取类别信息
```

### 模型转换

平台支持将 PyTorch 模型转换为其他格式：

1. **.pt → .onnx**：标准 ONNX 格式，跨平台兼容
2. **.onnx → .engine**：TensorRT 引擎，GPU 加速推理

转换会自动：
- 保存完整的配置文件
- 添加模型元数据
- 上传到 S3 存储

## API 端点

### 设备管理
- `GET /api/v1/devices` - 获取设备列表
- `GET /api/v1/devices/{id}` - 获取设备详情
- `POST /api/v1/devices` - 注册设备

### 数据集管理
- `GET /api/v1/datasets` - 获取数据集列表
- `POST /api/v1/datasets/upload` - 上传数据集

### 训练任务
- `GET /api/v1/training` - 获取训练任务列表
- `POST /api/v1/training` - 创建训练任务
- `POST /api/v1/training/{id}/start` - 启动训练

### 模型管理
- `GET /api/v1/models` - 获取模型列表
- `POST /api/v1/models/import` - 导入模型
- `POST /api/v1/models/{id}/convert` - 转换模型格式

### OTA 升级
- `GET /api/v1/ota/tasks` - 获取升级任务列表
- `POST /api/v1/ota/tasks` - 创建升级任务
- `POST /api/v1/ota/tasks/{id}/start` - 开始升级

## 数据库表结构

```sql
-- 核心业务表
datasets                -- 数据集表
models                  -- 模型表
training_jobs           -- 训练任务表
conversion_tasks        -- 转换任务表
ota_tasks              -- OTA升级任务表
device_upgrade_status  -- 设备升级状态表
devices                -- 设备表
training_metrics       -- 训练指标时序表(TimescaleDB)
```

## 开发说明

### 开发模式热挂载配置

本项目已配置**源码热挂载**，开发过程中修改代码无需重新构建镜像：

| 服务 | 源码挂载 | 热重载方式 | 说明 |
|------|----------|------------|------|
| **前端** | `../../frontend:/app` | Vite HMR | 修改 Vue/TS 文件自动刷新 |
| **后端** | `../../backend:/app` | Spring DevTools | 修改 Java 文件自动重启 |
| **训练** | `../../training:/app` | 直接生效 | 修改 Python 文件重启服务生效 |

#### 开发模式配置详情

**前端 (Vue3 + Vite)**
```yaml
frontend:
  image: node:21-alpine
  environment:
    - DOCKER_ENV=true          # Docker 环境标识
    - VITE_API_BASE_URL=/api/v1
  volumes:
    - ../../frontend:/app      # 源码热挂载
    - /app/node_modules         # 保护 node_modules
  command: sh -c "npm install && npm run dev -- --host 0.0.0.0 --port 3000"
```

**后端 (Spring Boot)**
```yaml
backend:
  image: maven:3.9-eclipse-temurin-21
  environment:
    # 数据库配置
    - SPRING_DATASOURCE_URL=jdbc:postgresql://postgres:5432/edge_cloud
    - SPRING_REDIS_HOST=redis
    # 服务间通信
    - TRAINING_SERVICE_URL=http://training:5002
    # 存储服务
    - S3_ENDPOINT=http://seaweedfs:8333
    - S3_BUCKET=edge-cloud-files
    # 开发模式配置（JDWP 调试已禁用以加快启动）
    - SPRING_DEVTOOLS_RESTART_ENABLED=true
    - SPRING_LIVE_RELOAD_ENABLED=true
  volumes:
    - ../../backend:/app       # 源码热挂载
    - ~/.m2:/root/.m2          # Maven 仓库缓存
  command: mvn spring-boot:run
```

**训练服务 (Python + Flask)**
```yaml
training:
  environment:
    # 后端通信
    - BACKEND_API_URL=http://backend:8080
    # MLflow 配置
    - MLFLOW_TRACKING_URI=http://mlflow:5000
    # S3 存储
    - S3_ENDPOINT=http://seaweedfs:8333
    - S3_BUCKET=edge-cloud
    # GPU 配置
    - USE_GPU=true
  volumes:
    - ../../training:/app      # 源码热挂载
    - ../../data/runs:/app/runs
    - ../../data/models:/app/models
```

#### 开发流程

1. **修改代码**：直接在 IDE 中编辑源文件
2. **前端变更**：Vite 自动热更新，无需手动刷新
3. **后端变更**：Spring DevTools 自动重启，无需手动操作
4. **训练服务**：修改 Python 文件后需重启容器生效

#### 服务间通信配置

| 连接 | 配置 | 说明 |
|------|------|------|
| 前端 → 后端 | `http://backend:8080` | 通过 Vite 代理 |
| 后端 → 训练 | `http://training:5002` | RestTemplate 调用 |
| 训练 → 后端 | `http://backend:8080` | 状态回调 |
| 后端 → PostgreSQL | `postgres:5432` | JPA 数据访问 |
| 后端 → Redis | `redis:6379` | 缓存 |
| 后端 → EMQX | `tcp://emqx:1883` | MQTT 消息 |
| 训练 → S3 | `http://seaweedfs:8333` | 模型存储 |

#### 调试端口

| 服务 | 调试端口 | 说明 |
|------|----------|------|
| 前端 | 3000 | Vite Dev Server |
| 后端 | 8081 | Spring Boot API |
| 训练 | 5002 | Flask API |
| PostgreSQL | 5432 | 数据库 |
| EMQX Dashboard | 18083 | MQTT 管理界面 |

### CUDA 版本兼容性

本项目采用混合 CUDA 版本策略：

| 环境 | CUDA | PyTorch | TensorRT | 说明 |
|------|------|---------|----------|------|
| 训练服务 | 12.5 | 2.5.0 (cu125) | 10.3 | 与 Jetson 兼容 |
| Jetson 生产 | 12.5 | - | 10.3 | JetPack 6.x |

**注意**：训练服务生成的 .engine 文件可直接部署到 Jetson 设备。

### MQTT 主题设计

```
# 设备订阅
device/{device_id}/ota/update        -- OTA升级指令

# 设备发布
device/{device_id}/ota/status        -- 升级状态上报
device/{device_id}/heartbeat         -- 心跳上报
```

## 参考文档

### 平台文档
- [训练服务详解](docs/04_training.md) - 数据集上传、训练流程、续训功能
- [REST API 文档](docs/EDGE_REST_API.md) - 完整的 API 接口说明

### 外部参考
- [Ultralytics YOLOv8官方文档](https://docs.ultralytics.com/zh/modes/)
- [SeaweedFS S3 API](https://github.com/seaweedfs/seaweedfs)
- [EMQX MQTT v5 规范](https://docs.emqx.com/en/latest/mqtt/mqtt5.html)

### 续训功能说明

本平台实现了改进的 YOLOv8 续训功能，解决了原生 YOLOv8 续训时的参数替换问题。详细说明请参考 [训练服务文档 - 续训功能章节](docs/04_training.md#6-续训功能详解)。

**主要特性**：
- ✅ 直接用检查点初始化模型，避免路径被替换
- ✅ 支持在续训时调整训练参数（轮次、优化器、patience 等）
- ✅ 完备的权重文件验证（last.pt → best.pt → 基础模型）
- ✅ 保留优化器状态，results.csv 自然追加
- ✅ 统一输出目录（`/app/work/outputs/{job_id}/train/`）
- ✅ 修复 save_dir 字段覆盖问题，确保输出到正确目录
- ✅ **可选择的参数策略** ⭐：用户可选择"使用指定参数"或"智能优化"
- ✅ **智能优化时参数自动禁用**：选择智能优化时，学习率等参数输入框自动变灰不可用
- ✅ **GPU 选项始终可用**：无论选择哪种策略，GPU 开关都可以使用

**参数策略对比**：

| 策略 | 说明 | 参数来源 | 界面状态 |
|------|------|----------|----------|
| **使用指定参数** | 完全由用户控制训练参数 | 用户在续训表单中指定的值 | 参数可编辑 |
| **智能优化** | 根据训练状态自动优化参数 | 基于 results.csv 分析和检查点原始参数 | 参数灰色不可用 |

**智能优化策略**（当启用时）：
- 初期 (epoch ≤ 30)：保持正常学习率，patience=30
- 中期 (30-100)：根据 mAP 趋势调整学习率 (0.2x-1.0x)，patience=30-50
- 后期 (epoch > 100)：降低学习率微调 (0.1x-0.3x)，patience=50-100
- 已收敛 (mAP > 0.7)：建议停止训练

**前端交互**：
- 续训按钮对 RUNNING、CANCELLED、FAILED 状态的任务可见
- 续训对话框提供参数策略单选框（智能优化/使用指定参数）
- 选择智能优化时，批次大小、图像尺寸、优化器、学习率、权重衰减等参数自动禁用（灰色）
- GPU 开关始终可用，不受策略选择影响

**验证状态**：
- ✅ 从 epoch 32 续训验证成功
- ✅ results.csv 正确追加新 epoch 数据
- ✅ 模型权重正确保存到统一目录
- ✅ patience 参数自动更新修复早停问题
- ✅ 智能优化功能正常工作，参数自动调整生效

## 许可证

MIT License
