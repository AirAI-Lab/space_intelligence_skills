package com.edge.cloud.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import jakarta.annotation.PostConstruct;
import java.io.InputStream;
import java.util.List;

/**
 * 存储服务门面（根据配置选择本地或S3存储）
 */
@Slf4j
@Service
@Primary
public class StorageServiceFacade implements StorageService {

    private final LocalStorageService localStorageService;
    private final S3StorageService s3StorageService;

    @Value("${FILE_STORAGE_TYPE:local}")
    private String storageType;

    private StorageService activeStorageService;

    public StorageServiceFacade(LocalStorageService localStorageService,
                                S3StorageService s3StorageService) {
        this.localStorageService = localStorageService;
        this.s3StorageService = s3StorageService;
    }

    @PostConstruct
    public void init() {
        // 根据配置选择存储服务
        if ("s3".equals(storageType)) {
            activeStorageService = s3StorageService;
        } else {
            activeStorageService = localStorageService;
        }
        log.info("存储服务初始化完成: type={}, implementation={}",
                 storageType, activeStorageService.getClass().getSimpleName());
    }

    @Override
    public String uploadFile(MultipartFile file, String category) throws Exception {
        return activeStorageService.uploadFile(file, category);
    }

    @Override
    public List<String> uploadFiles(MultipartFile[] files, String category) throws Exception {
        return activeStorageService.uploadFiles(files, category);
    }

    @Override
    public boolean deleteFile(String fileIdentifier) {
        return activeStorageService.deleteFile(fileIdentifier);
    }

    @Override
    public InputStream getFile(String fileIdentifier) {
        return activeStorageService.getFile(fileIdentifier);
    }

    @Override
    public String getFileUrl(String fileIdentifier) {
        return activeStorageService.getFileUrl(fileIdentifier);
    }

    @Override
    public List<?> listFiles(String category) throws Exception {
        return activeStorageService.listFiles(category);
    }

    @Override
    public boolean exists(String fileIdentifier) {
        return activeStorageService.exists(fileIdentifier);
    }

    @Override
    public String getStorageType() {
        return activeStorageService.getStorageType();
    }
}
