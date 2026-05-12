package com.edge.cloud.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;

/**
 * 全局异常处理：捕获 Spring 反序列化等框架层错误并记录日志
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Map<String, Object>> handleNotReadable(HttpMessageNotReadableException ex) {
        log.error("请求体解析失败: {}", ex.getMessage());
        return ResponseEntity.badRequest().body(Map.of(
                "status", "ERROR",
                "message", "Invalid request body: " + ex.getMostSpecificCause().getMessage()
        ));
    }
}
