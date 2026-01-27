package com.edge.cloud.service;

import com.edge.cloud.dto.ConversionTaskDTO;
import com.edge.cloud.entity.ConversionTask;
import com.edge.cloud.entity.Model;
import com.edge.cloud.repository.ConversionTaskRepository;
import com.edge.cloud.repository.ModelRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 模型转换服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ConversionService {

    private final ConversionTaskRepository conversionTaskRepository;
    private final ModelRepository modelRepository;
    private final RestTemplate restTemplate;

    @Value("${TRAINING_SERVICE_URL:http://localhost:5002}")
    private String trainingServiceUrl;

    /**
     * 创建转换任务
     */
    @Transactional
    public ConversionTask createConversionTask(String modelId, ConversionTask.ConversionType conversionType) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));

        // 检查是否已有相同类型的转换任务
        List<ConversionTask> existingTasks = conversionTaskRepository.findByModelId(modelId);
        for (ConversionTask task : existingTasks) {
            if (task.getConversionType() == conversionType
                    && task.getStatus() != ConversionTask.ConversionStatus.COMPLETED
                    && task.getStatus() != ConversionTask.ConversionStatus.FAILED) {
                throw new RuntimeException("已有相同类型的转换任务在执行中: " + task.getTaskId());
            }
        }

        // 生成任务ID
        String taskId = generateTaskId();

        // 创建转换任务实体
        ConversionTask task = new ConversionTask();
        task.setTaskId(taskId);
        task.setModelId(modelId);
        task.setConversionType(conversionType);
        task.setStatus(ConversionTask.ConversionStatus.PENDING);
        task.setProgress(0.0f);

        // 根据转换类型设置源格式和目标格式
        switch (conversionType) {
            case PT_TO_ONNX:
                task.setSourceFormat(ConversionTask.ModelFormat.PT);
                task.setTargetFormat(ConversionTask.ModelFormat.ONNX);
                break;
            case ONNX_TO_ENGINE_FP16:
            case ONNX_TO_ENGINE_INT8:
            case ONNX_TO_ENGINE_FP32:
                task.setSourceFormat(ConversionTask.ModelFormat.ONNX);
                task.setTargetFormat(ConversionTask.ModelFormat.ENGINE);
                break;
        }

        // 更新模型状态
        model.setStatus(Model.ModelStatus.CONVERTING);
        modelRepository.save(model);

        task = conversionTaskRepository.save(task);
        log.info("转换任务创建成功: taskId={}, modelId={}, type={}", taskId, modelId, conversionType);

        return task;
    }

    /**
     * 启动转换任务
     */
    @Transactional
    public ConversionTaskDTO startConversion(String taskId) {
        ConversionTask task = conversionTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("转换任务不存在: " + taskId));

        if (task.getStatus() != ConversionTask.ConversionStatus.PENDING) {
            throw new RuntimeException("任务状态不允许启动: " + task.getStatus());
        }

        try {
            task.setStatus(ConversionTask.ConversionStatus.RUNNING);
            conversionTaskRepository.save(task);

            // 准备转换请求
            Map<String, Object> request = new HashMap<>();
            request.put("task_id", taskId);
            request.put("model_id", task.getModelId());
            request.put("conversion_type", task.getConversionType().name());
            request.put("precision", getPrecisionFromType(task.getConversionType()));

            // TODO: 调用 Python 训练服务执行转换
            // restTemplate.postForEntity(trainingServiceUrl + "/convert", request, String.class);

            log.info("转换任务已启动: taskId={}", taskId);
            return toDTO(task);

        } catch (Exception e) {
            log.error("启动转换任务失败: taskId={}", taskId, e);
            task.setStatus(ConversionTask.ConversionStatus.FAILED);
            task.setErrorMessage(e.getMessage());
            conversionTaskRepository.save(task);

            // 恢复模型状态
            Model model = modelRepository.findById(task.getModelId()).orElse(null);
            if (model != null) {
                model.setStatus(Model.ModelStatus.READY);
                modelRepository.save(model);
            }

            throw new RuntimeException("启动转换失败: " + e.getMessage());
        }
    }

    /**
     * 更新转换进度（由训练服务回调）
     */
    @Transactional
    public void updateConversionProgress(String taskId, float progress) {
        ConversionTask task = conversionTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("转换任务不存在: " + taskId));

        task.setProgress(progress);
        conversionTaskRepository.save(task);

        log.debug("转换进度更新: taskId={}, progress={}%", taskId, progress * 100);
    }

    /**
     * 完成转换（由训练服务回调）
     */
    @Transactional
    public void completeConversion(String taskId, String outputPath, long fileSizeBytes, int optimizationTimeSeconds) {
        ConversionTask task = conversionTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("转换任务不存在: " + taskId));

        task.setStatus(ConversionTask.ConversionStatus.COMPLETED);
        task.setProgress(1.0f);
        task.setOutputFilePath(outputPath);
        task.setFileSizeBytes(fileSizeBytes);
        task.setOptimizationTimeSeconds(optimizationTimeSeconds);
        conversionTaskRepository.save(task);

        // 更新模型的文件路径
        Model model = modelRepository.findById(task.getModelId())
                .orElseThrow(() -> new RuntimeException("模型不存在: " + task.getModelId()));

        switch (task.getTargetFormat()) {
            case ONNX:
                model.setOnnxFilePath(outputPath);
                break;
            case ENGINE:
                model.setEngineFilePath(outputPath);
                break;
        }

        model.setStatus(Model.ModelStatus.READY);
        modelRepository.save(model);

        log.info("转换完成: taskId={}, outputPath={}, size={} bytes, time={} s",
                taskId, outputPath, fileSizeBytes, optimizationTimeSeconds);
    }

    /**
     * 转换失败（由训练服务回调）
     */
    @Transactional
    public void failConversion(String taskId, String errorMessage) {
        ConversionTask task = conversionTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("转换任务不存在: " + taskId));

        task.setStatus(ConversionTask.ConversionStatus.FAILED);
        task.setProgress(0.0f);
        task.setErrorMessage(errorMessage);
        conversionTaskRepository.save(task);

        // 恢复模型状态
        Model model = modelRepository.findById(task.getModelId()).orElse(null);
        if (model != null) {
            model.setStatus(Model.ModelStatus.READY);
            modelRepository.save(model);
        }

        log.error("转换失败: taskId={}, error={}", taskId, errorMessage);
    }

    /**
     * 获取转换任务详情
     */
    public ConversionTaskDTO getConversionTask(String taskId) {
        ConversionTask task = conversionTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("转换任务不存在: " + taskId));
        return toDTO(task);
    }

    /**
     * 根据模型ID查询转换任务列表
     */
    public List<ConversionTaskDTO> getConversionTasksByModel(String modelId) {
        List<ConversionTask> tasks = conversionTaskRepository.findByModelId(modelId);
        return tasks.stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    /**
     * 分页查询转换任务
     */
    public Map<String, Object> listConversionTasks(int page, int pageSize, ConversionTask.ConversionStatus status) {
        Pageable pageable = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "createdAt"));

        Page<ConversionTask> result;
        if (status != null) {
            result = conversionTaskRepository.findByStatus(status, pageable);
        } else {
            result = conversionTaskRepository.findAll(pageable);
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
     * 删除转换任务
     */
    @Transactional
    public void deleteConversionTask(String taskId) {
        ConversionTask task = conversionTaskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("转换任务不存在: " + taskId));

        if (task.getStatus() == ConversionTask.ConversionStatus.RUNNING) {
            throw new RuntimeException("无法删除运行中的任务");
        }

        conversionTaskRepository.deleteById(taskId);
        log.info("转换任务已删除: taskId={}", taskId);
    }

    /**
     * 生成任务ID
     */
    private String generateTaskId() {
        return "CONV" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
                + String.format("%04d", new Random().nextInt(10000));
    }

    /**
     * 根据转换类型获取精度
     */
    private String getPrecisionFromType(ConversionTask.ConversionType conversionType) {
        switch (conversionType) {
            case ONNX_TO_ENGINE_FP16:
                return "fp16";
            case ONNX_TO_ENGINE_INT8:
                return "int8";
            case ONNX_TO_ENGINE_FP32:
                return "fp32";
            default:
                return "fp32";
        }
    }

    /**
     * 转换为 DTO
     */
    private ConversionTaskDTO toDTO(ConversionTask task) {
        ConversionTaskDTO dto = new ConversionTaskDTO();
        dto.setTaskId(task.getTaskId());
        dto.setModelId(task.getModelId());
        dto.setSourceFormat(task.getSourceFormat());
        dto.setTargetFormat(task.getTargetFormat());
        dto.setConversionType(task.getConversionType());
        dto.setStatus(task.getStatus());
        dto.setProgress(task.getProgress());
        dto.setErrorMessage(task.getErrorMessage());
        dto.setOutputFilePath(task.getOutputFilePath());
        dto.setFileSizeBytes(task.getFileSizeBytes());
        dto.setOptimizationTimeSeconds(task.getOptimizationTimeSeconds());
        dto.setCreatedAt(task.getCreatedAt());
        dto.setUpdatedAt(task.getUpdatedAt());

        // 加载关联信息
        modelRepository.findById(task.getModelId())
                .ifPresent(m -> dto.setModelName(m.getModelName()));

        return dto;
    }
}
