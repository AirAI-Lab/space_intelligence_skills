package com.edge.cloud.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class WebhookConfigRequest {
    private String name;
    private String url;
    private String secret;
    private String events;  // comma-separated event types
    private String headers; // JSON string
    @JsonProperty("enabled")
    private Boolean enabled = true;
}
