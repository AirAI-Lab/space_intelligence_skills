package com.edge.cloud.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 设备兼容性检查结果
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CompatibilityCheckResult {

    /**
     * 设备ID
     */
    private String deviceId;

    /**
     * 设备名称
     */
    private String deviceName;

    /**
     * 兼容性状态
     */
    private CompatibilityStatus status;

    /**
     * 兼容性得分 (0-100)
     */
    private Integer score;

    /**
     * 检查详情
     */
    private List<CheckDetail> details;

    /**
     * 警告信息
     */
    private List<String> warnings;

    /**
     * 错误信息
     */
    private List<String> errors;

    /**
     * 推荐操作
     */
    private List<String> recommendations;

    /**
     * 兼容性状态枚举
     */
    public enum CompatibilityStatus {
        COMPATIBLE,        // 完全兼容
        COMPATIBLE_WITH_WARNING,  // 兼容但有警告
        NOT_COMPATIBLE,    // 不兼容
        UNKNOWN            // 未知状态（设备离线等）
    }

    /**
     * 检查详情
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CheckDetail {
        private String category;      // 检查类别：hardware, software, resource
        private String item;          // 检查项：gpu, memory, tensorrt_version, etc.
        private boolean passed;       // 是否通过
        private String requirement;   // 要求
        private String actual;        // 实际值
        private String message;       // 详细信息
    }
}
