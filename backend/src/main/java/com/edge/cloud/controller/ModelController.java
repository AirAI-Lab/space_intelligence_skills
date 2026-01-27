package com.edge.cloud.controller;

import com.edge.cloud.dto.ApiResponse;
import com.edge.cloud.dto.ModelCreateRequest;
import com.edge.cloud.dto.ModelDTO;
import com.edge.cloud.entity.ConversionTask;
import com.edge.cloud.entity.Model;
import com.edge.cloud.service.ModelService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

/**
 * 模型管理 API
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/models")
@RequiredArgsConstructor
@Tag(name = "模型管理", description = "模型创建、上传、转换、查询等接口")
public class ModelController {

    private final ModelService modelService;

    @PostMapping
    @Operation(summary = "创建模型记录")
    public ResponseEntity<ApiResponse<ModelDTO>> createModel(
            @RequestBody ModelCreateRequest request
    ) {
        try {
            log.info("创建模型记录请求: {}", request.getModelName());
            ModelDTO result = modelService.createModel(request);
            return ResponseEntity.ok(ApiResponse.success("模型记录创建成功", result));
        } catch (Exception e) {
            log.error("创建模型记录失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("创建失败: " + e.getMessage()));
        }
    }

    @PostMapping(value = "/{model_id}/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @Operation(summary = "上传模型文件")
    public ResponseEntity<ApiResponse<ModelDTO>> uploadModelFile(
            @Parameter(description = "模型ID") @PathVariable("model_id") String modelId,
            @Parameter(description = "模型文件") @RequestParam("file") MultipartFile file
    ) {
        try {
            log.info("上传模型文件: modelId={}, size={}", modelId, file.getSize());
            ModelDTO result = modelService.uploadModelFile(modelId, file);
            return ResponseEntity.ok(ApiResponse.success("模型文件上传成功", result));
        } catch (Exception e) {
            log.error("上传模型文件失败: modelId={}", modelId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("上传失败: " + e.getMessage()));
        }
    }

    @PostMapping("/{model_id}/convert")
    @Operation(summary = "转换模型格式", description = "将模型转换为 ONNX 或 TensorRT Engine 格式")
    public ResponseEntity<ApiResponse<ModelDTO>> convertModel(
            @Parameter(description = "模型ID") @PathVariable("model_id") String modelId,
            @Parameter(description = "转换类型") @RequestParam ConversionTask.ConversionType conversionType
    ) {
        try {
            log.info("转换模型: modelId={}, type={}", modelId, conversionType);
            ModelDTO result = modelService.convertModel(modelId, conversionType);
            return ResponseEntity.ok(ApiResponse.success("模型转换任务已创建", result));
        } catch (Exception e) {
            log.error("转换模型失败: modelId={}", modelId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("转换失败: " + e.getMessage()));
        }
    }

    @GetMapping("/{model_id}")
    @Operation(summary = "获取模型详情")
    public ResponseEntity<ApiResponse<ModelDTO>> getModel(
            @Parameter(description = "模型ID") @PathVariable("model_id") String modelId
    ) {
        try {
            ModelDTO result = modelService.getModel(modelId);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("获取模型失败: modelId={}", modelId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping
    @Operation(summary = "分页查询模型列表")
    public ResponseEntity<ApiResponse<Map<String, Object>>> listModels(
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") int page,
            @Parameter(description = "每页数量") @RequestParam(defaultValue = "20") int page_size,
            @Parameter(description = "模型类型过滤") @RequestParam(required = false) Model.ModelType type,
            @Parameter(description = "状态过滤") @RequestParam(required = false) Model.ModelStatus status
    ) {
        try {
            Map<String, Object> result = modelService.listModels(page, page_size, type, status);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("查询模型列表失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("查询失败: " + e.getMessage()));
        }
    }

    @GetMapping("/deployable")
    @Operation(summary = "获取可部署的模型列表")
    public ResponseEntity<ApiResponse<List<ModelDTO>>> getDeployableModels() {
        try {
            List<ModelDTO> models = modelService.getDeployableModels();
            return ResponseEntity.ok(ApiResponse.success(models));
        } catch (Exception e) {
            log.error("获取可部署模型失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @DeleteMapping("/{model_id}")
    @Operation(summary = "删除模型")
    public ResponseEntity<ApiResponse<Void>> deleteModel(
            @Parameter(description = "模型ID") @PathVariable("model_id") String modelId
    ) {
        try {
            modelService.deleteModel(modelId);
            return ResponseEntity.ok(ApiResponse.success("模型已删除", null));
        } catch (Exception e) {
            log.error("删除模型失败: modelId={}", modelId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("删除失败: " + e.getMessage()));
        }
    }

    /**
     * 内部回调接口：增加部署计数
     */
    @PostMapping("/internal/{model_id}/deploy/increment")
    @Operation(summary = "增加部署计数（内部回调）")
    public ResponseEntity<ApiResponse<Void>> incrementDeployCount(
            @Parameter(description = "模型ID") @PathVariable("model_id") String modelId
    ) {
        try {
            modelService.incrementDeployCount(modelId);
            return ResponseEntity.ok(ApiResponse.success(null));
        } catch (Exception e) {
            log.error("增加部署计数失败: modelId={}", modelId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("更新失败: " + e.getMessage()));
        }
    }

    /**
     * 内部回调接口：减少部署计数
     */
    @PostMapping("/internal/{model_id}/deploy/decrement")
    @Operation(summary = "减少部署计数（内部回调）")
    public ResponseEntity<ApiResponse<Void>> decrementDeployCount(
            @Parameter(description = "模型ID") @PathVariable("model_id") String modelId
    ) {
        try {
            modelService.decrementDeployCount(modelId);
            return ResponseEntity.ok(ApiResponse.success(null));
        } catch (Exception e) {
            log.error("减少部署计数失败: modelId={}", modelId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("更新失败: " + e.getMessage()));
        }
    }
}
