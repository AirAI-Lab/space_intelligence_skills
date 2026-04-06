# ACTA+ViT-Large 训练监控脚本
# 用途: 监听训练状态，在达到最佳结果时发送通知到飞书

param(
    [int]$CheckIntervalMinutes = 5,
    [switch]$Daemon
)

# 配置
$configFile = Join-Path $PSScriptRoot "training_monitor_config.json"
$stateFile = Join-Path $PSScriptRoot "acta_vit_monitor_state.json"

# 加载配置
function Get-Config {
    if (Test-Path $configFile) {
        return Get-Content $configFile -Raw | ConvertFrom-Json
    }
    return @{
        ContainerName = "rcmt-training"
        ContainerLogPath = "/workspace/peftcd_repro/peftcd_repro/artifacts/logs/acta_train.log"
        CheckIntervalMinutes = $CheckIntervalMinutes
        FeishuWebhook = ""
        NotificationChatId = ""
        BestMetricKey = "val_iou"
        TrainingType = "ACTA+ViT-Large"
        ProjectName = "PeftCD+ACTA"
    }
}

# 加载状态
function Get-State {
    if (Test-Path $stateFile) {
        return Get-Content $stateFile -Raw | ConvertFrom-Json
    }
    return @{
        LastCheck = $null
        BestIoU = 0
        BestF1 = 0
        LastEpoch = 0
        BestEpoch = 0
        NotificationsSent = @()
    }
}

# 保存状态
function Save-State {
    param($state)
    $state | ConvertTo-Json -Depth 5 | Set-Content $stateFile -Encoding UTF8
}

# 从 Docker 容器读取日志
function Get-ContainerLog {
    param([string]$ContainerName, [string]$LogPath)
    
    try {
        $log = docker exec $ContainerName bash -c "tail -100 $LogPath 2>/dev/null"
        if ($LASTEXITCODE -eq 0) {
            return $log -join "`n"
        }
    } catch {
        Write-Output "⚠ 无法从容器读取日志: $_"
    }
    return $null
}

# 解析日志内容
function Parse-LogContent {
    param([string]$content)
    
    $metrics = @{
        CurrentEpoch = 0
        TotalEpochs = 0
        Metrics = @{}
        IsRunning = $false
        IsCompleted = $false
        ErrorMessage = ""
        BestMetric = ""
        BestValue = 0
        HasNewBest = $false
    }
    
    if ([string]::IsNullOrWhiteSpace($content)) {
        return $metrics
    }
    
    # 提取 epoch 信息
    $epochMatch = $content | Select-String "Epoch\s+(\d+)/(\d+)\s+\|"
    if ($epochMatch) {
        $metrics.CurrentEpoch = [int]$epochMatch.Matches.Groups[1].Value
        $metrics.TotalEpochs = [int]$epochMatch.Matches.Groups[2].Value
        $metrics.IsRunning = $true
    }
    
    # 提取指标
    if ($content -match "val_f1=([\d.]+)") { $metrics.Metrics["val_f1"] = [double]$matches[1] }
    if ($content -match "val_iou=([\d.]+)") { $metrics.Metrics["val_iou"] = [double]$matches[1] }
    if ($content -match "val_p=([\d.]+)") { $metrics.Metrics["val_p"] = [double]$matches[1] }
    if ($content -match "val_r=([\d.]+)") { $metrics.Metrics["val_r"] = [double]$matches[1] }
    if ($content -match "train_loss=([\d.]+)") { $metrics.Metrics["train_loss"] = [double]$matches[1] }
    if ($content -match "val_loss=([\d.]+)") { $metrics.Metrics["val_loss"] = [double]$matches[1] }
    
    # 检查最佳结果
    $bestMatch = $content | Select-String "New best (IoU|F1) at epoch (\d+):\s*([\d.]+)"
    if ($bestMatch) {
        $metrics.BestMetric = $bestMatch.Matches.Groups[1].Value
        $metrics.BestValue = [double]$bestMatch.Matches.Groups[3].Value
        $metrics.HasNewBest = $true
    }
    
    # 检查完成和错误
    if ($content -match "Training completed|训练完成|Finished|All epochs completed") {
        $metrics.IsCompleted = $true
        $metrics.IsRunning = $false
    }
    
    if ($content -match "Error:|Exception:|CUDA out of memory|RuntimeError") {
        $errorMatch = $content | Select-String "(Error:|Exception:|RuntimeError).*" | Select-Object -Last 1
        $metrics.ErrorMessage = $errorMatch.Line
        $metrics.IsRunning = $false
    }
    
    return $metrics
}

# 发送飞书通知
function Send-FeishuNotification {
    param(
        [string]$Title,
        [string]$Message,
        [object]$Config
    )
    
    if ($Config.FeishuWebhook) {
        try {
            $body = @{
                msg_type = "interactive"
                card = @{
                    header = @{
                        title = @{
                            tag = "plain_text"
                            content = $Title
                        }
                        template = "blue"
                    }
                    elements = @(
                        @{
                            tag = "div"
                            text = @{
                                tag = "plain_text"
                                content = $Message
                            }
                        },
                        @{
                            tag = "note"
                            elements = @(
                                @{
                                    tag = "plain_text"
                                    content = "时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
                                }
                            )
                        }
                    )
                }
            } | ConvertTo-Json -Depth 5

            $response = Invoke-RestMethod -Uri $Config.FeishuWebhook -Method Post -Body $body -ContentType "application/json; charset=utf-8"
            
            if ($response.StatusCode -eq 0) {
                Write-Output "✓ 飞书通知发送成功"
                return $true
            } else {
                Write-Output "✗ 飞书通知发送失败: $($response.msg)"
                return $false
            }
        } catch {
            Write-Output "✗ 发送通知出错: $_"
            return $false
        }
    } else {
        Write-Output "⚠ 未配置飞书 Webhook"
        return $false
    }
}

# 主监控函数
function Invoke-TrainingMonitor {
    $config = Get-Config
    $state = Get-State
    
    Write-Output "`n=== $($config.TrainingType) 训练监控 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
    
    # 从容器读取日志
    $logContent = Get-ContainerLog -ContainerName $config.ContainerName -LogPath $config.ContainerLogPath
    
    if (-not $logContent) {
        Write-Output "⚠ 无法读取训练日志"
        return
    }
    
    # 解析日志
    $metrics = Parse-LogContent -content $logContent
    
    # 显示当前状态
    Write-Output "`n📊 当前训练状态:"
    if ($metrics.CurrentEpoch -gt 0) {
        $progress = [math]::Round($metrics.CurrentEpoch / $metrics.TotalEpochs * 100, 2)
        Write-Output "  Epoch: $($metrics.CurrentEpoch)/$($metrics.TotalEpochs) ($progress%)"
    }
    
    # 显示关键指标
    if ($metrics.Metrics.ContainsKey("val_iou")) {
        Write-Output "  Val IoU: $($metrics.Metrics['val_iou'])"
    }
    if ($metrics.Metrics.ContainsKey("val_f1")) {
        Write-Output "  Val F1: $($metrics.Metrics['val_f1'])"
    }
    if ($metrics.Metrics.ContainsKey("val_p")) {
        Write-Output "  Val Precision: $($metrics.Metrics['val_p'])"
    }
    if ($metrics.Metrics.ContainsKey("val_r")) {
        Write-Output "  Val Recall: $($metrics.Metrics['val_r'])"
    }
    if ($metrics.Metrics.ContainsKey("train_loss")) {
        Write-Output "  Train Loss: $($metrics.Metrics['train_loss'])"
    }
    if ($metrics.Metrics.ContainsKey("val_loss")) {
        Write-Output "  Val Loss: $($metrics.Metrics['val_loss'])"
    }
    
    if ($metrics.BestMetric) {
        Write-Output "  🏆 最佳 $($metrics.BestMetric): $($metrics.BestValue)" -ForegroundColor Green
    }
    
    if ($metrics.IsCompleted) {
        Write-Output "  状态: ✓ 训练完成"
    } elseif ($metrics.IsRunning) {
        Write-Output "  状态: ⏳ 训练中..."
    } elseif ($metrics.ErrorMessage) {
        Write-Output "  状态: ✗ 错误 - $($metrics.ErrorMessage)"
    }
    
    # 检查是否是新的最佳结果
    if ($metrics.HasNewBest -and $metrics.BestMetric -eq "IoU") {
        $currentIoU = $metrics.BestValue
        
        if ($currentIoU -gt $state.BestIoU) {
            Write-Output "`n🎉 检测到新的最佳 IoU: $currentIoU (之前: $($state.BestIoU))"
            
            # 构建通知消息
            $msgLines = @(
                "🎉 新的最佳 IoU 结果！",
                "",
                "Epoch: $($metrics.CurrentEpoch)/$($metrics.TotalEpochs)",
                "最佳 IoU: $currentIoU",
                "F1: $($metrics.Metrics['val_f1'])",
                "Precision: $($metrics.Metrics['val_p'])",
                "Recall: $($metrics.Metrics['val_r'])"
            )
            
            $notification = $msgLines -join "`n"
            
            # 发送飞书通知
            $sent = Send-FeishuNotification -Title "🎯 $($config.ProjectName) 训练更新" -Message $notification -Config $config
            
            # 更新状态
            $state.BestIoU = $currentIoU
            $state.BestF1 = $metrics.Metrics['val_f1']
            $state.BestEpoch = $metrics.CurrentEpoch
            
            if ($sent) {
                $state.NotificationsSent += @{
                    Timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
                    Epoch = $metrics.CurrentEpoch
                    IoU = $currentIoU
                    F1 = $metrics.Metrics['val_f1']
                }
            }
        }
    }
    
    # 更新状态
    $state.LastCheck = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    $state.LastEpoch = $metrics.CurrentEpoch
    Save-State -state $state
    
    Write-Output "`n✓ 监控检查完成"
}

# 主入口
if ($Daemon) {
    Write-Output "启动守护进程模式，检查间隔: $CheckIntervalMinutes 分钟"
    Write-Output "按 Ctrl+C 退出"
    
    while ($true) {
        Invoke-TrainingMonitor
        Start-Sleep -Seconds ($CheckIntervalMinutes * 60)
    }
} else {
    Invoke-TrainingMonitor
}
