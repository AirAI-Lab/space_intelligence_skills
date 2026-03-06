# 自动代码提交脚本
# 用途: 自动检查并提交代码变更

param(
    [string]$Workspace = "D:\github\edge_infer_cloud",
    [string]$Message = "",
    [switch]$Force
)

Write-Host "=== 自动代码提交 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -ForegroundColor Cyan

cd $Workspace

# 检查是否有变更
$status = git status --porcelain
if (-not $status) {
    Write-Host "无变更需要提交" -ForegroundColor Green
    exit 0
}

Write-Host "发现以下变更:" -ForegroundColor Yellow
git status --short

# 生成提交消息
if (-not $Message) {
    $date = Get-Date -Format 'yyyy-MM-dd HH:mm'
    $changedFiles = ($status | Measure-Object).Count
    $Message = "自动提交: $changedFiles 个文件变更 ($date)"
}

Write-Host "`n提交消息: $Message" -ForegroundColor Cyan

# 如果不是强制模式，询问确认
if (-not $Force) {
    $confirm = Read-Host "确认提交? (y/n)"
    if ($confirm -ne "y") {
        Write-Host "取消提交" -ForegroundColor Yellow
        exit 0
    }
}

# 添加所有变更
git add .
Write-Host "已添加所有变更" -ForegroundColor Green

# 提交
git commit -m $Message
if ($LASTEXITCODE -eq 0) {
    Write-Host "提交成功" -ForegroundColor Green
} else {
    Write-Host "提交失败" -ForegroundColor Red
    exit 1
}

# 推送
git push
if ($LASTEXITCODE -eq 0) {
    Write-Host "推送成功" -ForegroundColor Green
} else {
    Write-Host "推送失败，可能需要手动处理" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n=== 提交完成 ===" -ForegroundColor Cyan
