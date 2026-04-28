package com.edge.cloud.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class CloudInferenceResultRequest {

    @JsonProperty("device_id")
    private String deviceId;

    @JsonProperty("frame_id")
    private Long frameId;

    private String timestamp;

    private Map<String, SegmentInfo> segments;

    private List<AlertInfo> alerts;

    @JsonProperty("inference_time_ms")
    private Float inferenceTimeMs;

    @JsonProperty("image_base64")
    private String imageBase64;

    @Data
    public static class SegmentInfo {
        private Float area;
        private Float score;
        private List<Integer> bbox;
        @JsonProperty("class_name_cn")
        private String classNameCn;
    }

    @Data
    public static class AlertInfo {
        @JsonProperty("class_name")
        private String className;
        @JsonProperty("class_name_cn")
        private String classNameCn;
        private String level;
        private String message;
        private Float area;
    }
}
