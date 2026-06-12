# Edge Infer Cloud 变更日志

本文档记录 edge_infer_cloud 云边协同平台的版本变更历史。

---

## v2026.06.12 — 文档体系收敛 + 开发计划

### 新增

**对外交付文档入口**
- 新增根目录 `QUICKSTART.md`，作为客户、产品、开发、运维的统一文档入口。
- 新增 `docs/README.md` 正式文档目录，按角色指向市场、产品、技术文档。

**市场/运营文档**
- 新增 `docs/business/MARKET_OVERVIEW.md`。
- 新增 `docs/business/SCENARIO_SOLUTIONS.md`。
- 新增 `docs/business/COMPETITIVE_ADVANTAGES.md`。

**产品/UI 文档**
- 新增 `docs/product/PRODUCT_REQUIREMENTS.md`。
- 新增 `docs/product/USER_MANUAL.md`。
- 新增 `docs/product/UI_UX_DESIGN_GUIDE.md`。

**技术/开发/运维文档**
- 新增 `docs/technical/ARCHITECTURE.md`。
- 新增 `docs/technical/API_AND_INTEGRATION.md`。
- 新增 `docs/technical/TRAINING_AND_MODEL_GUIDE.md`。
- 新增 `docs/technical/DEVELOPMENT_PLAN.md`。
- 新增 `docs/technical/OPERATIONS_AND_TROUBLESHOOTING.md`。

### 变更

**文档结构收敛**
- 根目录 Markdown 按对外客户/交付版标准收敛，仅保留 `CHANGELOG.md`、`QUICKSTART.md`、`README_DOCKER.md`。
- `docs/` 正式文档收敛为 `business`、`product`、`technical` 三类。
- 旧文档迁移到本机归档目录 `docs/archive/2026-06-doc-cleanup/`，并通过 `.gitignore` 排除，不上传远端仓库。

**平台规划同步**
- 正式文档统一平台定位为“云边协同空间智能平台”。
- 明确技术边界：ZLMediaKit 负责流媒体核心，`edge_infer` 负责 C++ 边缘推理，Spring Boot 负责平台业务，Python 负责云端训练/推理/大模型能力。
- 补充空间态势、二维地图、未来三维地图和数字孪生大屏规划。
- 补充模型工厂开发方向：数据飞轮、辅助标注、零代码训练、一键导出、行业预设。

**Docker 部署手册**
- `README_DOCKER.md` 明确当前 Docker Compose 仍使用 `nginx-rtmp` 和 `mlflow`，后续规划接入 ZLMediaKit，并将 MLflow 调整为可选实验追踪组件。
- 明确 `edge_infer` 是独立 C++ 边缘推理框架，不在本仓库 Docker Compose 中启动。

### 说明

- 本次不提交本机归档目录内容。
- 本次不提交 `.tools/`、`output/`、`training/change_detection/`、`training/data/`、`training/yolov8n.onnx` 等本地生成或实验文件。

---

## v2026.06.10 — GPU 多卡放开 + MLflow 禁用

### 变更

**GPU 多卡支持**
- 移除所有 `CUDA_VISIBLE_DEVICES=0` 硬编码（docker-compose.yml/dev/prod、Dockerfile、.env.example）
- 默认自动使用宿主机全部 GPU，训练脚本通过 `--device` 参数选择具体卡
- 移除 training 容器 CPU/内存 limits，让容器自动使用宿主机全部资源

**MLflow 禁用**
- `models/requirements.txt` 和 `training/requirements.txt` 注释掉 mlflow 依赖
- 原因：ultralytics 自动注册 mlflow callback，无 MLflow server 时导致训练崩溃（NameResolutionError）

**docker-compose.yml 清理**
- 注释掉 edge_infer/external_data Windows 开发机路径挂载

---

## v2026.06.09 — IP 统一配置 + Schema 补全 + 端口修正

### 新增

**IP 统一配置体系**
- `.env.ip`：云端→192.168.1.123，边缘→192.168.0.1，字段名统一 EDGE_IP
- `scripts/configure_ip.sh`：一键同步 IP 到所有配置文件（独立于 deploy.sh）
- `README_DOCKER.md` §5.5：IP 配置章节，端口架构说明

**QA 文档**
- `QA.md`：部署经验 & 常见问题总结

### 变更

**数据库 Schema 补全**
- `schema.sql`：devices 建表补全 device_category/capabilities/protocol/labels + 硬件信息列
- `deploy.sh`：init_db 补全 devices 表 4 列 ALTER 语句

**端口与网络修正**
- `docker-compose.prod.yml`：EMQX 加 ports: 1883（边缘设备 MQTT 直连），Backend 加 ports: 8081
- `docker-compose.yml`：S3_EXTERNAL_ENDPOINT 改为环境变量引用

**配置更新**
- `OtaService.java`：默认 IP→192.168.1.123
- `construction_safety.yaml`：fallback_stream IP→192.168.1.123

---

## v2026.06.07 — SeaweedFS 修复 + 部署统一 + 移除 edge_infer 挂载

### 修复

**SeaweedFS S3 写入 500 错误**
- 根因：`volume.max=7` 导致 volume 槽位耗尽（Free:0），master 无法分配新 volume
- 修复：`volume.max` 恢复为 100，Free:93，S3 上传正常
- `FILE_STORAGE_TYPE` 默认值恢复为 `s3`

**start.ps1 WSL2 路径错误**
- 根因：未加载 `.env.wsl2`，Windows 路径 `D:/...` 传入 WSL2 docker-ce 导致 `invalid volume specification`
- 修复：自动检测 `.env.wsl2` 并传 `--env-file` 给 docker compose
- 修复 portproxy IP 解析被 WSL 代理警告干扰的问题

### 变更

**部署脚本统一**
- `deploy.sh` 重写：自动检测 IP/GPU、一次性全量部署、`init_db()` 自动建表（14 张实体表补丁）
- `start.ps1` 替代 `start-wsl2.ps1` + `init.ps1` + `dev-restart.bat/sh`
- 删除旧脚本：`build-push.sh`、`dev-restart.bat/sh`、`docker-compose.lite.yml`、`init.ps1`、`start-wsl2.ps1`、`BOOTSTRAP.md`

**配置统一**
- `PG_PASSWORD` 全部统一为 `admin123456`（`.env.example`、`docker-compose.yml`、`docker-compose.dev.yml`、`docker-compose.prod.yml`、`application.yml`）
- `docker-compose.prod.yml`：RTMP 镜像替换、去掉 training CPU/内存上限、去掉 `version` 字段
- `systemd/edge-cloud.service`：WorkingDirectory 改为 `__DEPLOY_DIR__` 模板

**移除 edge_infer 挂载**
- `docker-compose.dev.yml` 移除 `EDGE_INFER_PATH` 挂载，云边平台不需要挂载边缘侧仓库
- `.env` 和 `.env.wsl2` 同步移除 `EDGE_INFER_PATH` 变量

**依赖更新**
- `training/requirements.txt`：新增 `timm`、`transformers`、`einops`、`paho-mqtt`、`safetensors`

**新增文件**
- `deployment/docker/keepalive.ps1`：WSL2 keepalive 辅助脚本
- `deployment/docker/training-entrypoint.sh`：训练容器入口脚本

### 文档
- `README_DOCKER.md`：生产/开发彻底分离、S3 恢复为默认存储、部署统一为 `deploy.sh` 一条命令
- `docs/DEPLOYMENT.md`：WSL2 部署章节更新、Docker Desktop 代理清理说明

---

## v2026.05.26 — WSL2 开发环境 + 移除 API Key + 云端无图过滤

### 新增

**WSL2 跨平台 Docker 部署**
- WSL2 Ubuntu 内安装 docker-ce + nvidia-container-toolkit，GPU 直通验证通过
- `docker-compose.yml` 外部资源路径参数化（`EDGE_INFER_PATH` / `EXTERNAL_DATA_PATH`），兼容 Windows / WSL2 / Linux
- 新增 `.env.wsl2`：WSL2 特有路径覆盖
- `deploy.sh` 新增平台自动检测（`detect_platform`），WSL2 环境自动加载 `.env.wsl2`
- 模型权重通过符号链接共享（WSL2 原生文件系统 + `/mnt/d/` 访问 Windows 磁盘）

### 变更

**移除 API Key 认证**
- 删除 `spring-boot-starter-security` 依赖、`SecurityConfig`、`ApiKeyFilter`、`ApiKeyAuthentication`
- `OpenApiConfig` 移除 API Key 安全定义
- `application.yml` 移除 `edge.api.key` 配置项
- 前端 `api/index.ts` 移除 `X-API-Key` header
- **原因**：SPA 前端的 API Key 写在客户端 JS 中，任何人 F12 即可获取，不提供真正的安全价值。生产环境应依赖网络层防护（Nginx + HTTPS + 内网隔离）

**云端 RADIO 无图过滤**
- `engine.py`：图片生成失败或无 segments 时不上报（`if not image_b64: return None`），与边缘 smart 模式一致，避免无图告警

**RADIO 裸土检测提示词修正**
- `construction_safety.yaml`：正面提示词增加 "ground level" 和 "soil granules" 限定，反面提示词新增 4 条楼顶/建筑表面描述

**RADIO 模型下载文档**
- 新增 C-RADIOv4-H、SigLIP2、RADIO 模型下载地址和命令

---

## v2026.05.25 — 生产部署镜像化 + API 认证 + 第三方对接文档

### 新增

**API 认证（Spring Security + API Key）**
- `spring-boot-starter-security` 依赖
- `SecurityConfig.java`：无状态安全配置，公开端点（health、swagger、ws、云端推理上报），其他 API 需认证
- `ApiKeyFilter.java` + `ApiKeyAuthentication.java`：`X-API-Key` header 校验
- `OpenApiConfig.java`：Swagger UI 增加 API Key 安全定义
- `application.yml` 新增 `edge.api.key` 配置项，支持环境变量 `API_KEY`

**镜像构建与推送**
- `deployment/docker/build-push.sh`：一键构建 backend/frontend 镜像并推送到私有仓库

**第三方对接文档**
- `docs/integration-guide.md`：快速参考指南（REST API、Webhook、MQTT、WebSocket），含部署模式对照表

**部署脚本增强**
- `deploy.sh --init`：首次部署（生成 .env + 随机 API Key、初始化 SeaweedFS、等待数据库就绪）
- `deploy.sh --backup`：PostgreSQL 数据备份（gzip 压缩）
- `deploy.sh --restore`：数据恢复
- 端口占用和磁盘空间检查

### 变更

**配置文件更新**
- `.env.example`：更新为 SeaweedFS（替代 MinIO/InfluxDB）、新增 API_KEY、CLOUD_API_URL、REGISTRY
- `.env`：同步更新，移除过时的 InfluxDB/MinIO 引用
- `docker-compose.prod.yml`：backend 新增 `API_KEY` 环境变量

**文档同步更新**
- `THIRD_PARTY_INTEGRATION.md`：添加 API Key 认证说明、更新端口为生产模式（80 端口统一入口）、Python 示例适配
- `QUICKSTART.md`：新增生产模式部署命令和访问地址（开发/生产双表格）
- `DEPLOYMENT.md`：新增 `--init`/`--backup`/`--restore` 命令说明、API Key 配置
- `README_DOCKER.md`：新增 7.4 API 认证章节、生产环境建议增加 API Key
- `docs/README.md`：索引新增 integration-guide.md
- 所有文档中 `SnakeJenny`/`your-org` 仓库地址修正为 `AirAI-Lab`

---

## v2026.05.12 — 前端布局重构 + SCSS 视觉升级 + RADIO 提示词优化

### 新增

**前端布局重构**
- **Layout 组件体系**（`frontend/src/layout/`）：从 App.vue 提取独立布局组件
  - `Sidebar.vue`：侧边栏导航，支持折叠
  - `Header.vue`：顶部导航栏，面包屑 + 用户菜单
  - `TagsView.vue`：标签页导航，支持多页签切换和关闭
  - `Breadcrumb.vue`：面包屑路径
  - `layout/index.vue`：布局容器，组合 Sidebar + Header + TagsView
- **路由嵌套重构**（`router/index.ts`）：所有页面路由嵌套在 Layout 子路由下，支持 TagsView 多页签
- **Pinia Store**（`stores/app.ts`）：全局应用状态管理
- **NProgress 路由进度条**：路由切换时顶部进度条动画

**前端 SCSS 视觉升级**
- **CSS 变量系统**（`styles/variables.scss`）：主题色、灰色梯度、圆角、间距统一变量
- **Element Plus 组件覆盖**（`styles/element-overrides.scss`）：统一组件高度/圆角、dialog 缩放动画、message 无边框、table hover 等
- **全局基础样式**（`styles/global.scss`）：自定义滚动条、卡片工具类、badge 呼吸动画
- **SCSS Mixins**（`styles/mixins.scss`）：文本省略、居中定位、毛玻璃效果
- **Vite SCSS 全局注入**：所有组件自动可用 mixins，无需手动 import
- **新增依赖**：sass、@vueuse/core、nprogress、@types/nprogress

**后端改进**
- **全局异常处理**（`GlobalExceptionHandler.java`）：捕获 JSON 反序列化等框架错误，避免 500 空响应
- **心跳字段更新**（`DeviceCommunicationService.java`）：心跳上报同步更新设备静态信息（deviceName、deviceType、IP、gpuModel、osVersion 等），旧设备自动填充默认值
- **MQTT 自动重连**（`MqttService.java`）：`MqttCallback` → `MqttCallbackExtended`，利用 Paho 内置自动重连，移除 `@Scheduled` 手动重连
- **Device 实体字段长度**：`osVersion` 50→255、`gpuModel` 100→255，适配长版本字符串

**RADIO 云端推理**
- **裸土检测提示词优化**（`construction_safety.yaml`）：修复楼顶误检为裸土的问题
  - 正面提示词强调 "ground level"（地面）和 "soil granules"（土壤颗粒）
  - 反面提示词新增 4 条楼顶/建筑表面描述，降低对比分数

### 变更
- `App.vue` 从 ~200 行精简至 ~3 行，布局逻辑全部迁移到 Layout 组件
- `DeviceList.vue` 新增设备类型筛选、紧凑布局
- `DeviceDetail.vue` 新增设备类别、通信协议、能力标签、推理 FPS 展示
- `api/index.ts` 新增设备扩展 API（byType、byCategory、byTag、tags CRUD、commands）

---

## v2026.05.11 — 插件化推理 + EMQX 规则引擎 + 设备管理扩展

### 新增

**Task 1: 云端推理插件化重构**
- **插件基类** (`models/cloud_inference/plugin_base.py`)：`ScenarioPlugin` 从 YAML `cloud.radio.classes.*.alert` 动态读取告警规则，替代硬编码 `alert_map`
- **推理引擎** (`models/cloud_inference/engine.py`)：从 `radio_infer_server.py` 提取推理核心逻辑，委托给 plugin 生成告警
- **主服务精简** (`models/cloud_inference/radio_infer_server.py`)：从 ~739 行缩减到 ~546 行，删除硬编码告警和标注逻辑
- **文件迁移**：`cloud/` → `models/cloud_inference/`，通过 volume 挂载无需手动同步
- **新场景零代码接入**：只需创建 YAML 配置文件，指定 `--config` 即可运行

**Task 2: EMQX 规则引擎 + Docker Profiles**
- **4 条 EMQX 规则**：边缘/云端结果归一化 + 告警提取，自动路由到统一 topic 树
- **统一 topic 树**：`results/{device_id}/{channel_id}/{source}` 和 `alerts/{device_id}/{source}`
- **规则初始化脚本** (`deployment/emqx/init_rules.sh`)：容器启动自动创建规则，幂等
- **Docker Compose profiles**：3 种部署模式（纯推理 2 容器 / 推理+管理 8 容器 / 完整平台 10 容器）
- **后端订阅统一 topic**：`MqttService` 新增 `results/#` 订阅用于监控

**Task 3: 设备管理扩展**
- **设备类型枚举** (`DeviceType.java`)：JETSON_ORIN / DRONE / ROBOT_DOG / VEHICLE / SENSOR / CAMERA
- **能力模型** (`DeviceCapability.java`)：VIDEO_INPUT / INFERENCE / CONTROL / OTA_UPDATE 等
- **标签系统** (`DeviceTag.java` + `DeviceTagController.java`)：设备标签 CRUD + 按标签查询
- **命令持久化** (`DeviceCommand.java`)：设备下发命令审计记录
- **新 API 端点**：`GET /devices/by-type`、`GET /devices/by-category`、`GET /devices/{id}/commands`、标签 CRUD
- **向后兼容**：旧设备心跳自动填充默认值，现有 API 不变

### 改进
- `construction_safety.yaml` 补充 4 个 cloud radio classes 的 alert 字段
- `water_inspection.yaml` 告警级别与生产值对齐（black_water → critical 等）
- `test_plugin.py` 验证 4 个场景的 YAML 告警规则与旧硬编码一致

### 文档
- `README_DOCKER.md` 更新云端推理命令路径 + 多场景配置说明
- `INFERENCE_PIPELINE.md` 更新路径 + 移除手动同步说明 + 更新文件结构表
- `CODE_ANALYSIS_CLOUD.md` 更新为插件化架构描述
- `THIRD_PARTY_INTEGRATION.md` 增加 EMQX 统一 topic 订阅说明 + 更新示例代码
- `DEPLOYMENT.md` 增加 Docker Profiles 3 种部署模式说明

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
