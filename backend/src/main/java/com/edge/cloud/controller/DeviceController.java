package com.edge.cloud.controller;

import com.edge.cloud.dto.ApiResponse;
import com.edge.cloud.entity.Device;
import com.edge.cloud.entity.DeviceCommand;
import com.edge.cloud.repository.DeviceCommandRepository;
import com.edge.cloud.repository.DeviceRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 设备管理控制器
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/devices")
@RequiredArgsConstructor
@Tag(name = "设备管理", description = "设备查询、注册、删除等接口")
public class DeviceController {

    private final DeviceRepository deviceRepository;
    private final DeviceCommandRepository deviceCommandRepository;

    @GetMapping
    @Operation(summary = "获取设备列表")
    public ResponseEntity<ApiResponse<Map<String, Object>>> list(
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") int page,
            @Parameter(description = "每页数量") @RequestParam(defaultValue = "20") int pageSize,
            @Parameter(description = "搜索关键词") @RequestParam(required = false) String search,
            @Parameter(description = "状态筛选") @RequestParam(required = false) String status
    ) {
        try {
            // 创建分页和排序
            Pageable pageable = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "createdAt"));

            Page<Device> devicePage;
            if (status != null && !status.isEmpty()) {
                Device.DeviceStatus deviceStatus = Device.DeviceStatus.valueOf(status.toUpperCase());
                devicePage = deviceRepository.findByStatus(deviceStatus, pageable);
            } else {
                devicePage = deviceRepository.findAll(pageable);
            }

            Map<String, Object> response = new HashMap<>();
            response.put("items", devicePage.getContent());
            response.put("total", devicePage.getTotalElements());
            response.put("page", page);
            response.put("pageSize", pageSize);

            return ResponseEntity.ok(ApiResponse.success(response));
        } catch (Exception e) {
            log.error("获取设备列表失败", e);
            Map<String, Object> response = new HashMap<>();
            response.put("items", new java.util.ArrayList<>());
            response.put("total", 0);
            response.put("page", page);
            response.put("pageSize", pageSize);
            return ResponseEntity.ok(ApiResponse.success(response));
        }
    }

    @PostMapping
    @Operation(summary = "注册设备")
    public ResponseEntity<ApiResponse<Map<String, Object>>> register(@RequestBody Map<String, Object> request) {
        try {
            Device device = new Device();
            device.setDeviceId((String) request.get("device_id"));
            device.setDeviceName((String) request.get("device_name"));
            device.setDeviceType((String) request.get("device_type"));
            device.setGroupId((String) request.get("group_id"));
            device.setIp((String) request.get("ip"));
            device.setMac((String) request.get("mac"));
            device.setStatus(Device.DeviceStatus.OFFLINE);
            device.setCpuUsage(0f);
            device.setGpuUsage(0f);
            device.setMemoryUsage(0f);
            device.setDiskUsage(0f);

            Device saved = deviceRepository.save(device);

            Map<String, Object> response = new HashMap<>();
            response.put("device_id", saved.getDeviceId());
            response.put("device_name", saved.getDeviceName());
            response.put("status", saved.getStatus().toString());

            return ResponseEntity.ok(ApiResponse.success("设备注册成功", response));
        } catch (Exception e) {
            log.error("注册设备失败", e);
            return ResponseEntity.status(500).body(ApiResponse.error("注册设备失败: " + e.getMessage()));
        }
    }

    @GetMapping("/{device_id}")
    @Operation(summary = "获取设备详情")
    public ResponseEntity<ApiResponse<Device>> get(@PathVariable("device_id") String deviceId) {
        Optional<Device> device = deviceRepository.findById(deviceId);
        return device.map(value -> ResponseEntity.ok(ApiResponse.success(value)))
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{device_id}")
    @Operation(summary = "删除设备")
    public ResponseEntity<ApiResponse<Map<String, Object>>> delete(@PathVariable("device_id") String deviceId) {
        try {
            if (deviceRepository.existsById(deviceId)) {
                deviceRepository.deleteById(deviceId);
                Map<String, Object> response = new HashMap<>();
                response.put("device_id", deviceId);
                return ResponseEntity.ok(ApiResponse.success("设备删除成功", response));
            } else {
                return ResponseEntity.notFound().build();
            }
        } catch (Exception e) {
            log.error("删除设备失败", e);
            return ResponseEntity.status(500).body(ApiResponse.error("删除设备失败: " + e.getMessage()));
        }
    }

    @PutMapping("/{device_id}")
    @Operation(summary = "更新设备")
    public ResponseEntity<ApiResponse<Device>> update(
            @PathVariable("device_id") String deviceId,
            @RequestBody Device device) {
        try {
            device.setDeviceId(deviceId);
            Device updated = deviceRepository.save(device);
            return ResponseEntity.ok(ApiResponse.success(updated));
        } catch (Exception e) {
            log.error("更新设备失败", e);
            return ResponseEntity.status(500).body(ApiResponse.error("更新设备失败: " + e.getMessage()));
        }
    }

    @GetMapping("/stats")
    @Operation(summary = "获取设备统计信息")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getStatistics() {
        try {
            // 统计各状态的设备数量
            List<Object[]> statusCounts = deviceRepository.countByStatus();

            Map<String, Long> statusMap = new HashMap<>();
            statusMap.put("ONLINE", 0L);
            statusMap.put("OFFLINE", 0L);
            statusMap.put("UPGRADING", 0L);
            statusMap.put("ERROR", 0L);

            long total = 0;
            for (Object[] row : statusCounts) {
                Device.DeviceStatus status = (Device.DeviceStatus) row[0];
                Long count = (Long) row[1];
                statusMap.put(status.toString(), count);
                total += count;
            }

            Map<String, Object> stats = new HashMap<>();
            stats.put("total", total);
            stats.put("statusCounts", statusMap);

            return ResponseEntity.ok(ApiResponse.success(stats));
        } catch (Exception e) {
            log.error("获取设备统计失败", e);
            return ResponseEntity.status(500).body(ApiResponse.error("获取失败: " + e.getMessage()));
        }
    }

    @GetMapping("/by-type")
    @Operation(summary = "按设备类型查询")
    public ResponseEntity<ApiResponse<List<Device>>> findByType(
            @RequestParam("type") String deviceType) {
        return ResponseEntity.ok(ApiResponse.success(deviceRepository.findByDeviceType(deviceType)));
    }

    @GetMapping("/by-category")
    @Operation(summary = "按设备类别查询")
    public ResponseEntity<ApiResponse<List<Device>>> findByCategory(
            @RequestParam("category") String category) {
        return ResponseEntity.ok(ApiResponse.success(deviceRepository.findByDeviceCategory(category)));
    }

    @GetMapping("/{device_id}/commands")
    @Operation(summary = "获取设备命令历史")
    public ResponseEntity<ApiResponse<List<DeviceCommand>>> getCommandHistory(
            @PathVariable("device_id") String deviceId) {
        return ResponseEntity.ok(ApiResponse.success(
                deviceCommandRepository.findByDeviceIdOrderByCreatedAtDesc(deviceId)));
    }
}
