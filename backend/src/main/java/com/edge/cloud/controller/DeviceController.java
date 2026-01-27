package com.edge.cloud.controller;

import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * 设备管理控制器
 */
@RestController
@RequestMapping("/api/v1/devices")
public class DeviceController {

    private final List<Map<String, Object>> devices = new ArrayList<>();

    public DeviceController() {
        // 模拟数据
        Map<String, Object> device1 = new HashMap<>();
        device1.put("device_id", "EDGE_DEVICE_001");
        device1.put("device_name", "边缘设备1");
        device1.put("device_type", "jetson_orin");
        device1.put("group_id", "group_a");
        device1.put("status", "online");
        device1.put("cpu_usage", 45);
        device1.put("gpu_usage", 60);
        device1.put("last_heartbeat", "2026-01-27 10:00:00");
        devices.add(device1);

        Map<String, Object> device2 = new HashMap<>();
        device2.put("device_id", "EDGE_DEVICE_002");
        device2.put("device_name", "边缘设备2");
        device2.put("device_type", "jetson_xavier");
        device2.put("group_id", "group_a");
        device2.put("status", "offline");
        device2.put("cpu_usage", 0);
        device2.put("gpu_usage", 0);
        device2.put("last_heartbeat", "2026-01-27 09:30:00");
        devices.add(device2);
    }

    @GetMapping
    public Map<String, Object> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int page_size,
            @RequestParam(required = false) String search,
            @RequestParam(required = false) String status) {
        Map<String, Object> response = new HashMap<>();
        response.put("items", devices);
        response.put("total", devices.size());
        response.put("page", page);
        response.put("page_size", page_size);
        return response;
    }

    @PostMapping
    public Map<String, Object> register(@RequestBody Map<String, Object> device) {
        device.put("status", "offline");
        device.put("cpu_usage", 0);
        device.put("gpu_usage", 0);
        device.put("last_heartbeat", new Date().toString());
        devices.add(device);
        return device;
    }

    @GetMapping("/{device_id}")
    public Map<String, Object> get(@PathVariable String device_id) {
        return devices.stream()
                .filter(d -> d.get("device_id").equals(device_id))
                .findFirst()
                .orElse(new HashMap<>());
    }

    @DeleteMapping("/{device_id}")
    public Map<String, Object> delete(@PathVariable String device_id) {
        devices.removeIf(d -> d.get("device_id").equals(device_id));
        Map<String, Object> response = new HashMap<>();
        response.put("message", "Device deleted successfully");
        return response;
    }
}
