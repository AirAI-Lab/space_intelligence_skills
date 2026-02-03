package com.edge.cloud.service;

import com.edge.cloud.dto.ModelCreateRequest;
import com.edge.cloud.dto.ModelDTO;
import com.edge.cloud.entity.ConversionTask;
import com.edge.cloud.entity.Model;
import com.edge.cloud.repository.DatasetRepository;
import com.edge.cloud.repository.ModelRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 模型管理服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ModelService {

    private final ModelRepository modelRepository;
    private final DatasetRepository datasetRepository;
    private final ConversionService conversionService;
    private final StorageService storageService;
    private final RestTemplate restTemplate;

    @Value("${MODEL_STORAGE_PREFIX:models}")
    private String modelStoragePrefix;

    @Value("${TRAINING_SERVICE_URL:http://localhost:5002}")
    private String trainingServiceUrl;

    /**
     * 创建模型记录（训练完成后调用）
     */
    @Transactional
    public ModelDTO createModel(ModelCreateRequest request) {
        log.info("创建模型记录: {}", request.getModelName());

        // 验证父模型存在
        if (request.getParentModelId() != null) {
            modelRepository.findById(request.getParentModelId())
                    .orElseThrow(() -> new RuntimeException("父模型不存在: " + request.getParentModelId()));
        }

        // 验证数据集存在
        if (request.getDatasetId() != null) {
            datasetRepository.findById(request.getDatasetId())
                    .orElseThrow(() -> new RuntimeException("数据集不存在: " + request.getDatasetId()));
        }

        // 生成模型ID
        String modelId = generateModelId();

        // 创建模型实体
        Model model = new Model();
        model.setModelId(modelId);
        model.setModelName(request.getModelName());
        model.setModelType(request.getModelType());
        model.setFramework(request.getFramework());
        model.setVersion(request.getVersion());
        model.setParentModelId(request.getParentModelId());
        model.setDatasetId(request.getDatasetId());
        model.setInputWidth(request.getInputWidth());
        model.setInputHeight(request.getInputHeight());
        model.setStatus(Model.ModelStatus.TRAINING);
        model.setDeployedCount(0);

        model = modelRepository.save(model);
        log.info("模型记录创建成功: modelId={}", modelId);

        return toDTO(model);
    }

    /**
     * 上传模型文件（.pt 文件）
     */
    @Transactional
    public ModelDTO uploadModelFile(String modelId, MultipartFile file) throws Exception {
        log.info("开始上传模型文件: modelId={}, size={}, name={}",
                 modelId, file.getSize(), file.getOriginalFilename());

        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));

        long startTime = System.currentTimeMillis();

        // 上传到存储
        String filePath = storageService.uploadFile(file, modelStoragePrefix + "/" + modelId);

        long uploadTime = System.currentTimeMillis() - startTime;
        log.info("文件存储完成: modelId={}, path={}, time={}ms", modelId, filePath, uploadTime);

        model.setPtFilePath(filePath);
        model.setFileSizeBytes(file.getSize());
        model.setStatus(Model.ModelStatus.READY);

        model = modelRepository.save(model);

        long totalTime = System.currentTimeMillis() - startTime;
        log.info("模型文件上传成功: modelId={}, totalTime={}ms", modelId, totalTime);

        return toDTO(model);
    }

    /**
     * 更新模型指标（训练完成后调用）
     */
    @Transactional
    public void updateModelMetrics(String modelId, float map, float precision, float recall,
                                    float inferenceTimeMs, List<String> classNames) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));

        model.setMap(map);
        model.setPrecision(precision);
        model.setRecall(recall);
        model.setInferenceTimeMs(inferenceTimeMs);
        model.setClassNames(classNames);

        modelRepository.save(model);
        log.info("模型指标已更新: modelId={}, mAP={}", modelId, map);
    }

    /**
     * 转换模型格式
     */
    @Transactional
    public ModelDTO convertModel(String modelId, ConversionTask.ConversionType conversionType) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));

        // 检查模型是否可转换（本地文件或S3文件）
        // 训练产生的模型以 M_JOB 开头，文件在 S3 中
        boolean isTrainedModel = modelId.startsWith("M_JOB");
        boolean hasLocalFile = model.getPtFilePath() != null;

        if (!isTrainedModel && !hasLocalFile) {
            throw new RuntimeException("模型文件不存在，请先上传 .pt 文件或训练模型");
        }

        // 创建转换任务
        ConversionTask task = conversionService.createConversionTask(modelId, conversionType);

        log.info("模型转换任务已创建: modelId={}, taskId={}, type={}",
                modelId, task.getTaskId(), conversionType);

        // 调用转换服务执行转换
        conversionService.startConversion(task.getTaskId());

        return toDTO(model);
    }

    /**
     * 获取模型详情
     */
    public ModelDTO getModel(String modelId) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));
        return toDTO(model);
    }

    /**
     * 分页查询模型列表
     */
    public Map<String, Object> listModels(int page, int pageSize, Model.ModelType type, Model.ModelStatus status) {
        Pageable pageable = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "createdAt"));

        Page<Model> result;
        if (type != null && status != null) {
            // 同时按类型和状态过滤（需要自定义查询）
            result = modelRepository.findAll(pageable);
            result = filterResult(result, type, status);
        } else if (type != null) {
            result = modelRepository.findByModelType(type, pageable);
        } else if (status != null) {
            result = modelRepository.findByStatus(status, pageable);
        } else {
            result = modelRepository.findAll(pageable);
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
     * 获取可部署的模型列表
     */
    public List<ModelDTO> getDeployableModels() {
        return modelRepository.findDeployableModels().stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    /**
     * 增加模型部署计数
     */
    @Transactional
    public void incrementDeployCount(String modelId) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));

        model.setDeployedCount(model.getDeployedCount() + 1);
        model.setStatus(Model.ModelStatus.DEPLOYED);
        modelRepository.save(model);

        log.info("模型部署计数已更新: modelId={}, count={}", modelId, model.getDeployedCount());
    }

    /**
     * 减少模型部署计数
     */
    @Transactional
    public void decrementDeployCount(String modelId) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));

        int newCount = Math.max(0, model.getDeployedCount() - 1);
        model.setDeployedCount(newCount);

        if (newCount == 0) {
            model.setStatus(Model.ModelStatus.READY);
        }

        modelRepository.save(model);

        log.info("模型部署计数已更新: modelId={}, count={}", modelId, newCount);
    }

    /**
     * 删除模型
     */
    @Transactional
    public void deleteModel(String modelId) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));

        if (model.getDeployedCount() > 0) {
            throw new RuntimeException("模型正在使用中，无法删除");
        }

        // 删除存储文件
        if (model.getPtFilePath() != null) {
            storageService.deleteFile(model.getPtFilePath());
        }
        if (model.getOnnxFilePath() != null) {
            storageService.deleteFile(model.getOnnxFilePath());
        }
        if (model.getEngineFilePath() != null) {
            storageService.deleteFile(model.getEngineFilePath());
        }

        // 删除数据库记录
        modelRepository.deleteById(modelId);
        log.info("模型已删除: modelId={}", modelId);
    }

    /**
     * 生成模型ID
     */
    private String generateModelId() {
        return "M" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
                + String.format("%04d", new Random().nextInt(10000));
    }

    /**
     * 过滤结果
     */
    private Page<Model> filterResult(Page<Model> result, Model.ModelType type, Model.ModelStatus status) {
        List<Model> filtered = result.getContent().stream()
                .filter(m -> type == null || m.getModelType() == type)
                .filter(m -> status == null || m.getStatus() == status)
                .collect(Collectors.toList());

        return new PageImpl<>(
                filtered,
                result.getPageable(),
                result.getTotalElements()
        );
    }

    /**
     * 转换为 DTO
     */
    private ModelDTO toDTO(Model model) {
        ModelDTO dto = new ModelDTO();
        dto.setModelId(model.getModelId());
        dto.setModelName(model.getModelName());
        dto.setModelType(model.getModelType());
        dto.setFramework(model.getFramework());
        dto.setVersion(model.getVersion());
        dto.setParentModelId(model.getParentModelId());
        dto.setDatasetId(model.getDatasetId());
        dto.setPtFilePath(model.getPtFilePath());
        dto.setOnnxFilePath(model.getOnnxFilePath());
        dto.setEngineFilePath(model.getEngineFilePath());
        dto.setMap(model.getMap());
        dto.setMap50(model.getMap50());
        dto.setPrecision(model.getPrecision());
        dto.setRecall(model.getRecall());
        dto.setInferenceTimeMs(model.getInferenceTimeMs());
        dto.setInputWidth(model.getInputWidth());
        dto.setInputHeight(model.getInputHeight());
        dto.setClassNames(model.getClassNames());
        dto.setStatus(model.getStatus());
        dto.setFileSizeBytes(model.getFileSizeBytes());
        dto.setDeployedCount(model.getDeployedCount());
        dto.setCreatedAt(model.getCreatedAt());
        dto.setUpdatedAt(model.getUpdatedAt());

        // 加载关联信息
        if (model.getParentModelId() != null) {
            modelRepository.findById(model.getParentModelId())
                    .ifPresent(m -> dto.setParentModelName(m.getModelName()));
        }

        if (model.getDatasetId() != null) {
            datasetRepository.findById(model.getDatasetId())
                    .ifPresent(d -> dto.setDatasetName(d.getDatasetName()));
        }

        return dto;
    }
}
