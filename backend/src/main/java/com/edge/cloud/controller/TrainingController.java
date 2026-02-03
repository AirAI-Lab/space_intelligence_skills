package com.edge.cloud.controller;

import com.edge.cloud.dto.ApiResponse;
import com.edge.cloud.dto.TrainingJobCreateRequest;
import com.edge.cloud.dto.TrainingJobDTO;
import com.edge.cloud.dto.TrainingMetricDTO;
import com.edge.cloud.entity.TrainingJob;
import com.edge.cloud.service.TrainingService;
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
 * 训练任务管理 API
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/training")
@RequiredArgsConstructor
@Tag(name = "训练任务管理", description = "训练任务创建、启动、监控等接口")
public class TrainingController {

    private final TrainingService trainingService;

    @PostMapping
    @Operation(summary = "创建训练任务")
    public ResponseEntity<ApiResponse<TrainingJobDTO>> createTrainingJob(
            @RequestBody TrainingJobCreateRequest request
    ) {
        try {
            log.info("创建训练任务请求: {}", request.getJobName());
            TrainingJobDTO result = trainingService.createTrainingJob(request);
            return ResponseEntity.ok(ApiResponse.success("训练任务创建成功", result));
        } catch (Exception e) {
            log.error("创建训练任务失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("创建失败: " + e.getMessage()));
        }
    }

    @PostMapping("/{job_id}/start")
    @Operation(summary = "启动训练任务")
    public ResponseEntity<ApiResponse<TrainingJobDTO>> startTraining(
            @Parameter(description = "任务ID") @PathVariable("job_id") String jobId
    ) {
        try {
            log.info("启动训练任务: {}", jobId);
            TrainingJobDTO result = trainingService.startTraining(jobId);
            return ResponseEntity.ok(ApiResponse.success("训练任务已启动", result));
        } catch (Exception e) {
            log.error("启动训练任务失败: {}", jobId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("启动失败: " + e.getMessage()));
        }
    }

    @PostMapping("/{job_id}/stop")
    @Operation(summary = "停止训练任务")
    public ResponseEntity<ApiResponse<TrainingJobDTO>> stopTraining(
            @Parameter(description = "任务ID") @PathVariable("job_id") String jobId
    ) {
        try {
            log.info("停止训练任务: {}", jobId);
            TrainingJobDTO result = trainingService.stopTraining(jobId);
            return ResponseEntity.ok(ApiResponse.success("训练任务已停止", result));
        } catch (Exception e) {
            log.error("停止训练任务失败: {}", jobId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("停止失败: " + e.getMessage()));
        }
    }

    @PostMapping("/{job_id}/pause")
    @Operation(summary = "暂停训练任务")
    public ResponseEntity<ApiResponse<TrainingJobDTO>> pauseTraining(
            @Parameter(description = "任务ID") @PathVariable("job_id") String jobId
    ) {
        try {
            log.info("暂停训练任务: {}", jobId);
            TrainingJobDTO result = trainingService.pauseTraining(jobId);
            return ResponseEntity.ok(ApiResponse.success("训练任务已暂停", result));
        } catch (Exception e) {
            log.error("暂停训练任务失败: {}", jobId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("暂停失败: " + e.getMessage()));
        }
    }

    @PostMapping("/{job_id}/resume")
    @Operation(summary = "恢复训练任务")
    public ResponseEntity<ApiResponse<TrainingJobDTO>> resumeTraining(
            @Parameter(description = "任务ID") @PathVariable("job_id") String jobId
    ) {
        try {
            log.info("恢复训练任务: {}", jobId);
            TrainingJobDTO result = trainingService.resumeTraining(jobId);
            return ResponseEntity.ok(ApiResponse.success("训练任务已恢复", result));
        } catch (Exception e) {
            log.error("恢复训练任务失败: {}", jobId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("恢复失败: " + e.getMessage()));
        }
    }

    @GetMapping("/jobs")
    @Operation(summary = "分页查询训练任务列表")
    public ResponseEntity<ApiResponse<Map<String, Object>>> listTrainingJobs2(
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") int page,
            @Parameter(description = "每页数量") @RequestParam(defaultValue = "20") int pageSize,
            @Parameter(description = "状态过滤") @RequestParam(required = false) TrainingJob.TrainingStatus status
    ) {
        try {
            Map<String, Object> result = trainingService.listTrainingJobs(page, pageSize, status);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("查询训练任务列表失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("查询失败: " + e.getMessage()));
        }
    }

    @GetMapping("/{job_id}")
    @Operation(summary = "获取训练任务详情")
    public ResponseEntity<ApiResponse<TrainingJobDTO>> getTrainingJob(
            @Parameter(description = "任务ID") @PathVariable("job_id") String jobId
    ) {
        try {
            TrainingJobDTO result = trainingService.getTrainingJob(jobId);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取训练任务失败: {}", jobId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping
    @Operation(summary = "分页查询训练任务列表")
    public ResponseEntity<ApiResponse<Map<String, Object>>> listTrainingJobs(
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") int page,
            @Parameter(description = "每页数量") @RequestParam(defaultValue = "20") int page_size,
            @Parameter(description = "状态过滤") @RequestParam(required = false) TrainingJob.TrainingStatus status
    ) {
        try {
            Map<String, Object> result = trainingService.listTrainingJobs(page, page_size, status);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("查询训练任务列表失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("查询失败: " + e.getMessage()));
        }
    }

    @GetMapping("/{job_id}/metrics")
    @Operation(summary = "获取训练指标")
    public ResponseEntity<ApiResponse<List<TrainingMetricDTO>>> getTrainingMetrics(
            @Parameter(description = "任务ID") @PathVariable("job_id") String jobId
    ) {
        try {
            List<TrainingMetricDTO> metrics = trainingService.getTrainingMetrics(jobId);
            return ResponseEntity.ok(ApiResponse.success(metrics));
        } catch (Exception e) {
            log.error("获取训练指标失败: {}", jobId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @DeleteMapping("/{job_id}")
    @Operation(summary = "删除训练任务")
    public ResponseEntity<ApiResponse<Void>> deleteTrainingJob(
            @Parameter(description = "任务ID") @PathVariable("job_id") String jobId
    ) {
        try {
            trainingService.deleteTrainingJob(jobId);
            return ResponseEntity.ok(ApiResponse.success("训练任务已删除", null));
        } catch (Exception e) {
            log.error("删除训练任务失败: {}", jobId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("删除失败: " + e.getMessage()));
        }
    }

    @GetMapping("/{job_id}/logs")
    @Operation(summary = "获取训练日志")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getTrainingLogs(
            @Parameter(description = "任务ID") @PathVariable("job_id") String jobId,
            @Parameter(description = "日志行数") @RequestParam(defaultValue = "100") int lines
    ) {
        try {
            Map<String, Object> logs = trainingService.getTrainingLogs(jobId, lines);
            return ResponseEntity.ok(ApiResponse.success(logs));
        } catch (Exception e) {
            log.error("获取训练日志失败: {}", jobId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    /**
     * 内部回调接口：训练进度更新
     */
    @PostMapping("/internal/{job_id}/progress")
    @Operation(summary = "更新训练进度（内部回调）")
    public ResponseEntity<ApiResponse<Void>> updateProgress(
            @PathVariable("job_id") String jobId,
            @RequestParam int current_epoch,
            @RequestParam float progress,
            @RequestParam(required = false) Float train_loss,
            @RequestParam(required = false) Float val_loss
    ) {
        try {
            trainingService.updateTrainingProgress(jobId, current_epoch, progress, train_loss, val_loss);
            return ResponseEntity.ok(ApiResponse.success(null));
        } catch (Exception e) {
            log.error("更新训练进度失败: {}", jobId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("更新失败: " + e.getMessage()));
        }
    }

    /**
     * 内部回调接口：训练完成
     */
    @PostMapping("/internal/{job_id}/complete")
    @Operation(summary = "训练完成通知（内部回调）")
    public ResponseEntity<ApiResponse<Void>> completeTraining(
            @PathVariable("job_id") String jobId,
            @RequestParam String output_model_id,
            @RequestParam float final_map,
            @RequestParam(defaultValue = "0") float final_map50,
            @RequestParam float final_loss,
            @RequestParam int best_epoch
    ) {
        try {
            trainingService.completeTraining(jobId, output_model_id, final_map, final_map50, final_loss, best_epoch);
            return ResponseEntity.ok(ApiResponse.success(null));
        } catch (Exception e) {
            log.error("训练完成通知失败: {}", jobId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("通知失败: " + e.getMessage()));
        }
    }

    /**
     * 获取任务的实际训练进度（从 results.csv 读取）
     * 用于续训时获取原任务的实际训练轮次
     */
    @GetMapping("/{job_id}/actual-progress")
    @Operation(summary = "获取任务的实际训练进度")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getActualProgress(
            @PathVariable("job_id") String jobId
    ) {
        try {
            Map<String, Object> result = trainingService.getActualProgress(jobId);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取实际进度失败: {}", jobId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    /**
     * 从已完成的训练任务创建模型记录
     */
    @PostMapping("/{job_id}/create-model")
    @Operation(summary = "从训练任务创建模型记录")
    public ResponseEntity<ApiResponse<Map<String, Object>>> createModelFromTraining(
            @PathVariable("job_id") String jobId
    ) {
        try {
            Map<String, Object> result = trainingService.createModelFromTrainingJob(jobId);
            return ResponseEntity.ok(ApiResponse.success("模型记录创建成功", result));
        } catch (Exception e) {
            log.error("创建模型记录失败: {}", jobId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("创建失败: " + e.getMessage()));
        }
    }
}
