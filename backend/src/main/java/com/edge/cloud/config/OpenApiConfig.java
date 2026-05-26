package com.edge.cloud.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
            .info(new Info()
                .title("SkyEdge AI Cloud Platform API")
                .version("1.0")
                .description("边缘智能云平台 REST API — 设备管理、推理结果、模型训练、告警推送"));
    }
}
