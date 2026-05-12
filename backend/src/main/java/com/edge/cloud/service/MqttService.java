package com.edge.cloud.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken;
import org.eclipse.paho.client.mqttv3.MqttCallbackExtended;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.persist.MqttDefaultFilePersistence;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import java.io.File;
import java.util.Map;

import lombok.RequiredArgsConstructor;

/**
 * MQTT 服务（支持 OTA 升级）- 使用 MQTT v3.1.1
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MqttService {

    private final OtaService otaService;

    @Autowired
    @Lazy
    private InferenceResultService inferenceResultService;

    @Value("${mqtt.broker-url:${spring.mqtt.broker-url:tcp://localhost:1883}}")
    private String brokerUrl;

    @Value("${mqtt.client-id:${spring.mqtt.client-id:edge_cloud_backend}}")
    private String clientId;

    @Value("${mqtt.username:${spring.mqtt.username:admin}}")
    private String username;

    @Value("${mqtt.password:${spring.mqtt.password:admin123456}}")
    private String password;

    private MqttClient mqttClient;
    private final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new com.fasterxml.jackson.datatype.jsr310.JavaTimeModule());

    @PostConstruct
    public void init() {
        try {
            log.info("MQTT配置: brokerUrl={}, username={}, password={}", brokerUrl, username, "******");

            // 创建持久化目录
            String persistenceDir = System.getProperty("java.io.tmpdir") + File.separator + "mqtt" + File.separator + clientId;
            MqttDefaultFilePersistence persistence = new MqttDefaultFilePersistence(persistenceDir);

            mqttClient = new MqttClient(brokerUrl, clientId, persistence);
            MqttConnectOptions options = new MqttConnectOptions();
            options.setAutomaticReconnect(true);
            // 保持会话，重连后订阅不丢失
            options.setCleanSession(false);
            options.setUserName(username);
            options.setPassword(password.toCharArray());
            options.setConnectionTimeout(30);
            options.setKeepAliveInterval(120);
            // 设置遗嘱消息
            options.setWill("edge_cloud_backend/status", "offline".getBytes(), 1, false);

            mqttClient.setCallback(new MqttCallbackExtended() {
                @Override
                public void connectComplete(boolean reconnect, String serverURI) {
                    if (reconnect) {
                        log.info("MQTT 自动重连成功: serverURI={}", serverURI);
                    }
                }

                @Override
                public void connectionLost(Throwable cause) {
                    log.warn("MQTT 连接丢失，Paho 将自动重连: {}", cause.getMessage());
                }

                @Override
                public void messageArrived(String topic, MqttMessage message) throws Exception {
                    handleDeviceMessage(topic, message);
                }

                @Override
                public void deliveryComplete(IMqttDeliveryToken token) {
                    log.debug("MQTT 消息发送完成");
                }
            });

            mqttClient.connect(options);
            log.info("MQTT 客户端连接成功: brokerUrl={}, clientId={}", brokerUrl, clientId);

            // 订阅设备状态反馈主题
            subscribeToDeviceStatusTopics();

            // 订阅边缘推理结果主题
            String inferenceTopic = "device/+/inference/results";
            mqttClient.subscribe(inferenceTopic, 1);
            log.info("订阅边缘推理结果主题成功: {}", inferenceTopic);

            // 订阅统一结果 topic (EMQX 规则引擎归一化后的 topic)
            String unifiedResultsTopic = "results/#";
            mqttClient.subscribe(unifiedResultsTopic, 0);
            log.info("订阅统一结果主题成功: {}", unifiedResultsTopic);

        } catch (MqttException e) {
            log.error("MQTT 客户端连接失败", e);
        }
    }

    @PreDestroy
    public void destroy() {
        try {
            if (mqttClient != null && mqttClient.isConnected()) {
                mqttClient.disconnect();
                log.info("MQTT 客户端已断开连接");
            }
        } catch (MqttException e) {
            log.error("MQTT 客户端断开连接失败", e);
        }
    }

    /**
     * 订阅设备状态反馈主题
     */
    private void subscribeToDeviceStatusTopics() {
        try {
            // 订阅设备 OTA 状态反馈
            String otaStatusTopic = "device/+/ota/status";
            mqttClient.subscribe(otaStatusTopic, 1);
            log.info("订阅 OTA 状态主题成功: {}", otaStatusTopic);

        } catch (MqttException e) {
            log.error("订阅主题失败", e);
        }
    }

    /**
     * 处理设备消息
     */
    private void handleDeviceMessage(String topic, MqttMessage message) {
        try {
            String payload = new String(message.getPayload());
            log.debug("收到设备消息: topic={}, payload长度={}", topic, payload.length());

            // 解析主题: device/{device_id}/...
            String[] topicParts = topic.split("/");
            if (topicParts.length < 3) return;

            String deviceId = topicParts[1];

            // device/{device_id}/ota/status
            if (topicParts.length >= 4 && "ota".equals(topicParts[2]) && "status".equals(topicParts[3])) {
                handleDeviceStatusMessage(deviceId, payload);
                return;
            }

            // device/{device_id}/inference/results
            if (topicParts.length >= 4 && "inference".equals(topicParts[2]) && "results".equals(topicParts[3])) {
                handleInferenceResult(deviceId, payload);
                return;
            }

        } catch (Exception e) {
            log.error("处理设备消息失败: topic={}", topic, e);
        }
    }

    /**
     * 处理设备状态消息
     */
    private void handleDeviceStatusMessage(String deviceId, String payload) {
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> message = objectMapper.readValue(payload, Map.class);

            String taskId = (String) message.get("task_id");
            String status = (String) message.get("status");
            int progress = message.get("progress") != null ?
                    ((Number) message.get("progress")).intValue() : 0;
            String errorMessage = (String) message.get("error_message");

            // 根据 status 类型调用不同的处理方法
            // 边缘设备发送的状态: downloading, verifying, converting, applying, success, failed
            switch (status) {
                case "downloading":
                case "verifying":
                case "converting":
                case "applying":
                case "installing":
                    // 通过 OtaService 处理进度更新，传递当前阶段
                    try {
                        otaService.handleDeviceUpgradeProgress(taskId, deviceId, progress, status);
                        log.info("设备升级进度: taskId={}, deviceId={}, stage={}, progress={}%",
                                taskId, deviceId, status, progress);
                    } catch (Exception e) {
                        log.error("处理设备升级进度失败: taskId={}, deviceId={}", taskId, deviceId, e);
                    }
                    break;
                case "completed":
                case "success":
                    // 通过 OtaService 处理完成
                    try {
                        otaService.handleDeviceUpgradeComplete(taskId, deviceId);
                        log.info("设备升级完成: taskId={}, deviceId={}", taskId, deviceId);
                    } catch (Exception e) {
                        log.error("处理设备升级完成失败: taskId={}, deviceId={}", taskId, deviceId, e);
                    }
                    break;
                case "failed":
                case "download_failed":
                case "install_failed":
                    // 通过 OtaService 处理失败
                    try {
                        otaService.handleDeviceUpgradeFailed(taskId, deviceId, errorMessage);
                        log.warn("设备升级失败: taskId={}, deviceId={}, error={}", taskId, deviceId, errorMessage);
                    } catch (Exception e) {
                        log.error("处理设备升级失败错误: taskId={}, deviceId={}", taskId, deviceId, e);
                    }
                    break;
                default:
                    log.warn("未处理的设备状态: status={}, deviceId={}, taskId={}", status, deviceId, taskId);
            }

        } catch (Exception e) {
            log.error("处理设备状态消息失败: deviceId={}, payload={}", deviceId, payload, e);
        }
    }

    /**
     * 处理边缘推理结果 MQTT 消息 (device/{device_id}/inference/results)
     */
    private void handleInferenceResult(String deviceId, String payload) {
        try {
            com.edge.cloud.dto.InferenceResultRequest request =
                    objectMapper.readValue(payload, com.edge.cloud.dto.InferenceResultRequest.class);
            // 确保 device_id 一致
            if (request.getDeviceId() == null || request.getDeviceId().isEmpty()) {
                request.setDeviceId(deviceId);
            }
            inferenceResultService.saveEdgeResult(request);
            log.debug("MQTT边缘推理结果已存储: device={}, detections={}",
                    deviceId, request.getDetections() != null ? request.getDetections().size() : 0);
        } catch (Exception e) {
            log.error("处理MQTT边缘推理结果失败: device={}, payload长度={}", deviceId, payload.length(), e);
        }
    }

    /**
     * 发布消息到指定主题
     */
    public void publish(String topic, Map<String, Object> message) {
        try {
            if (mqttClient == null || !mqttClient.isConnected()) {
                log.warn("MQTT 客户端未连接，无法发送消息: topic={}", topic);
                return;
            }

            String payload = objectMapper.writeValueAsString(message);
            MqttMessage mqttMessage = new MqttMessage(payload.getBytes());
            mqttMessage.setQos(1);  // 至少一次
            mqttMessage.setRetained(false);

            mqttClient.publish(topic, mqttMessage);
            log.info("MQTT 消息已发送: topic={}, payload={}", topic, payload);

        } catch (Exception e) {
            log.error("发送 MQTT 消息失败: topic={}", topic, e);
        }
    }

    /**
     * 发布 OTA 更新消息到设备
     * 边缘设备期望订阅 topic: device/{device_id}/ota/command
     */
    public void publishOtaUpdate(String deviceId, String taskId, String upgradeType,
                                  String targetVersion, String downloadUrl, String modelId) {
        String topic = "device/" + deviceId + "/ota/command";

        Map<String, Object> message = Map.of(
                "task_id", taskId,
                "model_name", modelId != null ? modelId : "model",
                "model_version", targetVersion,
                "download_url", downloadUrl != null ? downloadUrl : "",
                "md5_checksum", "",
                "file_size", 0,
                "timestamp", System.currentTimeMillis()
        );

        publish(topic, message);
        log.info("OTA 更新消息已发送: deviceId={}, taskId={}, topic={}",
                deviceId, taskId, topic);
    }

    /**
     * 发布配置更新消息到设备
     */
    public void publishConfigUpdate(String deviceId, Map<String, Object> config) {
        String topic = "device/" + deviceId + "/config/update";

        Map<String, Object> message = new java.util.HashMap<>(config);
        message.put("timestamp", System.currentTimeMillis());

        publish(topic, message);
        log.info("配置更新消息已发送: deviceId={}", deviceId);
    }

    /**
     * 发布设备重启命令
     */
    public void publishDeviceRestart(String deviceId, String reason) {
        String topic = "device/" + deviceId + "/command/restart";

        Map<String, Object> message = Map.of(
                "reason", reason,
                "timestamp", System.currentTimeMillis()
        );

        publish(topic, message);
        log.info("设备重启命令已发送: deviceId={}, reason={}", deviceId, reason);
    }

    /**
     * 触发云端推理：通知边缘设备发送当前帧到云端进行 C-RADIOv4 分割
     */
    public void triggerCloudInference(String deviceId) {
        String topic = "device/" + deviceId + "/cloud/frame";

        Map<String, Object> message = Map.of(
                "action", "cloud_infer",
                "timestamp", System.currentTimeMillis()
        );

        publish(topic, message);
        log.info("云端推理触发命令已发送: deviceId={}", deviceId);
    }

    /**
     * 广播消息到所有设备
     */
    public void broadcast(String topicSuffix, Map<String, Object> message) {
        String topic = "device/+/+" + topicSuffix;
        // MQTT 广播使用通配符，实际发送时需要针对每个设备
        log.info("广播消息: topicSuffix={}", topicSuffix);
    }
}
