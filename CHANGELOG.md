# Edge Infer Cloud 变更日志

本文档记录 edge_infer_cloud 云边协同平台的版本变更历史。

---

## v2026.05.08 — 多通道推理 + 第三方对接 + 生产部署

### 新增
- **多通道视频推理**：支持 cam1/cam2/cam3 三路视频并行推理，共享 TensorRT Engine（只加载一次权重），各通道独立 CUDA Context
- **channel_id 全链路支持**：边缘上报 → MQTT → 后端存储 → DTO/API 全链路携带 channel_id 字段
- **第三方平台对接指南** (`docs/THIRD_PARTY_INTEGRATION.md`)：Webhook 推送、REST API 查询、MQTT 实时订阅、RTMP 视频流接入的完整对接说明和 Python 示例
- **生产部署配置** (`docker-compose.prod.yml`)：多阶段构建预编译镜像 + Nginx 统一反向代理（80 端口统一入口）
- **一键部署脚本** (`deploy.sh`)：支持 `--dev/--gpu/--stop/--status/--logs/--rebuild` 命令
- **systemd 服务** (`edge-cloud.service`)：Linux 服务器开机自启
- **部署文档** (`docs/DEPLOYMENT.md`)：Windows Docker Desktop / Linux 服务器分场景部署指南

### 修复
- `InferenceResultService.exportResults()` 缺少 `hasAlert` 参数导致编译失败
- `InferenceResultDTO` 缺少 `channelId` 字段，API 响应不返回 channel_id
- `InferenceResultRequest` 缺少 `@JsonIgnoreProperties(ignoreUnknown = true)`，边缘端新增字段导致 Jackson 反序列化失败
- 后端 `mvn clean compile` 后类文件不完整（0 JPA repositories），通过清理 `target/classes` 后重启解决

### 文档
- 更新 `docs/api/README.md`：补充推理结果查询、告警、统计、导出、Webhook 管理、文件存储等完整 API 文档

---

## snapshot-2026-04-29 — C-RADIOv4 云端推理 + 文档整理

### 新增
- **C-RADIOv4 云端推理**：云端 RADIO 模型分割推理，结果入库和前端展示
- **推理结果持久化**：边缘检测结果和云端分割结果统一存储到 TimescaleDB
- **告警系统**：告警级别（warning/critical/info）、告警消息、WebSocket 实时推送
- **MQTT 自动回退 RTMP**：MQTT 不可用时自动切换到 REST API 上报

### 改进
- README 启动命令和流程步骤精简
- Docker Ctrl+C 优雅退出修复

---

## v2026.04.28 — 变化检测 + 部署手册

### 新增
- **变化检测模块** (`change_detection`)：多类别模式、层次化检测
- **Docker 部署手册**：统一依赖、安装脚本
- **推理结果可视化**：前端推理结果列表、告警中心、统计趋势图

### 改进
- 文档重组：技术文档、业务文档、API 文档分类整理

---

## v20260424 — Docker 部署 + 统一需求

### 新增
- Docker Compose 完整部署配置（postgres/redis/emqx/seaweedfs/backend/frontend/training）
- 统一 Python 依赖文件 (`cloud_requirements.txt`)
- 训练服务 Dockerfile（GPU 支持）

---

## v2026.04.23 — RADIO 零样本检测

### 新增
- **RADIO 零样本检测**：construction_safety 和 park_monitoring 场景的零样本目标检测
- NVlabs RADIO 模型集成

---

## 2026-04-07-v1.2 — 变化检测初始化

### 新增
- 变化检测模块初始版本

---

## 2026-04-07-v3.4.1 — 项目结构清理

### 改进
- 移除 `writing/` 目录的 git 跟踪
- 项目结构精简

---

## release-2026-03-23 — 坝体渗水检测优化

### 改进
- 坝体渗水 v8 管线优化：dam>water 约束，F1=84%
- 数据集配置修复：标准 7:1:2 划分

---

## v1.0.0 — 2026-02-05 云边协同平台初始版本

### 核心功能
- **Spring Boot 3.x 后端**：REST API + WebSocket + MQTT 三协议支持
- **Vue 3 + TypeScript 前端**：设备管理、模型管理、训练管理、推理监控
- **设备管理**：边缘设备注册、心跳上报、状态监控（CPU/GPU/内存/温度）
- **训练管理**：YOLO 训练任务创建、进度监控、MLflow 集成
- **模型管理**：模型版本管理、ONNX → TensorRT 转换、部署
- **OTA 升级**：云端推送模型升级命令，边缘自动下载、校验、热加载
- **Webhook 系统**：告警/结果事件主动推送到第三方 URL
- **文件存储**：SeaweedFS (S3 兼容) 对象存储

### 基础设施
- PostgreSQL 16 + TimescaleDB 时序存储
- Redis 缓存
- EMQX 5.5 MQTT Broker
- MLflow 模型管理
- Docker Compose 容器化部署

---

## 变更记录格式

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 格式，每个版本包含以下分类：

- **新增**：新功能
- **改进**：已有功能的优化
- **修复**：Bug 修复
- **文档**：文档更新
- **移除**：已删除的功能
