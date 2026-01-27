package com.edge.cloud.dto;

import com.edge.cloud.entity.TrainingJob;
import lombok.Data;

import java.util.Map;

/**
 * 创建训练任务请求
 */
@Data
public class TrainingJobCreateRequest {

    private String jobName;
    private String datasetId;
    private String baseModelId;           // 基础模型ID（用于微调）
    private TrainingJob.TrainingType trainingType;
    private Integer epochs = 100;
    private Integer batchSize = 16;
    private Integer imgSize = 640;
    private Boolean useGpu = true;

    // 超参数
    private Map<String, Object> hyperparameters;
}
