package com.edge.cloud.dto;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class InferenceStatsDTO {
    private long totalResults;
    private long totalAlerts;
    private long edgeResults;
    private long cloudResults;
    private Map<String, Long> alertsByLevel;
    private List<DeviceStats> deviceStats;

    @Data
    public static class DeviceStats {
        private String deviceId;
        private long count;
        private double avgInferenceMs;
    }
}
