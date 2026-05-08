#!/usr/bin/env bash
# ============================================
# SkyEdge AI Cloud Platform 部署脚本
# ============================================
# 在 Linux 服务器上执行:
#   chmod +x deploy.sh
#   ./deploy.sh              # 生产模式部署
#   ./deploy.sh --dev        # 开发模式部署
#   ./deploy.sh --stop       # 停止所有服务
#   ./deploy.sh --status     # 查看服务状态
#   ./deploy.sh --logs       # 查看后端日志
#   ./deploy.sh --rebuild    # 重新构建镜像并部署
#   ./deploy.sh --gpu        # 含训练服务(GPU)
# ============================================

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"
DEV_COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
step()  { echo -e "${BLUE}[STEP]${NC} $1"; }

check_docker() {
    if ! command -v docker &>/dev/null; then
        error "Docker 未安装，请先安装 Docker Engine"
    fi
    if ! docker compose version &>/dev/null; then
        error "Docker Compose V2 未安装"
    fi
    info "Docker $(docker --format '{{.Server.Version}}')"
}

check_gpu() {
    if command -v nvidia-smi &>/dev/null; then
        local gpu_count
        gpu_count=$(nvidia-smi --list-gpus 2>/dev/null | wc -l)
        info "检测到 ${gpu_count} 块 GPU"
        return 0
    fi
    warn "未检测到 NVIDIA GPU，训练服务将不可用"
    return 1
}

build_images() {
    step "构建生产镜像..."
    docker compose -f "${COMPOSE_FILE}" build backend frontend
    info "镜像构建完成"
}

deploy_prod() {
    check_docker

    step "===== SkyEdge AI Cloud Platform 生产部署 ====="

    # 检查 .env 文件
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        warn "未找到 .env 文件，使用默认配置"
        cat > "${SCRIPT_DIR}/.env" << 'EOF'
# SkyEdge AI Cloud Platform 环境配置
VERSION=1.0.0
PG_PASSWORD=edge_pass
EMQX_PASSWORD=admin123456
EOF
        info "已生成默认 .env 文件: ${SCRIPT_DIR}/.env"
    fi

    # 构建镜像
    build_images

    # 启动服务
    step "启动服务..."
    local profiles=""
    if [ "${GPU_MODE:-false}" = "true" ]; then
        check_gpu && profiles="--profile gpu"
    fi

    docker compose -f "${COMPOSE_FILE}" --env-file "${SCRIPT_DIR}/.env" \
        up -d ${profiles}

    # 等待健康检查
    step "等待服务就绪..."
    sleep 10

    # 显示状态
    show_status

    echo ""
    info "部署完成！"
    info "前端管理界面: http://$(hostname -I | awk '{print $1}')/"
    info "REST API:     http://$(hostname -I | awk '{print $1}')/api/v1/"
    info "EMQX 管理:    http://$(hostname -I | awk '{print $1}')/emqx/"
}

deploy_dev() {
    check_docker

    step "===== SkyEdge AI Cloud Platform 开发模式 ====="

    docker compose -f "${DEV_COMPOSE_FILE}" up -d

    show_status
    echo ""
    info "开发模式启动完成"
    info "前端:   http://localhost:3000"
    info "后端:   http://localhost:8081"
    info "EMQX:   http://localhost:18083"
}

stop_all() {
    step "停止所有服务..."
    docker compose -f "${COMPOSE_FILE}" down --remove-orphans 2>/dev/null || true
    docker compose -f "${DEV_COMPOSE_FILE}" down --remove-orphans 2>/dev/null || true
    info "所有服务已停止"
}

show_status() {
    echo ""
    echo "========== 服务状态 =========="
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" \
        --filter "name=edge_cloud" --filter "name=rtmp" --filter "name=nginx"
    echo "================================"
}

show_logs() {
    local service="${1:-backend}"
    docker compose -f "${COMPOSE_FILE}" logs -f --tail=100 "${service}"
}

rebuild() {
    step "重新构建并部署..."
    stop_all
    build_images
    deploy_prod
}

# ========== 主入口 ==========

case "${1:-}" in
    --dev)
        deploy_dev
        ;;
    --stop)
        stop_all
        ;;
    --status)
        show_status
        ;;
    --logs)
        show_logs "${2:-backend}"
        ;;
    --rebuild)
        rebuild
        ;;
    --gpu)
        GPU_MODE=true deploy_prod
        ;;
    --help|-h)
        echo "用法: $0 [--dev|--stop|--status|--logs|--rebuild|--gpu]"
        echo ""
        echo "  (无参数)    生产模式部署"
        echo "  --dev       开发模式（挂载源码，热重载）"
        echo "  --stop      停止所有服务"
        echo "  --status    查看服务状态"
        echo "  --logs      查看日志（默认后端）"
        echo "  --rebuild   重新构建镜像并部署"
        echo "  --gpu       含 GPU 训练服务"
        ;;
    *)
        deploy_prod
        ;;
esac
