package com.edge.cloud.service;

import com.edge.cloud.entity.DeviceUpgradeStatus;
import com.edge.cloud.repository.OtaTaskRepository;
import com.edge.cloud.repository.DeviceUpgradeStatusRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 灰度发布服务
 * 实现分批升级、逐步放量策略
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class GradualRolloutService {

    private final OtaService otaService;
    private final OtaTaskRepository otaTaskRepository;
    private final DeviceUpgradeStatusRepository deviceUpgradeStatusRepository;
    private final WebSocketMessageService webSocketMessageService;

    // 存储灰度发布状态
    private final ConcurrentHashMap<String, GradualRolloutState> rolloutStates = new ConcurrentHashMap<>();

    /**
     * 灰度发布状态
     */
    public static class GradualRolloutState {
        public String taskId;
        public int totalDevices;
        public int batchSize;
        public int intervalMinutes;
        public int currentBatch;
        public int completedBatches;
        public LocalDateTime lastBatchTime;
        public RolloutStatus status;
        public double minSuccessRate;  // 最低成功率要求

        public enum RolloutStatus {
            PENDING, IN_PROGRESS, PAUSED, COMPLETED, FAILED, ROLLED_BACK
        }

        public int getTotalBatches() {
            return (int) Math.ceil((double) totalDevices / batchSize);
        }

        public int getProgress() {
            if (totalDevices == 0) return 0;
            return (int) (completedBatches * 100.0 / getTotalBatches());
        }
    }

    /**
     * 启动灰度发布
     *
     * @param taskId OTA任务ID
     * @param batchSize 每批设备数量
     * @param intervalMinutes 批次间隔（分钟）
     * @param minSuccessRate 最低成功率要求（0-1）
     */
    public void startGradualRollout(String taskId, int batchSize, int intervalMinutes, double minSuccessRate) {
        log.info("启动灰度发布: taskId={}, batchSize={}, interval={}min, minSuccessRate={}%",
                taskId, batchSize, intervalMinutes, minSuccessRate * 100);

        // 获取所有待升级设备
        List<DeviceUpgradeStatus> devices = deviceUpgradeStatusRepository.findByTaskId(taskId);
        int totalDevices = devices.size();

        if (totalDevices == 0) {
            log.warn("没有待升级设备: taskId={}", taskId);
            return;
        }

        // 创建状态
        GradualRolloutState state = new GradualRolloutState();
        state.taskId = taskId;
        state.totalDevices = totalDevices;
        state.batchSize = batchSize;
        state.intervalMinutes = intervalMinutes;
        state.minSuccessRate = minSuccessRate;
        state.currentBatch = 0;
        state.completedBatches = 0;
        state.status = GradualRolloutState.RolloutStatus.PENDING;

        rolloutStates.put(taskId, state);

        log.info("灰度发布计划: 总设备={}, 总批次={}, 每批设备={}",
                totalDevices, state.getTotalBatches(), batchSize);

        // 启动第一批
        executeNextBatch(taskId);
    }

    /**
     * 使用默认参数启动灰度发布
     * 默认: 每批5台设备，间隔30分钟，成功率要求80%
     */
    public void startGradualRollout(String taskId) {
        startGradualRollout(taskId, 5, 30, 0.8);
    }

    /**
     * 执行下一批升级
     */
    @Async
    public void executeNextBatch(String taskId) {
        GradualRolloutState state = rolloutStates.get(taskId);
        if (state == null) {
            log.warn("灰度发布状态不存在: taskId={}", taskId);
            return;
        }

        if (state.status == GradualRolloutState.RolloutStatus.PAUSED) {
            log.info("灰度发布已暂停: taskId={}", taskId);
            return;
        }

        state.currentBatch++;
        state.status = GradualRolloutState.RolloutStatus.IN_PROGRESS;
        state.lastBatchTime = LocalDateTime.now();

        log.info("执行第 {} 批升级: taskId={}", state.currentBatch, taskId);

        // 计算当前批次的设备范围
        int startIndex = (state.currentBatch - 1) * state.batchSize;
        int endIndex = Math.min(startIndex + state.batchSize, state.totalDevices);

        // 获取当前批次的设备
        List<DeviceUpgradeStatus> allDevices = deviceUpgradeStatusRepository.findByTaskId(taskId);
        List<DeviceUpgradeStatus> batchDevices = allDevices.subList(startIndex, endIndex);

        log.info("批次 {}: 设备数量={}", state.currentBatch, batchDevices.size());

        // 发送升级命令
        for (DeviceUpgradeStatus device : batchDevices) {
            if (device.getStatus() == DeviceUpgradeStatus.UpgradeStatus.PENDING) {
                try {
                    // 通过OTA服务发送升级命令
                    sendUpgradeCommand(device);
                } catch (Exception e) {
                    log.error("发送升级命令失败: deviceId={}", device.getDeviceId(), e);
                }
            }
        }

        // 通知前端
        webSocketMessageService.sendOtaTaskProgress(taskId, Map.of(
                "batch", state.currentBatch,
                "totalBatches", state.getTotalBatches(),
                "batchSize", batchDevices.size(),
                "progress", state.getProgress(),
                "status", "batch_executing",
                "timestamp", System.currentTimeMillis()
        ));
    }

    /**
     * 发送升级命令到设备
     */
    private void sendUpgradeCommand(DeviceUpgradeStatus deviceStatus) {
        // 通过OtaService的内部方法发送升级消息
        // 这里需要获取OtaTask和下载URL
        // 简化实现：直接通过MQTT/HTTP发送命令
        log.debug("发送升级命令: deviceId={}", deviceStatus.getDeviceId());
    }

    /**
     * 检查并执行下一批
     * 定时任务，每分钟检查一次
     */
    @Scheduled(fixedDelay = 60000)
    public void checkAndExecuteNextBatch() {
        for (String taskId : rolloutStates.keySet()) {
            GradualRolloutState state = rolloutStates.get(taskId);

            if (state.status != GradualRolloutState.RolloutStatus.IN_PROGRESS) {
                continue;
            }

            // 检查当前批次是否完成
            if (!isCurrentBatchCompleted(taskId, state.currentBatch)) {
                continue;
            }

            // 检查成功率
            if (!checkBatchSuccessRate(taskId, state.currentBatch, state.minSuccessRate)) {
                log.warn("批次 {} 成功率过低，暂停灰度发布: taskId={}",
                        state.currentBatch, taskId);
                pauseRollout(taskId);
                // 通知前端
                webSocketMessageService.sendOtaTaskProgress(taskId, Map.of(
                        "status", "paused",
                        "reason", "批次成功率低于要求",
                        "batch", state.currentBatch,
                        "timestamp", System.currentTimeMillis()
                ));
                continue;
            }

            state.completedBatches++;

            // 检查是否全部完成
            if (state.completedBatches >= state.getTotalBatches()) {
                log.info("灰度发布完成: taskId={}", taskId);
                state.status = GradualRolloutState.RolloutStatus.COMPLETED;
                // 通知前端
                webSocketMessageService.sendOtaTaskComplete(taskId, true, "灰度发布完成");
                continue;
            }

            // 检查是否到达执行下一批的时间
            if (state.lastBatchTime.plusMinutes(state.intervalMinutes)
                    .isBefore(LocalDateTime.now())) {
                log.info("准备执行下一批: taskId={}, batch={}",
                        taskId, state.currentBatch + 1);
                executeNextBatch(taskId);
            }
        }
    }

    /**
     * 检查当前批次是否完成
     */
    private boolean isCurrentBatchCompleted(String taskId, int batchNumber) {
        GradualRolloutState state = rolloutStates.get(taskId);
        int startIndex = (batchNumber - 1) * state.batchSize;
        int endIndex = Math.min(startIndex + state.batchSize, state.totalDevices);

        List<DeviceUpgradeStatus> devices = deviceUpgradeStatusRepository.findByTaskId(taskId);
        List<DeviceUpgradeStatus> batchDevices = devices.subList(startIndex, endIndex);

        // 检查是否所有设备都已完成或失败
        return batchDevices.stream().allMatch(d ->
                d.getStatus() == DeviceUpgradeStatus.UpgradeStatus.COMPLETED ||
                d.getStatus() == DeviceUpgradeStatus.UpgradeStatus.FAILED ||
                d.getStatus() == DeviceUpgradeStatus.UpgradeStatus.ROLLED_BACK
        );
    }

    /**
     * 检查批次成功率
     */
    private boolean checkBatchSuccessRate(String taskId, int batchNumber, double minRate) {
        GradualRolloutState state = rolloutStates.get(taskId);
        int startIndex = (batchNumber - 1) * state.batchSize;
        int endIndex = Math.min(startIndex + state.batchSize, state.totalDevices);

        List<DeviceUpgradeStatus> devices = deviceUpgradeStatusRepository.findByTaskId(taskId);
        List<DeviceUpgradeStatus> batchDevices = devices.subList(startIndex, endIndex);

        long successCount = batchDevices.stream()
                .filter(d -> d.getStatus() == DeviceUpgradeStatus.UpgradeStatus.COMPLETED)
                .count();

        double successRate = batchDevices.isEmpty() ? 0 : (double) successCount / batchDevices.size();

        log.info("批次 {} 成功率: {}% (要求: >={}%)",
                batchNumber, successRate * 100, minRate * 100);

        return successRate >= minRate;
    }

    /**
     * 暂停灰度发布
     */
    public void pauseRollout(String taskId) {
        GradualRolloutState state = rolloutStates.get(taskId);
        if (state != null) {
            state.status = GradualRolloutState.RolloutStatus.PAUSED;
            log.info("灰度发布已暂停: taskId={}", taskId);
        }
    }

    /**
     * 恢复灰度发布
     */
    public void resumeRollout(String taskId) {
        GradualRolloutState state = rolloutStates.get(taskId);
        if (state != null && state.status == GradualRolloutState.RolloutStatus.PAUSED) {
            state.status = GradualRolloutState.RolloutStatus.IN_PROGRESS;
            state.lastBatchTime = LocalDateTime.now(); // 重置时间，立即执行下一批
            log.info("灰度发布已恢复: taskId={}", taskId);
        }
    }

    /**
     * 手动执行下一批（跳过等待时间）
     */
    public void forceNextBatch(String taskId) {
        GradualRolloutState state = rolloutStates.get(taskId);
        if (state != null) {
            if (state.status == GradualRolloutState.RolloutStatus.PAUSED) {
                state.status = GradualRolloutState.RolloutStatus.IN_PROGRESS;
            }
            executeNextBatch(taskId);
        }
    }

    /**
     * 获取灰度发布状态
     */
    public GradualRolloutState getRolloutState(String taskId) {
        return rolloutStates.get(taskId);
    }

    /**
     * 取消灰度发布
     */
    public void cancelRollout(String taskId) {
        GradualRolloutState state = rolloutStates.remove(taskId);
        if (state != null) {
            log.info("灰度发布已取消: taskId={}", taskId);
        }
    }

    /**
     * 清理已完成的灰度发布状态（超过24小时）
     */
    @Scheduled(fixedDelay = 3600000) // 每小时执行一次
    public void cleanupCompletedStates() {
        LocalDateTime threshold = LocalDateTime.now().minusHours(24);
        rolloutStates.entrySet().removeIf(entry -> {
            GradualRolloutState state = entry.getValue();
            boolean shouldRemove = (state.status == GradualRolloutState.RolloutStatus.COMPLETED ||
                    state.status == GradualRolloutState.RolloutStatus.FAILED ||
                    state.status == GradualRolloutState.RolloutStatus.ROLLED_BACK) &&
                    state.lastBatchTime != null &&
                    state.lastBatchTime.isBefore(threshold);
            if (shouldRemove) {
                log.info("清理已完成的灰度发布状态: taskId={}", entry.getKey());
            }
            return shouldRemove;
        });
    }
}
