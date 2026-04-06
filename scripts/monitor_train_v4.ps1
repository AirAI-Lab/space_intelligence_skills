# 监控 temporal_peft v4 训练并通过 OpenClaw 发送飞书通知
param(
    [string]$LogFile = "D:\github\edge_infer\rcmt_v3\temporal_peft\logs\train_v4.log",
    [string]$StatusFile = "D:\github\edge_infer_cloud\scripts\train_v4_status.json"
)

if (-not (Test-Path $LogFile)) {
    Write-Output "ERROR: Log file not found"
    exit 1
}

$logContent = Get-Content $LogFile -Raw

# Extract current epoch - find last match
$epochMatches = [regex]::Matches($logContent, "Epoch (\d+)/200")
$currentEpoch = 0
if ($epochMatches -and $epochMatches.Count -gt 0) {
    $currentEpoch = [int]$epochMatches[$epochMatches.Count - 1].Groups[1].Value
}

# Extract latest validation F1
$f1Matches = [regex]::Matches($logContent, "验证 - Loss: [\d.]+\s+Thr: [\d.]+, F1: ([\d.]+)")
$latestF1 = 0.0
if ($f1Matches -and $f1Matches.Count -gt 0) {
    $latestF1 = [float]$f1Matches[$f1Matches.Count - 1].Groups[1].Value
}

# Extract best F1 - try multiple patterns to handle encoding issues
# Pattern 1: 标准格式 "新的最佳F1: 0.1306"
# Pattern 2: 可能的编码问题格式 "F1: 0.1306 (Epoch"
$bestF1 = 0.0

# Try standard pattern first
$bestMatches = [regex]::Matches($logContent, "新的最佳F1:\s*([\d.]+)")
if ($bestMatches -and $bestMatches.Count -gt 0) {
    $bestF1 = [float]$bestMatches[$bestMatches.Count - 1].Groups[1].Value
} else {
    # Fallback: extract from "F1: X.XXXX (Epoch Y)" pattern after "新的最佳" or similar
    $altMatches = [regex]::Matches($logContent, "最佳.*?F1:\s*([\d.]+)")
    if ($altMatches -and $altMatches.Count -gt 0) {
        $bestF1 = [float]$altMatches[$altMatches.Count - 1].Groups[1].Value
    }
}

# Extract patience
$patienceMatch = [regex]::Match($logContent, "patience:\s*(\d+)/(\d+)")
$patienceCurrent = 0
$patienceMax = 30
if ($patienceMatch -and $patienceMatch.Success) {
    $patienceCurrent = [int]$patienceMatch.Groups[1].Value
    $patienceMax = [int]$patienceMatch.Groups[2].Value
}

# Read last status
$lastBestF1 = 0.0
if (Test-Path $StatusFile) {
    try {
        $json = Get-Content $StatusFile -Raw | ConvertFrom-Json
        $lastBestF1 = [float]$json.bestF1
    } catch { }
}

# Create status object
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$statusObj = @{
    currentEpoch = $currentEpoch
    latestF1 = $latestF1
    bestF1 = $bestF1
    patienceCurrent = $patienceCurrent
    patienceMax = $patienceMax
    lastUpdate = $timestamp
}

# Save status
$statusObj | ConvertTo-Json | Out-File $StatusFile -Encoding UTF8

# Output status
Write-Output "Training Status:"
Write-Output "  Epoch: $currentEpoch/200"
Write-Output "  Latest F1: $latestF1"
Write-Output "  Best F1: $bestF1"
Write-Output "  Patience: $patienceCurrent/$patienceMax"
Write-Output "  Last Update: $timestamp"
Write-Output "  Previous Best: $lastBestF1"

# Check for new best F1
$hasNewBest = ($bestF1 -gt $lastBestF1 -and $bestF1 -gt 0)

if ($hasNewBest) {
    Write-Output ""
    Write-Output "========================================"
    Write-Output "NEW BEST F1 DETECTED: $bestF1 (Epoch $currentEpoch)"
    Write-Output "========================================"
    
    # Prepare notification message for Feishu
    $message = @"
🎯 训练进度更新

Epoch: $currentEpoch/200
✨ 新最佳F1: $bestF1
📊 最新F1: $latestF1
⏱️ Patience: $patienceCurrent/$patienceMax
🕐 时间: $timestamp

#训练监控 #TemporalPEFT
"@
    
    # Save message to temp file for OpenClaw to send
    $msgFile = "D:\github\edge_infer_cloud\scripts\pending_notification.txt"
    $message | Out-File $msgFile -Encoding UTF8
    
    Write-Output "Notification saved to: $msgFile"
    Write-Output "Message preview:"
    Write-Output $message
    
    # Return notification JSON
    $result = @{
        hasNewBest = $true
        epoch = $currentEpoch
        bestF1 = $bestF1
        message = $message
        notifyFile = $msgFile
    }
    $result | ConvertTo-Json
} else {
    $result = @{ hasNewBest = $false }
    $result | ConvertTo-Json
}
