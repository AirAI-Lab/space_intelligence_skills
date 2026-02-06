package com.edge.cloud.service;

import com.edge.cloud.dto.DeviceUpgradeStatusDTO;
import com.edge.cloud.dto.OtaTaskCreateRequest;
import com.edge.cloud.dto.OtaTaskDTO;
import com.edge.cloud.entity.*;
import com.edge.cloud.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Lazy;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
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
    private final DeploymentService deploymentService;
    private final com.edge.cloud.repository.ModelDeploymentRepository modelDeploymentRepository;

    // 使用 setter 注入打破循环依赖
    private MqttService mqttService;

    @Autowired
    @Lazy
    public void setMqttService(MqttService mqttService) {
        this.mqttService = mqttService;
    }

    @Value("${S3_ENDPOINT:http://localhost:8333}")
    private String s3Endpoint;

    @Value("${S3_EXTERNAL_ENDPOINT:http://192.168.0.103:8333}")
    private String s3ExternalEndpoint;

    @Value("${backend.external-url:http://localhost:8081}")
    private String backendExternalUrl;

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

            // 支持 ONNX 或 Engine 格式（Jetson 设备可接收 ONNX 后本地转换为 Engine）
            if (model.getOnnxFilePath() == null && model.getEngineFilePath() == null) {
                throw new RuntimeException("模型未转换，请先转换为 ONNX 或 Engine 格式");
            }
            log.info("模型验证通过: modelId={}, hasONNX={}, hasEngine={}",
                    model.getModelId(),
                    model.getOnnxFilePath() != null,
                    model.getEngineFilePath() != null);
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

            // 获取模型下载地址（优先使用 ONNX，Jetson 可本地转换为 Engine）
            String downloadUrl = null;
            String modelFileName = null;
            if (task.getModelId() != null) {
                Model model = modelRepository.findById(task.getModelId())
                        .orElseThrow(() -> new RuntimeException("模型不存在: " + task.getModelId()));

                // 优先使用 ONNX 文件（Jetson 可本地转换为 Engine）
                // 使用后端 API 下载，通过共享卷访问文件
                if (model.getOnnxFilePath() != null) {
                    // 使用后端 API 下载 ONNX 文件（使用可配置的外部URL）
                    downloadUrl = backendExternalUrl + "/api/v1/files/download?path=" + model.getOnnxFilePath();
                    modelFileName = "best.onnx";
                    log.info("使用 ONNX 文件进行 OTA: modelId={}, file={}, url={}", model.getModelId(), modelFileName, downloadUrl);
                } else if (model.getEngineFilePath() != null) {
                    downloadUrl = s3ExternalEndpoint + "/" + model.getEngineFilePath();
                    modelFileName = model.getEngineFilePath().substring(model.getEngineFilePath().lastIndexOf('/') + 1);
                    log.info("使用 Engine 文件进行 OTA: modelId={}, file={}, url={}", model.getModelId(), modelFileName, downloadUrl);
                } else {
                    throw new RuntimeException("模型没有可用的文件（ONNX 或 Engine）");
                }
            }

            // 向所有设备发送升级消息，并创建部署记录
            List<DeviceUpgradeStatus> statusList = deviceUpgradeStatusRepository.findByTaskId(taskId);
            for (DeviceUpgradeStatus status : statusList) {
                // 如果是模型升级，创建部署记录
                if (task.getModelId() != null) {
                    try {
                        deploymentService.createDeployment(
                                task.getModelId(),
                                status.getDeviceId(),
                                task.getTotalDevices() > 1 ? "BATCH" : "SINGLE",
                                "system",
                                taskId
                        );
                    } catch (Exception e) {
                        log.warn("创建部署记录失败: deviceId={}", status.getDeviceId(), e);
                    }
                }
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
            // 如果 downloadUrl 为空，重新获取
            if (downloadUrl == null || downloadUrl.isEmpty()) {
                downloadUrl = getDownloadUrl(task);
            }

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

            // 准备 MQTT 消息（使用边缘端期望的字段名）
            Map<String, Object> message = new HashMap<>();
            message.put("task_id", task.getTaskId());
            message.put("task_name", task.getTaskName());

            // 获取模型信息
            String modelDisplayName = "model";
            String modelVersion = task.getTargetVersion();
            if (task.getModelId() != null) {
                Model model = modelRepository.findById(task.getModelId()).orElse(null);
                if (model != null) {
                    modelDisplayName = model.getModelName();
                    message.put("model_id", model.getModelId());
                    message.put("model_display_name", modelDisplayName);
                    if (model.getInputWidth() != null) {
                        message.put("input_width", model.getInputWidth());
                    }
                    if (model.getInputHeight() != null) {
                        message.put("input_height", model.getInputHeight());
                    }
                    log.info("添加模型配置到 OTA 消息: modelId={}, modelName={}, inputSize={}x{}",
                            model.getModelId(), model.getModelName(),
                            model.getInputWidth(), model.getInputHeight());
                }
            }

            // 如果 version 为空，生成一个版本号（使用 task_id 后 8 位，保持与边缘端一致）
            if (modelVersion == null || modelVersion.isEmpty()) {
                modelVersion = task.getTaskId().substring(task.getTaskId().length() - 8);
            }

            message.put("model_name", modelDisplayName);
            message.put("model_version", modelVersion);
            message.put("download_url", downloadUrl);

            // 发送 MQTT 消息到边缘端订阅的命令主题
            String topic = "device/" + deviceId + "/ota/command";
            mqttService.publish(topic, message);

            log.info("OTA 升级消息已发送: deviceId={}, topic={}, downloadUrl={}", deviceId, topic, downloadUrl);

        } catch (Exception e) {
            log.error("发送 OTA 消息失败: deviceId={}", deviceId, e);
            failDeviceUpgrade(task.getTaskId(), deviceId, e.getMessage());
        }
    }

    /**
     * 获取模型下载地址
     */
    private String getDownloadUrl(OtaTask task) {
        if (task.getModelId() == null) {
            return null;
        }

        Model model = modelRepository.findById(task.getModelId())
                .orElseThrow(() -> new RuntimeException("模型不存在: " + task.getModelId()));

        // 优先使用 ONNX 文件（Jetson 可本地转换为 Engine）
        if (model.getOnnxFilePath() != null) {
            return backendExternalUrl + "/api/v1/files/download?path=" + model.getOnnxFilePath();
        } else if (model.getEngineFilePath() != null) {
            return s3ExternalEndpoint + "/" + model.getEngineFilePath();
        } else {
            throw new RuntimeException("模型没有可用的文件（ONNX 或 Engine）");
        }
    }

    /**
     * 处理设备升级进度更新（MQTT 回调）
     * @param taskId 任务ID
     * @param deviceId 设备ID
     * @param progress 当前进度百分比（0-100）
     * @param currentStage 当前阶段: downloading, verifying, converting, applying
     */
    @Transactional
    public void handleDeviceUpgradeProgress(String taskId, String deviceId, int progress, String currentStage) {
        DeviceUpgradeStatus status = deviceUpgradeStatusRepository.findByTaskIdAndDeviceId(taskId, deviceId)
                .orElseThrow(() -> new RuntimeException("设备升级状态不存在"));

        // 更新当前阶段（用于前端显示）
        status.setCurrentStage(currentStage);

        // 计算总体进度：将阶段进度映射到 0-100 的总体进度
        // downloading: 0-25%, verifying: 25-30%, converting: 30-90%, applying: 90-100%
        int overallProgress = calculateOverallProgress(currentStage, progress);
        status.setProgress(overallProgress);
        deviceUpgradeStatusRepository.save(status);

        // 更新任务的总进度（单设备任务时，直接使用设备进度）
        OtaTask task = otaTaskRepository.findById(taskId).orElse(null);
        if (task != null && task.getTotalDevices() == 1) {
            task.setProgress(overallProgress);
            otaTaskRepository.save(task);
        }

        log.debug("设备升级进度更新: taskId={}, deviceId={}, stage={}, stageProgress={}%, overallProgress={}%",
                taskId, deviceId, currentStage, progress, overallProgress);
    }

    /**
     * 根据阶段和阶段内进度计算总体进度
     * @param stage 当前阶段
     * @param stageProgress 阶段内进度（0-100）
     * @return 总体进度（0-100）
     */
    private int calculateOverallProgress(String stage, int stageProgress) {
        return switch (stage) {
            case "downloading" -> stageProgress / 4;  // 0-25%
            case "verifying" -> 25 + (stageProgress / 20);  // 25-30%
            case "converting" -> 30 + (stageProgress * 60 / 100);  // 30-90%
            case "applying" -> 90 + (stageProgress / 10);  // 90-100%
            case "installing" -> 90 + (stageProgress / 10);  // 90-100% (备用)
            default -> stageProgress;
        };
    }

    /**
     * 处理设备升级进度更新（MQTT 回调）- 兼容旧方法
     */
    @Transactional
    public void handleDeviceUpgradeProgress(String taskId, String deviceId, int progress) {
        handleDeviceUpgradeProgress(taskId, deviceId, progress, "unknown");
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

            // 标记部署记录成功（通过OTA任务ID和设备ID查找）
            if (task.getModelId() != null) {
                try {
                    deploymentService.markDeploymentSuccess(
                            findDeploymentId(taskId, deviceId),
                            device != null ? device.getInferenceFps() : null,
                            null,
                            null
                    );
                } catch (Exception e) {
                    log.warn("更新部署记录成功状态失败: taskId={}, deviceId={}", taskId, deviceId, e);
                }
            }
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

            // 标记部署记录失败
            if (task.getModelId() != null) {
                try {
                    deploymentService.markDeploymentFailed(
                            findDeploymentId(taskId, deviceId),
                            errorMessage
                    );
                } catch (Exception e) {
                    log.warn("更新部署记录失败状态: taskId={}, deviceId={}", taskId, deviceId, e);
                }
            }
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
    @Transactional(readOnly = true)
    public DeviceUpgradeStatusDTO getDeviceUpgradeStatus(String taskId, String deviceId) {
        DeviceUpgradeStatus status = deviceUpgradeStatusRepository.findByTaskIdAndDeviceId(taskId, deviceId)
                .orElseThrow(() -> new RuntimeException("设备升级状态不存在"));
        return statusToDTO(status);
    }

    /**
     * 获取任务的所有设备状态
     */
    @Transactional(readOnly = true)
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
     * 获取设备的待处理 OTA 任务
     */
    public OtaTaskDTO getPendingOtaTask(String deviceId) {
        // 查找该设备的 RUNNING 或 PENDING 状态的任务
        List<DeviceUpgradeStatus> pendingStatuses = deviceUpgradeStatusRepository
                .findRecentByDeviceId(deviceId).stream()
                .filter(s -> s.getStatus() == DeviceUpgradeStatus.UpgradeStatus.PENDING ||
                           s.getStatus() == DeviceUpgradeStatus.UpgradeStatus.DOWNLOADING)
                .collect(Collectors.toList());

        if (pendingStatuses.isEmpty()) {
            return null;
        }

        // 返回最早的一个待处理任务
        DeviceUpgradeStatus status = pendingStatuses.get(0);
        OtaTask task = otaTaskRepository.findById(status.getTaskId()).orElse(null);
        if (task == null) {
            return null;
        }

        return toDTO(task);
    }

    /**
     * 删除 OTA 任务
     */
    @Transactional
    public void deleteOtaTask(String taskId) {
        OtaTask task = otaTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("OTA 任务不存在: " + taskId));

        // 如果任务正在运行，先取消
        if (task.getStatus() == OtaTask.OtaStatus.RUNNING ||
            task.getStatus() == OtaTask.OtaStatus.SCHEDULED) {
            task.setStatus(OtaTask.OtaStatus.CANCELLED);
            otaTaskRepository.save(task);
            log.info("OTA 任务已取消: taskId={}", taskId);
        }

        // 先删除关联的设备升级状态记录
        deviceUpgradeStatusRepository.deleteByTaskId(taskId);

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

        // 计算进度百分比
        // 优先使用任务实际的进度值（单设备任务实时更新），否则用完成设备数计算
        if (task.getProgress() != null && task.getProgress() > 0) {
            dto.setProgress(task.getProgress());
        } else if (task.getTotalDevices() != null && task.getTotalDevices() > 0) {
            int progress = (task.getCompletedDevices() * 100) / task.getTotalDevices();
            dto.setProgress(progress);
        } else {
            dto.setProgress(0);
        }

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
        dto.setCurrentStage(status.getCurrentStage());  // 当前阶段
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

    // ==================== 回滚相关方法 ====================

    /**
     * 发送回滚命令到设备
     */
    @Transactional
    public void sendRollbackCommand(String deviceId, String taskId, String previousModelId) {
        try {
            // 准备 MQTT/HTTP 回滚消息
            Map<String, Object> message = new HashMap<>();
            message.put("task_id", taskId);
            message.put("action", "rollback");
            message.put("previous_model_id", previousModelId);

            // 发送消息到设备
            String topic = "device/" + deviceId + "/ota/rollback";
            mqttService.publish(topic, message);

            // 更新设备状态
            Device device = deviceRepository.findById(deviceId).orElse(null);
            if (device != null) {
                device.setStatus(Device.DeviceStatus.UPGRADING);
                deviceRepository.save(device);
            }

            log.info("回滚命令已发送: deviceId={}, previousModelId={}", deviceId, previousModelId);

        } catch (Exception e) {
            log.error("发送回滚命令失败: deviceId={}", deviceId, e);
            throw new RuntimeException("发送回滚命令失败: " + e.getMessage());
        }
    }

    /**
     * 处理设备回滚完成
     */
    @Transactional
    public void handleRollbackComplete(String deviceId, String taskId, boolean success) {
        DeviceUpgradeStatus status = deviceUpgradeStatusRepository
                .findByTaskIdAndDeviceId(taskId, deviceId)
                .orElse(null);

        if (status != null) {
            if (success) {
                status.setStatus(DeviceUpgradeStatus.UpgradeStatus.ROLLED_BACK);
            } else {
                status.setStatus(DeviceUpgradeStatus.UpgradeStatus.FAILED);
                status.setErrorMessage("回滚失败");
            }
            deviceUpgradeStatusRepository.save(status);
        }

        // 更新设备状态
        Device device = deviceRepository.findById(deviceId).orElse(null);
        if (device != null) {
            if (success) {
                device.setStatus(Device.DeviceStatus.ONLINE);
            } else {
                device.setStatus(Device.DeviceStatus.ERROR);
            }
            deviceRepository.save(device);
        }

        // 标记部署记录已回滚
        if (success) {
            try {
                deploymentService.markDeploymentRolledBack(findDeploymentId(taskId, deviceId));
            } catch (Exception e) {
                log.warn("更新部署记录回滚状态失败: taskId={}, deviceId={}", taskId, deviceId, e);
            }
        }

        log.info("设备回滚处理完成: deviceId={}, success={}", deviceId, success);
    }

    /**
     * 重试失败的设备
     */
    @Transactional
    public OtaTaskDTO retryFailedDevices(String taskId) {
        OtaTask task = otaTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("OTA任务不存在: " + taskId));

        // 获取失败的设备
        List<DeviceUpgradeStatus> failedStatuses = deviceUpgradeStatusRepository
                .findFailedDevices(taskId);

        if (failedStatuses.isEmpty()) {
            log.info("没有需要重试的失败设备: taskId={}", taskId);
            return toDTO(task);
        }

        log.info("重试失败设备: taskId={}, count={}", taskId, failedStatuses.size());

        // 重置失败设备的状态
        for (DeviceUpgradeStatus status : failedStatuses) {
            status.setStatus(DeviceUpgradeStatus.UpgradeStatus.PENDING);
            status.setProgress(0);
            status.setCurrentStage(null);  // 重置阶段
            status.setErrorMessage(null);
            deviceUpgradeStatusRepository.save(status);

            // 重新发送升级消息（downloadUrl 会在方法内部重新获取）
            sendOtaMessageToDevice(status.getDeviceId(), task, null);
        }

        // 更新任务状态
        task.setFailedDevices(0);
        task.setStatus(OtaTask.OtaStatus.RUNNING);
        otaTaskRepository.save(task);

        return toDTO(task);
    }

    /**
     * 重试单个设备
     */
    @Transactional
    public void retrySingleDevice(String taskId, String deviceId) {
        DeviceUpgradeStatus status = deviceUpgradeStatusRepository
                .findByTaskIdAndDeviceId(taskId, deviceId)
                .orElseThrow(() -> new RuntimeException("设备升级状态不存在"));

        // 重置状态
        status.setStatus(DeviceUpgradeStatus.UpgradeStatus.PENDING);
        status.setProgress(0);
        status.setCurrentStage(null);  // 重置阶段
        status.setErrorMessage(null);
        deviceUpgradeStatusRepository.save(status);

        // 获取任务信息
        OtaTask task = otaTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("OTA任务不存在: " + taskId));

        // 重新发送升级消息（downloadUrl 会在方法内部重新获取）
        sendOtaMessageToDevice(deviceId, task, null);

        log.info("单个设备重试已发送: taskId={}, deviceId={}", taskId, deviceId);
    }

    /**
     * 暂停升级任务
     */
    @Transactional
    public void pauseOtaTask(String taskId) {
        OtaTask task = otaTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("OTA任务不存在: " + taskId));

        if (task.getStatus() != OtaTask.OtaStatus.RUNNING) {
            throw new RuntimeException("只能暂停运行中的任务");
        }

        task.setStatus(OtaTask.OtaStatus.PAUSED);
        otaTaskRepository.save(task);

        log.info("升级任务已暂停: taskId={}", taskId);
    }

    /**
     * 恢复升级任务
     */
    @Transactional
    public void resumeOtaTask(String taskId) {
        OtaTask task = otaTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("OTA任务不存在: " + taskId));

        if (task.getStatus() != OtaTask.OtaStatus.PAUSED) {
            throw new RuntimeException("只能恢复已暂停的任务");
        }

        task.setStatus(OtaTask.OtaStatus.RUNNING);
        otaTaskRepository.save(task);

        // 继续处理PENDING状态的设备
        List<DeviceUpgradeStatus> pendingStatuses = deviceUpgradeStatusRepository
                .findByTaskIdAndStatus(taskId, DeviceUpgradeStatus.UpgradeStatus.PENDING);

        for (DeviceUpgradeStatus status : pendingStatuses) {
            // 重新发送升级消息（downloadUrl 会在方法内部重新获取）
            sendOtaMessageToDevice(status.getDeviceId(), task, null);
        }

        log.info("升级任务已恢复: taskId={}", taskId);
    }

    /**
     * 回滚设备升级（手动触发）
     */
    @Transactional
    public void rollbackDeviceUpgrade(String taskId, String deviceId) {
        log.info("手动回滚设备升级: taskId={}, deviceId={}", taskId, deviceId);

        // 检查任务和设备是否存在
        OtaTask task = otaTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("OTA任务不存在: " + taskId));

        Device device = deviceRepository.findById(deviceId)
                .orElseThrow(() -> new RuntimeException("设备不存在: " + deviceId));

        // 获取设备升级状态
        DeviceUpgradeStatus status = deviceUpgradeStatusRepository
                .findByTaskIdAndDeviceId(taskId, deviceId)
                .orElseThrow(() -> new RuntimeException("设备升级状态不存在"));

        // 通过AutoRollbackService执行回滚
        if (mqttService != null) {
            // 发送回滚命令到设备
            Map<String, Object> message = new HashMap<>();
            message.put("task_id", taskId);
            message.put("action", "rollback");

            String topic = "device/" + deviceId + "/ota/rollback";
            mqttService.publish(topic, message);

            log.info("回滚命令已发送: deviceId={}, topic={}", deviceId, topic);
        } else {
            throw new RuntimeException("MQTT服务不可用，无法发送回滚命令");
        }
    }

    /**
     * 获取设备状态汇总
     */
    public Map<String, Object> getDeviceStatusSummary(String taskId) {
        List<DeviceUpgradeStatus> allStatuses = deviceUpgradeStatusRepository.findByTaskId(taskId);

        int total = allStatuses.size();
        int pending = 0, downloading = 0, installing = 0, completed = 0, failed = 0, rolledBack = 0;

        for (DeviceUpgradeStatus status : allStatuses) {
            switch (status.getStatus()) {
                case PENDING -> pending++;
                case DOWNLOADING -> downloading++;
                case INSTALLING -> installing++;
                case COMPLETED -> completed++;
                case FAILED, DOWNLOAD_FAILED, INSTALL_FAILED -> failed++;
                case ROLLED_BACK -> rolledBack++;
                default -> {}
            }
        }

        Map<String, Object> summary = new HashMap<>();
        summary.put("task_id", taskId);
        summary.put("total", total);
        summary.put("pending", pending);
        summary.put("downloading", downloading);
        summary.put("installing", installing);
        summary.put("completed", completed);
        summary.put("failed", failed);
        summary.put("rolled_back", rolledBack);
        summary.put("progress", total > 0 ? (int) ((completed + failed + rolledBack) * 100.0 / total) : 0);

        return summary;
    }

    /**
     * 根据OTA任务ID和设备ID查找部署记录ID
     */
    private String findDeploymentId(String taskId, String deviceId) {
        return modelDeploymentRepository.findByOtaTaskIdAndDeviceId(taskId, deviceId)
                .map(com.edge.cloud.entity.ModelDeployment::getDeploymentId)
                .orElseThrow(() -> new RuntimeException("部署记录不存在: taskId=" + taskId + ", deviceId=" + deviceId));
    }

    /**
     * 替换模型（触发热加载）
     * 向设备发送MQTT消息，触发热加载已部署的模型
     */
    public void replaceModel(String taskId, String deviceId) {
        OtaTask task = otaTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("OTA任务不存在: " + taskId));

        if (task.getUpgradeType() != OtaTask.UpgradeType.MODEL) {
            throw new RuntimeException("该任务不是模型升级任务");
        }

        if (task.getModelId() == null) {
            throw new RuntimeException("该任务没有关联的模型");
        }

        // 获取模型信息
        Model model = modelRepository.findById(task.getModelId())
                .orElseThrow(() -> new RuntimeException("模型不存在: " + task.getModelId()));

        // 获取设备升级状态
        DeviceUpgradeStatus upgradeStatus = deviceUpgradeStatusRepository
                .findByTaskIdAndDeviceId(taskId, deviceId)
                .orElseThrow(() -> new RuntimeException("设备升级状态不存在"));

        // 构建engine文件路径
        // 使用与 sendOtaMessageToDevice 相同的逻辑来确定版本号
        // 保持与边缘端实际生成的文件名一致
        String version = task.getTargetVersion();
        if (version == null || version.isEmpty()) {
            // 使用 task_id 后 8 位（与边缘端逻辑一致）
            version = task.getTaskId().substring(task.getTaskId().length() - 8);
        }
        String engineFileName = task.getTaskName() + "_" + version + ".engine";
        String enginePath = "/home/nvidia/edge_infer/models/" + engineFileName;

        // 发送MQTT消息触发热加载
        Map<String, Object> message = new HashMap<>();
        message.put("task_id", taskId);
        message.put("task_name", task.getTaskName());
        message.put("model_id", model.getModelId());
        message.put("model_display_name", model.getModelName());
        message.put("model_version", model.getVersion());
        message.put("engine_path", enginePath);
        message.put("input_width", model.getInputWidth() != null ? model.getInputWidth() : 640);
        message.put("input_height", model.getInputHeight() != null ? model.getInputHeight() : 640);

        String topic = "device/" + deviceId + "/model/reload";
        mqttService.publish(topic, message);

        log.info("模型热加载指令已发送: deviceId={}, topic={}, enginePath={}", deviceId, topic, enginePath);
    }
}
