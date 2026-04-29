# 已知问题和解决方案

## Java 后端问题

### 1. 循环依赖问题
**症状**：
```
 UnsatisfiedDependencyException: Requested bean is currently in creation:
 Is there an unresolvable circular reference?
 ┌─────┐
 │  mqttService
 ↑     ↓
 │  otaService
 └─────┘
```

**解决方案**：使用 setter 注入打破循环依赖
```java
@Service
@RequiredArgsConstructor
public class OtaService {
    // 其他依赖...

    private MqttService mqttService;

    public void setMqttService(MqttService mqttService) {
        this.mqttService = mqttService;
    }
}
```

### 2. Repository 方法签名不匹配
**症状**：
```
method findByStatus in interface cannot be applied to given types;
  found: Status, Pageable
  reason: actual and formal argument lists differ in length
```

**解决方案**：添加 Pageable 重载方法
```java
public interface DatasetRepository extends JpaRepository<Dataset, String> {
    // 原有方法
    List<Dataset> findByStatus(Dataset.DatasetStatus status);

    // 添加 Pageable 重载
    Page<Dataset> findByStatus(Dataset.DatasetStatus status, Pageable pageable);
}
```

### 3. Page 是抽象类无法实例化
**症状**：
```
org.springframework.data.domain.Page is abstract; cannot be instantiated
```

**解决方案**：使用 PageImpl
```java
import org.springframework.data.domain.PageImpl;

return new PageImpl<>(
    filtered,
    result.getPageable(),
    result.getTotalElements()
);
```

### 4. MQTT v5 API 兼容性
**症状**：
```
cannot find symbol: method addActionCallback()
cannot find symbol: class MqttDisconnectResponse
```

**解决方案**：
```java
// 正确的 MQTT v5 导入
import org.eclipse.paho.mqttv5.client.MqttDisconnectResponse;

// 实现 MqttCallback 所有抽象方法
mqttClient.setCallback(new MqttCallback() {
    @Override
    public void messageArrived(String topic, MqttMessage message) { }

    @Override
    public void authPacketArrived(int reasonCode, MqttProperties properties) { }

    @Override
    public void connectComplete(boolean reconnect, String serverURI) { }

    @Override
    public void disconnected(MqttDisconnectResponse disconnectResponse) { }

    @Override
    public void mqttErrorOccurred(MqttException exception) { }

    @Override
    public void deliveryComplete(IMqttToken token) { }
});
```

### 5. HQL INTERVAL 语法不支持
**症状**：
```
mismatched input ''5 minutes'', expecting one of: DAY, HOUR, MINUTE...
```

**解决方案**：使用原生 SQL
```java
@Query(value = "SELECT * FROM devices WHERE status = 'ONLINE' " +
           "AND last_heartbeat < CURRENT_TIMESTAMP - INTERVAL '5 minutes'",
       nativeQuery = true)
List<Device> findOfflineDevices();
```

## Python 训练服务问题

### 1. S3 下载失败
**症状**：`botocore.exceptions.EndpointConnectionError`

**解决方案**：检查 SeaweedFS 服务状态
```bash
# 检查服务是否运行
docker ps | grep seaweed

# 检查 S3 API 是否可访问
curl http://localhost:8888
```

### 2. TensorRT 转换失败
**症状**：`trtexec: not found`

**解决方案**：使用 Python API 作为备选
```python
try:
    subprocess.run(['trtexec', ...])
except FileNotFoundError:
    # 回退到 Python API
    self._convert_to_engine_python_api(onnx_path, output_file, half, int8)
```

## Docker 问题

### 1. 后端容器无法连接数据库
**症状**：`Connection refused` 或 `could not connect to server`

**解决方案**：
```bash
# 检查网络
docker network inspect edge-cloud-network

# 确保服务在同一网络
docker-compose ps --format json | jq '.[] | select(.Networks[].Name | contains("edge-cloud-network"))'

# 检查数据库是否就绪
docker exec edge_cloud_postgres pg_isready
```

### 2. 构建缓存导致代码不更新
**症状**：修改代码后重建仍使用旧代码

**解决方案**：
```bash
# 清理构建缓存
docker-compose build --no-cache backend

# 或删除旧镜像
docker rmi docker-backend:latest
docker-compose build backend
```

### 3. Windows 路径问题
**症状**：`invalid path 'D:\github\...'`

**解决方案**：使用 Git Bash 或 WSL
```bash
# Git Bash 中使用 /d/ 路径格式
cd /d/github/edge_infer_cloud

# 或使用 wsl2
wsl cd /mnt/d/github/edge_infer_cloud
```

## 前端问题

### 1. API 跨域错误
**症状**：`CORS policy: No 'Access-Control-Allow-Origin' header`

**解决方案**：后端添加 CORS 配置（已完成）

### 2. WebSocket 连接失败
**症状**：`WebSocket connection failed`

**解决方案**：检查代理配置
```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8081',
        changeOrigin: true
      }
    }
  }
})
```

## 边缘端 MQTT 问题

### 1. mosquitto_loop_start 与 mosquitto_loop 冲突导致 segfault
**症状**：
```
SIGSEGV (segmentation fault) in mosquitto internal thread
MQTT 客户端断线后无法自动重连
```

**根因**：`mosquitto_loop_start()` 创建后台线程运行事件循环，同时在主循环中调用 `mosquitto_loop(0)` 导致两个线程同时操作 `mosq_` 句柄。

**解决方案**：移除 RunOnce() 中的 `mqtt_client_->Loop(0)` 调用，仅使用 `mosquitto_loop_start` + `mosquitto_reconnect_delay_set` 处理自动重连。
```cpp
// OnDisconnectCallback 中不要手动调用 mosquitto_reconnect
// mosquitto_loop_start 已创建后台线程并配合 reconnect_delay_set 自动重连
void MqttClient::OnDisconnectCallback(...) {
    client->connected_ = false;
    LOG_WARN("MQTT disconnected, loop_start will auto-reconnect");
    // 不要: mosquitto_reconnect(mosq);  // 会导致 segfault
}
```

### 2. 云端转发发送了已标注帧
**症状**：云端收到的帧带有检测框标注，而非原始帧。

**根因**：OutputLoop 中先调用 `Output()` 画框标注，再转发帧到云端。`Output()` 通过 `const_cast` 就地修改了帧数据。

**解决方案**：重排 OutputLoop 顺序，先转发原始帧再调用 `Output()` 画框。
```cpp
void Framework::OutputLoop() {
    // 1. 先转发原始帧到云端
    if (cloud_forward_enabled) { ... publish raw frame ... }
    // 2. 再画框标注 + 推流
    result_output_.Output(task.frame, ...);
}
```

## 性能优化建议

### 1. 数据库查询优化
- 使用 `@EntityGraph` 避免 N+1 查询
- 添加适当的数据库索引
- 使用分页查询大数据集

### 2. MQTT 性能
- 使用 QoS 1 保证消息到达
- 批量处理设备状态上报
- 合理设置心跳间隔

### 3. 存储优化
- 定期清理过期的训练日志
- 使用 S3 生命周期策略
- 压缩历史模型文件
