-- 清理模拟设备数据
-- 执行此脚本将删除所有模拟测试设备，确保只显示真实设备

-- 删除所有测试设备（可以根据需要调整条件）
DELETE FROM devices
WHERE device_id LIKE 'EDGE_DEVICE_%'
   OR device_id LIKE 'TEST_%'
   OR device_id LIKE 'MOCK_%';

-- 如果需要删除特定的设备（如 jetson_orin_001），可以使用：
-- DELETE FROM devices WHERE device_id = 'jetson_orin_001';

-- 验证删除结果
SELECT device_id, device_name, device_type, status, last_heartbeat
FROM devices
ORDER BY created_at DESC;
