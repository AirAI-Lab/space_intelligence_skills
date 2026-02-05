#!/bin/bash
# Jetson MQTT 部署脚本
# 在 Jetson 设备上执行此脚本

set -e

echo "=== Jetson Edge Infer MQTT 部署 ==="
echo "1. 更新配置文件..."

cd ~/edge_infer || { echo "错误: edge_infer 目录不存在"; exit 1; }

# 创建 framework_config.json
cat > config/framework_config.json << 'EOF'
{
  "input_uri": "rtmp://192.168.0.146:1935/stream/helmet_stub",
  "input_fps": 0,
  "output_url": "rtmp://192.168.0.146:1935/stream/jetson_output",
  "output_fps": 0,
  "local_video_path": "/home/nvidia/edge_infer/output/helmet_vis.mp4",
  "alert_image_dir": "/home/nvidia/edge_infer/output/alerts",
  "input_source": "rtmp://192.168.0.146:1935/stream/helmet_stub",
  "enable_cloud_sync": false,
  "enable_drone_comm": false,
  "enable_zhifei_platform": false,
  "plugins_root": ["src/plugins"],
  "use_tensorRT": true,
  "infer_input_size": [960, 960],
  "output_keep_original_size": true,
  "draw_box_scale_mode": "auto",
  "mqtt": {
    "enabled": true,
    "broker_host": "192.168.0.103",
    "broker_port": 1883,
    "client_id": "jetson_orin_001",
    "username": "",
    "password": "",
    "keep_alive": 60,
    "qos": 1
  },
  "ota": {
    "enabled": true,
    "model_dir": "/home/nvidia/edge_infer/models",
    "auto_reload": true
  }
}
EOF

echo "2. 创建模型目录..."
mkdir -p models
mkdir -p logs
mkdir -p output/alerts

echo "3. 编译 edge_framework (带 MQTT 支持)..."
mkdir -p build
cd build

cmake .. -DUSE_MQTT=ON -DUSE_TENSORRT=ON
make -j$(nproc)

echo "4. 启动 edge_framework..."
echo "=========================================="
echo "启动命令: ./edge_framework"
echo "=========================================="

# 在后台运行
nohup ./edge_framework > ../logs/edge_framework.log 2>&1 &
echo $! > ../logs/edge_framework.pid

echo ""
echo "=== 部署完成 ==="
echo "日志文件: tail -f ~/edge_infer/logs/edge_framework.log"
echo "停止进程: kill \$(cat ~/edge_infer/logs/edge_framework.pid)"
echo ""
echo "请在云端检查设备状态: jetson_orin_001"
