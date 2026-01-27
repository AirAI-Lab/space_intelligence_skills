package com.edge.cloud.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

/**
 * 健康检查控制器
 */
@RestController
@RequestMapping("/actuator")
public class HealthController {

    @GetMapping("/health")
    public Map<String, Object> health() {
        Map<String, Object> response = new HashMap<>();
        response.put("status", "UP");
        response.put("service", "edge-cloud-backend");
        return response;
    }

    @GetMapping
    public Map<String, Object> info() {
        Map<String, Object> response = new HashMap<>();
        response.put("name", "edge-infer-cloud");
        response.put("description", "云边协同管理平台后端");
        response.put("version", "1.0.0");
        return response;
    }
}
