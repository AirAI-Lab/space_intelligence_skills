package com.edge.cloud.dto;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 训练指标 DTO
 */
@Data
public class TrainingMetricDTO {

    private LocalDateTime time;
    private String jobId;
    private Integer epoch;
    private Float trainLoss;
    private Float valLoss;
    private Float map50;
    private Float map50_95;
    private Float precision;
    private Float recall;
    private Float learningRate;
}
