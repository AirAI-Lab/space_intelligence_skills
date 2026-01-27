package com.edge.cloud.dto;

import com.edge.cloud.entity.ConversionTask;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 模型转换任务 DTO
 */
@Data
public class ConversionTaskDTO {

    private String taskId;
    private String modelId;
    private ConversionTask.ModelFormat sourceFormat;
    private ConversionTask.ModelFormat targetFormat;
    private ConversionTask.ConversionType conversionType;
    private ConversionTask.ConversionStatus status;
    private Float progress;
    private String errorMessage;
    private String outputFilePath;
    private Long fileSizeBytes;
    private Integer optimizationTimeSeconds;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    // 关联信息
    private String modelName;
}
