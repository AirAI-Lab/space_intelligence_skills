# Jetson 一键修复脚本
# 使用方法: 在 PowerShell 中运行 .\fix_jetson.ps1

$JetsonIP = "192.168.0.104"
$Username = "nvidia"

Write-Host "=== Jetson 一键修复 ===" -ForegroundColor Green
Write-Host ""

# 创建修复命令
$FixCommands = @"
cd ~/edge_infer && \
git fetch origin && \
git reset --hard origin/master && \
mkdir -p config logs output/alerts models && \
cat > config/cloud_config.json << 'CLOUDCONFIG'
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
CLOUDCONFIG
cat config/cloud_config.json && \
pkill -9 edge_framework 2>/dev/null || true && \
cd ~/edge_infer && ./build/edge_framework
"@

Write-Host "请在 Jetson 上执行以下命令:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. SSH 连接:" -ForegroundColor Cyan
Write-Host "   ssh $Username@$JetsonIP"
Write-Host ""
Write-Host "2. 复制并执行以下命令:" -ForegroundColor Cyan
Write-Host ""
Write-Host $FixCommands
Write-Host ""

# 尝试使用 plink
$PlinkPath = "C:\Program Files\PuTTY\plink.exe"
if (Test-Path $PlinkPath) {
    Write-Host "找到 plink，正在自动执行..." -ForegroundColor Green
    $FixCommands | & $PlinkPath -ssh -l $Username -pw nvidia $JetsonIP 2>&1
}
