package com.edge.cloud.dto;

import com.edge.cloud.entity.Dataset;
import lombok.Data;

/**
 * 数据集上传请求
 */
@Data
public class DatasetUploadRequest {

    private String datasetName;
    private Dataset.DatasetType datasetType;
    private String format;  // yolov5, yolov8, coco, voc
    private String description;
}
