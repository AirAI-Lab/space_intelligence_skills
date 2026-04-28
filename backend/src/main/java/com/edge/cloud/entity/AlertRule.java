package com.edge.cloud.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "alert_rules")
public class AlertRule {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "name", length = 200, nullable = false)
    private String name;

    @Column(name = "device_id", length = 50)
    private String deviceId;  // null = all devices

    @Column(name = "model_name", length = 200)
    private String modelName; // null = all models

    @Column(name = "source", length = 20)
    private String source;    // null = all sources, or "edge"/"cloud"

    @Column(name = "class_name", length = 100)
    private String className; // e.g. "black_water", "swimming"

    @Column(name = "condition_type", length = 50, nullable = false)
    private String conditionType; // "area_threshold", "count_threshold", "confidence_threshold"

    @Column(name = "threshold_value")
    private Float thresholdValue;

    @Column(name = "alert_level", length = 20, nullable = false)
    private String alertLevel; // "info", "warning", "critical"

    @Column(name = "alert_message", length = 500)
    private String alertMessage;

    @Column(name = "trigger_cloud_infer")
    private Boolean triggerCloudInfer = false; // whether to trigger cloud inference on alert

    @Column(name = "enabled")
    private Boolean enabled = true;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
