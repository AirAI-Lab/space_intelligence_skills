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

### Windows + WSL2 vs Linux 服务器

| 对比 | Windows + WSL2 | Linux 服务器 |
|------|----------------|-------------|
| Docker 安装 | WSL2 Ubuntu 内安装 docker-ce | `curl get.docker.com \| sh` |
| 容器运行位置 | WSL2 内核（接近原生） | 直接在宿主机内核 |
| 磁盘 I/O | WSL2 原生文件系统接近原生；/mnt/ 跨文件系统慢 ~30% | 原生性能 |
| GPU 支持 | nvidia-container-toolkit 直通 | nvidia-container-toolkit 原生支持 |
| 适用场景 | 开发调试 | 正式部署 |
| 部署命令 | **完全相同** | **完全相同** |

**推荐路径**：
```
开发阶段 → Windows + WSL2 开发模式（写代码、调代码）
         → Windows + WSL2 生产模式（验证构建产物是否正确）
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

## 方式一：Windows + WSL2 部署

Windows 开发机通过 WSL2 Ubuntu 内安装 docker-ce 运行容器化服务。

### 1.1 环境准备

**1) 配置 WSL2 资源**

在 Windows 用户目录创建 `%USERPROFILE%\.wslconfig`：

```ini
[wsl2]
memory=24GB
processors=8
swap=8GB
localhostForwarding=true
[experimental]
autoMemoryReclaim=gradual
```

> 修改后需 `wsl --shutdown` 重启 WSL2。

**2) 安装 docker-ce**

```bash
wsl --start Ubuntu
# WSL2 内执行：
sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg

# 添加 Docker GPG key 和仓库
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 将当前用户加入 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 启动 Docker（WSL2 内非 systemd）
sudo service docker start

# 验证
docker --version
docker compose version
```

> **从 Docker Desktop 迁移？** 如果之前安装过 Docker Desktop，需清除其残留代理配置：
> ```bash
> sudo rm -rf /etc/systemd/system/docker.service.d
> echo '{}' > ~/.docker/config.json
> sudo service docker restart
> ```
> 否则 Docker 会尝试连接 Docker Desktop 的代理端口导致镜像拉取失败。

**3) 安装 NVIDIA Container Toolkit（GPU 直通）**

```bash
# 添加 NVIDIA 仓库
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 安装并配置
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo service docker restart

# 验证 GPU 直通
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
```

### 1.2 克隆项目并配置

**推荐在 WSL2 原生文件系统克隆**（I/O 性能远优于 `/mnt/d/`）：

```bash
cd ~
git clone https://github.com/AirAI-Lab/edge_infer_cloud.git
cd edge_infer_cloud
```

**模型权重通过符号链接共享**（避免重复下载 ~10GB）：

```bash
# 假设模型已在 Windows 的 D:\github\edge_infer_cloud\models\ 下
ln -s /mnt/d/github/edge_infer_cloud/models/C-RADIOv4-H ~/edge_infer_cloud/models/C-RADIOv4-H
ln -s /mnt/d/github/edge_infer_cloud/models/siglip2-giant-opt-patch16-384 ~/edge_infer_cloud/models/siglip2-giant-opt-patch16-384
ln -s /mnt/d/github/edge_infer_cloud/models/NVlabs_RADIO ~/edge_infer_cloud/models/NVlabs_RADIO
```

> **注意**：符号链接指向 `/mnt/d/`（Windows 磁盘），读取速度比 WSL2 原生文件系统慢约 30%，但对于模型加载（一次性读取）影响不大。

### 1.3 环境变量配置

`deploy.sh` 会自动检测 WSL2 并加载 `.env.wsl2`。确认 `deployment/docker/.env.wsl2` 内容正确：

```ini
# WSL2 外部资源路径（通过 /mnt/ 访问 Windows 磁盘）
EDGE_INFER_PATH=/mnt/d/github/edge_infer
EXTERNAL_DATA_PATH=/mnt/e/data

# WSL2 与 Windows 共享 IP（修改为本机局域网 IP）
CLOUD_API_URL=http://192.168.0.103:8081
```

### 1.4 一键启动（推荐）

项目提供了 Windows 一键启动脚本，自动完成：启动 Docker → 启动容器 → 等待就绪 → 配置端口转发。

```powershell
# PowerShell 管理员（右键以管理员身份运行）
cd D:\github\edge_infer_cloud\deployment\docker
.\start-wsl2.ps1
```

**首次部署**还需要初始化数据库：

```bash
# 在 WSL2 内执行（仅首次）
wsl -d Ubuntu
cd ~/edge_infer_cloud/deployment/docker
docker exec -i edge_cloud_postgres psql -U edge_user -d edge_cloud \
    < ../../backend/src/main/resources/schema.sql
```

> **重要**：首次部署或 `docker compose down -v` 后必须执行建表步骤，否则前端页面会报 500 错误。

**其他命令**：

```powershell
.\start-wsl2.ps1 -Status      # 查看服务状态和端口转发
.\start-wsl2.ps1 -Stop        # 停止所有服务
.\start-wsl2.ps1 -Rebuild     # 重新构建 training 镜像
.\start-wsl2.ps1 -ResetProxy  # 重置端口转发（WSL2 重启后 IP 变化时使用）
```

### 1.4.1 手动启动（不使用脚本）

```bash
# 在 WSL2 内执行
wsl -d Ubuntu
sudo service docker start
cd ~/edge_infer_cloud/deployment/docker

# 首次构建 training 镜像（需要下载 CUDA 基础镜像 ~5GB + PyTorch，约 30 分钟）
HTTP_PROXY=http://172.28.192.1:29290 HTTPS_PROXY=http://172.28.192.1:29290 \
    docker compose --profile gpu build training

# 启动所有服务（10 容器）
docker compose --profile standard --profile gpu up -d

# 初始化数据库（首次部署必须执行）
sleep 15
docker exec -i edge_cloud_postgres psql -U edge_user -d edge_cloud \
    < ../../backend/src/main/resources/schema.sql
```

配置端口转发（管理员 PowerShell，使局域网 IP 可达）：

```powershell
# 获取 WSL2 IP
$wslIp = (wsl -d Ubuntu -- bash -c "hostname -I | awk '{print `$1}'").Trim()

# 添加端口转发
$ports = @(8081, 3000, 1883, 18083, 1935, 8089, 8333, 8888, 5001, 5002, 5432, 6379, 8889)
foreach ($port in $ports) {
    netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wslIp
}
```

> **注意**：WSL2 重启后 IP 可能变化，需要重新执行端口转发，或使用 `.\start-wsl2.ps1` 自动处理。
| SeaweedFS | — | ✓ | ✓ |
| Portal | — | ✓ | ✓ |

> **模式 A（纯推理）**：EMQX 始终启动作为消息总线。第三方通过 MQTT 订阅 `results/#` 和 `alerts/#` 获取归一化推理结果。

**访问地址**：

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8081/api/v1 |
| EMQX 面板 | http://localhost:18083 |
| 文件存储 | http://localhost:8333 |

**验证**：

```bash
curl http://localhost:8081/actuator/health
wsl -d Ubuntu -- docker exec edge_cloud_training nvidia-smi
```

### 1.5 生产模式（验证构建产物）

用于在开发机上验证构建是否正确。

```bash
cd ~/edge_infer_cloud/deployment/docker

# 1. 先停掉开发模式
docker compose --profile standard --profile gpu down

# 2. 构建并启动生产模式
docker compose -f docker-compose.prod.yml up -d --build

# 3. 查看状态
docker compose -f docker-compose.prod.yml ps
```

**生产模式验证完成后**，输出应该是：
```
http://localhost/           → 前端管理界面（统一入口）
http://localhost/api/v1/    → REST API
http://localhost/emqx/      → EMQX 管理面板
```

### 1.5 网络注意事项

**本机访问**：通过 `localhost` 直接访问，WSL2 的 `localhostForwarding=true` 自动转发。

**局域网访问**（Jetson 等外部设备）：WSL2 Docker 端口不直接暴露到 Windows 局域网 IP，需要 `netsh portproxy` 转发。`start-wsl2.ps1` 脚本会自动配置。

**首次部署需要配置 Windows 防火墙**（管理员 PowerShell，仅首次）：

```powershell
# 放行容器端口
New-NetFirewallRule -DisplayName "Edge Cloud Platform" -Direction Inbound -Protocol TCP `
    -LocalPort 8081,3000,1883,18083,1935,8089,8333,8888,5001,5002,5432,6379,8889 `
    -Action Allow -Profile Any

# 放行 WSL2 Hyper-V 流量
Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction Allow
```

**代理配置**：

WSL2 内 Docker 引擎不继承宿主机的代理设置。如果需要代理：

```bash
# Docker daemon 代理（systemd 方式）
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/proxy.conf <<EOF
[Service]
Environment="HTTP_PROXY=http://172.28.192.1:29290"
Environment="HTTPS_PROXY=http://172.28.192.1:29290"
EOF

# 或 WSL2 非 systemd 方式：在启动前设置
export HTTP_PROXY=http://172.28.192.1:29290
export HTTPS_PROXY=http://172.28.192.1:29290
sudo service docker start
```

> `172.28.192.1` 是 WSL2 默认网关（宿主机 IP），可通过 `cat /etc/resolv.conf | grep nameserver` 查看实际值。

**npm 国内镜像**：

前端容器 `npm install` 默认使用 npmmirror 镜像（已内置在 docker-compose.yml）。

### 1.7 WSL2 日常操作

```bash
# 每次进入 WSL2 需要启动 Docker
sudo service docker start

# 查看服务状态
cd ~/edge_infer_cloud/deployment/docker
docker compose ps

# 查看日志
docker compose logs -f backend
docker compose logs -f training

# 重启某个服务
docker compose restart backend

# 停止所有服务
docker compose --profile standard --profile gpu down

# 停止并清除数据卷（慎用）
docker compose --profile standard --profile gpu down -v
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
docker compose --profile standard --profile gpu up -d       # 模式 C: 完整平台（9 容器）
```

> **生产环境推荐**：先执行 `./deploy.sh --init`（首次），后续用 `./deploy.sh --gpu`

> **首次部署** `--init` 会自动生成 `.env`（含随机 API Key）、初始化 SeaweedFS bucket、等待数据库就绪。

**步骤四：初始化数据库（首次部署必须）**

```bash
# 等待 PostgreSQL 就绪后执行建表
sleep 15
docker exec -i edge_cloud_postgres psql -U edge_user -d edge_cloud \
    < ../../backend/src/main/resources/schema.sql
```

> **重要**：首次部署或 `docker compose down -v` 后必须执行此步骤，否则前端页面报 500 错误。后续重启不需要重复执行。

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

## 从 Windows 迁移到 Linux 服务器

开发阶段在 Windows + WSL2（方式一）完成后，部署到 Linux 生产服务器（方式二）时的数据迁移步骤：

```bash
# 1. 在 WSL2 内导出数据库
docker exec edge_cloud_postgres pg_dump -U edge_user edge_cloud > backup.sql

# 2. 传输代码（推荐 git clone，最简洁）
ssh user@linux-server
git clone https://github.com/AirAI-Lab/edge_infer_cloud.git /opt/edge_cloud

# 3. 在 Linux 上按方式二部署后恢复数据
cd /opt/edge_cloud/deployment/docker
./deploy.sh --init
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

**Q: 如何选择 Windows + WSL2 还是 Linux 服务器？**
- 开发调试用 Windows + WSL2（代码在本地，热重载方便）
- 正式部署用 Linux 服务器（性能最优，systemd 开机自启）
- 两者的 Docker 命令完全相同

**Q: 如何选择开发模式还是生产模式？**
- 开发调试用 `docker-compose.yml`（开发模式）
- 正式部署用 `docker-compose.prod.yml`（生产模式）
- 两者不能同时运行（端口冲突），必须先停一个再启另一个

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
- Docker 的核心优势就是跨平台一致性：Windows WSL2 和 Linux 服务器部署命令完全相同
- 有 GPU 的服务器额外安装 nvidia-container-toolkit 即可

**Q: 数据会丢失吗？**
- Docker Volume 数据在 `docker compose down` 时不会丢失
- 只有 `docker compose down -v`（带 -v 参数）才会删除数据卷
- 迁移前建议 `pg_dump` 备份数据库
