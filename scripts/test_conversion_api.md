# 模型转换上传功能测试命令

## 环境变量
```bash
export CLOUD_BASE_URL="http://localhost:8080"  # 修改为实际的后端地址
export TASK_ID="CONV2026010112000012345"        # 修改为实际的转换任务ID
export ONNX_FILE="models/helmet_detect/best.onnx"
```

## 1. 检查转换任务状态
```bash
curl -s "${CLOUD_BASE_URL}/api/v1/conversion/tasks/${TASK_ID}" | jq '.'
```

## 2. 上传转换完成的文件（multipart/form-data）
```bash
curl -X POST \
  "${CLOUD_BASE_URL}/api/v1/conversion/internal/${TASK_ID}/complete-with-file" \
  -F "file=@${ONNX_FILE}" \
  -F "optimization_time_seconds=60" \
  | jq '.'
```

## 3. 验证模型记录已更新
```bash
# 先获取模型ID
MODEL_ID=$(curl -s "${CLOUD_BASE_URL}/api/v1/conversion/tasks/${TASK_ID}" | jq -r '.data.modelId')

# 获取模型详情
curl -s "${CLOUD_BASE_URL}/api/v1/models/${MODEL_ID}" | jq '.data | {status, onnxFilePath, onnxFileSizeBytes}'
```

## 4. 测试文件下载
```bash
# 下载 ONNX 文件（保存到本地）
MODEL_ID="your-model-id"
curl -X GET \
  "${CLOUD_BASE_URL}/api/v1/models/${MODEL_ID}/download?format=onnx" \
  -o "downloaded_model.onnx"

# 只检查响应头
curl -I "${CLOUD_BASE_URL}/api/v1/models/${MODEL_ID}/download?format=onnx"
```

## 5. 测试旧的回调方式（仅路径，不上传文件）
```bash
curl -X POST \
  "${CLOUD_BASE_URL}/api/v1/conversion/internal/${TASK_ID}/complete" \
  -d "output_path=models/helmet_detect/best.onnx" \
  -d "file_size_bytes=12345678" \
  -d "optimization_time_seconds=60"
```

## 6. 查看所有转换任务
```bash
curl -s "${CLOUD_BASE_URL}/api/v1/conversion/tasks?page=1&pageSize=10" | jq '.'
```

## 7. 查看所有模型
```bash
curl -s "${CLOUD_BASE_URL}/api/v1/models?page=1&pageSize=10" | jq '.data.items[] | {modelId, modelName, status, onnxFilePath}'
```

## 完整测试流程（PowerShell）
```powershell
# 设置变量
$CLOUD_BASE_URL = "http://localhost:8080"
$TASK_ID = "CONV2026010112000012345"
$ONNX_FILE = "models\helmet_detect\best.onnx"

# 1. 检查任务状态
Write-Host "1. 检查任务状态..."
Invoke-RestMethod -Uri "$CLOUD_BASE_URL/api/v1/conversion/tasks/$TASK_ID" -Method Get

# 2. 上传文件
Write-Host "2. 上传转换文件..."
$uploadResponse = Invoke-RestMethod -Uri "$CLOUD_BASE_URL/api/v1/conversion/internal/$TASK_ID/complete-with-file" `
    -Method Post `
    -Form @{
        file = Get-Item $ONNX_FILE
        optimization_time_seconds = 60
    }
$uploadResponse

# 3. 验证模型记录
Write-Host "3. 验证模型记录..."
$modelId = $uploadResponse.data.modelId
Invoke-RestMethod -Uri "$CLOUD_BASE_URL/api/v1/models/$modelId" -Method Get

# 4. 下载文件
Write-Host "4. 下载模型文件..."
Invoke-WebRequest -Uri "$CLOUD_BASE_URL/api/v1/models/$modelId/download?format=onnx" `
    -OutFile "test_download.onnx"
```

## 预期结果

### 成功的响应示例
```json
{
  "code": 200,
  "message": "成功",
  "data": null
}
```

### 模型详情更新后
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "modelId": "550e8400-e29b-41d4-a716-446655440000",
    "modelName": "helmet_detect",
    "status": "READY",
    "onnxFilePath": "models/uuid-filename.onnx",
    "onnxFileSizeBytes": 12345678
  }
}
```

### 下载响应头
```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="helmet_detect.onnx"
Content-Length: 12345678
```

## 故障排查

### 上传失败 (400)
- 检查任务ID是否正确
- 检查文件是否存在
- 检查文件类型是否正确

### 上传失败 (500)
- 检查后端日志
- 检查 S3/存储服务配置
- 检查文件大小是否超限

### 下载失败 (404)
- 检查模型记录中的文件路径
- 检查 S3/存储服务中文件是否存在
- 查看后端日志获取详细错误

### 下载返回 JSON 而非二进制
- 检查后端是否正常返回文件
- 查看响应内容是否为错误信息
- 检查存储服务配置
