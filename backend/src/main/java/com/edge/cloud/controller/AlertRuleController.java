package com.edge.cloud.controller;

import com.edge.cloud.dto.AlertRuleRequest;
import com.edge.cloud.dto.ApiResponse;
import com.edge.cloud.entity.AlertRule;
import com.edge.cloud.service.AlertRuleService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/v1/alert-rules")
@RequiredArgsConstructor
@Tag(name = "告警规则管理", description = "告警规则的增删改查")
public class AlertRuleController {

    private final AlertRuleService alertRuleService;

    @GetMapping
    @Operation(summary = "获取所有告警规则")
    public ResponseEntity<ApiResponse<List<AlertRule>>> listRules() {
        return ResponseEntity.ok(ApiResponse.success(alertRuleService.listRules()));
    }

    @PostMapping
    @Operation(summary = "创建告警规则")
    public ResponseEntity<ApiResponse<AlertRule>> createRule(@RequestBody AlertRuleRequest request) {
        try {
            return ResponseEntity.ok(ApiResponse.success("创建成功", alertRuleService.createRule(request)));
        } catch (Exception e) {
            log.error("创建告警规则失败", e);
            return ResponseEntity.status(500).body(ApiResponse.error("创建失败: " + e.getMessage()));
        }
    }

    @PutMapping("/{id}")
    @Operation(summary = "更新告警规则")
    public ResponseEntity<ApiResponse<AlertRule>> updateRule(
            @PathVariable Long id, @RequestBody AlertRuleRequest request) {
        try {
            return ResponseEntity.ok(ApiResponse.success("更新成功", alertRuleService.updateRule(id, request)));
        } catch (RuntimeException e) {
            return ResponseEntity.status(404).body(ApiResponse.error(404, e.getMessage()));
        } catch (Exception e) {
            log.error("更新告警规则失败: id={}", id, e);
            return ResponseEntity.status(500).body(ApiResponse.error("更新失败: " + e.getMessage()));
        }
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除告警规则")
    public ResponseEntity<ApiResponse<Void>> deleteRule(@PathVariable Long id) {
        alertRuleService.deleteRule(id);
        return ResponseEntity.ok(ApiResponse.success("删除成功", null));
    }
}
