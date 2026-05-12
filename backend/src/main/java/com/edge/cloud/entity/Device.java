package com.edge.cloud.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.ToString;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

/**
 * 设备实体
 */
@Data
@Entity
@Table(name = "devices")
@ToString(exclude = {})
public class Device {

    @Id
    @Column(name = "device_id", length = 50)
    private String deviceId;

    @Column(name = "device_name", length = 200)
    private String deviceName;

    @Column(name = "device_type", length = 50)
    private String deviceType;

    @Column(name = "group_id", length = 50)
    private String groupId;

    @Column(name = "ip", length = 50)
    private String ip;

    @Column(name = "mac", length = 50)
    private String mac;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", length = 50)
    private DeviceStatus status;

    @Column(name = "cpu_usage")
    private Float cpuUsage;

    @Column(name = "gpu_usage")
    private Float gpuUsage;

    @Column(name = "memory_usage")
    private Float memoryUsage;

    @Column(name = "disk_usage")
    private Float diskUsage;

    @Column(name = "current_model_id", length = 50)
    private String currentModelId;

    @Column(name = "current_version", length = 50)
    private String currentVersion;

    @Column(name = "current_firmware_version", length = 50)
    private String currentFirmwareVersion;

    @Column(name = "inference_fps")
    private Float inferenceFps;

    @Column(name = "mqtt_topic", length = 200)
    private String mqttTopic;

    // 设备扩展信息
    @Column(name = "device_category", length = 30)
    private String deviceCategory;

    @Column(name = "capabilities", length = 200)
    private String capabilities;

    @Column(name = "protocol", length = 30)
    private String protocol;

    @Column(name = "labels", columnDefinition = "TEXT")
    private String labels;

    // 硬件信息
    @Column(name = "os_version", length = 255)
    private String osVersion;

    @Column(name = "agent_version", length = 50)
    private String agentVersion;

    @Column(name = "gpu_model", length = 255)
    private String gpuModel;

    @Column(name = "gpu_memory_mb")
    private Integer gpuMemoryMb;

    @Column(name = "total_memory_mb")
    private Integer totalMemoryMb;

    @Column(name = "total_disk_mb")
    private Integer totalDiskMb;

    @Column(name = "temperature")
    private Float temperature;

    @Column(name = "uptime_seconds")
    private Long uptimeSeconds;

    @Column(name = "last_heartbeat")
    private LocalDateTime lastHeartbeat;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public enum DeviceStatus {
        ONLINE,
        OFFLINE,
        UPGRADING,
        ERROR
    }
}
