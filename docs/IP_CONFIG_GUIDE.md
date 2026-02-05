# WiFi IP 变更时快速配置指南

当云端或 Jetson 设备的 WiFi IP 地址发生变化时，按以下步骤统一更新配置。

## 快速步骤

### 1. 修改云端配置

**文件位置**: `edge_infer_cloud/.env.ip`

```bash
# 修改这两个 IP 地址
CLOUD_IP=192.168.0.xxx     # 改为新的云端 IP
JETSON_IP=192.168.0.xxx     # 改为新的 Jetson IP
```

### 2. 重启云端服务

```bash
cd edge_infer_cloud/deployment/docker
docker compose up -d --force-recreate backend
```

### 3. 同步 Jetson 配置

**方式1：在 Jetson 上拉取最新代码**
```bash
cd ~/edge_infer
git pull origin master
python scripts/sync_network_config.py
```

**方式2：从本机推送配置**
```bash
cd edge_infer
python scripts/sync_network_config.py
scp config/cloud_config.json nvidia@<JETSON_IP>:~/edge_infer/config/
scp config/framework_config.json nvidia@<JETSON_IP>:~/edge_infer/config/
```

### 4. 重启 Jetson edge_infer

```bash
# SSH 到 Jetson
ssh nvidia@<JETSON_IP>

# 重启 edge_infer
pkill -9 edge_framework
cd ~/edge_infer
./build/edge_framework > /tmp/edge_framework.log 2>&1 &
```

### 5. 验证连接

```bash
# 在云端检查设备心跳
curl http://localhost:8081/api/v1/devices

# 在 Jetson 上测试连接
curl http://<CLOUD_IP>:8081/actuator/health
```

## 配置文件说明

### edge_infer_cloud

| 文件 | 用途 |
|------|------|
| `.env.ip` | IP 地址配置源文件 |
| `deployment/docker/docker-compose.yml` | 使用 `${CLOUD_API_URL}` 变量 |

### edge_infer

| 文件 | 用途 |
|------|------|
| `config/network.config` | IP 地址配置源文件 |
| `config/cloud_config.json` | API 和 MQTT 配置 |
| `config/framework_config.json` | 框架和流地址配置 |
| `scripts/sync_network_config.py` | 配置同步脚本 |

## 常见问题

**Q: 修改了 .env.ip 但云端仍在使用旧 IP？**
A: 需要强制重新创建容器：`docker compose up -d --force-recreate backend`

**Q: Jetson 无法连接到云端？**
A: 检查：
1. `config/network.config` 中的 CLOUD_IP 是否正确
2. 运行 `python scripts/sync_network_config.py` 同步配置
3. 重启 edge_infer

**Q: 如何检查当前使用的 IP？**
A: 云端：`docker exec edge_cloud_backend printenv BACKEND_EXTERNAL_URL`
   Jetson：`grep "api_base_url\|broker_host" ~/edge_infer/config/cloud_config.json`
