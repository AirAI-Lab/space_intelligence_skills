package com.edge.cloud.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.LocalDateTime;
import java.util.Map;

@Data
@Entity
@Table(name = "inference_results")
public class InferenceResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "time", nullable = false)
    private LocalDateTime time;

    @Column(name = "device_id", length = 50, nullable = false)
    private String deviceId;

    @Column(name = "channel_id", length = 50)
    private String channelId;

    @Column(name = "source", length = 20, nullable = false)
    private String source;

    @Column(name = "model_name", length = 200)
    private String modelName;

    @Column(name = "task_type", length = 50)
    private String taskType;

    @Column(name = "frame_id")
    private Long frameId;

    @Column(name = "image_url", length = 500)
    private String imageUrl;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "result_json", columnDefinition = "jsonb")
    private Map<String, Object> resultJson;

    @Column(name = "alert_level", length = 20)
    private String alertLevel;

    @Column(name = "alert_message", columnDefinition = "TEXT")
    private String alertMessage;

    @Column(name = "inference_time_ms")
    private Float inferenceTimeMs;

    @Column(name = "detection_count")
    private Integer detectionCount;

    @Column(name = "summary_text", length = 500)
    private String summaryText;

    public InferenceResult() {
    }
}
