# 云边协同部署 — 常见问题与经验总结

> 本文档记录实际部署中遇到的问题、根因分析和解决方案，供团队参考。

---

## Q1: 边缘设备连不上云端 MQTT (1883) / API (8081)

### 现象
边缘设备（如 Jetson）启动后，设备注册和心跳失败，`192.168.1.123:1883` 和 `192.168.1.123:8081` 连接被拒绝。

### 根因
生产模式 (`docker-compose.prod.yml`) 中 EMQX 和 Backend 使用 `expose`（仅 Docker 内部网络可见），未通过 `ports` 对外暴露。外部设备无法访问。

### 解决
在 `docker-compose.prod.yml` 中将关键端口改为 `ports` 对外映射：

```yaml
# EMQX
emqx:
  ports:
    - "1883:1883"    # MQTT TCP — 边缘设备原生 MQTT 客户端直连

# Backend
backend:
  ports:
    - "8081:8080"    # REST API — 边缘设备注册/心跳/推理结果上报
```

修改后执行：
```bash
cd deployment/docker
docker compose -f docker-compose.prod.yml up -d
```

### 经验
- **生产模式**默认只暴露 Nginx (80/443) 和 RTMP (1935)
- 边缘设备需要直连的端口：**1883 (MQTT)**、**8081 (API)**、**1935 (RTMP)**
- 通过 Nginx 代理的端口 (80)：前端、API、S3、MLflow、EMQX 管理面板、MQTT WebSocket

---

## Q2: 设备注册报错 `column capabilities does not exist`

### 现象
边缘设备心跳上报时后端报错：`ERROR: column d1_0.capabilities does not exist`

### 根因
`Device.java` 实体新增了 `capabilities`、`device_category`、`protocol`、`labels` 字段，但 PostgreSQL 表结构未同步。Hibernate `ddl-auto` 在生产 profile 下未生效或被禁用。

### 解决
手动补全缺失列：
```bash
docker exec -i edge_cloud_postgres psql -U edge_user -d edge_cloud -c "
  ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_category VARCHAR(30);
  ALTER TABLE devices ADD COLUMN IF NOT EXISTS capabilities VARCHAR(200);
  ALTER TABLE devices ADD COLUMN IF NOT EXISTS protocol VARCHAR(30);
  ALTER TABLE devices ADD COLUMN IF NOT EXISTS labels TEXT;
"
```

### 预防
- 已将 ALTER 语句加入 `deploy.sh` 的 `init_db` 函数
- 已同步更新 `schema.sql` 建表语句
- **每次修改 Java 实体字段后，务必同步 `schema.sql` 和 `deploy.sh`**

---

## Q3: 云端推理启动报错 `No module named 'timm'` / `'paho'` / `'einops'`

### 现象
在 Training 容器中启动云端推理 `radio_infer_server.py`，报 `ModuleNotFoundError`。

### 根因
`training/requirements.txt` 已包含这些依赖，但 Docker 镜像是**在 requirements.txt 更新之前构建的**。容器运行后手动 `pip install` 只保存在容器临时层，重建容器会丢失。

### 解决
**重建镜像**（一次性安装所有依赖）：
```bash
cd deployment/docker
docker compose -f docker-compose.prod.yml build --no-cache training
docker compose -f docker-compose.prod.yml up -d training
```

### 预防
- **修改 `requirements.txt` 后必须重建镜像**
- 可通过 `./deploy.sh --rebuild` 一键重建
- 不要依赖在运行中的容器里手动 `pip install`

---

## Q4: 云端推理自动检测报 "MQTT 和 RTMP 均不可用"

### 现象
`radio_infer_server.py` 启动时报：
```
[ERROR] 自动检测: MQTT 和 RTMP 均不可用
[ERROR]   → 请通过 --stream 指定视频流地址，或确保 MQTT broker 可达
```

### 根因
通常有两个原因（需逐一排查）：
1. **`paho-mqtt` 未安装** — MQTT 检测直接抛异常返回 False（见 Q3）
2. **RTMP 降级流地址中没有推流** — `_check_stream()` 用 cv2 打开流失败

### 解决
1. 先确保 `paho-mqtt` 已安装（见 Q3 重建镜像）
2. 确保边缘端已推流到 RTMP 服务器：`ffprobe rtmp://192.168.1.123:1935/stream/cam1`
3. 如只验证 RTMP 直连模式，可手动指定：`--stream rtmp://192.168.1.123:1935/stream/cam1`

### 验证 MQTT 连通性
```bash
docker exec edge_cloud_training python3 -c "
import paho.mqtt.client as mqtt, time, os
result = [False]
def on_connect(c, u, f, rc):
    result[0] = (rc == 0); c.disconnect()
c = mqtt.Client(client_id='probe', protocol=mqtt.MQTTv311)
c.on_connect = on_connect
broker = os.getenv('MQTT_BROKER_URL','tcp://emqx:1883').replace('tcp://','')
h, p = broker.split(':')[0], int(broker.split(':')[1]) if ':' in broker else 1883
c.connect(h, p, keepalive=5); c.loop_start(); time.sleep(3); c.loop_stop()
print('MQTT OK' if result[0] else 'MQTT FAIL')
"
```

---

## Q5: IP 地址分散在多个文件，改一处漏一处

### 现象
云端 IP 变更后，部分配置仍指向旧 IP，导致边缘设备无法连接。

### 根因
IP 配置分散在 5+ 个文件中：`.env.ip`、`.env`、`docker-compose.yml`、场景 YAML、Java 默认值。

### 解决
使用统一 IP 同步脚本：
```bash
# 设置新 IP 并同步到所有配置文件
bash scripts/configure_ip.sh --cloud 192.168.1.123 --edge 192.168.0.1

# 查看当前配置
bash scripts/configure_ip.sh --show
```

### 工作流
```
编辑 .env.ip → 运行 configure_ip.sh 同步 → 运行 deploy.sh 部署
```

### 涉及文件

| 文件 | 配置项 | 说明 |
|------|--------|------|
| `deployment/docker/.env` | `CLOUD_API_URL` | 后端外部访问地址 |
| `deployment/docker/docker-compose.yml` | `S3_EXTERNAL_ENDPOINT` | Training 外部 S3（开发模式） |
| `models/*/configs/*.yaml` | `fallback_stream` | RTMP 降级流地址 |
| `backend/.../OtaService.java` | `S3_EXTERNAL_ENDPOINT` 默认值 | OTA 模型下载 URL |

---

## Q6: 修改 docker-compose 配置后需要重建镜像吗？

### 答案：取决于改了什么

| 修改内容 | 是否需要重建 | 命令 |
|----------|-------------|------|
| `environment` / `ports` / `volumes` | ❌ 不需要 | `docker compose up -d` |
| `build` 上下文中的代码/Dockerfile | ✅ 需要 | `docker compose build <service>` |
| `requirements.txt` / 依赖变更 | ✅ 需要 | `docker compose build --no-cache training` |
| `.env` 文件 | ❌ 不需要 | `docker compose up -d` |

### 快速参考
```bash
# 只改了配置（IP、环境变量、端口）— 不重建
cd deployment/docker && docker compose -f docker-compose.prod.yml up -d

# 改了代码或依赖 — 重建受影响的服务
docker compose -f docker-compose.prod.yml build training
docker compose -f docker-compose.prod.yml up -d training

# 全量重建
./deploy.sh --rebuild
```

---

## Q7: 为什么 OtaService.java / 配置中用 IP 而不是 localhost？

### 答案
这些 URL 是给**边缘设备访问云端**用的，不是给本机用的：
- `S3_EXTERNAL_ENDPOINT` → 边缘设备下载模型文件。`localhost` 对 Jetson 来说是 Jetson 自己
- `backend.external-url` → 边缘设备回调云端 API。同理
- `fallback_stream` → 云端推理从 RTMP 拉流。必须用云端外部 IP

**Docker 内部服务互访用 Docker 网络名**（如 `http://seaweedfs:8333`、`http://backend:8080`），这些不需要 IP。

---

## 端口速查表

### 边缘设备需要访问的端口

| 端口 | 协议 | 用途 | 边缘设备访问地址 |
|------|------|------|-----------------|
| **1883** | MQTT TCP | 心跳/推理帧转发/OTA命令 | `tcp://192.168.1.123:1883` |
| **8081** | HTTP REST | 设备注册/推理结果上报 | `http://192.168.1.123:8081/api/v1` |
| **80** | HTTP | Nginx 统一入口（前端/API/S3） | `http://192.168.1.123/api/v1` |
| **1935** | RTMP | 视频推流 | `rtmp://192.168.1.123:1935/stream/cam1` |

### 仅 Docker 内部访问（不对外暴露）

| 端口 | 服务 | 访问方式 |
|------|------|---------|
| 5432 | PostgreSQL | `postgres:5432` |
| 6379 | Redis | `redis:6379` |
| 5000 | MLflow | `mlflow:5000` |
| 8333 | SeaweedFS S3 | `seaweedfs:8333` |
| 5002 | Training | `training:5002` |

### 生产模式对外端口

| 端口 | 服务 | Nginx 代理路径 |
|------|------|---------------|
| 80 | Nginx | `/` (前端), `/api/` (后端), `/s3/` (S3), `/mlflow/`, `/emqx/`, `/mqtt/ws` |
| 443 | Nginx | HTTPS（需配置证书） |
| 1883 | EMQX | MQTT TCP 直连（边缘设备用） |
| 1935 | RTMP | 流媒体（边缘/ffmpeg 推流用） |
| 8081 | Backend | REST API 直连（边缘设备用） |
