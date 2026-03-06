# 首页数据显示修复说明

## 问题描述

首页（http://localhost:3000/）显示的都是硬编码的假数据：
- 统计卡片：在线设备42、数据集18、模型版本35、训练任务7
- 在线设备列表：固定的2个设备（EDGE_001, EDGE_002）
- 训练任务：固定的3个任务
- 设备状态图表：固定的35个在线、5个离线、2个故障

## 问题原因

前端 `Home.vue` 中使用了硬编码的假数据，没有从后端API获取真实数据。

## 修复内容

### 1. 后端添加设备统计API

**文件**: `backend/src/main/java/com/edge/cloud/controller/DeviceController.java`

添加了 `getStatistics()` 方法，返回设备统计信息：
- 总设备数
- 各状态设备数（ONLINE、OFFLINE、UPGRADING、ERROR）

```java
@GetMapping("/stats")
@Operation(summary = "获取设备统计信息")
public ResponseEntity<ApiResponse<Map<String, Object>>> getStatistics() {
    try {
        List<Object[]> statusCounts = deviceRepository.countByStatus();

        Map<String, Long> statusMap = new HashMap<>();
        statusMap.put("ONLINE", 0L);
        statusMap.put("OFFLINE", 0L);
        statusMap.put("UPGRADING", 0L);
        statusMap.put("ERROR", 0L);

        long total = 0;
        for (Object[] row : statusCounts) {
            Device.DeviceStatus status = (Device.DeviceStatus) row[0];
            Long count = (Long) row[1];
            statusMap.put(status.toString(), count);
            total += count;
        }

        Map<String, Object> stats = new HashMap<>();
        stats.put("total", total);
        stats.put("statusCounts", statusMap);

        return ResponseEntity.ok(ApiResponse.success(stats));
    } catch (Exception e) {
        log.error("获取设备统计失败", e);
        return ResponseEntity.status(500).body(ApiResponse.error("获取失败: " + e.getMessage()));
    }
}
```

### 2. 前端修复首页数据获取

**文件**: `frontend/src/views/Home.vue`

#### 修改内容：
- 移除所有硬编码的假数据
- 从真实API获取数据
- 添加自动刷新机制（每60秒）

#### 主要改动：

```typescript
// 加载统计数据
const loadStatistics = async () => {
  try {
    // 并行加载所有统计数据
    const [devicesRes, datasetsRes, modelsRes, trainingsRes] = await Promise.all([
      deviceApi.getList({ page: 1, pageSize: 1 }), // 只需要总数
      dataApi.getList({ page: 1, pageSize: 1 }),
      modelApi.getList({ page: 1, pageSize: 1 }),
      trainingApi.getList({ page: 1, pageSize: 5 }) // 获取最近5个训练任务
    ])

    // 更新统计数据
    statistics.value[0].value = devicesRes.data.total || 0
    statistics.value[1].value = datasetsRes.data.total || 0
    statistics.value[2].value = modelsRes.data.total || 0
    statistics.value[3].value = trainingsRes.data.total || 0

    // 获取设备状态统计
    const statsRes = await fetch('/api/v1/devices/stats').then(res => res.json())
    if (statsRes.code === 200 && statsRes.data.statusCounts) {
      deviceStatusStats.value = statsRes.data.statusCounts

      // 更新在线设备数量（使用ONLINE状态的数量）
      statistics.value[0].value = statsRes.data.statusCounts.ONLINE || 0
    }
  } catch (error: any) {
    console.error('加载统计数据失败:', error)
  }
}

// 加载在线设备列表
const loadOnlineDevices = async () => {
  try {
    const response = await deviceApi.getList({
      page: 1,
      pageSize: 10,
      status: 'ONLINE'
    })

    onlineDevices.value = (response.data.items || []).map((item: any) => ({
      deviceId: item.deviceId,
      deviceName: item.deviceName,
      cpuUsage: item.cpuUsage || 0,
      gpuUsage: item.gpuUsage || 0,
      memoryUsage: (item.memoryUsage || 0).toFixed(1),
      lastHeartbeat: item.lastHeartbeat || '-'
    }))
  } catch (error: any) {
    console.error('加载在线设备失败:', error)
    onlineDevices.value = []
  }
}

// 刷新所有数据
const refreshData = async () => {
  await loadStatistics()
  await loadOnlineDevices()
  // 更新图表
  if (deviceStatusChart.value) {
    initChart()
  }
}

onMounted(() => {
  refreshData()
  // 每分钟刷新一次数据
  setInterval(refreshData, 60000)
})
```

### 3. 前端API添加统计接口

**文件**: `frontend/src/api/index.ts`

添加了 `deviceApi.getStats()` 方法：

```typescript
/**
 * 获取设备统计信息
 */
getStats: () =>
  request.get('/devices/stats')
```

## 修复效果

### 修复前：
- ❌ 显示固定的假数据（42个在线设备、18个数据集等）
- ❌ 在线设备列表固定显示2个设备
- ❌ 训练任务固定显示3个任务
- ❌ 设备状态图表固定显示35/5/2

### 修复后：
- ✅ 显示真实的统计数据（从数据库获取）
- ✅ 在线设备列表动态显示当前在线的设备
- ✅ 训练任务显示最近的真实任务
- ✅ 设备状态图表动态反映实际状态分布
- ✅ 每60秒自动刷新数据

## 数据来源说明

首页现在使用以下API获取真实数据：

1. **设备统计**: `/api/v1/devices/stats`
   - 返回各状态的设备数量

2. **设备列表**: `/api/v1/devices?page=1&pageSize=10&status=ONLINE`
   - 返回在线设备列表

3. **数据集列表**: `/api/v1/datasets?page=1&pageSize=1`
   - 返回数据集总数

4. **模型列表**: `/api/v1/models?page=1&pageSize=1`
   - 返回模型总数

5. **训练任务**: `/api/v1/training?page=1&pageSize=5`
   - 返回最近5个训练任务

## 验证方法

1. 访问 http://localhost:3000/
2. 检查统计数据是否与实际一致
3. 刷新页面，确认数据实时更新
4. 等待60秒后，数据自动刷新

## 当前状态

根据实际数据库查询结果（2026-03-06 11:50）：
- **设备统计**: 0个在线、0个离线（所有模拟设备已删除）
- **数据集**: 3个
- **模型**: 2个
- **训练任务**: 根据实际任务数量显示

## 注意事项

1. **自动刷新**: 首页每60秒自动刷新一次数据
2. **空数据处理**: 当没有数据时，显示0或空列表，不会报错
3. **错误处理**: API调用失败时，会在控制台记录错误，不影响页面显示
4. **性能优化**: 使用并行请求（Promise.all）加快数据加载速度

## 相关文件

- `backend/src/main/java/com/edge/cloud/controller/DeviceController.java` - 设备管理控制器
- `backend/src/main/java/com/edge/cloud/repository/DeviceRepository.java` - 设备数据访问
- `frontend/src/views/Home.vue` - 首页组件
- `frontend/src/api/index.ts` - API接口定义
