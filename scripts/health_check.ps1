# 系统健康检查脚本
# 用途: 检查系统资源使用情况和关键进程状态

Write-Host "=== 系统健康检查 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -ForegroundColor Cyan
Write-Host ""

# CPU使用率
$cpu = Get-WmiObject Win32_Processor | Measure-Object -Property LoadPercentage -Average
$cpuUsage = [math]::Round($cpu.Average, 2)
$cpuColor = if ($cpuUsage -gt 80) { "Red" } elseif ($cpuUsage -gt 60) { "Yellow" } else { "Green" }
Write-Host "CPU使用率: $cpuUsage%" -ForegroundColor $cpuColor

# 内存使用率
$mem = Get-WmiObject Win32_OperatingSystem
$memUsedMB = [math]::Round(($mem.TotalVisibleMemorySize - $mem.FreePhysicalMemory) / 1MB, 2)
$memTotalMB = [math]::Round($mem.TotalVisibleMemorySize / 1MB, 2)
$memUsage = [math]::Round(($mem.TotalVisibleMemorySize - $mem.FreePhysicalMemory) / $mem.TotalVisibleMemorySize * 100, 2)
$memColor = if ($memUsage -gt 80) { "Red" } elseif ($memUsage -gt 60) { "Yellow" } else { "Green" }
Write-Host "内存使用: $memUsedMB MB / $memTotalMB MB ($memUsage%)" -ForegroundColor $memColor

# 磁盘空间
Write-Host "`n磁盘使用:" -ForegroundColor Cyan
$disks = Get-WmiObject Win32_LogicalDisk | Where-Object { $_.DriveType -eq 3 }
foreach ($disk in $disks) {
    $diskUsedGB = [math]::Round(($disk.Size - $disk.FreeSpace) / 1GB, 2)
    $diskTotalGB = [math]::Round($disk.Size / 1GB, 2)
    $diskUsage = [math]::Round(($disk.Size - $disk.FreeSpace) / $disk.Size * 100, 2)
    $diskColor = if ($diskUsage -gt 80) { "Red" } elseif ($diskUsage -gt 60) { "Yellow" } else { "Green" }
    Write-Host "  $($disk.DeviceID) $diskUsedGB GB / $diskTotalGB GB ($diskUsage%)" -ForegroundColor $diskColor
}

# GPU信息 (如果有NVIDIA GPU)
Write-Host "`nGPU信息:" -ForegroundColor Cyan
try {
    $nvidiaSmi = & "C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe" --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader 2>$null
    if ($nvidiaSmi) {
        $gpuInfo = $nvidiaSmi.Split(", ")
        Write-Host "  GPU: $($gpuInfo[0])" -ForegroundColor Green
        Write-Host "  GPU使用率: $($gpuInfo[1])" -ForegroundColor Green
        Write-Host "  显存: $($gpuInfo[2]) / $($gpuInfo[3])" -ForegroundColor Green
    }
} catch {
    Write-Host "  未检测到NVIDIA GPU" -ForegroundColor Yellow
}

# 关键进程检查
Write-Host "`n关键进程:" -ForegroundColor Cyan

# 训练进程
$python = Get-Process -Name python -ErrorAction SilentlyContinue
if ($python) {
    Write-Host "  训练进程: 运行中" -ForegroundColor Green
    Write-Host "    PID: $($python.Id)"
    Write-Host "    内存: $([math]::Round($python.WorkingSet64 / 1MB, 2)) MB"
    Write-Host "    CPU时间: $($python.TotalProcessorTime.TotalSeconds) 秒"
} else {
    Write-Host "  训练进程: 未运行" -ForegroundColor Yellow
}

# Gateway进程
$node = Get-Process -Name node -ErrorAction SilentlyContinue
if ($node) {
    Write-Host "  Gateway: 运行中" -ForegroundColor Green
    Write-Host "    PID: $($node.Id)"
} else {
    Write-Host "  Gateway: 未运行" -ForegroundColor Red
}

# 后端进程 (Java)
$java = Get-Process -Name java -ErrorAction SilentlyContinue
if ($java) {
    Write-Host "  后端服务: 运行中" -ForegroundColor Green
    Write-Host "    PID: $($java.Id)"
} else {
    Write-Host "  后端服务: 未运行" -ForegroundColor Yellow
}

# 前端进程 (如果有)
$frontend = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -match "vite|npm" }
if ($frontend) {
    Write-Host "  前端服务: 运行中" -ForegroundColor Green
} else {
    Write-Host "  前端服务: 未运行" -ForegroundColor Yellow
}

# 网络连接检查
Write-Host "`n网络连接:" -ForegroundColor Cyan
$netConnection = Test-Connection -ComputerName www.baidu.com -Count 1 -Quiet -ErrorAction SilentlyContinue
if ($netConnection) {
    Write-Host "  互联网连接: 正常" -ForegroundColor Green
} else {
    Write-Host "  互联网连接: 异常" -ForegroundColor Red
}

# 系统运行时间
$os = Get-WmiObject Win32_OperatingSystem
$uptime = (Get-Date) - $os.ConvertToDateTime($os.LastBootUpTime)
Write-Host "`n系统运行时间: $($uptime.Days)天 $($uptime.Hours)小时 $($uptime.Minutes)分钟" -ForegroundColor Cyan

Write-Host "`n=== 检查完成 ===" -ForegroundColor Cyan
