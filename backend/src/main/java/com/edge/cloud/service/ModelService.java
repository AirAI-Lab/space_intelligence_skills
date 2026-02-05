package com.edge.cloud.service;

import com.edge.cloud.dto.ModelCreateRequest;
import com.edge.cloud.dto.ModelDTO;
import com.edge.cloud.entity.ConversionTask;
import com.edge.cloud.entity.Model;
import com.edge.cloud.repository.ConversionTaskRepository;
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
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
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
    private final ConversionTaskRepository conversionTaskRepository;
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
        model.setPtFileSizeBytes(file.getSize());
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
     * 重新转换模型格式（删除旧转换结果并重新转换）
     */
    @Transactional
    public ModelDTO reconvertModel(String modelId, ConversionTask.ConversionType conversionType) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));

        // 获取该模型的所有转换任务
        List<ConversionTask> existingTasks = conversionTaskRepository.findByModelId(modelId);

        // 找到同类型的转换任务并删除
        for (ConversionTask task : existingTasks) {
            if (task.getConversionType() == conversionType) {
                log.info("删除旧的转换任务: taskId={}", task.getTaskId());
                conversionService.deleteConversionTask(task.getTaskId());
            }
        }

        // 根据转换类型清除对应的文件路径
        switch (conversionType) {
            case PT_TO_ONNX:
                if (model.getOnnxFilePath() != null) {
                    log.info("删除旧的 ONNX 文件: {}", model.getOnnxFilePath());
                    storageService.deleteFile(model.getOnnxFilePath());
                    model.setOnnxFilePath(null);
                }
                break;
            case ONNX_TO_ENGINE_FP16:
            case ONNX_TO_ENGINE_INT8:
            case ONNX_TO_ENGINE_FP32:
                if (model.getEngineFilePath() != null) {
                    log.info("删除旧的 Engine 文件: {}", model.getEngineFilePath());
                    storageService.deleteFile(model.getEngineFilePath());
                    model.setEngineFilePath(null);
                }
                break;
        }

        modelRepository.save(model);

        // 创建新的转换任务
        ConversionTask task = conversionService.createConversionTask(modelId, conversionType);
        log.info("重新转换任务已创建: modelId={}, taskId={}, type={}",
                modelId, task.getTaskId(), conversionType);

        // 启动转换
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
        dto.setPtFileSizeBytes(model.getPtFileSizeBytes());
        dto.setOnnxFilePath(model.getOnnxFilePath());
        dto.setOnnxFileSizeBytes(model.getOnnxFileSizeBytes());
        dto.setEngineFilePath(model.getEngineFilePath());
        dto.setEngineFileSizeBytes(model.getEngineFileSizeBytes());
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

    // ==================== 模型下载相关方法 ====================

    /**
     * 下载模型文件
     * 支持从 S3 或本地文件系统下载
     */
    public ResponseEntity<byte[]> downloadModelFile(String modelId, String format) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));

        String filePath;
        String fileName;

        // 根据格式选择文件路径
        switch (format.toLowerCase()) {
            case "pt":
            case "pth":
                filePath = model.getPtFilePath();
                fileName = model.getModelName() + ".pt";
                break;
            case "onnx":
                filePath = model.getOnnxFilePath();
                fileName = model.getModelName() + ".onnx";
                break;
            case "engine":
            case "tensorrt":
                filePath = model.getEngineFilePath();
                fileName = model.getModelName() + ".engine";
                break;
            default:
                // 默认尝试TensorRT引擎文件
                filePath = model.getEngineFilePath();
                if (filePath == null) {
                    filePath = model.getOnnxFilePath();
                }
                if (filePath == null) {
                    filePath = model.getPtFilePath();
                }
                fileName = model.getModelName() + "_" + format + ".bin";
        }

        if (filePath == null) {
            throw new RuntimeException("模型文件不存在: format=" + format + "，请先上传模型文件或进行格式转换");
        }

        try {
            byte[] content = null;

            // 首先尝试从存储服务获取文件（S3或本地存储）
            try {
                if (storageService.exists(filePath)) {
                    InputStream inputStream = storageService.getFile(filePath);
                    content = inputStream.readAllBytes();
                    inputStream.close();
                    log.info("从存储服务下载模型文件: modelId={}, format={}, path={}, size={} bytes",
                            modelId, format, filePath, content.length);
                } else {
                    log.warn("存储服务中文件不存在: {}", filePath);
                }
            } catch (Exception e) {
                log.warn("从存储服务获取文件失败: {}, 尝试本地文件系统", e.getMessage());
            }

            // 如果存储服务失败，尝试从本地文件系统读取（用于转换后的文件）
            if (content == null) {
                content = tryReadLocalFile(filePath);
                if (content != null) {
                    log.info("从本地文件系统下载模型文件: modelId={}, format={}, path={}, size={} bytes",
                            modelId, format, filePath, content.length);
                }
            }

            if (content == null) {
                throw new RuntimeException("模型文件不存在，请检查是否已上传模型或完成格式转换。文件路径: " + filePath);
            }

            // 设置响应头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
            headers.setContentDispositionFormData("attachment", fileName);

            return ResponseEntity.ok()
                    .headers(headers)
                    .body(content);

        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            log.error("下载模型文件失败: modelId={}, format={}, path={}", modelId, format, filePath, e);
            throw new RuntimeException("下载模型文件失败: " + e.getMessage());
        }
    }

    /**
     * 尝试从本地文件系统读取文件（用于转换服务生成的本地文件）
     */
    private byte[] tryReadLocalFile(String filePath) {
        try {
            java.io.File file = null;

            // 情况1: 如果路径包含 "outputs/" 或 "work/"，可能是转换服务生成的本地文件
            if (filePath.contains("outputs/") || filePath.contains("work/")) {
                file = new java.io.File(filePath);
                if (!file.exists()) {
                    // 尝试 /app/work 前缀（Docker 容器内路径）
                    file = new java.io.File("/app/work/outputs/" + filePath.substring(filePath.lastIndexOf("outputs/") + 8));
                }
            }
            // 情况2: S3 路径格式的 PT 文件，尝试映射到训练输出目录
            else if (filePath.startsWith("s3://models/")) {
                // S3 路径格式: s3://models/M_JOB202602011236009605/best.pt
                // 本地路径格式: /app/work/outputs/JOB202602011236009605/train/weights/best.pt
                String pathPart = filePath.substring("s3://models/".length()); // M_JOB202602011236009605/best.pt
                String[] parts = pathPart.split("/", 2);
                if (parts.length == 2) {
                    String modelId = parts[0]; // M_JOB202602011236009605
                    String fileName = parts[1]; // best.pt

                    // 对于训练生成的模型 (M_JOB*)，提取 JOB ID
                    if (modelId.startsWith("M_")) {
                        String jobId = modelId.substring(2); // JOB202602011236009605
                        file = new java.io.File("/app/work/outputs/" + jobId + "/train/weights/" + fileName);
                        log.debug("尝试训练输出目录: {}", file.getPath());
                    }
                }
            }

            // 如果上述方法未找到，尝试直接路径
            if (file == null || !file.exists()) {
                file = new java.io.File(filePath);
            }
            // 尝试在 /app/work/outputs 目录下查找
            if (!file.exists()) {
                file = new java.io.File("/app/work/outputs/" + filePath);
            }

            if (file.exists() && file.isFile()) {
                return java.nio.file.Files.readAllBytes(file.toPath());
            }

            log.warn("本地文件也不存在: {}", filePath);
            return null;
        } catch (Exception e) {
            log.warn("读取本地文件失败: {}", filePath, e);
            return null;
        }
    }

    /**
     * 获取模型文件下载信息
     */
    public Map<String, Object> getModelDownloadInfo(String modelId) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));

        Map<String, Object> info = new HashMap<>();
        info.put("model_id", modelId);
        info.put("model_name", model.getModelName());
        info.put("file_size_bytes", model.getFileSizeBytes());

        // 可用格式
        Map<String, Object> formats = new HashMap<>();
        if (model.getPtFilePath() != null) {
            formats.put("pt", Map.of(
                "path", model.getPtFilePath(),
                "size", model.getFileSizeBytes()
            ));
        }
        if (model.getOnnxFilePath() != null) {
            formats.put("onnx", Map.of(
                "path", model.getOnnxFilePath(),
                "size", model.getFileSizeBytes()
            ));
        }
        if (model.getEngineFilePath() != null) {
            formats.put("engine", Map.of(
                "path", model.getEngineFilePath(),
                "size", model.getFileSizeBytes()
            ));
        }
        info.put("available_formats", formats);

        // 下载URL前缀
        info.put("download_url_base", "/api/v1/models/" + modelId + "/download?format=");

        return info;
    }

    /**
     * 获取模型预览URL（临时下载链接）
     */
    public Map<String, Object> getModelPreviewUrl(String modelId, String format) {
        Model model = modelRepository.findById(modelId)
                .orElseThrow(() -> new RuntimeException("模型不存在: " + modelId));

        String filePath = switch (format.toLowerCase()) {
            case "pt", "pth" -> model.getPtFilePath();
            case "onnx" -> model.getOnnxFilePath();
            case "engine", "tensorrt" -> model.getEngineFilePath();
            default -> model.getEngineFilePath();
        };

        if (filePath == null) {
            throw new RuntimeException("模型文件不存在: format=" + format);
        }

        // 生成临时下载令牌（有效期1小时）
        String token = generateDownloadToken(modelId, format);

        Map<String, Object> urlInfo = new HashMap<>();
        urlInfo.put("model_id", modelId);
        urlInfo.put("format", format);
        urlInfo.put("download_url", "/api/v1/models/" + modelId + "/download?format=" + format + "&token=" + token);
        urlInfo.put("expires_at", System.currentTimeMillis() + 3600000); // 1小时后过期

        return urlInfo;
    }

    /**
     * 生成下载令牌
     */
    private String generateDownloadToken(String modelId, String format) {
        // 简单实现：使用Base64编码的modelId + format + timestamp
        String data = modelId + ":" + format + ":" + System.currentTimeMillis();
        return java.util.Base64.getEncoder().encodeToString(data.getBytes());
    }
}
