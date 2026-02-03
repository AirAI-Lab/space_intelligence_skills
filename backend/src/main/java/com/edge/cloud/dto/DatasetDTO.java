package com.edge.cloud.dto;

import com.edge.cloud.entity.Dataset;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 数据集 DTO
 */
@Data
public class DatasetDTO {

    private String datasetId;
    private String datasetName;
    private Dataset.DatasetType datasetType;
    private String format;
    private String datasetSource;  // upload 或 local
    private String storagePath;
    private Integer categoryCount;
    private Integer sampleCount;
    private Integer trainCount;
    private Integer valCount;
    private Integer testCount;
    private Dataset.DatasetStatus status;
    private Map<String, Object> metadata;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
