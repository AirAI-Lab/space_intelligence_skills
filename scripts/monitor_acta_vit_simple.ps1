# ACTA+ViT-Large 璁粌鐩戞帶鑴氭湰锛堢畝鍖栫増锛?# 鐩戝惉璁粌鐘舵€侊紝鍦ㄨ揪鍒版渶浣崇粨鏋滄椂璁板綍骞舵彁绀轰娇鐢?OpenClaw 鍙戦€侀€氱煡

param(
    [int]$CheckIntervalMinutes = 5,
    [switch]$Daemon,
    [switch]$SendNotificationNow
)

# 閰嶇疆
$ContainerName = "rcmt-training"
$ContainerLogPath = "/workspace/peftcd_repro/peftcd_repro/artifacts/logs/acta_train.log"
$stateFile = Join-Path $PSScriptRoot "acta_vit_monitor_state.json"

# 鍔犺浇鐘舵€?function Get-State {
    if (Test-Path $stateFile) {
        return Get-Content $stateFile -Raw | ConvertFrom-Json
    }
    return @{
        LastCheck = $null
        BestIoU = 0
        BestF1 = 0
        LastEpoch = 0
        BestEpoch = 0
        NotificationQueue = @()
    }
}

# 淇濆瓨鐘舵€?function Save-State {
    param($state)
    $state | ConvertTo-Json -Depth 5 | Set-Content $stateFile -Encoding UTF8
}

# 浠庡鍣ㄨ鍙栨棩蹇?function Get-ContainerLog {
    try {
        $log = docker exec $ContainerName bash -c "tail -100 $ContainerLogPath 2>/dev/null"
        if ($LASTEXITCODE -eq 0) {
            return $log -join "`n"
        }
    } catch { }
    return $null
}

# 瑙ｆ瀽鏃ュ織
function Parse-LogContent {
    param([string]$content)
    
    $metrics = @{
        CurrentEpoch = 0
        TotalEpochs = 0
        ValIoU = 0
        ValF1 = 0
        ValP = 0
        ValR = 0
        TrainLoss = 0
        ValLoss = 0
        BestMetric = ""
        BestValue = 0
        HasNewBest = $false
        IsRunning = $false
        IsCompleted = $false
        ErrorMessage = ""
    }
    
    if ([string]::IsNullOrWhiteSpace($content)) { return $metrics }
    
    # 鎻愬彇 epoch
    if ($content -match "Epoch\s+(\d+)/(\d+)\s+\|") {
        $metrics.CurrentEpoch = [int]$matches[1]
        $metrics.TotalEpochs = [int]$matches[2]
        $metrics.IsRunning = $true
    }
    
    # 鎻愬彇鎸囨爣
    if ($content -match "val_iou=([\d.]+)") { $metrics.ValIoU = [double]$matches[1] }
    if ($content -match "val_f1=([\d.]+)") { $metrics.ValF1 = [double]$matches[1] }
    if ($content -match "val_p=([\d.]+)") { $metrics.ValP = [double]$matches[1] }
    if ($content -match "val_r=([\d.]+)") { $metrics.ValR = [double]$matches[1] }
    if ($content -match "train_loss=([\d.]+)") { $metrics.TrainLoss = [double]$matches[1] }
    if ($content -match "val_loss=([\d.]+)") { $metrics.ValLoss = [double]$matches[1] }
    
    # 妫€鏌ユ渶浣崇粨鏋?    if ($content -match "New best (IoU|F1) at epoch \d+:\s*([\d.]+)") {
        $metrics.BestMetric = $matches[1]
        $metrics.BestValue = [double]$matches[2]
        $metrics.HasNewBest = $true
    }
    
    # 妫€鏌ュ畬鎴?閿欒
    if ($content -match "Training completed|璁粌瀹屾垚") {
        $metrics.IsCompleted = $true
        $metrics.IsRunning = $false
    }
    if ($content -match "Error:|Exception:|RuntimeError") {
        $metrics.IsRunning = $false
        $metrics.ErrorMessage = "璁粌鍑洪敊"
    }
    
    return $metrics
}

# 鐢熸垚閫氱煡娑堟伅
function New-NotificationMessage {
    param($metrics, $previousBest)
    
    $lines = @(
        "**馃帀 鏂扮殑鏈€浣?IoU 缁撴灉锛?*",
        "",
        "**Epoch:** $($metrics.CurrentEpoch)/$($metrics.TotalEpochs)",
        "**鏈€浣?IoU:** $($metrics.ValIoU)",
        "**F1 Score:** $($metrics.ValF1)",
        "**Precision:** $($metrics.ValP)",
        "**Recall:** $($metrics.ValR)",
        "**Train Loss:** $($metrics.TrainLoss)",
        "**Val Loss:** $($metrics.ValLoss)"
    )
    
    if ($previousBest -gt 0) {
        $improvement = [math]::Round(($metrics.ValIoU - $previousBest) * 100, 2)
        $lines += "`n**鎻愬崌:** +$improvement%"
    }
    
    return $lines -join "`n"
}

# 涓荤洃鎺у嚱鏁?function Invoke-TrainingMonitor {
    $state = Get-State
    
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Write-Output "`n========================================"
    Write-Output "ACTA+ViT-Large 璁粌鐩戞帶"
    Write-Output "鏃堕棿: $timestamp"
    Write-Output "========================================"
    
    # 璇诲彇鏃ュ織
    $logContent = Get-ContainerLog
    if (-not $logContent) {
        Write-Output "鈿?鏃犳硶璇诲彇璁粌鏃ュ織"
        return
    }
    
    # 瑙ｆ瀽
    $metrics = Parse-LogContent -content $logContent
    
    # 鏄剧ず鐘舵€?    Write-Output "`n馃搳 璁粌鐘舵€?"
    if ($metrics.CurrentEpoch -gt 0) {
        $progress = [math]::Round($metrics.CurrentEpoch / $metrics.TotalEpochs * 100, 2)
        Write-Output "  Epoch: $($metrics.CurrentEpoch)/$($metrics.TotalEpochs) ($progress%)"
    }
    
    Write-Output "  Val IoU: $($metrics.ValIoU)"
    Write-Output "  Val F1: $($metrics.ValF1)"
    Write-Output "  Val Precision: $($metrics.ValP)"
    Write-Output "  Val Recall: $($metrics.ValR)"
    Write-Output "  Train Loss: $($metrics.TrainLoss)"
    Write-Output "  Val Loss: $($metrics.ValLoss)"
    
    if ($metrics.BestMetric) {
        Write-Output "`n  馃弳 褰撳墠鏈€浣?$($metrics.BestMetric): $($metrics.BestValue)"
    }
    
    if ($metrics.IsCompleted) {
        Write-Output "`n  鉁?璁粌瀹屾垚"
    } elseif ($metrics.IsRunning) {
        Write-Output "`n  鈴?璁粌杩涜涓?.."
    } elseif ($metrics.ErrorMessage) {
        Write-Output "`n  鉁?$($metrics.ErrorMessage)"
    }
    
    # 妫€鏌ユ柊鐨勬渶浣崇粨鏋?    if ($metrics.HasNewBest -and $metrics.BestMetric -eq "IoU" -and $metrics.ValIoU -gt $state.BestIoU) {
        Write-Output "`n馃帀 妫€娴嬪埌鏂扮殑鏈€浣?IoU: $($metrics.ValIoU) (涔嬪墠: $($state.BestIoU))"
        
        # 鐢熸垚閫氱煡
        $notification = New-NotificationMessage -metrics $metrics -previousBest $state.BestIoU
        
        # 淇濆瓨鍒伴槦鍒?        $state.NotificationQueue += @{
            Timestamp = $timestamp
            Epoch = $metrics.CurrentEpoch
            IoU = $metrics.ValIoU
            F1 = $metrics.ValF1
            Message = $notification
        }
        
        # 鏇存柊鏈€浣冲€?        $state.BestIoU = $metrics.ValIoU
        $state.BestF1 = $metrics.ValF1
        $state.BestEpoch = $metrics.CurrentEpoch
        
        Write-Output "`n馃摑 閫氱煡宸插姞鍏ラ槦鍒楋紝绛夊緟鍙戦€?.."
        Write-Output "`n閫氱煡鍐呭:"
        Write-Output $notification
        
        # 濡傛灉鎸囧畾绔嬪嵆鍙戦€?        if ($SendNotificationNow) {
            Write-Output "`n鉁?宸叉爣璁颁负绔嬪嵆鍙戦€佹ā寮?
        }
    }
    
    # 鏇存柊鐘舵€?    $state.LastCheck = $timestamp
    $state.LastEpoch = $metrics.CurrentEpoch
    Save-State -state $state
    
    Write-Output "`n鉁?鐩戞帶妫€鏌ュ畬鎴?
    
    # 杩斿洖闃熷垪鐢ㄤ簬澶栭儴澶勭悊
    return $state.NotificationQueue
}

# 涓诲叆鍙?if ($Daemon) {
    Write-Output "鍚姩瀹堟姢杩涚▼妯″紡锛屾鏌ラ棿闅? $CheckIntervalMinutes 鍒嗛挓"
    Write-Output "鎸?Ctrl+C 閫€鍑?
    Write-Output ""
    
    while ($true) {
        $queue = Invoke-TrainingMonitor
        
        # 濡傛灉鏈夐€氱煡闃熷垪锛岃緭鍑哄埌鏂囦欢渚?OpenClaw 璇诲彇
        if ($queue -and $queue.Count -gt 0) {
            $notificationFile = Join-Path $PSScriptRoot "pending_notifications.json"
            $queue | ConvertTo-Json -Depth 5 | Set-Content $notificationFile -Encoding UTF8
            Write-Output "`n馃摡 閫氱煡宸蹭繚瀛樺埌: $notificationFile"
        }
        
        Start-Sleep -Seconds ($CheckIntervalMinutes * 60)
    }
} else {
    Invoke-TrainingMonitor
}
