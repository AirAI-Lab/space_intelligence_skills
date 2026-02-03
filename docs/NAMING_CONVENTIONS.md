# edge_infer_cloud 命名规范

## 概述

本文档定义了 edge_infer_cloud 云边协同平台的统一命名规范，确保跨语言、跨平台开发的一致性。

## 总体原则

**采用 camelCase 作为主要的命名规范**，因为：
1. JSON/JavaScript 生态系统使用 camelCase
2. Java 生态系统使用 camelCase
3. 这是 REST API 的行业最佳实践

## 分层规范

### 1. API 层（JSON 序列化）

**规范：camelCase**

```json
{
  "modelId": "model_001",
  "modelName": "YOLOv8n",
  "datasetId": "dataset_001",
  "datasetName": "安全帽检测",
  "createdAt": "2024-01-01T00:00:00Z"
}
```

### 2. 前端层（Vue/TypeScript）

**规范：camelCase**

```typescript
// ✅ 正确
interface Model {
  modelId: string
  modelName: string
  createdAt: string
}

// ❌ 错误
interface Model {
  model_id: string    // 不要使用 snake_case
  model_name: string
  created_at: string
}
```

**组件属性绑定：**
```vue
<!-- ✅ 正确 -->
<el-table-column prop="modelId" label="模型ID" />
<el-table-column prop="modelName" label="模型名称" />

<!-- ❌ 错误 -->
<el-table-column prop="model_id" label="模型ID" />
```

### 3. 后端层（Java）

**Entity 和 DTO 字段：camelCase**

```java
@Entity
@Table(name = "models")
public class Model {

    @Column(name = "model_id")      // 数据库列名用 snake_case
    private String modelId;          // Java 字段用 camelCase ✅

    @Column(name = "model_name")
    private String modelName;        // ✅

    @Column(name = "created_at")
    private LocalDateTime createdAt; // ✅
}
```

**DTO 返回：**
```java
@Data
public class ModelDTO {
    private String modelId;      // ✅ camelCase
    private String modelName;    // ✅
    private LocalDateTime createdAt; // ✅
}
```

### 4. 数据库层（PostgreSQL）

**规范：snake_case**

```sql
CREATE TABLE models (
    model_id VARCHAR(50) PRIMARY KEY,
    model_name VARCHAR(200) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 5. URL 层

**规范：kebab-case**

```
GET  /api/v1/models/{modelId}
POST /api/v1/training-jobs
GET  /api/v1/datasets/{datasetId}
```

## 术语对照表

| 中文 | 英文 | camelCase | snake_case | 备注 |
|------|------|-----------|------------|------|
| 模型ID | Model ID | modelId | model_id | - |
| 模型名称 | Model Name | modelName | model_name | - |
| 数据集ID | Dataset ID | datasetId | dataset_id | - |
| 数据集名称 | Dataset Name | datasetName | dataset_name | - |
| 设备ID | Device ID | deviceId | device_id | - |
| 设备名称 | Device Name | deviceName | device_name | - |
| 任务ID | Job ID | jobId | job_id | - |
| 任务名称 | Job Name | jobName | job_name | - |
| 创建时间 | Created At | createdAt | created_at | - |
| 更新时间 | Updated At | updatedAt | updated_at | - |
| 文件大小 | File Size | fileSize | file_size | - |
| 文件路径 | File Path | filePath | file_path | - |
| 训练轮次 | Current Epoch | currentEpoch | current_epoch | - |
| 总轮次 | Total Epochs | totalEpochs | total_epochs | - |
| 批次大小 | Batch Size | batchSize | batch_size | - |
| 图像大小 | Image Size | imgSize | img_size | - |

## Jackson 配置（Spring Boot 后端）

默认配置已正确，无需修改：

```yaml
# application.yml
spring:
  jackson:
    property-naming-strategy: LOWER_CAMEL_CASE  # 默认值，可省略
```

## 迁移检查清单

### 前端文件需要修改
- [ ] `src/api/index.ts` - API 定义
- [ ] `src/api/model.ts` - 模型 API
- [ ] `src/api/ota.ts` - OTA API
- [ ] `src/views/Home.vue` - 首页
- [ ] `src/views/ota/OtaTask.vue` - OTA 任务
- [ ] 其他使用 snake_case 的文件

### 后端无需修改
- Entity 和 DTO 已正确使用 camelCase
- Jackson 序列化默认配置正确
- @Column 注解正确使用 snake_case

## 代码审查要点

### PR 检查时注意：
1. 前端 API 调用参数是否使用 camelCase
2. 前端 interface 定义是否使用 camelCase
3. 模板绑定是否使用 camelCase 属性
4. 后端 DTO 是否使用 camelCase
5. 数据库 @Column 是否使用 snake_case

## 示例：完整的数据流

```typescript
// 前端 - TypeScript interface
interface Dataset {
  datasetId: string      // ✅ camelCase
  datasetName: string    // ✅
  createdAt: string      // ✅
}

// 前端 - API 调用
await dataApi.getList({ page: 1, page_size: 100 })  // URL 参数保持原样
```

```json
// JSON 响应
{
  "datasetId": "ds_001",     // ✅ camelCase
  "datasetName": "我的数据集", // ✅
  "createdAt": "2024-01-01"   // ✅
}
```

```java
// 后端 - DTO
@Data
public class DatasetDTO {
    private String datasetId;      // ✅ camelCase
    private String datasetName;    // ✅
    private LocalDateTime createdAt; // ✅
}
```

```sql
-- 数据库
CREATE TABLE datasets (
    dataset_id VARCHAR(50),     -- ✅ snake_case
    dataset_name VARCHAR(200),   -- ✅
    created_at TIMESTAMP        -- ✅
);
```

## 参考资料

- [JSON Style Guide](https://google.github.io/styleguide/jsoncstyleguide.xml) - Google JSON 规范
- [Spring Boot Jackson Documentation](https://docs.spring.io/spring-boot/docs/current/reference/html/web.html#web.servlet.spring-mvc.jackson)
- [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript) - JavaScript 命名规范
