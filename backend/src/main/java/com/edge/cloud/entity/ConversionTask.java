package com.edge.cloud.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

/**
 * 模型转换任务实体
 */
@Data
@Entity
@Table(name = "conversion_tasks")
public class ConversionTask {

    @Id
    @Column(name = "task_id", length = 50)
    private String taskId;

    @Column(name = "model_id", length = 50)
    private String modelId;

    @Enumerated(EnumType.STRING)
    @Column(name = "source_format", length = 20)
    private ModelFormat sourceFormat;

    @Enumerated(EnumType.STRING)
    @Column(name = "target_format", length = 20)
    private ModelFormat targetFormat;

    @Enumerated(EnumType.STRING)
    @Column(name = "conversion_type", length = 50)
    private ConversionType conversionType;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", length = 50)
    private ConversionStatus status;

    @Column(name = "progress")
    private Float progress = 0.0f;

    @Lob
    @Column(name = "error_message", columnDefinition = "text")
    private String errorMessage;

    @Column(name = "output_file_path", length = 500)
    private String outputFilePath;

    @Column(name = "file_size_bytes")
    private Long fileSizeBytes;

    @Column(name = "optimization_time_seconds")
    private Integer optimizationTimeSeconds;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public enum ModelFormat {
        PT,      // PyTorch
        ONNX,    // ONNX
        ENGINE,  // TensorRT
        TORCHSCRIPT
    }

    public enum ConversionType {
        PT_TO_ONNX,
        ONNX_TO_ENGINE_FP16,
        ONNX_TO_ENGINE_INT8,
        ONNX_TO_ENGINE_FP32
    }

    public enum ConversionStatus {
        PENDING,
        RUNNING,
        COMPLETED,
        FAILED,
        CANCELLED
    }
}
