package com.edge.cloud.controller;

import com.edge.cloud.dto.ApiResponse;
import com.edge.cloud.dto.CompatibilityCheckRequest;
import com.edge.cloud.dto.CompatibilityCheckResult;
import com.edge.cloud.service.DeviceCompatibilityService;
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
 * 设备兼容性检查 API
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/compatibility")
@RequiredArgsConstructor
@Tag(name = "设备兼容性检查", description = "模型部署前的设备兼容性检查接口")
public class DeviceCompatibilityController {

    private final DeviceCompatibilityService compatibilityService;

    @PostMapping("/check")
    @Operation(summary = "检查设备兼容性", description = "检查指定设备是否满足模型部署要求")
    public ResponseEntity<ApiResponse<Map<String, CompatibilityCheckResult>>> checkCompatibility(
            @RequestBody CompatibilityCheckRequest request
    ) {
        try {
            log.info("检查设备兼容性: modelId={}, deviceCount={}",
                    request.getModelId(), request.getDeviceIds().size());

            Map<String, CompatibilityCheckResult> results =
                    compatibilityService.batchCheckCompatibility(request);

            return ResponseEntity.ok(ApiResponse.success("兼容性检查完成", results));
        } catch (Exception e) {
            log.error("检查兼容性失败", e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("检查失败: " + e.getMessage()));
        }
    }

    @GetMapping("/check/{device_id}/{model_id}")
    @Operation(summary = "检查单个设备兼容性")
    public ResponseEntity<ApiResponse<CompatibilityCheckResult>> checkSingleDevice(
            @Parameter(description = "设备ID") @PathVariable("device_id") String deviceId,
            @Parameter(description = "模型ID") @PathVariable("model_id") String modelId
    ) {
        try {
            CompatibilityCheckResult result =
                    compatibilityService.checkCompatibility(deviceId, modelId);

            return ResponseEntity.ok(ApiResponse.success(result));
        } catch (Exception e) {
            log.error("检查兼容性失败: deviceId={}, modelId={}", deviceId, modelId, e);
            return ResponseEntity.status(500)
                    .body(ApiResponse.error("检查失败: " + e.getMessage()));
        }
    }

    @GetMapping("/device-types")
    @Operation(summary = "获取支持的设备类型列表")
    public ResponseEntity<ApiResponse<List<DeviceInfo>>> getSupportedDeviceTypes() {
        List<DeviceInfo> deviceTypes = List.of(
                new DeviceInfo("JETSON_ORIN", "NVIDIA Jetson Orin", 20480, 32, 8192),
                new DeviceInfo("JETSON_XAVIER", "NVIDIA Jetson Xavier", 16384, 32, 8192),
                new DeviceInfo("JETSON_NANO", "NVIDIA Jetson Nano", 4096, 4, 4096),
                new DeviceInfo("EDGE_BOX", "Edge Box", 8192, 8, 4096)
        );
        return ResponseEntity.ok(ApiResponse.success(deviceTypes));
    }

    /**
     * 设备信息
     */
    public record DeviceInfo(
            String deviceType,
            String deviceName,
            Integer gpuMemoryMb,
            Integer systemMemoryGb,
            Integer storageGb
    ) {}
}
