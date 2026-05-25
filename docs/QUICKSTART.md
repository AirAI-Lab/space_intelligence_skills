# edge_infer_cloud 快速启动指南

## 前置准备

### 硬件要求

| 资源 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 8核+ | 16核+ |
| 内存 | 32GB | 64GB |
| 存储 | 100GB 可用空间 | 200GB+ NVMe SSD |
| GPU (可选) | - | NVIDIA RTX 4060 Ti 16GB+ |

### 软件要求

- Windows 10/11 或 Linux
- Docker Desktop 4.30+ (Windows) 或 Docker 24+ (Linux)
- NVIDIA GPU Driver 545+ (如需 GPU 推理/训练)
- Git

---

## 快速启动 (5 分钟)

### 第一步：克隆项目

```bash
git clone https://github.com/AirAI-Lab/edge_infer_cloud.git
cd edge_infer_cloud
```

### 第二步：启动服务

```bash
cd deployment/docker
```

根据需求选择部署模式：

**开发模式**（源码挂载，热重载）：

| 模式 | 命令 | 容器数 | 适用场景 |
|------|------|--------|----------|
| **A: 纯推理** | `docker compose --profile gpu up -d` | 2 | 第三方只需 MQTT 推理结果 |
| **B: 推理+管理** | `docker compose --profile standard up -d` | 8 | 有管理需求但无 GPU |
| **C: 完整平台** | `docker compose --profile standard --profile gpu up -d` | 10 | 全功能部署 |

**生产模式**（预构建镜像，统一入口）：

```bash
# 首次部署（生成 .env、初始化存储）
./deploy.sh --init

# 生产部署
./deploy.sh              # 仅管理服务
./deploy.sh --gpu        # 含 GPU 训练/推理
```

> 详细部署说明见 [DEPLOYMENT.md](DEPLOYMENT.md)

### 第三步：验证安装

```bash
# 检查容器状态
docker compose ps

# 检查后端健康（模式 B/C）
curl http://localhost:8081/actuator/health
```

### 第四步：访问服务

**开发模式**：

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端管理平台 | http://localhost:3000 | Vue3 管理平台（模式 B/C） |
| 后端 API | http://localhost:8081/api/v1 | REST API（模式 B/C） |
| EMQX 面板 | http://localhost:18083 | MQTT 管理（admin / admin123456） |
| MLflow | http://localhost:5001 | 模型管理（模式 B/C） |

**生产模式**（Nginx 统一入口）：

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端管理平台 | http://{HOST}/ | 统一入口 |
| 后端 API | http://{HOST}/api/v1/ | REST API（需 `X-API-Key`） |
| API 文档 | http://{HOST}/swagger-ui.html | Swagger UI |
| EMQX 面板 | http://{HOST}/emqx/ | MQTT 管理 |

---

## 常用操作

```bash
# 查看日志
docker compose logs -f backend
docker compose logs -f training

# 停止所有服务
docker compose down

# 重启某个服务
docker compose restart backend

# 更新代码后重新部署
git pull
docker compose up -d --build
```

---

## 云端推理（模式 A/B/C 均可使用）

### 前置：下载模型权重

云端推理依赖三个大模型文件（总计约 10 GB），首次使用需手动下载：

```bash
pip install huggingface_hub

# C-RADIOv4-H (1.68 GB) — https://huggingface.co/nvidia/C-RADIOv4-H
huggingface-cli download nvidia/C-RADIOv4-H --local-dir models/C-RADIOv4-H

# SigLIP2 (7.5 GB) — https://huggingface.co/google/siglip2-giant-opt-patch16-384
huggingface-cli download google/siglip2-giant-opt-patch16-384 --local-dir models/siglip2-giant-opt-patch16-384

# RADIO 代码 — https://github.com/NVlabs/RADIO
git clone https://github.com/NVlabs/RADIO.git models/NVlabs_RADIO
```

> 国内网络：在命令前加 `HF_ENDPOINT=https://hf-mirror.com` 使用镜像站

### 启动推理

GPU 容器启动后，运行云端推理：

```bash
# 进入训练容器
docker exec -it edge_cloud_training bash

# 水利巡检场景
python /app/models/cloud_inference/radio_infer_server.py \
  --config /app/models/water_inspection/configs/water_inspection.yaml

# 施工安全场景
python /app/models/cloud_inference/radio_infer_server.py \
  --config /app/models/construction_safety/configs/construction_safety.yaml
```

> 新场景零代码接入：只需创建 YAML 配置文件，指定 `--config` 即可运行。

---

## 下一步

- [DEPLOYMENT.md](DEPLOYMENT.md) — 完整部署指南（开发/生产/Linux 迁移）
- [THIRD_PARTY_INTEGRATION.md](THIRD_PARTY_INTEGRATION.md) — 第三方平台对接指南
- [api/README.md](api/README.md) — REST API 完整参考
- [EDGE_REST_API.md](EDGE_REST_API.md) — 边缘设备 REST API
- [INFERENCE_PIPELINE.md](INFERENCE_PIPELINE.md) — 云边协同推理管线详解
