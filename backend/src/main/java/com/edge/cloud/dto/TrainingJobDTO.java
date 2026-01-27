package com.edge.cloud.dto;

import com.edge.cloud.entity.TrainingJob;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 训练任务 DTO
 */
@Data
public class TrainingJobDTO {

    private String jobId;
    private String jobName;
    private String datasetId;
    private String baseModelId;
    private String outputModelId;
    private Integer epochs;
    private Integer batchSize;
    private Integer imgSize;
    private Boolean useGpu;
    private TrainingJob.TrainingType trainingType;
    private Map<String, Object> hyperparameters;
    private TrainingJob.TrainingStatus status;
    private Integer currentEpoch;
    private Float progress;
    private Float finalMap;
    private Float finalLoss;
    private Integer bestEpoch;
    private String mlflowRunId;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    // 关联信息
    private String datasetName;
    private String baseModelName;
    private String outputModelName;
}
