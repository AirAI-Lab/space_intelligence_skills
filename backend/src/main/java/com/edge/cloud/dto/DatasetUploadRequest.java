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

    // 数据集来源：upload（上传）或 local（本地路径）
    private String datasetSource = "upload";

    // 本地路径（当 datasetSource = "local" 时使用）
    private String localPath;
}
