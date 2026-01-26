# 设备管理指南

## 设备注册

### 通过Web界面注册

1. 登录管理平台
2. 进入"设备管理"页面
3. 点击"添加设备"按钮
4. 填写设备信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| 设备ID | 设备唯一标识 | EDGE_DEVICE_001 |
| 设备名称 | 设备显示名称 | 机载设备1号 |
| 设备类型 | 设备型号 | jetson_orin |
| 所属分组 | 设备分组 | 巡检组A |

5. 点击"确定"完成注册

### 通过API注册

```bash
curl -X POST http://localhost:8080/api/v1/device/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "EDGE_DEVICE_001",
    "device_name": "机载设备1号",
    "device_type": "jetson_orin",
    "group_id": "group_a",
    "specs": {
      "cpu": "ARM Cortex-A78AE",
      "gpu": "NVIDIA Ampere",
      "memory": "32GB",
      "storage": "256GB"
    }
  }'
```

## 设备列表

### 查看所有设备

设备列表页面显示：

| 设备ID | 设备名称 | 状态 | CPU使用率 | GPU使用率 | 内存使用率 | 最后心跳 |
|--------|---------|------|----------|----------|-----------|---------|
| EDGE_001 | 设备1 | 在线 | 45% | 60% | 12.5GB | 5秒前 |
| EDGE_002 | 设备2 | 离线 | - | - | - | 1小时前 |

### 设备状态说明

- **在线**：设备正常连接，心跳正常
- **离线**：设备超过5分钟未发送心跳
- **告警**：设备资源使用率超过阈值
- **故障**：设备无法连接或异常

## 设备详情

### 查看设备详情

点击设备ID进入详情页面，可以看到：

#### 基础信息
- 设备ID、名称、类型
- IP地址、MAC地址
- 固件版本、运行时间

#### 实时指标
- CPU使用率曲线
- GPU使用率曲线
- 内存使用情况
- 存储使用情况
- 温度监控

#### 推理状态
- 当前加载的模型
- 推理帧率
- 检测结果统计

### 远程配置下发

#### 修改推理配置

1. 进入设备详情页
2. 点击"配置管理"
3. 修改配置参数：

```json
{
  "model_config": {
    "conf_threshold": 0.5,
    "nms_threshold": 0.45,
    "input_width": 960,
    "input_height": 960
  },
  "inference_config": {
    "max_fps": 30,
    "enable_trackbar": true
  }
}
```

4. 点击"应用配置"
5. 设备会自动重启推理服务

#### 修改推流配置

```json
{
  "output_config": {
    "enable_rtmp": true,
    "rtmp_url": "rtmp://server/live/stream",
    "enable_snapshot": true,
    "snapshot_interval": 10
  }
}
```

## 设备分组

### 创建分组

1. 进入"设备管理" → "分组管理"
2. 点击"创建分组"
3. 填写分组信息

### 分组操作

- **批量部署**：选择分组，一键部署模型到所有设备
- **批量配置**：统一配置分组内所有设备
- **批量升级**：OTA批量升级

## 设备告警

### 告警规则

系统自动监控以下指标：

| 指标 | 告警阈值 | 级别 |
|------|---------|------|
| CPU使用率 | >80% | 警告 |
| GPU使用率 | >90% | 警告 |
| 内存使用率 | >85% | 警告 |
| 温度 | >70°C | 严重 |
| 心跳超时 | >5分钟 | 离线 |

### 告警通知

告警触发后，系统会：

1. 在设备列表中标记设备状态
2. 发送告警通知（邮件/Webhook）
3. 记录告警日志

### 查看告警历史

进入"设备管理" → "告警记录"，可以查看历史告警。

## 设备日志

### 查看实时日志

1. 进入设备详情页
2. 点击"实时日志"
3. 可以看到设备的实时日志输出

### 日志级别

- DEBUG：调试信息
- INFO：一般信息
- WARN：警告信息
- ERROR：错误信息

### 日志搜索

支持按关键词、时间范围、日志级别搜索。

## 设备维护

### 重启设备

```bash
curl -X POST http://localhost:8080/api/v1/device/EDGE_DEVICE_001/restart
```

### 清理缓存

```bash
curl -X POST http://localhost:8080/api/v1/device/EDGE_DEVICE_001/clear-cache
```

### 设备卸载

```bash
curl -X DELETE http://localhost:8080/api/v1/device/EDGE_DEVICE_001
```

注意：卸载设备会删除所有关联配置，请谨慎操作。

## 常见问题

### Q1: 设备显示离线怎么办？

1. 检查设备网络连接
2. 检查边缘Agent是否运行
3. 检查防火墙设置
4. 查看设备日志

### Q2: 如何批量导入设备？

准备CSV文件：

```csv
device_id,device_name,device_type,group_id
EDGE_001,设备1,jetson_orin,group_a
EDGE_002,设备2,jetson_xavier,group_a
```

上传文件进行批量导入。

### Q3: 设备时间不同步怎么办？

边缘设备会自动与云端时间同步。如果仍有问题，可以手动设置：

```bash
# 在边缘设备上
sudo ntpdate -u time.nist.gov
```
