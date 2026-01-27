# 代码模板库使用指南

## 概述

edge_infer_cloud 代码模板库提供了可复用的代码模板和自动化代码生成工具，参考 YOLOv8 设计理念，帮助团队快速开发。

---

## 目录结构

```
templates/
├── frontend/           # 前端 Vue3 模板
├── backend/            # 后端 Spring Boot 模板
├── training/           # 训练 Python 模板
├── edge-agent/         # 边缘 Go 模板
└── configs/            # 配置文件模板
```

---

## 快速开始

### 1. 使用代码生成器创建 CRUD

```bash
# 生成设备管理代码
python scripts/generate-crud.py \
  --name Device \
  --resource device \
  --fields "name,type,ipAddress,status"

# 输出文件:
# backend/src/main/java/com/edge/cloud/entity/Device.java
# backend/src/main/java/com/edge/cloud/repository/DeviceRepository.java
# backend/src/main/java/com/edge/cloud/service/DeviceService.java
# backend/src/main/java/com/edge/cloud/controller/DeviceController.java
# frontend/src/views/device/List.vue
```

### 2. 使用训练模板

```bash
# 复制配置模板
cp templates/configs/train.yaml training/configs/
cp templates/configs/data.yaml training/configs/

# 修改后开始训练
python training/edge_train/cli.py train \
  --data training/configs/data.yaml \
  --model yolov8n.pt \
  --epochs 100
```

---

## 模板详解

### 训练模块模板（参考 YOLOv8）

#### CLI 命令格式

```bash
# 训练
edge-train train --data data.yaml --model yolov8n.pt --epochs 100 --batch 16

# 验证
edge-train val --model best.pt --data data.yaml

# 预测
edge-train predict --model best.pt --source images/ --conf 0.25

# 导出
edge-train export --model best.pt --format onnx
```

#### 数据集配置模板

```yaml
path: ../datasets/my_dataset
train: images/train
val: images/val

names:
  0: person
  1: car
nc: 2

augmentation:
  hsv_h: 0.015
  fliplr: 0.5
  mosaic: 1.0
```

---

### 后端模板

#### CRUD 模板组成

1. **Entity** - 数据库实体
2. **Repository** - 数据访问层
3. **Service** - 业务逻辑层
4. **Controller** - REST API 层

#### 使用代码生成器

```bash
python scripts/generate-crud.py \
  --name TrainingTask \
  --resource training-task \
  --fields "datasetId,config,status,progress,metrics"
```

---

### 前端模板

#### 列表页面模板

包含：
- 搜索栏
- 数据表格
- 分页组件
- 操作按钮

#### 扩展模板

```vue
<!-- 在 List.vue 基础上添加 -->
<el-table-column prop="customField" label="自定义字段" />
```

---

### 边缘代理模板

#### MQTT 客户端使用

```go
import "edge-infer-cloud/edge-agent/internal/mqtt"

client := mqtt.NewClient(
    "tcp://localhost:1883",
    "device-001",
    "username",
    "password",
)

client.Connect()
client.Subscribe("devices/+/status", 0, messageHandler)
```

---

## 代码生成器详细用法

### generate-crud.py 参数

| 参数 | 说明 | 示例 |
|------|------|------|
| --name | 实体名称 | Device, TrainingTask |
| --resource | 资源名称（URL路径） | device, training-task |
| --fields | 字段列表（逗号分隔） | name,status,createdAt |

### 示例

```bash
# 1. 设备管理
python scripts/generate-crud.py \
  --name Device \
  --resource device \
  --fields "name,type,ipAddress,status"

# 2. 训练任务
python scripts/generate-crud.py \
  --name TrainingTask \
  --resource training-task \
  --fields "datasetId,config,status,progress"

# 3. 数据集管理
python scripts/generate-crud.py \
  --name Dataset \
  --resource dataset \
  --fields "name,type,dataYamlPath,status,sampleCount"
```

---

## 开发工作流

### 添加新功能

1. **规划数据模型** → 定义字段
2. **运行代码生成器** → 生成基础代码
3. **自定义业务逻辑** → 在 Service 层添加
4. **自定义前端交互** → 在 Vue 组件中添加
5. **测试验证** → 编译运行

### 示例：添加设备监控功能

```bash
# 1. 生成 DeviceMetrics CRUD
python scripts/generate-crud.py \
  --name DeviceMetrics \
  --resource device-metrics \
  --fields "deviceId,cpuUsage,memoryUsage,gpuUsage,timestamp"

# 2. 在 DeviceService 中添加监控逻辑
# 3. 在前端添加图表展示
# 4. 配置 MQTT 订阅实时数据
```

---

## 常见问题

### Q: 如何添加自定义字段？

手动修改生成的 Entity 文件，添加自定义字段和注解。

### Q: 如何添加验证规则？

在 DTO 文件中添加 `@NotNull`, `@Size` 等验证注解。

### Q: 如何修改模板？

直接编辑 `templates/` 目录下的模板文件，所有新生成的代码都会使用新模板。

---

## 下一步

- [API 文档](../api/README.md)
- [开发规范](conventions.md)
