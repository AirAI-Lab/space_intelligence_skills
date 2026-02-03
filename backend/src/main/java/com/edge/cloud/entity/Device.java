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

    @Column(name = "mqtt_topic", length = 200)
    private String mqttTopic;

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
