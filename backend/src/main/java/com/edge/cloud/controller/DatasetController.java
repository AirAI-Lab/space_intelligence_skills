package com.edge.cloud.controller;

import com.edge.cloud.dto.ApiResponse;
import com.edge.cloud.dto.DatasetDTO;
import com.edge.cloud.dto.DatasetUploadRequest;
import com.edge.cloud.entity.Dataset;
import com.edge.cloud.service.DatasetService;
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
 * 数据集管理 API
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/datasets")
@RequiredArgsConstructor
@Tag(name = "数据集管理", description = "数据集上传、验证、查询等接口")
public class DatasetController {

    private final DatasetService datasetService;

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @Operation(summary = "上传/添加数据集", description = "上传 YOLO/COCO/VOC 格式的数据集压缩包，或指定本地路径")
    public ResponseEntity<ApiResponse<DatasetDTO>> uploadDataset(
            @Parameter(description = "数据集文件（上传方式必需）") @RequestParam(value = "file", required = false) MultipartFile file,
            @Parameter(description = "数据集名称") @RequestParam("datasetName") String datasetName,
            @Parameter(description = "数据集类型") @RequestParam("datasetType") Dataset.DatasetType datasetType,
            @Parameter(description = "数据集格式") @RequestParam(value = "format", defaultValue = "yolov8") String format,
            @Parameter(description = "描述") @RequestParam(value = "description", required = false) String description,
            @Parameter(description = "数据集来源：upload（上传）或 local（本地路径）") @RequestParam(value = "datasetSource", defaultValue = "upload") String datasetSource,
            @Parameter(description = "本地路径（本地方式必需）") @RequestParam(value = "localPath", required = false) String localPath
    ) {
        try {
            log.info("收到数据集添加请求: name={}, type={}, source={}", datasetName, datasetType, datasetSource);

            DatasetUploadRequest request = new DatasetUploadRequest();
            request.setDatasetName(datasetName);
            request.setDatasetType(datasetType);
            request.setFormat(format);
            request.setDescription(description);
            request.setDatasetSource(datasetSource);
            request.setLocalPath(localPath);

            DatasetDTO result = datasetService.uploadDataset(file, request);
            return ResponseEntity.ok(ApiResponse.success("数据集添加成功", result));

        } catch (Exception e) {
            log.error("数据集添加失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("数据集添加失败: " + e.getMessage()));
        }
    }

    @GetMapping("/{dataset_id}")
    @Operation(summary = "获取数据集详情")
    public ResponseEntity<ApiResponse<DatasetDTO>> getDataset(
            @Parameter(description = "数据集ID") @PathVariable("dataset_id") String datasetId
    ) {
        try {
            DatasetDTO dataset = datasetService.getDataset(datasetId);
            return ResponseEntity.ok(ApiResponse.success(dataset));
        } catch (Exception e) {
            log.error("获取数据集失败: {}", datasetId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取数据集失败: " + e.getMessage()));
        }
    }

    @GetMapping
    @Operation(summary = "分页查询数据集列表")
    public ResponseEntity<ApiResponse<Map<String, Object>>> listDatasets(
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") int page,
            @Parameter(description = "每页数量") @RequestParam(defaultValue = "20") int pageSize,
            @Parameter(description = "搜索关键词") @RequestParam(required = false) String search,
            @Parameter(description = "状态过滤") @RequestParam(required = false) Dataset.DatasetStatus status
    ) {
        try {
            Map<String, Object> result = datasetService.listDatasets(page, pageSize, search, status);
            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("查询数据集列表失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("查询失败: " + e.getMessage()));
        }
    }

    @GetMapping("/available")
    @Operation(summary = "获取可用数据集（用于训练）")
    public ResponseEntity<ApiResponse<List<DatasetDTO>>> getAvailableDatasets() {
        try {
            List<DatasetDTO> datasets = datasetService.getAvailableDatasets();
            return ResponseEntity.ok(ApiResponse.success(datasets));
        } catch (Exception e) {
            log.error("获取可用数据集失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @PostMapping("/{dataset_id}/validate")
    @Operation(summary = "验证数据集", description = "手动触发数据集格式验证和统计")
    public ResponseEntity<ApiResponse<DatasetDTO>> validateDataset(
            @Parameter(description = "数据集ID") @PathVariable("dataset_id") String datasetId
    ) {
        try {
            DatasetDTO dataset = datasetService.validateDataset(datasetId);
            return ResponseEntity.ok(ApiResponse.success("数据集验证已启动", dataset));
        } catch (Exception e) {
            log.error("数据集验证失败: {}", datasetId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("验证失败: " + e.getMessage()));
        }
    }

    @DeleteMapping("/{dataset_id}")
    @Operation(summary = "删除数据集")
    public ResponseEntity<ApiResponse<Void>> deleteDataset(
            @Parameter(description = "数据集ID") @PathVariable("dataset_id") String datasetId
    ) {
        try {
            datasetService.deleteDataset(datasetId);
            return ResponseEntity.ok(ApiResponse.success("数据集已删除", null));
        } catch (Exception e) {
            log.error("删除数据集失败: {}", datasetId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("删除失败: " + e.getMessage()));
        }
    }

    @GetMapping("/stats")
    @Operation(summary = "获取数据集统计信息")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getStatistics() {
        try {
            Map<String, Object> stats = datasetService.getStatistics();
            return ResponseEntity.ok(ApiResponse.success(stats));
        } catch (Exception e) {
            log.error("获取统计信息失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }
}
