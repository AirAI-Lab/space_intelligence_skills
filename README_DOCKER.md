# edge_infer_cloud Docker 部署手册

本文档说明如何从零开始，在一台新机器上通过 Docker 快速部署 **edge_infer_cloud 云边协同管理平台**。

> 目标读者：新加入团队的成员，需在一台全新 PC（Windows/Linux）上完成环境搭建并跑通所有服务。

---

## 1. 平台架构概览

edge_infer_cloud 由以下服务组成：

| 服务 | 技术栈 | 端口 | 说明 |
|------|--------|------|------|
| postgres | TimescaleDB + PostgreSQL 16 | 5432 | 时序+关系数据库 |
| redis | Redis 7 Alpine | 6379 | 缓存层 |
| emqx | EMQX 5.5 | 1883/8083/18083 | MQTT 消息代理 |
| mlflow | MLflow 2.9 | 5001 | 模型管理 |
| seaweedfs | SeaweedFS | 8333/8080/8888 | S3 兼容对象存储 |
| portal | Nginx Alpine | 8889 | 中文导航门户 |
| frontend | Node 21 Alpine | 3000 | Vue3 前端 |
| backend | Maven + Eclipse Temurin 21 | 8081 | Spring Boot 后端 |
| cloud_infer | CUDA 12.8 + PyTorch | 5003 | C-RADIOv4 云端推理（需GPU） |
| training | CUDA 12.8 + PyTorch | 5002 | 训练服务（需GPU） |

其中 `cloud_infer` 和 `training` 需要 NVIDIA GPU，通过 `--profile gpu` 启动。

---

## 2. 硬件与软件要求

### 2.1 硬件要求

| 资源 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 8核+ | 16核+ |
| 内存 | 16GB | 32GB+ |
| 存储 | 100GB 可用 | 200GB+ NVMe SSD |
| GPU | - | NVIDIA RTX 4060 Ti 16GB+ |

### 2.2 软件要求

- **操作系统**：Windows 10/11 或 Ubuntu 20.04+
- **Docker**：Docker Desktop 4.30+（Windows）或 Docker Engine 24+（Linux）
- **NVIDIA GPU Driver**：545+（如需 GPU 训练/推理）
- **NVIDIA Container Toolkit**（Linux GPU 场景）
- **Git**

---

## 3. 安装 Docker

### 3.1 使用一键脚本安装（推荐）

项目提供了 Docker 安装脚本，支持 Windows 和 Linux：

**Windows PowerShell（管理员）：**
```powershell
cd D:\github\edge_infer_cloud
powershell -ExecutionPolicy Bypass -File .\scripts\install_docker.ps1
```

**Linux（Ubuntu/Debian）：**
```bash
cd /path/to/edge_infer_cloud
bash scripts/install_docker.sh
```

### 3.2 手动安装 Docker

#### Windows

1. 下载并安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. 安装时勾选 **Use WSL 2 based engine**
3. 安装完成后重启电脑
4. 打开 Docker Desktop，等待引擎启动完成
5. 验证安装：
   ```powershell
   docker --version
   docker compose version
   ```

#### Linux（Ubuntu/Debian）

```bash
# 1. 卸载旧版本
sudo apt-get remove -y docker docker-engine docker.io containerd runc

# 2. 安装依赖
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# 3. 添加 Docker 官方 GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 4. 添加 Docker 仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. 安装 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 6. 将当前用户加入 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 7. 验证
docker --version
docker compose version
```

### 3.3 安装 NVIDIA Container Toolkit（GPU 场景，Linux）

```bash
# 1. 添加 NVIDIA 仓库
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 2. 安装
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# 3. 配置 Docker 运行时
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 4. 验证 GPU 可用
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
```

> **Windows 用户**：Docker Desktop 内置了 GPU 支持，只需确保安装了最新的 NVIDIA 驱动即可，无需额外安装 NVIDIA Container Toolkit。

---

## 4. 克隆项目

```powershell
# Windows
cd D:\github
git clone https://github.com/SnakeJenny/edge_infer_cloud.git
cd edge_infer_cloud
```

```bash
# Linux
cd /opt
sudo git clone https://github.com/SnakeJenny/edge_infer_cloud.git
sudo chown -R $USER:$USER edge_infer_cloud
cd edge_infer_cloud
```

---

## 5. 配置环境

### 5.1 创建数据卷目录

**Windows PowerShell：**
```powershell
New-Item -ItemType Directory -Path "D:\docker\volumes\edge_cloud" -Force
```

**Linux：**
```bash
sudo mkdir -p /docker/volumes/edge_cloud
```

### 5.2 配置 .env 文件

```powershell
# Windows
cd deployment\docker
Copy-Item .env.example .env
notepad .env
```

```bash
# Linux
cd deployment/docker
cp .env.example .env
vim .env
```

**需要确认的关键配置项：**

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `VOLUME_BASE_PATH` | `D:/docker/volumes/edge_cloud` | 数据卷基础路径（Linux 改为 `/docker/volumes/edge_cloud`） |
| `SPRING_DATASOURCE_PASSWORD` | `edge_pass` | 数据库密码（生产环境务必修改） |
| `CLOUD_API_URL` | `http://192.168.0.103:8081` | 后端外部访问地址（改为本机局域网 IP） |
| `SPRING_REDIS_PASSWORD` | `redis_pass` | Redis 密码（生产环境务必修改） |

### 5.3 下载模型权重（GPU 场景）

如需使用云端推理和训练服务，需要下载以下模型文件并放入对应目录：

| 目录 | 内容 | 说明 |
|------|------|------|
| `models/C-RADIOv4-H/` | `c-radio_v4-h_half.pth.tar` | C-RADIOv4 分割模型权重 |
| `models/siglip2-giant-opt-patch16-384/` | SigLIP2 文本编码器 | 开放词汇分割的文本编码器 |
| `models/NVlabs_RADIO/` | RADIO 官方代码 | C-RADIOv4 依赖的底层代码 |

---

## 6. 启动服务

### 6.1 仅启动管理平台（无 GPU，适合开发调试）

```bash
cd deployment/docker

# 启动基础服务
docker compose up -d postgres redis emqx mlflow seaweedfs portal

# 等待数据库就绪（约 15s）
sleep 15

# 启动前后端
docker compose up -d backend frontend
```

### 6.2 启动完整平台（含 GPU 训练/推理）

```bash
cd deployment/docker

# 验证 GPU
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi

# 启动所有服务（含 GPU profile）
docker compose --profile gpu up -d
```

### 6.3 使用初始化脚本一键启动（推荐）

**Windows PowerShell：**
```powershell
cd deployment\docker
powershell -ExecutionPolicy Bypass -File .\init.ps1
```

脚本会自动检测 Docker、Git、GPU 状态，引导选择启动模式。

---

## 7. 验证部署

### 7.1 检查容器状态

```bash
docker compose ps
```

预期输出（管理平台模式）：

```
NAME                      STATUS          PORTS
edge_cloud_postgres       Up (healthy)    0.0.0.0:5432->5432/tcp
edge_cloud_redis          Up              0.0.0.0:6379->6379/tcp
edge_cloud_emqx           Up              0.0.0.0:1883->1883/tcp
edge_cloud_mlflow         Up (healthy)    0.0.0.0:5001->5000/tcp
edge_cloud_seaweedfs      Up (healthy)    0.0.0.0:8333->8333/tcp
edge_cloud_portal         Up              0.0.0.0:8889->80/tcp
edge_cloud_backend        Up              0.0.0.0:8081->8080/tcp
edge_cloud_frontend       Up              0.0.0.0:3000->3000/tcp
```

### 7.2 检查服务健康

```bash
# 后端健康检查
curl http://localhost:8081/actuator/health

# 训练服务（GPU 模式）
curl http://localhost:5002/health

# 云端推理（GPU 模式）
curl http://localhost:5003/health
```

### 7.3 访问各服务

| 服务 | 地址 | 账号 | 说明 |
|------|------|------|------|
| **中文导航门户** | http://localhost:8889 | - | 统一入口，推荐首次使用 |
| 前端管理平台 | http://localhost:3000 | - | Vue3 管理界面 |
| 后端 API | http://localhost:8081 | - | REST API |
| API 文档 | http://localhost:8081/swagger-ui.html | - | Swagger UI |
| EMQX 控制台 | http://localhost:18083 | admin / admin123456 | MQTT 管理 |
| MLflow | http://localhost:5001 | - | 模型实验管理 |
| SeaweedFS | http://localhost:8888 | - | 文件存储管理 |

---

## 8. 常用操作

### 8.1 日志查看

```bash
# 查看所有日志
docker compose logs -f

# 查看特定服务
docker compose logs -f backend
docker compose logs -f training
docker compose logs -f cloud_infer

# 查看最近 100 行
docker compose logs --tail=100 backend
```

### 8.2 停止与重启

```bash
# 停止所有服务
docker compose down

# 重启单个服务
docker compose restart backend

# 停止并清理数据卷（慎用！会删除数据库数据）
docker compose down -v
```

### 8.3 更新部署

```bash
git pull
docker compose up -d --build
```

### 8.4 进入容器调试

```bash
# 进入后端容器
docker exec -it edge_cloud_backend bash

# 进入数据库
docker exec -it edge_cloud_postgres psql -U edge_user -d edge_cloud

# 查看容器资源占用
docker stats
```

---

## 9. 故障排查

### 9.1 端口冲突

```powershell
# Windows
netstat -ano | findstr :3000
netstat -ano | findstr :8081
```

```bash
# Linux
ss -tlnp | grep :3000
ss -tlnp | grep :8081
```

修改 `docker-compose.yml` 中的端口映射解决。

### 9.2 GPU 不可用

```bash
# 检查驱动
nvidia-smi

# 检查 Docker GPU 支持
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi

# Linux: 确认 nvidia-container-toolkit 已安装
nvidia-ctk --version
```

### 9.3 后端启动失败（数据库未就绪）

后端依赖 PostgreSQL 完全启动。如出现数据库连接失败：

```bash
# 检查 postgres 状态
docker compose ps postgres

# 手动重启后端（等待 postgres healthy 后）
docker compose restart backend
```

### 9.4 SeaweedFS 健康检查超时

SeaweedFS 首次启动需要较长时间初始化（最多 90s），这是正常现象。如果持续失败：

```bash
# 查看 seaweedfs 日志
docker compose logs seaweedfs

# 重启
docker compose restart seaweedfs
```

### 9.5 前端 npm install 缓慢

前端使用 `node:21-alpine` 镜像，首次启动时会在容器内执行 `npm install`。如遇到网络问题，可配置 npm 镜像：

```bash
# 进入前端容器
docker exec -it edge_cloud_frontend sh

# 配置淘宝镜像
npm config set registry https://registry.npmmirror.com
```

---

## 10. 生产环境建议

1. **修改所有默认密码**：数据库、Redis、EMQX、SeaweedFS
2. **配置 HTTPS**：通过 Nginx 反向代理 + SSL 证书
3. **资源限制**：在 `docker-compose.yml` 中通过 `deploy.resources` 限制 CPU/内存
4. **定期备份**：PostgreSQL 数据 + SeaweedFS 文件 + MLflow 模型
5. **日志管理**：配置日志轮转，避免磁盘写满
6. **监控告警**：利用后端 `/actuator/health` 端点配置健康检查

---

## 11. Docker Compose 服务依赖关系

```
frontend ──→ backend ──→ postgres
          │          ├──→ redis
          │          ├──→ emqx
          │          └──→ seaweedfs
          └──→ (独立访问)
cloud_infer ──→ emqx
training ──→ mlflow ──→ (独立)
         ├──→ seaweedfs
         └──→ emqx
```

- `backend` 等待 postgres、redis、emqx、seaweedfs 就绪后启动
- `frontend` 等待 backend 启动
- `cloud_infer` 和 `training` 仅在 `--profile gpu` 时启动

---

## 12. 下一步

- 阅读 [快速启动指南](docs/QUICKSTART.md) 了解更多细节
- 查看 [API 文档](http://localhost:8081/swagger-ui.html)
- 了解边缘端部署：参考 `edge_infer` 项目的 `README_JETSON.md`
