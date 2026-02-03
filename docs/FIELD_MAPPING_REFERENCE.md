# 字段映射参考文档

本文档提供完整的字段名称映射关系（数据库 → 后端 → 前端），防止命名不一致问题。

## 概述

本项目在各层之间遵循严格的命名约定：
- **数据库**: `snake_case`（全小写，下划线分隔）
- **Java 后端**: `camelCase`，使用 `@Column` 注解显式映射
- **前端 TypeScript**: `camelCase`，与 Java DTO 字段名完全一致

## 训练模块

### TrainingJob 实体/DTO

| 数据库列名 | Java 实体/DTO 字段 | 前端字段 | 说明 |
|----------------|----------------------|----------------|-------|
| job_id | jobId | jobId | 主键 |
| job_name | jobName | jobName | - |
| dataset_id | datasetId | datasetId | - |
| dataset_source | datasetSource | datasetSource | 值: backend, url, local |
| dataset_url | datasetUrl | datasetUrl | 可选的 URL 数据源 |
| dataset_path | datasetPath | datasetPath | 本地文件系统路径 |
| dataset_name | datasetName | datasetName | 显示名称 |
| base_model_id | baseModelId | baseModelId | 可选 - 用于微调 |
| base_model | baseModel | baseModel | 预训练模型名称（如 yolov8n.pt） |
| output_model_id | outputModelId | outputModelId | 训练完成后生成 |
| epochs | epochs | epochs | **不是 totalEpochs** |
| batch_size | batchSize | batchSize | - |
| img_size | imgSize | imgSize | - |
| use_gpu | useGpu | useGpu | 布尔值 |
| training_type | trainingType | trainingType | 枚举: FULL_TRAINING, FINE_TUNING |
| hyperparameters | hyperparameters | hyperparameters | JSON 对象 |
| status | status | status | **枚举值必须大写**: PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED |
| current_epoch | currentEpoch | currentEpoch | - |
| progress | progress | progress | **浮点数 0-1，显示时需乘以 100** |
| final_map | finalMap | finalMap | **不是 map** |
| final_loss | finalLoss | finalLoss | **不是 loss** |
| best_epoch | bestEpoch | bestEpoch | - |
| mlflow_run_id | mlflowRunId | mlflowRunId | MLflow 跟踪 ID |
| started_at | startedAt | startedAt | LocalDateTime |
| completed_at | completedAt | completedAt | LocalDateTime |
| created_at | createdAt | createdAt | LocalDateTime |
| updated_at | updatedAt | updatedAt | LocalDateTime |

### 关联实体的额外 DTO 字段

| 字段 | 来源 | 说明 |
|-------|--------|-------|
| baseModelName | Model.modelName | 来自基础模型关联 |
| outputModelName | Model.modelName | 来自输出模型关联 |

## 模型模块

### Model 实体/DTO

| 数据库列名 | Java 实体/DTO 字段 | 前端字段 | 说明 |
|----------------|----------------------|----------------|-------|
| model_id | modelId | modelId | 主键 |
| model_name | modelName | modelName | - |
| model_type | modelType | modelType | 枚举: DETECTION, CLASSIFICATION, etc. |
| framework | framework | framework | PyTorch, ONNX, TensorFlow |
| version | version | version | - |
| parent_model_id | parentModelId | parentModelId | 可选 - 用于微调的父模型 |
| dataset_id | datasetId | datasetId | 可选 - 训练使用的数据集 |
| pt_file_path | ptFilePath | ptFilePath | PyTorch 模型文件路径 |
| onnx_file_path | onnxFilePath | onnxFilePath | ONNX 模型文件路径 |
| engine_file_path | engineFilePath | engineFilePath | TensorRT 引擎文件路径 |
| map | map | map | **注意：这对 Model 实体是正确的**（不同于 TrainingJob 的 finalMap） |
| precision | precision | precision | 浮点数 0-1 |
| recall | recall | recall | 浮点数 0-1 |
| inference_time_ms | inferenceTimeMs | inferenceTimeMs | 毫秒 |
| input_width | inputWidth | inputWidth | 图像输入宽度 |
| input_height | inputHeight | inputHeight | 图像输入高度 |
| class_names | classNames | classNames | 类标签数组 |
| status | status | status | **枚举值必须大写**: READY, TRAINING, CONVERTING, DEPLOYED, ARCHIVED, ERROR |
| file_size_bytes | fileSizeBytes | fileSizeBytes | 文件大小（字节） |
| deployed_count | deployedCount | deployedCount | 已部署设备数量 |
| created_at | createdAt | createdAt | LocalDateTime |
| updated_at | updatedAt | updatedAt | LocalDateTime |

### 重要说明：Model vs TrainingJob 字段名

| 实体 | 字段名 | 说明 |
|--------|------------|-------|
| Model | `map` | 模型的性能指标（正确） |
| TrainingJob | `finalMap` | 训练完成后的最终指标（正确） |

这是**不同的实体**，使用**不同的字段名**。两者都是正确的。

## 前端显示格式化示例

```typescript
// 进度：后端返回 0-1，前端显示 0-100
<el-progress :percentage="(job.progress || 0) * 100" />

// 轮次显示：显示 当前/总数
{{ job.currentEpoch || 0 }} / {{ job.epochs || 0 }}

// 指标：使用 finalMap, finalLoss（不是 map, loss）
mAP: {{ job.finalMap || '-' }}
Loss: {{ job.finalLoss || '-' }}

// 状态：必须使用大写比较
v-if="job.status === 'PENDING'"  // 不是 'pending'
v-if="job.status === 'RUNNING'"  // 不是 'running'
```

## 重要规则

### 1. 命名约定
- **数据库**: snake_case（全小写，下划线分隔）
- **Java 后端**: camelCase，使用 @Column 显式映射列名
- **前端 TypeScript**: camelCase，与 Java DTO 字段名完全匹配

### 2. 枚举值
- 所有 Java 枚举值使用**大写**（PENDING, RUNNING, COMPLETED 等）
- 前端必须使用大写值进行比较
- 使用 `Record<string, string>` 进行类型安全的映射

### 3. 进度表示
- **存储**: 数据库/后端存储浮点数 0-1
- **显示**: 乘以 100 转换为百分比
- 使用 `(value || 0) * 100` 进行安全转换

### 4. 字段名错误模式（不要使用）

#### TrainingJob 实体
| ❌ 错误 | ✅ 正确 |
|---------|-----------|
| totalEpochs | epochs |
| map | finalMap（针对 TrainingJob） |
| loss | finalLoss |
| elapsedTime | startedAt（或客户端计算） |
| estimatedTimeRemaining | DTO 中不存在（不要使用） |
| modelName | baseModel 或 baseModelName |
| map50 | DTO 中不存在（不要使用） |
| precision | DTO 中不存在（不要使用） |
| recall | DTO 中不存在（不要使用） |
| learningRate | DTO 中不存在（不要使用） |

#### Model 实体
| ❌ 错误 | ✅ 正确 |
|---------|-----------|
| N/A | `map` 对 Model 实体是正确的 |

## 验证清单

提交更改前检查：

- [ ] 所有数据库列使用 snake_case
- [ ] 所有 @Column 注解显式映射到 snake_case
- [ ] 所有前端字段名与后端 DTO 完全匹配
- [ ] 所有枚举比较使用大写值
- [ ] 进度值显示时乘以 100
- [ ] 移除所有"DTO 中不存在"的字段
- [ ] 测试：创建任务并验证所有字段正确显示
- [ ] 测试：检查 404 错误是否已解决

## 常见错误快速参考

### 错误："column xxx does not exist"
**原因**: 添加新实体字段后数据库架构未更新
**修复**: 运行 ALTER TABLE 添加缺失的列

### 错误：按钮不显示（启动/停止/暂停）
**原因**: 状态大小写不匹配（比较小写 vs 大写）
**修复**: 使用大写比较：`row.status === 'PENDING'`

### 错误：指标显示 undefined
**原因**: 字段名错误（map vs finalMap，loss vs finalLoss）
**修复**: 使用 DTO 中的正确字段名

### 错误：进度显示 0-1 而不是 0-100%
**原因**: 没有乘以 100
**修复**: 使用 `(row.progress || 0) * 100`

## 模块扩展模板

为任何模块添加新字段时，遵循此模板：

1. **数据库**: 添加 snake_case 列
   ```sql
   ALTER TABLE table_name ADD COLUMN new_field VARCHAR(100);
   ```

2. **实体**: 添加带 @Column 映射的字段
   ```java
   @Column(name = "new_field")
   private String newField;
   ```

3. **DTO**: 添加字段（与实体同名）
   ```java
   private String newField;
   ```

4. **前端**: 使用与 DTO 完全相同的名称
   ```typescript
   {{ job?.newField }}
   ```
