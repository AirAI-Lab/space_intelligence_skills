package com.edge.cloud.service;

import com.edge.cloud.entity.Device;
import com.edge.cloud.entity.DeviceUpgradeStatus;
import com.edge.cloud.repository.DeviceRepository;
import com.edge.cloud.repository.DeviceUpgradeStatusRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 自动回滚服务
 * 监控设备升级后的健康状态，异常时自动回滚
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AutoRollbackService {

    private final OtaService otaService;
    private final DeviceUpgradeStatusRepository deviceUpgradeStatusRepository;
    private final DeviceRepository deviceRepository;
    private final WebSocketMessageService webSocketMessageService;

    // 存储设备升级前的状态（用于回滚）
    private final ConcurrentHashMap<String, DeviceRollbackInfo> rollbackInfoMap = new ConcurrentHashMap<>();

    /**
     * 设备回滚信息
     */
    public static class DeviceRollbackInfo {
        public String deviceId;
        public String taskId;
        public String previousModelId;
        public String previousModelVersion;
        public String previousFirmwareVersion;
        public LocalDateTime upgradeTime;
        public boolean rollbackRequested;
        public int consecutiveFailures; // 连续失败次数
    }

    /**
     * 记录设备升级前的状态
     */
    public void recordPreUpgradeState(String deviceId, String taskId) {
        Device device = deviceRepository.findById(deviceId).orElse(null);
        if (device == null) {
            log.warn("设备不存在，无法记录升级前状态: deviceId={}", deviceId);
            return;
        }

        DeviceRollbackInfo info = new DeviceRollbackInfo();
        info.deviceId = deviceId;
        info.taskId = taskId;
        info.previousModelId = device.getCurrentModelId();
        info.previousModelVersion = device.getCurrentVersion();
        info.previousFirmwareVersion = device.getCurrentFirmwareVersion();
        info.upgradeTime = LocalDateTime.now();
        info.rollbackRequested = false;
        info.consecutiveFailures = 0;

        rollbackInfoMap.put(deviceId, info);

        log.info("记录设备升级前状态: deviceId={}, modelId={}, version={}",
                deviceId, info.previousModelId, info.previousModelVersion);
    }

    /**
     * 设备升级完成后，启动健康检查
     */
    public void startHealthCheck(String deviceId, String taskId) {
        log.info("启动设备健康检查: deviceId={}, taskId={}", deviceId, taskId);
        // 健康检查通过定时任务执行
    }

    /**
     * 定时健康检查
     * 每分钟检查一次需要健康检查的设备
     */
    @Scheduled(fixedDelay = 60000)
    public void performHealthCheck() {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime threshold = now.minusMinutes(5); // 升级完成5分钟后开始检查

        for (String deviceId : rollbackInfoMap.keySet()) {
            DeviceRollbackInfo info = rollbackInfoMap.get(deviceId);

            // 只检查升级超过5分钟且未回滚的设备
            if (info.upgradeTime.isBefore(threshold) && !info.rollbackRequested) {
                checkDeviceHealth(deviceId, info, now);
            }
        }
    }

    /**
     * 检查设备健康状态
     */
    private void checkDeviceHealth(String deviceId, DeviceRollbackInfo info, LocalDateTime now) {
        Device device = deviceRepository.findById(deviceId).orElse(null);
        if (device == null) {
            return;
        }

        boolean healthy = true;
        String reason = null;

        // 检查1: 设备是否离线（超过10分钟无心跳）
        if (device.getLastHeartbeat() != null &&
            device.getLastHeartbeat().isBefore(now.minusMinutes(10))) {
            healthy = false;
            reason = "设备离线超过10分钟";
        } else if (device.getStatus() == Device.DeviceStatus.OFFLINE) {
            healthy = false;
            reason = "设备状态为离线";
        }

        // 检查2: 设备温度过高
        if (device.getTemperature() != null && device.getTemperature() > 85) {
            healthy = false;
            reason = String.format("温度过高: %.1f°C", device.getTemperature());
        }

        // 检查3: 推理FPS过低（如果设备正在运行推理）
        if (device.getInferenceFps() != null && device.getInferenceFps() < 5) {
            healthy = false;
            reason = String.format("推理FPS过低: %.1f", device.getInferenceFps());
        }

        // 检查4: GPU使用率异常
        if (device.getGpuUsage() != null) {
            if (device.getGpuUsage() > 98) {
                healthy = false;
                reason = String.format("GPU使用率过高: %.1f%%", device.getGpuUsage());
            } else if (device.getInferenceFps() != null && device.getInferenceFps() > 0
                    && device.getGpuUsage() < 10) {
                healthy = false;
                reason = String.format("GPU使用率异常低: %.1f%% (有推理任务)", device.getGpuUsage());
            }
        }

        // 检查5: 内存使用率过高
        if (device.getMemoryUsage() != null && device.getMemoryUsage() > 95) {
            healthy = false;
            reason = String.format("内存使用率过高: %.1f%%", device.getMemoryUsage());
        }

        // 检查6: 设备处于错误状态
        if (device.getStatus() == Device.DeviceStatus.ERROR) {
            healthy = false;
            reason = "设备状态为ERROR";
        }

        if (!healthy) {
            info.consecutiveFailures++;
            log.warn("设备健康检查失败 [{}/3]: deviceId={}, reason={}",
                    info.consecutiveFailures, deviceId, reason);

            // 连续3次失败才触发回滚
            if (info.consecutiveFailures >= 3) {
                triggerRollback(deviceId, reason);
            }
        } else {
            log.debug("设备健康检查通过: deviceId={}", deviceId);

            // 重置失败计数
            info.consecutiveFailures = 0;

            // 如果升级超过1小时且健康，清理回滚信息
            if (info.upgradeTime.plusHours(1).isBefore(now)) {
                rollbackInfoMap.remove(deviceId);
                log.info("设备健康稳定，清理回滚信息: deviceId={}", deviceId);
            }
        }
    }

    /**
     * 触发回滚
     */
    public void triggerRollback(String deviceId, String reason) {
        DeviceRollbackInfo info = rollbackInfoMap.get(deviceId);
        if (info == null) {
            log.warn("无回滚信息，无法回滚: deviceId={}", deviceId);
            return;
        }

        if (info.rollbackRequested) {
            log.info("回滚已请求，跳过: deviceId={}", deviceId);
            return;
        }

        info.rollbackRequested = true;

        log.warn("触发设备回滚: deviceId={}, reason={}, previousModel={}",
                deviceId, reason, info.previousModelId);

        try {
            // 如果有之前的模型，发送回滚命令
            if (info.previousModelId != null) {
                otaService.sendRollbackCommand(deviceId, info.taskId, info.previousModelId);
            } else {
                // 没有之前模型，只更新状态
                handleRollbackComplete(deviceId, info.taskId, true);
            }

            // 通知前端
            webSocketMessageService.sendOtaTaskProgress(info.taskId, Map.of(
                    "device_id", deviceId,
                    "action", "rollback",
                    "reason", reason,
                    "previous_model_id", info.previousModelId != null ? info.previousModelId : "无",
                    "timestamp", System.currentTimeMillis()
            ));
        } catch (Exception e) {
            log.error("触发回滚失败: deviceId={}", deviceId, e);
            info.rollbackRequested = false; // 允许重试
        }
    }

    /**
     * 手动触发回滚
     */
    @Transactional
    public void manualRollback(String deviceId) {
        DeviceRollbackInfo info = rollbackInfoMap.get(deviceId);
        String reason = "手动触发回滚";

        if (info != null) {
            triggerRollback(deviceId, reason);
        } else {
            // 尝试从数据库获取最近的升级记录
            List<DeviceUpgradeStatus> recentStatuses =
                    deviceUpgradeStatusRepository.findRecentByDeviceId(deviceId);

            if (!recentStatuses.isEmpty()) {
                DeviceUpgradeStatus lastStatus = recentStatuses.get(0);
                log.info("从数据库获取最近升级记录进行回滚: taskId={}", lastStatus.getTaskId());

                // 创建临时回滚信息
                info = new DeviceRollbackInfo();
                info.deviceId = deviceId;
                info.taskId = lastStatus.getTaskId();
                info.upgradeTime = lastStatus.getCreatedAt();
                info.rollbackRequested = false;

                rollbackInfoMap.put(deviceId, info);
                triggerRollback(deviceId, reason);
            } else {
                log.warn("找不到可回滚的升级记录: deviceId={}", deviceId);
            }
        }
    }

    /**
     * 处理回滚完成
     */
    @Transactional
    public void handleRollbackComplete(String deviceId, String taskId, boolean success) {
        DeviceRollbackInfo info = rollbackInfoMap.get(deviceId);
        if (info == null) {
            log.warn("无回滚信息，taskId可能不匹配: deviceId={}, taskId={}", deviceId, taskId);
            return;
        }

        if (success) {
            log.info("回滚成功: deviceId={}", deviceId);

            // 更新设备状态
            Device device = deviceRepository.findById(deviceId).orElse(null);
            if (device != null && info.previousModelId != null) {
                device.setCurrentModelId(info.previousModelId);
                device.setCurrentVersion(info.previousModelVersion);
                device.setCurrentFirmwareVersion(info.previousFirmwareVersion);
                device.setStatus(Device.DeviceStatus.ONLINE);
                deviceRepository.save(device);
            }

            // 更新升级状态
            deviceUpgradeStatusRepository.findByTaskIdAndDeviceId(taskId, deviceId).ifPresent(status -> {
                status.setStatus(DeviceUpgradeStatus.UpgradeStatus.ROLLED_BACK);
                deviceUpgradeStatusRepository.save(status);
            });

            // 清理回滚信息
            rollbackInfoMap.remove(deviceId);

            // 通知前端
            webSocketMessageService.sendOtaTaskComplete(taskId, false, "已自动回滚");
        } else {
            log.error("回滚失败: deviceId={}", deviceId);
            info.rollbackRequested = false; // 允许重试
            info.consecutiveFailures = 0;   // 重置失败计数

            // 通知前端回滚失败
            webSocketMessageService.sendOtaTaskProgress(taskId, Map.of(
                    "device_id", deviceId,
                    "action", "rollback_failed",
                    "message", "回滚失败，需要人工干预",
                    "timestamp", System.currentTimeMillis()
            ));
        }
    }

    /**
     * 获取回滚信息
     */
    public DeviceRollbackInfo getRollbackInfo(String deviceId) {
        return rollbackInfoMap.get(deviceId);
    }

    /**
     * 检查设备是否可以回滚
     */
    public boolean canRollback(String deviceId) {
        DeviceRollbackInfo info = rollbackInfoMap.get(deviceId);
        return info != null && info.previousModelId != null && !info.rollbackRequested;
    }

    /**
     * 清理过期的回滚信息（超过24小时）
     */
    @Scheduled(fixedDelay = 3600000) // 每小时执行一次
    public void cleanupExpiredRollbackInfo() {
        LocalDateTime threshold = LocalDateTime.now().minusHours(24);
        rollbackInfoMap.entrySet().removeIf(entry -> {
            boolean shouldRemove = entry.getValue().upgradeTime.isBefore(threshold);
            if (shouldRemove) {
                log.info("清理过期回滚信息: deviceId={}", entry.getKey());
            }
            return shouldRemove;
        });
    }
}
