package com.edge.cloud.entity;

public enum DeviceType {
    JETSON_ORIN("EDGE_COMPUTE", "NVIDIA Jetson Orin"),
    JETSON_XAVIER("EDGE_COMPUTE", "NVIDIA Jetson Xavier"),
    JETSON_NANO("EDGE_COMPUTE", "NVIDIA Jetson Nano"),
    EDGE_BOX("EDGE_COMPUTE", "边缘计算盒子"),
    DRONE("UAV", "无人机"),
    ROBOT_DOG("ROBOTIC", "机器狗"),
    VEHICLE("VEHICLE", "无人车"),
    SENSOR("SENSOR", "传感器"),
    CAMERA("CAMERA", "摄像头");

    private final String category;
    private final String description;

    DeviceType(String category, String description) {
        this.category = category;
        this.description = description;
    }

    public String getCategory() { return category; }
    public String getDescription() { return description; }

    public static DeviceType fromString(String value) {
        if (value == null) return EDGE_BOX;
        try {
            return valueOf(value.toUpperCase());
        } catch (IllegalArgumentException e) {
            return EDGE_BOX;
        }
    }

    public static String inferCategory(String deviceType) {
        return fromString(deviceType).getCategory();
    }
}
