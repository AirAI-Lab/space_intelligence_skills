# edge_infer_cloud 快速启动指南

## 前置准备

### 1. 硬件要求

| 资源 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 8核+ | 16核+ |
| 内存 | 32GB | 64GB |
| 存储 | 100GB 可用空间 | 200GB+ NVMe SSD |
| GPU (可选) | - | NVIDIA RTX 4060 Ti 16GB+ |

### 2. 软件要求

- Windows 10/11 或 Linux
- Docker Desktop 4.30+ (Windows) 或 Docker 24+ (Linux)
- NVIDIA GPU Driver 545+ (如需 GPU 训练)
- Git

---

## 快速启动 (5 分钟)

### 第一步：克隆项目

```powershell
# Windows PowerShell
cd D:\github
git clone https://github.com/SnakeJenny/edge_infer_cloud.git
cd edge_infer_cloud
```

### 第二步：创建数据卷目录

```powershell
# Windows PowerShell
New-Item -ItemType Directory -Path "D:\docker\volumes\edge_cloud" -Force
New-Item -ItemType Directory -Path "D:\docker\volumes\edge_cloud\postgres_data" -Force
New-Item -ItemType Directory -Path "D:\docker\volumes\edge_cloud\redis_data" -Force
New-Item -ItemType Directory -Path "D:\docker\volumes\edge_cloud\influxdb_data" -Force
New-Item -ItemType Directory -Path "D:\docker\volumes\edge_cloud\minio_data" -Force
New-Item -ItemType Directory -Path "D:\docker\volumes\edge_cloud\mlflow_data" -Force
New-Item -ItemType Directory -Path "D:\docker\volumes\edge_cloud\emqx_data" -Force
```

### 第三步：配置环境变量

```powershell
# 复制环境变量模板
cd deployment\docker
Copy-Item .env.example .env

# 使用记事本编辑 .env 文件
notepad .env
```

**重要配置项：**
```bash
# 确认数据卷路径正确
VOLUME_BASE_PATH=D:/docker/volumes/edge_cloud

# 生产环境请修改密码
SPRING_DATASOURCE_PASSWORD=edge_pass_change_me
INFLUXDB_PASSWORD=influx_admin_pass_change_me
MINIO_SECRET_KEY=minioadmin_change_me
```

### 第四步：启动服务

#### 选项 A：仅启动管理平台（无 GPU 训练）

```powershell
# 启动所有服务（除训练服务）
docker-compose up -d postgres redis emqx influxdb minio mlflow backend frontend

# 等待服务启动
Start-Sleep -Seconds 30
```

#### 选项 B：启动完整平台（含 GPU 训练）

```powershell
# 确认 GPU 可用
docker run --rm --gpus all nvcr.io/nvidia/cuda:12.5.0-base-ubuntu22.04 nvidia-smi

# 启动所有服务（包括 GPU 训练）
docker-compose --profile gpu up -d

# 等待服务启动
Start-Sleep -Seconds 60
```

### 第五步：验证安装

```powershell
# 检查容器状态
docker-compose ps

# 检查服务健康状态
curl http://localhost:8081/actuator/health
```

### 第六步：访问服务

| 服务 | 地址 | 用户名 | 密码 | 说明 |
|------|------|--------|------|------|
| **中文导航门户** ⭐ | http://localhost:8889 | - | - | 统一服务入口 |
| 前端管理平台 | http://localhost:3000 | - | - | Vue3 管理平台 |
| 后端 API | http://localhost:8081 | - | - | Spring Boot REST API |
| API 文档 | http://localhost:8081/swagger-ui.html | - | - | Swagger UI 接口文档 |
| EMQX Dashboard | http://localhost:18083 | admin | admin123456 | MQTT 消息队列 |
| MLflow | http://localhost:5001 | - | - | 模型管理（英文） |
| SeaweedFS | http://localhost:8888 | - | - | 文件存储（英文） |

> **提示**：MLflow 和 SeaweedFS 为国际开源项目，无官方中文版。建议通过中文导航门户访问。

---

## 常用操作

### 查看日志

```powershell
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f training
```

### 停止服务

```powershell
# 停止所有服务
docker-compose down

# 停止并删除数据卷（谨慎操作！）
docker-compose down -v
```

### 重启服务

```powershell
# 重启特定服务
docker-compose restart backend

# 重启所有服务
docker-compose restart
```

### 更新服务

```powershell
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```

---

## 故障排查

### 问题 1：端口冲突

```powershell
# 检查端口占用
netstat -ano | findstr :3000
netstat -ano | findstr :8081

# 解决方法：修改 docker-compose.yml 中的端口映射
```

### 问题 2：GPU 不可用

```powershell
# 检查 NVIDIA 驱动
nvidia-smi

# 检查 Docker GPU 支持
docker run --rm --gpus all nvcr.io/nvidia/cuda:12.5.0-base-ubuntu22.04 nvidia-smi

# Windows 确认 WSL2 和 Docker Desktop 配置
# Settings → General → Use the WSL 2 based engine
# Settings → Resources → WSL Integration
```

### 问题 3：容器启动失败

```powershell
# 查看详细日志
docker-compose logs backend
docker-compose logs training

# 检查数据卷权限
ls -la D:/docker/volumes/edge_cloud
```

### 问题 4：数据库连接失败

```powershell
# 检查 PostgreSQL 容器状态
docker ps | findstr postgres

# 进入容器检查
docker exec -it edge_cloud_postgres psql -U edge_user -d edge_cloud
```

---

## 开发模式启动

### 前端开发

```powershell
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
```

### 后端开发

```powershell
cd backend
mvn spring-boot:run
# API 访问 http://localhost:8081
```

### 训练服务开发

```powershell
cd training
pip install -r requirements.txt
python -m edge_train.cli --help
```

---

## 生产部署建议

1. **修改默认密码**
   - 数据库密码 (edge_user)
   - EMQX 密码 (admin/admin123456)
   - SeaweedFS S3 密钥 (admin/admin123456)

2. **配置资源限制**
   - 在 docker-compose.yml 中设置 CPU/内存限制
   - 使用 `deploy.resources` 配置

3. **启用 HTTPS**
   - 使用 Nginx 反向代理
   - 配置 SSL 证书

4. **定期备份**
   - PostgreSQL + TimescaleDB 数据备份
   - SeaweedFS 文件备份
   - MLflow 模型备份
   - Redis 持久化配置

5. **监控告警**
   - 使用后端 API 监控端点
   - 配置自定义监控面板

---

## 下一步

- 阅读 [用户手册](./user_manual/01_quick_start.md)
- 查看 [API 文档](./api.md)
- 了解 [架构设计](./architecture.md)

## 获取帮助

- GitHub Issues: https://github.com/SnakeJenny/edge_infer_cloud/issues
- 文档: https://docs.edgeinfer.cloud
