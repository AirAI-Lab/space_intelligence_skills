package com.edge.cloud.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * 文件存储服务
 * 支持本地存储和云存储（阿里云OSS/腾讯云COS）
 * 完全自主知识产权，无AGPL限制
 */
@Service
public class FileStorageService {

    @Value("${file.storage.type:local}")
    private String storageType;

    @Value("${file.storage.path:/app/data/files}")
    private String storagePath;

    // 云存储配置（预留，后期可选启用）
    @Value("${file.storage.oss.endpoint:#{null}}")
    private String ossEndpoint;

    @Value("${file.storage.oss.accessKey:#{null}}")
    private String ossAccessKey;

    @Value("${file.storage.oss.secretKey:#{null}}")
    private String ossSecretKey;

    @Value("${file.storage.oss.bucket:#{null}}")
    private String ossBucket;

    /**
     * 上传文件
     */
    public String uploadFile(MultipartFile file, String category) throws IOException {
        String fileName = generateFileName(file.getOriginalFilename());
        Path targetPath = Paths.get(storagePath, category, fileName);

        // 确保目录存在
        Files.createDirectories(targetPath.getParent());

        // 保存文件
        Files.copy(file.getInputStream(), targetPath, StandardCopyOption.REPLACE_EXISTING);

        return targetPath.toString();
    }

    /**
     * 批量上传文件
     */
    public List<String> uploadFiles(MultipartFile[] files, String category) throws IOException {
        List<String> paths = new ArrayList<>();
        for (MultipartFile file : files) {
            paths.add(uploadFile(file, category));
        }
        return paths;
    }

    /**
     * 删除文件
     */
    public boolean deleteFile(String filePath) {
        try {
            Path path = Paths.get(filePath);
            return Files.deleteIfExists(path);
        } catch (IOException e) {
            return false;
        }
    }

    /**
     * 获取文件
     */
    public Path getFile(String filePath) {
        return Paths.get(filePath);
    }

    /**
     * 获取文件URL（用于前端访问）
     */
    public String getFileUrl(String filePath) {
        // 本地存储返回相对路径
        if ("local".equals(storageType)) {
            return "/api/v1/files/download?path=" + filePath;
        }
        // 云存储返回云端URL（后期实现）
        return filePath;
    }

    /**
     * 列出目录下的文件
     */
    public List<String> listFiles(String category) throws IOException {
        Path dirPath = Paths.get(storagePath, category);
        if (!Files.exists(dirPath)) {
            return new ArrayList<>();
        }
        return Files.list(dirPath)
                .filter(Files::isRegularFile)
                .map(Path::toString)
                .toList();
    }

    /**
     * 生成唯一文件名
     */
    private String generateFileName(String originalFileName) {
        String extension = "";
        if (originalFileName != null && originalFileName.contains(".")) {
            extension = originalFileName.substring(originalFileName.lastIndexOf("."));
        }
        return UUID.randomUUID().toString() + extension;
    }

    /**
     * 获取存储类型
     */
    public String getStorageType() {
        return storageType;
    }

    /**
     * 检查是否配置了云存储
     */
    public boolean isCloudStorageEnabled() {
        return ossEndpoint != null && !ossEndpoint.isEmpty();
    }
}
