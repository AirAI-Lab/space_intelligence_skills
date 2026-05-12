package com.edge.cloud.service;

import com.edge.cloud.dto.*;
import com.edge.cloud.entity.Device;
import com.edge.cloud.entity.DeviceType;
import com.edge.cloud.entity.DeviceCapability;
import com.edge.cloud.repository.DeviceCommandRepository;
import com.edge.cloud.repository.DeviceRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 设备通信服务 (RESTful方式)
 * 替代MQTT，使用HTTP+WebSocket实现云边通信
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DeviceCommunicationService {

    private final DeviceRepository deviceRepository;
    private final DeviceCommandRepository deviceCommandRepository;
    private final OtaService otaService;
    private final InferenceResultService inferenceResultService;

    // 待下发给设备的命令缓存 (deviceId -> List<Command>)
    private final Map<String, Queue<PendingCommand>> pendingCommands = new ConcurrentHashMap<>();

    /**
     * 处理设备心跳
     */
    @Transactional
    public DeviceHeartbeatResponse processHeartbeat(DeviceHeartbeatRequest request) {
        // 查找或创建设备
        Device device = deviceRepository.findById(request.getDeviceId())
                .orElseGet(() -> createDeviceFromRequest(request));

        // 更新设备状态
        updateDeviceStatus(device, request);
        deviceRepository.save(device);

        // 构建响应
        return DeviceHeartbeatResponse.builder()
                .status("SUCCESS")
                .message("Heartbeat received")
                .serverTime(System.currentTimeMillis())
                .commands(getPendingCommandsForDevice(device.getDeviceId()))
                .build();
    }

    /**
     * 注册新设备
     */
    @Transactional
    public Map<String, Object> registerDevice(DeviceHeartbeatRequest request) {
        // 检查设备是否已存在
        if (deviceRepository.existsById(request.getDeviceId())) {
            // 已存在则更新
            return processHeartbeat(request).toMap();
        }

        // 创建新设备
        Device device = createDeviceFromRequest(request);
        device.setStatus(Device.DeviceStatus.ONLINE);
        deviceRepository.save(device);

        log.info("新设备注册成功: deviceId={}, deviceName={}, deviceType={}",
                device.getDeviceId(), device.getDeviceName(), device.getDeviceType());

        Map<String, Object> result = new HashMap<>();
        result.put("status", "SUCCESS");
        result.put("message", "Device registered successfully");
        result.put("device_id", device.getDeviceId());
        result.put("registered_at", LocalDateTime.now().toString());
        return result;
    }

    /**
     * 处理OTA状态上报
     */
    @Transactional
    public Map<String, Object> processOtaStatus(OtaStatusReportRequest request) {
        try {
            // 根据状态调用不同的处理方法
            switch (request.getStatus()) {
                case "DOWNLOADING":
                case "VERIFYING":
                case "APPLYING":
                    // 更新进度
                    otaService.handleDeviceUpgradeProgress(
                            request.getTaskId(),
                            request.getDeviceId(),
                            request.getProgress()
                    );
                    break;

                case "COMPLETED":
                    // 处理完成
                    otaService.handleDeviceUpgradeComplete(
                            request.getTaskId(),
                            request.getDeviceId()
                    );
                    break;

                case "FAILED":
                    // 处理失败
                    otaService.handleDeviceUpgradeFailed(
                            request.getTaskId(),
                            request.getDeviceId(),
                            request.getError() != null ? request.getError() : "Unknown error"
                    );
                    break;
            }

            return Map.of(
                    "status", "SUCCESS",
                    "message", "OTA status received"
            );

        } catch (Exception e) {
            log.error("处理OTA状态失败: taskId={}, error={}", request.getTaskId(), e.getMessage(), e);
            return Map.of(
                    "status", "ERROR",
                    "message", e.getMessage()
            );
        }
    }

    /**
     * 处理推理结果上报
     */
    public Map<String, Object> processInferenceResult(InferenceResultRequest request) {
        try {
            inferenceResultService.saveEdgeResult(request);
            log.debug("推理结果已持久化: deviceId={}, modelId={}, detections={}",
                    request.getDeviceId(),
                    request.getModelId(),
                    request.getDetections().size());
        } catch (Exception e) {
            log.error("推理结果持久化失败: deviceId={}", request.getDeviceId(), e);
        }

        return Map.of(
                "status", "SUCCESS",
                "message", "Inference result received"
        );
    }

    /**
     * 获取待执行的命令
     */
    public Map<String, Object> getPendingCommands(String deviceId, String lastCommandId) {
        Queue<PendingCommand> commands = pendingCommands.get(deviceId);

        if (commands == null || commands.isEmpty()) {
            return Map.of(
                    "status", "SUCCESS",
                    "commands", List.of(),
                    "has_more", false
            );
        }

        List<DeviceHeartbeatResponse.DeviceCommand> commandList = new ArrayList<>();
        PendingCommand cmd;
        while ((cmd = commands.poll()) != null && commandList.size() < 10) {
            // 限制每次返回最多10个命令
            commandList.add(cmd.toCommand());
        }

        return Map.of(
                "status", "SUCCESS",
                "commands", commandList,
                "has_more", !commands.isEmpty()
        );
    }

    /**
     * 添加待下发的命令
     */
    public void addCommand(String deviceId, String commandType, String taskId, Map<String, Object> params) {
        PendingCommand command = new PendingCommand(
                UUID.randomUUID().toString(),
                commandType,
                taskId,
                params,
                System.currentTimeMillis() + 3600000 // 1小时后过期
        );

        pendingCommands.computeIfAbsent(deviceId, k -> new LinkedList<>()).offer(command);
        log.info("命令已添加到队列: deviceId={}, commandType={}, taskId={}", deviceId, commandType, taskId);
    }

    /**
     * 确认命令已接收
     */
    public void acknowledgeCommand(String deviceId, String commandId) {
        log.info("命令已确认: deviceId={}, commandId={}", deviceId, commandId);
        // 命令已在poll时移除，这里只需记录日志
    }

    /**
     * 获取模型下载信息
     */
    public Map<String, Object> getModelDownloadInfo(String modelId) {
        // 从存储服务获取模型下载URL
        String downloadUrl = "/api/v1/models/" + modelId + "/file";

        return Map.of(
                "model_id", modelId,
                "download_url", downloadUrl,
                "expires_at", System.currentTimeMillis() + 3600000
        );
    }

    /**
     * 从心跳请求创建设备实体
     */
    private Device createDeviceFromRequest(DeviceHeartbeatRequest request) {
        Device device = new Device();
        device.setDeviceId(request.getDeviceId());
        device.setDeviceName(request.getDeviceName());
        device.setDeviceType(request.getDeviceType());
        device.setIp(request.getIp());
        device.setMac(request.getMac());
        device.setStatus(Device.DeviceStatus.ONLINE);
        device.setLastHeartbeat(LocalDateTime.now());
        device.setCpuUsage(request.getCpuUsage());
        device.setGpuUsage(request.getGpuUsage());
        device.setMemoryUsage(request.getMemoryUsage());
        device.setDiskUsage(request.getDiskUsage());
        device.setCurrentModelId(request.getCurrentModelId());
        device.setCurrentVersion(request.getCurrentModelVersion());

        // 设置扩展字段: 类别、能力、协议 (旧设备自动推断默认值)
        String dtype = request.getDeviceType();
        device.setDeviceCategory(DeviceType.inferCategory(dtype));
        device.setCapabilities(DeviceCapability.defaultForEdge());
        device.setProtocol("MQTT_REST");

        return device;
    }

    /**
     * 更新设备状态
     */
    private void updateDeviceStatus(Device device, DeviceHeartbeatRequest request) {
        device.setStatus(Device.DeviceStatus.ONLINE);
        device.setLastHeartbeat(LocalDateTime.now());
        device.setCpuUsage(request.getCpuUsage());
        device.setGpuUsage(request.getGpuUsage());
        device.setMemoryUsage(request.getMemoryUsage());
        device.setDiskUsage(request.getDiskUsage());
        device.setTemperature(request.getTemperature());

        // 心跳中携带的静态信息也更新（边缘端可能动态变化）
        if (request.getDeviceName() != null) device.setDeviceName(request.getDeviceName());
        if (request.getDeviceType() != null) device.setDeviceType(request.getDeviceType());
        if (request.getIp() != null) device.setIp(request.getIp());
        if (request.getGpuModel() != null) device.setGpuModel(request.getGpuModel());
        if (request.getOsVersion() != null) device.setOsVersion(request.getOsVersion());
        if (request.getCurrentModelId() != null) device.setCurrentModelId(request.getCurrentModelId());
        if (request.getCurrentModelVersion() != null) device.setCurrentVersion(request.getCurrentModelVersion());
        if (request.getInferenceFps() != null) device.setInferenceFps(request.getInferenceFps());

        // 推断默认值（旧设备可能为空）
        if (device.getDeviceCategory() == null) {
            device.setDeviceCategory(DeviceType.inferCategory(device.getDeviceType()));
        }
        if (device.getCapabilities() == null || device.getCapabilities().isEmpty()) {
            device.setCapabilities(DeviceCapability.defaultForEdge());
        }
        if (device.getProtocol() == null || device.getProtocol().isEmpty()) {
            device.setProtocol("MQTT_REST");
        }
    }

    /**
     * 获取待下发给设备的命令列表
     */
    private List<DeviceHeartbeatResponse.DeviceCommand> getPendingCommandsForDevice(String deviceId) {
        Queue<PendingCommand> commands = pendingCommands.get(deviceId);
        if (commands == null || commands.isEmpty()) {
            return List.of();
        }

        List<DeviceHeartbeatResponse.DeviceCommand> result = new ArrayList<>();
        Iterator<PendingCommand> iter = commands.iterator();
        while (iter.hasNext() && result.size() < 5) {
            PendingCommand cmd = iter.next();
            // 移除过期命令
            if (cmd.expireAt < System.currentTimeMillis()) {
                iter.remove();
                continue;
            }
            result.add(cmd.toCommand());
            iter.remove();
        }
        return result;
    }

    /**
     * 定期检查并更新设备在线状态
     * 每1分钟执行一次，将超过5分钟未心跳的在线设备标记为离线
     */
    @Scheduled(fixedDelay = 60000) // 每1分钟执行一次
    @Transactional
    public void checkAndUpdateDeviceStatus() {
        try {
            // 查找超时的在线设备（最后心跳时间超过5分钟）
            List<Device> offlineDevices = deviceRepository.findOfflineDevices();

            if (!offlineDevices.isEmpty()) {
                log.info("发现 {} 个设备长时间未心跳，标记为离线", offlineDevices.size());

                for (Device device : offlineDevices) {
                    log.debug("设备 {} 最后心跳时间: {}，标记为离线",
                            device.getDeviceId(), device.getLastHeartbeat());
                    device.setStatus(Device.DeviceStatus.OFFLINE);
                    deviceRepository.save(device);
                }
            }
        } catch (Exception e) {
            log.error("检查设备在线状态失败", e);
        }
    }

    /**
     * 定期清理过期命令
     */
    @Scheduled(fixedDelay = 300000) // 每5分钟执行一次
    public void cleanExpiredCommands() {
        long now = System.currentTimeMillis();
        pendingCommands.forEach((deviceId, commands) -> {
            commands.removeIf(cmd -> cmd.expireAt < now);
        });
    }

    /**
     * 待下发的命令
     */
    private static class PendingCommand {
        final String commandId;
        final String commandType;
        final String taskId;
        final Map<String, Object> params;
        final long expireAt;

        PendingCommand(String commandId, String commandType, String taskId,
                      Map<String, Object> params, long expireAt) {
            this.commandId = commandId;
            this.commandType = commandType;
            this.taskId = taskId;
            this.params = params;
            this.expireAt = expireAt;
        }

        DeviceHeartbeatResponse.DeviceCommand toCommand() {
            return DeviceHeartbeatResponse.DeviceCommand.builder()
                    .commandId(commandId)
                    .commandType(commandType)
                    .taskId(taskId)
                    .params(params != null ? params.toString() : "{}")
                    .priority(5)
                    .expireAt(expireAt)
                    .build();
        }
    }
}
