package com.edge.cloud.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.stream.Stream;

/**
 * 本地存储服务实现
 */
@Slf4j
@Component
public class LocalStorageService implements StorageService {

    @Value("${FILE_STORAGE_PATH:/app/data/files}")
    private String storagePath;

    @PostConstruct
    public void init() {
        try {
            Path path = Paths.get(storagePath);
            Files.createDirectories(path);
            log.info("本地存储服务初始化成功: path={}", storagePath);
        } catch (IOException e) {
            log.error("本地存储服务初始化失败", e);
            throw new RuntimeException("本地存储服务初始化失败: " + e.getMessage(), e);
        }
    }

    @Override
    public String uploadFile(MultipartFile file, String category) throws IOException {
        String fileName = generateFileName(file.getOriginalFilename());
        Path targetPath = Paths.get(storagePath, category, fileName);

        // 确保目录存在
        Files.createDirectories(targetPath.getParent());

        // 保存文件
        Files.copy(file.getInputStream(), targetPath, StandardCopyOption.REPLACE_EXISTING);

        log.info("文件上传成功: path={}", targetPath);
        return targetPath.toString();
    }

    @Override
    public List<String> uploadFiles(MultipartFile[] files, String category) throws IOException {
        List<String> paths = new ArrayList<>();
        for (MultipartFile file : files) {
            paths.add(uploadFile(file, category));
        }
        return paths;
    }

    @Override
    public boolean deleteFile(String fileIdentifier) {
        try {
            Path path = Paths.get(fileIdentifier);
            boolean deleted = Files.deleteIfExists(path);
            log.info("文件删除: path={}, result={}", fileIdentifier, deleted);
            return deleted;
        } catch (IOException e) {
            log.error("文件删除失败: {}", fileIdentifier, e);
            return false;
        }
    }

    @Override
    public InputStream getFile(String fileIdentifier) {
        try {
            Path path = Paths.get(fileIdentifier);
            return Files.newInputStream(path);
        } catch (IOException e) {
            log.error("获取文件失败: {}", fileIdentifier, e);
            throw new RuntimeException("获取文件失败: " + e.getMessage(), e);
        }
    }

    @Override
    public String getFileUrl(String fileIdentifier) {
        // 本地存储返回通过后端代理的URL
        return "/api/v1/files/download?path=" + fileIdentifier;
    }

    @Override
    public List<LocalFileInfo> listFiles(String category) throws IOException {
        Path dirPath = Paths.get(storagePath, category);
        if (!Files.exists(dirPath)) {
            return new ArrayList<>();
        }

        List<LocalFileInfo> files = new ArrayList<>();
        try (Stream<Path> paths = Files.list(dirPath)) {
            paths.filter(Files::isRegularFile)
                  .forEach(path -> {
                      try {
                          files.add(new LocalFileInfo(
                              path.toString(),
                              path.getFileName().toString(),
                              Files.size(path),
                              Files.getLastModifiedTime(path).toMillis()
                          ));
                      } catch (IOException e) {
                          log.error("获取文件信息失败: {}", path, e);
                      }
                  });
        }

        return files;
    }

    @Override
    public boolean exists(String fileIdentifier) {
        return Files.exists(Paths.get(fileIdentifier));
    }

    @Override
    public String uploadBytes(byte[] data, String category, String contentType) throws Exception {
        String fileName = UUID.randomUUID().toString() + ".jpg";
        Path targetPath = Paths.get(storagePath, category, fileName);
        Files.createDirectories(targetPath.getParent());
        Files.write(targetPath, data);
        log.info("字节数据上传成功: path={}, size={}", targetPath, data.length);
        return targetPath.toString();
    }

    @Override
    public String getStorageType() {
        return "local";
    }

    private String generateFileName(String originalFileName) {
        String extension = "";
        if (originalFileName != null && originalFileName.contains(".")) {
            extension = originalFileName.substring(originalFileName.lastIndexOf("."));
        }
        return UUID.randomUUID().toString() + extension;
    }

    public record LocalFileInfo(
        String path,
        String name,
        long size,
        long lastModified
    ) {}
}
