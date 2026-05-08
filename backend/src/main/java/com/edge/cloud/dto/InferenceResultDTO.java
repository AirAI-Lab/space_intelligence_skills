package com.edge.cloud.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.Map;

@Data
public class InferenceResultDTO {
    private Long id;
    private LocalDateTime time;
    @JsonProperty("device_id")
    private String deviceId;
    @JsonProperty("channel_id")
    private String channelId;
    private String source;
    @JsonProperty("model_name")
    private String modelName;
    @JsonProperty("task_type")
    private String taskType;
    @JsonProperty("frame_id")
    private Long frameId;
    @JsonProperty("image_url")
    private String imageUrl;
    @JsonProperty("result_json")
    private Map<String, Object> resultJson;
    @JsonProperty("alert_level")
    private String alertLevel;
    @JsonProperty("alert_message")
    private String alertMessage;
    @JsonProperty("inference_time_ms")
    private Float inferenceTimeMs;
    @JsonProperty("detection_count")
    private Integer detectionCount;
    @JsonProperty("summary_text")
    private String summaryText;
}
