-- 数据库迁移：添加设备表缺失的列
-- 执行方式：psql -U postgres -d edge_infer_cloud -f V2__add_missing_device_columns.sql

-- 添加缺失的列到 devices 表
ALTER TABLE devices ADD COLUMN IF NOT EXISTS ip VARCHAR(50);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS mac VARCHAR(50);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS current_firmware_version VARCHAR(50);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS inference_fps FLOAT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS os_version VARCHAR(50);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS agent_version VARCHAR(50);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS gpu_model VARCHAR(100);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS gpu_memory_mb INT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS total_memory_mb INT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS total_disk_mb INT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS temperature FLOAT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS uptime_seconds BIGINT;

-- 添加注释
COMMENT ON COLUMN devices.ip IS '设备IP地址';
COMMENT ON COLUMN devices.mac IS '设备MAC地址';
COMMENT ON COLUMN devices.current_firmware_version IS '当前固件版本';
COMMENT ON COLUMN devices.inference_fps IS '推理帧率';
COMMENT ON COLUMN devices.os_version IS '操作系统版本';
COMMENT ON COLUMN devices.agent_version IS '代理版本';
COMMENT ON COLUMN devices.gpu_model IS 'GPU型号';
COMMENT ON COLUMN devices.gpu_memory_mb IS 'GPU显存(MB)';
COMMENT ON COLUMN devices.total_memory_mb IS '总内存(MB)';
COMMENT ON COLUMN devices.total_disk_mb IS '总磁盘(MB)';
COMMENT ON COLUMN devices.temperature IS '设备温度(摄氏度)';
COMMENT ON COLUMN devices.uptime_seconds IS '运行时长(秒)';
