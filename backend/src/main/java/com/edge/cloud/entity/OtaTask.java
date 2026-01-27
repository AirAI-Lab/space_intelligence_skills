package com.edge.cloud.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

/**
 * OTA 升级任务实体
 */
@Data
@Entity
@Table(name = "ota_tasks")
public class OtaTask {

    @Id
    @Column(name = "task_id", length = 50)
    private String taskId;

    @Column(name = "task_name", nullable = false, length = 200)
    private String taskName;

    @Enumerated(EnumType.STRING)
    @Column(name = "upgrade_type", length = 50)
    private UpgradeType upgradeType;

    @Column(name = "model_id", length = 50)
    private String modelId;

    @Column(name = "target_version", length = 50)
    private String targetVersion;

    @Enumerated(EnumType.STRING)
    @Column(name = "strategy", length = 50)
    private UpgradeStrategy strategy;

    @Column(name = "scheduled_time")
    private LocalDateTime scheduledTime;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", length = 50)
    private OtaStatus status;

    @Column(name = "total_devices")
    private Integer totalDevices;

    @Column(name = "completed_devices")
    private Integer completedDevices = 0;

    @Column(name = "failed_devices")
    private Integer failedDevices = 0;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public enum UpgradeType {
        MODEL,           // 模型升级
        FIRMWARE,        // 固件升级
        CONFIG           // 配置更新
    }

    public enum UpgradeStrategy {
        IMMEDIATE,       // 立即升级
        SCHEDULED,       // 定时升级
        GRADUAL,         // 灰度升级
        MANUAL           // 手动触发
    }

    public enum OtaStatus {
        PENDING,
        SCHEDULED,
        RUNNING,
        PAUSED,
        COMPLETED,
        FAILED,
        CANCELLED
    }
}
