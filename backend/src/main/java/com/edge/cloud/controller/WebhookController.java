package com.edge.cloud.controller;

import com.edge.cloud.dto.ApiResponse;
import com.edge.cloud.dto.WebhookConfigRequest;
import com.edge.cloud.entity.WebhookConfig;
import com.edge.cloud.service.WebhookService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/v1/webhooks")
@RequiredArgsConstructor
@Tag(name = "Webhook管理", description = "Webhook配置的增删改查")
public class WebhookController {

    private final WebhookService webhookService;

    @GetMapping
    @Operation(summary = "获取所有Webhook配置")
    public ResponseEntity<ApiResponse<List<WebhookConfig>>> listConfigs() {
        return ResponseEntity.ok(ApiResponse.success(webhookService.listConfigs()));
    }

    @PostMapping
    @Operation(summary = "创建Webhook配置")
    public ResponseEntity<ApiResponse<WebhookConfig>> createConfig(@RequestBody WebhookConfigRequest request) {
        try {
            return ResponseEntity.ok(ApiResponse.success("创建成功", webhookService.createConfig(request)));
        } catch (Exception e) {
            log.error("创建Webhook失败", e);
            return ResponseEntity.status(500).body(ApiResponse.error("创建失败: " + e.getMessage()));
        }
    }

    @PutMapping("/{id}")
    @Operation(summary = "更新Webhook配置")
    public ResponseEntity<ApiResponse<WebhookConfig>> updateConfig(
            @PathVariable Long id, @RequestBody WebhookConfigRequest request) {
        try {
            return ResponseEntity.ok(ApiResponse.success("更新成功", webhookService.updateConfig(id, request)));
        } catch (RuntimeException e) {
            return ResponseEntity.status(404).body(ApiResponse.error(404, e.getMessage()));
        } catch (Exception e) {
            log.error("更新Webhook失败: id={}", id, e);
            return ResponseEntity.status(500).body(ApiResponse.error("更新失败: " + e.getMessage()));
        }
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除Webhook配置")
    public ResponseEntity<ApiResponse<Void>> deleteConfig(@PathVariable Long id) {
        webhookService.deleteConfig(id);
        return ResponseEntity.ok(ApiResponse.success("删除成功", null));
    }
}
