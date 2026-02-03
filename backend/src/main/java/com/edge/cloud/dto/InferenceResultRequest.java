package com.edge.cloud.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 推理结果上报请求 (边缘端 -> 云端)
 */
@Data
public class InferenceResultRequest {

    /**
     * 设备ID
     */
    @JsonProperty("device_id")
    private String deviceId;

    /**
     * 模型ID
     */
    @JsonProperty("model_id")
    private String modelId;

    /**
     * 模型版本
     */
    @JsonProperty("model_version")
    private String modelVersion;

    /**
     * 推理耗时(毫秒)
     */
    @JsonProperty("inference_time_ms")
    private Integer inferenceTimeMs;

    /**
     * 帧数
     */
    @JsonProperty("frame_count")
    private Integer frameCount;

    /**
     * 帧宽度
     */
    @JsonProperty("frame_width")
    private Integer frameWidth;

    /**
     * 帧高度
     */
    @JsonProperty("frame_height")
    private Integer frameHeight;

    /**
     * 检测结果列表
     */
    private List<Detection> detections;

    /**
     * 时间戳
     */
    private LocalDateTime timestamp;

    /**
     * 检测结果
     */
    @Data
    public static class Detection {
        /**
         * 类别ID
         */
        @JsonProperty("class_id")
        private Integer classId;

        /**
         * 类别名称
         */
        @JsonProperty("class_name")
        private String className;

        /**
         * 置信度
         */
        private Float confidence;

        /**
         * 边界框 [x, y, width, height]
         */
        private List<Integer> bbox;
    }
}
