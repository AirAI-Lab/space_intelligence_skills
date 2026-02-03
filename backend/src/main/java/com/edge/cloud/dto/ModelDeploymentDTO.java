package com.edge.cloud.dto;

import com.edge.cloud.entity.ModelDeployment;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 模型部署记录 DTO
 */
@Data
public class ModelDeploymentDTO {

    private String deploymentId;
    private String modelId;
    private String modelName;
    private String deviceId;
    private String deviceName;
    private String deploymentType;
    private String status;
    private String previousModelId;
    private String previousModelName;
    private String otaTaskId;
    private String deployedBy;
    private LocalDateTime deployedAt;
    private LocalDateTime completedAt;
    private LocalDateTime rollbackAt;
    private String errorMessage;
    private Float inferenceFps;
    private Integer memoryUsageMb;
    private Float gpuUtilization;
    private Boolean isAbTest;
    private String abTestGroup;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    // 扩展字段
    private Long durationMs;        // 部署耗时（毫秒）
    private String durationText;    // 部署耗时文本描述
    private String statusText;      // 状态文本描述
    private String typeText;        // 类型文本描述

    /**
     * 从实体转换为DTO
     */
    public static ModelDeploymentDTO fromEntity(ModelDeployment entity) {
        ModelDeploymentDTO dto = new ModelDeploymentDTO();
        dto.setDeploymentId(entity.getDeploymentId());
        dto.setModelId(entity.getModelId());
        dto.setModelName(entity.getModelName());
        dto.setDeviceId(entity.getDeviceId());
        dto.setDeviceName(entity.getDeviceName());
        dto.setDeploymentType(entity.getDeploymentType());
        dto.setStatus(entity.getStatus());
        dto.setPreviousModelId(entity.getPreviousModelId());
        dto.setPreviousModelName(entity.getPreviousModelName());
        dto.setOtaTaskId(entity.getOtaTaskId());
        dto.setDeployedBy(entity.getDeployedBy());
        dto.setDeployedAt(entity.getDeployedAt());
        dto.setCompletedAt(entity.getCompletedAt());
        dto.setRollbackAt(entity.getRollbackAt());
        dto.setErrorMessage(entity.getErrorMessage());
        dto.setInferenceFps(entity.getInferenceFps());
        dto.setMemoryUsageMb(entity.getMemoryUsageMb());
        dto.setGpuUtilization(entity.getGpuUtilization());
        dto.setIsAbTest(entity.getIsAbTest());
        dto.setAbTestGroup(entity.getAbTestGroup());
        dto.setCreatedAt(entity.getCreatedAt());
        dto.setUpdatedAt(entity.getUpdatedAt());

        // 计算部署耗时
        if (entity.getDeployedAt() != null && entity.getCompletedAt() != null) {
            long duration = java.time.Duration.between(entity.getDeployedAt(), entity.getCompletedAt()).toMillis();
            dto.setDurationMs(duration);
            dto.setDurationText(formatDuration(duration));
        }

        // 设置状态文本
        dto.setStatusText(getStatusText(entity.getStatus()));
        dto.setTypeText(getTypeText(entity.getDeploymentType()));

        return dto;
    }

    private static String formatDuration(long milliseconds) {
        long seconds = milliseconds / 1000;
        if (seconds < 60) {
            return seconds + "秒";
        }
        long minutes = seconds / 60;
        long remainingSeconds = seconds % 60;
        if (minutes < 60) {
            return minutes + "分" + remainingSeconds + "秒";
        }
        long hours = minutes / 60;
        long remainingMinutes = minutes % 60;
        return hours + "小时" + remainingMinutes + "分";
    }

    private static String getStatusText(String status) {
        if (status == null) return "未知";
        return switch (status) {
            case "DEPLOYING" -> "部署中";
            case "SUCCESS" -> "成功";
            case "FAILED" -> "失败";
            case "ROLLED_BACK" -> "已回滚";
            default -> status;
        };
    }

    private static String getTypeText(String type) {
        if (type == null) return "未知";
        return switch (type) {
            case "SINGLE" -> "单设备部署";
            case "BATCH" -> "批量部署";
            case "GRADUAL" -> "灰度发布";
            case "AB_TEST" -> "A/B测试";
            default -> type;
        };
    }
}
