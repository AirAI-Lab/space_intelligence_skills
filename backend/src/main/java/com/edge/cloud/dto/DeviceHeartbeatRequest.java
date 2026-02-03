package com.edge.cloud.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 设备心跳请求 (边缘端 -> 云端)
 */
@Data
public class DeviceHeartbeatRequest {

    /**
     * 设备唯一标识
     */
    @JsonProperty("device_id")
    private String deviceId;

    /**
     * 设备名称
     */
    @JsonProperty("device_name")
    private String deviceName;

    /**
     * 设备类型: EDGE_BOX, JETSON_ORIN, JETSON_XAVIER, DRONE_BOX
     */
    @JsonProperty("device_type")
    private String deviceType;

    /**
     * IP地址
     */
    private String ip;

    /**
     * MAC地址
     */
    private String mac;

    /**
     * 操作系统版本
     */
    @JsonProperty("os_version")
    private String osVersion;

    /**
     * Agent版本
     */
    @JsonProperty("agent_version")
    private String agentVersion;

    /**
     * GPU型号
     */
    @JsonProperty("gpu_model")
    private String gpuModel;

    /**
     * GPU显存总量(MB)
     */
    @JsonProperty("gpu_memory")
    private Integer gpuMemory;

    /**
     * GPU显存使用量(MB)
     */
    @JsonProperty("gpu_memory_usage")
    private Integer gpuMemoryUsage;

    /**
     * CPU使用率 (0-100)
     */
    @JsonProperty("cpu_usage")
    private Float cpuUsage;

    /**
     * GPU使用率 (0-100)
     */
    @JsonProperty("gpu_usage")
    private Float gpuUsage;

    /**
     * 内存使用率 (0-100)
     */
    @JsonProperty("memory_usage")
    private Float memoryUsage;

    /**
     * 磁盘使用率 (0-100)
     */
    @JsonProperty("disk_usage")
    private Float diskUsage;

    /**
     * 设备温度 (摄氏度)
     */
    private Float temperature;

    /**
     * 当前运行模型ID
     */
    @JsonProperty("model_id")
    private String currentModelId;

    /**
     * 当前运行模型版本
     */
    @JsonProperty("model_version")
    private String currentModelVersion;

    /**
     * 推理FPS
     */
    @JsonProperty("inference_fps")
    private Float inferenceFps;

    /**
     * 设备运行时长(秒)
     */
    @JsonProperty("uptime_seconds")
    private Long uptimeSeconds;

    /**
     * 时间戳
     */
    private LocalDateTime timestamp;
}
