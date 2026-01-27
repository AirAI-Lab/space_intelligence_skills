package com.edge.cloud.service;

import com.edge.cloud.dto.DatasetDTO;
import com.edge.cloud.dto.DatasetUploadRequest;
import com.edge.cloud.entity.Dataset;
import com.edge.cloud.repository.DatasetRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * 数据集管理服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DatasetService {

    private final DatasetRepository datasetRepository;
    private final StorageService storageService;

    @Value("${DATASET_UPLOAD_PATH:/tmp/datasets}")
    private String datasetUploadPath;

    @Value("${DATASET_STORAGE_PREFIX:datasets}")
    private String datasetStoragePrefix;

    /**
     * 上传数据集
     */
    @Transactional
    public DatasetDTO uploadDataset(MultipartFile file, DatasetUploadRequest request) throws Exception {
        log.info("开始上传数据集: {}, 文件大小: {} bytes", request.getDatasetName(), file.getSize());

        // 1. 生成数据集ID
        String datasetId = generateDatasetId();

        // 2. 上传文件到存储
        String storagePath = storageService.uploadFile(file, datasetStoragePrefix);

        // 3. 创建数据集实体
        Dataset dataset = new Dataset();
        dataset.setDatasetId(datasetId);
        dataset.setDatasetName(request.getDatasetName());
        dataset.setDatasetType(request.getDatasetType());
        dataset.setFormat(request.getFormat());
        dataset.setStoragePath(storagePath);
        dataset.setStatus(Dataset.DatasetStatus.UPLOADING);

        // 4. 保存到数据库
        dataset = datasetRepository.save(dataset);

        // 5. 异步验证数据集格式
        validateDatasetAsync(dataset);

        log.info("数据集上传成功: datasetId={}, storagePath={}", datasetId, storagePath);
        return toDTO(dataset);
    }

    /**
     * 异步验证数据集
     */
    @Transactional
    public void validateDatasetAsync(Dataset dataset) {
        try {
            log.info("开始验证数据集: {}", dataset.getDatasetId());

            // TODO: 下载并解压数据集文件
            // TODO: 验证 YOLO 格式 (images/*.jpg, labels/*.txt, data.yaml)
            // TODO: 统计样本数量、类别数量
            // TODO: 划分 train/val/test

            // 模拟验证结果
            dataset.setCategoryCount(5);
            dataset.setSampleCount(15000);
            dataset.setTrainCount(12000);
            dataset.setValCount(2500);
            dataset.setTestCount(500);
            dataset.setStatus(Dataset.DatasetStatus.READY);

            // 创建元数据
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("class_names", Arrays.asList("person", "helmet", "reflective_vest", "head", "no_vest"));
            metadata.put("validated_at", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
            dataset.setMetadata(metadata);

            datasetRepository.save(dataset);
            log.info("数据集验证完成: {}", dataset.getDatasetId());

        } catch (Exception e) {
            log.error("数据集验证失败: {}", dataset.getDatasetId(), e);
            dataset.setStatus(Dataset.DatasetStatus.ERROR);
            datasetRepository.save(dataset);
        }
    }

    /**
     * 手动触发数据集验证
     */
    @Transactional
    public DatasetDTO validateDataset(String datasetId) {
        Dataset dataset = datasetRepository.findById(datasetId)
                .orElseThrow(() -> new RuntimeException("数据集不存在: " + datasetId));

        validateDatasetAsync(dataset);
        return toDTO(dataset);
    }

    /**
     * 获取数据集详情
     */
    public DatasetDTO getDataset(String datasetId) {
        Dataset dataset = datasetRepository.findById(datasetId)
                .orElseThrow(() -> new RuntimeException("数据集不存在: " + datasetId));
        return toDTO(dataset);
    }

    /**
     * 分页查询数据集
     */
    public Map<String, Object> listDatasets(int page, int pageSize, String search, Dataset.DatasetStatus status) {
        Pageable pageable = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "createdAt"));

        Page<Dataset> result;
        if (status != null) {
            result = datasetRepository.findByStatus(status, pageable);
        } else {
            result = datasetRepository.findAll(pageable);
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
     * 删除数据集
     */
    @Transactional
    public void deleteDataset(String datasetId) {
        Dataset dataset = datasetRepository.findById(datasetId)
                .orElseThrow(() -> new RuntimeException("数据集不存在: " + datasetId));

        // 删除存储文件
        if (dataset.getStoragePath() != null) {
            storageService.deleteFile(dataset.getStoragePath());
        }

        // 删除数据库记录
        datasetRepository.deleteById(datasetId);
        log.info("数据集已删除: {}", datasetId);
    }

    /**
     * 获取可用的数据集（用于训练）
     */
    public List<DatasetDTO> getAvailableDatasets() {
        return datasetRepository.findAvailableDatasets().stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    /**
     * 统计数据集信息
     */
    public Map<String, Object> getStatistics() {
        Map<String, Object> stats = new HashMap<>();

        long total = datasetRepository.count();
        long ready = datasetRepository.findByStatus(Dataset.DatasetStatus.READY, Pageable.unpaged()).getTotalElements();

        stats.put("total", total);
        stats.put("ready", ready);
        stats.put("uploading", total - ready);

        return stats;
    }

    /**
     * 生成数据集ID
     */
    private String generateDatasetId() {
        return "DS" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
                + String.format("%04d", new Random().nextInt(10000));
    }

    /**
     * 转换为 DTO
     */
    private DatasetDTO toDTO(Dataset dataset) {
        DatasetDTO dto = new DatasetDTO();
        dto.setDatasetId(dataset.getDatasetId());
        dto.setDatasetName(dataset.getDatasetName());
        dto.setDatasetType(dataset.getDatasetType());
        dto.setFormat(dataset.getFormat());
        dto.setStoragePath(dataset.getStoragePath());
        dto.setCategoryCount(dataset.getCategoryCount());
        dto.setSampleCount(dataset.getSampleCount());
        dto.setTrainCount(dataset.getTrainCount());
        dto.setValCount(dataset.getValCount());
        dto.setTestCount(dataset.getTestCount());
        dto.setStatus(dataset.getStatus());
        dto.setMetadata(dataset.getMetadata());
        dto.setCreatedAt(dataset.getCreatedAt());
        dto.setUpdatedAt(dataset.getUpdatedAt());
        return dto;
    }
}
