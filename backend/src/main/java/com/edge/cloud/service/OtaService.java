package com.edge.cloud.service;

import com.edge.cloud.dto.DeviceUpgradeStatusDTO;
import com.edge.cloud.dto.OtaTaskCreateRequest;
import com.edge.cloud.dto.OtaTaskDTO;
import com.edge.cloud.entity.*;
import com.edge.cloud.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

/**
 * OTA 升级管理服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OtaService {

    private final OtaTaskRepository otaTaskRepository;
    private final DeviceUpgradeStatusRepository deviceUpgradeStatusRepository;
    private final DeviceRepository deviceRepository;
    private final ModelRepository modelRepository;

    // 使用 setter 注入打破循环依赖
    private MqttService mqttService;

    public void setMqttService(MqttService mqttService) {
        this.mqttService = mqttService;
    }

    @Value("${S3_ENDPOINT:http://localhost:8333}")
    private String s3Endpoint;

    /**
     * 创建 OTA 升级任务
     */
    @Transactional
    public OtaTaskDTO createOtaTask(OtaTaskCreateRequest request) {
        log.info("创建 OTA 升级任务: {}", request.getTaskName());

        // 验证模型存在
        if (request.getUpgradeType() == OtaTask.UpgradeType.MODEL && request.getModelId() != null) {
            Model model = modelRepository.findById(request.getModelId())
                    .orElseThrow(() -> new RuntimeException("模型不存在: " + request.getModelId()));

            if (model.getEngineFilePath() == null) {
                throw new RuntimeException("模型未转换，请先转换为 .engine 格式");
            }
        }

        // 获取目标设备列表
        List<String> deviceIds = request.getDeviceIds();
        if (deviceIds == null || deviceIds.isEmpty()) {
            if (request.getGroupId() != null) {
                deviceIds = deviceRepository.findByGroupId(request.getGroupId())
                        .stream()
                        .map(Device::getDeviceId)
                        .collect(Collectors.toList());
            } else {
                throw new RuntimeException("请指定目标设备或设备组");
            }
        }

        // 生成任务ID
        String taskId = generateTaskId();

        // 创建 OTA 任务实体
        OtaTask task = new OtaTask();
        task.setTaskId(taskId);
        task.setTaskName(request.getTaskName());
        task.setUpgradeType(request.getUpgradeType());
        task.setModelId(request.getModelId());
        task.setTargetVersion(request.getTargetVersion());
        task.setStrategy(request.getStrategy() != null ? request.getStrategy() : OtaTask.UpgradeStrategy.IMMEDIATE);
        task.setScheduledTime(request.getScheduledTime());
        task.setStatus(OtaTask.OtaStatus.PENDING);
        task.setTotalDevices(deviceIds.size());

        task = otaTaskRepository.save(task);

        // 创建设备升级状态记录
        for (String deviceId : deviceIds) {
            DeviceUpgradeStatus status = new DeviceUpgradeStatus();
            status.setStatusId(generateStatusId());
            status.setTaskId(taskId);
            status.setDeviceId(deviceId);
            status.setStatus(DeviceUpgradeStatus.UpgradeStatus.PENDING);
            deviceUpgradeStatusRepository.save(status);
        }

        log.info("OTA 升级任务创建成功: taskId={}, deviceCount={}", taskId, deviceIds.size());

        // 如果是立即升级，直接启动
        if (task.getStrategy() == OtaTask.UpgradeStrategy.IMMEDIATE) {
            startOtaTask(taskId);
        } else if (task.getStrategy() == OtaTask.UpgradeStrategy.SCHEDULED) {
            task.setStatus(OtaTask.OtaStatus.SCHEDULED);
            otaTaskRepository.save(task);
        }

        return toDTO(task);
    }

    /**
     * 启动 OTA 升级任务
     */
    @Transactional
    public OtaTaskDTO startOtaTask(String taskId) {
        OtaTask task = otaTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("OTA 任务不存在: " + taskId));

        if (task.getStatus() != OtaTask.OtaStatus.PENDING
                && task.getStatus() != OtaTask.OtaStatus.SCHEDULED) {
            throw new RuntimeException("任务状态不允许启动: " + task.getStatus());
        }

        try {
            task.setStatus(OtaTask.OtaStatus.RUNNING);
            otaTaskRepository.save(task);

            // 获取模型下载地址
            String downloadUrl = null;
            if (task.getModelId() != null) {
                Model model = modelRepository.findById(task.getModelId())
                        .orElseThrow(() -> new RuntimeException("模型不存在: " + task.getModelId()));
                downloadUrl = s3Endpoint + "/" + model.getEngineFilePath();
            }

            // 向所有设备发送升级消息
            List<DeviceUpgradeStatus> statusList = deviceUpgradeStatusRepository.findByTaskId(taskId);
            for (DeviceUpgradeStatus status : statusList) {
                sendOtaMessageToDevice(status.getDeviceId(), task, downloadUrl);
            }

            log.info("OTA 升级任务已启动: taskId={}", taskId);
            return toDTO(task);

        } catch (Exception e) {
            log.error("启动 OTA 任务失败: taskId={}", taskId, e);
            task.setStatus(OtaTask.OtaStatus.FAILED);
            otaTaskRepository.save(task);
            throw new RuntimeException("启动 OTA 任务失败: " + e.getMessage());
        }
    }

    /**
     * 向设备发送 OTA 升级消息
     */
    private void sendOtaMessageToDevice(String deviceId, OtaTask task, String downloadUrl) {
        try {
            // 更新设备状态
            DeviceUpgradeStatus status = deviceUpgradeStatusRepository.findByTaskIdAndDeviceId(task.getTaskId(), deviceId)
                    .orElseThrow(() -> new RuntimeException("设备升级状态不存在"));

            status.setStatus(DeviceUpgradeStatus.UpgradeStatus.DOWNLOADING);
            status.setDownloadStartTime(LocalDateTime.now());
            deviceUpgradeStatusRepository.save(status);

            // 更新设备状态
            Device device = deviceRepository.findById(deviceId).orElse(null);
            if (device != null) {
                device.setStatus(Device.DeviceStatus.UPGRADING);
                deviceRepository.save(device);
            }

            // 准备 MQTT 消息
            Map<String, Object> message = new HashMap<>();
            message.put("task_id", task.getTaskId());
            message.put("upgrade_type", task.getUpgradeType().name());
            message.put("target_version", task.getTargetVersion());
            message.put("download_url", downloadUrl);
            message.put("model_id", task.getModelId());

            // 发送 MQTT 消息
            String topic = "device/" + deviceId + "/ota/update";
            mqttService.publish(topic, message);

            log.info("OTA 升级消息已发送: deviceId={}, topic={}", deviceId, topic);

        } catch (Exception e) {
            log.error("发送 OTA 消息失败: deviceId={}", deviceId, e);
            failDeviceUpgrade(task.getTaskId(), deviceId, e.getMessage());
        }
    }

    /**
     * 处理设备升级进度更新（MQTT 回调）
     */
    @Transactional
    public void handleDeviceUpgradeProgress(String taskId, String deviceId, int progress) {
        DeviceUpgradeStatus status = deviceUpgradeStatusRepository.findByTaskIdAndDeviceId(taskId, deviceId)
                .orElseThrow(() -> new RuntimeException("设备升级状态不存在"));

        status.setProgress(progress);
        deviceUpgradeStatusRepository.save(status);

        log.debug("设备升级进度更新: taskId={}, deviceId={}, progress={}%",
                taskId, deviceId, progress);
    }

    /**
     * 处理设备升级完成（MQTT 回调）
     */
    @Transactional
    public void handleDeviceUpgradeComplete(String taskId, String deviceId) {
        DeviceUpgradeStatus status = deviceUpgradeStatusRepository.findByTaskIdAndDeviceId(taskId, deviceId)
                .orElseThrow(() -> new RuntimeException("设备升级状态不存在"));

        status.setStatus(DeviceUpgradeStatus.UpgradeStatus.COMPLETED);
        status.setProgress(100);
        status.setInstallCompleteTime(LocalDateTime.now());
        deviceUpgradeStatusRepository.save(status);

        // 更新设备状态
        Device device = deviceRepository.findById(deviceId).orElse(null);
        if (device != null) {
            device.setStatus(Device.DeviceStatus.ONLINE);
            device.setCurrentVersion(status.getTask().getTargetVersion());
            if (status.getTask().getModelId() != null) {
                device.setCurrentModelId(status.getTask().getModelId());
            }
            deviceRepository.save(device);
        }

        // 更新任务计数
        OtaTask task = otaTaskRepository.findById(taskId).orElse(null);
        if (task != null) {
            task.setCompletedDevices(task.getCompletedDevices() + 1);
            if (task.getCompletedDevices() + task.getFailedDevices() >= task.getTotalDevices()) {
                task.setStatus(OtaTask.OtaStatus.COMPLETED);
            }
            otaTaskRepository.save(task);
        }

        log.info("设备升级完成: taskId={}, deviceId={}", taskId, deviceId);
    }

    /**
     * 处理设备升级失败（MQTT 回调）
     */
    @Transactional
    public void handleDeviceUpgradeFailed(String taskId, String deviceId, String errorMessage) {
        failDeviceUpgrade(taskId, deviceId, errorMessage);
    }

    /**
     * 设备升级失败处理
     */
    private void failDeviceUpgrade(String taskId, String deviceId, String errorMessage) {
        DeviceUpgradeStatus status = deviceUpgradeStatusRepository.findByTaskIdAndDeviceId(taskId, deviceId)
                .orElseThrow(() -> new RuntimeException("设备升级状态不存在"));

        status.setStatus(DeviceUpgradeStatus.UpgradeStatus.FAILED);
        status.setErrorMessage(errorMessage);
        deviceUpgradeStatusRepository.save(status);

        // 更新设备状态
        Device device = deviceRepository.findById(deviceId).orElse(null);
        if (device != null) {
            device.setStatus(Device.DeviceStatus.ERROR);
            deviceRepository.save(device);
        }

        // 更新任务计数
        OtaTask task = otaTaskRepository.findById(taskId).orElse(null);
        if (task != null) {
            task.setFailedDevices(task.getFailedDevices() + 1);
            if (task.getCompletedDevices() + task.getFailedDevices() >= task.getTotalDevices()) {
                task.setStatus(OtaTask.OtaStatus.FAILED);
            }
            otaTaskRepository.save(task);
        }

        log.error("设备升级失败: taskId={}, deviceId={}, error={}", taskId, deviceId, errorMessage);
    }

    /**
     * 获取 OTA 任务详情
     */
    public OtaTaskDTO getOtaTask(String taskId) {
        OtaTask task = otaTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("OTA 任务不存在: " + taskId));
        return toDTO(task);
    }

    /**
     * 获取设备升级状态
     */
    public DeviceUpgradeStatusDTO getDeviceUpgradeStatus(String taskId, String deviceId) {
        DeviceUpgradeStatus status = deviceUpgradeStatusRepository.findByTaskIdAndDeviceId(taskId, deviceId)
                .orElseThrow(() -> new RuntimeException("设备升级状态不存在"));
        return statusToDTO(status);
    }

    /**
     * 获取任务的所有设备状态
     */
    public List<DeviceUpgradeStatusDTO> getTaskDeviceStatuses(String taskId) {
        List<DeviceUpgradeStatus> statuses = deviceUpgradeStatusRepository.findByTaskId(taskId);
        return statuses.stream()
                .map(this::statusToDTO)
                .collect(Collectors.toList());
    }

    /**
     * 分页查询 OTA 任务
     */
    public Map<String, Object> listOtaTasks(int page, int pageSize, OtaTask.OtaStatus status) {
        Pageable pageable = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "createdAt"));

        Page<OtaTask> result;
        if (status != null) {
            result = otaTaskRepository.findByStatus(status, pageable);
        } else {
            result = otaTaskRepository.findAll(pageable);
        }

        Map<String, Object> response = new HashMap<>();
        response.put("items", result.getContent().stream()
                .map(this::toDTO)
                .collect(Collectors.toList()));
        response.put("total", result.getTotalElements());
        response.put("page", page);
        response.put("pageSize", pageSize);

        return response;
    }

    /**
     * 删除 OTA 任务
     */
    @Transactional
    public void deleteOtaTask(String taskId) {
        OtaTask task = otaTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("OTA 任务不存在: " + taskId));

        if (task.getStatus() == OtaTask.OtaStatus.RUNNING) {
            throw new RuntimeException("无法删除运行中的任务");
        }

        otaTaskRepository.deleteById(taskId);
        log.info("OTA 任务已删除: taskId={}", taskId);
    }

    /**
     * 生成任务ID
     */
    private String generateTaskId() {
        return "OTA" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
                + String.format("%04d", new Random().nextInt(10000));
    }

    /**
     * 生成状态ID
     */
    private String generateStatusId() {
        return "STATUS" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
                + String.format("%04d", new Random().nextInt(10000));
    }

    /**
     * 转换为 DTO
     */
    private OtaTaskDTO toDTO(OtaTask task) {
        OtaTaskDTO dto = new OtaTaskDTO();
        dto.setTaskId(task.getTaskId());
        dto.setTaskName(task.getTaskName());
        dto.setUpgradeType(task.getUpgradeType());
        dto.setModelId(task.getModelId());
        dto.setTargetVersion(task.getTargetVersion());
        dto.setStrategy(task.getStrategy());
        dto.setScheduledTime(task.getScheduledTime());
        dto.setStatus(task.getStatus());
        dto.setTotalDevices(task.getTotalDevices());
        dto.setCompletedDevices(task.getCompletedDevices());
        dto.setFailedDevices(task.getFailedDevices());
        dto.setCreatedAt(task.getCreatedAt());
        dto.setUpdatedAt(task.getUpdatedAt());

        // 加载关联信息
        if (task.getModelId() != null) {
            modelRepository.findById(task.getModelId())
                    .ifPresent(m -> dto.setModelName(m.getModelName()));
        }

        return dto;
    }

    /**
     * 状态转换为 DTO
     */
    private DeviceUpgradeStatusDTO statusToDTO(DeviceUpgradeStatus status) {
        DeviceUpgradeStatusDTO dto = new DeviceUpgradeStatusDTO();
        dto.setStatusId(status.getStatusId());
        dto.setTaskId(status.getTaskId());
        dto.setDeviceId(status.getDeviceId());
        dto.setStatus(status.getStatus());
        dto.setProgress(status.getProgress());
        dto.setErrorMessage(status.getErrorMessage());
        dto.setDownloadStartTime(status.getDownloadStartTime());
        dto.setDownloadCompleteTime(status.getDownloadCompleteTime());
        dto.setInstallStartTime(status.getInstallStartTime());
        dto.setInstallCompleteTime(status.getInstallCompleteTime());
        dto.setCreatedAt(status.getCreatedAt());
        dto.setUpdatedAt(status.getUpdatedAt());

        // 加载关联信息
        deviceRepository.findById(status.getDeviceId())
                .ifPresent(d -> dto.setDeviceName(d.getDeviceName()));

        return dto;
    }
}
