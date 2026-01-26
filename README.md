# edge_infer_cloud - 云边协同管理平台

edge_infer 的云边协同管理平台，提供设备管理、数据管理、模型训练、模型部署、OTA升级等完整能力。

## 项目概述

在现有 edge_infer 边缘推理框架基础上，新建独立仓库实现云边协同管理能力。

## 核心功能

- **设备管理**：设备注册、状态监控、远程配置下发
- **数据管理**：数据上传、数据集管理、AI辅助标注
- **训练管理**：参考YOLOv8的训练流程，支持多种模型训练
- **模型管理**：模型版本管理、格式转换、一键部署
- **OTA升级**：差异化升级、灰度发布、自动回滚

## 技术栈

### 云端平台
- **前端**：Vue 3 + TypeScript + Element Plus
- **后端**：Spring Boot 3.x
- **数据库**：PostgreSQL + Redis + InfluxDB
- **存储**：MinIO + MLflow
- **消息**：EMQX MQTT Broker

### 边缘端
- **推理引擎**：edge_infer (C++)
- **Edge Agent**：Go

## 参考文档

- [Ultralytics YOLOv8官方文档](https://docs.ultralytics.com/zh/modes/)

## 快速开始

### 前置要求

- Docker & Docker Compose
- Node.js 18+
- Java 17+
- Python 3.10+
- Go 1.21+

### 启动云端平台

```bash
cd deployment/docker
docker-compose up -d
```

### 访问服务

- 前端: http://localhost:3000
- 后端API: http://localhost:8080
- MinIO控制台: http://localhost:9001
- EMQX控制台: http://localhost:18083
- MLflow: http://localhost:5000

## 项目结构

```
edge_infer_cloud/
├── frontend/         # Vue3前端
├── backend/          # Spring Boot后端
├── training/         # Python训练框架
├── edge-agent/       # Go边缘Agent
├── deployment/       # 部署配置
└── docs/            # 文档
```

## 许可证

MIT License
