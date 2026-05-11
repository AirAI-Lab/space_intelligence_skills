# 云边协同平台代码分析报告

## 项目概述

**项目名称**: edge_infer_cloud (SkyEdge AI - 云边协同推理平台)
**项目路径**: D:\github\edge_infer_cloud
**技术栈**:
- 后端: Spring Boot (Java 17+) + PostgreSQL + TimescaleDB + Redis + MQTT
- 前端: Vue 3 + Element Plus + TypeScript
- 训练: Python + Flask + YOLOv8 + PyTorch
- 模型: PyTorch (变化检测 RCMT/RCMT-V3) + ONNX + TensorRT
- 部署: Docker + Docker Compose

---

## 一、后端服务架构

### 1.1 技术架构

**框架**: Spring Boot 3.x
**数据库**: PostgreSQL 16 + TimescaleDB (时序数据)
**缓存**: Redis
**消息队列**: MQTT (EMQX) + WebSocket (实时推送)
**文件存储**: 本地文件系统 / S3 (可配置)

### 1.2 分层架构

```
backend/src/main/java/com/edge/cloud/
├── EdgeCloudApplication.java          # 应用入口
├── config/                             # 配置层
│   ├── RestTemplateConfig.java        # HTTP客户端配置
│   └── WebSocketConfig.java            # WebSocket配置
├── controller/                         # 控制器层 (API接口)
│   ├── ModelController.java            # 模型管理
│   ├── DeviceController.java           # 设备管理
│   ├── TrainingController.java         # 训练任务管理
│   ├── DeploymentController.java       # 部署记录管理
│   ├── OtaController.java              # OTA升级管理
│   ├── EdgeDeviceController.java       # 边缘设备通信
│   ├── DatasetController.java          # 数据集管理
│   ├── ConversionController.java       # 模型转换
│   ├── FileController.java             # 文件管理
│   └── HealthController.java           # 健康检查
├── dto/                                # 数据传输对象
├── entity/                             # 实体类 (JPA)
├── repository/                         # 数据访问层
└── service/                            # 业务逻辑层
    ├── ModelService.java               # 模型业务逻辑
    ├── TrainingService.java            # 训练业务逻辑
    ├── DeploymentService.java          # 部署业务逻辑
    ├── OtaService.java                # OTA业务逻辑
    ├── DeviceCommunicationService.java # 设备通信
    ├── MqttService.java                # MQTT服务
    ├── WebSocketMessageService.java    # WebSocket消息
    ├── ConversionService.java          # 模型转换
    ├── StorageService.java             # 存储服务接口
    └── AutoRollbackService.java        # 自动回滚
```

### 1.3 后端API接口列表

#### 1.3.1 模型管理 API (`/api/v1/models`)

| 方法 | 路径 | 说明 | 请求体 |
|------|------|------|--------|
| POST | `/models` | 创建模型记录 | `{modelName, modelType, framework, version}` |
| POST | `/models/{model_id}/upload` | 上传模型文件 | MultipartFile |
| POST | `/models/{model_id}/convert` | 转换模型格式 | `{conversionType}` |
| POST | `/models/{model_id}/reconvert` | 重新转换模型 | `{conversionType}` |
| GET | `/models/{model_id}` | 获取模型详情 | - |
| GET | `/models` | 分页查询模型列表 | `{page, pageSize, type, status}` |
| GET | `/models/deployable` | 获取可部署模型列表 | - |
| GET | `/models/{model_id}/download` | 下载模型文件 | `{format}` |
| GET | `/models/{model_id}/download-info` | 获取模型下载信息 | - |
| GET | `/models/{model_id}/preview-url` | 获取模型预览URL | `{format}` |
| DELETE | `/models/{model_id}` | 删除模型 | - |
| POST | `/models/internal/{model_id}/deploy/increment` | 增加部署计数 (内部) | - |
| POST | `/models/internal/{model_id}/deploy/decrement` | 减少部署计数 (内部) | - |

**模型转换类型**:
- `PT_TO_ONNX`: PyTorch → ONNX
- `ONNX_TO_ENGINE_FP16`: ONNX → TensorRT FP16
- `ONNX_TO_ENGINE_INT8`: ONNX → TensorRT INT8
- `ONNX_TO_ENGINE_FP32`: ONNX → TensorRT FP32

#### 1.3.2 设备管理 API (`/api/v1/devices`)

| 方法 | 路径 | 说明 | 请求体 |
|------|------|------|--------|
| GET | `/devices` | 获取设备列表 | `{page, pageSize, search, status}` |
| POST | `/devices` | 注册设备 | `{device_id, device_name, device_type, ...}` |
| GET | `/devices/{device_id}` | 获取设备详情 | - |
| PUT | `/devices/{device_id}` | 更新设备 | Device对象 |
| DELETE | `/devices/{device_id}` | 删除设备 | - |

#### 1.3.3 训练任务管理 API (`/api/v1/training`)

| 方法 | 路径 | 说明 | 请求体 |
|------|------|------|--------|
| POST | `/training` | 创建训练任务 | `{jobName, datasetId, epochs, ...}` |
| POST | `/training/{job_id}/start` | 启动训练任务 | - |
| POST | `/training/{job_id}/stop` | 停止训练任务 | - |
| POST | `/training/{job_id}/pause` | 暂停训练任务 | - |
| POST | `/training/{job_id}/resume` | 恢复训练任务 | - |
| GET | `/training` | 分页查询训练任务 | `{page, pageSize, status}` |
| GET | `/training/{job_id}` | 获取训练任务详情 | - |
| GET | `/training/{job_id}/metrics` | 获取训练指标 | - |
| GET | `/training/{job_id}/logs` | 获取训练日志 | `{lines}` |
| DELETE | `/training/{job_id}` | 删除训练任务 | - |
| GET | `/training/{job_id}/actual-progress` | 获取实际训练进度 | - |
| POST | `/training/{job_id}/create-model` | 从训练任务创建模型记录 | - |
| POST | `/training/internal/{job_id}/progress` | 更新训练进度 (内部) | - |
| POST | `/training/internal/{job_id}/complete` | 训练完成通知 (内部) | - |

#### 1.3.4 部署记录 API (`/api/v1/deployments`)

| 方法 | 路径 | 说明 | 请求体 |
|------|------|------|--------|
| GET | `/deployments/{deployment_id}` | 获取部署记录详情 | - |
| GET | `/deployments` | 分页查询部署记录 | `{modelId, deviceId, status, ...}` |
| GET | `/deployments/recent` | 获取最近部署记录 | `{page, pageSize}` |
| GET | `/deployments/model/{model_id}/history` | 获取模型的部署历史 | - |
| GET | `/deployments/model/{model_id}/stats` | 获取模型部署统计 | - |
| GET | `/deployments/model/{model_id}/active-devices` | 获取模型当前运行的设备列表 | - |
| GET | `/deployments/device/{device_id}/history` | 获取设备的部署历史 | `{page, pageSize}` |
| GET | `/deployments/device/{device_id}/current` | 获取设备的当前部署信息 | - |
| DELETE | `/deployments/{deployment_id}` | 删除部署记录 | - |
| DELETE | `/deployments/batch` | 批量删除部署记录 | `[deploymentId1, ...]` |
| DELETE | `/deployments/clear` | 清空所有已完成/失败的部署记录 | - |

#### 1.3.5 OTA升级管理 API (`/api/v1/ota`)

| 方法 | 路径 | 说明 | 请求体 |
|------|------|------|--------|
| POST | `/ota/tasks` | 创建OTA升级任务 | `{taskName, upgradeType, deviceIds, ...}` |
| POST | `/ota/tasks/{task_id}/start` | 启动OTA升级任务 | - |
| GET | `/ota/tasks/{task_id}` | 获取OTA升级任务详情 | - |
| GET | `/ota/tasks` | 分页查询OTA升级任务 | `{page, pageSize, status}` |
| GET | `/ota/tasks/{task_id}/devices` | 获取任务的所有设备状态 | - |
| GET | `/ota/pending/{device_id}` | 查询设备的待处理OTA任务 | - |
| DELETE | `/ota/tasks/{task_id}` | 删除OTA升级任务 | - |
| POST | `/ota/tasks/{task_id}/retry` | 重试失败设备 | - |
| POST | `/ota/tasks/{task_id}/devices/{device_id}/retry` | 重试单个设备 | - |
| POST | `/ota/tasks/{task_id}/devices/{device_id}/rollback` | 回滚设备升级 | - |
| GET | `/ota/tasks/{task_id}/devices/summary` | 获取设备状态汇总 | - |
| POST | `/ota/tasks/{task_id}/pause` | 暂停升级任务 | - |
| POST | `/ota/tasks/{task_id}/resume` | 恢复升级任务 | - |
| POST | `/ota/tasks/{task_id}/devices/{device_id}/replace-model` | 替换模型 (触发热加载) | - |
| POST | `/ota/internal/tasks/{task_id}/devices/{device_id}/progress` | 设备升级进度更新 (MQTT回调) | - |
| POST | `/ota/internal/tasks/{task_id}/devices/{device_id}/complete` | 设备升级完成 (MQTT回调) | - |
| POST | `/ota/internal/tasks/{task_id}/devices/{device_id}/fail` | 设备升级失败 (MQTT回调) | - |

#### 1.3.6 边缘设备通信 API (`/api/v1/edge`)

| 方法 | 路径 | 说明 | 请求体 |
|------|------|------|--------|
| POST | `/edge/heartbeat` | 设备心跳 | `{deviceId, cpuUsage, gpuUsage, ...}` |
| POST | `/edge/register` | 设备注册 | DeviceHeartbeatRequest |
| POST | `/edge/ota/status` | OTA升级状态上报 | `{taskId, deviceId, status, progress}` |
| POST | `/edge/inference/result` | 推理结果上报 | `{deviceId, modelId, detections}` |
| GET | `/edge/commands` | 获取待执行命令 | `{device_id, last_command_id}` |
| GET | `/edge/models/{model_id}/download` | 下载模型文件 | - |
| POST | `/edge/commands/{command_id}/ack` | 命令执行确认 | `{device_id}` |

#### 1.3.7 数据集管理 API (`/api/v1/datasets`)

| 方法 | 路径 | 说明 | 请求体 |
|------|------|------|--------|
| POST | `/datasets/upload` | 上传数据集 | MultipartFile + FormData |
| GET | `/datasets` | 获取数据集列表 | `{page, pageSize, search}` |
| GET | `/datasets/{dataset_id}` | 获取数据集详情 | - |
| DELETE | `/datasets/{dataset_id}` | 删除数据集 | - |
| POST | `/datasets/{dataset_id}/validate` | 重新验证数据集 | - |

#### 1.3.8 模型转换 API (`/api/v1/conversion`)

| 方法 | 路径 | 说明 | 请求体 |
|------|------|------|--------|
| POST | `/conversion/{task_id}/start` | 启动转换任务 | - |
| GET | `/conversion/tasks/{task_id}` | 获取转换任务详情 | - |
| GET | `/conversion/models/{model_id}/tasks` | 根据模型ID查询转换任务 | - |
| GET | `/conversion/tasks` | 分页查询转换任务 | `{page, pageSize, status}` |
| DELETE | `/conversion/tasks/{task_id}` | 删除转换任务 | - |

### 1.4 数据库结构

**核心表**:

1. **devices** - 设备表
2. **datasets** - 数据集表
3. **models** - 模型表
4. **training_jobs** - 训练任务表
5. **training_metrics** - 训练指标表 (TimescaleDB超表)
6. **model_deployments** - 模型部署表
7. **ota_tasks** - OTA任务表
8. **device_upgrade_status** - 设备升级状态表
9. **conversion_tasks** - 模型转换任务表

**主要关系**:
- models → datasets (多对一)
- models → models (父子关系，通过parent_model_id)
- training_jobs → datasets (多对一)
- training_jobs → models (输出模型)
- model_deployments → models (多对一)
- model_deployments → devices (多对一)
- ota_tasks → models (多对一，OTA升级模型)
- ota_tasks → device_upgrade_status (一对多)

---

## 二、前端组件结构

### 2.1 技术栈

**框架**: Vue 3 (Composition API)
**UI库**: Element Plus
**语言**: TypeScript
**路由**: Vue Router 4
**HTTP客户端**: Axios
**构建工具**: Vite

### 2.2 目录结构

```
frontend/src/
├── App.vue                    # 根组件
├── main.ts                    # 应用入口
├── router/                    # 路由配置
│   └── index.ts              # 路由定义
├── api/                       # API调用封装
│   └── index.ts              # 所有API接口定义
├── components/               # 公共组件
├── stores/                   # 状态管理 (Pinia)
├── utils/                    # 工具函数
└── views/                    # 页面组件
    ├── Home.vue             # 首页
    ├── device/              # 设备管理
    │   ├── DeviceList.vue  # 设备列表
    │   └── DeviceDetail.vue # 设备详情
    ├── data/                # 数据管理
    │   ├── DatasetList.vue # 数据集列表
    │   └── DatasetDetail.vue # 数据集详情
    ├── training/            # 训练管理
    │   ├── TrainingJob.vue  # 训练任务列表
    │   └── TrainingDetail.vue # 训练任务详情
    ├── model/               # 模型管理
    │   ├── ModelList.vue    # 模型列表
    │   └── ModelDetail.vue  # 模型详情
    ├── ota/                 # OTA升级
    │   └── OtaTask.vue      # OTA任务列表
    └── deployment/          # 部署记录
        └── DeploymentRecord.vue # 部署记录
```

### 2.3 路由配置

| 路径 | 组件 | 说明 |
|------|------|------|
| `/` | Home.vue | 首页 |
| `/device` | DeviceList.vue | 设备列表 |
| `/device/:id` | DeviceDetail.vue | 设备详情 |
| `/data` | DatasetList.vue | 数据集列表 |
| `/data/datasets/:id` | DatasetDetail.vue | 数据集详情 |
| `/training` | TrainingJob.vue | 训练任务列表 |
| `/training/:id` | TrainingDetail.vue | 训练任务详情 |
| `/model` | ModelList.vue | 模型列表 |
| `/model/:id` | ModelDetail.vue | 模型详情 |
| `/ota` | OtaTask.vue | OTA任务列表 |
| `/deployment` | DeploymentRecord.vue | 部署记录 |

### 2.4 前端页面和组件列表

#### 2.4.1 首页 (`Home.vue`)

**功能**:
- 系统概览
- 统计数据展示 (设备数、模型数、训练任务数等)
- 快捷入口

#### 2.4.2 设备管理

**DeviceList.vue** - 设备列表
- 设备列表展示 (表格)
- 设备状态筛选 (在线/离线)
- 设备搜索
- 设备注册
- 设备删除
- 设备详情查看

**DeviceDetail.vue** - 设备详情
- 设备基本信息
- 设备状态监控 (CPU/GPU/内存/磁盘)
- 设备部署历史
- 设备日志查看
- 设备配置管理

#### 2.4.3 数据管理

**DatasetList.vue** - 数据集列表
- 数据集列表展示
- 数据集上传 (文件/URL/本地路径)
- 数据集删除
- 数据集详情查看
- 数据集统计

**DatasetDetail.vue** - 数据集详情
- 数据集基本信息
- 数据集统计 (类别数/样本数)
- 数据集结构预览
- 数据集验证状态
- 数据集删除

#### 2.4.4 训练管理

**TrainingJob.vue** - 训练任务列表
- 训练任务列表展示
- 训练任务状态筛选 (运行中/已完成/失败等)
- 训练任务搜索
- 创建训练任务
- 启动/停止/暂停/恢复训练任务
- 训练任务详情查看
- 训练任务删除

**TrainingDetail.vue** - 训练任务详情
- 训练任务基本信息
- 训练进度展示 (进度条)
- 训练指标曲线 (Loss/mAP)
- 训练日志实时查看
- 训练参数配置
- 模型导出 (PyTorch/ONNX/TensorRT)
- 模型部署

#### 2.4.5 模型管理

**ModelList.vue** - 模型列表
- 模型列表展示
- 模型状态筛选 (就绪/训练中/已部署)
- 模型类型筛选
- 模型搜索
- 导入模型 (创建记录+上传文件)
- 模型删除
- 模型详情查看
- 模型部署

**ModelDetail.vue** - 模型详情
- 模型基本信息 (名称/类型/框架/版本)
- 模型性能指标 (mAP/Precision/Recall/推理时间)
- 模型文件管理 (PT/ONNX/Engine)
- 模型转换 (PyTorch→ONNX→TensorRT)
- 模型预览 (可视化)
- 模型部署
- 模型下载

#### 2.4.6 OTA升级

**OtaTask.vue** - OTA任务列表
- OTA任务列表展示
- OTA任务状态筛选
- 创建OTA任务 (模型升级/配置升级/固件升级)
- 启动/暂停/恢复OTA任务
- 重试失败设备
- 设备回滚
- OTA任务详情查看
- OTA任务删除

#### 2.4.7 部署记录

**DeploymentRecord.vue** - 部署记录
- 部署记录列表展示
- 部署状态筛选
- 按模型/设备/时间筛选
- 批量删除部署记录
- 部署统计 (模型部署数/设备部署历史)

### 2.5 API调用封装

**所有API接口定义在** `frontend/src/api/index.ts`

**API分组**:
- `deviceApi` - 设备管理
- `dataApi` - 数据集管理
- `trainingApi` - 训练任务管理
- `modelApi` - 模型管理
- `otaApi` - OTA升级管理
- `compatibilityApi` - 设备兼容性检查
- `inferenceApi` - 推理API
- `datasetStatsApi` - 数据集统计
- `conversionApi` - 模型转换
- `deploymentApi` - 部署记录

**示例**:

```typescript
// 获取模型列表
export const modelApi = {
  getList: (params: { page?: number; pageSize?: number; type?: string; status?: string }) =>
    request.get('/models', { params }),

  // 上传模型文件
  upload: (modelId: string, file: File, onProgress?: (percent: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    return uploadRequest.post(`/models/${modelId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      }
    })
  },

  // 部署模型
  deploy: (data: { modelId: string; deviceIds: string[] }) =>
    request.post('/models/deploy', data),
}
```

### 2.6 侧边栏菜单

**App.vue** 侧边栏菜单:

- **首页** (`/`)
- **设备管理** (`/device`)
- **数据管理** (`/data`)
- **训练管理** (`/training`)
- **模型管理** (`/model`)
- **OTA升级** (`/ota`)
- **部署记录** (`/deployment`)

---

## 三、数据流和通讯机制

### 3.1 通讯架构

```
┌─────────────────────────────────────────────────────────────┐
│                     前端 (Vue 3)                              │
│                   HTTP REST API                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                   后端 (Spring Boot)                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Controller → Service → Repository → PostgreSQL      │   │
│  └──────────────────────────────────────────────────────┘   │
│                        │                                     │
│  ┌─────────────────────┼───────────────────────────────┐   │
│  │                     │                               │   │
│  ▼                     ▼                               ▼   │
│ ┌───────┐          ┌────────┐                      ┌───────┐│
│ │ MQTT  │          │WebSocket│                     │ Redis  ││
│ └───────┘          └────────┘                      └───────┘│
└─────────────────────────────────────────────────────────────┘
        │                     │
        ▼                     ▼
┌───────────────┐    ┌──────────────┐
│ MQTT Broker   │    │  训练服务     │
│ (EMQX)        │    │  (Flask)     │
└───────────────┘    └──────────────┘
        │
        ▼
┌───────────────┐
│ 边缘设备       │
│ (Agent)       │
└───────────────┘
```

### 3.2 主要通讯方式

#### 3.2.1 HTTP REST API (前端↔后端)

**场景**: 前端与后端的常规数据交互

**示例**:
- 查询设备列表: `GET /api/v1/devices`
- 创建训练任务: `POST /api/v1/training`
- 上传模型文件: `POST /api/v1/models/{id}/upload`

**特点**:
- 请求/响应模式
- 支持大文件上传 (multipart/form-data)
- 统一响应格式: `{code, message, data}`

#### 3.2.2 MQTT (后端↔边缘设备)

**场景**: 边缘设备与云端的实时通讯

**MQTT主题**:
- 上行 (设备→云端):
  - `edge/device/{device_id}/heartbeat` - 设备心跳
  - `edge/device/{device_id}/ota/status` - OTA状态上报
  - `edge/device/{device_id}/inference/result` - 推理结果上报
- 下行 (云端→设备):
  - `edge/device/{device_id}/command` - 命令下发
  - `edge/device/{device_id}/ota/task` - OTA任务下发

**特点**:
- 实时性强
- 支持离线消息 (CleanSession=false)
- 适合网络不稳定的边缘环境

**代码实现** (`MqttService.java`):

```java
@PostConstruct
public void init() {
    MqttConnectOptions options = new MqttConnectOptions();
    options.setAutomaticReconnect(true);
    options.setCleanSession(false);  // 保持会话，支持离线消息
    mqttClient.connect(options);

    // 订阅设备状态反馈主题
    mqttClient.subscribe("edge/device/+/status");
    mqttClient.subscribe("edge/device/+/ota/status");
}
```

#### 3.2.3 WebSocket (后端↔前端)

**场景**: 前端实时接收设备状态、训练进度等推送消息

**WebSocket主题**:
- `/topic/devices/registered` - 新设备注册通知
- `/topic/device/{device_id}/status` - 设备状态更新
- `/topic/training/{job_id}/progress` - 训练进度更新
- `/topic/ota/{task_id}/progress` - OTA进度更新

**特点**:
- 实时推送
- 双向通讯
- 减少轮询开销

**代码实现** (`WebSocketConfig.java`):

```java
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {
    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        config.enableSimpleBroker("/topic");
        config.setApplicationDestinationPrefixes("/app");
    }
}
```

#### 3.2.4 REST (边缘设备↔后端)

**场景**: 边缘设备通过HTTP与后端通讯 (备用方案)

**API**:
- `POST /api/v1/edge/heartbeat` - 设备心跳
- `POST /api/v1/edge/register` - 设备注册
- `POST /api/v1/edge/ota/status` - OTA状态上报
- `GET /api/v1/edge/commands` - 获取待执行命令
- `GET /api/v1/edge/models/{model_id}/download` - 下载模型文件

**特点**:
- 无需MQTT
- 简单易用
- 适合短时连接

### 3.3 核心数据流

#### 3.3.1 训练流程数据流

```
1. 创建训练任务 (前端)
   前端 → POST /api/v1/training → 后端 → 训练服务

2. 训练服务执行训练
   训练服务 → 更新训练进度 → POST /api/v1/training/internal/{id}/progress → 后端

3. 后端推送进度到前端
   后端 → WebSocket推送 → 前端 (训练进度实时更新)

4. 训练完成
   训练服务 → POST /api/v1/training/internal/{id}/complete → 后端

5. 创建模型记录
   后端 → 调用 ModelService → 创建模型记录 → 数据库

6. 模型转换
   前端 → POST /api/v1/models/{id}/convert → 后端 → 训练服务 (转换)
   → 更新模型状态 → WebSocket推送 → 前端
```

#### 3.3.2 部署流程数据流

```
1. 前端发起部署
   前端 → POST /api/v1/models/deploy → 后端

2. 后端处理部署
   后端 → 创建部署记录 → 数据库
        → 检查设备兼容性
        → 增加部署计数 → POST /api/v1/models/internal/{id}/deploy/increment

3. 下发部署命令
   后端 → MQTT发送 → edge/device/{device_id}/command → 边缘设备
   (或: 后端 → 存储待下命令 → 边缘设备GET /api/v1/edge/commands获取)

4. 边缘设备下载模型
   边缘设备 → GET /api/v1/edge/models/{model_id}/download → 后端 → 返回下载URL

5. 边缘设备加载模型
   边缘设备 → 加载模型 → 推理

6. 边缘设备上报心跳
   边缘设备 → POST /api/v1/edge/heartbeat → 后端 → 更新设备状态

7. 后端推送设备状态到前端
   后端 → WebSocket推送 /topic/device/{device_id}/status → 前端
```

#### 3.3.3 OTA升级流程数据流

```
1. 创建OTA任务
   前端 → POST /api/v1/ota/tasks → 后端 → 创建OTA任务 → 数据库

2. 启动OTA任务
   前端 → POST /api/v1/ota/tasks/{id}/start → 后端

3. 下发OTA任务到设备
   后端 → MQTT发送 → edge/device/{device_id}/ota/task → 边缘设备

4. 边缘设备下载/应用更新
   边缘设备 → 下载模型/配置 → 应用更新

5. 边缘设备上报OTA进度
   边缘设备 → POST /api/v1/edge/ota/status → 后端
   (或: 边缘设备 → MQTT发送 → edge/device/{device_id}/ota/status → 后端)

6. 后端推送OTA进度到前端
   后端 → WebSocket推送 /topic/ota/{task_id}/progress → 前端

7. 升级完成
   边缘设备 → 上报完成 → 后端 → 更新OTA任务状态 → 前端
```

### 3.4 数据存储策略

**PostgreSQL**: 持久化存储
- 设备信息
- 模型信息
- 训练任务
- 部署记录
- OTA任务

**TimescaleDB**: 时序数据 (PostgreSQL扩展)
- 训练指标 (TrainingMetric)
- 设备心跳历史

**Redis**: 缓存
- 设备在线状态
- 训练任务进度缓存
- Session管理

**本地文件系统 / S3**: 文件存储
- 模型文件 (PT/ONNX/Engine)
- 数据集文件
- 训练输出 (权重/日志)

---

## 四、模型训练流程

### 4.1 训练服务架构

**服务框架**: Flask
**训练框架**: YOLOv8 (Ultralytics)
**实验追踪**: MLflow
**模型框架**: PyTorch

**目录结构**:

```
training/
├── app.py                        # Flask应用入口
├── requirements.txt              # Python依赖
├── yolo26n.pt                    # YOLOv8n预训练权重
└── edge_train/                   # 训练核心模块
    ├── __init__.py
    ├── trainer.py               # YOLO训练器
    ├── converter.py             # 模型转换器 (ONNX/TensorRT)
    ├── validator.py             # 验证器
    ├── optimizer.py             # 智能参数优化器
    ├── augmentation.py          # 数据增强
    ├── config.py                # 配置管理
    └── autotrainer.py           # 自动训练器
```

### 4.2 训练流程详解

#### 4.2.1 创建训练任务

**入口**: `POST /api/v1/training`

**步骤**:

1. **数据集验证**
   - 检查数据集是否存在 (`DatasetRepository.findById()`)
   - 检查数据集状态是否为 `READY`
   - 支持三种数据集来源:
     - `backend`: 后端上传的数据集
     - `url`: 远程URL数据集
     - `local`: 本地路径数据集

2. **续训处理**
   - 如果是续训 (`resume=true`)
   - 检查原任务是否存在
   - 读取原任务的训练进度 (`results.csv`)
   - 加载原任务的权重 (`last.pt`)

3. **创建训练任务记录**
   ```java
   TrainingJob job = new TrainingJob();
   job.setJobId("JOB" + System.currentTimeMillis());
   job.setJobName(request.getJobName());
   job.setDatasetId(datasetId);
   job.setBaseModel(request.getBaseModel());
   job.setEpochs(request.getEpochs());
   job.setBatchSize(request.getBatchSize());
   // ... 其他参数
   job.setStatus(TrainingStatus.PENDING);
   trainingJobRepository.save(job);
   ```

4. **调用训练服务**
   ```java
   String trainUrl = trainingServiceUrl + "/train";
   Map<String, Object> requestBody = new HashMap<>();
   requestBody.put("job_id", job.getJobId());
   requestBody.put("dataset_id", datasetId);
   requestBody.put("epochs", job.getEpochs());
   // ... 其他参数
   restTemplate.postForEntity(trainUrl, requestBody, Map.class);
   ```

#### 4.2.2 训练服务接收请求

**入口**: `POST /train` (Flask)

**代码** (`app.py`):

```python
@app.route('/train', methods=['POST'])
def start_training():
    data = request.get_json()

    job_id = data.get('job_id')
    dataset_id = data.get('dataset_id')
    dataset_source = data.get('dataset_source', 'backend')
    epochs = data.get('epochs', 100)
    batch_size = data.get('batch_size', 16)
    img_size = data.get('img_size', 640)
    use_gpu = data.get('use_gpu', True)
    base_model = data.get('base_model', 'yolov8n.pt')
    resume = data.get('resume', False)
    resume_job_id = data.get('resume_job_id')

    # 启动训练任务
    result = trainer.start_training(
        job_id=job_id,
        dataset_id=dataset_id,
        dataset_source=dataset_source,
        epochs=epochs,
        batch_size=batch_size,
        img_size=img_size,
        use_gpu=use_gpu,
        base_model=base_model,
        resume=resume,
        resume_job_id=resume_job_id
    )

    return jsonify(result)
```

#### 4.2.3 训练执行

**代码** (`trainer.py`):

```python
class YOLOTrainer:
    def start_training(self, job_id, dataset_id, dataset_source,
                       epochs, batch_size, img_size, use_gpu, base_model,
                       resume=False, resume_job_id=None, enable_smart_optimization=True):
        """启动训练任务"""

        # 1. 准备数据集
        if dataset_source == "backend":
            # 从后端下载数据集
            dataset_path = self._download_dataset(dataset_id)
        elif dataset_source == "url":
            dataset_path = self._download_from_url(dataset_url)
        elif dataset_source == "local":
            dataset_path = dataset_path

        # 2. 准备模型
        if resume and resume_job_id:
            # 续训: 加载之前的权重
            resume_weights = self.config.get_output_path(resume_job_id) / 'train' / 'weights' / 'last.pt'
            model = YOLO(str(resume_weights))
            start_epoch = self._get_actual_progress(resume_job_id)
        else:
            # 新训练: 加载预训练权重
            model = YOLO(base_model)
            start_epoch = 0

        # 3. 配置超参数
        hyperparams = {
            'optimizer': hyperparameters.get('optimizer', 'AdamW'),
            'lr0': hyperparameters.get('lr0', 0.01),
            'weight_decay': hyperparameters.get('weight_decay', 0.0005),
            'mosaic': hyperparameters.get('mosaic', 1.0),
            'mixup': hyperparameters.get('mixup', 0.0),
            # ... 其他参数
        }

        # 4. 启动MLflow实验追踪
        mlflow.start_run(run_name=job_id)

        # 5. 启动训练线程 (后台执行)
        def train_thread():
            try:
                # 更新状态为RUNNING
                self._update_training_status(job_id, 'RUNNING')

                # 训练模型
                results = model.train(
                    data=str(dataset_path / 'data.yaml'),
                    epochs=epochs,
                    batch=batch_size,
                    imgsz=img_size,
                    device='cuda' if use_gpu else 'cpu',
                    project=str(self.config.get_output_path(job_id)),
                    name='train',
                    resume=resume,
                    **hyperparams
                )

                # 训练完成
                best_map = results.results_dict.get('metrics/mAP50-95(B)', 0)
                best_epoch = results.results_dict.get('best_epoch', 0)
                final_loss = results.results_dict.get('train/box_loss', 0)

                # 回调后端: 训练完成
                self._notify_training_complete(job_id, best_map, best_epoch, final_loss)

                # 更新状态为COMPLETED
                self._update_training_status(job_id, 'COMPLETED')

            except Exception as e:
                logger.error(f"训练失败: {e}")
                self._update_training_status(job_id, 'FAILED')

        thread = threading.Thread(target=train_thread)
        thread.daemon = True
        thread.start()

        return {'status': 'SUCCESS', 'message': '训练任务已启动'}
```

#### 4.2.4 训练进度监控

**进度监控线程**:

```python
def _start_progress_monitor(self, job_id):
    """启动进度监控线程"""

    def monitor():
        stop_event = threading.Event()
        self.progress_stop_events[job_id] = stop_event

        while not stop_event.is_set():
            # 读取results.csv获取训练进度
            results_csv = self.config.get_output_path(job_id) / 'train' / 'results.csv'
            if results_csv.exists():
                df = pd.read_csv(results_csv)
                if not df.empty:
                    latest = df.iloc[-1]
                    current_epoch = int(latest.get('epoch', 0))
                    train_loss = float(latest.get('train/box_loss', 0))
                    val_loss = float(latest.get('val/box_loss', 0))
                    progress = current_epoch / epochs

                    # 回调后端: 更新训练进度
                    self._notify_training_progress(job_id, current_epoch, progress, train_loss, val_loss)

            # 等待5秒
            stop_event.wait(5)

    thread = threading.Thread(target=monitor)
    thread.daemon = True
    thread.start()
```

**后端回调接口**:

```java
// TrainingController.java

@PostMapping("/internal/{job_id}/progress")
public ResponseEntity<ApiResponse<Void>> updateProgress(
    @PathVariable("job_id") String jobId,
    @RequestParam int current_epoch,
    @RequestParam float progress,
    @RequestParam(required = false) Float train_loss,
    @RequestParam(required = false) Float val_loss
) {
    trainingService.updateTrainingProgress(jobId, current_epoch, progress, train_loss, val_loss);
    return ResponseEntity.ok(ApiResponse.success(null));
}
```

#### 4.2.5 训练完成处理

**训练完成回调**:

```java
// TrainingController.java

@PostMapping("/internal/{job_id}/complete")
public ResponseEntity<ApiResponse<Void>> completeTraining(
    @PathVariable("job_id") String jobId,
    @RequestParam String output_model_id,
    @RequestParam float final_map,
    @RequestParam float final_map50,
    @RequestParam float final_loss,
    @RequestParam int best_epoch
) {
    trainingService.completeTraining(jobId, output_model_id, final_map, final_map50, final_loss, best_epoch);
    return ResponseEntity.ok(ApiResponse.success(null));
}
```

**后端处理逻辑**:

```java
@Transactional
public void completeTraining(String jobId, String outputModelId, float finalMap,
                            float finalMap50, float finalLoss, int bestEpoch) {
    // 1. 更新训练任务状态
    TrainingJob job = trainingJobRepository.findById(jobId)
            .orElseThrow(() -> new RuntimeException("训练任务不存在"));
    job.setStatus(TrainingStatus.COMPLETED);
    job.setProgress(1.0f);
    job.setFinalMap(finalMap);
    job.setFinalLoss(finalLoss);
    job.setBestEpoch(bestEpoch);
    job.setCompletedAt(LocalDateTime.now());
    trainingJobRepository.save(job);

    // 2. 创建模型记录 (如果需要)
    if (outputModelId == null) {
        ModelCreateRequest modelRequest = new ModelCreateRequest();
        modelRequest.setModelName(job.getJobName() + "_model");
        modelRequest.setModelType(Model.ModelType.DETECTION);
        modelRequest.setFramework("YOLOv8");
        modelRequest.setVersion("1.0");
        modelRequest.setDatasetId(job.getDatasetId());

        ModelDTO model = modelService.createModel(modelRequest);
        outputModelId = model.getModelId();

        // 关联模型到训练任务
        job.setOutputModelId(outputModelId);
        trainingJobRepository.save(job);
    }

    // 3. 复制训练输出到模型存储
    Path trainOutput = Paths.get(trainingService.getOutputPath(jobId), "train", "weights");
    Path modelStorage = Paths.get(modelStoragePrefix, outputModelId);

    Files.createDirectories(modelStorage);
    Files.copy(trainOutput.resolve("best.pt"), modelStorage.resolve("best.pt"));
    Files.copy(trainOutput.resolve("last.pt"), modelStorage.resolve("last.pt"));

    // 4. 更新模型记录
    Model model = modelRepository.findById(outputModelId).get();
    model.setPtFilePath(modelStorage.resolve("best.pt").toString());
    model.setMap(finalMap);
    model.setMap50(finalMap50);
    model.setStatus(Model.ModelStatus.READY);
    modelRepository.save(model);
}
```

#### 4.2.6 模型转换

**转换流程**:

```
PyTorch (.pt) → ONNX (.onnx) → TensorRT Engine (.engine)
```

**代码** (`converter.py`):

```python
class ModelConverter:
    def convert_to_onnx(self, pt_path, onnx_path, img_size=640):
        """将PyTorch模型转换为ONNX"""

        model = YOLO(pt_path)
        model.export(format='onnx', imgsz=img_size, simplify=True)

        # 移动ONNX文件到目标路径
        shutil.move(str(pt_path.parent / 'best.onnx'), str(onnx_path))

        return onnx_path

    def convert_to_tensorrt(self, onnx_path, engine_path, precision='fp16'):
        """将ONNX模型转换为TensorRT Engine"""

        import tensorrt as trt

        # 创建TensorRT构建器
        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(TRT_LOGGER)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, TRT_LOGGER)

        # 解析ONNX模型
        with open(onnx_path, 'rb') as model:
            parser.parse(model.read())

        # 配置精度
        config = builder.create_builder_config()
        if precision == 'fp16':
            config.set_flag(trt.BuilderFlag.FP16)
        elif precision == 'int8':
            config.set_flag(trt.BuilderFlag.INT8)

        # 构建引擎
        serialized_engine = builder.build_serialized_network(network, config)

        # 保存引擎
        with open(engine_path, 'wb') as f:
            f.write(serialized_engine)

        return engine_path
```

**后端调用**:

```java
// ModelService.java

public ModelDTO convertModel(String modelId, ConversionTask.ConversionType conversionType) {
    Model model = modelRepository.findById(modelId)
            .orElseThrow(() -> new RuntimeException("模型不存在"));

    // 创建转换任务
    ConversionTask task = new ConversionTask();
    task.setTaskId("CONV" + System.currentTimeMillis());
    task.setModelId(modelId);
    task.setConversionType(conversionType);
    task.setStatus(ConversionTask.ConversionStatus.PENDING);
    conversionTaskRepository.save(task);

    // 调用训练服务执行转换
    String convertUrl = trainingServiceUrl + "/convert";
    Map<String, Object> requestBody = new HashMap<>();
    requestBody.put("task_id", task.getTaskId());
    requestBody.put("pt_path", model.getPtFilePath());
    requestBody.put("conversion_type", conversionType.toString());

    restTemplate.postForEntity(convertUrl, requestBody, Map.class);

    return toDTO(model);
}
```

### 4.3 训练参数配置

**支持的训练参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `epochs` | int | 100 | 训练轮次 |
| `batch_size` | int | 16 | 批次大小 |
| `img_size` | int | 640 | 输入图像大小 |
| `use_gpu` | boolean | true | 是否使用GPU |
| `base_model` | string | "yolov8n.pt" | 预训练模型 |
| `optimizer` | string | "AdamW" | 优化器 |
| `lr0` | float | 0.01 | 初始学习率 |
| `weight_decay` | float | 0.0005 | 权重衰减 |
| `workers` | int | 8 | 数据加载线程数 |
| `warmup_epochs` | int | 3 | 预热轮次 |
| `save_period` | int | 10 | 保存间隔 (epoch) |
| `mosaic` | float | 1.0 | Mosaic数据增强概率 |
| `mixup` | float | 0.0 | Mixup数据增强概率 |

**续训参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `resume` | boolean | 是否继续之前的训练 |
| `resume_job_id` | string | 要继续的任务ID |
| `enable_smart_optimization` | boolean | 是否启用智能参数优化 |

### 4.4 训练指标

**YOLOv8训练指标**:

| 指标 | 名称 | 说明 |
|------|------|------|
| `train/box_loss` | 边界框损失 | 训练集 |
| `train/cls_loss` | 分类损失 | 训练集 |
| `train/dfl_loss` | 分布聚焦损失 | 训练集 |
| `val/box_loss` | 边界框损失 | 验证集 |
| `val/cls_loss` | 分类损失 | 验证集 |
| `val/dfl_loss` | 分布聚焦损失 | 验证集 |
| `metrics/precision(B)` | 精确率 | 验证集 |
| `metrics/recall(B)` | 召回率 | 验证集 |
| `metrics/mAP50(B)` | mAP@0.5 | 验证集 |
| `metrics/mAP50-95(B)` | mAP@0.5:0.95 | 验证集 |

**指标存储**: TimescaleDB超表 `training_metrics`

```sql
CREATE TABLE training_metrics (
    metric_id BIGSERIAL,
    job_id VARCHAR(50),
    epoch INT,
    metric_name VARCHAR(50),
    metric_value FLOAT,
    timestamp TIMESTAMP,
    PRIMARY KEY (metric_id)
);

-- 转换为超表 (支持时间分区)
SELECT create_hypertable('training_metrics', 'timestamp');
```

### 4.5 MLflow实验追踪

**实验追踪配置**:

```python
# config.py
class TrainingConfig:
    mlflow_tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5001')
```

**记录指标**:

```python
mlflow.set_tracking_uri(config.mlflow_tracking_uri)
mlflow.start_run(run_name=job_id)

mlflow.log_params({
    'epochs': epochs,
    'batch_size': batch_size,
    'img_size': img_size,
    'base_model': base_model,
})

mlflow.log_metrics({
    'final_map': final_map,
    'final_loss': final_loss,
    'best_epoch': best_epoch
})

mlflow.log_artifact(str(output_path / 'train' / 'weights' / 'best.pt'))

mlflow.end_run()
```

---

## 五、云端推理服务 (C-RADIOv4 — 插件化)

### 5.1 概述

`models/cloud_inference/radio_infer_server.py` 是基于 C-RADIOv4 的云端统一推理服务。采用**插件化架构**，告警规则从 YAML 配置动态读取，新增场景无需修改代码。

**核心文件**：

| 文件 | 职责 |
|------|------|
| `radio_infer_server.py` | 服务主入口 — MQTT/RTMP 模式管理 |
| `plugin_base.py` | 插件基类 — 从 YAML `cloud.radio.classes.*.alert` 动态读取告警规则 |
| `engine.py` | 推理引擎 — 模型加载、推理、标注绘制、告警生成 |

### 5.2 架构

```
边缘设备 → MQTT(device/+/cloud/frame) → radio_infer_server.py
                                              ↓
                                         ScenarioPlugin (读取 YAML 告警规则)
                                              ↓
                                         InferenceEngine → C-RADIOv4-H 零样本分割
                                              ↓
                                         plugin.generate_alerts() → YAML 驱动告警
                                              ↓
                                    HTTP POST → backend:8080 推理结果上报
                                              ↓
                                    MQTT(device/{id}/cloud/result) → EMQX 规则引擎
                                              ↓
                                    results/{id}/{ch}/cloud + alerts/{id}/cloud (统一 topic)
```

### 5.3 推理流程

1. **帧接收**：通过 MQTT 订阅 `device/+/cloud/frame` 接收边缘设备转发的 JPEG 原始帧（Base64 编码）
2. **预处理**：解码 JPEG → resize 到 378×378 → 归一化
3. **C-RADIOv4 推理**：通过 SigLIP2-g 特征提取器生成图像特征，与预定义的类别文本提示进行相似度匹配
4. **类别匹配**：支持多种语义分割类别（如 `bare_soil_uncovered`、`dust_pollution` 等），通过配置文件定义
5. **告警生成**：**插件化** — 从 YAML 的 `cloud.radio.classes.*.alert` 字段动态读取规则，不再硬编码
6. **结果上报**：通过 HTTP POST 将推理结果和可视化图像上传到后端

### 5.4 配置

通过 YAML 配置文件定义分割类别和告警规则，新增场景只需创建 YAML，无需改代码：

```yaml
# models/{scenario}/configs/{scenario}.yaml
cloud:
  radio:
    classes:
      bare_soil_uncovered:
        zh: "裸土未覆盖"
        prompts:
          - exposed bare soil without any covering material
        alert:
          enabled: true
          level: warning
          description: "裸土未覆盖"
    inference:
      threshold: 0.25
      min_area: 0.003
```

**新场景接入流程**：
1. 创建 `models/{scenario}/configs/{scenario}.yaml`（含 classes + alert 字段）
2. 启动命令加 `--config` 指定新 YAML
3. 不需要修改任何 Python 代码

### 5.5 可视化

推理结果可视化包含：
- 分割区域彩色叠加
- 自适应字体大小的标签（`max(24, min(w,h)//25)`）
- 边界检查确保标签不超出图像范围
- 标签背景 padding 增大（10px），防止文字截断

### 5.6 性能

| 指标 | 值 |
|------|-----|
| 首帧推理 | ~1900ms（模型预热） |
| 稳态推理 | ~900-960ms |
| 模型参数量 | 1412.4M (C-RADIOv4-H + SigLIP2-g) |
| 设备 | CUDA GPU |

### 5.7 部署

```bash
# 在 Docker 容器中启动（前台，支持 Ctrl+C 终止）
docker exec -it edge_cloud_training python3 /app/models/cloud_inference/radio_infer_server.py \
  --config /app/models/construction_safety/configs/construction_safety.yaml \
  --checkpoint /app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar \
  --radio-code /app/models/NVlabs_RADIO \
  --siglip2 /app/models/siglip2-giant-opt-patch16-384

# 或后台运行
docker exec -d edge_cloud_training bash -c \
  "python3 /app/models/cloud_inference/radio_infer_server.py \
  --config /app/models/water_inspection/configs/water_inspection.yaml \
  --checkpoint /app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar \
  --radio-code /app/models/NVlabs_RADIO \
  --siglip2 /app/models/siglip2-giant-opt-patch16-384 \
  >> /tmp/cloud_infer.log 2>&1"
```

---

## 七、算法模型目录

### 7.1 模型目录结构

```
models/
├── rcmt/              # RCMT V2.0 (变化检测)
│   ├── __init__.py
│   ├── model.py      # 模型定义
│   ├── train.py      # 训练脚本
│   ├── inference.py  # 推理脚本
│   ├── dataset_manager.py  # 数据集管理
│   ├── configs/
│   │   └── rcmt_config.json  # 训练配置
│   └── README.md     # 使用文档
└── rcmt_v3/          # RCMT V3.0 (变化检测)
    ├── __init__.py
    ├── inference.py  # 推理引擎
    ├── service.py    # 推理服务
    ├── quick_start.py  # 快速开始
    ├── configs/
    │   ├── rcmt_v3_swin.yaml  # Swin-Temporal配置
    │   └── rcmt_v3_optimized.yaml  # Optimized配置
    ├── weights/
    │   └── best_model.pth  # 最佳模型权重
    └── README.md     # 使用文档
```

### 7.2 RCMT (Recurrent Cross-Memory Transformer) V2.0

**用途**: 卫星图像变化检测

**架构**:
- 主干: SAM2 / DINOv2 / CLIP (多主干支持)
- 融合: Concat / Add / Attention
- 编码器: Transformer / LSTM / GRU
- 任务: 变化检测 + 分割 + 属性识别

**主要模块**:

| 模块 | 文件 | 功能 |
|------|------|------|
| 模型定义 | `model.py` | RCMT模型架构 |
| 训练 | `train.py` | 训练循环、模型保存、导出 |
| 推理 | `inference.py` | 单图/批量推理、可视化 |
| 数据管理 | `dataset_manager.py` | 数据集下载、划分、伪标签生成 |

**训练配置** (`configs/rcmt_config.json`):

```json
{
  "model": {
    "backbone_type": "dinov2",
    "fusion_type": "attention",
    "embed_dim": 768,
    "depth": 12,
    "num_heads": 12
  },
  "data": {
    "data_dir": "./datasets",
    "split": {
      "train_ratio": 0.7,
      "val_ratio": 0.2,
      "test_ratio": 0.1
    }
  },
  "training": {
    "batch_size": 2,
    "num_epochs": 100,
    "learning_rate": 1e-4,
    "weight_decay": 1e-4,
    "optimizer": "adamw",
    "scheduler": "cosine",
    "use_amp": true
  }
}
```

### 7.3 RCMT V3.0

**用途**: 高性能变化检测

**版本**:

| 版本 | 架构 | 参数量 | 最佳F1 | 最佳IoU |
|------|------|--------|--------|---------|
| Swin-Temporal | Swin Transformer + 时序融合 | 58.7M | 0.8931 | 0.8068 |
| Optimized | 混合 CNN-Transformer | ~30M | 0.8909 | 0.8033 |

**推理引擎** (`inference.py`):

```python
class InferenceEngine:
    def __init__(self, config_path, device="cuda"):
        self.config = self._load_config(config_path)
        self.model = self._load_model()
        self.device = torch.device(device)

    def infer_pair(self, image_t1, image_t2):
        """推理图像对"""

        # 预处理
        tensor_t1 = self._preprocess(image_t1)
        tensor_t2 = self._preprocess(image_t2)

        # 拼接输入
        input_tensor = torch.cat([tensor_t1, tensor_t2], dim=0).unsqueeze(0)

        # 推理
        with torch.no_grad():
            if self.config['inference']['use_amp']:
                with torch.cuda.amp.autocast():
                    output = self.model(input_tensor.to(self.device))
            else:
                output = self.model(input_tensor.to(self.device))

        # 后处理
        mask = self._postprocess(output)

        return {
            'mask': mask,
            'prob': output.squeeze().cpu().numpy(),
            'inference_time': elapsed_time
        }
```

**配置文件** (`configs/rcmt_v3_swin.yaml`):

```yaml
model:
  name: "rcmt_v3_swin_temporal"
  architecture:
    swin:
      embed_dim: 96
      depths: [2, 2, 2, 2]
      num_heads: [2, 4, 8, 16]
      window_size: 7
  weights:
    best: "checkpoints_swin_final/best_model.pth"

input:
  img_size: 256
  in_channels: 3
  mean: [0.485, 0.456, 0.406]
  std: [0.229, 0.224, 0.225]

inference:
  batch_size: 1
  use_amp: true
  threshold: 0.5
```

---

## 八、总结

### 8.1 架构特点

1. **微服务架构**:
   - 后端Spring Boot + 训练服务Flask 独立部署
   - 通过REST API通讯

2. **多层通讯机制**:
   - HTTP REST: 前端↔后端、边缘设备↔后端
   - MQTT: 边缘设备↔后端 (实时、离线消息支持)
   - WebSocket: 后端↔前端 (实时推送)

3. **完整的生命周期管理**:
   - 数据集管理 → 模型训练 → 模型转换 → 模型部署 → OTA升级

4. **云边协同**:
   - 云端: 训练、模型管理、任务调度
   - 边缘: 推理、状态上报、OTA接收

### 8.2 技术亮点

1. **智能训练优化**:
   - 续训支持
   - 智能参数优化
   - MLflow实验追踪

2. **灵活的数据集管理**:
   - 支持后端上传、URL、本地路径三种来源
   - 数据集验证

3. **完整的OTA机制**:
   - 支持模型升级、配置升级、固件升级
   - 支持回滚、重试
   - 渐进式发布

4. **高效的模型转换**:
   - PyTorch → ONNX → TensorRT
   - 支持FP16/INT8量化
   - 提升推理性能

### 8.3 扩展性

1. **水平扩展**:
   - 训练服务可多实例部署
   - 支持负载均衡

2. **插件化**:
   - 新增模型类型只需添加对应Service和Controller
   - 支持自定义训练框架

3. **存储扩展**:
   - 本地文件系统 / S3 / MinIO

---

**文档版本**: 1.0
**生成日期**: 2026-03-06
**作者**: SkyEdge AI Team
