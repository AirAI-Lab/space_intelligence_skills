# edge_infer_cloud 文档目录

## 快速开始

| 文档 | 说明 |
|------|------|
| [QUICKSTART.md](QUICKSTART.md) | 5 分钟快速部署指南（3 种部署模式） |
| [DEPLOYMENT.md](DEPLOYMENT.md) | 完整部署指南（开发/生产/Linux 迁移） |
| [THIRD_PARTY_INTEGRATION.md](THIRD_PARTY_INTEGRATION.md) | 第三方平台对接指南（MQTT/Webhook/REST） |
| [integration-guide.md](integration-guide.md) | 第三方对接快速参考（REST/Webhook/MQTT/WebSocket） |

## API 参考

| 文档 | 说明 |
|------|------|
| [api/README.md](api/README.md) | REST API 完整参考（推理、设备、Webhook、文件、OTA） |
| [EDGE_REST_API.md](EDGE_REST_API.md) | 边缘设备 REST API（注册、心跳、命令、推理上报） |
| [INFERENCE_PIPELINE.md](INFERENCE_PIPELINE.md) | 云边协同推理管线详解（边缘推理 → 云端 C-RADIOv4 → 后端） |

## 用户手册 (`user_manual/`)

对应后端 Controller 功能模块，面向平台使用者：

| 文档 | 对应后端模块 |
|------|-------------|
| [02_device_management](user_manual/02_device_management.md) | DeviceController — 设备注册、状态监控 |
| [03_data_management](user_manual/03_data_management.md) | DatasetController — 数据集上传、标注 |
| [04_training](user_manual/04_training.md) | TrainingController — 在线训练、参数配置 |
| [05_model_deploy](user_manual/05_model_deploy.md) | DeploymentController — 模型部署、TensorRT 转换 |
| [06_ota_upgrade](user_manual/06_ota_upgrade.md) | OtaController — OTA 升级、灰度发布 |

## 开发文档 (`development/`)

面向开发者，代码分析与架构设计：

| 文档 | 说明 |
|------|------|
| [CODE_ANALYSIS_EDGE](development/CODE_ANALYSIS_EDGE.md) | 边缘推理框架代码分析（C++ 插件系统、CUDA 预处理） |
| [CODE_ANALYSIS_CLOUD](development/CODE_ANALYSIS_CLOUD.md) | 云端平台代码分析（Spring Boot、Vue 3、C-RADIOv4 推理） |
| [EDGE_INFER_FRAMEWORK](development/EDGE_INFER_FRAMEWORK.md) | 边缘推理框架开发指南 |
| [TRAINING_GUIDE](development/TRAINING_GUIDE.md) | 数据集与训练流程详解 |

## 产品设计 (`design/`)

面向团队内部，产品定位与未来规划：

| 文档 | 说明 |
|------|------|
| [OVERVIEW](design/OVERVIEW.md) | 系统总览与产品定位 |
| [ARCHITECTURE_CLARIFICATION](design/ARCHITECTURE_CLARIFICATION.md) | 云边分离开发模式说明 |
| [PRODUCT_ROADMAP](design/PRODUCT_ROADMAP.md) | 产品路线图 |
| [WORK_PLAN](design/WORK_PLAN.md) | 工作计划与里程碑 |
| [MULTI_AGENT_DESIGN](design/MULTI_AGENT_DESIGN.md) | 多智能体架构设计 |
| [TECHNICAL_MOAT](design/TECHNICAL_MOAT.md) | 技术护城河方案 |

## 商业与实施 (`business/`)

面向招投标、商务和项目管理：

| 文档 | 说明 |
|------|------|
| [TECHNICAL_ADVANTAGES](business/TECHNICAL_ADVANTAGES.md) | 投标技术优势 |
| [BUSINESS_PLAN](business/BUSINESS_PLAN.md) | 商业计划 |
| [IMPLEMENTATION_MASTER_PLAN](business/IMPLEMENTATION_MASTER_PLAN.md) | 实施总纲 |
| [CONSTRUCTION_SAFETY_STRATEGY](business/CONSTRUCTION_SAFETY_STRATEGY.md) | 施工安全实施策略 |
| [WATER_INSPECTION_PLAN](business/WATER_INSPECTION_PLAN.md) | 水利巡检技术方案 |
| [algorithm_inventory](business/algorithm_inventory.md) | 算法清单（120+） |

## 操作指南 (`guides/`)

| 文档 | 说明 |
|------|------|
| [GIT_VERSION_CONTROL](guides/GIT_VERSION_CONTROL.md) | Git 版本管理 |
| [SAFE_COMMIT_STRATEGY](guides/SAFE_COMMIT_STRATEGY.md) | 自动化提交安全策略 |
| [24H_AUTOMATION](guides/24H_AUTOMATION.md) | 24 小时自动化工作方案 |

## 其他

- [LICENSE_COMPLIANCE.md](LICENSE_COMPLIANCE.md) — 开源协议合规性说明
- [articles/](articles/) — 技术文章系列（RADIO、YOLO、平台等）
