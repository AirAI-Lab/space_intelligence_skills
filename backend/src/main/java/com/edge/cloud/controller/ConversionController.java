package com.edge.cloud.controller;

import com.edge.cloud.dto.ApiResponse;
import com.edge.cloud.dto.ConversionTaskDTO;
import com.edge.cloud.entity.ConversionTask;
import com.edge.cloud.service.ConversionService;
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
 * 模型转换 API
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/conversion")
@RequiredArgsConstructor
@Tag(name = "模型转换", description = "模型格式转换任务管理接口")
public class ConversionController {

    private final ConversionService conversionService;

    @PostMapping("/{task_id}/start")
    @Operation(summary = "启动转换任务")
    public ResponseEntity<ApiResponse<ConversionTaskDTO>> startConversion(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId
    ) {
        try {
            log.info("启动转换任务: {}", taskId);
            ConversionTaskDTO result = conversionService.startConversion(taskId);
            return ResponseEntity.ok(ApiResponse.success("转换任务已启动", result));
        } catch (Exception e) {
            log.error("启动转换任务失败: {}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("启动失败: " + e.getMessage()));
        }
    }

    @GetMapping("/tasks/{task_id}")
    @Operation(summary = "获取转换任务详情")
    public ResponseEntity<ApiResponse<ConversionTaskDTO>> getConversionTask(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId
    ) {
        try {
            ConversionTaskDTO result = conversionService.getConversionTask(taskId);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取转换任务失败: {}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping("/tasks")
    @Operation(summary = "分页查询转换任务")
    public ResponseEntity<ApiResponse<Map<String, Object>>> listConversionTasks(
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") int page,
            @Parameter(description = "每页数量") @RequestParam(defaultValue = "20") int page_size,
            @Parameter(description = "状态过滤") @RequestParam(required = false) ConversionTask.ConversionStatus status
    ) {
        try {
            Map<String, Object> result = conversionService.listConversionTasks(page, page_size, status);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("查询转换任务列表失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("查询失败: " + e.getMessage()));
        }
    }

    @GetMapping("/models/{model_id}/tasks")
    @Operation(summary = "根据模型ID查询转换任务")
    public ResponseEntity<ApiResponse<List<ConversionTaskDTO>>> getConversionTasksByModel(
            @Parameter(description = "模型ID") @PathVariable("model_id") String modelId
    ) {
        try {
            List<ConversionTaskDTO> result = conversionService.getConversionTasksByModel(modelId);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("查询模型转换任务失败: modelId={}", modelId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("查询失败: " + e.getMessage()));
        }
    }

    @DeleteMapping("/tasks/{task_id}")
    @Operation(summary = "删除转换任务")
    public ResponseEntity<ApiResponse<Void>> deleteConversionTask(
            @Parameter(description = "任务ID") @PathVariable("task_id") String taskId
    ) {
        try {
            conversionService.deleteConversionTask(taskId);
            return ResponseEntity.ok(ApiResponse.success("转换任务已删除", null));
        } catch (Exception e) {
            log.error("删除转换任务失败: {}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("删除失败: " + e.getMessage()));
        }
    }

    /**
     * 内部回调接口：更新转换进度
     */
    @PostMapping("/internal/{task_id}/progress")
    @Operation(summary = "更新转换进度（内部回调）")
    public ResponseEntity<ApiResponse<Void>> updateProgress(
            @PathVariable("task_id") String taskId,
            @RequestParam float progress
    ) {
        try {
            conversionService.updateConversionProgress(taskId, progress);
            return ResponseEntity.ok(ApiResponse.success(null));
        } catch (Exception e) {
            log.error("更新转换进度失败: {}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("更新失败: " + e.getMessage()));
        }
    }

    /**
     * 内部回调接口：转换完成
     */
    @PostMapping("/internal/{task_id}/complete")
    @Operation(summary = "转换完成通知（内部回调）")
    public ResponseEntity<ApiResponse<Void>> completeConversion(
            @PathVariable("task_id") String taskId,
            @RequestParam String output_path,
            @RequestParam long file_size_bytes,
            @RequestParam int optimization_time_seconds
    ) {
        try {
            conversionService.completeConversion(taskId, output_path, file_size_bytes, optimization_time_seconds);
            return ResponseEntity.ok(ApiResponse.success(null));
        } catch (Exception e) {
            log.error("转换完成通知失败: {}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("通知失败: " + e.getMessage()));
        }
    }

    /**
     * 内部回调接口：转换失败
     */
    @PostMapping("/internal/{task_id}/fail")
    @Operation(summary = "转换失败通知（内部回调）")
    public ResponseEntity<ApiResponse<Void>> failConversion(
            @PathVariable("task_id") String taskId,
            @RequestParam String error_message
    ) {
        try {
            conversionService.failConversion(taskId, error_message);
            return ResponseEntity.ok(ApiResponse.success(null));
        } catch (Exception e) {
            log.error("转换失败通知失败: {}", taskId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("通知失败: " + e.getMessage()));
        }
    }
}
