package com.edge.cloud.dto;

import com.edge.cloud.entity.DeviceUpgradeStatus;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 设备升级状态 DTO
 */
@Data
public class DeviceUpgradeStatusDTO {

    private String statusId;
    private String taskId;
    private String deviceId;
    private DeviceUpgradeStatus.UpgradeStatus status;
    private Integer progress;
    private String currentStage;  // 当前阶段: downloading, verifying, converting, applying
    private String errorMessage;
    private LocalDateTime downloadStartTime;
    private LocalDateTime downloadCompleteTime;
    private LocalDateTime installStartTime;
    private LocalDateTime installCompleteTime;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    // 关联信息
    private String deviceName;
}
