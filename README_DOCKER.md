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
| training | CUDA 12.8 + PyTorch | 5002 | 训练服务 + 云端推理（需GPU） |

其中 `training` 需要 NVIDIA GPU，通过 `--profile gpu` 启动。云端推理在 Training 容器中运行，无需独立容器。

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
docker compose logs -f training

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
training ──→ mlflow ──→ (独立)
         ├──→ seaweedfs
         ├──→ emqx (云端推理 MQTT)
         └──→ backend (推理结果上报)
```

- `backend` 等待 postgres、redis、emqx、seaweedfs 就绪后启动
- `frontend` 等待 backend 启动
- `training` 仅在 `--profile gpu` 时启动，同时承担训练和云端推理职责

---

## 12. 前端功能概览

前端基于 **Vue 3 + Element Plus + ECharts**，提供以下页面：

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | 首页仪表盘 | 设备在线数、数据集/模型/训练任务统计、推理趋势图、最近告警、在线设备列表（CPU/GPU/内存） |
| `/device` | 设备管理 | 设备列表（搜索/状态过滤）、注册设备、设备详情（实时指标、推理结果 tab） |
| `/data` | 数据集管理 | 数据集列表、上传数据集、数据集详情（图片预览、标注信息） |
| `/training` | 训练任务 | 创建训练任务（选择数据集/模型/超参数）、启动/暂停/停止训练、实时 metrics 图表、训练日志 |
| `/model` | 模型管理 | 模型列表、模型详情（版本、文件、指标）、模型格式转换（PT → ONNX → Engine） |
| `/ota` | OTA 升级 | 创建升级任务（选择设备/模型/版本）、实时进度追踪、暂停/恢复/重试/回滚 |
| `/deployment` | 部署记录 | 部署历史记录、部署状态 |
| `/inference` | 推理结果 | 边缘+云端推理结果列表（分页/过滤）、图片预览（含分割标注）、清空数据 |
| `/alerts` | 告警中心 | 告警统计卡片（严重/警告/信息）、24 小时趋势图、告警列表（图片预览）、清空数据 |
| `/alert-rules` | 告警规则 | 创建/编辑/删除告警规则（条件类型：面积阈值/置信度/检出数量） |
| `/webhooks` | Webhook 管理 | 创建/编辑/删除 Webhook（事件过滤、自定义 Header、触发统计） |

首页仪表盘每 60 秒自动刷新。

---

## 13. 训练服务

### 13.1 训练服务架构

训练服务由 **后端 API（Java）** + **训练引擎（Python/YOLOv8）** + **MLflow 实验管理** 三部分组成。

训练容器 `edge_cloud_training` 已包含 PyTorch + CUDA + Ultralytics，通过 `--profile gpu` 启动。

### 13.2 训练工作流

```
1. 前端创建训练任务 → POST /api/v1/training
2. 启动训练 → POST /api/v1/training/{job_id}/start
3. 后端调用训练容器 API → POST http://training:5002/train
4. 训练容器异步执行 YOLOv8 训练
5. 进度回调 → POST /api/v1/training/internal/{job_id}/progress（每 5 秒）
6. 训练完成 → 上传 best.pt 到 S3，回调后端更新状态
7. 前端通过轮询或 WebSocket 展示进度
```

### 13.3 创建训练任务

通过前端 `/training` 页面操作，或通过 API：

```bash
curl -X POST http://localhost:8081/api/v1/training \
  -H "Content-Type: application/json" \
  -d '{
    "jobName": "施工安全检测模型 v1",
    "datasetSource": "backend",
    "datasetId": "DS001",
    "baseModel": "yolov8n.pt",
    "trainingType": "FULL_TRAINING",
    "epochs": 100,
    "batchSize": 16,
    "imgSize": 640,
    "optimizer": "AdamW",
    "lr0": 0.01,
    "workers": 8
  }'
```

**数据集来源**（`datasetSource`）：

| 来源 | 说明 |
|------|------|
| `backend` | 从前端上传的数据集中选择（数据集管理页面） |
| `url` | 从远程 URL 下载（支持 Git 仓库） |
| `local` | 使用容器内本地路径 |

**关键超参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `epochs` | 100 | 训练轮数 |
| `batchSize` | 16 | 批大小 |
| `imgSize` | 640 | 输入图像尺寸 |
| `optimizer` | AdamW | 优化器（SGD / Adam / AdamW） |
| `lr0` | 0.01 | 初始学习率 |
| `patience` | 30 | 早停耐心值 |

### 13.4 训练管理 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/training` | POST | 创建训练任务 |
| `/api/v1/training/{id}/start` | POST | 启动训练 |
| `/api/v1/training/{id}/stop` | POST | 停止训练 |
| `/api/v1/training/{id}/pause` | POST | 暂停训练 |
| `/api/v1/training/{id}/resume` | POST | 恢复训练（支持智能参数优化） |
| `/api/v1/training/jobs` | GET | 查询训练任务列表 |
| `/api/v1/training/{id}` | GET | 查询任务详情 |
| `/api/v1/training/{id}/metrics` | GET | 查询训练指标（mAP、Loss 等） |
| `/api/v1/training/{id}/logs` | GET | 查询训练日志 |
| `/api/v1/training/{id}/create-model` | POST | 训练完成后创建模型记录 |

### 13.5 训练输出

训练完成后产出以下文件（存储在 S3/SeaweedFS）：

```
models/{model_id}/
├── best.pt              # 最优模型权重
├── best.onnx            # ONNX 导出（可选）
├── model_config.json    # 模型元信息（类别、输入尺寸、指标）
├── classes.txt          # 类别名称
└── data.yaml            # 数据集配置
```

### 13.6 智能恢复训练

恢复训练（Resume）时，系统自动分析历史训练状态：

| 训练阶段 | 趋势 | 策略 |
|---------|------|------|
| 中期 | 稳定/停滞 | 学习率 ×0.5，增大 patience |
| 中期 | 下降 | 学习率 ×0.2，恢复训练 |
| 后期 | 上升 | 学习率 ×0.3，微调 |
| 后期 | 停滞 | 学习率 ×0.1，关闭 Mosaic 增强 |
| 收敛 | mAP > 0.7 且稳定 | 建议停止训练 |

### 13.7 MLflow 实验管理

训练指标自动记录到 MLflow：

- **实验名称**：`yolov8_{dataset_id}`
- **记录参数**：数据集、模型、超参数
- **记录指标**：mAP50、mAP50-95、Precision、Recall、Loss

访问 `http://localhost:5001` 查看 MLflow UI。

---

## 14. OTA 升级

### 14.1 OTA 升级架构

```
前端创建任务 → 后端 OTA Service → MQTT 下发命令 → 边缘设备执行升级
                                   ↓
                              下载 → 验证 → 转换 → 应用
                                   ↓
                              MQTT 上报状态 → 后端更新进度 → 前端实时展示
```

### 14.2 OTA 升级流程

**云端操作**：

1. 前端 `/ota` 页面创建升级任务（选择目标设备 + 模型版本）
2. 后端生成下载 URL，通过 MQTT 发送升级命令到 `device/{device_id}/ota/command`
3. 前端实时展示各设备升级进度

**边缘设备执行**（C++ OTA Handler）：

| 阶段 | 进度 | 说明 |
|------|------|------|
| 下载 | 0-25% | 从云端下载 ONNX 模型文件 |
| 验证 | 25-30% | MD5 校验文件完整性 |
| 转换 | 30-90% | ONNX → TensorRT Engine（FP16 优化） |
| 应用 | 90-100% | 热加载新模型 |
| 完成 | 100% | 上报成功状态 |

### 14.3 OTA 管理 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/ota/tasks` | POST | 创建升级任务 |
| `/api/v1/ota/tasks/{id}/start` | POST | 启动升级 |
| `/api/v1/ota/tasks/{id}/pause` | POST | 暂停升级 |
| `/api/v1/ota/tasks/{id}/resume` | POST | 恢复升级 |
| `/api/v1/ota/tasks/{id}/retry` | POST | 重试失败设备 |
| `/api/v1/ota/tasks/{id}/devices/{did}/rollback` | POST | 回滚单台设备 |
| `/api/v1/ota/tasks/{id}/devices/{did}/replace-model` | POST | 热替换模型（不重启） |
| `/api/v1/ota/tasks` | GET | 查询任务列表 |
| `/api/v1/ota/tasks/{id}` | GET | 查询任务详情 |
| `/api/v1/ota/tasks/{id}/devices` | GET | 查询设备升级状态 |

### 14.4 MQTT 通信协议

| Topic | 方向 | 说明 |
|-------|------|------|
| `device/{id}/ota/command` | 云→边 | 升级命令（task_id, model_url, version） |
| `device/{id}/ota/status` | 边→云 | 升级进度（progress, stage, error） |
| `device/{id}/model/reload` | 云→边 | 模型热加载触发 |

### 14.5 创建 OTA 升级示例

```bash
# 创建升级任务（指定设备和模型）
curl -X POST http://localhost:8081/api/v1/ota/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "taskName": "施工安全模型升级 v2",
    "modelId": "M_JOB20241228...",
    "version": "2.0.0",
    "deviceIds": ["jetson_orin_001"],
    "strategy": "IMMEDIATE"
  }'

# 启动升级
curl -X POST http://localhost:8081/api/v1/ota/tasks/{task_id}/start
```

---

## 15. 设备管理

### 15.1 设备注册

设备通过两种方式注册：

**方式 1：边缘设备自动注册**（推荐）

边缘设备启动后自动发送心跳，后端检测到新设备自动创建记录。

**方式 2：手动注册**

```bash
curl -X POST http://localhost:8081/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "jetson_orin_001",
    "deviceName": "1号施工区域 Jetson",
    "deviceType": "JETSON_ORIN",
    "ipAddress": "192.168.0.107"
  }'
```

### 15.2 设备状态

| 状态 | 说明 |
|------|------|
| `ONLINE` | 正常发送心跳 |
| `OFFLINE` | 超过 5 分钟未收到心跳 |
| `UPGRADING` | OTA 升级中 |
| `ERROR` | 升级失败或设备异常 |

### 15.3 心跳上报

边缘设备每 30 秒上报心跳，包含系统指标：

```json
{
  "device_id": "jetson_orin_001",
  "cpu_usage": 45.2,
  "gpu_usage": 78.3,
  "memory_usage": 62.1,
  "disk_usage": 35.0,
  "temperature": 58.5,
  "fps": 28.5,
  "model_id": "M001",
  "model_version": "1.0.0"
}
```

### 15.4 设备管理 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/devices` | GET | 设备列表（分页、状态过滤） |
| `/api/v1/devices` | POST | 注册设备 |
| `/api/v1/devices/{id}` | GET | 设备详情 |
| `/api/v1/devices/{id}` | PUT | 更新设备信息 |
| `/api/v1/devices/{id}` | DELETE | 删除设备 |
| `/api/v1/devices/stats` | GET | 设备统计（在线/离线/升级中） |
| `/api/v1/edge/heartbeat` | POST | 边缘心跳上报 |
| `/api/v1/edge/register` | POST | 边缘设备自注册 |

---

## 16. 文件存储

### 16.1 存储模式

系统支持两种存储后端，通过 `FILE_STORAGE_TYPE` 环境变量切换：

| 模式 | 配置值 | 说明 |
|------|--------|------|
| S3 对象存储（推荐） | `s3` | SeaweedFS / 阿里云 OSS / 腾讯云 COS |
| 本地文件系统 | `local` | 存储在容器内 `/app/data/files` |

Docker Compose 默认使用 S3 模式（SeaweedFS）。

### 16.2 文件管理 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/files/upload` | POST | 上传单个文件（`category` 参数分类） |
| `/api/v1/files/upload/batch` | POST | 批量上传 |
| `/api/v1/files/download?key=...` | GET | 下载文件（S3 模式） |
| `/api/v1/files/download?path=...` | GET | 下载文件（本地模式） |
| `/api/v1/files/delete` | DELETE | 删除文件 |
| `/api/v1/files/list?category=...` | GET | 按分类列出文件 |
| `/api/v1/files/info` | GET | 查询存储类型 |

### 16.3 SeaweedFS 管理

访问 `http://localhost:8888` 查看 SeaweedFS 管理界面。

推理结果图片自动存储在 `inference/` 分类下。

---

## 17. 告警与 Webhook

### 17.1 告警规则

通过 `/alert-rules` 页面或 API 创建告警规则：

```bash
# 示例：裸土面积超过 5% 时触发告警
curl -X POST http://localhost:8081/api/v1/alert-rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "裸土未覆盖告警",
    "source": "cloud",
    "className": "bare_soil_uncovered",
    "conditionType": "area_threshold",
    "thresholdValue": 0.05,
    "alertLevel": "warning",
    "triggerCloudInfer": false
  }'
```

**条件类型**（`conditionType`）：

| 类型 | 说明 | 适用来源 |
|------|------|---------|
| `area_threshold` | 分割面积占比超过阈值 | 云端（C-RADIOv4） |
| `confidence_threshold` | 检测置信度超过阈值 | 边缘（YOLOv8） |
| `count_threshold` | 检出数量超过阈值 | 边缘/云端 |

**告警级别**：`critical`（严重）、`warning`（警告）、`info`（信息）

### 17.2 Webhook 集成

通过 `/webhooks` 页面或 API 配置 Webhook，将告警推送到外部平台（如智飞）：

```bash
# 创建 Webhook
curl -X POST http://localhost:8081/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "智飞平台告警推送",
    "url": "https://external-platform.example.com/api/alerts",
    "secret": "my-secret-key",
    "events": "alert.critical,alert.warning",
    "headers": "{\"Authorization\": \"Bearer xxx\"}"
  }'
```

**事件类型**：
- `alert.critical` / `alert.warning` / `alert.info` — 告警事件
- `alert.*` — 所有告警（通配符）
- `result.edge` / `result.cloud` — 推理结果事件

**Webhook 推送格式**：

```json
{
  "event": "alert.critical",
  "timestamp": "2026-04-28T10:30:00",
  "data": { /* 推理结果完整信息 */ }
}
```

---

## 18. 数据库

### 18.1 表结构总览

| 表名 | 类型 | 说明 |
|------|------|------|
| `devices` | 普通表 | 设备信息和在线状态 |
| `models` | 普通表 | 模型元数据 |
| `model_deployments` | 普通表 | 模型部署历史 |
| `training_jobs` | 普通表 | 训练任务记录 |
| `training_metrics` | **超表** | 训练指标时序数据 |
| `inference_results` | **超表** | 推理结果时序数据 |
| `ota_tasks` | 普通表 | OTA 升级任务 |
| `device_upgrade_status` | 普通表 | 设备升级状态 |
| `alert_rules` | 普通表 | 告警规则配置 |
| `webhook_configs` | 普通表 | Webhook 配置 |
| `datasets` | 普通表 | 数据集元数据 |

其中 `training_metrics` 和 `inference_results` 使用 TimescaleDB 超表，自动按时间分区。

### 18.2 首次建表

首次部署需手动建表（后端 JPA 不会自动执行 schema.sql）：

```bash
docker exec -it edge_cloud_postgres psql -U edge_user -d edge_cloud
```

在 psql 中执行 `backend/src/main/resources/schema.sql` 中的建表语句，或逐个执行：

```sql
-- 启用 TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 推理结果表（超表）
CREATE TABLE IF NOT EXISTS inference_results (
    id BIGSERIAL, time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id VARCHAR(50) NOT NULL, source VARCHAR(20) NOT NULL,
    model_name VARCHAR(200), task_type VARCHAR(50), frame_id BIGINT,
    image_url VARCHAR(500), result_json JSONB,
    alert_level VARCHAR(20), alert_message TEXT,
    inference_time_ms FLOAT, detection_count INT DEFAULT 0,
    summary_text VARCHAR(500), PRIMARY KEY (time, id)
);
SELECT create_hypertable('inference_results', 'time', if_not_exists => TRUE);

-- 告警规则表
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL,
    device_id VARCHAR(50), source VARCHAR(20), class_name VARCHAR(100),
    condition_type VARCHAR(50) DEFAULT 'area_threshold',
    threshold_value FLOAT DEFAULT 0.01, alert_level VARCHAR(20) DEFAULT 'warning',
    trigger_cloud_infer BOOLEAN DEFAULT FALSE, enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Webhook 配置表
CREATE TABLE IF NOT EXISTS webhook_configs (
    id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL,
    url VARCHAR(500) NOT NULL, secret VARCHAR(200),
    events VARCHAR(500), headers TEXT,
    enabled BOOLEAN DEFAULT TRUE, trigger_count INT DEFAULT 0,
    last_trigger_at TIMESTAMP, last_error VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

\q
```

> 后续重启不需要重新建表。其他表（devices, models, training_jobs 等）由 JPA 自动创建。

---

## 19. 云边协同推理完整演示流程

本节给出从零开始验证云边协同推理的完整步骤。以 **施工安全监测** (`construction_safety`) 为示例场景。

### 19.1 环境假设

| 角色 | IP | 说明 |
|------|-----|------|
| 云端服务器 (本机) | `192.168.0.103` | GPU 服务器，运行 Docker 服务 |
| 边缘设备 (Jetson) | `192.168.0.107` | Jetson Orin，运行 edge_infer |

> 如果只有一台机器，可以在云端同时运行边缘和云端推理（仅限验证功能）。

### 19.2 云边协同架构

```
摄像头/视频 ──RTSP/RTMP──► Jetson (107) 边缘推理
                               │  YOLOv8: helmet/head/person/vest 实时检测 (~30fps)
                               │
                               ├─ MQTT → 后端 → 前端展示（实时检测）
                               │
                               └─ 每 3s 编码 JPEG ──MQTT──► 云端 (103) GPU 推理
                                  device/{id}/cloud/frame     │  C-RADIOv4: 裸土/积水/扬尘/材料堆放
                                                              │  REST POST → 后端 → 前端展示
```

**边缘负责实时检测，云端负责非实时零样本分割，两者是并列业务。**

云端推理脚本 `radio_infer_server.py` 支持 4 种运行模式：

| 模式 | 帧来源 | 说明 |
|------|--------|------|
| **自动**（默认） | 检测 MQTT/RTMP 可达性自动选择 | 零配置，推荐 |
| **MQTT** | 边缘设备转发 JPEG 帧 | 生产环境 |
| **RTMP 直连** | 云端直接拉 RTMP 原始流 | 开发演示，无边缘设备 |
| **双通道** | MQTT 为主 + RTMP 补充 | 过渡期双重保障 |

**自动降级**：MQTT 模式运行中连续 30 秒无帧 → 自动从 YAML 配置的 `fallback_stream` 拉原始视频流 → MQTT 恢复后自动切回。更换场地只需修改 YAML，无需改命令行。

**数据流通道**：

| 通道 | 协议 | 说明 |
|------|------|------|
| 边缘 → 后端 | MQTT + REST | 推理结果上报（双通道冗余） |
| 边缘 → 云端 | MQTT | JPEG 帧转发（每 3 秒，~100KB/帧） |
| 云端 → 后端 | REST | 分割结果上报（含标注图片） |
| 后端 → 前端 | WebSocket | 实时推送 |

### 19.3 Step 1：启动云端基础服务

在云端服务器 (103) 上执行：

```powershell
cd D:\github\edge_infer_cloud\deployment\docker

# 启动基础设施 (数据库 + 缓存 + MQTT + 存储)
docker compose up -d postgres redis emqx mlflow seaweedfs portal

# 等待 PostgreSQL 就绪
Start-Sleep -Seconds 20

# 启动后端和前端
docker compose up -d backend frontend
```

等待后端就绪（首次启动需下载 Maven 依赖，约 3 分钟）：

```bash
docker compose logs -f backend
# 看到 "Started EdgeInferCloudApplication" 即可 Ctrl+C 退出
```

**验证**：

```bash
docker compose ps
# 应看到 8 个容器均为 Up:
# edge_cloud_postgres, edge_cloud_redis, edge_cloud_emqx,
# edge_cloud_seaweedfs, edge_cloud_mlflow, edge_cloud_portal,
# edge_cloud_backend, edge_cloud_frontend
```

### 19.4 Step 2：初始化数据库（首次部署）

首次部署需要手动创建推理结果表（后端 JPA 不会自动执行 schema.sql）：

```bash
docker exec -it edge_cloud_postgres psql -U edge_user -d edge_cloud
```

在 psql 中执行：

```sql
-- 启用 TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 推理结果表
CREATE TABLE IF NOT EXISTS inference_results (
    id BIGSERIAL,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id VARCHAR(50) NOT NULL,
    source VARCHAR(20) NOT NULL,
    model_name VARCHAR(200),
    task_type VARCHAR(50),
    frame_id BIGINT,
    image_url VARCHAR(500),
    result_json JSONB,
    alert_level VARCHAR(20),
    alert_message TEXT,
    inference_time_ms FLOAT,
    detection_count INT DEFAULT 0,
    summary_text VARCHAR(500),
    PRIMARY KEY (time, id)
);
SELECT create_hypertable('inference_results', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_ir_device_time ON inference_results(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_ir_alert_time ON inference_results(alert_level, time DESC) WHERE alert_level IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ir_result_json ON inference_results USING gin(result_json);

-- 告警规则表
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    device_id VARCHAR(50),
    model_name VARCHAR(200),
    source VARCHAR(20),
    class_name VARCHAR(100),
    condition_type VARCHAR(50) DEFAULT 'area_threshold',
    threshold_value FLOAT DEFAULT 0.01,
    alert_level VARCHAR(20) DEFAULT 'warning',
    trigger_cloud_infer BOOLEAN DEFAULT FALSE,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Webhook 配置表
CREATE TABLE IF NOT EXISTS webhook_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    secret VARCHAR(200),
    events TEXT,
    headers TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    trigger_count INT DEFAULT 0,
    last_trigger_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 退出
\q
```

> 后续重启不需要重新建表，仅在首次部署时执行。

### 19.5 Step 3：启动 RTMP 服务器 + 推流

#### 方式 A：使用推流脚本（推荐）

项目提供了 `scripts/push_stream.ps1` 一键推流脚本：

```powershell
# Windows PowerShell — 自动循环推流
powershell -ExecutionPolicy Bypass -File scripts\push_stream.ps1
```

脚本会自动检测 ffmpeg、显示视频信息、循环推流。可通过参数自定义：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\push_stream.ps1 `
    -VideoPath "D:\videos\my_video.mp4" `
    -RtmpUrl "rtmp://192.168.0.103:1935/stream/safety_cam"
```

#### 方式 B：手动推流

```powershell
# 先启动 RTMP 服务器
docker run --name rtmp-server -d -p 1935:1935 -p 8089:80 alfg/nginx-rtmp:latest

# Windows PowerShell — 循环推送施工安全视频
ffmpeg -re -stream_loop -1 `
    -i D:\github\edge_infer_cloud\models\construction_safety\data\construction_safety.mp4 `
    -c:v libx264 -preset veryfast -tune zerolatency `
    -g 15 -bf 0 `
    -f flv rtmp://192.168.0.103:1935/stream/safety_cam
```

```bash
# Linux/macOS
ffmpeg -re -stream_loop -1 \
    -i /path/to/construction_safety.mp4 \
    -c:v libx264 -preset ultrafast -tune zerolatency \
    -b:v 2000k -maxrate 2500k -bufsize 5000k \
    -f flv rtmp://192.168.0.103:1935/stream/safety_cam
```

> 如需推 USB 摄像头：`ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 ... -f flv rtmp://...`
>
> 如需推 RTSP 摄像头：`ffmpeg -rtsp_transport tcp -i rtsp://admin:pass@192.168.0.200:554/stream1 -c:v libx264 ... -f flv rtmp://...`

**验证推流**：

```bash
ffprobe rtmp://192.168.0.103:1935/stream/safety_cam
# 应显示视频流信息（分辨率、帧率、编码格式）
```

### 19.6 Step 4：启动云端推理

云端推理脚本内置防重复启动（自动终止旧实例），支持自动降级。

```powershell
# PowerShell（推荐）
docker exec edge_cloud_training python3 /app/radio_infer_server.py `
  --config /app/models/construction_safety/configs/construction_safety.yaml `
  --checkpoint /app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar `
  --radio-code /app/models/NVlabs_RADIO `
  --siglip2 /app/models/siglip2-giant-opt-patch16-384
```

```bash
# Git Bash（需加路径保护前缀）
MSYS_NO_PATHCONV=1 docker exec edge_cloud_training python3 /app/radio_infer_server.py \
  --config /app/models/construction_safety/configs/construction_safety.yaml \
  --checkpoint /app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar \
  --radio-code /app/models/NVlabs_RADIO \
  --siglip2 /app/models/siglip2-giant-opt-patch16-384
```

> **无需 `--stream`**：降级流地址从 YAML 配置文件的 `deployment.cloud.fallback_stream` 自动读取。更换场地只需改 YAML。传 `--stream` 可覆盖。

**预期日志**：

```
自动检测: MQTT ✓ → MQTT 模式                              ← 有边缘设备在线
RTMP 降级: 30s 无帧时自动切换到 rtmp://192.168.0.103/...   ← 自动降级已就绪
[1] jetson_orin_001 frame=1 (mqtt): ['bare_soil_uncovered'], 1 alerts, 120ms
```

**停止推理**：

```powershell
docker exec edge_cloud_training bash -c "pkill -f radio_infer_server"
```

### 19.7 Step 5：配置并启动边缘推理

在 Jetson (107) 上操作：

```bash
ssh nvidia@192.168.0.107

# 1. 编译 (如果还没有)
cd /home/nvidia/edge_infer
mkdir -p build && cd build
cmake .. -DUSE_TENSORRT=ON
make -j$(nproc)

# 2. 修改配置 — 将 input_uri 指向 RTMP 流
vi ~/edge_infer/config/framework_config.json
```

`config/framework_config.json` 关键配置：

```json
{
  "input_uri": "rtmp://192.168.0.103:1935/stream/safety_cam",
  "output_url": "rtmp://192.168.0.103:1935/stream/jetson_output",
  "enable_cloud_sync": true
}
```

`config/cloud_config.json` 关键配置：

```json
{
  "cloud": {
    "enabled": true,
    "api_base_url": "http://192.168.0.103:8081/api/v1",
    "device_id": "jetson_orin_001",
    "device_type": "JETSON_ORIN"
  },
  "mqtt": {
    "enabled": true,
    "broker_host": "192.168.0.103",
    "broker_port": 1883,
    "client_id": "jetson_orin_001"
  },
  "cloud_forward": {
    "enabled": true,
    "interval": 3,
    "quality": 70,
    "max_width": 960
  }
}
```

启动边缘推理：

```bash
cd /home/nvidia/edge_infer/build
./edge_framework
```

**预期日志**：

```
Framework LoadConfigs success
Framework Init: MQTT client connected to 192.168.0.103:1883
Framework Init: OTA handler initialized
Framework Start: input stream ready (first frame received)
Framework Start success
```

### 19.8 Step 6：验证完整数据流

所有服务启动后，逐一验证每个环节：

#### 验证 MQTT 通信

浏览器打开 EMQX Dashboard：`http://192.168.0.103:18083`（账号：admin / admin123456）

```
→ 菜单 "Connections"
  应看到连接: backend, jetson_orin_001, radio_infer_*

→ 菜单 "Subscriptions"
  应看到:
  - backend 订阅 device/+/inference/results
  - backend 订阅 device/+/ota/status
  - radio_infer_* 订阅 device/+/cloud/frame
```

#### 验证推理结果

```bash
# 查询所有推理结果
curl -s http://localhost:8081/api/v1/inference/results?page=1\&page_size=5 | python3 -m json.tool

# 仅查询边缘结果
curl -s "http://localhost:8081/api/v1/inference/results?page=1&page_size=5&source=edge" | python3 -m json.tool

# 仅查询云端结果
curl -s "http://localhost:8081/api/v1/inference/results?page=1&page_size=5&source=cloud" | python3 -m json.tool

# 告警查询
curl -s "http://localhost:8081/api/v1/inference/alerts?levels=critical,warning" | python3 -m json.tool

# 统计信息
curl -s http://localhost:8081/api/v1/inference/stats | python3 -m json.tool
```

#### 验证数据库

```bash
docker exec -it edge_cloud_postgres psql -U edge_user -d edge_cloud -c \
  "SELECT source, count(*), round(avg(inference_time_ms)::numeric,1) as avg_ms
   FROM inference_results
   WHERE time > NOW() - INTERVAL '10 minutes'
   GROUP BY source ORDER BY source;"
```

预期输出：

```
 source | count | avg_ms
--------+-------+--------
 cloud  |    20 |  120.5
 edge   |   300 |   25.3
```

#### 验证前端

浏览器打开 `http://192.168.0.103:3000`：

1. **首页** → 推理趋势图和最近告警
2. **推理结果** → 实时刷新边缘+云端结果列表
3. **告警中心** → 告警卡片和趋势柱状图
4. **设备管理** → 设备在线状态

### 19.9 配置告警规则（可选）

通过前端 `http://192.168.0.103:3000/alert-rules` 可视化配置，或通过 API：

```bash
# 裸土未覆盖告警 (云端分割面积 > 5%)
curl -X POST http://192.168.0.103:8081/api/v1/alert-rules \
  -H "Content-Type: application/json" \
  -d '{"name":"裸土未覆盖告警","source":"cloud","class_name":"bare_soil_uncovered","condition_type":"area_threshold","threshold_value":0.05,"alert_level":"warning"}'

# 未戴安全帽告警 (边缘检测)
curl -X POST http://192.168.0.103:8081/api/v1/alert-rules \
  -H "Content-Type: application/json" \
  -d '{"name":"未戴安全帽告警","source":"edge","class_name":"head","condition_type":"confidence_threshold","threshold_value":0.5,"alert_level":"critical"}'
```

### 19.10 导出推理结果（可选）

```bash
# 导出 CSV (Excel 兼容)
curl "http://192.168.0.103:8081/api/v1/inference/export?format=csv" -o inference_results.csv

# 导出 JSON
curl "http://192.168.0.103:8081/api/v1/inference/export?format=json" -o inference_results.json

# 按条件过滤导出
curl "http://192.168.0.103:8081/api/v1/inference/export?source=cloud&alert_level=critical&format=csv" -o critical_cloud_alerts.csv
```

### 19.11 一键演示脚本

项目提供了一键演示脚本 `scripts/demo_construction_safety.ps1`，自动完成 Step 3 ~ Step 6：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo_construction_safety.ps1
```

脚本会自动：
1. 检查后端服务是否运行
2. 启动 RTMP 服务器
3. 配置告警规则（6 条预设规则）
4. 启动 FFmpeg 推流（新窗口）
5. 构建并启动云端推理 Docker 容器

脚本执行完成后，只需在 Jetson 上手动启动边缘推理：

```bash
ssh nvidia@192.168.0.107
vi ~/edge_infer/config/framework_config.json   # 确认 input_uri
cd ~/edge_infer/build && ./edge_framework
```

### 19.12 常见问题排查

| 现象 | 排查命令 | 可能原因 |
|------|---------|---------|
| 前端看不到推理结果 | `docker compose logs backend \| grep "推理结果"` | 后端未收到 MQTT 消息 |
| EMQX 无连接 | `docker compose logs emqx` | EMQX 未启动或端口被占 |
| 云端推理模型加载失败 | `docker compose logs training` | 模型文件未挂载到容器 |
| `radio_infer_server.py` 无法导入模型 | 检查 `models/` 目录下权重文件 | 模型路径未配置 |
| 边缘连接不上 MQTT | 在 107 上: `mosquitto_pub -h 103 -t test -m hello` | 网络/防火墙问题 |
| RTMP 推流失败 | `ffprobe rtmp://103:1935/stream/safety_cam` | RTMP 服务器未启动 |
| 数据库表不存在 | `docker exec -it edge_cloud_postgres psql -U edge_user -d edge_cloud -c "\dt"` | 未执行 Step 2 建表 |
| MQTT 反复断开 (rc=7) | `docker exec edge_cloud_training ps aux \| grep radio_infer` | 重复进程 client ID 冲突，杀掉多余进程 |
| Git Bash 路径错误 | 命令前加 `MSYS_NO_PATHCONV=1` | Git Bash 自动转换 Unix 路径 |

### 19.13 快速启停命令汇总

```bash
# ===== 一键启动 (云端 103) =====
cd deployment/docker
docker compose up -d postgres redis emqx mlflow seaweedfs portal
sleep 20
docker compose up -d backend frontend

# 启动云端推理（自动模式，降级流从 YAML 读取）
docker exec edge_cloud_training python3 /app/radio_infer_server.py \
  --config /app/models/construction_safety/configs/construction_safety.yaml \
  --checkpoint /app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar \
  --radio-code /app/models/NVlabs_RADIO \
  --siglip2 /app/models/siglip2-giant-opt-patch16-384

# ===== 一键启动 (边缘 107) =====
cd /home/nvidia/edge_infer/build && ./edge_framework

# ===== 一键演示 (本机 PowerShell) =====
powershell -ExecutionPolicy Bypass -File scripts\demo_construction_safety.ps1

# ===== 重建 Training 容器（首次或 Dockerfile 更新后）=====
docker compose --profile gpu build training
docker compose --profile gpu up -d training
docker exec edge_cloud_training pip install timm einops transformers paho-mqtt

# ===== 停止 =====
docker exec edge_cloud_training bash -c "pkill -f radio_infer_server"   # 停止推理
docker compose down                                                      # 停止所有服务
docker stop rtmp-server 2>/dev/null                                      # 停止 RTMP

# ===== 清理数据 =====
# 前端界面：推理结果页/告警中心页点击「清空数据」
# 命令行：
docker exec edge_cloud_postgres psql -U edge_user -d edge_cloud -c "TRUNCATE inference_results;"
```

---

## 20. 下一步

- 查看 [API 文档](http://localhost:8081/swagger-ui.html)
- 了解边缘端部署：参考 `edge_infer` 项目的 `README_JETSON.md`
- 阅读投标技术优势文档：[docs/TECHNICAL_ADVANTAGES.md](docs/TECHNICAL_ADVANTAGES.md)
