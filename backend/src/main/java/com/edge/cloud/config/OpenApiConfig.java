package com.edge.cloud.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
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
                .description("边缘智能云平台 REST API — 设备管理、推理结果、模型训练、告警推送"))
            .addSecurityItem(new SecurityRequirement().addList("API Key"))
            .components(new Components()
                .addSecuritySchemes("API Key",
                    new SecurityScheme()
                        .type(SecurityScheme.Type.APIKEY)
                        .in(SecurityScheme.In.HEADER)
                        .name("X-API-Key")
                        .description("在 .env 中配置的 API_KEY")));
    }
}
