# 暂停训练并运行验证脚本
# 使用方法: 在 PowerShell 中运行 .\pause_and_validate.ps1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "      RCMT-V3 暂停训练并运行验证" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 检查当前 GPU 状态
Write-Host "📊 检查 GPU 状态..." -ForegroundColor Yellow
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits

Write-Host ""
Write-Host "⚠️  警告: 这将暂停正在进行的训练!" -ForegroundColor Red
Write-Host ""
$confirm = Read-Host "是否继续? (y/n)"

if ($confirm -ne "y") {
    Write-Host "❌ 操作已取消" -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "🛑 查找训练进程..." -ForegroundColor Yellow

# 查找 Python 训练进程
$pythonProcesses = Get-Process python* -ErrorAction SilentlyContinue | 
    Where-Object { $_.MainWindowTitle -like "*train*" -or $_.CommandLine -like "*rcmt_v3*" }

if ($pythonProcesses) {
    Write-Host "   找到训练进程:" -ForegroundColor Green
    $pythonProcesses | Format-Table Id, ProcessName, CPU, WorkingSet -AutoSize
    
    $stop = Read-Host "是否停止这些进程? (y/n)"
    if ($stop -eq "y") {
        $pythonProcesses | Stop-Process -Force
        Write-Host "✅ 训练进程已停止" -ForegroundColor Green
        Start-Sleep -Seconds 5
    }
} else {
    Write-Host "   未找到训练进程" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🧹 清理 GPU 缓存..." -ForegroundColor Yellow
python -c "import torch; torch.cuda.empty_cache(); print('GPU cache cleared')"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "🔍 开始验证..." -ForegroundColor Yellow
Write-Host ""

# 运行验证脚本
Set-Location "D:\github\edge_infer_cloud\validation_results"

python quick_validate.py `
    --data-dir "D:\data\LEVIR-CD256" `
    --config "../models/rcmt_v3/configs/rcmt_v3_swin.yaml" `
    --model-path "D:/github/edge_infer/rcmt_v3/checkpoints_swin_final/best_model.pth" `
    --num-samples 5 `
    --output-dir "./sysu_cd_demo"

Write-Host ""
Write-Host "✅ 验证完成!" -ForegroundColor Green
Write-Host ""
Write-Host "📂 结果保存在: D:\github\edge_infer_cloud\validation_results\sysu_cd_demo" -ForegroundColor Cyan
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan

# 询问是否恢复训练
Write-Host ""
$resume = Read-Host "是否恢复训练? (y/n)"

if ($resume -eq "y") {
    Write-Host ""
    Write-Host "🔄 恢复训练..." -ForegroundColor Yellow
    
    Set-Location "D:\github\edge_infer\rcmt_v3"
    
    Start-Process python -ArgumentList `
        "train_rcmt_v3_swin_temporal.py", `
        "--resume", "checkpoints_swin_final/latest_checkpoint.pth" `
        -NoNewWindow
    
    Write-Host "✅ 训练已恢复" -ForegroundColor Green
}

Write-Host ""
Write-Host "完成!" -ForegroundColor Green
