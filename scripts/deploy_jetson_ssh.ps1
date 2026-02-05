# Jetson 部署脚本 - 自动化编译和启动

$JetsonIP = "192.168.0.104"
$Username = "nvidia"

Write-Host "=== Jetson 自动部署脚本 ===" -ForegroundColor Green
Write-Host ""

# 检查是否安装了 plink
$PlinkPaths = @(
    "C:\Program Files\PuTTY\plink.exe",
    "C:\Program Files (x86)\PuTTY\plink.exe",
    "$env:USERPROFILE\AppData\Local\Programs\PuTTY\plink.exe"
)

$PlinkPath = $null
foreach ($Path in $PlinkPaths) {
    if (Test-Path $Path) {
        $PlinkPath = $Path
        break
    }
}

# SSH 命令序列
$CommandSequence = @"
cd ~/edge_infer
git merge --abort 2>/dev/null || true
git reset --hard origin/master
rm -rf build
mkdir build && cd build
cmake .. -DUSE_TENSORRT=ON
make -j$(nproc)
echo "编译完成，edge_framework 位于 build/ 目录"
echo "启动命令: cd ~/edge_infer/build && ./edge_framework"
"@

if ($PlinkPath) {
    Write-Host "找到 plink: $PlinkPath" -ForegroundColor Green
    Write-Host "正在连接到 Jetson..." -ForegroundColor Cyan

    $Result = & $PlinkPath -ssh -l $Username -pw nvidia $JetsonIP $CommandSequence 2>&1
    Write-Host $Result
} else {
    Write-Host "未找到 plink.exe" -ForegroundColor Red
    Write-Host ""
    Write-Host "请手动执行以下步骤:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. 打开 PowerShell 或 CMD" -ForegroundColor White
    Write-Host "2. 执行: ssh $Username@$JetsonIP" -ForegroundColor Cyan
    Write-Host "3. 输入密码: nvidia" -ForegroundColor Cyan
    Write-Host "4. 复制并执行以下命令:" -ForegroundColor White
    Write-Host ""
    Write-Host $CommandSequence
}

Write-Host ""
Write-Host "=== 请检查编译结果 ===" -ForegroundColor Green
