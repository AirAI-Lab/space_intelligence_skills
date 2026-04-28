package com.edge.cloud.service;

import com.edge.cloud.dto.*;
import com.edge.cloud.entity.InferenceResult;
import com.edge.cloud.repository.InferenceResultRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.ByteArrayOutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.Base64;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class InferenceResultService {

    private final InferenceResultRepository inferenceResultRepository;
    private final WebSocketMessageService webSocketMessageService;
    private final WebhookService webhookService;
    private final StorageService storageService;

    @Transactional
    public InferenceResult saveEdgeResult(InferenceResultRequest request) {
        InferenceResult result = new InferenceResult();
        result.setTime(request.getTimestamp() != null ? request.getTimestamp() : LocalDateTime.now());
        result.setDeviceId(request.getDeviceId());
        result.setSource("edge");
        result.setModelName(request.getModelId());
        result.setTaskType("detect");
        result.setFrameId(request.getFrameCount() != null ? request.getFrameCount().longValue() : null);
        result.setInferenceTimeMs(request.getInferenceTimeMs() != null ? request.getInferenceTimeMs().floatValue() : null);

        int detectionCount = request.getDetections() != null ? request.getDetections().size() : 0;
        result.setDetectionCount(detectionCount);

        // Build result_json from detections
        Map<String, Object> resultJson = new HashMap<>();
        resultJson.put("model_id", request.getModelId());
        resultJson.put("model_version", request.getModelVersion());
        resultJson.put("frame_width", request.getFrameWidth());
        resultJson.put("frame_height", request.getFrameHeight());
        resultJson.put("detections", request.getDetections());
        result.setResultJson(resultJson);

        // Extract alert info — use edge-side is_alert flag from plugin chain
        String alertLevel = null;
        String alertMessage = null;
        if (request.getDetections() != null) {
            for (InferenceResultRequest.Detection det : request.getDetections()) {
                if (Boolean.TRUE.equals(det.getIsAlert())) {
                    alertLevel = "warning";
                    alertMessage = det.getClassName() + " 检出 (置信度: " + String.format("%.2f", det.getConfidence()) + ")";
                }
            }
        }
        result.setAlertLevel(alertLevel);
        result.setAlertMessage(alertMessage);

        // Summary
        if (detectionCount > 0) {
            result.setSummaryText(String.format("边缘检测: %d个目标", detectionCount));
        }

        // Upload image if provided
        if (request.getImageBase64() != null && !request.getImageBase64().isEmpty()) {
            try {
                byte[] imageBytes = Base64.getDecoder().decode(request.getImageBase64());
                String key = storageService.uploadBytes(imageBytes, "inference", "image/jpeg");
                String imageUrl = storageService.getFileUrl(key);
                result.setImageUrl(imageUrl);
                log.debug("Edge inference image uploaded: key={}", key);
            } catch (Exception e) {
                log.warn("Failed to upload edge inference image: {}", e.getMessage());
            }
        }

        InferenceResult saved = inferenceResultRepository.save(result);
        broadcastResult(saved);
        log.debug("Edge inference result saved: id={}, device={}, detections={}",
                saved.getId(), saved.getDeviceId(), detectionCount);
        return saved;
    }

    @Transactional
    public InferenceResult saveCloudResult(CloudInferenceResultRequest request) {
        InferenceResult result = new InferenceResult();
        result.setTime(LocalDateTime.now());
        result.setDeviceId(request.getDeviceId());
        result.setSource("cloud");
        result.setModelName("C-RADIOv4");
        result.setTaskType("segment");
        result.setFrameId(request.getFrameId());
        result.setInferenceTimeMs(request.getInferenceTimeMs());

        // Build result_json
        Map<String, Object> resultJson = new HashMap<>();
        resultJson.put("segments", request.getSegments());
        resultJson.put("alerts", request.getAlerts());
        result.setResultJson(resultJson);

        // Count segments
        int segmentCount = request.getSegments() != null ? request.getSegments().size() : 0;
        result.setDetectionCount(segmentCount);

        // Extract highest alert level
        String alertLevel = null;
        String alertMessage = null;
        if (request.getAlerts() != null && !request.getAlerts().isEmpty()) {
            for (CloudInferenceResultRequest.AlertInfo alert : request.getAlerts()) {
                String level = alert.getLevel();
                if (level != null) {
                    if (alertLevel == null || compareAlertLevels(level, alertLevel) > 0) {
                        alertLevel = level;
                    }
                    alertMessage = alert.getMessage();
                }
            }
        }
        result.setAlertLevel(alertLevel);
        result.setAlertMessage(alertMessage);

        // Summary
        if (segmentCount > 0 && request.getSegments() != null) {
            result.setSummaryText(String.format("云端分割: %d个区域", segmentCount));
        }

        // Upload image if provided
        if (request.getImageBase64() != null && !request.getImageBase64().isEmpty()) {
            try {
                byte[] imageBytes = Base64.getDecoder().decode(request.getImageBase64());
                String key = storageService.uploadBytes(imageBytes, "inference", "image/jpeg");
                String imageUrl = storageService.getFileUrl(key);
                result.setImageUrl(imageUrl);
                log.debug("Inference image uploaded: key={}, url={}", key, imageUrl);
            } catch (Exception e) {
                log.warn("Failed to upload inference image: {}", e.getMessage());
            }
        }

        InferenceResult saved = inferenceResultRepository.save(result);
        broadcastResult(saved);
        log.debug("Cloud inference result saved: id={}, device={}, segments={}, alerts={}",
                saved.getId(), saved.getDeviceId(), segmentCount,
                request.getAlerts() != null ? request.getAlerts().size() : 0);
        return saved;
    }

    public Page<InferenceResult> queryResults(String deviceId, String source,
            String alertLevel, boolean hasAlert, LocalDateTime startTime, LocalDateTime endTime,
            int page, int pageSize) {
        Pageable pageable = PageRequest.of(Math.max(0, page - 1), pageSize, Sort.by(Sort.Direction.DESC, "time"));
        // hasAlert 模式：只返回有告警的结果
        if (hasAlert && alertLevel == null) {
            if (startTime != null && endTime != null) {
                return inferenceResultRepository.findWithFiltersAndTime(deviceId, source, "any", startTime, endTime, pageable);
            }
            return inferenceResultRepository.findWithFilters(deviceId, source, "any", pageable);
        }
        if (startTime != null && endTime != null) {
            return inferenceResultRepository.findWithFiltersAndTime(deviceId, source, alertLevel, startTime, endTime, pageable);
        }
        return inferenceResultRepository.findWithFilters(deviceId, source, alertLevel, pageable);
    }

    public Optional<InferenceResult> getResult(Long id) {
        return inferenceResultRepository.findById(id);
    }

    public Page<InferenceResult> queryAlerts(List<String> levels, int page, int pageSize) {
        Pageable pageable = PageRequest.of(Math.max(0, page - 1), pageSize, Sort.by(Sort.Direction.DESC, "time"));
        if (levels != null && !levels.isEmpty()) {
            return inferenceResultRepository.findByAlertLevelIn(levels, pageable);
        }
        return inferenceResultRepository.findByAlertLevelIsNotNull(pageable);
    }

    public InferenceStatsDTO getStats() {
        LocalDateTime since = LocalDateTime.now().minusDays(1);
        InferenceStatsDTO stats = new InferenceStatsDTO();
        stats.setTotalResults(inferenceResultRepository.countSince(since));
        stats.setTotalAlerts(inferenceResultRepository.countAlertsSince(since));

        // Alert level breakdown
        Map<String, Long> alertsByLevel = new LinkedHashMap<>();
        List<Object[]> levelCounts = inferenceResultRepository.countByAlertLevelSince(since);
        for (Object[] row : levelCounts) {
            alertsByLevel.put((String) row[0], (Long) row[1]);
        }
        stats.setAlertsByLevel(alertsByLevel);

        // Device stats
        List<InferenceStatsDTO.DeviceStats> deviceStats = new ArrayList<>();
        List<Object[]> deviceRows = inferenceResultRepository.statsByDeviceSince(since);
        for (Object[] row : deviceRows) {
            InferenceStatsDTO.DeviceStats ds = new InferenceStatsDTO.DeviceStats();
            ds.setDeviceId((String) row[0]);
            ds.setCount(((Number) row[1]).longValue());
            ds.setAvgInferenceMs(row[2] != null ? ((Number) row[2]).doubleValue() : 0);
            deviceStats.add(ds);
        }
        stats.setDeviceStats(deviceStats);

        // Source counts
        stats.setEdgeResults(inferenceResultRepository.countBySourceSince("edge", since));
        stats.setCloudResults(inferenceResultRepository.countBySourceSince("cloud", since));

        return stats;
    }

    public InferenceResultDTO toDTO(InferenceResult entity) {
        InferenceResultDTO dto = new InferenceResultDTO();
        dto.setId(entity.getId());
        dto.setTime(entity.getTime());
        dto.setDeviceId(entity.getDeviceId());
        dto.setSource(entity.getSource());
        dto.setModelName(entity.getModelName());
        dto.setTaskType(entity.getTaskType());
        dto.setFrameId(entity.getFrameId());
        dto.setImageUrl(entity.getImageUrl());
        dto.setResultJson(entity.getResultJson());
        dto.setAlertLevel(entity.getAlertLevel());
        dto.setAlertMessage(entity.getAlertMessage());
        dto.setInferenceTimeMs(entity.getInferenceTimeMs());
        dto.setDetectionCount(entity.getDetectionCount());
        dto.setSummaryText(entity.getSummaryText());
        return dto;
    }

    private void broadcastResult(InferenceResult result) {
        InferenceResultDTO dto = toDTO(result);
        webSocketMessageService.broadcast("/topic/inference/" + result.getDeviceId() + "/results", dto);
        if (result.getAlertLevel() != null) {
            webSocketMessageService.broadcast("/topic/inference/alerts", dto);
            webhookService.fireAlertEvent(dto);
        }
        webhookService.fireResultEvent(dto);
    }

    public InferenceTrendDTO getTrend() {
        LocalDateTime since = LocalDateTime.now().minusDays(1);
        InferenceTrendDTO trend = new InferenceTrendDTO();

        // Hourly data
        List<InferenceTrendDTO.DataPoint> hourly = new ArrayList<>();
        List<Object[]> rows = inferenceResultRepository.hourlyTrendSince(since);
        for (Object[] row : rows) {
            InferenceTrendDTO.DataPoint dp = new InferenceTrendDTO.DataPoint();
            dp.setHour((String) row[0]);
            dp.setCount(((Number) row[1]).longValue());
            dp.setAlertCount(((Number) row[2]).longValue());
            hourly.add(dp);
        }
        trend.setHourly(hourly);

        // Class distribution from result_json (extract detection class_name)
        Map<String, Long> classDist = new LinkedHashMap<>();
        List<InferenceResult> recentResults = inferenceResultRepository
                .findAll(PageRequest.of(0, 1000, Sort.by(Sort.Direction.DESC, "time")))
                .getContent();
        for (InferenceResult r : recentResults) {
            if (r.getResultJson() == null) continue;
            Object detections = r.getResultJson().get("detections");
            if (detections instanceof List<?> detList) {
                for (Object d : detList) {
                    if (d instanceof Map<?, ?> m && m.get("class_name") instanceof String cn) {
                        classDist.merge(cn, 1L, Long::sum);
                    }
                }
            }
            Object segments = r.getResultJson().get("segments");
            if (segments instanceof Map<?, ?> segMap) {
                for (Object key : segMap.keySet()) {
                    if (key instanceof String cn) {
                        classDist.merge(cn, 1L, Long::sum);
                    }
                }
            }
        }
        trend.setClassDistribution(classDist);

        // Avg inference time by source
        Map<String, Double> avgBySource = new LinkedHashMap<>();
        List<Object[]> sourceRows = inferenceResultRepository.avgInferenceMsBySourceSince(since);
        for (Object[] row : sourceRows) {
            avgBySource.put((String) row[0], row[1] != null ? ((Number) row[1]).doubleValue() : 0);
        }
        trend.setAvgInferenceMsBySource(avgBySource);

        return trend;
    }

    public byte[] exportResults(String deviceId, String source, String alertLevel,
            LocalDateTime startTime, LocalDateTime endTime, String format) throws Exception {
        Page<InferenceResult> results = queryResults(deviceId, source, alertLevel,
                startTime, endTime, 1, 10000);
        List<InferenceResultDTO> dtos = results.getContent().stream()
                .map(this::toDTO).toList();

        if ("csv".equalsIgnoreCase(format)) {
            return exportCsv(dtos);
        }
        // Default JSON
        com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
        mapper.registerModule(new com.fasterxml.jackson.datatype.jsr310.JavaTimeModule());
        return mapper.writerWithDefaultPrettyPrinter().writeValueAsBytes(dtos);
    }

    private byte[] exportCsv(List<InferenceResultDTO> dtos) throws Exception {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        OutputStreamWriter writer = new OutputStreamWriter(baos, StandardCharsets.UTF_8);
        writer.write('﻿'); // BOM for Excel
        writer.write("时间,设备ID,来源,模型,任务类型,告警级别,告警消息,检出数,推理耗时(ms)\n");
        DateTimeFormatter fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
        for (InferenceResultDTO d : dtos) {
            writer.write(String.format("%s,%s,%s,%s,%s,%s,%s,%d,%s\n",
                    d.getTime() != null ? d.getTime().format(fmt) : "",
                    d.getDeviceId(),
                    d.getSource(),
                    d.getModelName() != null ? d.getModelName() : "",
                    d.getTaskType() != null ? d.getTaskType() : "",
                    d.getAlertLevel() != null ? d.getAlertLevel() : "",
                    d.getAlertMessage() != null ? d.getAlertMessage().replace(",", "，") : "",
                    d.getDetectionCount() != null ? d.getDetectionCount() : 0,
                    d.getInferenceTimeMs() != null ? String.format("%.1f", d.getInferenceTimeMs()) : ""
            ));
        }
        writer.flush();
        return baos.toByteArray();
    }

    private int compareAlertLevels(String a, String b) {
        Map<String, Integer> order = Map.of("critical", 3, "warning", 2, "info", 1);
        return order.getOrDefault(a, 0) - order.getOrDefault(b, 0);
    }

    @Transactional
    public long clearAll() {
        long count = inferenceResultRepository.count();
        if (count > 0) {
            inferenceResultRepository.deleteAllInBatch();
        }
        return count;
    }
}
