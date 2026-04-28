package com.edge.cloud.controller;

import com.edge.cloud.dto.ApiResponse;
import com.edge.cloud.dto.CloudInferenceResultRequest;
import com.edge.cloud.dto.InferenceResultDTO;
import com.edge.cloud.dto.InferenceStatsDTO;
import com.edge.cloud.dto.InferenceTrendDTO;
import com.edge.cloud.entity.InferenceResult;
import com.edge.cloud.service.InferenceResultService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequestMapping("/api/v1")
@RequiredArgsConstructor
@Tag(name = "推理结果查询", description = "推理结果查询、告警、统计接口")
public class InferenceResultController {

    private final InferenceResultService inferenceResultService;

    @PostMapping("/cloud/inference/result")
    @Operation(summary = "云端推理结果上报")
    public ResponseEntity<ApiResponse<Map<String, Object>>> reportCloudResult(
            @RequestBody CloudInferenceResultRequest request) {
        try {
            InferenceResult saved = inferenceResultService.saveCloudResult(request);
            return ResponseEntity.ok(ApiResponse.success("云端推理结果已保存",
                    Map.of("id", saved.getId(), "status", "SUCCESS")));
        } catch (Exception e) {
            log.error("保存云端推理结果失败: device={}", request.getDeviceId(), e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("保存失败: " + e.getMessage()));
        }
    }

    @GetMapping("/inference/results")
    @Operation(summary = "分页查询推理结果")
    public ResponseEntity<ApiResponse<Map<String, Object>>> queryResults(
            @Parameter(description = "设备ID") @RequestParam(required = false) String device_id,
            @Parameter(description = "来源: edge/cloud") @RequestParam(required = false) String source,
            @Parameter(description = "告警级别") @RequestParam(required = false) String alert_level,
            @Parameter(description = "仅显示有告警的记录") @RequestParam(required = false, defaultValue = "false") boolean has_alert,
            @Parameter(description = "开始时间") @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime start_time,
            @Parameter(description = "结束时间") @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime end_time,
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") int page,
            @Parameter(description = "每页数量") @RequestParam(defaultValue = "20") int page_size) {
        try {
            Page<InferenceResult> results = inferenceResultService.queryResults(
                    device_id, source, alert_level, has_alert, start_time, end_time, page, page_size);

            Map<String, Object> data = new HashMap<>();
            data.put("items", results.getContent().stream()
                    .map(inferenceResultService::toDTO)
                    .collect(Collectors.toList()));
            data.put("total", results.getTotalElements());
            data.put("page", page);
            data.put("page_size", page_size);

            return ResponseEntity.ok(ApiResponse.success(data));
        } catch (Exception e) {
            log.error("查询推理结果失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("查询失败: " + e.getMessage()));
        }
    }

    @GetMapping("/inference/results/{id}")
    @Operation(summary = "获取推理结果详情")
    public ResponseEntity<ApiResponse<InferenceResultDTO>> getResult(
            @Parameter(description = "结果ID") @PathVariable Long id) {
        return inferenceResultService.getResult(id)
                .map(result -> ResponseEntity.ok(
                        ApiResponse.success(inferenceResultService.toDTO(result))))
                .orElse(ResponseEntity.status(404)
                        .body(ApiResponse.error(404, "结果不存在")));
    }

    @GetMapping("/inference/alerts")
    @Operation(summary = "查询告警列表")
    public ResponseEntity<ApiResponse<Map<String, Object>>> queryAlerts(
            @Parameter(description = "告警级别列表") @RequestParam(required = false) List<String> levels,
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") int page,
            @Parameter(description = "每页数量") @RequestParam(defaultValue = "20") int page_size) {
        try {
            Page<InferenceResult> results = inferenceResultService.queryAlerts(levels, page, page_size);

            Map<String, Object> data = new HashMap<>();
            data.put("items", results.getContent().stream()
                    .map(inferenceResultService::toDTO)
                    .collect(Collectors.toList()));
            data.put("total", results.getTotalElements());
            data.put("page", page);
            data.put("page_size", page_size);

            return ResponseEntity.ok(ApiResponse.success(data));
        } catch (Exception e) {
            log.error("查询告警失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("查询失败: " + e.getMessage()));
        }
    }

    @GetMapping("/inference/stats")
    @Operation(summary = "推理统计（最近24小时）")
    public ResponseEntity<ApiResponse<InferenceStatsDTO>> getStats() {
        try {
            InferenceStatsDTO stats = inferenceResultService.getStats();
            return ResponseEntity.ok(ApiResponse.success(stats));
        } catch (Exception e) {
            log.error("获取推理统计失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取统计失败: " + e.getMessage()));
        }
    }

    @GetMapping("/inference/trend")
    @Operation(summary = "推理趋势（最近24小时，按小时聚合）")
    public ResponseEntity<ApiResponse<InferenceTrendDTO>> getTrend() {
        try {
            return ResponseEntity.ok(ApiResponse.success(inferenceResultService.getTrend()));
        } catch (Exception e) {
            log.error("获取推理趋势失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取趋势失败: " + e.getMessage()));
        }
    }

    @GetMapping("/inference/export")
    @Operation(summary = "导出推理结果（CSV或JSON）")
    public ResponseEntity<byte[]> exportResults(
            @Parameter(description = "设备ID") @RequestParam(required = false) String device_id,
            @Parameter(description = "来源: edge/cloud") @RequestParam(required = false) String source,
            @Parameter(description = "告警级别") @RequestParam(required = false) String alert_level,
            @Parameter(description = "开始时间") @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime start_time,
            @Parameter(description = "结束时间") @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime end_time,
            @Parameter(description = "导出格式: csv/json") @RequestParam(defaultValue = "csv") String format) {
        try {
            byte[] data = inferenceResultService.exportResults(
                    device_id, source, alert_level, start_time, end_time, format);

            String filename = "inference_results." + format.toLowerCase();
            String contentType = "csv".equalsIgnoreCase(format)
                    ? "text/csv"
                    : MediaType.APPLICATION_JSON_VALUE;

            return ResponseEntity.ok()
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=" + filename)
                    .contentType(MediaType.parseMediaType(contentType))
                    .body(data);
        } catch (Exception e) {
            log.error("导出推理结果失败", e);
            return ResponseEntity.status(500).body(null);
        }
    }

    @DeleteMapping("/inference/results")
    @Operation(summary = "清空所有推理结果")
    public ResponseEntity<ApiResponse<Map<String, Object>>> clearAllResults() {
        try {
            long count = inferenceResultService.clearAll();
            log.info("已清空推理结果: {} 条", count);
            return ResponseEntity.ok(ApiResponse.success("已清空",
                    Map.of("deleted", count)));
        } catch (Exception e) {
            log.error("清空推理结果失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("清空失败: " + e.getMessage()));
        }
    }
}
