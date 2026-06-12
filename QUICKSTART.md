# 云边协同空间智能平台文档入口

## 1. 平台定位

本平台是云边协同空间智能平台，面向视频感知、边缘一体机、传感器、无人车、无人机、机器人和机器狗等设备，提供视频接入、设备管理、边缘推理结果接入、云端训练、大模型分析、空间态势、告警处置和报表能力。

## 2. 技术边界

- ZLMediaKit/C++：负责流媒体核心。
- edge_infer/C++：负责边缘侧取流、推流、解码、推理、结果上报和离线缓存。
- Spring Boot/Java：负责平台业务、权限、审计、数据治理和业务编排。
- Python：负责云端训练、云端推理、抽帧分析、零样本推理、大模型推理和评测。
- Vue3/TypeScript：负责管理端、空间态势、视频工作台、报表和 AI 助手。

## 3. 按角色阅读

### 市场、运营、售前、客户

- [市场方案](docs/business/MARKET_OVERVIEW.md)
- [场景解决方案](docs/business/SCENARIO_SOLUTIONS.md)
- [竞争优势与投标指标](docs/business/COMPETITIVE_ADVANTAGES.md)

### 产品、项目、UI、实施

- [产品需求文档](docs/product/PRODUCT_REQUIREMENTS.md)
- [用户手册](docs/product/USER_MANUAL.md)
- [UI/UX 设计规范](docs/product/UI_UX_DESIGN_GUIDE.md)

### 开发、运维、第三方集成

- [技术架构文档](docs/technical/ARCHITECTURE.md)
- [API 与第三方集成文档](docs/technical/API_AND_INTEGRATION.md)
- [训练与模型交付指南](docs/technical/TRAINING_AND_MODEL_GUIDE.md)
- [开发计划](docs/technical/DEVELOPMENT_PLAN.md)
- [运维与故障排查](docs/technical/OPERATIONS_AND_TROUBLESHOOTING.md)
- [Docker 部署手册](README_DOCKER.md)

## 4. 快速部署

部署以 [README_DOCKER.md](README_DOCKER.md) 为准。

支持：

- 开发版：Windows + WSL + Docker。
- 生产版：Linux + Docker。

## 5. 当前 MVP 范围

- 二维地图接入。
- 摄像头和边缘设备点位绑定。
- RTSP 视频接入和预览。
- ZLMediaKit 流状态同步。
- edge_infer 边缘推理结果接入。
- 告警事件和证据展示。
- 数据集、训练任务、模型版本基础闭环。
- AI 助手只读问答和日报/月报草稿。

## 6. 文档维护规则

- 正式文档只保留在 `docs/business`、`docs/product`、`docs/technical` 三类目录。
- 旧文档统一归档到 `docs/archive`，不作为正式入口。
- 部署流程以根目录 `README_DOCKER.md` 为准。
- 文档内容必须与当前代码、部署方式和产品定位保持一致。
