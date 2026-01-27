package com.edge.cloud.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;
import lombok.ToString;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 模型实体
 */
@Data
@Entity
@Table(name = "models")
@ToString(exclude = {"classNames"})
public class Model {

    @Id
    @Column(name = "model_id", length = 50)
    private String modelId;

    @Column(name = "model_name", nullable = false, length = 200)
    private String modelName;

    @Enumerated(EnumType.STRING)
    @Column(name = "model_type", nullable = false, length = 50)
    private ModelType modelType;

    @Column(name = "framework", length = 50)
    private String framework;

    @Column(name = "version", nullable = false, length = 50)
    private String version;

    @Column(name = "parent_model_id", length = 50)
    private String parentModelId;

    @Column(name = "dataset_id", length = 50)
    private String datasetId;

    @Column(name = "pt_file_path", length = 500)
    private String ptFilePath;

    @Column(name = "onnx_file_path", length = 500)
    private String onnxFilePath;

    @Column(name = "engine_file_path", length = 500)
    private String engineFilePath;

    @Column(name = "map")
    private Float map;

    @Column(name = "precision")
    private Float precision;

    @Column(name = "recall")
    private Float recall;

    @Column(name = "inference_time_ms")
    private Float inferenceTimeMs;

    @Column(name = "input_width")
    private Integer inputWidth;

    @Column(name = "input_height")
    private Integer inputHeight;

    @Lob
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "class_names", columnDefinition = "jsonb")
    private List<String> classNames;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", length = 50)
    private ModelStatus status;

    @Column(name = "file_size_bytes")
    private Long fileSizeBytes;

    @Column(name = "deployed_count")
    private Integer deployedCount = 0;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public enum ModelType {
        DETECTION,      // 目标检测
        CLASSIFICATION, // 图像分类
        SEGMENTATION,   // 语义分割
        POSE,          // 姿态估计
        OTHER
    }

    public enum ModelStatus {
        TRAINING,       // 训练中
        CONVERTING,     // 转换中
        READY,          // 就绪
        DEPLOYED,       // 已部署
        ARCHIVED,       // 已归档
        ERROR           // 错误
    }
}
