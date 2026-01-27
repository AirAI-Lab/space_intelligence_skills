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
        log.info("创建训练任务: {}", request.getJobName());

        // 验证数据集存在
        Dataset dataset = datasetRepository.findById(request.getDatasetId())
                .orElseThrow(() -> new RuntimeException("数据集不存在: " + request.getDatasetId()));

        if (dataset.getStatus() != Dataset.DatasetStatus.READY) {
            throw new RuntimeException("数据集未就绪: " + dataset.getStatus());
        }

        // 验证基础模型存在（如果是微调）
        if (request.getBaseModelId() != null) {
            Model baseModel = modelRepository.findById(request.getBaseModelId())
                    .orElseThrow(() -> new RuntimeException("基础模型不存在: " + request.getBaseModelId()));
        }

        // 生成任务ID
        String jobId = generateJobId();

        // 创建训练任务实体
        TrainingJob job = new TrainingJob();
        job.setJobId(jobId);
        job.setJobName(request.getJobName());
        job.setDatasetId(request.getDatasetId());
        job.setBaseModelId(request.getBaseModelId());
        job.setEpochs(request.getEpochs());
        job.setBatchSize(request.getBatchSize());
        job.setImgSize(request.getImgSize());
        job.setUseGpu(request.getUseGpu());
        job.setTrainingType(request.getTrainingType() != null ? request.getTrainingType() : TrainingJob.TrainingType.FULL_TRAINING);
        job.setHyperparameters(request.getHyperparameters());
        job.setStatus(TrainingJob.TrainingStatus.PENDING);
        job.setCurrentEpoch(0);
        job.setProgress(0.0f);

        // 保存到数据库
        job = trainingJobRepository.save(job);
        log.info("训练任务创建成功: jobId={}", jobId);

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

            // 调用训练服务启动训练
            Map<String, Object> trainingRequest = new HashMap<>();
            trainingRequest.put("job_id", jobId);
            trainingRequest.put("dataset_id", job.getDatasetId());
            trainingRequest.put("epochs", job.getEpochs());
            trainingRequest.put("batch_size", job.getBatchSize());
            trainingRequest.put("img_size", job.getImgSize());
            trainingRequest.put("use_gpu", job.getUseGpu());
            trainingRequest.put("base_model", job.getBaseModelId());
            trainingRequest.put("hyperparameters", job.getHyperparameters());

            // TODO: 调用 Python 训练服务 API
            // restTemplate.postForEntity(trainingServiceUrl + "/train", trainingRequest, String.class);

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
            // TODO: 调用训练服务停止训练
            // restTemplate.postForEntity(trainingServiceUrl + "/train/" + jobId + "/stop", null, String.class);

            job.setStatus(TrainingJob.TrainingStatus.CANCELLED);
            job.setCompletedAt(LocalDateTime.now());
            trainingJobRepository.save(job);

            log.info("训练任务已停止: jobId={}", jobId);
            return toDTO(job);

        } catch (Exception e) {
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
    public void completeTraining(String jobId, String outputModelId, float finalMap, float finalLoss, int bestEpoch) {
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

        log.info("训练完成: jobId={}, outputModel={}, mAP={}", jobId, outputModelId, finalMap);
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
        dto.setBaseModelId(job.getBaseModelId());
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
        dto.setStartedAt(job.getStartedAt());
        dto.setCompletedAt(job.getCompletedAt());
        dto.setCreatedAt(job.getCreatedAt());
        dto.setUpdatedAt(job.getUpdatedAt());

        // 加载关联信息
        if (job.getDatasetId() != null) {
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
}
