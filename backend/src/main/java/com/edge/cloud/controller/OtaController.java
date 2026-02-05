package com.edge.cloud.controller;

import com.edge.cloud.dto.ApiResponse;
import com.edge.cloud.dto.DeviceUpgradeStatusDTO;
import com.edge.cloud.dto.OtaTaskCreateRequest;
import com.edge.cloud.dto.OtaTaskDTO;
import com.edge.cloud.entity.OtaTask;
import com.edge.cloud.service.OtaService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * OTA 升级管理 API
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/ota")
@RequiredArgsConstructor
@Tag(name = "OTA 升级管理", description = "OTA 升级任务创建、启动、监控等接口")
public class OtaController {

    private final OtaService otaService;

    @PostMapping("/tasks")
    @Operation(summary = "创建 OTA 升级任务")
    public ResponseEntity<ApiResponse<OtaTaskDTO>> createOtaTask(
            @RequestBody OtaTaskCreateRequest request
    ) {
        try {
            log.info("创建 OTA 升级任务请求: {}", request.getTaskName());
            OtaTaskDTO result = otaService.createOtaTask(request);
            return ResponseEntity.ok(ApiResponse.success("OTA 升级任务创建成功", result));
        } catch (Exception e) {
            log.error("创建 OTA 升级任务失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("创建失败: " + e.getMessage()));
        }
    }

    @PostMapping("/tasks/{task_id}/start")
    @Operation(summary = "启动 OTA 升级任务")
    public ResponseEntity<ApiResponse<OtaTaskDTO>> startOtaTask(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId
    ) {
        try {
            log.info("启动 OTA 升级任务: {}", taskId);
            OtaTaskDTO result = otaService.startOtaTask(taskId);
            return ResponseEntity.ok(ApiResponse.success("OTA 升级任务已启动", result));
        } catch (Exception e) {
            log.error("启动 OTA 升级任务失败: {}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("启动失败: " + e.getMessage()));
        }
    }

    @GetMapping("/tasks/{task_id}")
    @Operation(summary = "获取 OTA 升级任务详情")
    public ResponseEntity<ApiResponse<OtaTaskDTO>> getOtaTask(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId
    ) {
        try {
            OtaTaskDTO result = otaService.getOtaTask(taskId);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取 OTA 升级任务失败: {}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping("/tasks")
    @Operation(summary = "分页查询 OTA 升级任务列表")
    public ResponseEntity<ApiResponse<Map<String, Object>>> listOtaTasks(
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") int page,
            @Parameter(description = "每页数量") @RequestParam(defaultValue = "20") int page_size,
            @Parameter(description = "状态过滤") @RequestParam(required = false) OtaTask.OtaStatus status
    ) {
        try {
            Map<String, Object> result = otaService.listOtaTasks(page, page_size, status);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("查询 OTA 升级任务列表失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("查询失败: " + e.getMessage()));
        }
    }

    @GetMapping("/tasks/{task_id}/devices")
    @Operation(summary = "获取任务的所有设备状态")
    public ResponseEntity<ApiResponse<List<DeviceUpgradeStatusDTO>>> getTaskDeviceStatuses(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId
    ) {
        try {
            List<DeviceUpgradeStatusDTO> result = otaService.getTaskDeviceStatuses(taskId);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取设备升级状态失败: taskId={}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping("/tasks/{task_id}/devices/{device_id}")
    @Operation(summary = "获取指定设备的升级状态")
    public ResponseEntity<ApiResponse<DeviceUpgradeStatusDTO>> getDeviceUpgradeStatus(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId,
            @Parameter(description = "设备ID") @PathVariable("device_id") String deviceId
    ) {
        try {
            DeviceUpgradeStatusDTO result = otaService.getDeviceUpgradeStatus(taskId, deviceId);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取设备升级状态失败: taskId={}, deviceId={}", taskId, deviceId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping("/pending/{device_id}")
    @Operation(summary = "查询设备的待处理 OTA 任务")
    public ResponseEntity<ApiResponse<OtaTaskDTO>> getPendingOtaTask(
            @Parameter(description = "设备ID") @PathVariable("device_id") String deviceId
    ) {
        try {
            OtaTaskDTO result = otaService.getPendingOtaTask(deviceId);
            if (result == null) {
                return ResponseEntity.ok(ApiResponse.success("无待处理任务", null));
            }
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("查询待处理任务失败: deviceId={}", deviceId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("查询失败: " + e.getMessage()));
        }
    }

    @DeleteMapping("/tasks/{task_id}")
    @Operation(summary = "删除 OTA 升级任务")
    public ResponseEntity<ApiResponse<Void>> deleteOtaTask(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId
    ) {
        try {
            otaService.deleteOtaTask(taskId);
            return ResponseEntity.ok(ApiResponse.success("OTA 升级任务已删除", null));
        } catch (Exception e) {
            log.error("删除 OTA 升级任务失败: {}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("删除失败: " + e.getMessage()));
        }
    }

    /**
     * 内部回调接口：设备升级进度更新（MQTT 回调）
     */
    @PostMapping("/internal/tasks/{task_id}/devices/{device_id}/progress")
    @Operation(summary = "设备升级进度更新（MQTT 回调）")
    public ResponseEntity<ApiResponse<Void>> updateDeviceUpgradeProgress(
            @PathVariable("task_id") String taskId,
            @PathVariable("device_id") String deviceId,
            @RequestParam int progress
    ) {
        try {
            otaService.handleDeviceUpgradeProgress(taskId, deviceId, progress);
            return ResponseEntity.ok(ApiResponse.success(null));
        } catch (Exception e) {
            log.error("更新设备升级进度失败: taskId={}, deviceId={}", taskId, deviceId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("更新失败: " + e.getMessage()));
        }
    }

    /**
     * 内部回调接口：设备升级完成（MQTT 回调）
     */
    @PostMapping("/internal/tasks/{task_id}/devices/{device_id}/complete")
    @Operation(summary = "设备升级完成（MQTT 回调）")
    public ResponseEntity<ApiResponse<Void>> completeDeviceUpgrade(
            @PathVariable("task_id") String taskId,
            @PathVariable("device_id") String deviceId
    ) {
        try {
            otaService.handleDeviceUpgradeComplete(taskId, deviceId);
            return ResponseEntity.ok(ApiResponse.success(null));
        } catch (Exception e) {
            log.error("处理设备升级完成失败: taskId={}, deviceId={}", taskId, deviceId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("处理失败: " + e.getMessage()));
        }
    }

    /**
     * 内部回调接口：设备升级失败（MQTT 回调）
     */
    @PostMapping("/internal/tasks/{task_id}/devices/{device_id}/fail")
    @Operation(summary = "设备升级失败（MQTT 回调）")
    public ResponseEntity<ApiResponse<Void>> failDeviceUpgrade(
            @PathVariable("task_id") String taskId,
            @PathVariable("device_id") String deviceId,
            @RequestParam String error_message
    ) {
        try {
            otaService.handleDeviceUpgradeFailed(taskId, deviceId, error_message);
            return ResponseEntity.ok(ApiResponse.success(null));
        } catch (Exception e) {
            log.error("处理设备升级失败失败: taskId={}, deviceId={}", taskId, deviceId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("处理失败: " + e.getMessage()));
        }
    }

    // ==================== P2阶段接口（重试、回滚、暂停、恢复） ====================

    @PostMapping("/tasks/{task_id}/retry")
    @Operation(summary = "重试失败设备")
    public ResponseEntity<ApiResponse<OtaTaskDTO>> retryFailedDevices(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId
    ) {
        try {
            log.info("重试失败设备: taskId={}", taskId);
            OtaTaskDTO result = otaService.retryFailedDevices(taskId);
            return ResponseEntity.ok(ApiResponse.success("已重试失败设备", result));
        } catch (Exception e) {
            log.error("重试失败设备失败: taskId={}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("重试失败: " + e.getMessage()));
        }
    }

    @PostMapping("/tasks/{task_id}/devices/{device_id}/retry")
    @Operation(summary = "重试单个设备")
    public ResponseEntity<ApiResponse<Void>> retrySingleDevice(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId,
            @Parameter(description = "设备ID") @PathVariable("device_id") String deviceId
    ) {
        try {
            log.info("重试单个设备: taskId={}, deviceId={}", taskId, deviceId);
            otaService.retrySingleDevice(taskId, deviceId);
            return ResponseEntity.ok(ApiResponse.success("已重试设备", null));
        } catch (Exception e) {
            log.error("重试设备失败: taskId={}, deviceId={}", taskId, deviceId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("重试失败: " + e.getMessage()));
        }
    }

    @PostMapping("/tasks/{task_id}/devices/{device_id}/rollback")
    @Operation(summary = "回滚设备升级")
    public ResponseEntity<ApiResponse<Void>> rollbackDeviceUpgrade(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId,
            @Parameter(description = "设备ID") @PathVariable("device_id") String deviceId
    ) {
        try {
            log.info("回滚设备升级: taskId={}, deviceId={}", taskId, deviceId);
            otaService.rollbackDeviceUpgrade(taskId, deviceId);
            return ResponseEntity.ok(ApiResponse.success("回滚指令已发送", null));
        } catch (Exception e) {
            log.error("回滚设备升级失败: taskId={}, deviceId={}", taskId, deviceId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("回滚失败: " + e.getMessage()));
        }
    }

    @GetMapping("/tasks/{task_id}/devices/summary")
    @Operation(summary = "获取设备状态汇总")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getDeviceStatusSummary(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId
    ) {
        try {
            Map<String, Object> summary = otaService.getDeviceStatusSummary(taskId);
            return ResponseEntity.ok(ApiResponse.success(summary));
        } catch (Exception e) {
            log.error("获取设备状态汇总失败: taskId={}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @PostMapping("/tasks/{task_id}/pause")
    @Operation(summary = "暂停升级任务")
    public ResponseEntity<ApiResponse<Void>> pauseOtaTask(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId
    ) {
        try {
            log.info("暂停升级任务: taskId={}", taskId);
            otaService.pauseOtaTask(taskId);
            return ResponseEntity.ok(ApiResponse.success("升级任务已暂停", null));
        } catch (Exception e) {
            log.error("暂停升级任务失败: taskId={}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("暂停失败: " + e.getMessage()));
        }
    }

    @PostMapping("/tasks/{task_id}/resume")
    @Operation(summary = "恢复升级任务")
    public ResponseEntity<ApiResponse<Void>> resumeOtaTask(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId
    ) {
        try {
            log.info("恢复升级任务: taskId={}", taskId);
            otaService.resumeOtaTask(taskId);
            return ResponseEntity.ok(ApiResponse.success("升级任务已恢复", null));
        } catch (Exception e) {
            log.error("恢复升级任务失败: taskId={}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("恢复失败: " + e.getMessage()));
        }
    }

    @PostMapping("/tasks/{task_id}/devices/{device_id}/replace-model")
    @Operation(summary = "替换模型（触发热加载）")
    public ResponseEntity<ApiResponse<Void>> replaceModel(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId,
            @Parameter(description = "设备ID") @PathVariable("device_id") String deviceId
    ) {
        try {
            log.info("替换模型: taskId={}, deviceId={}", taskId, deviceId);
            otaService.replaceModel(taskId, deviceId);
            return ResponseEntity.ok(ApiResponse.success("已发送模型热加载指令", null));
        } catch (Exception e) {
            log.error("替换模型失败: taskId={}, deviceId={}", taskId, deviceId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("替换失败: " + e.getMessage()));
        }
    }
}
