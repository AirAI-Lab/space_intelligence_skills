package com.edge.cloud.dto;

import com.edge.cloud.entity.Model;
import lombok.Data;

/**
 * 创建模型请求
 */
@Data
public class ModelCreateRequest {

    private String modelName;
    private Model.ModelType modelType;
    private String framework;  // yolov8, pytorch, etc.
    private String version;
    private String parentModelId;      // 父模型ID（用于版本追踪）
    private String datasetId;          // 训练数据集ID
    private Integer inputWidth = 640;
    private Integer inputHeight = 640;
}
