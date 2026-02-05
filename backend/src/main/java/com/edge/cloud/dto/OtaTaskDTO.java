package com.edge.cloud.dto;

import com.edge.cloud.entity.OtaTask;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * OTA 升级任务 DTO
 */
@Data
public class OtaTaskDTO {

    private String taskId;
    private String taskName;
    private OtaTask.UpgradeType upgradeType;
    private String modelId;
    private String targetVersion;
    private OtaTask.UpgradeStrategy strategy;
    private LocalDateTime scheduledTime;
    private OtaTask.OtaStatus status;
    private Integer totalDevices;
    private Integer completedDevices;
    private Integer failedDevices;
    private Integer progress;  // 计算字段：完成百分比
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    // 关联信息
    private String modelName;
}
