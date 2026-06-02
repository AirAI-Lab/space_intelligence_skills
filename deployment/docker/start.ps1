#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Edge Cloud Platform — Windows 统一管理脚本
.DESCRIPTION
    合并原 start-wsl2.ps1 + init.ps1 + dev-restart.bat。
    一键管理 WSL2 Docker 部署：初始化、启动、停止、重启、keepalive。
.EXAMPLE
    .\start.ps1                   # 启动所有服务
    .\start.ps1 -Init             # 首次初始化
    .\start.ps1 -Restart backend  # 重启后端
    .\start.ps1 -Lite             # 仅 EMQX
    .\start.ps1 -Stop             # 停止所有
#>

param(
    [switch]$Init,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Rebuild,
    [switch]$ResetProxy,
    [string]$Restart,
    [switch]$Lite,
    [switch]$InstallKeepalive,
    [switch]$RemoveKeepalive,
    [switch]$CheckKeepalive
)

$ErrorActionPreference = "Stop"
$Ports = @(8081, 3000, 1883, 18083, 1935, 8089, 8333, 8888, 5001, 5002, 5432, 6379, 8889)
$ComposeFile = "docker-compose.dev.yml"
$WSLProjectPath = "~/edge_infer_cloud/deployment/docker"
$EnvFile = ""  # WSL2 path override

function Write-Info($msg)  { Write-Host "[INFO] $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Step($msg)  { Write-Host "[STEP] $msg" -ForegroundColor Cyan }

# ========== Keepalive ==========

$KeepaliveTaskName = "EdgeCloud-WSL2-Keepalive"

function Install-KeepaliveTask {
    $task = Get-ScheduledTask -TaskName $KeepaliveTaskName -ErrorAction SilentlyContinue
    if ($task) {
        Write-Info "Keepalive task already installed"
        return
    }
    Write-Step "Installing keepalive scheduled task..."
    # 直接用 wsl.exe 执行 bash sleep 循环，比 powershell wrapper 更稳定
    $action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d Ubuntu -- bash -c 'while true; do sleep 300; done'"
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -DontStopOnIdleEnd `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Days 365) `
        -RestartCount 999 `
        -RestartInterval (New-TimeSpan -Minutes 3) `
        -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $KeepaliveTaskName -Action $action -Trigger $trigger -Settings $settings -Description "Edge Cloud WSL2 keepalive session" -Force | Out-Null
    Write-Info "Keepalive task installed (wsl.exe direct)"
}

function Remove-KeepaliveTask {
    $task = Get-ScheduledTask -TaskName $KeepaliveTaskName -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $KeepaliveTaskName -Confirm:$false
        Write-Info "Keepalive task removed"
    } else {
        Write-Warn "Keepalive task not found"
    }
}

function Start-KeepaliveTask {
    $task = Get-ScheduledTask -TaskName $KeepaliveTaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Install-KeepaliveTask
        $task = Get-ScheduledTask -TaskName $KeepaliveTaskName -ErrorAction SilentlyContinue
    }

    # 强制重启 task（无论当前状态），确保 WSL2 会话存活
    if ($task.State -eq "Running") {
        Write-Info "Keepalive already running"
        return
    }

    # 尝试启动，最多重试 3 次
    $retries = 0
    while ($retries -lt 3) {
        Stop-ScheduledTask -TaskName $KeepaliveTaskName -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
        Start-ScheduledTask -TaskName $KeepaliveTaskName -ErrorAction Stop
        Start-Sleep -Seconds 3
        $task = Get-ScheduledTask -TaskName $KeepaliveTaskName
        if ($task.State -eq "Running") {
            Write-Info "Keepalive task started and running"
            return
        }
        $retries++
        Write-Warn "Keepalive start attempt $retries failed (state: $($task.State))"
    }
    Write-Warn "Keepalive task failed to start after 3 attempts. WSL2 may sleep during idle."
    Write-Warn "Manual fix: Start-ScheduledTask -TaskName $KeepaliveTaskName"
}

# ========== Port Proxy ==========

function Remove-PortProxy {
    foreach ($port in $Ports) {
        netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null | Out-Null
    }
}

function Setup-PortProxy {
    $rawOutput = wsl -d Ubuntu -- bash -c "hostname -I | cut -d' ' -f1" 2>&1 | Out-String
    $wslIp = ($rawOutput -split "`n" | Where-Object { $_ -match "^\d+\.\d+\.\d+\.\d+" } | Select-Object -First 1).Trim()
    if (-not $wslIp -or $wslIp -notmatch "^\d+\.\d+\.\d+\.\d+$") {
        Write-Warn "Cannot get WSL2 IP, skipping portproxy"
        return
    }
    foreach ($port in $Ports) {
        netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null | Out-Null
    }
    foreach ($port in $Ports) {
        netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wslIp
    }
    Write-Info "Portproxy: 0.0.0.0:* -> ${wslIp}:* ($($Ports.Count) ports)"
}

# ========== WSL Docker Helper ==========

# Check if .env.wsl2 exists and prepare env-file flag
$HasWsl2Env = (wsl -d Ubuntu -- bash -c "test -f ${WSLProjectPath}/.env.wsl2 && echo yes" 2>$null).Trim() -eq "yes"
if ($HasWsl2Env) {
    $EnvFile = "--env-file .env.wsl2"
}

function Invoke-WSLDocker($cmd) {
    wsl -d Ubuntu -- bash -c "cd $WSLProjectPath; $cmd"
}

# ========== Init (首次初始化) ==========

function Initialize-Environment {
    Write-Host "`n========== Edge Cloud 初始化向导 ==========" -ForegroundColor Cyan

    # 检查 Docker
    Write-Host "[1/5] 检查 WSL2 + Docker..." -ForegroundColor Yellow
    $wslOk = wsl -d Ubuntu -- docker version 2>$null
    if (-not $wslOk) {
        Write-Warn "WSL2 Docker 未就绪，尝试启动..."
        wsl -d Ubuntu -- bash -c "sudo service docker start 2>/dev/null"
        Start-Sleep -Seconds 5
        $wslOk = wsl -d Ubuntu -- docker version 2>$null
        if (-not $wslOk) { Write-Warn "Docker 仍未就绪，请检查安装"; return }
    }
    Write-Info "Docker OK"

    # 创建数据目录
    Write-Host "[2/5] 创建数据目录..." -ForegroundColor Yellow
    wsl -d Ubuntu -- bash -c 'mkdir -p ~/edge_infer_cloud/data/{runs,models,shared_models,work,datasets}'

    # 复制 .env
    Write-Host "[3/5] 配置环境变量..." -ForegroundColor Yellow
    $envFile = Join-Path $PSScriptRoot ".env"
    $envExample = Join-Path $PSScriptRoot ".env.example"
    if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
        Copy-Item $envExample $envFile
        Write-Info "已创建 .env，请检查 CLOUD_API_URL"
    } else {
        Write-Info ".env 已存在"
    }

    # GPU 检查
    Write-Host "[4/5] 检查 GPU..." -ForegroundColor Yellow
    $gpuOk = wsl -d Ubuntu -- nvidia-smi 2>$null
    if ($gpuOk) {
        Write-Info "NVIDIA GPU 可用"
    } else {
        Write-Warn "未检测到 GPU，训练服务将不可用"
    }

    # 选择模式
    Write-Host "[5/5] 选择启动模式..." -ForegroundColor Yellow
    Write-Host "  1. 完整平台 (推荐)"
    Write-Host "  2. 完整平台 + GPU 训练"
    Write-Host "  3. Lite 模式 (仅 MQTT)"
    $choice = Read-Host "请选择 (1-3)"

    switch ($choice) {
        "1" { Start-Services }
        "2" { Start-Services -WithGPU }
        "3" { Start-Services -LiteMode }
        default { Write-Warn "无效选择"; return }
    }
}

# ========== Start ==========

function Start-Services([switch]$WithGPU, [switch]$LiteMode) {
    # Step 1: Start Docker
    Write-Step "Starting WSL2 Docker..."
    wsl -d Ubuntu -- bash -c 'sudo rm -rf /etc/systemd/system/docker.service.d 2>/dev/null; sudo service docker start 2>/dev/null || true'
    Start-Sleep -Seconds 5

    # Step 2: Keepalive
    Write-Step "Ensuring keepalive session..."
    Start-KeepaliveTask

    # Step 3: Start containers
    Write-Step "Starting containers..."
    if ($LiteMode) {
        Invoke-WSLDocker "docker compose -f $ComposeFile $EnvFile up -d"
    } elseif ($WithGPU) {
        Invoke-WSLDocker "docker compose -f $ComposeFile $EnvFile --profile full --profile gpu up -d"
    } else {
        Invoke-WSLDocker "docker compose -f $ComposeFile $EnvFile --profile full up -d"
    }
    Start-Sleep -Seconds 5

    # Step 4: Wait for backend (skip in lite mode)
    if (-not $LiteMode) {
        Write-Step "Waiting for backend..."
        $retries = 0
        while ($retries -lt 30) {
            $health = curl.exe -s --connect-timeout 2 http://localhost:8081/actuator/health 2>$null
            if ($health -match "UP") { break }
            $retries++
            Start-Sleep -Seconds 3
            Write-Host "." -NoNewline
        }
        Write-Host ""
        if ($retries -ge 30) {
            Write-Warn "Backend startup timeout"
        } else {
            Write-Info "Backend ready"
        }
    }

    # Step 5: Portproxy
    Write-Step "Configuring port proxy (LAN access)..."
    Setup-PortProxy

    # Step 6: Show status
    Write-Host ""
    Write-Host "========== Startup Complete ==========" -ForegroundColor Green
    Write-Host ""
    if ($LiteMode) {
        Write-Host "Lite mode (MQTT only):"
        Write-Host "  EMQX:  http://localhost:18083 (admin/admin123456)"
    } else {
        Write-Host "Local access:"
        Write-Host "  Frontend:  http://localhost:3000"
        Write-Host "  Backend:   http://localhost:8081/api/v1"
        Write-Host "  EMQX:      http://localhost:18083 (admin/admin123456)"
        Write-Host "  RTMP:      rtmp://localhost:1935/stream/cam1"
        $lanIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -match "WLAN|Ethernet" -and $_.IPAddress -notmatch "^127\." } | Select-Object -First 1).IPAddress
        if ($lanIp) {
            Write-Host ""
            Write-Host "LAN access:" -ForegroundColor Yellow
            Write-Host "  Backend:  http://${lanIp}:8081" -ForegroundColor Yellow
            Write-Host "  MQTT:     tcp://${lanIp}:1883" -ForegroundColor Yellow
        }
    }
    Write-Host ""
}

# ========== Restart ==========

function Restart-Service($svc) {
    switch ($svc) {
        { $_ -in "backend", "b" } {
            Write-Step "Restarting backend..."
            Invoke-WSLDocker "docker compose -f $ComposeFile $EnvFile --profile full up -d --build --force-recreate backend"
        }
        { $_ -in "training", "t" } {
            Write-Step "Restarting training..."
            Invoke-WSLDocker "docker compose -f $ComposeFile $EnvFile --profile full --profile gpu up -d --build --force-recreate training"
        }
        { $_ -in "frontend", "f" } {
            Write-Step "Restarting frontend..."
            Invoke-WSLDocker "docker compose -f $ComposeFile $EnvFile --profile full up -d --build --force-recreate frontend"
        }
        { $_ -in "all", "a" } {
            Write-Step "Restarting all services..."
            Invoke-WSLDocker "docker compose -f $ComposeFile $EnvFile --profile full --profile gpu up -d --build --force-recreate"
        }
        default {
            Write-Warn "Unknown service: $svc"
            Write-Host "Usage: .\start.ps1 -Restart [backend|training|frontend|all]"
            return
        }
    }
    Write-Info "Done"
}

# ========== Dispatch ==========

if ($InstallKeepalive) {
    Install-KeepaliveTask
    Start-KeepaliveTask
    Write-Info "Done. Task auto-starts on every login."
    exit 0
}
if ($RemoveKeepalive) { Remove-KeepaliveTask; exit 0 }

if ($CheckKeepalive) {
    $task = Get-ScheduledTask -TaskName $KeepaliveTaskName -ErrorAction SilentlyContinue
    if ($task) {
        $info = $task | Get-ScheduledTaskInfo
        Write-Info "Task: $($task.State)"
        Write-Info "Last run: $($info.LastRunTime)"
    } else {
        Write-Warn "Keepalive task not installed. Run: .\start.ps1 -InstallKeepalive"
    }
    exit 0
}

if ($Init)      { Initialize-Environment; exit 0 }
if ($Stop)      {
    Write-Step "Stopping all services..."
    Invoke-WSLDocker "docker compose -f $ComposeFile $EnvFile --profile full --profile gpu down 2>/dev/null"
    Remove-PortProxy
    Write-Info "Stopped"
    exit 0
}
if ($Status)    {
    Write-Host "`n========== Container Status ==========" -ForegroundColor Cyan
    wsl -d Ubuntu -- bash -c 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter name=edge_cloud 2>/dev/null'
    Write-Host "`n========== Port Proxy ==========" -ForegroundColor Cyan
    netsh interface portproxy show v4tov4
    Write-Host ""
    exit 0
}
if ($Rebuild)   {
    Write-Step "Rebuilding training image..."
    Invoke-WSLDocker "docker compose -f $ComposeFile $EnvFile --profile gpu build training"
    Write-Info "Build complete"
    exit 0
}
if ($ResetProxy) { Remove-PortProxy; Setup-PortProxy; exit 0 }
if ($Restart)   { Restart-Service $Restart; exit 0 }
if ($Lite)      { Start-Services -LiteMode; exit 0 }

# Default: start full stack with GPU
Start-Services -WithGPU
