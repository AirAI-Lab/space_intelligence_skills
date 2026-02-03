package com.edge.cloud.service;

import com.edge.cloud.dto.TrainingJobDTO;
import com.edge.cloud.dto.TrainingJobCreateRequest;
import com.edge.cloud.dto.TrainingMetricDTO;
import com.edge.cloud.entity.*;
import com.edge.cloud.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 训练任务管理服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class TrainingService {

    private final TrainingJobRepository trainingJobRepository;
    private final DatasetRepository datasetRepository;
    private final ModelRepository modelRepository;
    private final TrainingMetricRepository trainingMetricRepository;
    private final RestTemplate restTemplate;

    @Value("${TRAINING_SERVICE_URL:http://localhost:5002}")
    private String trainingServiceUrl;

    @Value("${MLFLOW_TRACKING_URI:http://localhost:5001}")
    private String mlflowTrackingUri;

    /**
     * 创建训练任务
     */
    @Transactional
    public TrainingJobDTO createTrainingJob(TrainingJobCreateRequest request) {
        log.info("创建训练任务: {}, datasetSource: {}, optimizer: {}, lr0: {}, weightDecay: {}, workers: {}",
            request.getJobName(), request.getDatasetSource(), request.getOptimizer(), request.getLr0(), request.getWeightDecay(), request.getWorkers());

        String datasetId = null;
        String datasetName = null;

        // 根据数据集来源进行验证
        String datasetSource = request.getDatasetSource() != null ? request.getDatasetSource() : "backend";

        switch (datasetSource) {
            case "backend":
                // 验证后端数据集存在
                if (request.getDatasetId() == null || request.getDatasetId().isEmpty()) {
                    throw new RuntimeException("请选择数据集");
                }
                Dataset dataset = datasetRepository.findById(request.getDatasetId())
                        .orElseThrow(() -> new RuntimeException("数据集不存在: " + request.getDatasetId()));
                if (dataset.getStatus() != Dataset.DatasetStatus.READY) {
                    throw new RuntimeException("数据集未就绪: " + dataset.getStatus());
                }
                datasetId = request.getDatasetId();
                datasetName = dataset.getDatasetName();
                break;

            case "url":
                // URL 数据集
                if (request.getDatasetUrl() == null || request.getDatasetUrl().isEmpty()) {
                    throw new RuntimeException("请输入数据集 URL");
                }
                // 生成虚拟数据集ID用于标识
                datasetId = "URL_" + System.currentTimeMillis();
                log.info("使用 URL 数据集: url={}, name={}", request.getDatasetUrl(), request.getDatasetName());
                break;

            case "local":
                // 本地路径数据集
                if (request.getDatasetPath() == null || request.getDatasetPath().isEmpty()) {
                    throw new RuntimeException("请输入本地路径");
                }
                // 生成虚拟数据集ID用于标识
                datasetId = "LOCAL_" + System.currentTimeMillis();
                log.info("使用本地路径数据集: path={}, name={}", request.getDatasetPath(), request.getDatasetName());
                break;

            default:
                throw new RuntimeException("不支持的数据集来源: " + datasetSource);
        }

        // 方案B：续训时使用原任务ID，不创建新任务
        TrainingJob job;  // 改为使用 job 实体
        if (Boolean.TRUE.equals(request.getResume()) && request.getResumeJobId() != null) {
            // 续训：使用原任务ID
            String resumeJobId = request.getResumeJobId();
            log.info("续训任务：使用原任务ID {}", resumeJobId);

            // 验证原任务存在
            job = trainingJobRepository.findById(resumeJobId)
                    .orElseThrow(() -> new RuntimeException("原任务不存在: " + resumeJobId));

            // 如果原任务正在运行，先停止它
            if (job.getStatus() == TrainingJob.TrainingStatus.RUNNING) {
                log.info("续训任务：原任务正在运行，先停止任务 {}", resumeJobId);
                try {
                    // 调用训练服务停止训练
                    if (trainingServiceUrl != null) {
                        restTemplate.postForObject(trainingServiceUrl + "/train/" + resumeJobId + "/stop", null, String.class);
                        log.info("续训任务：已停止原任务 {}", resumeJobId);
                    }
                } catch (Exception e) {
                    log.warn("续训任务：停止原任务失败，继续创建续训任务: {}", e.getMessage());
                }
                // 更新数据库状态为已取消
                job.setStatus(TrainingJob.TrainingStatus.CANCELLED);
                trainingJobRepository.save(job);
            }

            // 更新原任务状态（保持原任务名称不变）
            job.setStatus(TrainingJob.TrainingStatus.PENDING);
            job.setStartedAt(null);  // 重置启动时间
            job.setCompletedAt(null);
            job.setOutputModelId(null);
            job.setFinalMap(null);
            job.setFinalLoss(null);
            job.setBestEpoch(null);
            // 注意：不修改 jobName，保持原任务名称

            // 如果请求有新的训练参数，更新它们
            if (request.getEpochs() != null) {
                job.setEpochs(request.getEpochs());
            }
            if (request.getBatchSize() != null) {
                job.setBatchSize(request.getBatchSize());
            }
            if (request.getImgSize() != null) {
                job.setImgSize(request.getImgSize());
            }

            // 更新续训标志
            job.setResume(true);
            job.setResumeJobId(resumeJobId);
            job.setEnableSmartOptimization(request.getEnableSmartOptimization() != null ? request.getEnableSmartOptimization() : true);

            log.info("续训任务已更新: jobId={}, jobName={}", job.getJobId(), job.getJobName());
        } else {
            // 普通训练：创建新任务
            job = new TrainingJob();
            job.setJobId(generateJobId());
            job.setJobName(request.getJobName());
            job.setResume(false);
            job.setResumeJobId(null);
        }

        // 构建超参数 map（YOLOv8 参数 - 针对溺水检测优化）
        Map<String, Object> hyperparameters = new HashMap<>();
        if (request.getHyperparameters() != null && !request.getHyperparameters().isEmpty()) {
            // 使用传入的超参数（兼容旧版）
            log.info("使用传入的 hyperparameters map: {}", request.getHyperparameters());
            hyperparameters = request.getHyperparameters();
        } else {
            // 从新字段构建超参数（使用优化的默认值）
            log.info("从新字段构建 hyperparameters: optimizer={}, lr0={}, lrf={}, mixup={}",
                request.getOptimizer(), request.getLr0(), request.getLrf(), request.getMixup());

            // 优化器配置：默认使用 AdamW（更快收敛）
            hyperparameters.put("optimizer", request.getOptimizer() != null ? request.getOptimizer() : "AdamW");
            // 学习率：初始 0.01，最终 0.001（学习率衰减）
            hyperparameters.put("lr0", request.getLr0() != null ? request.getLr0() : 0.01);
            hyperparameters.put("lrf", request.getLrf() != null ? request.getLrf() : 0.001);  // 最终学习率，实现衰减策略
            hyperparameters.put("momentum", 0.937);
            hyperparameters.put("weight_decay", request.getWeightDecay() != null ? request.getWeightDecay() : 0.0005);

            // 训练稳定性参数
            hyperparameters.put("warmup_epochs", request.getWarmupEpochs() != null ? request.getWarmupEpochs() : 3);
            hyperparameters.put("warmup_momentum", 0.8);
            hyperparameters.put("warmup_bias_lr", 0.1);

            // 早停机制：30轮无改善则停止
            hyperparameters.put("patience", request.getPatience() != null ? request.getPatience() : 30);
            hyperparameters.put("save_period", request.getSavePeriod() != null ? request.getSavePeriod() : 10);

            // 数据增强：针对小数据集优化
            hyperparameters.put("mosaic", request.getMosaic() != null ? request.getMosaic() : 1.0);
            hyperparameters.put("mixup", request.getMixup() != null ? request.getMixup() : 0.15);  // 开启轻量Mixup
            hyperparameters.put("copy_paste", 0.5);  // 复制粘贴增强

            // HSV增强
            hyperparameters.put("hsv_h", 0.015);
            hyperparameters.put("hsv_s", 0.7);
            hyperparameters.put("hsv_v", 0.4);

            // 损失函数权重
            hyperparameters.put("box", 7.5);
            hyperparameters.put("cls", 0.5);
            hyperparameters.put("dfl", 1.5);

            // 其他参数
            if (request.getWorkers() != null) hyperparameters.put("workers", request.getWorkers());

            log.info("构建的优化 hyperparameters: {}", hyperparameters);
        }

        // 对于普通训练（非续训），创建新的训练任务实体
        // 对于续训，job 已经在上面被设置为原任务，只需要更新超参数
        if (!Boolean.TRUE.equals(job.getResume())) {
            // 普通训练：创建新任务
            job.setJobId(generateJobId());
            job.setJobName(request.getJobName());
            job.setDatasetId(datasetId);
            job.setDatasetSource(datasetSource);
            job.setDatasetUrl(request.getDatasetUrl());
            job.setDatasetPath(request.getDatasetPath());
            job.setDatasetName(request.getDatasetName());
            job.setBaseModelId(request.getBaseModelId());
            job.setBaseModel(request.getBaseModel());
            job.setEpochs(request.getEpochs());
            job.setBatchSize(request.getBatchSize());
            job.setImgSize(request.getImgSize());
            job.setUseGpu(request.getUseGpu());
            job.setTrainingType(request.getTrainingType() != null ? request.getTrainingType() : TrainingJob.TrainingType.FULL_TRAINING);
            job.setHyperparameters(hyperparameters);
            job.setStatus(TrainingJob.TrainingStatus.PENDING);
            job.setCurrentEpoch(0);
            job.setProgress(0.0f);
            job.setResume(false);
            job.setResumeJobId(null);
        } else {
            // 续训：更新超参数，保持其他字段不变（包括任务名称）
            job.setHyperparameters(hyperparameters);
        }

        // 保存到数据库
        job = trainingJobRepository.save(job);
        log.info("训练任务保存成功: jobId={}, jobName={}, datasetSource={}, datasetId={}, resume={}",
                job.getJobId(), job.getJobName(), datasetSource, datasetId, job.getResume());

        return toDTO(job);
    }

    /**
     * 启动训练任务
     */
    @Transactional
    public TrainingJobDTO startTraining(String jobId) {
        TrainingJob job = trainingJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("训练任务不存在: " + jobId));

        if (job.getStatus() != TrainingJob.TrainingStatus.PENDING) {
            throw new RuntimeException("任务状态不允许启动: " + job.getStatus());
        }

        try {
            // 更新任务状态
            job.setStatus(TrainingJob.TrainingStatus.RUNNING);
            job.setStartedAt(LocalDateTime.now());
            trainingJobRepository.save(job);

            // 获取数据集存储路径
            String datasetStoragePath = null;
            if ("backend".equals(job.getDatasetSource()) && job.getDatasetId() != null) {
                datasetStoragePath = datasetRepository.findById(job.getDatasetId())
                        .map(dataset -> {
                            // 对于本地路径数据集，需要返回完整路径
                            if ("local".equals(dataset.getDatasetSource())) {
                                String storagePath = dataset.getStoragePath();
                                // 如果 storagePath 已经是完整路径，直接使用；否则添加基础路径
                                if (storagePath.startsWith("/app/data/datasets/") || storagePath.startsWith("/app/data/datasets\\")) {
                                    return storagePath;
                                }
                                return "/app/data/datasets/" + storagePath;
                            }
                            return dataset.getStoragePath();
                        })
                        .orElse(null);
            }

            // 调用训练服务启动训练
            Map<String, Object> trainingRequest = new HashMap<>();
            trainingRequest.put("job_id", jobId);
            trainingRequest.put("dataset_id", job.getDatasetId());
            trainingRequest.put("dataset_source", job.getDatasetSource());
            trainingRequest.put("dataset_url", job.getDatasetUrl());
            trainingRequest.put("dataset_path", job.getDatasetPath());
            trainingRequest.put("dataset_name", job.getDatasetName());
            trainingRequest.put("dataset_storage_path", datasetStoragePath);
            trainingRequest.put("epochs", job.getEpochs());
            trainingRequest.put("batch_size", job.getBatchSize());
            trainingRequest.put("img_size", job.getImgSize());
            trainingRequest.put("use_gpu", job.getUseGpu());
            // 使用 baseModel 字段（优先）或 baseModelId
            String baseModel = job.getBaseModel() != null ? job.getBaseModel() :
                              (job.getBaseModelId() != null ? job.getBaseModelId() : "yolov8n.pt");
            trainingRequest.put("base_model", baseModel);
            // 传递超参数到训练服务
            trainingRequest.put("hyperparameters", job.getHyperparameters());
            // 断点续训参数
            trainingRequest.put("resume", job.getResume() != null ? job.getResume() : false);
            trainingRequest.put("resume_job_id", job.getResumeJobId());
            // 智能参数优化开关
            trainingRequest.put("enable_smart_optimization", job.getEnableSmartOptimization() != null ? job.getEnableSmartOptimization() : true);

            // 调用 Python 训练服务 API
            String response = restTemplate.postForObject(trainingServiceUrl + "/train", trainingRequest, String.class);
            log.info("训练服务响应: {}", response);

            log.info("训练任务已启动: jobId={}", jobId);
            return toDTO(job);

        } catch (Exception e) {
            log.error("启动训练任务失败: jobId={}", jobId, e);
            job.setStatus(TrainingJob.TrainingStatus.FAILED);
            trainingJobRepository.save(job);
            throw new RuntimeException("启动训练失败: " + e.getMessage());
        }
    }

    /**
     * 停止训练任务
     */
    @Transactional
    public TrainingJobDTO stopTraining(String jobId) {
        TrainingJob job = trainingJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("训练任务不存在: " + jobId));

        if (job.getStatus() != TrainingJob.TrainingStatus.RUNNING) {
            throw new RuntimeException("任务未在运行中");
        }

        try {
            // 调用训练服务停止训练
            ResponseEntity<String> response = restTemplate.postForEntity(
                trainingServiceUrl + "/train/" + jobId + "/stop", null, String.class);

            // 检查训练服务响应
            if (response.getStatusCode().is2xxSuccessful()) {
                job.setStatus(TrainingJob.TrainingStatus.CANCELLED);
                job.setCompletedAt(LocalDateTime.now());
                trainingJobRepository.save(job);
                log.info("训练任务已停止: jobId={}", jobId);
            } else {
                log.warn("训练服务返回非成功状态: {}", response.getStatusCode());
                // 即使训练服务返回错误，也更新数据库状态
                job.setStatus(TrainingJob.TrainingStatus.CANCELLED);
                job.setCompletedAt(LocalDateTime.now());
                trainingJobRepository.save(job);
            }

            return toDTO(job);

        } catch (Exception e) {
            // 如果训练服务找不到任务（可能已结束或服务重启），仍然更新数据库状态
            String errorMsg = e.getMessage();
            if (errorMsg != null && errorMsg.contains("not found")) {
                log.warn("训练服务中找不到任务，但更新数据库状态: jobId={}", jobId);
                job.setStatus(TrainingJob.TrainingStatus.CANCELLED);
                job.setCompletedAt(LocalDateTime.now());
                trainingJobRepository.save(job);
                return toDTO(job);
            }

            log.error("停止训练任务失败: jobId={}", jobId, e);
            throw new RuntimeException("停止训练失败: " + e.getMessage());
        }
    }

    /**
     * 暂停训练任务
     */
    @Transactional
    public TrainingJobDTO pauseTraining(String jobId) {
        TrainingJob job = trainingJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("训练任务不存在: " + jobId));

        if (job.getStatus() != TrainingJob.TrainingStatus.RUNNING) {
            throw new RuntimeException("任务未在运行中");
        }

        job.setStatus(TrainingJob.TrainingStatus.PAUSED);
        trainingJobRepository.save(job);

        log.info("训练任务已暂停: jobId={}", jobId);
        return toDTO(job);
    }

    /**
     * 恢复训练任务
     */
    @Transactional
    public TrainingJobDTO resumeTraining(String jobId) {
        TrainingJob job = trainingJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("训练任务不存在: " + jobId));

        if (job.getStatus() != TrainingJob.TrainingStatus.PAUSED) {
            throw new RuntimeException("任务未在暂停状态");
        }

        job.setStatus(TrainingJob.TrainingStatus.RUNNING);
        trainingJobRepository.save(job);

        // TODO: 调用训练服务恢复训练
        log.info("训练任务已恢复: jobId={}", jobId);
        return toDTO(job);
    }

    /**
     * 更新训练进度（由训练服务回调）
     */
    @Transactional
    public void updateTrainingProgress(String jobId, int currentEpoch, float progress, Float trainLoss, Float valLoss) {
        TrainingJob job = trainingJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("训练任务不存在: " + jobId));

        job.setCurrentEpoch(currentEpoch);
        job.setProgress(progress);
        trainingJobRepository.save(job);

        // 记录训练指标到时序数据库
        TrainingMetric metric = new TrainingMetric(LocalDateTime.now(), jobId, currentEpoch);
        metric.setTrainLoss(trainLoss);
        metric.setValLoss(valLoss);
        trainingMetricRepository.save(metric);

        log.debug("训练进度更新: jobId={}, epoch={}, progress={}%", jobId, currentEpoch, progress * 100);
    }

    /**
     * 完成训练（由训练服务回调）
     */
    @Transactional
    public void completeTraining(String jobId, String outputModelId, float finalMap, float finalMap50, float finalLoss, int bestEpoch) {
        TrainingJob job = trainingJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("训练任务不存在: " + jobId));

        job.setStatus(TrainingJob.TrainingStatus.COMPLETED);
        job.setOutputModelId(outputModelId);
        job.setFinalMap(finalMap);
        job.setFinalLoss(finalLoss);
        job.setBestEpoch(bestEpoch);
        job.setProgress(1.0f);
        job.setCompletedAt(LocalDateTime.now());
        trainingJobRepository.save(job);

        // 自动创建模型记录（如果不存在）
        if (!modelRepository.existsById(outputModelId)) {
            createModelFromTraining(job, outputModelId, finalMap, finalMap50);
        }

        log.info("训练完成: jobId={}, outputModel={}, mAP50-95={}, mAP50={}", jobId, outputModelId, finalMap, finalMap50);
    }

    /**
     * 从训练任务创建模型记录
     */
    @Transactional
    private void createModelFromTraining(TrainingJob job, String modelId, float finalMap, float finalMap50) {
        try {
            Model model = new Model();
            model.setModelId(modelId);
            model.setModelName(job.getJobName()); // 使用任务名称作为模型名称
            model.setModelType(Model.ModelType.DETECTION);
            model.setFramework("PyTorch");
            model.setVersion("1.0.0");
            model.setParentModelId(job.getBaseModelId());
            model.setDatasetId(job.getDatasetId());
            model.setPtFilePath("s3://models/" + modelId + "/best.pt"); // S3 路径
            model.setMap(finalMap);   // mAP50-95
            model.setMap50(finalMap50); // mAP50
            model.setInputWidth(job.getImgSize());
            model.setInputHeight(job.getImgSize());
            model.setStatus(Model.ModelStatus.READY);
            model.setDeployedCount(0);
            model.setFileSizeBytes(0L); // 未知大小

            modelRepository.save(model);
            log.info("自动创建模型记录成功: modelId={}, modelName={}, mAP50={}", modelId, model.getModelName(), finalMap50);
        } catch (Exception e) {
            log.error("创建模型记录失败: modelId={}, error={}", modelId, e.getMessage(), e);
        }
    }

    /**
     * 从已完成的训练任务创建模型记录（供前端调用）
     */
    @Transactional
    public Map<String, Object> createModelFromTrainingJob(String jobId) {
        TrainingJob job = trainingJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("训练任务不存在: " + jobId));

        if (job.getStatus() != TrainingJob.TrainingStatus.COMPLETED) {
            throw new RuntimeException("只能从已完成的训练任务创建模型记录");
        }

        if (job.getOutputModelId() == null) {
            throw new RuntimeException("训练任务没有输出模型");
        }

        // 检查模型记录是否已存在
        if (modelRepository.existsById(job.getOutputModelId())) {
            // 已存在，直接返回
            Model existingModel = modelRepository.findById(job.getOutputModelId()).get();
            return Map.of(
                "modelId", existingModel.getModelId(),
                "modelName", existingModel.getModelName(),
                "message", "模型记录已存在"
            );
        }

        // 尝试从训练日志读取 map50
        float map50 = readMap50FromTrainingLogs(jobId);

        // 创建模型记录
        float finalMap = job.getFinalMap() != null ? job.getFinalMap() : 0f;
        createModelFromTraining(job, job.getOutputModelId(), finalMap, map50);

        return Map.of(
            "modelId", job.getOutputModelId(),
            "modelName", job.getJobName(),
            "message", "模型记录创建成功"
        );
    }

    /**
     * 从训练日志读取 mAP50 指标
     */
    private float readMap50FromTrainingLogs(String jobId) {
        try {
            String url = trainingServiceUrl + "/train/" + jobId + "/logs?lines=1";
            Map<String, Object> response = restTemplate.getForObject(url, Map.class);

            if (response != null && "success".equals(response.get("status"))) {
                @SuppressWarnings("unchecked")
                Map<String, Object> data = (Map<String, Object>) response.get("data");
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> logs = (List<Map<String, Object>>) data.get("logs");

                if (logs != null && !logs.isEmpty()) {
                    String message = (String) logs.get(0).get("message");
                    if (message != null) {
                        // 解析日志中的 mAP50 指标
                        // 格式: "Epoch 100/100: metrics/mAP50-95(B)=0.30598, metrics/mAP50(B)=0.55938"
                        if (message.contains("metrics/mAP50(B)=")) {
                            int startIdx = message.indexOf("metrics/mAP50(B)=") + 16;
                            int endIdx = message.indexOf(",", startIdx);
                            if (endIdx > startIdx) {
                                String map50Str = message.substring(startIdx, endIdx);
                                return Float.parseFloat(map50Str);
                            }
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.warn("从训练日志读取 mAP50 失败: jobId={}, error={}", jobId, e.getMessage());
        }

        // 默认值：如果没有找到 map50，使用 map * 1.8 作为估算
        return 0f; // 返回 0，让后续逻辑处理
    }

    /**
     * 获取训练任务详情
     */
    public TrainingJobDTO getTrainingJob(String jobId) {
        TrainingJob job = trainingJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("训练任务不存在: " + jobId));
        return toDTO(job);
    }

    /**
     * 分页查询训练任务
     */
    public Map<String, Object> listTrainingJobs(int page, int pageSize, TrainingJob.TrainingStatus status) {
        Pageable pageable = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "createdAt"));

        Page<TrainingJob> result;
        if (status != null) {
            result = trainingJobRepository.findByStatus(status, pageable);
        } else {
            result = trainingJobRepository.findAll(pageable);
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
     * 获取训练指标
     */
    public List<TrainingMetricDTO> getTrainingMetrics(String jobId) {
        List<TrainingMetric> metrics = trainingMetricRepository.findByJobIdOrderByEpoch(jobId);
        return metrics.stream()
                .map(this::metricToDTO)
                .collect(Collectors.toList());
    }

    /**
     * 删除训练任务
     */
    @Transactional
    public void deleteTrainingJob(String jobId) {
        TrainingJob job = trainingJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("训练任务不存在: " + jobId));

        if (job.getStatus() == TrainingJob.TrainingStatus.RUNNING) {
            throw new RuntimeException("无法删除运行中的任务");
        }

        // 删除训练指标
        trainingMetricRepository.deleteByJobId(jobId);

        // 删除任务
        trainingJobRepository.deleteById(jobId);
        log.info("训练任务已删除: jobId={}", jobId);
    }

    /**
     * 获取训练日志
     */
    public Map<String, Object> getTrainingLogs(String jobId, int lines) {
        TrainingJob job = trainingJobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("训练任务不存在: " + jobId));

        // 从训练服务获取日志
        try {
            String url = trainingServiceUrl + "/train/" + jobId + "/logs?tail=" + lines;
            Map<String, Object> response = restTemplate.getForObject(url, Map.class);

            if (response != null && "success".equals(response.get("status"))) {
                return response;
            } else {
                return Map.of("logs", List.of(), "message", "暂无日志");
            }
        } catch (Exception e) {
            log.warn("从训练服务获取日志失败: {}", e.getMessage());
            // 如果训练服务不可用，返回提示信息
            return Map.of(
                "logs", List.of(
                    Map.of(
                        "time", LocalDateTime.now().toString(),
                        "level", "INFO",
                        "message", "训练日志功能正在开发中，请通过 Docker 查看实时日志: docker logs edge_cloud_training"
                    )
                ),
                "message", "训练服务暂时不可用"
            );
        }
    }

    /**
     * 生成任务ID
     */
    private String generateJobId() {
        return "JOB" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
                + String.format("%04d", new Random().nextInt(10000));
    }

    /**
     * 转换为 DTO
     */
    private TrainingJobDTO toDTO(TrainingJob job) {
        TrainingJobDTO dto = new TrainingJobDTO();
        dto.setJobId(job.getJobId());
        dto.setJobName(job.getJobName());
        dto.setDatasetId(job.getDatasetId());
        dto.setDatasetSource(job.getDatasetSource());
        dto.setDatasetUrl(job.getDatasetUrl());
        dto.setDatasetPath(job.getDatasetPath());
        dto.setBaseModelId(job.getBaseModelId());
        dto.setBaseModel(job.getBaseModel());  // 设置预训练模型名称
        dto.setOutputModelId(job.getOutputModelId());
        dto.setEpochs(job.getEpochs());
        dto.setBatchSize(job.getBatchSize());
        dto.setImgSize(job.getImgSize());
        dto.setUseGpu(job.getUseGpu());
        dto.setTrainingType(job.getTrainingType());
        dto.setHyperparameters(job.getHyperparameters());
        dto.setStatus(job.getStatus());
        dto.setCurrentEpoch(job.getCurrentEpoch());
        dto.setProgress(job.getProgress());
        dto.setFinalMap(job.getFinalMap());
        dto.setFinalLoss(job.getFinalLoss());
        dto.setBestEpoch(job.getBestEpoch());
        dto.setMlflowRunId(job.getMlflowRunId());
        dto.setResume(job.getResume());
        dto.setResumeJobId(job.getResumeJobId());
        dto.setStartedAt(job.getStartedAt());
        dto.setCompletedAt(job.getCompletedAt());
        dto.setCreatedAt(job.getCreatedAt());
        dto.setUpdatedAt(job.getUpdatedAt());

        // 加载关联信息
        // 如果是 url/local 来源，使用自定义名称
        if ("url".equals(job.getDatasetSource()) || "local".equals(job.getDatasetSource())) {
            dto.setDatasetName(job.getDatasetName());
        } else if (job.getDatasetId() != null) {
            datasetRepository.findById(job.getDatasetId())
                    .ifPresent(d -> dto.setDatasetName(d.getDatasetName()));
        }

        if (job.getBaseModelId() != null) {
            modelRepository.findById(job.getBaseModelId())
                    .ifPresent(m -> dto.setBaseModelName(m.getModelName()));
        }

        if (job.getOutputModelId() != null) {
            modelRepository.findById(job.getOutputModelId())
                    .ifPresent(m -> dto.setOutputModelName(m.getModelName()));
        }

        return dto;
    }

    /**
     * 转换指标为 DTO
     */
    private TrainingMetricDTO metricToDTO(TrainingMetric metric) {
        TrainingMetricDTO dto = new TrainingMetricDTO();
        dto.setTime(metric.getTime());
        dto.setJobId(metric.getJobId());
        dto.setEpoch(metric.getEpoch());
        dto.setTrainLoss(metric.getTrainLoss());
        dto.setValLoss(metric.getValLoss());
        dto.setMap50(metric.getMap50());
        dto.setMap50_95(metric.getMap50_95());
        dto.setPrecision(metric.getPrecision());
        dto.setRecall(metric.getRecall());
        dto.setLearningRate(metric.getLearningRate());
        return dto;
    }

    /**
     * 获取任务的实际训练进度（从训练服务的 results.csv 读取）
     * 用于续训时获取原任务的实际训练轮次
     */
    public Map<String, Object> getActualProgress(String jobId) {
        try {
            String url = trainingServiceUrl + "/train/" + jobId + "/actual-progress";
            Map<String, Object> response = restTemplate.getForObject(url, Map.class);

            if (response != null && "success".equals(response.get("status"))) {
                @SuppressWarnings("unchecked")
                Map<String, Object> data = (Map<String, Object>) response.get("data");
                return data;
            } else {
                return Map.of("current_epoch", 0, "exists", false);
            }
        } catch (Exception e) {
            log.warn("从训练服务获取实际进度失败: jobId={}, error={}", jobId, e.getMessage());
            return Map.of("current_epoch", 0, "exists", false);
        }
    }
}
