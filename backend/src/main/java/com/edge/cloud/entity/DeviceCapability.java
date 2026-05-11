package com.edge.cloud.entity;

public enum DeviceCapability {
    VIDEO_INPUT("视频输入"),
    INFERENCE("AI推理"),
    CONTROL("设备控制"),
    SENSING("传感采集"),
    CLOUD_FORWARD("云端转发"),
    OTA_UPDATE("OTA升级"),
    MULTI_CHANNEL("多通道");

    private final String description;

    DeviceCapability(String description) {
        this.description = description;
    }

    public String getDescription() { return description; }

    public static String defaultForEdge() {
        return "VIDEO_INPUT,INFERENCE,CLOUD_FORWARD,OTA_UPDATE";
    }

    public static String defaultForSensor() {
        return "SENSING";
    }
}
