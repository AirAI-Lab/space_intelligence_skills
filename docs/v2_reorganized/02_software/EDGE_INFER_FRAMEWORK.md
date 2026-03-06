# 软件开发指南

> **负责模块**: 边缘AI推理框架、云边协同平台
> **代码仓库**: `edge_infer`, `edge_infer_cloud`

---

## 1. 边缘AI推理框架 (`edge_infer`)

### 1.1 架构概览

```
┌────────────────────────────────────────────────────────────┐
│                    边缘推理框架                             │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ PluginManager │  │ InferenceEngine│  │ Communicator │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│  ┌────────────────────────────────────────────────────┐   │
│  │              插件系统 (21个插件)                     │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐             │   │
│  │  │YOLOv8   │ │  RCMT   │ │SegFormer│ ...         │   │
│  │  │检测插件  │ │变化检测 │ │分割插件  │             │   │
│  │  └─────────┘ └─────────┘ └─────────┘             │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件

| 组件 | 路径 | 说明 |
|------|------|------|
| **PluginManager** | `src/plugin_manager/` | 插件加载、生命周期管理 |
| **Core** | `src/core/` | 核心接口定义 |
| **Plugins** | `src/plugins/` | 21个AI推理插件 |
| **Utils** | `src/utils/` | 工具函数 |
| **MQTT** | `src/mqtt/` | 云边通讯 |

### 1.3 插件开发规范

每个插件必须实现以下接口：

```cpp
// include/plugin/base_plugin.h
class BasePlugin {
public:
    virtual ~BasePlugin() = default;
    
    // 插件信息
    virtual std::string name() const = 0;
    virtual std::string version() const = 0;
    
    // 生命周期
    virtual bool init(const Config& config) = 0;
    virtual bool start() = 0;
    virtual bool stop() = 0;
    virtual bool release() = 0;
    
    // 推理
    virtual Result infer(const Input& input) = 0;
};
```

### 1.4 现有插件列表

| 插件类型 | 插件名称 | 模型 |
|----------|----------|------|
| 目标检测 | `object_detection` | YOLOv8 |
| 目标检测 | `person_detection` | YOLOv8-person |
| 目标检测 | `vehicle_detection` | YOLOv8-vehicle |
| 目标检测 | `face_detection` | RetinaFace |
| 变化检测 | `change_detection` | **RCMT** |
| 语义分割 | `semantic_seg` | SegFormer |
| 实例分割 | `instance_seg` | YOLOv8-seg |
| 目标跟踪 | `mot_tracking` | DeepSORT |
| 姿态估计 | `pose_estimation` | YOLOv8-pose |
| 异常检测 | `anomaly_detection` | AutoEncoder |
| 计数 | `counting` | YOLOv8 + 跟踪 |
| 文字识别 | `text_ocr` | PaddleOCR |
| ... | ... | ... |

---

## 2. 云边协同平台 (`edge_infer_cloud`)

### 2.1 后端架构 (Spring Boot)

```
backend/src/main/java/
├── controller/       # REST API
│   ├── DeviceController.java
│   ├── ModelController.java
│   ├── TrainingController.java
│   └── ...
├── service/          # 业务逻辑
├── repository/       # 数据访问
├── entity/           # 实体类
├── config/           # 配置
└── util/             # 工具类
```

### 2.2 前端架构 (Vue3)

```
frontend/src/
├── views/            # 页面
│   ├── DeviceManagement.vue
│   ├── ModelManagement.vue
│   ├── TrainingMonitor.vue
│   └── ...
├── components/       # 组件
├── api/              # API调用
├── stores/           # Pinia状态管理
├── router/           # 路由
└── utils/            # 工具函数
```

### 2.3 核心功能模块

| 模块 | 说明 | 状态 |
|------|------|------|
| **设备管理** | 设备注册、状态监控、OTA升级 | ✅ |
| **模型管理** | 模型上传、版本管理、分发 | ✅ |
| **训练服务** | 在线训练、参数配置、日志 | ✅ |
| **数据管理** | 数据集上传、标注、预处理 | ✅ |
| **任务管理** | 推理任务、调度、结果 | ✅ |

---

## 3. 开发任务清单

### 3.1 高优先级

- [ ] 插件热加载优化
- [ ] 推理性能优化 (TensorRT)
- [ ] 云边通讯稳定性
- [ ] 前端UI优化

### 3.2 中优先级

- [ ] 多模型并行推理
- [ ] 边缘设备资源监控
- [ ] 训练任务队列
- [ ] 数据增强Pipeline

### 3.3 低优先级

- [ ] 插件市场
- [ ] 可视化调试工具
- [ ] 自动化测试覆盖

---

## 4. 调用此代理

使用 `@delegate` 命令：

```
@delegate 软件开发代理: 请检查edge_infer的插件加载逻辑
@delegate 软件开发代理: 优化后端的模型下载接口
@delegate 软件开发代理: 前端添加训练进度可视化
```

---

**相关文档**:
- [插件开发指南](./PLUGIN_DEVELOPMENT.md)
- [云边协同平台](./CLOUD_PLATFORM.md)
- [系统总览](../01_architecture/OVERVIEW.md)
