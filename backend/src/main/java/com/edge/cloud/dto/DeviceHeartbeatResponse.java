package com.edge.cloud.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 设备心跳响应 (云端 -> 边缘端)
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DeviceHeartbeatResponse {

    /**
     * 响应状态: SUCCESS, ERROR
     */
    private String status;

    /**
     * 响应消息
     */
    private String message;

    /**
     * 云端时间戳
     */
    private Long serverTime;

    /**
     * 待执行的命令列表
     */
    private List<DeviceCommand> commands;

    /**
     * 转换为Map (用于注册响应)
     */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("status", status);
        map.put("message", message);
        map.put("serverTime", serverTime);
        if (commands != null) {
            map.put("commands", commands);
        }
        return map;
    }

    /**
     * 设备命令
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DeviceCommand {
        /**
         * 命令类型: OTA_UPDATE, CONFIG_UPDATE, RESTART, STOP
         */
        private String commandType;

        /**
         * 命令ID
         */
        private String commandId;

        /**
         * 任务ID (OTA任务)
         */
        private String taskId;

        /**
         * 命令参数 (JSON)
         */
        private String params;

        /**
         * 优先级: 0-9 (9最高)
         */
        private Integer priority;

        /**
         * 过期时间戳
         */
        private Long expireAt;
    }
}
