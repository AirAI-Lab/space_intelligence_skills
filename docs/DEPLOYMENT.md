# SkyEdge AI 部署指南

## 部署方式对比

| 方式 | 适用场景 | 管理方式 | 启动速度 |
|------|----------|----------|----------|
| **开发模式** | 本地开发调试 | `docker compose up -d` | 后端 ~85s |
| **生产模式** | 服务器部署、演示 | `deploy.sh` | 后端 ~15s |
| **开机自启** | 长期运行 | systemd + Docker | 最优 |

---

## 开发模式 vs 生产模式

两者**都运行在 Docker 中**，区别不在"运行在哪里"，而在**容器内怎么跑**：

```
开发模式（当前）                              生产模式
┌──────────────────────────┐       ┌──────────────────────────┐
│ 镜像: maven (~500MB)     │       │ 镜像: JRE-alpine (~200MB) │
│ 命令: mvn spring-boot:run│       │ 命令: java -jar app.jar   │
│ 源码: 挂载 Windows 目录   │       │ 源码: 编译打包进镜像       │
│ 改代码: 自动热重载        │       │ 改代码: 需重新构建镜像     │
│ 启动: ~85秒(编译+运行)   │       │ 启动: ~15秒(直接运行)     │
│ 入口: 3000/8081/1883/... │       │ 入口: 统一 80 端口(Nginx) │
│ 资源: 无限制              │       │ 资源: 每服务有内存/CPU上限 │
│ 日志: 无大小限制          │       │ 日志: 50MB×5 轮转         │
└──────────────────────────┘       └──────────────────────────┘
```

**一句话**：开发模式是"在容器里写代码"，生产模式是"在容器里运行编译好的程序"。

### 详细对比

| 对比项 | 开发模式 | 生产模式 |
|--------|----------|----------|
| 后端镜像 | `maven:3.9` (~500MB) | `eclipse-temurin:21-jre-alpine` (~200MB) |
| 前端镜像 | `node:21-alpine` + dev server | `nginx:alpine` + 静态文件 (~25MB) |
| 启动时间 | ~85s（编译+启动） | ~15s（直接运行 JAR） |
| 代码更新 | 热重载 | 需重新构建镜像 |
| 端口暴露 | 3000/8081/1883/8333/... | 仅 80/443/1935 |
| Nginx | 无 | 统一反向代理 |
| 资源限制 | 无 | 每个服务配额 |
| 配置文件 | `docker-compose.yml` | `docker-compose.prod.yml` |

### Docker Desktop (Windows) vs Linux 服务器

| 对比 | Docker Desktop (Windows) | Linux 原生 Docker |
|------|--------------------------|-------------------|
| Docker 安装 | Docker Desktop 一键安装 | `curl get.docker.com \| sh` |
| 容器运行位置 | WSL2 虚拟机内核 | 直接在宿主机内核 |
| 磁盘 I/O | 慢 ~30%（跨虚拟磁盘） | 原生性能 |
| GPU 支持 | 仅 WSL2 GPU 直通，配置复杂 | nvidia-container-toolkit 原生支持 |
| 适用场景 | 开发调试 | 正式部署 |
| 部署命令 | **完全相同** | **完全相同** |

**推荐路径**：
```
当前阶段 → Docker Desktop 开发模式（写代码、调代码）
         → Docker Desktop 生产模式（验证构建产物是否正确）
部署上线 → Linux 服务器生产模式（./deploy.sh 一键部署）
```

---

## 生产模式架构

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

## 方式一：Windows Docker Desktop 部署

### 1.1 开发模式（当前使用）

适用于开发阶段，代码修改实时生效。

**前置条件**：
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 已安装并运行
- WSL2 后端已启用（Docker Desktop 默认使用 WSL2）

**启动**：

```bash
cd deployment/docker

# 模式 A: 纯推理 — 仅 EMQX + GPU 训练容器（2 容器）
docker compose --profile gpu up -d

# 模式 B: 推理 + 管理 — 无 GPU 训练（8 容器）
docker compose --profile standard up -d

# 模式 C: 完整平台 — 管理 + GPU 训练（10 容器）
docker compose --profile standard --profile gpu up -d
```

**部署模式说明**：

| 模式 | 命令 | 容器数 | 适用场景 |
|------|------|--------|----------|
| **A: 纯推理** | `--profile gpu` | 2 | 第三方只需 MQTT 推理结果，无需管理界面 |
| **B: 推理+管理** | `--profile standard` | 8 | 有管理需求但无 GPU 训练 |
| **C: 完整平台** | `--profile standard --profile gpu` | 10 | 全功能开发/生产部署 |

**各模式下服务状态**：

| 服务 | 模式 A | 模式 B | 模式 C |
|------|--------|--------|--------|
| EMQX (消息总线) | ✓ | ✓ | ✓ |
| Training (GPU 推理) | ✓ | — | ✓ |
| PostgreSQL | — | ✓ | ✓ |
| Redis | — | ✓ | ✓ |
| Backend (Spring Boot) | — | ✓ | ✓ |
| Frontend (Vue3) | — | ✓ | ✓ |
| MLflow | — | ✓ | ✓ |
| SeaweedFS | — | ✓ | ✓ |
| Portal | — | ✓ | ✓ |

> **模式 A（纯推理）**：EMQX 始终启动作为消息总线。第三方通过 MQTT 订阅 `results/#` 和 `alerts/#` 获取归一化推理结果。云端推理在 training 容器中运行。

**访问地址**：

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8081/api/v1 |
| EMQX 面板 | http://localhost:18083 |
| 文件存储 | http://localhost:8333 |

**日常开发**：

```bash
# 查看服务状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 重启某个服务
docker compose restart backend

# 停止所有服务
docker compose down

# 停止并清除数据（慎用）
docker compose down -v
```

### 1.2 生产模式（验证构建产物）

在 Windows Docker Desktop 上也可以运行生产模式，用于验证构建是否正确。

**从开发模式切换到生产模式**：

```bash
cd deployment/docker

# 1. 先停掉开发模式
docker compose down

# 2. 构建并启动生产模式
docker compose -f docker-compose.prod.yml up -d --build

# 3. 查看状态
docker compose -f docker-compose.prod.yml ps
```

**或者使用部署脚本**（Git Bash 中执行）：

```bash
chmod +x deploy.sh
./deploy.sh --stop       # 停开发模式
./deploy.sh              # 启动生产模式
```

**切换回开发模式**：

```bash
docker compose -f docker-compose.prod.yml down   # 停生产模式
docker compose up -d                              # 启开发模式
```

> 注意：两种模式不能同时运行（端口冲突），必须先停一个再启另一个。

**生产模式验证完成后**，输出应该是：
```
http://localhost/           → 前端管理界面（统一入口）
http://localhost/api/v1/    → REST API
http://localhost/emqx/      → EMQX 管理面板
```

---

## 方式二：Linux 服务器部署（推荐生产环境）

### 2.1 全新 Ubuntu 服务器安装

**步骤一：安装 Docker**

```bash
# 一键安装 Docker Engine（适用于 Ubuntu/Debian）
curl -fsSL https://get.docker.com | sh

# 将当前用户加入 docker 组（免 sudo）
sudo usermod -aG docker $USER

# 重新登录使组权限生效
exit
# 重新 SSH 登录后验证
docker --version
docker compose version
```

**步骤二：安装 NVIDIA Container Toolkit（需要 GPU 训练时）**

```bash
# 添加 NVIDIA 仓库
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sudo sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 安装
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# 配置 Docker 使用 NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 验证 GPU 在容器内可用
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

**步骤三：部署 SkyEdge AI**

```bash
# 克隆仓库
git clone https://github.com/AirAI-Lab/edge_infer_cloud.git
cd edge_infer_cloud

# 方式 A: 一键脚本部署（推荐）
cd deployment/docker
chmod +x deploy.sh
./deploy.sh --init       # 首次部署：生成 .env、初始化存储、启动服务
./deploy.sh --gpu        # 完整平台（含 GPU 训练/推理）

# 方式 B: docker compose profiles 精细控制
docker compose --profile gpu up -d                          # 模式 A: 纯推理（2 容器）
docker compose --profile standard up -d                     # 模式 B: 推理+管理（8 容器）
docker compose --profile standard --profile gpu up -d       # 模式 C: 完整平台（10 容器）
```

> **生产环境推荐**：先执行 `./deploy.sh --init`（首次），后续用 `./deploy.sh --gpu`

> **首次部署** `--init` 会自动生成 `.env`（含随机 API Key）、初始化 SeaweedFS bucket、等待数据库就绪。

### 2.2 管理命令

```bash
./deploy.sh --status     # 查看服务状态
./deploy.sh --logs       # 查看后端日志
./deploy.sh --logs nginx # 查看 nginx 日志
./deploy.sh --stop       # 停止所有服务
./deploy.sh --rebuild    # 重新构建镜像并部署（代码更新后）
./deploy.sh --init       # 首次部署初始化
./deploy.sh --backup     # 备份数据库
./deploy.sh --restore backup.sql.gz  # 恢复数据库
./deploy.sh --help       # 查看所有命令
```

### 2.3 配置开机自启（systemd）

```bash
# 复制服务文件
sudo cp deployment/docker/systemd/edge-cloud.service /etc/systemd/system/

# 按实际安装路径修改
sudo sed -i "s|/opt/edge_cloud|$(cd ../.. && pwd)|g" /etc/systemd/system/edge-cloud.service

# 启用并启动
sudo systemctl daemon-reload
sudo systemctl enable edge-cloud    # 开机自启
sudo systemctl start edge-cloud

# 管理
sudo systemctl status edge-cloud
sudo systemctl stop edge-cloud
sudo systemctl restart edge-cloud
journalctl -u edge-cloud -f         # 查看日志
```

---

## 方式三：从 Windows 迁移到 Linux

如果当前在 Windows Docker Desktop 上运行，迁移到 Linux 服务器的步骤：

### 3.1 导出数据

```bash
# 在 Windows 上执行：导出数据库
docker exec edge_cloud_postgres pg_dump -U edge_user edge_cloud > backup.sql

# 导出 Webhook 配置等（可选）
docker exec edge_cloud_postgres pg_dump -U edge_user edge_cloud --table=webhook_configs --table=alert_rules > config_backup.sql
```

### 3.2 传输代码到 Linux

```bash
# 方式一：rsync（推荐，增量同步）
rsync -avz --exclude='.git' --exclude='node_modules' --exclude='.venv' \
    ./edge_infer_cloud/ user@linux-server:/opt/edge_cloud/

# 方式二：scp
scp -r edge_infer_cloud user@linux-server:/opt/

# 方式三：git clone（推荐）
ssh user@linux-server
git clone https://github.com/AirAI-Lab/edge_infer_cloud.git /opt/edge_cloud
```

### 3.3 在 Linux 上部署并恢复数据

```bash
# 部署（选择合适的模式）
cd /opt/edge_cloud/deployment/docker
chmod +x deploy.sh

# 模式 A: 纯推理（仅 EMQX + GPU 训练，第三方通过 MQTT 获取结果）
docker compose --profile gpu up -d

# 模式 C: 完整平台（管理 + GPU 推理）
./deploy.sh --gpu

# 恢复数据（模式 B/C 需要，模式 A 无数据库）
cat backup.sql | docker exec -i edge_cloud_postgres psql -U edge_user -d edge_cloud
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
# 版本号（用于镜像 tag）
VERSION=1.0.0

# 数据库密码（生产环境请修改）
PG_PASSWORD=edge_pass

# EMQX 管理面板密码
EMQX_PASSWORD=admin123456

# API 认证密钥（第三方调用 REST API 时携带 X-API-Key header）
# 生产环境务必修改为强密钥，首次 --init 会自动生成
API_KEY=edge-cloud-api-key-change-me
```

> 运行 `./deploy.sh --init` 会自动生成 `.env` 并填充随机 API Key。

---

## 常见问题

**Q: 如何选择开发模式还是生产模式？**
- 开发调试用 `docker-compose.yml`（开发模式）
- 正式部署用 `docker-compose.prod.yml`（生产模式）
- 两者不能同时运行（端口冲突），必须先停一个再启另一个

**Q: 在 Windows Docker Desktop 上能运行生产模式吗？**
- 可以。生产模式只是换了镜像和配置，Docker Engine 是一样的
- 用于验证构建产物是否正确，但 I/O 性能仍受 WSL2 虚拟化影响
- 正式部署建议迁移到 Linux 服务器

**Q: 如何更新代码后重新部署？**
- 开发模式：修改代码后自动热重载
- 生产模式：`./deploy.sh --rebuild`

**Q: 训练/推理服务怎么启动？**
- 训练服务需要 NVIDIA GPU 和 nvidia-container-toolkit
- 使用 `./deploy.sh --gpu` 启动，或 `docker compose --profile gpu up -d`
- 没有 GPU 的服务器不需要启动训练服务，使用 `--profile standard` 即可

**Q: 第三方只需要推理结果，怎么最小化部署？**
- 仅需 2 个容器：EMQX（消息总线）+ Training（GPU 推理）
- 命令：`docker compose --profile gpu up -d`
- 第三方通过 MQTT 订阅 `results/#` 和 `alerts/#` 获取归一化结果
- 无需数据库、后端、前端

**Q: 新的 Linux 服务器部署流程一样吗？**
- 完全一样。只需先安装 Docker（`curl -fsSL https://get.docker.com | sh`），然后执行 `./deploy.sh`
- Docker 的核心优势就是跨平台一致性：Windows、Ubuntu、CentOS 部署命令完全相同
- 有 GPU 的服务器额外安装 nvidia-container-toolkit 即可

**Q: 数据会丢失吗？**
- Docker Volume 数据在 `docker compose down` 时不会丢失
- 只有 `docker compose down -v`（带 -v 参数）才会删除数据卷
- 迁移前建议 `pg_dump` 备份数据库
