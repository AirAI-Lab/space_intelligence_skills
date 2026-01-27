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
| **训练服务** | YOLOv8 训练框架 + MLflow 集成 | ✅ 完成 |
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
```

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

- [Ultralytics YOLOv8官方文档](https://docs.ultralytics.com/zh/modes/)
- [SeaweedFS S3 API](https://github.com/seaweedfs/seaweedfs)
- [EMQX MQTT v5 规范](https://docs.emqx.com/en/latest/mqtt/mqtt5.html)

## 许可证

MIT License
