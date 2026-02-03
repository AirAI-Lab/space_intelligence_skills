package com.edge.cloud.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * 设备兼容性检查请求
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CompatibilityCheckRequest {

    /**
     * 模型ID
     */
    private String modelId;

    /**
     * 目标设备ID列表
     */
    private List<String> deviceIds;

    /**
     * 模型格式类型（可选）
     */
    private String modelFormat;

    /**
     * 模型大小（字节）
     */
    private Long modelSizeBytes;

    /**
     * 模型输入分辨率
     */
    private Map<String, Integer> inputResolution;

    /**
     * 是否需要TensorRT
     */
    private Boolean requireTensorRt;

    /**
     * 最低TensorRT版本
     */
    private String minTensorRtVersion;

    /**
     * 最低显存要求(MB)
     */
    private Integer minGpuMemoryMb;

    /**
     * 最低内存要求(MB)
     */
    private Integer minMemoryMb;

    /**
     * 最低磁盘空间要求(MB)
     */
    private Integer minDiskMb;
}
