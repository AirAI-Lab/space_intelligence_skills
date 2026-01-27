# ============================================
# edge_infer_cloud 初始化脚本 (Windows PowerShell)
# ============================================

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "edge_infer_cloud 初始化向导" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Docker
Write-Host "[1/6] 检查 Docker..." -ForegroundColor Yellow
try {
    docker version | Out-Null
    Write-Host "✓ Docker 已安装" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker 未安装或未启动" -ForegroundColor Red
    exit 1
}

# 检查 Git
Write-Host "[2/6] 检查 Git..." -ForegroundColor Yellow
try {
    git --version | Out-Null
    Write-Host "✓ Git 已安装" -ForegroundColor Green
} catch {
    Write-Host "✗ Git 未安装" -ForegroundColor Red
    exit 1
}

# 创建数据卷目录
Write-Host "[3/6] 创建数据卷目录..." -ForegroundColor Yellow
$baseVolumePath = "D:\docker\volumes\edge_cloud"
$volumes = @(
    "postgres_data",
    "redis_data",
    "seaweedfs_data",
    "file_storage_data",
    "mlflow_data",
    "emqx_data"
)

if (-not (Test-Path $baseVolumePath)) {
    New-Item -ItemType Directory -Path $baseVolumePath -Force | Out-Null
    Write-Host "✓ 创建基础目录: $baseVolumePath" -ForegroundColor Green
}

foreach ($volume in $volumes) {
    $path = Join-Path $baseVolumePath $volume
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "✓ 创建数据卷: $volume" -ForegroundColor Green
    }
}

# 复制环境变量文件
Write-Host "[4/6] 配置环境变量..." -ForegroundColor Yellow
$envFile = ".\.env"
$envExample = ".\.env.example"

if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "✓ 已创建 .env 文件" -ForegroundColor Green
    Write-Host "  请编辑 .env 文件，修改生产环境密码" -ForegroundColor Yellow
} else {
    Write-Host "✓ .env 文件已存在" -ForegroundColor Green
}

# 检查 GPU（可选）
Write-Host "[5/6] 检查 GPU 支持..." -ForegroundColor Yellow
try {
    nvidia-smi | Out-Null
    Write-Host "✓ 检测到 NVIDIA GPU" -ForegroundColor Green

    # 测试 Docker GPU 支持
    $gpuTest = docker run --rm --gpus all nvcr.io/nvidia/cuda:12.5.0-base-ubuntu22.04 nvidia-smi 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker GPU 支持正常" -ForegroundColor Green
        $gpuAvailable = $true
    } else {
        Write-Host "⚠ Docker GPU 支持未正确配置" -ForegroundColor Yellow
        Write-Host "  训练服务将无法使用 GPU" -ForegroundColor Yellow
        $gpuAvailable = $false
    }
} catch {
    Write-Host "⚠ 未检测到 NVIDIA GPU" -ForegroundColor Yellow
    Write-Host "  训练服务将使用 CPU（较慢）" -ForegroundColor Yellow
    $gpuAvailable = $false
}

# 选择启动模式
Write-Host ""
Write-Host "[6/6] 选择启动模式..." -ForegroundColor Yellow
Write-Host "1. 管理平台模式（不含 GPU 训练）" -ForegroundColor White
Write-Host "2. 完整平台模式（含 GPU 训练）" -ForegroundColor White
Write-Host "3. 退出" -ForegroundColor White
Write-Host ""

$choice = Read-Host "请选择 (1-3)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "启动管理平台..." -ForegroundColor Cyan
        docker-compose up -d

        Write-Host ""
        Write-Host "==================================" -ForegroundColor Green
        Write-Host "服务启动成功！" -ForegroundColor Green
        Write-Host "==================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "访问地址：" -ForegroundColor White
        Write-Host "  中文导航门户: http://localhost:8889" -ForegroundColor Cyan
        Write-Host "  前端: http://localhost:3000" -ForegroundColor Cyan
        Write-Host "  后端: http://localhost:8081" -ForegroundColor Cyan
        Write-Host "  API文档: http://localhost:8081/swagger-ui.html" -ForegroundColor Cyan
        Write-Host "  EMQX: http://localhost:18083 (admin/admin123456)" -ForegroundColor Cyan
        Write-Host "  MLflow: http://localhost:5001" -ForegroundColor Cyan
        Write-Host "  SeaweedFS: http://localhost:8888" -ForegroundColor Cyan
        Write-Host ""
    }
    "2" {
        if (-not $gpuAvailable) {
            Write-Host ""
            Write-Host "⚠ 警告: 未检测到 GPU 支持或配置不正确" -ForegroundColor Red
            $confirm = Read-Host "是否继续？ (y/N)"
            if ($confirm -ne "y") {
                exit 0
            }
        }

        Write-Host ""
        Write-Host "启动完整平台..." -ForegroundColor Cyan
        docker-compose --profile gpu up -d

        Write-Host ""
        Write-Host "==================================" -ForegroundColor Green
        Write-Host "服务启动成功！" -ForegroundColor Green
        Write-Host "==================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "访问地址：" -ForegroundColor White
        Write-Host "  中文导航门户: http://localhost:8889" -ForegroundColor Cyan
        Write-Host "  前端: http://localhost:3000" -ForegroundColor Cyan
        Write-Host "  后端: http://localhost:8081" -ForegroundColor Cyan
        Write-Host "  训练服务: http://localhost:5002" -ForegroundColor Cyan
        Write-Host "  EMQX: http://localhost:18083 (admin/admin123456)" -ForegroundColor Cyan
        Write-Host ""
    }
    "3" {
        Write-Host "退出" -ForegroundColor Yellow
        exit 0
    }
    default {
        Write-Host "无效选择" -ForegroundColor Red
        exit 1
    }
}

# 显示后续步骤
Write-Host "后续步骤：" -ForegroundColor White
Write-Host "1. 查看服务状态: docker-compose ps" -ForegroundColor Yellow
Write-Host "2. 查看日志: docker-compose logs -f" -ForegroundColor Yellow
Write-Host "3. 停止服务: docker-compose down" -ForegroundColor Yellow
Write-Host ""
