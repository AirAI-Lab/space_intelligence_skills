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

    // 数据集来源：backend（管理后台上传）, url（URL下载）, local（本地路径）
    private String datasetSource = "backend";

    // 后端数据集ID（datasetSource=backend 时使用）
    private String datasetId;

    // URL 数据集（datasetSource=url 时使用）
    private String datasetUrl;
    private String datasetName;           // 自定义数据集名称（url/local 时使用）

    // 本地路径（datasetSource=local 时使用）
    private String datasetPath;

    private String baseModelId;           // 基础模型ID（用于微调已有模型）
    private String baseModel;             // 预训练模型名称（yolov8n.pt 等）
    private TrainingJob.TrainingType trainingType;
    private Integer epochs = 100;
    private Integer batchSize = 16;
    private Integer imgSize = 640;
    private Boolean useGpu = true;

    // 超参数（YOLOv8 - 针对溺水检测优化的默认值）
    private String optimizer = "AdamW";    // 优化器: SGD, Adam, AdamW（默认AdamW更快收敛）
    private Double lr0 = 0.01;             // 初始学习率
    private Double lrf = 0.001;            // 最终学习率（实现学习率衰减）
    private Double weightDecay = 0.0005;   // 权重衰减
    private Integer workers = 8;           // 工作线程数
    private Integer warmupEpochs = 3;      // 预热轮次
    private Integer savePeriod = 10;       // 保存频率
    private Double mosaic = 1.0;           // Mosaic增强概率
    private Double mixup = 0.15;           // Mixup增强概率（默认开启轻量Mixup）
    private Integer patience = 30;         // 早停耐心值（30轮无改善则停止）

    // 断点续训参数
    private Boolean resume = false;        // 是否继续之前的训练
    private String resumeJobId;            // 要继续的任务ID
    private Boolean enableSmartOptimization = true;  // 是否启用智能参数优化（续训时）

    // 超参数（兼容旧版）
    private Map<String, Object> hyperparameters;
}
