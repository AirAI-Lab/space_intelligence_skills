# API 与第三方集成文档

## 1. 集成范围

本文档面向开发人员、第三方系统和实施人员，说明平台对接边界和主要接口分类。

## 2. edge_infer 对接

通信方式：

- MQTT：心跳、资源状态、推理结果、命令回执。
- HTTP：模型包下载、证据上传、日志拉取、批量补传。
- RTSP/RTMP/WebRTC：视频流输入和输出。

推理结果基础字段：

- `deviceId`
- `channelId`
- `taskId`
- `modelId`
- `modelVersion`
- `capabilityCode`
- `timestamp`
- `frameId`
- `objects`
- `regions`
- `scores`
- `imageUrl`
- `videoClipUrl`
- `rawPayload`

## 3. ZLMediaKit 对接

平台调用 ZLMediaKit HTTP API：

- 创建拉流代理。
- 删除拉流代理。
- 获取流列表。
- 获取播放地址。
- 截图。
- 开始录像。
- 停止录像。

平台接收 ZLMediaKit WebHook：

- 流注册。
- 流注销。
- 播放事件。
- 推流事件。
- 录像完成。
- 鉴权请求。

## 4. 空间地图对接

地图供应商支持：

- 天地图。
- 离线瓦片。
- 私有 GIS。
- 后续三维地图和数字孪生引擎。

主要接口：

- 地图供应商配置。
- 图层配置。
- 区域边界。
- 点位管理。
- 轨迹查询。
- 告警热力图。
- 地图框选查询。

## 5. 大模型对接

支持网络 API、本地模型和混合模式。

供应商配置：

- `base_url`
- `api_key`
- `model`
- `timeout`
- `max_tokens`
- `temperature`
- 项目可见范围。

安全要求：

- 默认只发送脱敏后的结构化数据。
- 原始视频默认不发送给外部模型。
- 工具调用继承用户权限。
- 所有调用写入审计。

## 6. Webhook 对接

平台支持向第三方系统推送：

- 告警事件。
- 设备状态。
- 视频流状态。
- 训练任务状态。
- 模型部署状态。

Webhook 必须配置签名或 secret 校验。

## 7. 主要 REST 接口分类

- `/api/spatial/**`
- `/api/video/**`
- `/api/devices/**`
- `/api/algorithm/**`
- `/api/inference/**`
- `/api/alerts/**`
- `/api/datasets/**`
- `/api/training/**`
- `/api/models/**`
- `/api/assistant/**`
- `/api/system/**`

