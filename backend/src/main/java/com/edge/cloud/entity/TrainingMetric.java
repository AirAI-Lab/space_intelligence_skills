package com.edge.cloud.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 训练指标时序实体 (TimescaleDB)
 */
@Data
@Entity
@Table(name = "training_metrics")
public class TrainingMetric {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "time", nullable = false)
    private LocalDateTime time;

    @Column(name = "job_id", length = 50, nullable = false)
    private String jobId;

    @Column(name = "epoch", nullable = false)
    private Integer epoch;

    @Column(name = "train_loss")
    private Float trainLoss;

    @Column(name = "val_loss")
    private Float valLoss;

    @Column(name = "map50")
    private Float map50;

    @Column(name = "map50_95")
    private Float map50_95;

    @Column(name = "precision")
    private Float precision;

    @Column(name = "recall")
    private Float recall;

    @Column(name = "learning_rate")
    private Float learningRate;

    public TrainingMetric() {
    }

    public TrainingMetric(LocalDateTime time, String jobId, Integer epoch) {
        this.time = time;
        this.jobId = jobId;
        this.epoch = epoch;
    }
}
