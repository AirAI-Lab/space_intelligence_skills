#Requires -RunAsAdministrator
<#
.SYNOPSIS
    WSL2 Edge Cloud Platform Startup Script
.DESCRIPTION
    One-click startup: WSL2 Docker + containers + Windows portproxy.
    Requires admin privileges (for netsh portproxy).
.EXAMPLE
    .\start-wsl2.ps1
    .\start-wsl2.ps1 -Stop
    .\start-wsl2.ps1 -Status
#>

param(
    [switch]$Stop,
    [switch]$Status,
    [switch]$Rebuild,
    [switch]$ResetProxy
)

$ErrorActionPreference = "Stop"
$Ports = @(8081, 3000, 1883, 18083, 1935, 8089, 8333, 8888, 5001, 5002, 5432, 6379, 8889)
$ProjectDir = "$PSScriptRoot"

function Write-Info($msg)  { Write-Host "[INFO] $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Step($msg)  { Write-Host "[STEP] $msg" -ForegroundColor Cyan }

# ========== Helper Functions ==========

function Remove-PortProxy {
    Write-Info "Removing port proxy rules..."
    foreach ($port in $Ports) {
        netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null | Out-Null
    }
}

function Setup-PortProxy {
    $wslIp = (wsl -d Ubuntu -- bash -c "hostname -I | cut -d' ' -f1" 2>$null).Trim()

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

    Write-Info "Portproxy configured: 0.0.0.0:* -> ${wslIp}:* ($($Ports.Count) ports)"

    $testResult = curl.exe -s --connect-timeout 3 "http://${wslIp}:8081/actuator/health" 2>$null
    if ($testResult -match "UP") {
        Write-Info "Portproxy verification passed"
    } else {
        Write-Warn "Portproxy verification failed, check Windows Firewall"
        Write-Warn "Run in admin PowerShell:"
        Write-Warn '  New-NetFirewallRule -DisplayName "Edge Cloud" -Direction Inbound -Protocol TCP -LocalPort 8081,3000,1883,18083,1935,8089,8333,8888,5001,5002,5432,6379,8889 -Action Allow -Profile Any'
    }
}

# ========== Stop ==========
if ($Stop) {
    Write-Step "Stopping all services..."
    wsl -d Ubuntu -- bash -c "cd ~/edge_infer_cloud/deployment/docker; docker compose --profile standard --profile gpu down 2>/dev/null"
    Remove-PortProxy
    Write-Info "Stopped"
    exit 0
}

# ========== Status ==========
if ($Status) {
    Write-Host "`n========== Container Status ==========" -ForegroundColor Cyan
    wsl -d Ubuntu -- bash -c "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' --filter name=edge_cloud 2>/dev/null"
    Write-Host "`n========== Port Proxy ==========" -ForegroundColor Cyan
    netsh interface portproxy show v4tov4
    Write-Host ""
    exit 0
}

# ========== Rebuild ==========
if ($Rebuild) {
    Write-Step "Rebuilding training image..."
    wsl -d Ubuntu -- bash -c "cd ~/edge_infer_cloud/deployment/docker; docker compose --profile gpu build training"
    Write-Info "Build complete"
    exit 0
}

# ========== Reset Proxy ==========
if ($ResetProxy) {
    Remove-PortProxy
    Setup-PortProxy
    exit 0
}

# ========== Main: Start Services ==========

# Step 1: Start WSL2 Docker (clean Docker Desktop proxy remnants)
Write-Step "Starting WSL2 Docker..."
wsl -d Ubuntu -- bash -c "sudo rm -rf /etc/systemd/system/docker.service.d 2>/dev/null; sudo service docker start 2>/dev/null || sudo dockerd &"
Start-Sleep -Seconds 5

$dockerOk = wsl -d Ubuntu -- docker info 2>$null
if (-not $dockerOk) {
    Write-Warn "Docker not ready, waiting..."
    Start-Sleep -Seconds 10
}

# Step 2: Start containers
Write-Step "Starting containers..."
wsl -d Ubuntu -- bash -c "cd ~/edge_infer_cloud/deployment/docker; docker compose --profile standard --profile gpu up -d"
Start-Sleep -Seconds 5

# Step 3: Wait for backend
Write-Step "Waiting for backend..."
$retries = 0
while ($retries -lt 30) {
    $health = curl.exe -s --connect-timeout 2 http://localhost:8081/actuator/health 2>$null
    if ($health -match "UP") {
        break
    }
    $retries++
    Start-Sleep -Seconds 3
    Write-Host "." -NoNewline
}
Write-Host ""

if ($retries -ge 30) {
    Write-Warn "Backend startup timeout. Check: wsl -d Ubuntu -- docker logs edge_cloud_backend"
} else {
    Write-Info "Backend ready"
}

# Step 4: Configure portproxy
Write-Step "Configuring port proxy (LAN access)..."
Setup-PortProxy

# Step 5: Show status
Write-Host ""
Write-Host "========== Startup Complete ==========" -ForegroundColor Green
Write-Host ""
Write-Host "Local access (localhost):"
Write-Host "  Frontend:  http://localhost:3000"
Write-Host "  Backend:   http://localhost:8081/api/v1"
Write-Host "  EMQX:      http://localhost:18083 (admin/admin123456)"
Write-Host "  RTMP:      rtmp://localhost:1935/stream/cam1"
Write-Host ""
Write-Host "LAN access (Jetson and other devices):"
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -match "WLAN|Ethernet" -and $_.IPAddress -notmatch "^127\." } | Select-Object -First 1).IPAddress
if ($lanIp) {
    Write-Host "  Backend:  http://${lanIp}:8081" -ForegroundColor Yellow
    Write-Host "  MQTT:     tcp://${lanIp}:1883" -ForegroundColor Yellow
    Write-Host "  RTMP:     rtmp://${lanIp}:1935/stream/cam1" -ForegroundColor Yellow
}
Write-Host ""
