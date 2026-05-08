package com.edge.cloud;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Edge Cloud 云边协同管理平台 - 主应用入口
 */
@SpringBootApplication
@EnableScheduling
@EnableAsync
public class EdgeCloudApplication {

    public static void main(String[] args) {
        SpringApplication.run(EdgeCloudApplication.class, args);
    }
}
