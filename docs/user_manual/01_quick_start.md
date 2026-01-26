# 快速开始

## 前置准备

### 宿主机配置要求

#### 最低配置（开发/测试）
| 资源 | 配置 | 说明 |
|------|------|------|
| CPU | 8核+ | Intel i7/AMD Ryzen 7 |
| 内存 | 32GB | 运行所有容器 |
| 存储 | 500GB SSD | 系统+数据+模型 |
| 网络 | 千兆网卡 | 局域网通信 |

#### 推荐配置（小规模生产）
| 资源 | 配置 | 说明 |
|------|------|------|
| CPU | 16核+ | AMD Ryzen 9/Intel i9 |
| 内存 | 64GB | 支持多并发 |
| 存储 | 2TB NVMe SSD | 数据+模型存储 |
| GPU | RTX 4060 Ti 16GB | 小规模训练 |
| 网络 | 千兆网卡 | 局域网通信 |

### 软件要求

- Docker 24.0+
- Docker Compose 2.20+
- Node.js 18+ (开发前端)
- Java 17+ (开发后端)
- Python 3.10+ (训练)
- Go 1.21+ (开发Agent)

### 边缘设备准备

- Jetson Xavier NX / AGX Orin / Nano
- 已安装 edge_infer 推理框架
- 网络与宿主机连通

## 5分钟快速部署

### 第一步：克隆仓库

```bash
cd D:\github
git clone https://github.com/yourorg/edge_infer_cloud.git
cd edge_infer_cloud
```

### 第二步：配置环境变量

```bash
cd deployment/docker
cp .env.example .env
# 编辑 .env 文件，修改密码等配置
```

### 第三步：启动所有服务

```bash
# Windows PowerShell
docker-compose up -d

# Linux/Mac
docker-compose up -d
```

### 第四步：验证安装

```bash
# 查看所有容器状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

## 访问服务

启动成功后，可以访问以下服务：

| 服务 | 地址 | 用户名 | 密码 |
|------|------|--------|------|
| 前端 | http://localhost:3000 | - | - |
| 后端API | http://localhost:8080 | - | - |
| MinIO控制台 | http://localhost:9001 | minioadmin | minioadmin |
| EMQX控制台 | http://localhost:18083 | admin | public |
| MLflow | http://localhost:5000 | - | - |
| Grafana | http://localhost:3001 | admin | admin |

## 注册边缘设备

### 方式一：通过Web界面

1. 打开前端页面 http://localhost:3000
2. 点击"设备管理" → "添加设备"
3. 填写设备信息
4. 生成设备证书

### 方式二：通过API

```bash
curl -X POST http://localhost:8080/api/v1/device/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "EDGE_DEVICE_001",
    "device_name": "边缘设备1",
    "device_type": "jetson_orin"
  }'
```

### 在边缘设备上运行Agent

```bash
# 在边缘设备上
wget https://github.com/yourorg/edge_infer_cloud/releases/download/v1.0.0/edge-agent-linux-arm64
chmod +x edge-agent-linux-arm64
./edge-agent-linux-arm64 --server=http://YOUR_HOST_IP:8080 --device-id=EDGE_DEVICE_001
```

## 运行第一个推理任务

### 第一步：上传模型

1. 点击"模型管理" → "上传模型"
2. 选择训练好的模型文件（.engine 或 .onnx）
3. 填写模型信息

### 第二步：部署到边缘设备

1. 在模型列表中，点击"部署"
2. 选择目标设备
3. 确认部署

### 第三步：启动推理

```bash
# 通过API启动推理
curl -X POST http://localhost:8080/api/v1/inference/start \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "EDGE_DEVICE_001",
    "model_id": "your_model_id",
    "input_uri": "rtsp://camera_stream"
  }'
```

## 常见问题

### Q1: 端口冲突怎么办？

如果默认端口已被占用，可以在 `.env` 文件中修改端口配置，或修改 `docker-compose.yml` 中的端口映射。

### Q2: 如何停止所有服务？

```bash
docker-compose down
```

### Q3: 如何查看日志？

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs postgres

# 实时查看日志
docker-compose logs -f backend
```

### Q4: 如何备份数据？

```bash
# 备份PostgreSQL
docker exec edge-cloud-postgres pg_dump -U edge_user edge_cloud > backup.sql

# 备份MinIO
docker exec edge-cloud-minio mc mirror /data /backup/minio
```

## 下一步

- 阅读 [设备管理指南](02_device_management.md)
- 阅读 [数据管理指南](03_data_management.md)
- 阅读 [模型训练指南](04_training.md)
