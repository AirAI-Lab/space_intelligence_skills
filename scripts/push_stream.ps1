# construction_safety 推流脚本
# 将施工安全视频推流到 RTMP 服务器，供边缘端和云端同时消费
param(
    [string]$VideoPath = "D:\github\edge_infer_cloud\models\construction_safety\data\construction_safety.mp4",
    [string]$RtmpUrl = "rtmp://192.168.0.103:1935/stream/safety_cam",
    [switch]$Loop = $true
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $VideoPath)) {
    Write-Host "[ERROR] 视频文件不存在: $VideoPath" -ForegroundColor Red
    exit 1
}

# 检查 ffmpeg
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Host "[ERROR] 未找到 ffmpeg, 请先安装" -ForegroundColor Red
    Write-Host "  下载: https://www.gyan.dev/ffmpeg/builds/" -ForegroundColor Yellow
    exit 1
}

$fileSize = (Get-Item $VideoPath).Length / 1MB
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  施工安全视频推流" -ForegroundColor Cyan
Write-Host "  视频文件: $VideoPath ($([math]::Round($fileSize, 1)) MB)" -ForegroundColor Cyan
Write-Host "  推流地址: $RtmpUrl" -ForegroundColor Cyan
Write-Host "  循环推流: $Loop" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 构建 ffmpeg 命令
$loopArg = if ($Loop) { "-stream_loop", "-1" } else { @() }

Write-Host "推流中... (Ctrl+C 停止)" -ForegroundColor Green
Write-Host ""
Write-Host "消费端:" -ForegroundColor Yellow
Write-Host "  边缘端: rtmp://192.168.0.103:1935/stream/safety_cam (实时推理)" -ForegroundColor White
Write-Host "  云  端: rtmp://192.168.0.103:1935/stream/safety_cam (采样推理)" -ForegroundColor White
Write-Host ""

ffmpeg -re @loopArg -i $VideoPath `
    -c:v libx264 -preset veryfast -tune zerolatency `
    -g 15 -bf 0 `
    -f flv $RtmpUrl
