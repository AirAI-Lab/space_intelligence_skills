# ============================================
# edge_infer_cloud Docker 环境一键安装脚本 (Windows PowerShell)
# 用法: powershell -ExecutionPolicy Bypass -File .\scripts\install_docker.ps1 [-WithGPU]
# 需要以管理员身份运行
# ============================================

param(
    [switch]$WithGPU = $false
)

$ErrorActionPreference = "Stop"

# 颜色辅助函数
function Write-Info($msg)  { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Fail($msg)  { Write-Host "[FAIL] $msg" -ForegroundColor Red }

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  edge_infer_cloud Docker 环境安装" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# ---------- 检查管理员权限 ----------
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warn "建议以管理员身份运行此脚本"
    Write-Host "右键 PowerShell -> 以管理员身份运行" -ForegroundColor Yellow
    Write-Host ""
}

# ---------- 1. 检查/安装 Docker Desktop ----------
Write-Info "[1/6] 检查 Docker..."

$dockerInstalled = $false
try {
    $dockerVer = docker --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Docker 已安装: $dockerVer"
        $dockerInstalled = $true
    }
} catch {}

if (-not $dockerInstalled) {
    Write-Info "Docker 未安装，正在准备安装..."

    # 检查 WSL2
    Write-Info "检查 WSL2..."
    $wslStatus = wsl --status 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Info "正在启用 WSL2..."
        dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart 2>$null
        dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart 2>$null
        Write-Warn "WSL2 已启用，可能需要重启电脑后再次运行此脚本"
        Write-Host "请重启后重新运行: powershell -ExecutionPolicy Bypass -File .\scripts\install_docker.ps1" -ForegroundColor Yellow
        exit 0
    }
    Write-Ok "WSL2 已就绪"

    # 下载 Docker Desktop
    $dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"
    $dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"

    Write-Info "正在下载 Docker Desktop..."
    try {
        Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller -UseBasicParsing
        Write-Ok "下载完成"
    } catch {
        Write-Fail "下载失败，请手动下载安装: https://www.docker.com/products/docker-desktop/"
        Write-Host "下载后双击安装，勾选 'Use WSL 2 based engine'" -ForegroundColor Yellow
        exit 1
    }

    # 安装
    Write-Info "正在安装 Docker Desktop（需要几分钟）..."
    Start-Process -FilePath $dockerInstaller -ArgumentList "install", "--quiet", "--accept-license" -Wait -NoNewWindow

    # 清理安装包
    Remove-Item -Path $dockerInstaller -Force -ErrorAction SilentlyContinue

    Write-Ok "Docker Desktop 安装完成"
    Write-Warn "请启动 Docker Desktop 并等待引擎就绪后，重新运行此脚本进行后续配置"
    Write-Host "可以在开始菜单搜索 'Docker Desktop' 启动" -ForegroundColor Yellow
    exit 0
}

# 验证 Docker 引擎运行中
try {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Docker 已安装但引擎未运行"
        Write-Host "请启动 Docker Desktop 后重新运行此脚本" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Warn "Docker 引擎未运行，请先启动 Docker Desktop"
    exit 1
}
Write-Ok "Docker 引擎运行正常"

# 检查 Docker Compose
try {
    $composeVer = docker compose version 2>$null
    Write-Ok "Docker Compose: $composeVer"
} catch {
    Write-Fail "Docker Compose 插件不可用，请更新 Docker Desktop"
    exit 1
}

# ---------- 2. 检查 GPU ----------
Write-Host ""
Write-Info "[2/6] 检查 GPU 支持..."

$gpuAvailable = $false
try {
    $nvidiaSmi = nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "检测到 NVIDIA GPU 驱动: $($nvidiaSmi.Trim())"

        if ($WithGPU) {
            Write-Info "验证 Docker GPU 支持..."
            $gpuTest = docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "Docker GPU 支持验证通过"
                $gpuAvailable = $true
            } else {
                Write-Warn "Docker GPU 验证失败"
                Write-Host "请确认 Docker Desktop 设置中启用了 GPU 支持" -ForegroundColor Yellow
            }
        } else {
            Write-Info "GPU 可用（启动时添加 --profile gpu 启用训练/推理服务）"
            $gpuAvailable = $true
        }
    }
} catch {
    Write-Warn "未检测到 NVIDIA GPU，训练和推理服务将无法使用 GPU"
}

# ---------- 3. 检查 Git ----------
Write-Host ""
Write-Info "[3/6] 检查 Git..."

try {
    $gitVer = git --version 2>$null
    Write-Ok "Git 已安装: $gitVer"
} catch {
    Write-Info "Git 未安装，正在安装..."
    winget install --id Git.Git -e --source winget --accept-package-agreement --accept-source-agreement 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "winget 安装 Git 失败，请手动安装: https://git-scm.com/download/win"
    } else {
        Write-Ok "Git 安装完成"
    }
}

# ---------- 4. 拉取基础镜像 ----------
Write-Host ""
Write-Info "[4/6] 拉取基础镜像（首次可能需要几分钟）..."

$images = @(
    "timescale/timescaledb:latest-pg16",
    "redis:7-alpine",
    "nginx:alpine",
    "emqx/emqx:5.5.0",
    "ghcr.io/mlflow/mlflow:v2.9.0",
    "chrislusf/seaweedfs:latest",
    "maven:3.9-eclipse-temurin-21",
    "node:21-alpine"
)

foreach ($img in $images) {
    Write-Info "拉取 ${img}..."
    docker pull $img 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "${img} 就绪"
    } else {
        Write-Warn "${img} 拉取失败（可能网络问题，后续启动时会自动重试）"
    }
}

# ---------- 5. 创建数据卷目录 ----------
Write-Host ""
Write-Info "[5/6] 创建数据卷目录..."

$volumeBase = "D:\docker\volumes\edge_cloud"
$volumes = @(
    "postgres_data",
    "redis_data",
    "seaweedfs_data",
    "file_storage_data",
    "mlflow_data",
    "emqx_data"
)

if (-not (Test-Path $volumeBase)) {
    New-Item -ItemType Directory -Path $volumeBase -Force | Out-Null
    Write-Ok "创建基础目录: $volumeBase"
}

foreach ($vol in $volumes) {
    $path = Join-Path $volumeBase $vol
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Ok "创建数据卷: $vol"
    } else {
        Write-Ok "已存在: $vol"
    }
}

# 创建项目数据目录
$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$dataDirs = @("data\datasets", "data\models", "data\runs", "data\work", "data\shared_models")
foreach ($dir in $dataDirs) {
    $path = Join-Path $projectDir $dir
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Ok "创建: $dir"
    }
}

# ---------- 6. 配置环境变量 ----------
Write-Host ""
Write-Info "[6/6] 配置环境变量..."

$deployDir = Join-Path $projectDir "deployment\docker"
$envFile = Join-Path $deployDir ".env"
$envExample = Join-Path $deployDir ".env.example"

if (Test-Path $envFile) {
    Write-Ok ".env 文件已存在"
} else {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Ok "已从 .env.example 创建 .env"
        Write-Warn "请编辑 .env 文件，修改以下配置："
        Write-Host "  - CLOUD_API_URL: 改为本机局域网 IP" -ForegroundColor Yellow
        Write-Host "  - 生产环境请修改数据库和 Redis 密码" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  编辑命令: notepad $envFile" -ForegroundColor White
    } else {
        Write-Warn "未找到 .env.example，请手动创建 .env"
    }
}

# ---------- 完成 ----------
Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "启动方式:" -ForegroundColor White
Write-Host ""
Write-Host "  # 方式一：使用初始化脚本（推荐）" -ForegroundColor White
Write-Host "  cd $deployDir" -ForegroundColor Gray
Write-Host "  powershell -ExecutionPolicy Bypass -File .\init.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "  # 方式二：手动启动管理平台" -ForegroundColor White
Write-Host "  cd $deployDir" -ForegroundColor Gray
Write-Host "  docker compose up -d postgres redis emqx mlflow seaweedfs portal" -ForegroundColor Gray
Write-Host "  Start-Sleep -Seconds 15" -ForegroundColor Gray
Write-Host "  docker compose up -d backend frontend" -ForegroundColor Gray
Write-Host ""

if ($gpuAvailable) {
    Write-Host "  # 完整平台（含 GPU 训练/推理）" -ForegroundColor White
    Write-Host "  docker compose --profile gpu up -d" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "访问地址:" -ForegroundColor White
Write-Host "  中文导航门户: http://localhost:8889" -ForegroundColor Cyan
Write-Host "  前端管理平台: http://localhost:3000" -ForegroundColor Cyan
Write-Host "  后端 API:     http://localhost:8081" -ForegroundColor Cyan
Write-Host "  API 文档:     http://localhost:8081/swagger-ui.html" -ForegroundColor Cyan
Write-Host "  EMQX 控制台:  http://localhost:18083 (admin/admin123456)" -ForegroundColor Cyan
Write-Host "  MLflow:       http://localhost:5001" -ForegroundColor Cyan
Write-Host "  SeaweedFS:    http://localhost:8888" -ForegroundColor Cyan
Write-Host ""
Write-Host "常用命令:" -ForegroundColor White
Write-Host "  查看状态: docker compose ps" -ForegroundColor Gray
Write-Host "  查看日志: docker compose logs -f" -ForegroundColor Gray
Write-Host "  停止服务: docker compose down" -ForegroundColor Gray
Write-Host ""
