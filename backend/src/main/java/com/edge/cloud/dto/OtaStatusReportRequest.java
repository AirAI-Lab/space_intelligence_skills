package com.edge.cloud.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * OTA升级状态上报请求 (边缘端 -> 云端)
 */
@Data
public class OtaStatusReportRequest {

    /**
     * 任务ID
     */
    @JsonProperty("task_id")
    private String taskId;

    /**
     * 设备ID
     */
    @JsonProperty("device_id")
    private String deviceId;

    /**
     * 升级状态: PENDING, DOWNLOADING, VERIFYING, APPLYING, COMPLETED, FAILED
     */
    private String status;

    /**
     * 进度 (0-100)
     */
    private Integer progress;

    /**
     * 错误信息 (失败时)
     */
    private String error;

    /**
     * 时间戳
     */
    private LocalDateTime timestamp;
}
