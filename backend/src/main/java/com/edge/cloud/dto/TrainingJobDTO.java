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
    private String datasetSource;  // backend, url, local
    private String datasetUrl;
    private String datasetPath;
    private String datasetName;
    private String baseModelId;
    private String baseModel;  // 预训练模型名称（如 yolov8n.pt）
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
    private Boolean resume;
    private String resumeJobId;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    // 关联信息（从关联实体获取）
    private String baseModelName;
    private String outputModelName;
}
