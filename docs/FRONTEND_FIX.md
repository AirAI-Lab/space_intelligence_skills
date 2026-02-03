# 前端组件字段名修复指南

## 问题分析

后端返回驼峰命名（camelCase）：
- `deviceId`, `deviceName`, `deviceType`, `cpuUsage` 等

前端模板需要更新为驼峰命名：
- `device_id` → `deviceId`
- `device_name` → `deviceName`
- `device_type` → `deviceType`
- `cpu_usage` → `cpuUsage`
- `gpu_usage` → `gpuUsage`
- `memory_usage` → `memoryUsage`
- `last_heartbeat` → `lastHeartbeat`

## 需要修复的文件

1. `frontend/src/views/device/DeviceList.vue` - 设备列表
2. `frontend/src/views/model/ModelList.vue` - 模型列表
3. `frontend/src/views/ota/OtaTask.vue` - OTA任务
4. `frontend/src/views/training/TrainingJob.vue` - 训练任务

## 快速修复方案

由于Docker挂载卷的修改不生效，建议：

1. 直接修改宿主机上的文件
2. 或者重新构建前端容器

```bash
# 停止前端
docker-compose stop frontend

# 重新构建前端
docker-compose build frontend

# 启动前端
docker-compose up -d frontend
```

## 临时验证方案

可以直接访问后端API验证数据：

```bash
# 设备列表
curl http://localhost:8081/api/v1/devices

# 模型列表
curl http://localhost:8081/api/v1/models

# OTA任务
curl http://localhost:8081/api/v1/ota/tasks
```
