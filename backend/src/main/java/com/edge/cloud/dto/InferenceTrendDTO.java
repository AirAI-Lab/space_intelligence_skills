package com.edge.cloud.dto;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class InferenceTrendDTO {
    private List<DataPoint> hourly;
    private Map<String, Long> classDistribution;
    private Map<String, Double> avgInferenceMsBySource;

    @Data
    public static class DataPoint {
        private String hour;  // "2026-04-24T10"
        private long count;
        private long alertCount;
    }
}
