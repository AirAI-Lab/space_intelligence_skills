package com.edge.cloud.controller;

import com.edge.cloud.service.StorageService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.InputStreamResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 文件管理控制器
 * 提供文件上传、下载、删除、列表等功能
 * 支持本地存储和 S3 存储（SeaweedFS/阿里云OSS/腾讯云COS）
 */
@Tag(name = "文件管理", description = "文件上传下载管理")
@RestController
@RequestMapping("/api/v1/files")
@RequiredArgsConstructor
public class FileController {

    private final StorageService storageService;

    @Operation(summary = "上传文件")
    @PostMapping("/upload")
    public ResponseEntity<Map<String, Object>> uploadFile(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "category", defaultValue = "general") String category) {
        Map<String, Object> result = new HashMap<>();
        try {
            String fileIdentifier = storageService.uploadFile(file, category);
            result.put("success", true);
            result.put("identifier", fileIdentifier);
            result.put("url", storageService.getFileUrl(fileIdentifier));
            result.put("category", category);
            result.put("storageType", storageService.getStorageType());
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            result.put("success", false);
            result.put("error", e.getMessage());
            return ResponseEntity.internalServerError().body(result);
        }
    }

    @Operation(summary = "批量上传文件")
    @PostMapping("/upload/batch")
    public ResponseEntity<Map<String, Object>> uploadFiles(
            @RequestParam("files") MultipartFile[] files,
            @RequestParam(value = "category", defaultValue = "general") String category) {
        Map<String, Object> result = new HashMap<>();
        try {
            List<String> identifiers = storageService.uploadFiles(files, category);
            result.put("success", true);
            result.put("identifiers", identifiers);
            result.put("count", identifiers.size());
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            result.put("success", false);
            result.put("error", e.getMessage());
            return ResponseEntity.internalServerError().body(result);
        }
    }

    @Operation(summary = "下载文件（本地存储路径）")
    @GetMapping("/download")
    public ResponseEntity<Resource> downloadFile(@RequestParam("path") String path) {
        try {
            Path filePath = Path.of(path);
            if (!Files.exists(filePath)) {
                return ResponseEntity.notFound().build();
            }

            Resource resource = new InputStreamResource(Files.newInputStream(filePath));
            String contentType = Files.probeContentType(filePath);
            if (contentType == null) {
                contentType = "application/octet-stream";
            }

            return ResponseEntity.ok()
                    .contentType(MediaType.parseMediaType(contentType))
                    .header(HttpHeaders.CONTENT_DISPOSITION,
                            "attachment; filename=\"" + filePath.getFileName().toString() + "\"")
                    .body(resource);
        } catch (IOException e) {
            return ResponseEntity.internalServerError().build();
        }
    }

    @Operation(summary = "下载文件（S3存储key）")
    @GetMapping("/download/s3")
    public ResponseEntity<Resource> downloadS3File(@RequestParam("key") String key) {
        try {
            InputStream inputStream = storageService.getFile(key);
            Resource resource = new InputStreamResource(inputStream);

            String fileName = key.substring(key.lastIndexOf("/") + 1);

            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_OCTET_STREAM)
                    .header(HttpHeaders.CONTENT_DISPOSITION,
                            "attachment; filename=\"" + fileName + "\"")
                    .body(resource);
        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }

    @Operation(summary = "删除文件")
    @DeleteMapping("/delete")
    public ResponseEntity<Map<String, Object>> deleteFile(
            @RequestParam(value = "path", required = false) String path,
            @RequestParam(value = "key", required = false) String key) {
        Map<String, Object> result = new HashMap<>();

        // 优先使用 key，其次使用 path
        String identifier = key != null ? key : path;

        if (identifier == null) {
            result.put("success", false);
            result.put("error", "必须提供 path 或 key 参数");
            return ResponseEntity.badRequest().body(result);
        }

        boolean deleted = storageService.deleteFile(identifier);
        result.put("success", deleted);
        return ResponseEntity.ok(result);
    }

    @Operation(summary = "列出文件")
    @GetMapping("/list")
    public ResponseEntity<Map<String, Object>> listFiles(
            @RequestParam(value = "category", defaultValue = "general") String category) {
        Map<String, Object> result = new HashMap<>();
        try {
            List<?> files = storageService.listFiles(category);
            result.put("success", true);
            result.put("files", files);
            result.put("count", files.size());
            result.put("storageType", storageService.getStorageType());
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            result.put("success", false);
            result.put("error", e.getMessage());
            return ResponseEntity.internalServerError().body(result);
        }
    }

    @Operation(summary = "获取存储信息")
    @GetMapping("/info")
    public ResponseEntity<Map<String, Object>> getStorageInfo() {
        Map<String, Object> result = new HashMap<>();
        result.put("storageType", storageService.getStorageType());
        result.put("description", getDescription(storageService.getStorageType()));
        return ResponseEntity.ok(result);
    }

    private String getDescription(String storageType) {
        return switch (storageType) {
            case "local" -> "本地文件存储";
            case "s3" -> "S3兼容对象存储（SeaweedFS/阿里云OSS/腾讯云COS）";
            default -> "未知存储类型";
        };
    }
}
