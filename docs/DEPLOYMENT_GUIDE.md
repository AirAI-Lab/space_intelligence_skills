# 模型部署配置指南

本文档详细说明云边协同模型部署的配置和故障排查。

## 目录

- [重要配置：BACKEND_EXTERNAL_URL](#重要配置backend_external_url)
- [部署流程](#部署流程)
- [Jetson设备配置](#jetson设备配置)
- [故障排查](#故障排查)

---

## 重要配置：BACKEND_EXTERNAL_URL

### 为什么需要此配置

当创建模型部署任务时，云端会通过 MQTT 向 Jetson 设备发送下载模型文件的 URL。这个 URL 必须是 Jetson 设备能够访问的地址。

### 配置位置

`deployment/docker/docker-compose.yml`

```yaml
backend:
  environment:
    # 外部访问URL配置（设备下载文件用，根据实际网络修改）
    - BACKEND_EXTERNAL_URL=http://192.168.0.103:8081
```

### 配置场景

| 场景 | 配置值 | 示例 |
|------|--------|------|
| **局域网部署** | `http://服务器IP:8081` | `http://192.168.1.100:8081` |
| **公网部署** | `http://域名:8081` | `http://cloud.example.com:8081` |
| **HTTPS部署** | `https://域名` | `https://cloud.example.com` |
| **本地测试** | `http://localhost:8081` | 仅用于同机测试 |

### 如何获取服务器IP

**Windows:**
```powershell
ipconfig
# 查找 "IPv4 地址"
```

**Linux:**
```bash
ip addr show
# 或
hostname -I
```

### 验证配置

在 Jetson 设备上运行以下命令验证能否访问：

```bash
# 测试连接
curl -I http://your-backend-url:8081/actuator/health

# 测试文件下载（使用实际的文件路径）
curl "http://your-backend-url:8081/api/v1/files/download?path=/app/work/outputs/CONVxxx/best.onnx" --output test.onnx
```

**成功响应示例：**
```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Length: 12481922
```

---

## 部署流程

### 1. 前置检查

- [ ] 云端服务正常运行（后端、训练、MQTT）
- [ ] 模型已转换为 ONNX 或 Engine 格式
- [ ] BACKEND_EXTERNAL_URL 已正确配置
- [ ] Jetson 设备在线（心跳正常）

### 2. 创建部署任务

**方式1：通过Web界面**
1. 进入"模型管理" → 选择模型 → 点击"部署"
2. 选择目标设备
3. 确认部署

**方式2：通过API**
```bash
curl -X POST http://localhost:8081/api/v1/ota/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "taskName": "模型部署",
    "upgradeType": "MODEL",
    "modelId": "M_JOBxxx",
    "deviceIds": ["jetson_orin_001"]
  }'
```

### 3. 监控部署进度

**Web界面：** 进入"部署记录"查看实时进度

**API查询：**
```bash
# 查询任务状态
curl http://localhost:8081/api/v1/ota/tasks/{task_id}

# 查询设备状态
curl http://localhost:8081/api/v1/ota/tasks/{task_id}/devices
```

### 4. 部署状态说明

| 状态 | 说明 | 预期耗时 |
|------|------|----------|
| **PENDING** | 任务已创建，等待启动 | < 1秒 |
| **DOWNLOADING** | 设备正在下载模型 | 取决于文件大小和网络 |
| **INSTALLING** | 设备正在安装/转换 | TensorRT转换可能需要1-5分钟 |
| **DEPLOYING** | 部署执行中 | - |
| **SUCCESS** | 部署成功 | - |
| **FAILED** | 部署失败 | - |

---

## Jetson设备配置

### 网络配置

**确保 Jetson 设备能访问云端服务：**

```bash
# 测试网络连通性
ping <云端服务器IP>

# 测试 HTTP 访问
curl -I http://<云端服务器IP>:8081/actuator/health
```

### MQTT 配置

Jetson 设备需要订阅以下 MQTT 主题：

```
# 订阅OTA指令
device/{device_id}/ota/command

# 发布设备状态
device/{device_id}/ota/status
device/{device_id}/heartbeat
```

### 模型存储目录

Jetson 设备默认模型存储路径：

```
/opt/edge-infer/models/
├── {model_id}/
│   ├── best.onnx      # ONNX 模型
│   ├── best.engine    # TensorRT 引擎
│   └── model_config.json  # 模型配置
```

---

## 故障排查

### 问题1：进度一直为0%

**症状：** 部署任务创建后，进度一直显示0%，设备状态为 DOWNLOADING

**可能原因：**
1. Jetson 设备无法访问下载 URL
2. MQTT 消息未送达
3. 模型文件路径错误

**排查步骤：**

```bash
# 1. 检查云端日志
docker logs edge_cloud_backend | grep "OTA.*下载"

# 2. 检查 MQTT 消息是否发送
docker logs edge_cloud_backend | grep "OTA 升级消息已发送"

# 3. 在 Jetson 设备上测试下载
curl "http://BACKEND_EXTERNAL_URL/api/v1/files/download?path=xxx" --output test.onnx
```

**解决方案：**
- 修正 BACKEND_EXTERNAL_URL 配置
- 检查防火墙设置
- 确认 Jetson 设备网络连接正常

### 问题2：下载失败

**症状：** 设备状态显示下载失败

**可能原因：**
1. 模型文件不存在
2. S3/存储服务异常
3. 网络中断

**排查步骤：**

```bash
# 检查模型文件是否存在
curl http://localhost:8081/api/v1/models/{model_id}

# 检查文件路径
# ONNX 文件应该在 S3 或 /app/work/outputs/ 目录下
```

**解决方案：**
- 重新转换模型
- 检查存储服务状态
- 重启部署任务

### 问题3：TensorRT构建失败

**症状：** 安装阶段失败，错误信息包含 "TensorRT" 或 "Engine"

**可能原因：**
1. ONNX 文件格式不正确
2. TensorRT 版本不兼容
3. Jetson 设备内存不足

**排查步骤：**

```bash
# 在 Jetson 设备上查看日志
journalctl -u edge-infer -n 100

# 检查 TensorRT 版本
dpkg -l | grep tensorrt
```

**解决方案：**
- 确认训练服务导出的是标准 ONNX 格式
- 更新 Jetson 设备 TensorRT 版本
- 减小批处理大小或模型输入尺寸

### 问题4：设备离线

**症状：** 设备列表显示离线状态

**可能原因：**
1. Jetson 设备未运行
2. 网络连接中断
3. MQTT 连接断开

**排查步骤：**

```bash
# 检查设备心跳时间
curl http://localhost:8081/api/v1/devices/{device_id}

# 查看 MQTT 连接状态
# 登录 EMQX Dashboard: http://localhost:18083
# 检查客户端列表
```

**解决方案：**
- 启动 Jetson 设备上的 edge-infer 服务
- 检查网络连接
- 重启 MQTT 客户端

---

## 配置检查清单

部署前请确认以下配置：

### 云端配置

- [ ] `BACKEND_EXTERNAL_URL` 已设置为 Jetson 可访问的地址
- [ ] 后端服务运行正常（`curl http://localhost:8081/actuator/health`）
- [ ] MQTT 服务运行正常（EMQX Dashboard 可访问）
- [ ] 模型文件已转换（ONNX 或 Engine 格式）

### 网络配置

- [ ] Jetson 设备能 ping 通云端服务器
- [ ] Jetson 设备能访问 BACKEND_EXTERNAL_URL
- [ ] 防火墙允许 8081 端口访问
- [ ] MQTT 端口 1883 可访问

### 设备配置

- [ ] Jetson 设备在线（心跳正常）
- [ ] MQTT 客户端正常运行
- [ ] 设备有足够存储空间（至少 2GB）

---

## API 参考

### 创建部署任务

```http
POST /api/v1/ota/tasks
Content-Type: application/json

{
  "taskName": "模型部署",
  "upgradeType": "MODEL",
  "modelId": "M_JOBxxx",
  "deviceIds": ["jetson_orin_001"],
  "strategy": "IMMEDIATE"
}
```

### 查询任务状态

```http
GET /api/v1/ota/tasks/{task_id}
```

### 查询设备状态

```http
GET /api/v1/ota/tasks/{task_id}/devices
```

### 重试失败任务

```http
POST /api/v1/ota/tasks/{task_id}/devices/{device_id}/retry
```

---

## 附录：完整部署示例

### 场景：局域网部署

**服务器信息：**
- IP: 192.168.1.100
- 端口: 8081

**配置步骤：**

1. 编辑 `docker-compose.yml`：
```yaml
- BACKEND_EXTERNAL_URL=http://192.168.1.100:8081
```

2. 重启后端服务：
```bash
docker-compose restart backend
```

3. 在 Jetson 设备上验证：
```bash
curl -I http://192.168.1.100:8081/actuator/health
```

4. 创建部署任务（通过 Web 界面或 API）

5. 监控部署进度

### 预期日志

**云端日志：**
```
使用 ONNX 文件进行 OTA: modelId=M_JOBxxx, file=best.onnx, url=http://192.168.1.100:8081/api/v1/files/download?path=/app/work/outputs/CONVxxx/best.onnx
OTA 升级消息已发送: deviceId=jetson_orin_001, topic=device/jetson_orin_001/ota/command
```

**Jetson 设备日志：**
```
收到OTA升级指令: task_id=OTAxxx
开始下载模型: url=http://192.168.1.100:8081/api/v1/files/download?path=...
下载完成: size=12481922 bytes
开始构建TensorRT引擎...
引擎构建完成
部署成功
```
