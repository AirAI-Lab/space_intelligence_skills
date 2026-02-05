# Jetson MQTT 部署脚本 (PowerShell)
# 使用方法: .\deploy_jetson_mqtt.ps1

$JetsonIP = "192.168.0.104"
$Username = "nvidia"
$Password = "nvidia"
$CloudIP = "192.168.0.103"

Write-Host "=== Jetson Edge Infer MQTT 部署 ===" -ForegroundColor Green
Write-Host "Jetson IP: $JetsonIP"
Write-Host "云端 IP: $CloudIP"
Write-Host ""

# 使用 sshpass 的替代方案 - 通过 plink 或 expect
# 由于 Windows 10+ 有内置 SSH，我们创建一个临时脚本

$ScriptContent = @"
#!/bin/bash
set -e
echo "=== Jetson Edge Infer MQTT 部署 ==="
echo "1. 更新配置文件..."

cd ~/edge_infer || { echo "错误: edge_infer 目录不存在"; exit 1; }

# 创建 framework_config.json
cat > config/framework_config.json << 'EOFF'
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
    "broker_host": "$CloudIP",
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
EOFF

echo "2. 创建必要的目录..."
mkdir -p models logs output/alerts

echo "3. 编译 edge_framework..."
mkdir -p build
cd build
cmake .. -DUSE_MQTT=ON -DUSE_TENSORRT=ON
make -j\$(nproc)

echo "4. 部署完成!"
echo "请在另一个终端启动: cd ~/edge_infer/build && ./edge_framework"
"@

# 保存临时脚本
$TempScript = "$env:TEMP\deploy_jetson_temp.sh"
$ScriptContent | Out-File -FilePath $TempScript -Encoding ASCII

Write-Host "请手动执行以下步骤:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 将以下脚本内容复制到 Jetson:" -ForegroundColor Cyan
Write-Host ""
Write-Host $ScriptContent
Write-Host ""
Write-Host "2. 或使用 SCP 传输脚本:" -ForegroundColor Cyan
Write-Host "scp $TempScript ${Username}@${JetsonIP}:~/deploy.sh"
Write-Host ""
Write-Host "3. SSH 登录到 Jetson 执行:" -ForegroundColor Cyan
Write-Host "ssh ${Username}@${JetsonIP}"
Write-Host "bash ~/deploy.sh"
Write-Host ""

# 清理临时文件
Remove-Item $TempScript -ErrorAction SilentlyContinue
