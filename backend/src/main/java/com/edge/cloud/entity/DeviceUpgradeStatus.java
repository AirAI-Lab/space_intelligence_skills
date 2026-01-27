package com.edge.cloud.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

import com.edge.cloud.entity.OtaTask;

/**
 * 设备升级状态实体
 */
@Data
@Entity
@Table(name = "device_upgrade_status")
public class DeviceUpgradeStatus {

    @Id
    @Column(name = "status_id", length = 50)
    private String statusId;

    @Column(name = "task_id", length = 50, nullable = false)
    private String taskId;

    @Column(name = "device_id", length = 50, nullable = false)
    private String deviceId;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", length = 50)
    private UpgradeStatus status;

    @Column(name = "progress")
    private Integer progress = 0;

    @Lob
    @Column(name = "error_message", columnDefinition = "text")
    private String errorMessage;

    @Column(name = "download_start_time")
    private LocalDateTime downloadStartTime;

    @Column(name = "download_complete_time")
    private LocalDateTime downloadCompleteTime;

    @Column(name = "install_start_time")
    private LocalDateTime installStartTime;

    @Column(name = "install_complete_time")
    private LocalDateTime installCompleteTime;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    // 关联的 OTA 任务（用于获取任务详情）
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "task_id", insertable = false, updatable = false)
    private OtaTask task;

    public enum UpgradeStatus {
        PENDING,
        DOWNLOADING,
        DOWNLOAD_FAILED,
        DOWNLOADED,
        INSTALLING,
        INSTALL_FAILED,
        INSTALLED,
        VERIFYING,
        COMPLETED,
        ROLLED_BACK,
        FAILED
    }
}
