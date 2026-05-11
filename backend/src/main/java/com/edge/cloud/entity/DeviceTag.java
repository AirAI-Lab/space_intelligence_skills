package com.edge.cloud.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "device_tags")
public class DeviceTag {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "device_id", nullable = false, length = 50)
    private String deviceId;

    @Column(name = "tag_key", nullable = false, length = 50)
    private String tagKey;

    @Column(name = "tag_value", length = 200)
    private String tagValue;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }

    // Getters and Setters
    public Long getId() { return id; }
    public String getDeviceId() { return deviceId; }
    public void setDeviceId(String deviceId) { this.deviceId = deviceId; }
    public String getTagKey() { return tagKey; }
    public void setTagKey(String tagKey) { this.tagKey = tagKey; }
    public String getTagValue() { return tagValue; }
    public void setTagValue(String tagValue) { this.tagValue = tagValue; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
