#!/bin/bash
# Jetson 自动修复和启动脚本

set -e

echo "=== Jetson 自动修复脚本 ==="
echo ""

cd ~/edge_infer

echo "1. 拉取最新代码..."
git fetch origin
git reset --hard origin/master

echo ""
echo "2. 检查并创建配置文件..."

# 创建 cloud_config.json
mkdir -p config logs output/alerts models

if [ ! -f "config/cloud_config.json" ]; then
    echo "创建 cloud_config.json..."
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
    echo "✓ cloud_config.json 已创建"
else
    echo "✓ cloud_config.json 已存在"
fi

echo ""
echo "3. 验证配置文件..."
cat config/cloud_config.json

echo ""
echo "4. 停止旧进程..."
pkill -9 edge_framework 2>/dev/null || true
sleep 1

echo ""
echo "5. 启动 edge_framework..."
echo "=========================================="
cd ~/edge_infer
./build/edge_framework &
EDGE_PID=$!
echo ""
echo "edge_framework 已启动 (PID: $EDGE_PID)"
echo ""
echo "等待 3 秒检查 MQTT 连接..."
sleep 3

# 检查进程是否还在运行
if ps -p $EDGE_PID > /dev/null; then
    echo "✓ edge_framework 正在运行"
    echo ""
    echo "查看日志: tail -f ~/edge_infer/logs/edge_framework.log"
    echo "停止进程: kill $EDGE_PID"
else
    echo "✗ edge_framework 已退出，请检查错误"
fi

echo ""
echo "=== 完成 ==="
