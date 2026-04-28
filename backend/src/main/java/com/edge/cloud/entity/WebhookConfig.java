package com.edge.cloud.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "webhook_configs")
public class WebhookConfig {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "name", length = 200, nullable = false)
    private String name;

    @Column(name = "url", length = 500, nullable = false)
    private String url;

    @Column(name = "secret", length = 200)
    private String secret;

    @Column(name = "events", length = 500)
    private String events;  // comma-separated: "alert.critical,alert.warning,result.cloud"

    @Column(name = "headers", columnDefinition = "TEXT")
    private String headers; // JSON: {"Authorization": "Bearer xxx"}

    @Column(name = "enabled")
    private Boolean enabled = true;

    @Column(name = "last_trigger_time")
    private LocalDateTime lastTriggerTime;

    @Column(name = "trigger_count")
    private Integer triggerCount = 0;

    @Column(name = "last_error", length = 500)
    private String lastError;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
