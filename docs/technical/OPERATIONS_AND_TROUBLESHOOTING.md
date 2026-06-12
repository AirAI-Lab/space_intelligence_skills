# 运维与故障排查

## 1. 文档定位

本文档面向开发、实施和运维人员。部署流程以根目录 `README_DOCKER.md` 为准，本文档补充运行维护和常见故障处理。

## 2. 服务清单

核心服务：

- backend。
- frontend。
- PostgreSQL/TimescaleDB。
- Redis。
- EMQX。
- SeaweedFS。
- ZLMediaKit。
- training-service。
- cloud-infer-service。

可选服务：

- MLflow。
- TensorBoard。

## 3. 健康检查

需要检查：

- 后端健康。
- 数据库连接。
- Redis 连接。
- EMQX 连接。
- S3 存储连接。
- ZLMediaKit API。
- 训练服务。
- 推理服务。
- 大模型供应商。
- 地图服务。

## 4. MLflow 故障

问题链路：

1. Ultralytics 自动注册 MLflow callback。
2. 训练启动时调用 `mlflow.set_experiment()`。
3. 尝试连接 `http://mlflow:5000`。
4. 容器重建后 DNS 解析失败。
5. 训练崩溃。

处理策略：

- 默认设置 `MLFLOW_ENABLED=false`。
- 默认设置 `TRAINING_TRACKING_MODE=platform`。
- 训练服务不主动调用 `mlflow.set_experiment()`。
- MLflow 写入失败只记录 warning。
- 启用 MLflow 时必须确保服务名、网络、healthcheck 和持久化配置正确。

## 5. 视频无法预览

排查顺序：

1. 检查源 RTSP/RTMP 地址。
2. 检查 ZLMediaKit 容器状态。
3. 检查拉流代理是否创建成功。
4. 检查播放 URL。
5. 检查浏览器播放协议支持。
6. 检查播放鉴权。

## 6. 边缘结果不上报

排查顺序：

1. 检查 `edge_infer` 运行状态。
2. 检查设备心跳。
3. 检查 MQTT 连接。
4. 检查 topic 配置。
5. 检查设备 ID、通道 ID、任务 ID 是否一致。
6. 检查后端接收接口日志。

## 7. 地图无法显示

排查顺序：

1. 检查地图供应商配置。
2. 检查 Token。
3. 检查网络访问。
4. 检查坐标系。
5. 检查图层 URL。
6. 检查浏览器控制台错误。

## 8. 大模型调用失败

排查顺序：

1. 检查供应商启用状态。
2. 检查 API Key。
3. 检查 Base URL。
4. 检查模型名。
5. 检查网络连通性。
6. 检查调用限额。
7. 检查用户权限和脱敏规则。

## 9. 备份恢复

需要备份：

- PostgreSQL 数据。
- SeaweedFS/S3 文件。
- `.env` 配置。
- 模型文件。
- 报表文件。
- 地图和大模型供应商配置。

