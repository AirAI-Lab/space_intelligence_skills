package com.edge.cloud.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.eclipse.paho.mqttv5.client.IMqttToken;
import org.eclipse.paho.mqttv5.client.MqttClient;
import org.eclipse.paho.mqttv5.client.MqttConnectionOptions;
import org.eclipse.paho.mqttv5.client.MqttDisconnectResponse;
import org.eclipse.paho.mqttv5.common.MqttException;
import org.eclipse.paho.mqttv5.common.MqttMessage;
import org.eclipse.paho.mqttv5.common.packet.MqttProperties;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import java.util.Map;

import lombok.RequiredArgsConstructor;

/**
 * MQTT 服务（支持 OTA 升级）
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MqttService {

    private final OtaService otaService;

    @Value("${MQTT_BROKER_URL:tcp://localhost:1883}")
    private String brokerUrl;

    @Value("${MQTT_CLIENT_ID:edge_cloud_backend}")
    private String clientId;

    @Value("${MQTT_USERNAME:admin}")
    private String username;

    @Value("${MQTT_PASSWORD:admin123456}")
    private String password;

    private MqttClient mqttClient;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @PostConstruct
    public void init() {
        try {
            mqttClient = new MqttClient(brokerUrl, clientId);
            MqttConnectionOptions options = new MqttConnectionOptions();
            options.setAutomaticReconnect(true);
            options.setCleanStart(true);
            options.setUserName(username);
            options.setPassword(password.getBytes());
            options.setConnectionTimeout(30);
            options.setKeepAliveInterval(60);

            mqttClient.connect(options);
            log.info("MQTT 客户端连接成功: brokerUrl={}, clientId={}", brokerUrl, clientId);

            // 订阅设备状态反馈主题
            subscribeToDeviceStatusTopics();

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

            // 设置消息回调
            mqttClient.setCallback(new org.eclipse.paho.mqttv5.client.MqttCallback() {
                @Override
                public void messageArrived(String topic, MqttMessage message) throws Exception {
                    handleDeviceMessage(topic, message);
                }

                @Override
                public void authPacketArrived(int reasonCode, MqttProperties properties) {
                    log.debug("MQTT 认证包到达: reasonCode={}", reasonCode);
                }

                @Override
                public void connectComplete(boolean reconnect, String serverURI) {
                    log.info("MQTT 连接{}成功: {}", reconnect ? "重连" : "初始", serverURI);
                }

                @Override
                public void disconnected(MqttDisconnectResponse disconnectResponse) {
                    log.warn("MQTT 连接断开: {}", disconnectResponse.getReasonString());
                }

                @Override
                public void mqttErrorOccurred(MqttException exception) {
                    log.error("MQTT 发生错误", exception);
                }

                @Override
                public void deliveryComplete(IMqttToken token) {
                    log.debug("MQTT 消息发送完成");
                }
            });

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
            log.debug("收到设备消息: topic={}, payload={}", topic, payload);

            // 解析主题: device/{device_id}/ota/status
            String[] topicParts = topic.split("/");
            if (topicParts.length >= 4) {
                String deviceId = topicParts[1];
                String messageType = topicParts[3];  // status

                if ("status".equals(messageType)) {
                    handleDeviceStatusMessage(deviceId, payload);
                }
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
            switch (status) {
                case "downloading":
                case "installing":
                    // 通过 OtaService 处理进度更新
                    try {
                        otaService.handleDeviceUpgradeProgress(taskId, deviceId, progress);
                    } catch (Exception e) {
                        log.error("处理设备升级进度失败: taskId={}, deviceId={}", taskId, deviceId, e);
                    }
                    break;
                case "completed":
                    // 通过 OtaService 处理完成
                    try {
                        otaService.handleDeviceUpgradeComplete(taskId, deviceId);
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
                    } catch (Exception e) {
                        log.error("处理设备升级失败错误: taskId={}, deviceId={}", taskId, deviceId, e);
                    }
                    break;
                default:
                    log.debug("未处理的设备状态: status={}, deviceId={}", status, deviceId);
            }

        } catch (Exception e) {
            log.error("处理设备状态消息失败: deviceId={}, payload={}", deviceId, payload, e);
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
            log.debug("MQTT 消息已发送: topic={}, payload={}", topic, payload);

        } catch (Exception e) {
            log.error("发送 MQTT 消息失败: topic={}", topic, e);
        }
    }

    /**
     * 发布 OTA 更新消息到设备
     */
    public void publishOtaUpdate(String deviceId, String taskId, String upgradeType,
                                  String targetVersion, String downloadUrl, String modelId) {
        String topic = "device/" + deviceId + "/ota/update";

        Map<String, Object> message = Map.of(
                "task_id", taskId,
                "upgrade_type", upgradeType,
                "target_version", targetVersion,
                "download_url", downloadUrl != null ? downloadUrl : "",
                "model_id", modelId != null ? modelId : "",
                "timestamp", System.currentTimeMillis()
        );

        publish(topic, message);
        log.info("OTA 更新消息已发送: deviceId={}, taskId={}, upgradeType={}",
                deviceId, taskId, upgradeType);
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
     * 广播消息到所有设备
     */
    public void broadcast(String topicSuffix, Map<String, Object> message) {
        String topic = "device/+/+" + topicSuffix;
        // MQTT 广播使用通配符，实际发送时需要针对每个设备
        log.info("广播消息: topicSuffix={}", topicSuffix);
    }
}
