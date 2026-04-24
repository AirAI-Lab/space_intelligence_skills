#!/usr/bin/env bash
# ============================================
# edge_infer_cloud Docker 环境一键安装脚本 (Linux)
# 支持: Ubuntu 20.04/22.04/24.04, Debian 11/12
# 用法: bash scripts/install_docker.sh [--with-gpu]
# ============================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

WITH_GPU=false
[[ "${1:-}" == "--with-gpu" ]] && WITH_GPU=true

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

# ---------- 前置检查 ----------
info "===== edge_infer_cloud Docker 环境安装 ====="
echo ""

# 检查是否为 root 或有 sudo 权限
if [[ $EUID -ne 0 ]]; then
    SUDO="sudo"
    if ! $SUDO -n true 2>/dev/null; then
        warn "后续步骤需要 sudo 权限，请确保当前用户有 sudo 权限"
    fi
else
    SUDO=""
fi

# 检测发行版
if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    OS_ID="${ID:-unknown}"
    OS_VERSION="${VERSION_ID:-unknown}"
else
    fail "无法检测操作系统版本"
fi

info "检测到系统: ${OS_ID} ${OS_VERSION}"

if [[ "$OS_ID" != "ubuntu" && "$OS_ID" != "debian" ]]; then
    warn "此脚本主要针对 Ubuntu/Debian。其他发行版请参考 README_DOCKER.md 手动安装。"
    read -rp "是否继续？(y/N) " confirm
    [[ "$confirm" != "y" && "$confirm" != "Y" ]] && exit 0
fi

# ---------- 1. 安装 Docker ----------
echo ""
info "[1/5] 检查 Docker..."

if command -v docker &>/dev/null; then
    DOCKER_VERSION=$(docker --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)
    ok "Docker 已安装: ${DOCKER_VERSION}"
else
    info "正在安装 Docker Engine..."

    # 卸载旧版本
    $SUDO apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

    # 安装依赖
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq ca-certificates curl gnupg

    # 添加 Docker GPG key
    $SUDO install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/${OS_ID}/gpg | \
        $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null
    $SUDO chmod a+r /etc/apt/keyrings/docker.gpg

    # 添加 Docker 仓库
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${OS_ID} ${VERSION_CODENAME} stable" | \
        $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null

    # 安装
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # 将当前用户加入 docker 组
    $SUDO usermod -aG docker $USER
    ok "Docker 安装完成"
    warn "已将当前用户加入 docker 组。请注销后重新登录使权限生效，或执行: newgrp docker"
fi

# 验证 Docker Compose
if docker compose version &>/dev/null; then
    ok "Docker Compose 已就绪: $(docker compose version --short)"
else
    fail "Docker Compose 插件未安装"
fi

# ---------- 2. 安装 NVIDIA Container Toolkit (可选) ----------
echo ""
info "[2/5] 检查 GPU 支持..."

GPU_AVAILABLE=false
if command -v nvidia-smi &>/dev/null; then
    NVIDIA_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)
    ok "检测到 NVIDIA GPU 驱动: ${NVIDIA_VERSION}"

    if $WITH_GPU; then
        if command -v nvidia-container-toolkit &>/dev/null || dpkg -l | grep -q nvidia-container-toolkit; then
            ok "NVIDIA Container Toolkit 已安装"
        else
            info "正在安装 NVIDIA Container Toolkit..."
            curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
                $SUDO gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg 2>/dev/null

            curl -s -L "https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list" | \
                sed "s#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g" | \
                $SUDO tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

            $SUDO apt-get update -qq
            $SUDO apt-get install -y -qq nvidia-container-toolkit

            $SUDO nvidia-ctk runtime configure --runtime=docker
            $SUDO systemctl restart docker
            ok "NVIDIA Container Toolkit 安装完成"
        fi

        # 验证
        if docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi &>/dev/null; then
            ok "Docker GPU 支持验证通过"
            GPU_AVAILABLE=true
        else
            warn "Docker GPU 验证失败，可能需要重启 Docker 或重新登录"
        fi
    else
        info "跳过 GPU 安装（如需请使用 --with-gpu 参数）"
    fi
else
    warn "未检测到 NVIDIA GPU，训练和推理服务将无法使用 GPU"
    info "如需 GPU 支持，请先安装 NVIDIA 驱动: https://www.nvidia.com/Download/index.aspx"
fi

# ---------- 3. 检查 Git ----------
echo ""
info "[3/5] 检查 Git..."

if command -v git &>/dev/null; then
    ok "Git 已安装: $(git --version)"
else
    info "正在安装 Git..."
    $SUDO apt-get install -y -qq git
    ok "Git 安装完成"
fi

# ---------- 4. 创建数据目录 ----------
echo ""
info "[4/5] 创建数据卷目录..."

VOLUME_BASE="/docker/volumes/edge_cloud"
for dir in postgres_data redis_data seaweedfs_data file_storage_data mlflow_data emqx_data; do
    target="${VOLUME_BASE}/${dir}"
    if [[ ! -d "$target" ]]; then
        $SUDO mkdir -p "$target"
        ok "创建: ${target}"
    else
        ok "已存在: ${target}"
    fi
done

# 创建模型相关目录
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
for dir in data/datasets data/models data/runs data/work data/shared_models; do
    target="${PROJECT_DIR}/${dir}"
    if [[ ! -d "$target" ]]; then
        mkdir -p "$target"
        ok "创建: ${target}"
    fi
done

# ---------- 5. 配置环境变量 ----------
echo ""
info "[5/5] 配置环境变量..."

DEPLOY_DIR="${PROJECT_DIR}/deployment/docker"
if [[ -f "${DEPLOY_DIR}/.env" ]]; then
    ok ".env 文件已存在"
else
    if [[ -f "${DEPLOY_DIR}/.env.example" ]]; then
        cp "${DEPLOY_DIR}/.env.example" "${DEPLOY_DIR}/.env"
        # 修改 Linux 的数据卷路径
        sed -i "s|VOLUME_BASE_PATH=.*|VOLUME_BASE_PATH=${VOLUME_BASE}|" "${DEPLOY_DIR}/.env"
        ok "已从 .env.example 创建 .env（数据卷路径已适配 Linux）"
        warn "请编辑 .env 文件修改生产环境密码: vim ${DEPLOY_DIR}/.env"
    else
        warn "未找到 .env.example，请手动创建 .env 文件"
    fi
fi

# ---------- 完成 ----------
echo ""
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}  安装完成！${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""
echo "启动方式:"
echo ""
echo "  # 管理平台模式（无 GPU）"
echo "  cd ${DEPLOY_DIR}"
echo "  docker compose up -d postgres redis emqx mlflow seaweedfs portal"
echo "  sleep 15"
echo "  docker compose up -d backend frontend"
echo ""
if $GPU_AVAILABLE; then
    echo "  # 完整平台（含 GPU 训练/推理）"
    echo "  cd ${DEPLOY_DIR}"
    echo "  docker compose --profile gpu up -d"
    echo ""
fi
echo "访问地址:"
echo "  中文导航门户: http://localhost:8889"
echo "  前端管理平台: http://localhost:3000"
echo "  后端 API:     http://localhost:8081"
echo "  API 文档:     http://localhost:8081/swagger-ui.html"
echo "  EMQX 控制台:  http://localhost:18083 (admin/admin123456)"
echo "  MLflow:       http://localhost:5001"
echo "  SeaweedFS:    http://localhost:8888"
echo ""
echo "查看服务状态: docker compose ps"
echo "查看日志:     docker compose logs -f"
echo "停止服务:     docker compose down"
echo ""
