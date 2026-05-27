-- edge_infer_cloud 数据库初始化脚本
-- 适用于 PostgreSQL 16 + TimescaleDB

-- 启用 TimescaleDB 扩展
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================
-- 1. 设备表 (devices)
-- ============================================
CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(50) PRIMARY KEY,
    device_name VARCHAR(200),
    device_type VARCHAR(50),
    device_category VARCHAR(30),
    group_id VARCHAR(50),
    status VARCHAR(50) DEFAULT 'OFFLINE',
    ip VARCHAR(50),
    mac VARCHAR(50),
    protocol VARCHAR(30),
    capabilities VARCHAR(200),
    labels TEXT,
    cpu_usage FLOAT,
    gpu_usage FLOAT,
    memory_usage FLOAT,
    disk_usage FLOAT,
    temperature FLOAT,
    os_version VARCHAR(255),
    agent_version VARCHAR(50),
    current_firmware_version VARCHAR(50),
    gpu_model VARCHAR(255),
    gpu_memory_mb INT,
    total_memory_mb INT,
    total_disk_mb INT,
    inference_fps FLOAT,
    uptime_seconds BIGINT,
    current_model_id VARCHAR(50),
    current_version VARCHAR(50),
    mqtt_topic VARCHAR(200),
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_devices_status ON devices(status);
CREATE INDEX idx_devices_group_id ON devices(group_id);
CREATE INDEX idx_devices_current_model_id ON devices(current_model_id);
CREATE INDEX idx_devices_device_category ON devices(device_category);

-- ============================================
-- 2. 设备标签表 (device_tags)
-- ============================================
CREATE TABLE IF NOT EXISTS device_tags (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    tag_key VARCHAR(50) NOT NULL,
    tag_value VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_device_tags_device ON device_tags(device_id);

-- ============================================
-- 3. 设备命令表 (device_commands)
-- ============================================
CREATE TABLE IF NOT EXISTS device_commands (
    id BIGSERIAL PRIMARY KEY,
    command_id VARCHAR(50) UNIQUE NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    command_type VARCHAR(50) NOT NULL,
    task_id VARCHAR(50),
    params TEXT,
    status VARCHAR(20),
    expire_at TIMESTAMP,
    sent_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_device_commands_device ON device_commands(device_id);
CREATE INDEX idx_device_commands_status ON device_commands(status);

-- ============================================
-- 4. 数据集表 (datasets)
-- ============================================
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id VARCHAR(50) PRIMARY KEY,
    dataset_name VARCHAR(200) NOT NULL,
    dataset_type VARCHAR(50) NOT NULL,
    dataset_source VARCHAR(20),
    format VARCHAR(50) NOT NULL,
    storage_path VARCHAR(500),
    category_count INT,
    sample_count INT,
    train_count INT,
    val_count INT,
    test_count INT,
    status VARCHAR(50) DEFAULT 'UPLOADING',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_datasets_type ON datasets(dataset_type);
CREATE INDEX idx_datasets_status ON datasets(status);
CREATE INDEX idx_datasets_format ON datasets(format);

-- ============================================
-- 5. 模型表 (models)
-- ============================================
CREATE TABLE IF NOT EXISTS models (
    model_id VARCHAR(50) PRIMARY KEY,
    model_name VARCHAR(200) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    framework VARCHAR(50),
    version VARCHAR(50) NOT NULL,
    parent_model_id VARCHAR(50),
    dataset_id VARCHAR(50),
    pt_file_path VARCHAR(500),
    pt_file_size_bytes BIGINT,
    onnx_file_path VARCHAR(500),
    onnx_file_size_bytes BIGINT,
    engine_file_path VARCHAR(500),
    engine_file_size_bytes BIGINT,
    map FLOAT,
    map50 FLOAT,
    precision FLOAT,
    recall FLOAT,
    inference_time_ms FLOAT,
    input_width INT,
    input_height INT,
    class_names JSONB,
    status VARCHAR(50) DEFAULT 'TRAINING',
    file_size_bytes BIGINT,
    deployed_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (parent_model_id) REFERENCES models(model_id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

CREATE INDEX idx_models_type ON models(model_type);
CREATE INDEX idx_models_status ON models(status);
CREATE INDEX idx_models_parent_model_id ON models(parent_model_id);
CREATE INDEX idx_models_dataset_id ON models(dataset_id);

-- ============================================
-- 6. 模型部署记录表 (model_deployment)
-- ============================================
CREATE TABLE IF NOT EXISTS model_deployment (
    deployment_id VARCHAR(50) PRIMARY KEY,
    model_id VARCHAR(50) NOT NULL,
    model_name VARCHAR(200),
    device_id VARCHAR(50) NOT NULL,
    device_name VARCHAR(200),
    deployment_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    previous_model_id VARCHAR(50),
    previous_model_name VARCHAR(200),
    ota_task_id VARCHAR(50),
    deployed_by VARCHAR(50),
    deployed_at TIMESTAMP,
    completed_at TIMESTAMP,
    rollback_at TIMESTAMP,
    error_message VARCHAR(500),
    inference_fps FLOAT,
    memory_usage_mb INT,
    gpu_utilization FLOAT,
    is_ab_test BOOLEAN DEFAULT false,
    ab_test_group VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_model_deployment_model ON model_deployment(model_id);
CREATE INDEX idx_model_deployment_device ON model_deployment(device_id);
CREATE INDEX idx_model_deployment_status ON model_deployment(status);

-- ============================================
-- 7. 训练任务表 (training_jobs)
-- ============================================
CREATE TABLE IF NOT EXISTS training_jobs (
    job_id VARCHAR(50) PRIMARY KEY,
    job_name VARCHAR(200) NOT NULL,
    dataset_id VARCHAR(50),
    dataset_source VARCHAR(20),
    dataset_url VARCHAR(500),
    dataset_path VARCHAR(500),
    dataset_name VARCHAR(200),
    base_model_id VARCHAR(50),
    base_model VARCHAR(100),
    output_model_id VARCHAR(50),
    epochs INT NOT NULL,
    batch_size INT NOT NULL,
    img_size INT NOT NULL,
    use_gpu BOOLEAN DEFAULT true,
    training_type VARCHAR(50),
    hyperparameters JSONB,
    status VARCHAR(50) DEFAULT 'PENDING',
    current_epoch INT DEFAULT 0,
    progress FLOAT DEFAULT 0,
    final_map FLOAT,
    final_loss FLOAT,
    best_epoch INT,
    resume BOOLEAN DEFAULT false,
    resume_job_id VARCHAR(50),
    enable_smart_optimization BOOLEAN DEFAULT false,
    mlflow_run_id VARCHAR(100),
    mlflow_experiment_id VARCHAR(100),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id),
    FOREIGN KEY (base_model_id) REFERENCES models(model_id),
    FOREIGN KEY (output_model_id) REFERENCES models(model_id)
);

CREATE INDEX idx_training_jobs_status ON training_jobs(status);
CREATE INDEX idx_training_jobs_dataset_id ON training_jobs(dataset_id);
CREATE INDEX idx_training_jobs_base_model_id ON training_jobs(base_model_id);

-- ============================================
-- 8. 训练指标时序表 (training_metrics) - TimescaleDB
-- ============================================
CREATE TABLE IF NOT EXISTS training_metrics (
    time TIMESTAMPTZ NOT NULL,
    job_id VARCHAR(50) NOT NULL,
    epoch INT NOT NULL,
    train_loss FLOAT,
    val_loss FLOAT,
    map50 FLOAT,
    map50_95 FLOAT,
    precision FLOAT,
    recall FLOAT,
    learning_rate FLOAT,
    PRIMARY KEY (time, job_id)
);

-- 创建 TimescaleDB 超表
SELECT create_hypertable('training_metrics', 'time', if_not_exists => TRUE);

CREATE INDEX idx_training_metrics_job_id ON training_metrics(job_id);
CREATE INDEX idx_training_metrics_epoch ON training_metrics(epoch);

-- ============================================
-- 9. 转换任务表 (conversion_tasks)
-- ============================================
CREATE TABLE IF NOT EXISTS conversion_tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    model_id VARCHAR(50),
    source_format VARCHAR(20),
    target_format VARCHAR(20),
    conversion_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'PENDING',
    progress FLOAT DEFAULT 0,
    error_message TEXT,
    output_file_path VARCHAR(500),
    file_size_bytes BIGINT,
    optimization_time_seconds INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (model_id) REFERENCES models(model_id)
);

CREATE INDEX idx_conversion_tasks_model_id ON conversion_tasks(model_id);
CREATE INDEX idx_conversion_tasks_status ON conversion_tasks(status);

-- ============================================
-- 10. OTA 升级任务表 (ota_tasks)
-- ============================================
CREATE TABLE IF NOT EXISTS ota_tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    task_name VARCHAR(200) NOT NULL,
    upgrade_type VARCHAR(50),
    model_id VARCHAR(50),
    target_version VARCHAR(50),
    strategy VARCHAR(50),
    scheduled_time TIMESTAMP,
    status VARCHAR(50) DEFAULT 'PENDING',
    progress INT DEFAULT 0,
    total_devices INT,
    completed_devices INT DEFAULT 0,
    failed_devices INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (model_id) REFERENCES models(model_id)
);

CREATE INDEX idx_ota_tasks_status ON ota_tasks(status);
CREATE INDEX idx_ota_tasks_model_id ON ota_tasks(model_id);
CREATE INDEX idx_ota_tasks_scheduled_time ON ota_tasks(scheduled_time);

-- ============================================
-- 11. 设备升级状态表 (device_upgrade_status)
-- ============================================
CREATE TABLE IF NOT EXISTS device_upgrade_status (
    status_id VARCHAR(50) PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    progress INT DEFAULT 0,
    current_stage VARCHAR(20),
    error_message TEXT,
    download_start_time TIMESTAMP,
    download_complete_time TIMESTAMP,
    install_start_time TIMESTAMP,
    install_complete_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id) REFERENCES ota_tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    UNIQUE(task_id, device_id)
);

CREATE INDEX idx_device_upgrade_status_task_id ON device_upgrade_status(task_id);
CREATE INDEX idx_device_upgrade_status_device_id ON device_upgrade_status(device_id);
CREATE INDEX idx_device_upgrade_status_status ON device_upgrade_status(status);

-- ============================================
-- 12. 推理结果时序表 (inference_results) - TimescaleDB
-- 存储边缘端 YOLO 检测和云端 C-RADIOv4 分割结果
-- ============================================
CREATE TABLE IF NOT EXISTS inference_results (
    id BIGSERIAL,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id VARCHAR(50) NOT NULL,
    channel_id VARCHAR(50),
    source VARCHAR(20) NOT NULL,
    model_name VARCHAR(200),
    task_type VARCHAR(50),
    frame_id BIGINT,
    image_url VARCHAR(500),
    result_json JSONB,
    alert_level VARCHAR(20),
    alert_message TEXT,
    inference_time_ms FLOAT,
    detection_count INT DEFAULT 0,
    summary_text VARCHAR(500),
    PRIMARY KEY (time, id)
);

SELECT create_hypertable('inference_results', 'time', if_not_exists => TRUE);

CREATE INDEX idx_ir_device_time ON inference_results(device_id, time DESC);
CREATE INDEX idx_ir_alert_time ON inference_results(alert_level, time DESC) WHERE alert_level IS NOT NULL;
CREATE INDEX idx_ir_source ON inference_results(source);
CREATE INDEX idx_ir_result_json ON inference_results USING gin(result_json);

-- ============================================
-- 13. Webhook 配置表 (webhook_configs)
-- ============================================
CREATE TABLE IF NOT EXISTS webhook_configs (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    url VARCHAR(500) NOT NULL,
    secret VARCHAR(200),
    events VARCHAR(500),
    headers TEXT,
    enabled BOOLEAN DEFAULT true,
    last_trigger_time TIMESTAMP,
    trigger_count INT DEFAULT 0,
    last_error VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_webhook_configs_enabled ON webhook_configs(enabled);

-- ============================================
-- 14. 告警规则表 (alert_rules)
-- ============================================
CREATE TABLE IF NOT EXISTS alert_rules (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    device_id VARCHAR(50),
    model_name VARCHAR(200),
    source VARCHAR(20),
    class_name VARCHAR(100),
    condition_type VARCHAR(50) NOT NULL,
    threshold_value FLOAT,
    alert_level VARCHAR(20) NOT NULL,
    alert_message VARCHAR(500),
    trigger_cloud_infer BOOLEAN DEFAULT false,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alert_rules_enabled ON alert_rules(enabled);
CREATE INDEX idx_alert_rules_device ON alert_rules(device_id) WHERE device_id IS NOT NULL;
CREATE INDEX idx_alert_rules_class ON alert_rules(class_name) WHERE class_name IS NOT NULL;

-- ============================================
-- 自动更新 updated_at 字段的触发器
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为所有需要自动更新 updated_at 的表创建触发器
CREATE TRIGGER update_devices_updated_at BEFORE UPDATE ON devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_datasets_updated_at BEFORE UPDATE ON datasets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_models_updated_at BEFORE UPDATE ON models
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_training_jobs_updated_at BEFORE UPDATE ON training_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversion_tasks_updated_at BEFORE UPDATE ON conversion_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ota_tasks_updated_at BEFORE UPDATE ON ota_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_upgrade_status_updated_at BEFORE UPDATE ON device_upgrade_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_webhook_configs_updated_at BEFORE UPDATE ON webhook_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alert_rules_updated_at BEFORE UPDATE ON alert_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_model_deployment_updated_at BEFORE UPDATE ON model_deployment
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_commands_updated_at BEFORE UPDATE ON device_commands
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 完成
-- ============================================
-- 数据库初始化完成！14 张表已创建。
-- 验证: \dt
