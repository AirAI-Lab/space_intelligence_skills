# construction_safety 完整演示启动脚本
#
# 架构: FFmpeg 推流 → 边缘端(YOLOv8 实时) + 云端(C-RADIOv4 采样) 并行推理
#
# 用法:
#   powershell -ExecutionPolicy Bypass -File scripts\demo_construction_safety.ps1
#
# 前提:
#   1. Docker 服务已启动 (deployment/docker/docker compose up -d)
#   2. 本机有 NVIDIA GPU + nvidia-container-toolkit
#   3. C-RADIOv4 模型权重已下载到 models/ 目录
param(
    [string]$RtmpUrl = "rtmp://192.168.0.103:1935/stream/safety_cam",
    [string]$BackendUrl = "http://localhost:8081",
    [int]$SampleInterval = 3,
    [string]$VideoPath = "D:\github\edge_infer_cloud\models\construction_safety\data\construction_safety.mp4"
)

$ErrorActionPreference = "Stop"
$DockerDir = "$PSScriptRoot\..\deployment\docker"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  施工安全 — 云边协同推理演示" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  边缘端 (Jetson 192.168.0.107): YOLOv8 实时检测" -ForegroundColor White
Write-Host "    → helmet / head / person / reflective_vest / ..." -ForegroundColor DarkGray
Write-Host "  云  端 (本机 GPU): C-RADIOv4 零样本分割" -ForegroundColor White
Write-Host "    → 裸土 / 积水 / 扬尘 / 材料堆放" -ForegroundColor DarkGray
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: 检查后端服务 ──
Write-Host "[Step 1/5] 检查后端服务..." -ForegroundColor Yellow
try {
    Invoke-RestMethod -Uri "$BackendUrl/api/v1/inference/stats" -TimeoutSec 3 | Out-Null
    Write-Host "  OK" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] 后端未启动: $BackendUrl" -ForegroundColor Red
    Write-Host "  启动: cd deployment/docker && docker compose up -d" -ForegroundColor Yellow
    exit 1
}

# ── Step 2: RTMP 服务器 ──
Write-Host "[Step 2/5] RTMP 服务器..." -ForegroundColor Yellow
$rtmp = docker ps --filter "name=rtmp-server" --format "{{.Names}}" 2>$null
if (-not $rtmp) {
    docker run --name rtmp-server -d -p 1935:1935 -p 8089:80 alfg/nginx-rtmp:latest 2>$null
    Start-Sleep -Seconds 2
    Write-Host "  已启动" -ForegroundColor Green
} else {
    Write-Host "  已运行" -ForegroundColor Green
}

# ── Step 3: 配置告警规则 ──
Write-Host "[Step 3/5] 配置告警规则..." -ForegroundColor Yellow
$existing = (Invoke-RestMethod -Uri "$BackendUrl/api/v1/alert-rules").data
foreach ($r in $existing) {
    Invoke-RestMethod -Uri "$BackendUrl/api/v1/alert-rules/$($r.id)" -Method DELETE | Out-Null
}

$rules = @(
    @{ name="edge_no_helmet"; class_name="head"; condition_type="count_threshold"; threshold_value=1; alert_level="critical"; alert_message="未佩戴安全帽" },
    @{ name="edge_no_vest"; class_name="no_vest"; condition_type="count_threshold"; threshold_value=1; alert_level="warning"; alert_message="未穿反光衣" },
    @{ name="edge_person_density"; class_name="person"; condition_type="count_threshold"; threshold_value=6; alert_level="warning"; alert_message="人员密集 (>6人)" },
    @{ name="cloud_bare_soil"; class_name="bare_soil_uncovered"; condition_type="area_threshold"; threshold_value=0.05; alert_level="warning"; alert_message="裸土未覆盖" },
    @{ name="cloud_pit_water"; class_name="pit_water_accumulation"; condition_type="area_threshold"; threshold_value=0.03; alert_level="warning"; alert_message="基坑积水" },
    @{ name="cloud_dust"; class_name="dust_pollution"; condition_type="area_threshold"; threshold_value=0.01; alert_level="critical"; alert_message="扬尘污染" }
)
foreach ($r in $rules) {
    $body = ($r + @{ enabled=$true }) | ConvertTo-Json
    Invoke-RestMethod -Uri "$BackendUrl/api/v1/alert-rules" -Method POST -Body $body -ContentType "application/json" | Out-Null
    Write-Host "  $($r.name): $($r.alert_level)" -ForegroundColor White
}
Write-Host "  OK ($($rules.Count) 条规则)" -ForegroundColor Green

# ── Step 4: 推流 ──
Write-Host "[Step 4/5] 启动推流..." -ForegroundColor Yellow
if (-not (Test-Path $VideoPath)) {
    Write-Host "  [FAIL] 视频不存在: $VideoPath" -ForegroundColor Red
    exit 1
}
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Host "  [FAIL] 未找到 ffmpeg" -ForegroundColor Red
    exit 1
}
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Write-Host '推流中... (Ctrl+C 停止)' -ForegroundColor Green;",
    "ffmpeg -re -stream_loop -1 -i `"$VideoPath`" -c:v libx264 -preset veryfast -tune zerolatency -g 15 -bf 0 -f flv $RtmpUrl"
) -WindowStyle Normal
Write-Host "  推流已启动: $RtmpUrl" -ForegroundColor Green

# ── Step 5: 构建并启动云端推理 ──
Write-Host "[Step 5/5] 启动云端推理 (Docker GPU)..." -ForegroundColor Yellow

Push-Location $DockerDir

# 先构建镜像 (代码和配置已打入镜像)
Write-Host "  构建镜像 edge-cloud-infer:latest..." -ForegroundColor DarkGray
docker compose --profile gpu build cloud_infer 2>&1 | ForEach-Object { Write-Host "  $_" }

# 设置流式模式参数
$configPath = "/app/models/construction_safety/configs/construction_safety.yaml"
$envFile = "$DockerDir\.env.demo"
@"
CONFIG_PATH=$configPath
STREAM_URL=$RtmpUrl
STREAM_INTERVAL=$SampleInterval
STREAM_DEVICE_ID=cloud_gpu_103
"@ | Set-Content $envFile -Encoding UTF8

docker compose --profile gpu up -d cloud_infer 2>&1 | ForEach-Object { Write-Host "  $_" }
Pop-Location

Write-Host "  云端推理已启动" -ForegroundColor Green

# ── 完成 ──
Start-Sleep -Seconds 2
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  服务状态:" -ForegroundColor Cyan
docker ps --filter "name=edge_cloud_radio_infer" --format "  {{.Names}}: {{.Status}}" 2>$null
Write-Host ""
Write-Host "  查看云端推理日志:" -ForegroundColor Cyan
Write-Host "    docker logs -f edge_cloud_radio_infer" -ForegroundColor White
Write-Host ""
Write-Host "  边缘端 (Jetson) 手动启动:" -ForegroundColor Cyan
Write-Host "    vi ~/edge_infer/config/framework_config.json" -ForegroundColor White
Write-Host "    # input_uri → $RtmpUrl" -ForegroundColor DarkGray
Write-Host "    cd ~/edge_infer && ./build/edge_framework" -ForegroundColor White
Write-Host ""
Write-Host "  前端:" -ForegroundColor Cyan
Write-Host "    http://localhost:3000/inference    推理结果" -ForegroundColor White
Write-Host "    http://localhost:3000/alerts        告警中心" -ForegroundColor White
Write-Host "    http://localhost:3000/alert-rules   告警规则" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan
