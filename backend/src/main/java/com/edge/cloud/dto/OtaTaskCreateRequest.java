package com.edge.cloud.dto;

import com.edge.cloud.entity.OtaTask;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 创建 OTA 升级任务请求
 */
@Data
public class OtaTaskCreateRequest {

    private String taskName;
    private OtaTask.UpgradeType upgradeType;
    private String modelId;              // 模型升级时使用
    private String targetVersion;        // 目标版本号
    private OtaTask.UpgradeStrategy strategy;
    private LocalDateTime scheduledTime; // 定时升级时间
    private List<String> deviceIds;      // 目标设备列表
    private String groupId;              // 设备组ID（可选，批量升级）
}
