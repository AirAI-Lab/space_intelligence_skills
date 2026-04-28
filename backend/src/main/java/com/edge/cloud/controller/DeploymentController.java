package com.edge.cloud.controller;

import com.edge.cloud.dto.ApiResponse;
import com.edge.cloud.dto.ModelDeploymentDTO;
import com.edge.cloud.service.DeploymentService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 部署记录 API
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/deployments")
@RequiredArgsConstructor
@Tag(name = "部署记录", description = "模型部署记录查询、统计接口")
public class DeploymentController {

    private final DeploymentService deploymentService;

    @GetMapping("/{deployment_id}")
    @Operation(summary = "获取部署记录详情")
    public ResponseEntity<ApiResponse<ModelDeploymentDTO>> getDeployment(
            @Parameter(description = "部署ID") @PathVariable("deployment_id") String deploymentId
    ) {
        try {
            ModelDeploymentDTO result = deploymentService.getDeployment(deploymentId);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取部署记录失败: deploymentId={}", deploymentId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping
    @Operation(summary = "分页查询部署记录")
    public ResponseEntity<ApiResponse<Map<String, Object>>> listDeployments(
            @Parameter(description = "模型ID") @RequestParam(required = false) String modelId,
            @Parameter(description = "设备ID") @RequestParam(required = false) String deviceId,
            @Parameter(description = "状态") @RequestParam(required = false) String status,
            @Parameter(description = "部署类型") @RequestParam(required = false) String deploymentType,
            @Parameter(description = "开始时间") @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime startTime,
            @Parameter(description = "结束时间") @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime endTime,
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") int page,
            @Parameter(description = "每页数量") @RequestParam(defaultValue = "20") int page_size
    ) {
        try {
            Map<String, Object> result = deploymentService.listDeployments(
                    modelId, deviceId, status, deploymentType, startTime, endTime, page, page_size);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("查询部署记录失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("查询失败: " + e.getMessage()));
        }
    }

    @GetMapping("/recent")
    @Operation(summary = "获取最近部署记录")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getRecentDeployments(
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") int page,
            @Parameter(description = "每页数量") @RequestParam(defaultValue = "20") int page_size
    ) {
        try {
            Map<String, Object> result = deploymentService.getRecentDeployments(page, page_size);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取最近部署记录失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping("/model/{model_id}/history")
    @Operation(summary = "获取模型的部署历史")
    public ResponseEntity<ApiResponse<List<ModelDeploymentDTO>>> getModelDeploymentHistory(
            @Parameter(description = "模型ID") @PathVariable("model_id") String modelId
    ) {
        try {
            List<ModelDeploymentDTO> result = deploymentService.getModelDeploymentHistory(modelId);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取模型部署历史失败: modelId={}", modelId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping("/model/{model_id}/stats")
    @Operation(summary = "获取模型部署统计")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getModelDeploymentStats(
            @Parameter(description = "模型ID") @PathVariable("model_id") String modelId
    ) {
        try {
            Map<String, Object> result = deploymentService.getDeploymentStats(modelId);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取模型部署统计失败: modelId={}", modelId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping("/model/{model_id}/active-devices")
    @Operation(summary = "获取模型当前运行的设备列表")
    public ResponseEntity<ApiResponse<List<Map<String, Object>>>> getModelActiveDevices(
            @Parameter(description = "模型ID") @PathVariable("model_id") String modelId
    ) {
        try {
            List<Map<String, Object>> result = deploymentService.getModelActiveDevices(modelId);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取模型运行设备失败: modelId={}", modelId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping("/device/{device_id}/history")
    @Operation(summary = "获取设备的部署历史")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getDeviceDeploymentHistory(
            @Parameter(description = "设备ID") @PathVariable("device_id") String deviceId,
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") int page,
            @Parameter(description = "每页数量") @RequestParam(defaultValue = "20") int page_size
    ) {
        try {
            Map<String, Object> result = deploymentService.getDeviceDeploymentHistory(deviceId, page, page_size);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取设备部署历史失败: deviceId={}", deviceId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping("/device/{device_id}/current")
    @Operation(summary = "获取设备的当前部署信息")
    public ResponseEntity<ApiResponse<ModelDeploymentDTO>> getDeviceCurrentDeployment(
            @Parameter(description = "设备ID") @PathVariable("device_id") String deviceId
    ) {
        try {
            ModelDeploymentDTO result = deploymentService.getDeviceCurrentDeployment(deviceId);
            if (result == null) {
                return ResponseEntity.ok(ApiResponse.success("设备暂无部署记录", null));
            }
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取设备当前部署失败: deviceId={}", deviceId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @DeleteMapping("/{deployment_id}")
    @Operation(summary = "删除部署记录")
    public ResponseEntity<ApiResponse<Void>> deleteDeployment(
            @Parameter(description = "部署ID") @PathVariable("deployment_id") String deploymentId
    ) {
        try {
            deploymentService.deleteDeployment(deploymentId);
            return ResponseEntity.ok(ApiResponse.success("部署记录已删除", null));
        } catch (Exception e) {
            log.error("删除部署记录失败: deploymentId={}", deploymentId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("删除失败: " + e.getMessage()));
        }
    }

    @DeleteMapping("/batch")
    @Operation(summary = "批量删除部署记录")
    public ResponseEntity<ApiResponse<Map<String, Object>>> deleteDeployments(
            @Parameter(description = "部署ID列表") @RequestBody List<String> deploymentIds
    ) {
        try {
            int successCount = 0;
            int failCount = 0;
            for (String deploymentId : deploymentIds) {
                try {
                    deploymentService.deleteDeployment(deploymentId);
                    successCount++;
                } catch (Exception e) {
                    failCount++;
                    log.warn("删除部署记录失败: deploymentId={}", deploymentId, e);
                }
            }
            Map<String, Object> result = new HashMap<>();
            result.put("total", deploymentIds.size());
            result.put("success", successCount);
            result.put("failed", failCount);
            return ResponseEntity.ok(ApiResponse.success("批量删除完成", result));
        } catch (Exception e) {
            log.error("批量删除部署记录失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("删除失败: " + e.getMessage()));
        }
    }

    @DeleteMapping("/clear")
    @Operation(summary = "清空所有已完成/失败/已回滚的部署记录")
    public ResponseEntity<ApiResponse<Map<String, Object>>> clearCompletedDeployments() {
        try {
            Map<String, Object> result = deploymentService.clearCompletedDeployments();
            return ResponseEntity.ok(ApiResponse.success("清空完成", result));
        } catch (Exception e) {
            log.error("清空部署记录失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("清空失败: " + e.getMessage()));
        }
    }
}
