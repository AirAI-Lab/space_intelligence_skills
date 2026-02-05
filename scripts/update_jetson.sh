#!/bin/bash
# Jetson 更新并重新编译脚本

set -e

echo "=== Jetson Edge Infer 更新脚本 ==="
echo ""

# 1. 备份当前版本
echo "1. 备份当前版本..."
cd ~
if [ -d "edge_infer" ]; then
    mv edge_infer edge_infer_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
    echo "  已备份到: edge_infer_backup_*"
fi

# 2. 克隆最新代码
echo "2. 从 GitHub 克隆最新代码..."
git clone https://github.com/AirAI-Lab/edge_infer.git
cd edge_infer

# 3. 检查 MQTT 依赖
echo "3. 检查 MQTT 依赖..."
if ! dpkg -l | grep -q libmosquitto-dev; then
    echo "  安装 MQTT 依赖..."
    sudo apt-get update
    sudo apt-get install -y libmosquitto-dev libmosquitto1
fi

# 4. 创建配置文件
echo "4. 创建配置文件..."
mkdir -p config logs output/alerts models

cat > config/framework_config.json << 'EOF'
{
  "input_uri": "rtmp://192.168.0.103:1935/stream/helmet_stub",
  "input_fps": 0,
  "output_url": "rtmp://192.168.0.104:1935/stream/jetson_output",
  "output_fps": 0,
  "local_video_path": "/home/nvidia/edge_infer/output/helmet_vis.mp4",
  "alert_image_dir": "/home/nvidia/edge_infer/output/alerts",
  "input_source": "rtmp://192.168.0.103:1935/stream/helmet_stub",
  "enable_cloud_sync": false,
  "enable_drone_comm": false,
  "enable_zhifei_platform": false,
  "plugins_root": ["src/plugins"],
  "use_tensorRT": true,
  "infer_input_size": [960, 960],
  "output_keep_original_size": true,
  "draw_box_scale_mode": "auto"
}
EOF

echo "  创建 cloud_config.json..."
cat > config/cloud_config.json << 'EOF'
{
  "cloud": {
    "enabled": true,
    "api_base_url": "http://192.168.0.103:8081/api/v1",
    "device_id": "jetson_orin_001",
    "device_name": "Jetson Orin Edge Device",
    "device_type": "JETSON_ORIN"
  },
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

# 5. 编译
echo "5. 编译 edge_framework..."
mkdir -p build
cd build
cmake .. -DUSE_TENSORRT=ON
make -j$(nproc)

echo ""
echo "=== 编译完成 ==="
echo ""
echo "新功能："
echo "  ✓ ONNX→Engine 转换器 (onnx_converter)"
echo "  ✓ OTA 支持 ONNX 文件下载并自动转换"
echo "  ✓ MQTT 云边协同"
echo ""
echo "启动命令:"
echo "  cd ~/edge_infer/build"
echo "  ./edge_framework"
echo ""
