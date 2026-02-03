package com.edge.cloud.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.LocalDateTime;

/**
 * 模型部署记录实体
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "model_deployment")
public class ModelDeployment {

    @Id
    @Column(name = "deployment_id", length = 50)
    private String deploymentId;

    @Column(name = "model_id", length = 50, nullable = false)
    private String modelId;

    @Column(name = "model_name", length = 200)
    private String modelName;

    @Column(name = "device_id", length = 50, nullable = false)
    private String deviceId;

    @Column(name = "device_name", length = 200)
    private String deviceName;

    /**
     * 部署类型: SINGLE, BATCH, GRADUAL, AB_TEST
     */
    @Column(name = "deployment_type", length = 20, nullable = false)
    private String deploymentType;

    /**
     * 部署状态: DEPLOYING, SUCCESS, FAILED, ROLLED_BACK
     */
    @Column(name = "status", length = 20, nullable = false)
    private String status;

    @Column(name = "previous_model_id", length = 50)
    private String previousModelId;

    @Column(name = "previous_model_name", length = 200)
    private String previousModelName;

    @Column(name = "ota_task_id", length = 50)
    private String otaTaskId;

    @Column(name = "deployed_by", length = 50)
    private String deployedBy;

    @Column(name = "deployed_at")
    private LocalDateTime deployedAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @Column(name = "rollback_at")
    private LocalDateTime rollbackAt;

    @Column(name = "error_message", length = 500)
    private String errorMessage;

    @Column(name = "inference_fps")
    private Float inferenceFps;

    @Column(name = "memory_usage_mb")
    private Integer memoryUsageMb;

    @Column(name = "gpu_utilization")
    private Float gpuUtilization;

    @Column(name = "is_ab_test")
    private Boolean isAbTest;

    @Column(name = "ab_test_group", length = 20)
    private String abTestGroup; // A, B, CONTROL

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
        if (status == null) {
            status = "DEPLOYING";
        }
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }

    /**
     * 部署状态枚举
     */
    public enum DeploymentStatus {
        DEPLOYING,
        SUCCESS,
        FAILED,
        ROLLED_BACK
    }

    /**
     * 部署类型枚举
     */
    public enum DeploymentType {
        SINGLE,      // 单设备部署
        BATCH,       // 批量部署
        GRADUAL,     // 灰度发布
        AB_TEST      // A/B测试
    }
}
