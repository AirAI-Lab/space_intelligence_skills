package com.edge.cloud.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;
import lombok.ToString;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 训练任务实体
 */
@Data
@Entity
@Table(name = "training_jobs")
@ToString(exclude = {"hyperparameters"})
public class TrainingJob {

    @Id
    @Column(name = "job_id", length = 50)
    private String jobId;

    @Column(name = "job_name", nullable = false, length = 200)
    private String jobName;

    @Column(name = "dataset_id", length = 50)
    private String datasetId;

    // 数据集来源：backend, url, local
    @Column(name = "dataset_source", length = 20)
    private String datasetSource = "backend";

    // URL 数据集地址（datasetSource=url 时使用）
    @Column(name = "dataset_url", length = 500)
    private String datasetUrl;

    // 本地数据集路径（datasetSource=local 时使用）
    @Column(name = "dataset_path", length = 500)
    private String datasetPath;

    // 自定义数据集名称（datasetSource=url/local 时使用）
    @Column(name = "dataset_name", length = 200)
    private String datasetName;

    @Column(name = "base_model_id", length = 50)
    private String baseModelId;

    @Column(name = "base_model", length = 100)
    private String baseModel;  // 预训练模型名称（如 yolov8n.pt）

    @Column(name = "output_model_id", length = 50)
    private String outputModelId;

    @Column(name = "epochs", nullable = false)
    private Integer epochs;

    @Column(name = "batch_size", nullable = false)
    private Integer batchSize;

    @Column(name = "img_size", nullable = false)
    private Integer imgSize;

    @Column(name = "use_gpu")
    private Boolean useGpu = true;

    @Enumerated(EnumType.STRING)
    @Column(name = "training_type", length = 50)
    private TrainingType trainingType;

    @Lob
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "hyperparameters", columnDefinition = "jsonb")
    private Map<String, Object> hyperparameters;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", length = 50)
    private TrainingStatus status;

    @Column(name = "current_epoch")
    private Integer currentEpoch = 0;

    @Column(name = "progress")
    private Float progress = 0.0f;

    @Column(name = "final_map")
    private Float finalMap;

    @Column(name = "final_loss")
    private Float finalLoss;

    @Column(name = "best_epoch")
    private Integer bestEpoch;

    @Column(name = "mlflow_run_id", length = 100)
    private String mlflowRunId;

    @Column(name = "mlflow_experiment_id", length = 100)
    private String mlflowExperimentId;

    @Column(name = "resume")
    private Boolean resume = false;

    @Column(name = "resume_job_id", length = 50)
    private String resumeJobId;

    @Column(name = "enable_smart_optimization")
    private Boolean enableSmartOptimization = true;  // 是否启用智能参数优化（续训时）

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public enum TrainingType {
        FULL_TRAINING,       // 完整训练
        FINE_TUNING,         // 微调
        TRANSFER_LEARNING    // 迁移学习
    }

    public enum TrainingStatus {
        PENDING,            // 等待中
        RUNNING,            // 运行中
        PAUSED,             // 已暂停
        COMPLETED,          // 已完成
        FAILED,             // 失败
        CANCELLED           // 已取消
    }
}
