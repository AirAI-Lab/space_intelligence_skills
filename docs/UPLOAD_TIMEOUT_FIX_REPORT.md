# 上传超时和进度显示修复完成报告

## 修复日期
2026-01-27

## 修复概述

修复了模型上传超时（30000ms）和上传进度一直显示的问题。

---

## 问题分析

### 原始错误
```
导入模型失败: timeout of 30000ms exceeded
```

### 问题原因
1. **axios 默认超时太短**: 30 秒超时对于 5.99MB 文件不够
2. **没有上传进度显示**: 用户无法知道上传进度
3. **文件上传使用普通请求**: 应该使用专用长超时配置

---

## 修复方案

### 1. 创建专用上传请求实例

**文件**: [frontend/src/api/index.ts](frontend/src/api/index.ts)

**修改**:
```typescript
// 普通请求 60 秒超时
const request = axios.create({
  baseURL: '/api/v1',
  timeout: 60000
})

// 文件上传 5 分钟超时
const uploadRequest = axios.create({
  baseURL: '/api/v1',
  timeout: 300000
})
```

### 2. 更新模型上传 API

**修改**:
```typescript
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
}
```

### 3. 前端上传逻辑更新

**文件**: [frontend/src/views/model/ModelList.vue](frontend/src/views/model/ModelList.vue)

**修改**:
```typescript
// 导入模型
const importModel = async () => {
  // ... 验证代码 ...

  importing.value = true
  uploadProgress.value = 0  // 初始化进度

  try {
    // 1. 创建模型记录
    const createResponse = await modelApi.create({...})
    const modelId = createResponse.data.modelId

    // 2. 上传模型文件（带进度回调）
    await modelApi.upload(modelId, uploadedFile.value, (percent) => {
      uploadProgress.value = percent  // 实时更新进度
    })

    ElMessage.success('模型导入成功')
  } catch (error: any) {
    ElMessage.error('导入模型失败: ' + (error.message || '未知错误'))
  } finally {
    importing.value = false
    uploadProgress.value = 0
  }
}
```

### 4. 按钮文本显示进度

**模板**:
```vue
<el-button type="primary" @click="importModel" :loading="importing">
  {{ importing ? `上传中 ${uploadProgress}%` : '导入' }}
</el-button>
```

---

## 配置修改总结

| 配置项 | 修改前 | 修改后 |
|--------|--------|--------|
| axios 普通请求超时 | 30 秒 | 60 秒 |
| axios 文件上传超时 | 30 秒 | 300 秒 (5分钟) |
| 上传进度显示 | 无 | 实时百分比 |
| 最大文件大小 | 1MB | 500MB |

---

## 测试步骤

### 1. 清空浏览器缓存
- 按 `Ctrl` + `Shift` + `R` 硬刷新

### 2. 访问前端
```
http://localhost:3000
```

### 3. 测试模型上传
1. 导航到"模型管理"
2. 点击"导入模型"
3. 填写信息：
   - 模型名称：`测试模型`
   - 模型类型：`目标检测 (YOLOv8)`
   - 框架：`PyTorch`
   - 版本：`1.0.0`
4. 选择模型文件（.pt 文件，最大 500MB）
5. 点击"导入"

**预期结果**:
- 按钮显示"上传中 0%"
- 进度条从 0% → 100%
- 上传完成后显示"模型导入成功"

---

## 故障排除

### 如果仍然超时

1. **检查网络速度**
```bash
# 测试上传速度
curl -o /dev/null -w "Speed: %{speed_download} bytes/sec" -F "file=@test.pt" http://localhost:3000/api/v1/models/test/upload
```

2. **检查后端日志**
```bash
docker logs edge_cloud_backend -f
# 查看是否有上传相关错误
```

3. **检查磁盘空间**
```bash
docker exec edge_cloud_backend df -h
# 确保有足够的磁盘空间
```

### 如果进度不更新

1. **打开浏览器开发者工具 (F12)**
2. **查看 Network 选项卡**
3. **找到上传请求**
4. **查看 "Size" 和 "Time" 列**

---

## 后端存储位置

### 本地存储模式
```
/app/data/files/models/{model_id}/{file_name}
```

### 查看存储的文件
```bash
# 进入后端容器
docker exec -it edge_cloud_backend sh

# 查看模型文件
ls -lh /app/data/files/models/

# 查看特定模型的文件
ls -lh /app/data/files/models/{model_id}/
```

---

## 支持的模型文件格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| PyTorch | `.pt`, `.pth` | PyTorch 训练的模型 |
| ONNX | `.onnx` | 跨平台推理模型 |
| TensorRT | `.engine` | NVIDIA GPU 加速模型 |

---

## 当前状态

### ✅ 已完成
- axios 超时时间增加到 60 秒（普通请求）
- 文件上传超时时间增加到 5 分钟
- 添加上传进度实时显示
- 按钮显示上传百分比

### ✅ 已配置
- Spring Boot 文件上传限制: 500MB
- Nginx 上传大小限制: 500MB
- 后端本地存储服务

---

## 下次测试

1. **清空浏览器缓存**: `Ctrl` + `Shift` + `R`
2. **访问**: http://localhost:3000
3. **测试上传**: 选择 5.99MB 的 .pt 文件
4. **观察进度**: 按钮应该显示"上传中 X%"

如果仍有问题，请查看：
- 浏览器开发者工具 → Network 选项卡（查看上传状态）
- 后端日志: `docker logs edge_cloud_backend -f`
