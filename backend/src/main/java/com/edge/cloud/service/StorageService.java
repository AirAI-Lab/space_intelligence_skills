package com.edge.cloud.service;

import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.util.List;

/**
 * 存储服务接口
 * 支持多种存储后端：本地存储、S3（SeaweedFS/阿里云OSS/腾讯云COS）
 */
public interface StorageService {

    /**
     * 上传文件
     * @param file 文件
     * @param category 分类（如：models、datasets、logs）
     * @return 文件标识符（本地为路径，S3为key）
     */
    String uploadFile(MultipartFile file, String category) throws Exception;

    /**
     * 批量上传文件
     */
    List<String> uploadFiles(MultipartFile[] files, String category) throws Exception;

    /**
     * 删除文件
     */
    boolean deleteFile(String fileIdentifier);

    /**
     * 获取文件流
     */
    InputStream getFile(String fileIdentifier);

    /**
     * 获取文件访问URL
     */
    String getFileUrl(String fileIdentifier);

    /**
     * 列出指定分类下的文件
     */
    List<?> listFiles(String category) throws Exception;

    /**
     * 检查文件是否存在
     */
    boolean exists(String fileIdentifier);

    /**
     * 获取存储类型
     */
    String getStorageType();
}
