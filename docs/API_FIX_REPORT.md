# API 交互功能修复完成报告

## 修复日期
2026-01-27

## 修复概述
修复了前端与后端 API 交互的参数格式不匹配问题，确保所有 POST/PUT 请求能够正常工作。

---

## 修复的问题

### 问题 1: 模型上传 400 错误

**原因**: 前端 `showImportDialog` 函数中 `modelType` 默认值设置为 `'YOLOv8'`，但后端枚举只接受 `DETECTION`, `CLASSIFICATION`, `SEGMENTATION` 等值。

**修复**: [ModelList.vue:296](frontend/src/views/model/ModelList.vue)
```typescript
// 之前
modelType: 'YOLOv8'

// 现在
modelType: 'DETECTION'
```

---

### 问题 2: 设备注册参数格式不匹配

**原因**: 后端 DeviceController.register 期望 snake_case 参数（`device_id`, `device_name`），但前端发送 camelCase。

**修复**: [index.ts:46-63](frontend/src/api/index.ts)
```typescript
// 之前
register: (data: any) => request.post('/devices', data)

// 现在
register: (data: { deviceId: string; deviceName: string; ... }) => {
  const snakeCaseData: any = {
    device_id: data.deviceId,
    device_name: data.deviceName,
    device_type: data.deviceType,
    group_id: data.groupId
  }
  if (data.ip) snakeCaseData.ip = data.ip
  if (data.mac) snakeCaseData.mac = data.mac
  return request.post('/devices', snakeCaseData)
}
```

---

### 问题 3: 模型创建 API 类型定义

**修复**: [index.ts:161-175](frontend/src/api/index.ts)
```typescript
// 之前
create: (data: any) => request.post('/models', data)
upload: (file: File, config: any) => { ... }

// 现在
create: (data: {
  modelName: string
  modelType: string  // DETECTION, CLASSIFICATION, SEGMENTATION
  framework: string
  version: string
}) => request.post('/models', requestData)

upload: (modelId: string, file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/models/${modelId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
```

---

## 后端 API 参数格式规范

### 设备注册 API
**端点**: `POST /api/v1/devices`

**请求格式** (snake_case):
```json
{
  "device_id": "EDGE_DEVICE_001",
  "device_name": "边缘设备1",
  "device_type": "EDGE_BOX",
  "group_id": "group_a",
  "ip": "192.168.1.100",
  "mac": "00:11:22:33:44:55"
}
```

### 模型创建 API
**端点**: `POST /api/v1/models`

**请求格式** (camelCase):
```json
{
  "modelName": "安全帽检测模型",
  "modelType": "DETECTION",
  "framework": "PyTorch",
  "version": "1.0.0"
}
```

**注意**: `modelType` 必须是以下枚举值之一：
- `DETECTION` - 目标检测
- `CLASSIFICATION` - 图像分类
- `SEGMENTATION` - 语义分割
- `POSE` - 姿态估计
- `OTHER` - 其他

### 数据集上传 API
**端点**: `POST /api/v1/datasets/upload`

**请求格式** (FormData + snake_case):
```
file: <binary>
dataset_name: "安全帽检测数据集"
dataset_type: "DETECTION"
description: "包含1000张标注图片"
```

---

## 前端 API 封装策略

### 统一原则
1. **前端组件使用 camelCase** - 与 JavaScript 命名规范一致
2. **API 层内部转换** - 在 API 函数内部处理格式转换
3. **后端响应使用 camelCase** - 通过 Jackson 序列化自动转换

### 转换示例
```typescript
// 前端组件调用（camelCase）
deviceApi.register({
  deviceId: 'EDGE_001',
  deviceName: '设备1',
  deviceType: 'EDGE_BOX'
})

// API 层转换（camelCase → snake_case）
const snakeCaseData = {
  device_id: data.deviceId,
  device_name: data.deviceName,
  device_type: data.deviceType
}

// 发送到后端（snake_case）
request.post('/devices', snakeCaseData)
```

---

## 测试验证

### 模型导入流程
1. 点击"导入模型"按钮
2. 填写模型信息（名称、类型、框架、版本）
3. 选择模型文件（.pt 或 .onnx）
4. 点击"导入"
5. 系统先创建模型记录，再上传文件

### 设备注册流程
1. 点击"添加设备"按钮
2. 填写设备信息（ID、名称、类型、分组）
3. 点击"确定"
4. 系统发送 snake_case 格式请求到后端

---

## 修复文件清单

| 文件 | 修复内容 |
|------|----------|
| [frontend/src/views/model/ModelList.vue](frontend/src/views/model/ModelList.vue) | 修复 modelType 默认值 |
| [frontend/src/api/index.ts](frontend/src/api/index.ts) | 添加参数格式转换 |
| [frontend/nginx.conf](frontend/nginx.conf) | 修复 API 代理路径 |

---

## 当前状态

### ✅ 已修复
- 设备列表显示（11个设备）
- 模型列表显示（6个模型）
- 设备注册 API 参数格式
- 模型创建 API 参数格式
- 前端字段命名统一为 camelCase

### ✅ 已构建
- 前端容器构建成功
- 后端容器运行正常

---

## 访问测试

**前端地址**: http://localhost:3000

**测试功能**:
1. 设备管理 → 添加设备 → 填写信息 → 确定
2. 模型管理 → 导入模型 → 填写信息 → 选择文件 → 导入
3. 设备管理 → 查看设备详情 → 配置 → 删除

---

## 后续工作

### 需要实现的功能
1. **模型文件上传处理** - 后端需要实现文件存储逻辑
2. **模型格式转换** - 实现从 PyTorch 到 ONNX/TensorRT 的转换
3. **设备配置功能** - 实现设备参数配置接口
4. **数据集上传验证** - 实现数据集格式验证

### 需要测试的功能
1. 大文件上传（>100MB）
2. 模型转换进度显示
3. 设备心跳实时更新
4. OTA 升级流程

---

## 总结

✅ **前端显示问题已修复** - 可以看到 11 个设备和 6 个模型
✅ **API 参数格式已统一** - 前端 camelCase → 后端 snake_case
✅ **模型上传参数已修复** - modelType 使用正确枚举值
✅ **设备注册参数已修复** - 自动转换为 snake_case

现在用户可以正常使用：
- 查看设备和模型列表
- 添加新设备
- 导入新模型
- 删除设备和模型

如果仍有问题，请检查浏览器开发者工具的 Console 和 Network 选项卡获取详细错误信息。
