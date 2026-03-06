# 训练监控脚本
# 用途: 检查Swin V2训练状态并发送通知

param(
    [string]$LogFile = "D:\github\edge_infer\rcmt_v3\logs_swin_final_v2\train.log",
    [switch]$SendNotification
)

Write-Host "=== 训练状态检查 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -ForegroundColor Cyan

# 检查日志文件是否存在
if (-not (Test-Path $LogFile)) {
    Write-Host "错误: 日志文件不存在 - $LogFile" -ForegroundColor Red
    exit 1
}

# 读取最后30行
$lastLines = Get-Content $LogFile -Tail 30

# 提取当前状态
$currentEpoch = ($lastLines | Select-String "Epoch \[(\d+)/300\]" | Select-Object -Last 1).Matches.Groups[1].Value
$bestF1 = ($lastLines | Select-String "New Best Model! F1: ([\d.]+)" | Select-Object -Last 1).Matches.Groups[1].Value
$currentF1 = ($lastLines | Select-String "Val.*F1: ([\d.]+)" | Select-Object -Last 1).Matches.Groups[1].Value

# 检查训练状态
if ($lastLines -match "训练完成") {
    Write-Host "状态: 训练已完成 ✓" -ForegroundColor Green
    $status = "completed"
} elseif ($lastLines -match "Error|Exception|CUDA out of memory") {
    Write-Host "状态: 训练出错 ✗" -ForegroundColor Red
    Write-Host "错误信息:" -ForegroundColor Red
    $lastLines | Select-String "Error|Exception" | Select-Object -Last 5 | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    $status = "error"
} elseif ($currentEpoch) {
    Write-Host "状态: 训练进行中..." -ForegroundColor Green
    $status = "running"
} else {
    Write-Host "状态: 未知" -ForegroundColor Yellow
    $status = "unknown"
}

# 显示详细信息
Write-Host "`n训练进度:" -ForegroundColor Cyan
if ($currentEpoch) {
    $progress = [math]::Round([int]$currentEpoch / 300 * 100, 2)
    Write-Host "  Epoch: $currentEpoch/300 ($progress%)"
}
if ($bestF1) {
    Write-Host "  最佳F1: $bestF1" -ForegroundColor Green
}
if ($currentF1) {
    Write-Host "  当前F1: $currentF1"
}

# 检查GPU使用情况
$gpuProcess = Get-Process -Name python -ErrorAction SilentlyContinue
if ($gpuProcess) {
    Write-Host "`n训练进程: 运行中 (PID: $($gpuProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "`n训练进程: 未运行" -ForegroundColor Yellow
}

# 如果需要发送通知
if ($SendNotification) {
    # TODO: 实现飞书通知
    Write-Host "`n通知功能待实现" -ForegroundColor Yellow
}

# 返回状态码
switch ($status) {
    "completed" { exit 0 }
    "error" { exit 2 }
    "running" { exit 0 }
    default { exit 1 }
}
