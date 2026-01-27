package com.edge.cloud.dto;

import com.edge.cloud.entity.Model;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 模型 DTO
 */
@Data
public class ModelDTO {

    private String modelId;
    private String modelName;
    private Model.ModelType modelType;
    private String framework;
    private String version;
    private String parentModelId;
    private String datasetId;
    private String ptFilePath;
    private String onnxFilePath;
    private String engineFilePath;
    private Float map;
    private Float precision;
    private Float recall;
    private Float inferenceTimeMs;
    private Integer inputWidth;
    private Integer inputHeight;
    private List<String> classNames;
    private Model.ModelStatus status;
    private Long fileSizeBytes;
    private Integer deployedCount;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    // 关联信息
    private String parentModelName;
    private String datasetName;
}
