package com.edge.cloud.service;

import com.edge.cloud.dto.CompatibilityCheckRequest;
import com.edge.cloud.dto.CompatibilityCheckResult;
import com.edge.cloud.entity.Device;
import com.edge.cloud.entity.Model;
import com.edge.cloud.repository.DeviceRepository;
import com.edge.cloud.repository.ModelRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;

/**
 * 设备兼容性检查服务
 * 用于检查设备是否满足模型部署的硬件、软件和资源要求
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DeviceCompatibilityService {

    private final DeviceRepository deviceRepository;
    private final ModelRepository modelRepository;

    // 硬件兼容性配置
    private static final Map<String, HardwareSpec> HARDWARE_SPECS = new HashMap<>();
    static {
        // Jetson Orin
        HARDWARE_SPECS.put("JETSON_ORIN", new HardwareSpec(
            "Orin", 20480, 32, 8192, "8.6"
        ));
        // Jetson Xavier
        HARDWARE_SPECS.put("JETSON_XAVIER", new HardwareSpec(
            "Xavier", 16384, 32, 8192, "7.2"
        ));
        // Jetson Nano
        HARDWARE_SPECS.put("JETSON_NANO", new HardwareSpec(
            "Nano", 4096, 4, 4096, "5.3"
        ));
        // Edge Box
        HARDWARE_SPECS.put("EDGE_BOX", new HardwareSpec(
            "EdgeBox", 8192, 8, 4096, "6.0"
        ));
    }

    // TensorRT版本兼容性
    private static final String MIN_TENSORRT_VERSION = "8.0.0";

    /**
     * 检查单个设备的兼容性
     */
    public CompatibilityCheckResult checkCompatibility(String deviceId, String modelId) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));

        return checkCompatibility(deviceId, model);
    }

    /**
     * 批量检查设备兼容性
     */
    public Map<String, CompatibilityCheckResult> batchCheckCompatibility(
            CompatibilityCheckRequest request) {

        // 获取模型信息
        Model model = modelRepository.findById(request.getModelId())
                .orElseThrow(() -> new RuntimeException("模型不存在: " + request.getModelId()));

        // 批量检查
        Map<String, CompatibilityCheckResult> results = new HashMap<>();
        for (String deviceId : request.getDeviceIds()) {
            try {
                CompatibilityCheckResult result = checkCompatibility(deviceId, model);
                results.put(deviceId, result);
            } catch (Exception e) {
                log.error("检查设备兼容性失败: deviceId={}, error={}", deviceId, e.getMessage());
                results.put(deviceId, CompatibilityCheckResult.builder()
                        .deviceId(deviceId)
                        .status(CompatibilityCheckResult.CompatibilityStatus.UNKNOWN)
                        .errors(List.of("检查失败: " + e.getMessage()))
                        .build());
            }
        }

        return results;
    }

    /**
     * 检查设备兼容性（核心逻辑）
     */
    private CompatibilityCheckResult checkCompatibility(String deviceId, Model model) {
        Device device = deviceRepository.findById(deviceId)
                .orElseThrow(() -> new RuntimeException("设备不存在: " + deviceId));

        List<CompatibilityCheckResult.CheckDetail> details = new ArrayList<>();
        List<String> warnings = new ArrayList<>();
        List<String> errors = new ArrayList<>();
        List<String> recommendations = new ArrayList<>();
        int score = 100;

        // 1. 检查设备状态
        if (device.getStatus() != Device.DeviceStatus.ONLINE) {
            errors.add("设备当前状态为: " + device.getStatus() + "，无法部署");
            return CompatibilityCheckResult.builder()
                    .deviceId(deviceId)
                    .deviceName(device.getDeviceName())
                    .status(CompatibilityCheckResult.CompatibilityStatus.UNKNOWN)
                    .score(0)
                    .errors(errors)
                    .build();
        }

        // 2. 硬件兼容性检查
        CompatibilityCheckResult.CheckDetail gpuCheck = checkGpuCompatibility(device, model);
        details.add(gpuCheck);
        if (!gpuCheck.isPassed()) {
            errors.add(gpuCheck.getMessage());
            score -= 40;
        }

        // 3. 显存检查
        CompatibilityCheckResult.CheckDetail gpuMemoryCheck = checkGpuMemory(device, model);
        details.add(gpuMemoryCheck);
        if (!gpuMemoryCheck.isPassed()) {
            errors.add(gpuMemoryCheck.getMessage());
            score -= 30;
        } else if (gpuMemoryCheck.getMessage() != null &&
                   gpuMemoryCheck.getMessage().contains("接近上限")) {
            warnings.add(gpuMemoryCheck.getMessage());
            score -= 10;
        }

        // 4. 内存检查
        CompatibilityCheckResult.CheckDetail memoryCheck = checkMemory(device, model);
        details.add(memoryCheck);
        if (!memoryCheck.isPassed()) {
            errors.add(memoryCheck.getMessage());
            score -= 25;
        }

        // 5. 磁盘空间检查
        CompatibilityCheckResult.CheckDetail diskCheck = checkDiskSpace(device, model);
        details.add(diskCheck);
        if (!diskCheck.isPassed()) {
            errors.add(diskCheck.getMessage());
            score -= 20;
        } else if (diskCheck.getMessage() != null &&
                   diskCheck.getMessage().contains("空间紧张")) {
            warnings.add(diskCheck.getMessage());
            score -= 5;
        }

        // 6. TensorRT版本检查
        CompatibilityCheckResult.CheckDetail tensorRtCheck = checkTensorRtVersion(device, model);
        details.add(tensorRtCheck);
        if (!tensorRtCheck.isPassed()) {
            errors.add(tensorRtCheck.getMessage());
            score -= 35;
        }

        // 7. 生成推荐操作
        if (!warnings.isEmpty() || !errors.isEmpty()) {
            recommendations.addAll(generateRecommendations(device, details));
        }

        // 确定兼容性状态
        CompatibilityCheckResult.CompatibilityStatus status;
        if (score >= 80) {
            status = CompatibilityCheckResult.CompatibilityStatus.COMPATIBLE;
        } else if (score >= 50) {
            status = CompatibilityCheckResult.CompatibilityStatus.COMPATIBLE_WITH_WARNING;
        } else {
            status = CompatibilityCheckResult.CompatibilityStatus.NOT_COMPATIBLE;
        }

        return CompatibilityCheckResult.builder()
                .deviceId(deviceId)
                .deviceName(device.getDeviceName())
                .status(status)
                .score(Math.max(0, score))
                .details(details)
                .warnings(warnings)
                .errors(errors)
                .recommendations(recommendations)
                .build();
    }

    /**
     * 检查GPU兼容性
     */
    private CompatibilityCheckResult.CheckDetail checkGpuCompatibility(Device device, Model model) {
        String deviceType = device.getDeviceType();
        HardwareSpec spec = HARDWARE_SPECS.get(deviceType);

        boolean passed = spec != null;
        String message = passed ? null : "不支持的设备类型: " + deviceType;

        return CompatibilityCheckResult.CheckDetail.builder()
                .category("hardware")
                .item("gpu_type")
                .passed(passed)
                .requirement("支持的设备类型")
                .actual(deviceType)
                .message(message)
                .build();
    }

    /**
     * 检查GPU显存
     */
    private CompatibilityCheckResult.CheckDetail checkGpuMemory(Device device, Model model) {
        // 根据模型输入大小估算显存需求
        int inputPixels = model.getInputWidth() * model.getInputHeight();
        int requiredGpuMemory = 1024; // 基础需求 1GB

        // 根据输入分辨率调整
        if (inputPixels > 640 * 640) {
            requiredGpuMemory = 2048;
        }
        if (inputPixels > 1280 * 1280) {
            requiredGpuMemory = 4096;
        }

        Integer availableGpuMemory = device.getGpuMemoryMb();
        if (availableGpuMemory == null) {
            return CompatibilityCheckResult.CheckDetail.builder()
                    .category("resource")
                    .item("gpu_memory")
                    .passed(false)
                    .requirement(requiredGpuMemory + " MB")
                    .actual("未知")
                    .message("无法获取GPU显存信息")
                    .build();
        }

        // 计算可用显存（考虑当前使用）
        int usedMemory = device.getGpuUsage() != null ?
                (int) (availableGpuMemory * device.getGpuUsage() / 100) : 0;
        int freeMemory = availableGpuMemory - usedMemory;

        boolean passed = freeMemory >= requiredGpuMemory;
        String message;
        if (!passed) {
            message = String.format("GPU显存不足: 需要 %d MB，可用 %d MB",
                    requiredGpuMemory, freeMemory);
        } else if (freeMemory < requiredGpuMemory * 1.5) {
            message = String.format("GPU显存接近上限: 需要 %d MB，可用 %d MB",
                    requiredGpuMemory, freeMemory);
        } else {
            message = null;
        }

        return CompatibilityCheckResult.CheckDetail.builder()
                .category("resource")
                .item("gpu_memory")
                .passed(passed)
                .requirement("≥" + requiredGpuMemory + " MB")
                .actual(freeMemory + " MB")
                .message(message)
                .build();
    }

    /**
     * 检查系统内存
     */
    private CompatibilityCheckResult.CheckDetail checkMemory(Device device, Model model) {
        Integer totalMemory = device.getTotalMemoryMb();
        if (totalMemory == null) {
            totalMemory = 8192; // 默认8GB
        }

        int requiredMemory = 4096; // 最低4GB
        boolean passed = totalMemory >= requiredMemory;
        String message = passed ? null :
                String.format("系统内存不足: 需要 %d MB，当前 %d MB",
                        requiredMemory, totalMemory);

        return CompatibilityCheckResult.CheckDetail.builder()
                .category("resource")
                .item("memory")
                .passed(passed)
                .requirement("≥" + requiredMemory + " MB")
                .actual(totalMemory + " MB")
                .message(message)
                .build();
    }

    /**
     * 检查磁盘空间
     */
    private CompatibilityCheckResult.CheckDetail checkDiskSpace(Device device, Model model) {
        long modelSize = model.getFileSizeBytes() != null ? model.getFileSizeBytes() : 100 * 1024 * 1024;
        int requiredDisk = (int) (modelSize / 1024 / 1024) + 500; // 模型大小 + 500MB 缓冲

        Integer totalDisk = device.getTotalDiskMb();
        if (totalDisk == null) {
            return CompatibilityCheckResult.CheckDetail.builder()
                    .category("resource")
                    .item("disk_space")
                    .passed(true)
                    .requirement("≥" + requiredDisk + " MB")
                    .actual("未知")
                    .message("无法获取磁盘信息，假设空间充足")
                    .build();
        }

        Float diskUsage = device.getDiskUsage();
        int freeDisk = diskUsage != null ?
                (int) (totalDisk * (100 - diskUsage) / 100) : totalDisk;

        boolean passed = freeDisk >= requiredDisk;
        String message;
        if (!passed) {
            message = String.format("磁盘空间不足: 需要 %d MB，可用 %d MB",
                    requiredDisk, freeDisk);
        } else if (freeDisk < requiredDisk * 2) {
            message = String.format("磁盘空间紧张: 需要 %d MB，可用 %d MB",
                    requiredDisk, freeDisk);
        } else {
            message = null;
        }

        return CompatibilityCheckResult.CheckDetail.builder()
                .category("resource")
                .item("disk_space")
                .passed(passed)
                .requirement("≥" + requiredDisk + " MB")
                .actual(freeDisk + " MB")
                .message(message)
                .build();
    }

    /**
     * 检查TensorRT版本
     */
    private CompatibilityCheckResult.CheckDetail checkTensorRtVersion(Device device, Model model) {
        // 如果模型不是TensorRT格式，跳过检查
        if (model.getEngineFilePath() == null) {
            return CompatibilityCheckResult.CheckDetail.builder()
                    .category("software")
                    .item("tensorrt_version")
                    .passed(true)
                    .requirement("-")
                    .actual("非TensorRT模型")
                    .message(null)
                    .build();
        }

        // 检查设备类型是否支持TensorRT
        String deviceType = device.getDeviceType();
        boolean supported = deviceType != null &&
                (deviceType.contains("JETSON") || deviceType.contains("EDGE") ||
                 deviceType.contains("ORIN") || deviceType.contains("XAVIER"));

        String message = supported ? null :
                "设备类型 " + deviceType + " 可能不支持TensorRT";

        return CompatibilityCheckResult.CheckDetail.builder()
                .category("software")
                .item("tensorrt_support")
                .passed(supported)
                .requirement("TensorRT支持")
                .actual(deviceType)
                .message(message)
                .build();
    }

    /**
     * 生成推荐操作
     */
    private List<String> generateRecommendations(Device device,
                                                  List<CompatibilityCheckResult.CheckDetail> details) {
        List<String> recommendations = new ArrayList<>();

        for (CompatibilityCheckResult.CheckDetail detail : details) {
            if (!detail.isPassed()) {
                switch (detail.getItem()) {
                    case "gpu_memory":
                        recommendations.add("考虑停止其他占用GPU的进程，或使用显存更小的模型格式（如INT8量化）");
                        break;
                    case "memory":
                        recommendations.add("建议增加系统内存，或减少其他运行的程序");
                        break;
                    case "disk_space":
                        recommendations.add("清理不必要的文件释放磁盘空间");
                        break;
                    case "tensorrt_support":
                        recommendations.add("考虑使用ONNX格式模型，或升级到支持TensorRT的设备");
                        break;
                    default:
                        recommendations.add("检查设备配置是否正确");
                }
            }
        }

        return recommendations;
    }

    /**
     * 硬件规格配置
     */
    private static class HardwareSpec {
        final String gpuModel;
        final int gpuMemoryMb;
        final int memoryGb;
        final int storageGb;
        final String computeCapability;

        HardwareSpec(String gpuModel, int gpuMemoryMb, int memoryGb,
                    int storageGb, String computeCapability) {
            this.gpuModel = gpuModel;
            this.gpuMemoryMb = gpuMemoryMb;
            this.memoryGb = memoryGb;
            this.storageGb = storageGb;
            this.computeCapability = computeCapability;
        }
    }
}
