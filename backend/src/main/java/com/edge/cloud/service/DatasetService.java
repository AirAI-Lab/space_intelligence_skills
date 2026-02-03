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
     * 上传数据集（支持文件上传和本地路径两种方式）
     */
    @Transactional
    public DatasetDTO uploadDataset(MultipartFile file, DatasetUploadRequest request) throws Exception {
        String datasetSource = request.getDatasetSource() != null ? request.getDatasetSource() : "upload";
        log.info("开始添加数据集: {}, 来源: {}", request.getDatasetName(), datasetSource);

        // 1. 生成数据集ID
        String datasetId = generateDatasetId();

        // 2. 创建数据集实体
        Dataset dataset = new Dataset();
        dataset.setDatasetId(datasetId);
        dataset.setDatasetName(request.getDatasetName());
        dataset.setDatasetType(request.getDatasetType());
        dataset.setFormat(request.getFormat());
        dataset.setDatasetSource(datasetSource);
        dataset.setStatus(Dataset.DatasetStatus.VALIDATING);

        // 3. 根据来源处理存储路径
        if ("local".equals(datasetSource)) {
            // 本地路径方式
            String localPath = request.getLocalPath();
            if (localPath == null || localPath.trim().isEmpty()) {
                throw new IllegalArgumentException("本地路径不能为空");
            }
            dataset.setStoragePath(localPath);
            dataset = datasetRepository.save(dataset);

            // 直接验证本地路径
            validateLocalDatasetAsync(dataset);

            log.info("本地数据集添加成功: datasetId={}, localPath={}", datasetId, localPath);
        } else {
            // 文件上传方式
            if (file == null || file.isEmpty()) {
                throw new IllegalArgumentException("上传文件不能为空");
            }
            log.info("上传文件大小: {} bytes", file.getSize());

            String storagePath = storageService.uploadFile(file, datasetStoragePrefix);
            dataset.setStoragePath(storagePath);
            dataset.setStatus(Dataset.DatasetStatus.UPLOADING);
            dataset = datasetRepository.save(dataset);

            // 解压并验证上传的数据集
            validateDatasetAsync(dataset);

            log.info("上传数据集添加成功: datasetId={}, storagePath={}", datasetId, storagePath);
        }

        return toDTO(dataset);
    }

    /**
     * 验证本地数据集（不需要解压）
     */
    @Transactional
    public void validateLocalDatasetAsync(Dataset dataset) {
        try {
            log.info("开始验证本地数据集: {}", dataset.getDatasetId());

            // 本地路径数据集需要加上基础路径
            Path datasetDir;
            if ("local".equals(dataset.getDatasetSource())) {
                String storagePath = dataset.getStoragePath();
                // 如果 storagePath 已经是完整路径，直接使用；否则添加基础路径
                if (storagePath.startsWith("/app/data/datasets/") || storagePath.startsWith("/app/data/datasets\\")) {
                    datasetDir = Paths.get(storagePath);
                } else {
                    datasetDir = Paths.get("/app/data/datasets", storagePath);
                }
            } else {
                datasetDir = Paths.get(dataset.getStoragePath());
            }

            log.info("验证数据集路径: {}", datasetDir);

            // 检查目录是否存在
            if (!Files.exists(datasetDir) || !Files.isDirectory(datasetDir)) {
                throw new IOException("数据集目录不存在: " + datasetDir);
            }

            // 验证并生成 data.yaml
            DatasetValidationResult validation = validateLocalDatasetYaml(datasetDir);

            // 更新数据集信息
            dataset.setCategoryCount(validation.categoryCount);
            dataset.setSampleCount(validation.totalSamples);
            dataset.setTrainCount(validation.trainSamples);
            dataset.setValCount(validation.valSamples);
            dataset.setTestCount(validation.testSamples);

            // 创建元数据
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("yaml_content", validation.yamlContent);
            metadata.put("yaml_valid", validation.yamlValid);
            metadata.put("yaml_errors", validation.yamlErrors);
            metadata.put("class_names", validation.classNames);
            metadata.put("directory_structure", validation.directoryStructure);
            metadata.put("validated_at", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
            metadata.put("is_local", true);
            dataset.setMetadata(metadata);

            dataset.setStatus(validation.isValid ? Dataset.DatasetStatus.READY : Dataset.DatasetStatus.ERROR);
            datasetRepository.save(dataset);

            log.info("本地数据集验证完成: datasetId={}, valid={}", dataset.getDatasetId(), validation.isValid);

        } catch (Exception e) {
            log.error("本地数据集验证失败: {}", dataset.getDatasetId(), e);
            dataset.setStatus(Dataset.DatasetStatus.ERROR);

            Map<String, Object> metadata = dataset.getMetadata() != null ? dataset.getMetadata() : new HashMap<>();
            metadata.put("error_message", e.getMessage());
            metadata.put("error_at", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
            dataset.setMetadata(metadata);

            datasetRepository.save(dataset);
        }
    }

    /**
     * 验证本地数据集的 YAML（不生成新文件，支持从标签文件解析类别）
     */
    private DatasetValidationResult validateLocalDatasetYaml(Path datasetDir) throws Exception {
        DatasetValidationResult result = new DatasetValidationResult();

        // 1. 检查目录结构 - 支持 val 和 valid 两种命名
        Path dataYamlPath = datasetDir.resolve("data.yaml");
        Path trainImages = datasetDir.resolve("train").resolve("images");
        Path trainLabels = datasetDir.resolve("train").resolve("labels");

        // 尝试 val 或 valid 目录
        Path valImages = datasetDir.resolve("val").resolve("images");
        Path valLabels = datasetDir.resolve("val").resolve("labels");
        Path validImages = datasetDir.resolve("valid").resolve("images");
        Path validLabels = datasetDir.resolve("valid").resolve("labels");

        // 测试集目录
        Path testImages = datasetDir.resolve("test").resolve("images");
        Path testLabels = datasetDir.resolve("test").resolve("labels");

        // 使用存在的验证集目录（优先 val，其次 valid）
        Path actualValImages = Files.exists(valImages) ? valImages : validImages;
        Path actualValLabels = Files.exists(valLabels) ? valLabels : validLabels;
        boolean useValid = !Files.exists(valImages) && Files.exists(validImages);

        // 记录目录结构
        Map<String, Object> structure = new HashMap<>();
        structure.put("has_data_yaml", Files.exists(dataYamlPath));
        structure.put("has_train_images", Files.exists(trainImages));
        structure.put("has_train_labels", Files.exists(trainLabels));
        structure.put("has_val_images", Files.exists(valImages));
        structure.put("has_val_labels", Files.exists(valLabels));
        structure.put("has_valid_images", Files.exists(validImages));
        structure.put("has_valid_labels", Files.exists(validLabels));
        structure.put("has_test_images", Files.exists(testImages));
        structure.put("has_test_labels", Files.exists(testLabels));
        structure.put("val_directory_name", useValid ? "valid" : "val");
        result.directoryStructure = structure;

        // 2. 统计样本数量
        if (Files.exists(trainImages)) {
            result.trainSamples = (int) Files.list(trainImages).count();
        }
        if (Files.exists(actualValImages)) {
            result.valSamples = (int) Files.list(actualValImages).count();
        }
        if (Files.exists(testImages)) {
            result.testSamples = (int) Files.list(testImages).count();
        }
        result.totalSamples = result.trainSamples + result.valSamples + result.testSamples;

        // 3. 处理 data.yaml
        if (Files.exists(dataYamlPath)) {
            // 读取并验证现有的 data.yaml
            String yamlContent = Files.readString(dataYamlPath);
            result.yamlContent = yamlContent;
            result = parseYamlContent(yamlContent, result);
        } else {
            // 尝试从标签文件解析类别信息
            result.yamlErrors.add("未找到 data.yaml 文件，尝试从标签文件解析类别");
            result = parseClassesFromLabels(trainLabels, actualValLabels, result);

            // 如果成功解析到类别，生成 yaml 内容
            if (result.classNames.size() > 0) {
                result.yamlContent = generateYamlContent(datasetDir, result);
                result.yamlValid = true;
                result.yamlErrors.add("已从标签文件解析到 " + result.classNames.size() + " 个类别");
            } else {
                result.yamlErrors.add("无法从标签文件解析类别，请手动创建 data.yaml");
                result.yamlValid = false;
            }
        }

        // 4. 验证是否有效
        if (result.isValid) {
            result.isValid = result.trainSamples > 0 && result.valSamples > 0;
        }

        return result;
    }

    /**
     * 从标签文件解析类别信息（支持 VisDrone 等格式）
     */
    private DatasetValidationResult parseClassesFromLabels(Path trainLabels, Path valLabels, DatasetValidationResult result) {
        try {
            Set<Integer> classIds = new HashSet<>();

            // 从训练标签解析
            if (Files.exists(trainLabels)) {
                try (var labelFiles = Files.list(trainLabels)) {
                    labelFiles.limit(100).forEach(labelFile -> {
                        try {
                            List<String> lines = Files.readAllLines(labelFile);
                            for (String line : lines) {
                                line = line.trim();
                                if (line.isEmpty()) continue;

                                // YOLO 格式: class_id x_center y_center width height
                                String[] parts = line.split("\\s+");
                                if (parts.length >= 5) {
                                    try {
                                        int classId = Integer.parseInt(parts[0]);
                                        classIds.add(classId);
                                    } catch (NumberFormatException e) {
                                        // 忽略非数字行
                                    }
                                }
                            }
                        } catch (IOException e) {
                            log.warn("读取标签文件失败: {}", labelFile);
                        }
                    });
                }
            }

            // 从验证标签解析
            if (Files.exists(valLabels)) {
                try (var labelFiles = Files.list(valLabels)) {
                    labelFiles.limit(100).forEach(labelFile -> {
                        try {
                            List<String> lines = Files.readAllLines(labelFile);
                            for (String line : lines) {
                                line = line.trim();
                                if (line.isEmpty()) continue;

                                String[] parts = line.split("\\s+");
                                if (parts.length >= 5) {
                                    try {
                                        int classId = Integer.parseInt(parts[0]);
                                        classIds.add(classId);
                                    } catch (NumberFormatException e) {
                                        // 忽略非数字行
                                    }
                                }
                            }
                        } catch (IOException e) {
                            log.warn("读取标签文件失败: {}", labelFile);
                        }
                    });
                }
            }

            // 转换为类别列表
            List<Integer> sortedIds = new ArrayList<>(classIds);
            Collections.sort(sortedIds);

            for (int classId : sortedIds) {
                result.classNames.add("class_" + classId);
            }
            result.categoryCount = sortedIds.size();

            log.info("从标签文件解析到 {} 个类别: {}", result.categoryCount, sortedIds);

        } catch (Exception e) {
            log.warn("从标签文件解析类别失败: {}", e.getMessage());
        }

        return result;
    }

    /**
     * 异步验证数据集
     */
    @Transactional
    public void validateDatasetAsync(Dataset dataset) {
        try {
            log.info("开始验证数据集: {}", dataset.getDatasetId());

            // 1. 获取并解压数据集文件
            Path datasetDir = extractDataset(dataset);

            // 2. 验证并生成 data.yaml
            DatasetValidationResult validation = validateAndGenerateYaml(datasetDir);

            // 3. 更新数据集信息
            dataset.setCategoryCount(validation.categoryCount);
            dataset.setSampleCount(validation.totalSamples);
            dataset.setTrainCount(validation.trainSamples);
            dataset.setValCount(validation.valSamples);
            dataset.setTestCount(validation.testSamples);

            // 4. 创建元数据（包含 YAML 内容和验证结果）
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("yaml_content", validation.yamlContent);
            metadata.put("yaml_valid", validation.yamlValid);
            metadata.put("yaml_errors", validation.yamlErrors);
            metadata.put("class_names", validation.classNames);
            metadata.put("directory_structure", validation.directoryStructure);
            metadata.put("validated_at", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
            metadata.put("extracted_path", datasetDir.toString());
            dataset.setMetadata(metadata);

            dataset.setStatus(validation.isValid ? Dataset.DatasetStatus.READY : Dataset.DatasetStatus.ERROR);
            datasetRepository.save(dataset);

            log.info("数据集验证完成: datasetId={}, valid={}", dataset.getDatasetId(), validation.isValid);

        } catch (Exception e) {
            log.error("数据集验证失败: {}", dataset.getDatasetId(), e);
            dataset.setStatus(Dataset.DatasetStatus.ERROR);

            // 保存错误信息到 metadata
            Map<String, Object> metadata = dataset.getMetadata() != null ? dataset.getMetadata() : new HashMap<>();
            metadata.put("error_message", e.getMessage());
            metadata.put("error_at", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
            dataset.setMetadata(metadata);

            datasetRepository.save(dataset);
        }
    }

    /**
     * 解压数据集文件
     */
    private Path extractDataset(Dataset dataset) throws Exception {
        String storagePath = dataset.getStoragePath();
        log.info("解压数据集: datasetId={}, storagePath={}", dataset.getDatasetId(), storagePath);

        // 从存储服务获取文件
        InputStream fileStream = storageService.getFile(storagePath);

        // 创建解压目录
        Path extractDir = Paths.get(datasetUploadPath, dataset.getDatasetId());
        Files.createDirectories(extractDir);

        // 解压文件
        try (ZipInputStream zis = new ZipInputStream(fileStream)) {
            ZipEntry entry;
            byte[] buffer = new byte[8192];

            while ((entry = zis.getNextEntry()) != null) {
                Path entryPath = extractDir.resolve(entry.getName());

                // 安全检查：防止 Zip Slip
                if (!entryPath.normalize().startsWith(extractDir.normalize())) {
                    throw new IOException("恶意 ZIP 文件: " + entry.getName());
                }

                if (entry.isDirectory()) {
                    Files.createDirectories(entryPath);
                } else {
                    Files.createDirectories(entryPath.getParent());
                    try (OutputStream os = Files.newOutputStream(entryPath)) {
                        int len;
                        while ((len = zis.read(buffer)) > 0) {
                            os.write(buffer, 0, len);
                        }
                    }
                }
                zis.closeEntry();
            }
        }

        log.info("数据集解压完成: {}", extractDir);
        return extractDir;
    }

    /**
     * 数据集验证结果
     */
    private static class DatasetValidationResult {
        boolean isValid = true;
        boolean yamlValid = false;
        String yamlContent = "";
        List<String> yamlErrors = new ArrayList<>();
        List<String> classNames = new ArrayList<>();
        int categoryCount = 0;
        int totalSamples = 0;
        int trainSamples = 0;
        int valSamples = 0;
        int testSamples = 0;
        Map<String, Object> directoryStructure = new HashMap<>();
    }

    /**
     * 验证数据集并生成/检查 data.yaml（支持从标签文件解析类别）
     */
    private DatasetValidationResult validateAndGenerateYaml(Path datasetDir) throws Exception {
        DatasetValidationResult result = new DatasetValidationResult();

        // 1. 检查目录结构 - 支持 val 和 valid 两种命名
        Path dataYamlPath = datasetDir.resolve("data.yaml");
        Path trainImages = datasetDir.resolve("train").resolve("images");
        Path trainLabels = datasetDir.resolve("train").resolve("labels");

        // 尝试 val 或 valid 目录
        Path valImages = datasetDir.resolve("val").resolve("images");
        Path valLabels = datasetDir.resolve("val").resolve("labels");
        Path validImages = datasetDir.resolve("valid").resolve("images");
        Path validLabels = datasetDir.resolve("valid").resolve("labels");

        // 测试集目录
        Path testImages = datasetDir.resolve("test").resolve("images");
        Path testLabels = datasetDir.resolve("test").resolve("labels");

        // 使用存在的验证集目录（优先 val，其次 valid）
        Path actualValImages = Files.exists(valImages) ? valImages : validImages;
        Path actualValLabels = Files.exists(valLabels) ? valLabels : validLabels;
        boolean useValid = !Files.exists(valImages) && Files.exists(validImages);

        // 记录目录结构
        Map<String, Object> structure = new HashMap<>();
        structure.put("has_data_yaml", Files.exists(dataYamlPath));
        structure.put("has_train_images", Files.exists(trainImages));
        structure.put("has_train_labels", Files.exists(trainLabels));
        structure.put("has_val_images", Files.exists(valImages));
        structure.put("has_val_labels", Files.exists(valLabels));
        structure.put("has_valid_images", Files.exists(validImages));
        structure.put("has_valid_labels", Files.exists(validLabels));
        structure.put("has_test_images", Files.exists(testImages));
        structure.put("has_test_labels", Files.exists(testLabels));
        structure.put("val_directory_name", useValid ? "valid" : "val");
        result.directoryStructure = structure;

        // 2. 统计样本数量
        if (Files.exists(trainImages)) {
            result.trainSamples = (int) Files.list(trainImages).count();
        }
        if (Files.exists(actualValImages)) {
            result.valSamples = (int) Files.list(actualValImages).count();
        }
        if (Files.exists(testImages)) {
            result.testSamples = (int) Files.list(testImages).count();
        }
        result.totalSamples = result.trainSamples + result.valSamples + result.testSamples;

        // 3. 处理 data.yaml
        if (Files.exists(dataYamlPath)) {
            // 读取并验证现有的 data.yaml
            String yamlContent = Files.readString(dataYamlPath);
            result.yamlContent = yamlContent;
            result = parseYamlContent(yamlContent, result);
        } else {
            // 尝试从标签文件解析类别信息
            result.yamlErrors.add("未找到 data.yaml 文件，尝试从标签文件解析类别");
            result = parseClassesFromLabels(trainLabels, actualValLabels, result);

            // 生成新的 data.yaml
            result.yamlContent = generateYamlContent(datasetDir, result);

            try {
                Files.writeString(dataYamlPath, result.yamlContent);
                result.yamlValid = true;
                result.yamlErrors.add("已自动生成 data.yaml 文件");
            } catch (Exception e) {
                result.yamlErrors.add("生成 data.yaml 失败: " + e.getMessage());
                result.isValid = false;
            }
        }

        // 4. 验证是否有效
        result.isValid = result.trainSamples > 0 && result.valSamples > 0
                     && (result.yamlValid || result.yamlContent != null && !result.yamlContent.isEmpty());

        return result;
    }

    /**
     * 解析 YAML 内容
     */
    private DatasetValidationResult parseYamlContent(String yamlContent, DatasetValidationResult result) {
        try {
            // 简单解析 YAML（按行解析）
            String[] lines = yamlContent.split("\n");
            boolean inNamesList = false;

            for (String line : lines) {
                line = line.trim();

                // 检查是否在 names 列表中
                if (line.startsWith("names:")) {
                    result.yamlValid = true;
                    // 检查是否是列表格式
                    if (line.contains("[")) {
                        inNamesList = true;
                        // 不 continue，因为列表内容可能在同一行
                    } else {
                        // 不是列表格式，可能是字典格式
                        continue;
                    }
                }

                // 解析列表格式的类别: names: ['class1', 'class2']
                if (inNamesList) {
                    // 提取单引号或双引号中的内容
                    java.util.regex.Pattern pattern = java.util.regex.Pattern.compile("['\"]([^'\"]+)['\"]");
                    java.util.regex.Matcher matcher = pattern.matcher(line);
                    while (matcher.find()) {
                        String className = matcher.group(1);
                        if (!className.isEmpty()) {
                            result.classNames.add(className);
                            result.categoryCount++;
                        }
                    }
                    // 列表结束
                    if (line.contains("]")) {
                        inNamesList = false;
                    }
                    continue;
                }

                // 解析字典格式的类别: "0: person"
                if (line.matches("\\d+:\\s*.+")) {
                    String[] parts = line.split(":", 2);
                    if (parts.length == 2) {
                        result.classNames.add(parts[1].trim().replaceAll("^['\"]|['\"]$", ""));
                        result.categoryCount++;
                    }
                }
            }

            if (!result.yamlValid) {
                result.yamlErrors.add("YAML 格式不完整：缺少 names 字段");
            }

        } catch (Exception e) {
            result.yamlErrors.add("解析 YAML 失败: " + e.getMessage());
            result.yamlValid = false;
        }
        return result;
    }

    /**
     * 生成 YAML 内容
     */
    private String generateYamlContent(Path datasetDir, DatasetValidationResult result) {
        // 从目录结构中获取验证集目录名（val 或 valid）
        String valDirName = "val";
        if (result.directoryStructure != null && result.directoryStructure.containsKey("val_directory_name")) {
            valDirName = (String) result.directoryStructure.get("val_directory_name");
        }

        StringBuilder yaml = new StringBuilder();
        yaml.append("# YOLOv5/v8 数据集配置文件\n");
        yaml.append("# 自动生成于: ").append(LocalDateTime.now()).append("\n\n");
        yaml.append("path: ").append(datasetDir.toAbsolutePath()).append("\n");
        yaml.append("train: train/images\n");
        yaml.append("val: ").append(valDirName).append("/images\n");
        yaml.append("test: test/images  # 可选\n\n");

        // 类别数量
        yaml.append("nc: ").append(result.categoryCount > 0 ? result.categoryCount : 1).append("\n");

        // 类别名称
        yaml.append("names: ");
        if (!result.classNames.isEmpty()) {
            yaml.append("[");
            for (int i = 0; i < result.classNames.size(); i++) {
                if (i > 0) yaml.append(", ");
                yaml.append("'").append(result.classNames.get(i)).append("'");
            }
            yaml.append("]\n");
        } else {
            yaml.append("['class_0']  # 请根据实际情况修改\n");
        }

        return yaml.toString();
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
        dto.setDatasetSource(dataset.getDatasetSource());
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
