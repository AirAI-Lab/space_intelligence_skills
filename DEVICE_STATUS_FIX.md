# 设备在线状态修复说明

## 问题描述

设备管理页面 (http://localhost:3000/device) 显示设备 `jetson_orin_001` 为在线状态，但实际该设备并未运行。

## 问题原因

1. **模拟设备数据**：`schema.sql` 中插入了测试设备数据，这些设备的初始状态可能为 `ONLINE`
2. **缺少离线检查机制**：系统没有定时任务检查长时间未发送心跳的设备，导致这些设备一直显示为在线状态
3. **状态判断不准确**：前端和后端都没有根据 `last_heartbeat` 时间戳来判断设备是否真实在线

## 修复内容

### 1. 添加设备在线状态检查定时任务

**文件**: `backend/src/main/java/com/edge/cloud/service/DeviceCommunicationService.java`

添加了 `checkAndUpdateDeviceStatus()` 定时任务：
- 每1分钟执行一次
- 自动查找超过5分钟未发送心跳的在线设备
- 将这些设备的状态自动更新为 `OFFLINE`

```java
@Scheduled(fixedDelay = 60000) // 每1分钟执行一次
@Transactional
public void checkAndUpdateDeviceStatus() {
    try {
        List<Device> offlineDevices = deviceRepository.findOfflineDevices();

        if (!offlineDevices.isEmpty()) {
            log.info("发现 {} 个设备长时间未心跳，标记为离线", offlineDevices.size());

            for (Device device : offlineDevices) {
                log.debug("设备 {} 最后心跳时间: {}，标记为离线",
                        device.getDeviceId(), device.getLastHeartbeat());
                device.setStatus(Device.DeviceStatus.OFFLINE);
                deviceRepository.save(device);
            }
        }
    } catch (Exception e) {
        log.error("检查设备在线状态失败", e);
    }
}
```

### 2. 移除模拟设备初始化数据

**文件**: `backend/src/main/resources/schema.sql`

注释掉了测试设备的插入语句，避免系统初始化时创建模拟数据：

```sql
-- 注意：已移除模拟设备数据，避免干扰实际设备状态
-- 真实设备应通过心跳接口自动注册
-- INSERT INTO devices (device_id, device_name, device_type, group_id, status, mqtt_topic) VALUES
-- ('EDGE_DEVICE_001', '边缘设备1', 'jetson_orin', 'group_a', 'ONLINE', 'device/EDGE_DEVICE_001'),
-- ('EDGE_DEVICE_002', '边缘设备2', 'jetson_xavier', 'group_a', 'OFFLINE', 'device/EDGE_DEVICE_002')
-- ON CONFLICT (device_id) DO NOTHING;
```

### 3. 创建清理脚本

**文件**: `backend/src/main/resources/cleanup_mock_devices.sql`

提供了SQL脚本用于清理现有数据库中的模拟设备数据。

## 使用说明

### 1. 清理现有模拟设备

如果数据库中已经存在模拟设备，执行以下命令清理：

```bash
# 进入数据库
psql -U edge_user -d edge_cloud

# 执行清理脚本
\i backend/src/main/resources/cleanup_mock_devices.sql

# 或者直接执行SQL
DELETE FROM devices WHERE device_id LIKE 'EDGE_DEVICE_%';

# 删除特定设备（如 jetson_orin_001）
DELETE FROM devices WHERE device_id = 'jetson_orin_001';
```

### 2. 重启后端服务

修改完成后，重启后端服务以使更改生效：

```bash
# 如果使用 Docker Compose
docker-compose restart backend

# 或手动重启服务
```

### 3. 验证修复效果

1. 等待1-2分钟，让定时任务运行
2. 访问 http://localhost:3000/device 查看设备列表
3. 确认：
   - 模拟设备已被删除或标记为离线
   - 只显示真实注册的设备
   - 设备状态与实际情况一致

## 工作原理

### 设备注册流程

1. 边缘设备启动时，通过心跳接口注册
2. `DeviceCommunicationService.processHeartbeat()` 收到心跳后：
   - 创建或更新设备记录
   - 设置状态为 `ONLINE`
   - 更新 `last_heartbeat` 为当前时间

### 设备离线检测

1. 定时任务每1分钟执行一次
2. 查询条件：`status = 'ONLINE' AND last_heartbeat < CURRENT_TIMESTAMP - INTERVAL '5 minutes'`
3. 将符合条件的设备状态更新为 `OFFLINE`

### 设备重新上线

当设备重新发送心跳时，状态会自动更新为 `ONLINE`。

## 注意事项

1. **心跳超时时间**：默认设置为5分钟，可根据实际需求调整 `DeviceRepository.findOfflineDevices()` 中的时间间隔
2. **定时任务频率**：默认每1分钟执行一次，可通过修改 `@Scheduled(fixedDelay = 60000)` 调整
3. **数据库初始化**：新建数据库时，不会再插入模拟设备数据
4. **真实设备**：只有真实发送心跳的设备才会出现在列表中

## 后续优化建议

1. **前端显示**：可以在前端添加最后心跳时间显示，帮助用户快速判断设备状态
2. **告警机制**：可以添加设备离线告警功能，当设备离线时发送通知
3. **自定义超时**：允许为不同设备类型设置不同的心跳超时时间
4. **设备分组**：对设备进行分组管理，便于批量操作和监控

## 相关文件

- `backend/src/main/java/com/edge/cloud/service/DeviceCommunicationService.java` - 设备通信服务
- `backend/src/main/java/com/edge/cloud/repository/DeviceRepository.java` - 设备数据访问
- `backend/src/main/java/com/edge/cloud/controller/DeviceController.java` - 设备管理API
- `backend/src/main/java/com/edge/cloud/entity/Device.java` - 设备实体
- `backend/src/main/resources/schema.sql` - 数据库架构定义
- `backend/src/main/resources/cleanup_mock_devices.sql` - 模拟设备清理脚本
- `frontend/src/views/device/DeviceList.vue` - 设备列表页面
