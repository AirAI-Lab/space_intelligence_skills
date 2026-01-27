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
 * 数据集实体
 */
@Data
@Entity
@Table(name = "datasets")
@ToString(exclude = {"metadata"})
public class Dataset {

    @Id
    @Column(name = "dataset_id", length = 50)
    private String datasetId;

    @Column(name = "dataset_name", nullable = false, length = 200)
    private String datasetName;

    @Enumerated(EnumType.STRING)
    @Column(name = "dataset_type", nullable = false, length = 50)
    private DatasetType datasetType;

    @Column(name = "format", nullable = false, length = 50)
    private String format;

    @Column(name = "storage_path", length = 500)
    private String storagePath;

    @Column(name = "category_count")
    private Integer categoryCount;

    @Column(name = "sample_count")
    private Integer sampleCount;

    @Column(name = "train_count")
    private Integer trainCount;

    @Column(name = "val_count")
    private Integer valCount;

    @Column(name = "test_count")
    private Integer testCount;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", length = 50)
    private DatasetStatus status;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata", columnDefinition = "jsonb")
    private Map<String, Object> metadata;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public enum DatasetType {
        DETECTION,   // 目标检测
        CLASSIFICATION,  // 图像分类
        SEGMENTATION,    // 语义分割
        POSE,           // 姿态估计
        OTHER
    }

    public enum DatasetStatus {
        UPLOADING,
        VALIDATING,
        READY,
        ERROR,
        DELETED
    }
}
