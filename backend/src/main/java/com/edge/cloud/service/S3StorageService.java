package com.edge.cloud.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.*;
import software.amazon.awssdk.core.sync.RequestBody;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * S3 存储服务（支持 SeaweedFS、阿里云OSS、腾讯云COS等）
 * 使用 Apache 2.0 协议的 AWS SDK，商业化友好
 */
@Slf4j
@Component
public class S3StorageService implements StorageService {

    private S3Client s3Client;

    @Value("${S3_ENDPOINT:#{null}}")
    private String endpoint;

    @Value("${S3_ACCESS_KEY:admin}")
    private String accessKey;

    @Value("${S3_SECRET_KEY:admin}")
    private String secretKey;

    @Value("${S3_BUCKET:edge-cloud-files}")
    private String bucketName;

    @Value("${file.storage.s3.region:us-east-1}")
    private String region;

    @Value("${S3_PATH_STYLE_ACCESS:true}")
    private boolean pathStyleAccess;

    @PostConstruct
    public void init() {
        try {
            var credentials = AwsBasicCredentials.create(accessKey, secretKey);

            s3Client = S3Client.builder()
                    .endpointOverride(new java.net.URI(endpoint))
                    .credentialsProvider(StaticCredentialsProvider.create(credentials))
                    .region(Region.of(region))
                    .serviceConfiguration(b -> b
                            .pathStyleAccessEnabled(pathStyleAccess)
                            .chunkedEncodingEnabled(false))
                    .build();

            // 创建bucket（如果不存在）
            ensureBucketExists();

            log.info("S3存储服务初始化成功: endpoint={}, bucket={}", endpoint, bucketName);
        } catch (Exception e) {
            log.error("S3存储服务初始化失败", e);
            throw new RuntimeException("S3存储服务初始化失败: " + e.getMessage(), e);
        }
    }

    @PreDestroy
    public void destroy() {
        if (s3Client != null) {
            s3Client.close();
        }
    }

    /**
     * 上传文件
     */
    public String uploadFile(MultipartFile file, String category) throws IOException {
        String fileName = generateFileName(file.getOriginalFilename());
        String key = category + "/" + fileName;

        try {
            PutObjectRequest putRequest = PutObjectRequest.builder()
                    .bucket(bucketName)
                    .key(key)
                    .contentType(file.getContentType())
                    .contentLength(file.getSize())
                    .build();

            s3Client.putObject(putRequest,
                RequestBody.fromInputStream(file.getInputStream(), file.getSize()));

            log.info("文件上传成功: bucket={}, key={}", bucketName, key);
            return key;
        } catch (Exception e) {
            log.error("文件上传失败: {}", key, e);
            throw new IOException("文件上传失败: " + e.getMessage(), e);
        }
    }

    /**
     * 批量上传文件
     */
    public List<String> uploadFiles(MultipartFile[] files, String category) throws IOException {
        List<String> keys = new ArrayList<>();
        for (MultipartFile file : files) {
            keys.add(uploadFile(file, category));
        }
        return keys;
    }

    /**
     * 删除文件
     */
    public boolean deleteFile(String key) {
        try {
            DeleteObjectRequest deleteRequest = DeleteObjectRequest.builder()
                    .bucket(bucketName)
                    .key(key)
                    .build();

            s3Client.deleteObject(deleteRequest);
            log.info("文件删除成功: bucket={}, key={}", bucketName, key);
            return true;
        } catch (Exception e) {
            log.error("文件删除失败: {}", key, e);
            return false;
        }
    }

    /**
     * 获取文件流
     */
    public InputStream getFile(String key) {
        try {
            GetObjectRequest getRequest = GetObjectRequest.builder()
                    .bucket(bucketName)
                    .key(key)
                    .build();

            return s3Client.getObject(getRequest);
        } catch (Exception e) {
            // 文件不存在时返回 null，而不是抛出异常
            // 这样调用者可以实现回退机制
            String errorMessage = e.getMessage();
            if (errorMessage != null && errorMessage.contains("404")) {
                log.warn("S3 文件不存在: {}", key);
                return null;
            }
            // 其他错误（如网络问题）仍然抛出异常
            log.error("获取 S3 文件失败: {}", key, e);
            throw new RuntimeException("获取文件失败: " + e.getMessage(), e);
        }
    }

    /**
     * 获取文件URL（用于前端访问）
     */
    public String getFileUrl(String key) {
        // 返回通过后端代理的URL
        return "/api/v1/files/download?key=" + key;
    }

    /**
     * 列出目录下的文件
     */
    public List<S3ObjectInfo> listFiles(String category) {
        try {
            ListObjectsV2Request listRequest = ListObjectsV2Request.builder()
                    .bucket(bucketName)
                    .prefix(category + "/")
                    .build();

            ListObjectsV2Response response = s3Client.listObjectsV2(listRequest);

            List<S3ObjectInfo> files = new ArrayList<>();
            for (S3Object object : response.contents()) {
                files.add(new S3ObjectInfo(
                    object.key(),
                    object.size(),
                    object.lastModified()
                ));
            }

            return files;
        } catch (Exception e) {
            log.error("列出文件失败: {}", category, e);
            return new ArrayList<>();
        }
    }

    /**
     * 检查文件是否存在
     */
    public boolean exists(String key) {
        try {
            HeadObjectRequest headRequest = HeadObjectRequest.builder()
                    .bucket(bucketName)
                    .key(key)
                    .build();

            s3Client.headObject(headRequest);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * 确保bucket存在
     */
    private void ensureBucketExists() {
        try {
            // 检查bucket是否存在
            HeadBucketRequest headBucketRequest = HeadBucketRequest.builder()
                    .bucket(bucketName)
                    .build();

            s3Client.headBucket(headBucketRequest);
            log.info("Bucket已存在: {}", bucketName);
        } catch (Exception e) {
            // Bucket不存在，创建它
            try {
                CreateBucketRequest createBucketRequest = CreateBucketRequest.builder()
                        .bucket(bucketName)
                        .build();

                s3Client.createBucket(createBucketRequest);
                log.info("Bucket创建成功: {}", bucketName);
            } catch (Exception ex) {
                log.error("创建Bucket失败: {}", bucketName, ex);
                throw new RuntimeException("创建Bucket失败: " + ex.getMessage(), ex);
            }
        }
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

    @Override
    public String uploadBytes(byte[] data, String category, String contentType) throws Exception {
        String fileName = UUID.randomUUID().toString() + ".jpg";
        String key = category + "/" + fileName;
        PutObjectRequest putRequest = PutObjectRequest.builder()
                .bucket(bucketName)
                .key(key)
                .contentType(contentType)
                .contentLength((long) data.length)
                .build();
        s3Client.putObject(putRequest, RequestBody.fromBytes(data));
        log.info("字节数据上传成功: key={}, size={}", key, data.length);
        return key;
    }

    @Override
    public String getStorageType() {
        return "s3";
    }

    /**
     * S3对象信息
     */
    public record S3ObjectInfo(
        String key,
        long size,
        java.time.Instant lastModified
    ) {}
}
