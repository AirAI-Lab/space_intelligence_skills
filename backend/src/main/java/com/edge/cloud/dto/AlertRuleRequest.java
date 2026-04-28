package com.edge.cloud.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class AlertRuleRequest {
    private String name;
    @JsonProperty("device_id")
    private String deviceId;
    @JsonProperty("model_name")
    private String modelName;
    private String source;
    @JsonProperty("class_name")
    private String className;
    @JsonProperty("condition_type")
    private String conditionType;
    @JsonProperty("threshold_value")
    private Float thresholdValue;
    @JsonProperty("alert_level")
    private String alertLevel;
    @JsonProperty("alert_message")
    private String alertMessage;
    @JsonProperty("trigger_cloud_infer")
    private Boolean triggerCloudInfer = false;
    @JsonProperty("enabled")
    private Boolean enabled = true;
}
