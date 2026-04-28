package com.edge.cloud.service;

import com.edge.cloud.dto.DeviceUpgradeStatusDTO;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

import java.util.Map;

/**
 * WebSocket消息服务
 * 用于向前端实时推送训练日志、OTA进度等消息
 */
@Service
@Slf4j
public class WebSocketMessageService {

    private final SimpMessagingTemplate messagingTemplate;
    private final ObjectMapper objectMapper;

    public WebSocketMessageService(
            SimpMessagingTemplate messagingTemplate,
            ObjectMapper objectMapper
    ) {
        this.messagingTemplate = messagingTemplate;
        this.objectMapper = objectMapper;
    }

    /**
     * 广播消息到所有订阅指定主题的客户端
     *
     * @param topic   主题（例如：/topic/training/progress）
     * @param payload 消息内容
     */
    public void broadcast(String topic, Object payload) {
        try {
            messagingTemplate.convertAndSend(topic, payload);
            log.debug("广播消息到 {}: {}", topic, objectMapper.writeValueAsString(payload));
        } catch (Exception e) {
            log.error("广播消息失败: topic={}, error={}", topic, e.getMessage());
        }
    }

    /**
     * 发送消息到指定用户
     *
     * @param user    用户标识
     * @param topic   主题
     * @param payload 消息内容
     */
    public void sendToUser(String user, String topic, Object payload) {
        try {
            messagingTemplate.convertAndSendToUser(user, topic, payload);
            log.debug("发送消息到用户 {}: {}", user, objectMapper.writeValueAsString(payload));
        } catch (Exception e) {
            log.error("发送用户消息失败: user={}, error={}", user, e.getMessage());
        }
    }

    // ==================== 训练相关消息 ====================

    /**
     * 发送训练进度更新
     *
     * @param jobId    训练任务ID
     * @param progress 进度信息
     */
    public void sendTrainingProgress(String jobId, Map<String, Object> progress) {
        broadcast("/topic/training/" + jobId + "/progress", progress);
    }

    /**
     * 发送训练日志
     *
     * @param jobId 训练任务ID
     * @param log   日志内容
     */
    public void sendTrainingLog(String jobId, String log) {
        broadcast("/topic/training/" + jobId + "/log", Map.of(
                "jobId", jobId,
                "message", log,
                "timestamp", System.currentTimeMillis()
        ));
    }

    /**
     * 发送训练完成通知
     *
     * @param jobId    训练任务ID
     * @param metrics  最终指标
     */
    public void sendTrainingComplete(String jobId, Map<String, Object> metrics) {
        broadcast("/topic/training/" + jobId + "/complete", Map.of(
                "jobId", jobId,
                "metrics", metrics,
                "timestamp", System.currentTimeMillis()
        ));
    }

    // ==================== OTA相关消息 ====================

    /**
     * 发送OTA任务进度更新
     *
     * @param taskId OTA任务ID
     * @param data   进度数据
     */
    public void sendOtaTaskProgress(String taskId, Map<String, Object> data) {
        broadcast("/topic/ota/" + taskId + "/progress", data);
    }

    /**
     * 发送设备升级状态更新
     *
     * @param taskId  OTA任务ID
     * @param status  设备升级状态
     */
    public void sendDeviceUpgradeStatus(String taskId, DeviceUpgradeStatusDTO status) {
        broadcast("/topic/ota/" + taskId + "/devices", status);
    }

    /**
     * 发送OTA任务完成通知
     *
     * @param taskId     OTA任务ID
     * @param success    是否成功
     * @param message    消息
     */
    public void sendOtaTaskComplete(String taskId, boolean success, String message) {
        broadcast("/topic/ota/" + taskId + "/complete", Map.of(
                "taskId", taskId,
                "success", success,
                "message", message,
                "timestamp", System.currentTimeMillis()
        ));
    }

    // ==================== 模型相关消息 ====================

    // ==================== 推理结果相关消息 ====================

    /**
     * 发送推理结果到设备专属topic
     */
    public void sendInferenceResult(String deviceId, Object result) {
        broadcast("/topic/inference/" + deviceId + "/results", result);
    }

    /**
     * 发送告警到全局告警topic
     */
    public void sendInferenceAlert(Object alert) {
        broadcast("/topic/inference/alerts", alert);
    }

    /**
     * 发送模型转换进度
     *
     * @param modelId  模型ID
     * @param progress 进度百分比
     * @param status   状态描述
     */
    public void sendModelConversionProgress(String modelId, int progress, String status) {
        broadcast("/topic/model/" + modelId + "/conversion", Map.of(
                "modelId", modelId,
                "progress", progress,
                "status", status,
                "timestamp", System.currentTimeMillis()
        ));
    }

    /**
     * 发送模型分析完成通知
     *
     * @param modelId 模型ID
     * @param result  分析结果
     */
    public void sendModelAnalysisComplete(String modelId, Map<String, Object> result) {
        broadcast("/topic/model/" + modelId + "/analysis", result);
    }
}
