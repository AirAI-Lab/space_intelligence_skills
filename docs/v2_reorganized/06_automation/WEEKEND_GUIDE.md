# 周末自动化快速启动指南

> **目标**: 确保OpenClaw在周末期间持续工作
> **时间**: 周五配置，周末自动运行

---

## 1. 立即执行 (现在)

### 1.1 检查Gateway状态

```powershell
# 方法1: 检查进程
Get-Process -Name node -ErrorAction SilentlyContinue | Select-Object ProcessName, Id, StartTime

# 方法2: 如果有openclaw命令
openclaw status
```

### 1.2 确保Gateway运行

```powershell
# 如果Gateway未运行，启动它
openclaw gateway start

# 或者后台运行
Start-Process powershell -ArgumentList "-NoExit", "-Command", "openclaw gateway start"
```

### 1.3 测试远程控制

**通过手机飞书发送**:
```
@delegate 汇报当前状态
```

应该收到回复确认系统正常。

---

## 2. 周末前配置 (周五)

### 2.1 配置自动检查任务

编辑 `HEARTBEAT.md`:

```markdown
# HEARTBEAT.md

## 任务列表

### 1. 训练监控 (每次心跳)
- 检查 D:\github\edge_infer\rcmt_v3\logs_swin_final_v2\train.log
- 如果训练完成或出错，发送飞书通知

### 2. 代码同步 (每4小时)
- 检查未提交的变更
- 自动提交有意义的改动

### 3. 日报生成 (每天18:00)
- 汇总训练进度
- 汇总代码变更
```

### 2.2 配置Git自动提交 (可选)

创建 `scripts\auto_commit.ps1`:

```powershell
# 自动提交脚本
$workspace = "D:\github\edge_infer_cloud"
cd $workspace

# 检查是否有变更
$status = git status --porcelain
if ($status) {
    # 提交变更
    git add .
    git commit -m "自动提交: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    git push
    Write-Host "已提交变更"
} else {
    Write-Host "无变更需要提交"
}
```

### 2.3 配置Windows任务计划 (可选)

```powershell
# 每小时运行一次
$action = New-ScheduledTaskAction -Execute "powershell" `
    -Argument "-File D:\github\edge_infer_cloud\scripts\auto_commit.ps1"
$trigger = New-ScheduledTaskTrigger -Hourly
Register-ScheduledTask -TaskName "SkyEdge-AutoCommit" -Action $action -Trigger $trigger
```

---

## 3. 远程控制指令

### 3.1 基础指令

```
# 汇报状态
@delegate 汇报空中智能体项目当前状态

# 训练监控
@delegate 算法开发代理: 检查Swin V2训练进度
@delegate 算法开发代理: 训练完成了吗？F1达到多少？

# 代码管理
@delegate 软件开发代理: 提交今天的代码变更
@delegate 软件开发代理: 检查是否有未提交的改动

# 文档更新
@delegate 更新MEMORY.md，记录今天的进度
```

### 3.2 高级指令

```
# 生成周报
@delegate 生成本周工作总结，包括训练进度和代码变更

# 分析问题
@delegate 算法开发代理: 分析训练日志，检查是否有异常

# 优化建议
@delegate 基于当前训练状态，给出下一步优化建议
```

### 3.3 紧急指令

```
# 停止任务
@delegate 停止所有训练任务

# 告警
@delegate 发送告警：训练异常，请检查

# 系统状态
@delegate 检查系统资源使用情况
```

---

## 4. 监控脚本

### 4.1 训练监控脚本

创建 `scripts\monitor_training.ps1`:

```powershell
# 训练监控脚本
$logFile = "D:\github\edge_infer\rcmt_v3\logs_swin_final_v2\train.log"
$lastLines = Get-Content $logFile -Tail 20

# 检查训练状态
if ($lastLines -match "训练完成") {
    Write-Host "训练已完成！"
    # TODO: 发送飞书通知
} elseif ($lastLines -match "Error|Exception") {
    Write-Host "训练出错！"
    # TODO: 发送告警
} else {
    # 提取当前epoch和F1
    $epoch = ($lastLines | Select-String "Epoch (\d+)/300" | Select-Object -Last 1).Matches.Groups[1].Value
    $f1 = ($lastLines | Select-String "F1: ([\d.]+)" | Select-Object -Last 1).Matches.Groups[1].Value
    Write-Host "训练进行中: Epoch $epoch/300, F1: $f1"
}
```

### 4.2 系统健康检查

创建 `scripts\health_check.ps1`:

```powershell
# 系统健康检查
Write-Host "=== 系统健康检查 $(Get-Date -Format 'yyyy-MM-dd HH:mm') ==="

# CPU使用率
$cpu = Get-WmiObject Win32_Processor | Measure-Object -Property LoadPercentage -Average
Write-Host "CPU使用率: $($cpu.Average)%"

# 内存使用率
$mem = Get-WmiObject Win32_OperatingSystem
$memUsage = [math]::Round(($mem.TotalVisibleMemorySize - $mem.FreePhysicalMemory) / $mem.TotalVisibleMemorySize * 100, 2)
Write-Host "内存使用率: $memUsage%"

# 磁盘空间
$disk = Get-WmiObject Win32_LogicalDisk -Filter "DeviceID='C:'"
$diskUsage = [math]::Round(($disk.Size - $disk.FreeSpace) / $disk.Size * 100, 2)
Write-Host "磁盘使用率: $diskUsage%"

# 训练进程
$python = Get-Process -Name python -ErrorAction SilentlyContinue
if ($python) {
    Write-Host "训练进程: 运行中 (PID: $($python.Id))"
} else {
    Write-Host "训练进程: 未运行"
}

# Gateway进程
$node = Get-Process -Name node -ErrorAction SilentlyContinue
if ($node) {
    Write-Host "Gateway进程: 运行中 (PID: $($node.Id))"
} else {
    Write-Host "Gateway进程: 未运行"
}
```

---

## 5. 周末后恢复 (周一)

### 5.1 检查任务

```powershell
# 检查训练状态
D:\github\edge_infer_cloud\scripts\monitor_training.ps1

# 检查系统状态
D:\github\edge_infer_cloud\scripts\health_check.ps1

# 检查代码同步
cd D:\github\edge_infer_cloud
git status
git log --oneline --since="Friday"
```

### 5.2 汇总周末进度

```
@delegate 生成本周末的工作总结报告
```

---

## 6. 故障处理

### 6.1 Gateway意外停止

```powershell
# 重启Gateway
openclaw gateway restart

# 或重新启动
openclaw gateway stop
openclaw gateway start
```

### 6.2 训练意外中断

```
@delegate 算法开发代理: 检查训练日志，找出中断原因
@delegate 算法开发代理: 如果可能，恢复训练
```

### 6.3 无法远程控制

1. 检查Gateway是否运行
2. 检查网络连接
3. 重启Gateway

---

## 7. 注意事项

1. **保持电脑开机** - 方案1要求电脑持续运行
2. **网络稳定** - 确保网络连接稳定
3. **电源管理** - 关闭自动休眠和睡眠
4. **定期检查** - 周末至少远程检查一次

---

**创建日期**: 2026-03-06
**更新日期**: 2026-03-06
