# 自动化提交安全策略

> **目的**: 确保自动化提交不会造成代码丢失
> **日期**: 2026-03-06

---

## 1. 安全措施

### 1.1 自动化脚本已添加保护

修改 `scripts/auto_commit.ps1`，添加以下检查：

```powershell
# 在提交前创建备份分支
function Create-BackupBranch {
    $date = Get-Date -Format 'yyyyMMdd-HHmm'
    $branchName = "auto-backup-$date"
    git branch $branchName
    Write-Host "已创建备份分支: $branchName" -ForegroundColor Green
}

# 检查是否有重要变更
function Check-ImportantChanges {
    $status = git status --porcelain
    $fileCount = ($status | Measure-Object).Count

    if ($fileCount -gt 50) {
        Write-Host "警告: 变更文件较多 ($fileCount 个)" -ForegroundColor Yellow
        Write-Host "建议先创建备份分支" -ForegroundColor Yellow
        Create-BackupBranch
    }
}

# 在执行提交前调用
Check-ImportantChanges
```

### 1.2 Heartbeat任务更新

修改 `HEARTBEAT.md`:

```markdown
# HEARTBEAT.md

## 训练状态检查 (每小时)
- 检查RCMT训练状态
- 如果训练完成，发送飞书通知

## 代码同步检查 (每4小时)
- 检查是否有未提交的代码变更
- **如果变更超过50个文件，先创建备份分支**
- 自动提交有意义的变更

## 日报生成 (每天18:00)
- 汇总今天的训练进度
- 汇总代码变更
- 生成简要日报
```

---

## 2. 版本标签策略

### 2.1 自动创建每日标签

创建 `scripts/daily_tag.ps1`:

```powershell
# 每天下班前自动创建标签
$date = Get-Date -Format 'yyyy-MM-dd'
$tagName = "daily-$date"

# 检查是否已有今天的标签
$existingTag = git tag -l $tagName
if (-not $existingTag) {
    # 创建标签
    $message = "每日快照: $date"
    git tag -a $tagName -m $message

    # 推送到远程
    git push origin $tagName

    Write-Host "已创建每日标签: $tagName" -ForegroundColor Green
} else {
    Write-Host "今天的标签已存在: $tagName" -ForegroundColor Yellow
}
```

### 2.2 功能里程碑标签

完成重要功能后：

```powershell
# 功能完成后创建标签
git tag -a v1.2.0-feature-name -m "功能描述"
git push origin v1.2.0-feature-name
```

---

## 3. 紧急回退方案

### 3.1 快速回退脚本

创建 `scripts/emergency_rollback.ps1`:

```powershell
param(
    [string]$Version = "v1.0.1-ota-enhancement"
)

Write-Host "=== 紧急回退到 $Version ===" -ForegroundColor Red

# 1. 保存当前工作
$currentBranch = git branch --show-current
$backupBranch = "emergency-backup-$(Get-Date -Format 'yyyyMMdd-HHmm')"
git branch $backupBranch
Write-Host "已创建紧急备份分支: $backupBranch" -ForegroundColor Yellow

# 2. 回退到指定版本
git checkout main
git reset --hard $Version

Write-Host "已回退到 $Version" -ForegroundColor Green
Write-Host "如需恢复，执行: git checkout $backupBranch" -ForegroundColor Cyan
```

### 3.2 使用方法

```powershell
# 回退到OTA功能版本
.\scripts\emergency_rollback.ps1 -Version "v1.0.1-ota-enhancement"

# 回退到今天早上
.\scripts\emergency_rollback.ps1 -Version "daily-2026-03-06"
```

---

## 4. 最佳实践

### 4.1 重大修改前

```powershell
# 1. 创建备份分支
git branch backup-before-<feature>

# 2. 推送到远程
git push origin backup-before-<feature>

# 3. 开始工作...
```

### 4.2 每天下班前

```powershell
# 1. 提交今天的变更
.\scripts\auto_commit.ps1

# 2. 创建每日标签
.\scripts\daily_tag.ps1

# 3. 推送所有分支和标签
git push --all
git push --tags
```

### 4.3 周末前

```powershell
# 1. 创建周末备份
git branch weekend-backup-$(Get-Date -Format 'yyyyMMdd')
git push origin weekend-backup-*

# 2. 打上周末标签
git tag -a weekend-$(Get-Date -Format 'yyyyMMdd') -m "周末快照"
git push origin weekend-*
```

---

## 5. 监控和告警

### 5.1 变更监控

在heartbeat中添加：

```markdown
## 变更监控 (每次心跳)
- 检查变更文件数量
- 如果 >50个文件，发送告警
- 如果 >100个文件，暂停自动提交
```

### 5.2 自动保护

创建 `scripts/check_before_commit.ps1`:

```powershell
# 检查是否需要保护
$changes = git status --porcelain | Measure-Object | Select-Object -ExpandProperty Count

if ($changes -gt 100) {
    Write-Host "警告: 变更文件过多 ($changes 个)" -ForegroundColor Red
    Write-Host "建议:" -ForegroundColor Yellow
    Write-Host "1. 检查是否误操作" -ForegroundColor Yellow
    Write-Host "2. 分批提交" -ForegroundColor Yellow
    Write-Host "3. 创建备份分支" -ForegroundColor Yellow

    # 发送飞书告警
    # TODO: 调用飞书API

    exit 1
}

exit 0
```

---

## 6. 当前版本清单

### 6.1 标签

- `v1.1.0-doc-restructure` (2026-03-06) - 文档重组
- `v1.0.1-ota-enhancement` (2026-02-06) - OTA功能

### 6.2 备份分支

- `backup-before-doc-restructure` - 文档重组前

### 6.3 可以随时回退的版本

```powershell
# 查看所有可用版本
git tag -l
git branch -a
```

---

**维护者**: SkyEdge AI Team
**创建日期**: 2026-03-06
