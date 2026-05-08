# SkyEdge AI 部署指南

## 部署方式对比

| 方式 | 适用场景 | 管理方式 | 启动速度 |
|------|----------|----------|----------|
| **开发模式（当前）** | 本地开发调试 | `docker compose up -d` | 后端 ~85s |
| **生产模式（Docker）** | 服务器部署、小规模 | `deploy.sh` | 后端 ~15s |
| **混合模式** | 性能敏感场景 | systemd + Docker | 最优 |

---

## 方式一：开发模式（当前使用）

适用于开发阶段，代码修改实时生效。

```bash
cd deployment/docker
docker compose up -d
```

特点：
- 源码目录挂载到容器，修改即时生效
- 后端 `mvn spring-boot:run`，前端 `npm run dev`
- 在 Docker Desktop (Windows/Mac) 或 Linux 上运行

**问题**：启动慢、不适合生产、端口分散。

---

## 方式二：生产模式（推荐）

使用多阶段构建的预编译镜像 + Nginx 统一入口。

### 架构

```
                    ┌─────────────────────────────────┐
                    │         Nginx (:80)              │
                    │  统一反向代理 + 静态资源            │
                    └──┬──────┬──────┬──────┬─────────┘
                       │      │      │      │
              /api/    │  /ws  │  /   │ /s3/ │  /mqtt/ws
                       │      │      │      │
         ┌─────────────▼┐  ┌──▼──┐ ┌─▼──┐ ┌▼────────┐
         │  Backend     │  │ WS  │ │FE  │ │MQTT WS  │
         │  (JRE)       │  │     │ │    │ │         │
         └──────┬───────┘  └─────┘ └────┘ └─────────┘
                │
    ┌───────────┼───────────────┐
    │           │               │
  PostgreSQL  Redis    EMQX    SeaweedFS
  (时序数据)  (缓存)  (MQTT)   (文件存储)
```

### 部署步骤

**在 Linux 服务器上**（如 192.168.0.103）：

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/edge_infer_cloud.git
cd edge_infer_cloud

# 2. 一键部署
cd deployment/docker
chmod +x deploy.sh
./deploy.sh              # 生产模式
./deploy.sh --gpu        # 含 GPU 训练服务
```

### 管理命令

```bash
./deploy.sh --status     # 查看服务状态
./deploy.sh --logs       # 查看后端日志
./deploy.sh --logs nginx # 查看 nginx 日志
./deploy.sh --stop       # 停止所有服务
./deploy.sh --rebuild    # 重新构建镜像并部署
```

### 生产模式 vs 开发模式

| 对比项 | 开发模式 | 生产模式 |
|--------|----------|----------|
| 后端镜像 | `maven:3.9` (~500MB) | `eclipse-temurin:21-jre-alpine` (~200MB) |
| 前端镜像 | `node:21-alpine` + dev server | `nginx:alpine` + 静态文件 (~25MB) |
| 启动时间 | ~85s（编译+启动） | ~15s（直接运行 JAR） |
| 代码更新 | 热重载 | 需重新构建镜像 |
| 端口暴露 | 3000/8081/1883/8333/... | 仅 80/443/1935 |
| Nginx | 无 | 统一反向代理 |
| 资源限制 | 无 | 每个服务配额 |

### 统一访问入口

生产模式下所有服务通过 Nginx 的 80 端口统一入口：

| 路径 | 服务 | 说明 |
|------|------|------|
| `http://{HOST}/` | 前端 | 管理界面 |
| `http://{HOST}/api/v1/` | 后端 | REST API |
| `http://{HOST}/ws` | 后端 | WebSocket |
| `http://{HOST}/s3/` | SeaweedFS | 文件存储 |
| `http://{HOST}/mlflow/` | MLflow | 模型管理 |
| `http://{HOST}/mqtt/ws` | EMQX | MQTT WebSocket |
| `http://{HOST}/emqx/` | EMQX | 管理面板 |

---

## 方式三：开机自启（systemd）

部署到 Linux 服务器后，配置 systemd 实现开机自动启动：

```bash
# 复制服务文件
sudo cp deployment/docker/systemd/edge-cloud.service /etc/systemd/system/

# 按实际路径修改 WorkingDirectory
sudo sed -i "s|/opt/edge_cloud|$(pwd)|g" /etc/systemd/system/edge-cloud.service

# 启用并启动
sudo systemctl daemon-reload
sudo systemctl enable edge-cloud
sudo systemctl start edge-cloud

# 管理
sudo systemctl status edge-cloud
sudo systemctl stop edge-cloud
sudo systemctl restart edge-cloud
journalctl -u edge-cloud -f   # 查看日志
```

---

## 边缘设备部署参考

边缘推理框架采用原生部署（非 Docker），获得最佳 GPU 性能：

```
Jetson 设备（原生部署）
├── build/edge_framework     ← C++ 编译产物
├── config/                  ← 配置文件
├── models/                  ← TensorRT Engine
├── scripts/start.sh         ← 启停脚本
└── rtmp_nginx.conf          ← RTMP 推流
```

**为什么不推荐边缘设备用 Docker？**
- TensorRT/CUDA 在容器内性能损失约 10-15%
- Jetson 硬件编码器（h264_v4l2m2m）在容器内不可用
- 原生部署可直接使用 JetPack 多媒体 API
- 编译后的 C++ 二进制性能最优

**云端服务适合 Docker 的原因：**
- Java/Python 服务无 GPU 性能损失
- 统一环境管理，避免依赖冲突
- 多阶段构建后镜像体积小
- 易于横向扩展和迁移

---

## 环境变量配置

创建 `deployment/docker/.env` 文件：

```bash
# 版本号
VERSION=1.0.0

# 数据库密码（生产环境请修改）
PG_PASSWORD=edge_pass

# EMQX 管理面板密码
EMQX_PASSWORD=admin123456
```

---

## 从 Windows Docker Desktop 迁移到 Linux

如果当前在 Windows Docker Desktop 上运行，迁移到 Linux 服务器的步骤：

```bash
# 1. 在 Windows 上导出数据
docker exec edge_cloud_postgres pg_dump -U edge_user edge_cloud > backup.sql

# 2. 将代码和数据传输到 Linux 服务器
rsync -avz --exclude='.git' --exclude='node_modules' \
    ./edge_infer_cloud/ user@linux-server:/opt/edge_cloud/

# 3. 在 Linux 服务器上部署
cd /opt/edge_cloud/deployment/docker
./deploy.sh

# 4. 恢复数据（如需要）
cat backup.sql | docker exec -i edge_cloud_postgres psql -U edge_user -d edge_cloud
```

---

## 常见问题

**Q: 如何选择开发模式还是生产模式？**
- 开发调试用 `docker-compose.yml`（开发模式）
- 正式部署用 `docker-compose.prod.yml`（生产模式）
- 两者可以共存，但不要同时运行（端口冲突）

**Q: 如何更新代码后重新部署？**
- 开发模式：修改代码后自动热重载
- 生产模式：`./deploy.sh --rebuild`

**Q: 训练服务怎么启动？**
- 训练服务需要 NVIDIA GPU 和 nvidia-docker runtime
- 使用 `./deploy.sh --gpu` 启动，或 `docker compose --profile gpu up -d`
