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
#   ./deploy.sh --init       # 首次部署初始化
#   ./deploy.sh --backup     # 备份数据库
#   ./deploy.sh --restore    # 恢复数据库
# ============================================

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"
DEV_COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
ENV_FILE="${SCRIPT_DIR}/.env"
BACKUP_DIR="${SCRIPT_DIR}/backups"

# 平台检测：自动识别 Linux / WSL2 并加载对应 .env 覆盖
detect_platform() {
    if grep -qi microsoft /proc/version 2>/dev/null; then
        echo "wsl2"
    elif [[ "$(uname -s)" == "Linux" ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}
PLATFORM=$(detect_platform)
if [[ "$PLATFORM" == "wsl2" && -f "${SCRIPT_DIR}/.env.wsl2" ]]; then
    set -a; source "${SCRIPT_DIR}/.env.wsl2"; set +a
fi

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

check_ports() {
    local ports=(80 1883 5432 6379 8333)
    local occupied=""
    for port in "${ports[@]}"; do
        if ss -tlnp 2>/dev/null | grep -q ":${port} " || \
           netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
            occupied="${occupied} ${port}"
        fi
    done
    if [ -n "$occupied" ]; then
        warn "以下端口已被占用:${occupied}，可能导致启动失败"
    fi
}

check_disk() {
    local avail
    avail=$(df -BG "${SCRIPT_DIR}" | awk 'NR==2 {print $4}' | tr -d 'G')
    if [ "${avail:-0}" -lt 10 ]; then
        warn "磁盘剩余空间不足 10GB: ${avail}GB"
    else
        info "磁盘剩余: ${avail}GB"
    fi
}

build_images() {
    step "构建生产镜像..."
    docker compose -f "${COMPOSE_FILE}" build backend frontend
    info "镜像构建完成"
}

init_env() {
    if [ ! -f "${ENV_FILE}" ]; then
        warn "未找到 .env 文件，从模板生成..."
        cp "${SCRIPT_DIR}/.env.example" "${ENV_FILE}"

        # 生成随机 API Key
        local api_key
        api_key=$(openssl rand -hex 16 2>/dev/null || head -c 32 /dev/urandom | xxd -p | head -c 32)
        if [ -n "$api_key" ]; then
            sed -i "s/API_KEY=.*/API_KEY=${api_key}/" "${ENV_FILE}"
            info "已生成 API Key: ${api_key}"
        fi

        # 生成随机 EMQX 密码
        local emqx_pass
        emqx_pass=$(openssl rand -base64 12 2>/dev/null || echo "emqx_$(date +%s)")
        sed -i "s/EMQX_PASSWORD=.*/EMQX_PASSWORD=${emqx_pass}/" "${ENV_FILE}"

        info "已生成 .env 文件: ${ENV_FILE}"
        info "请检查并修改 CLOUD_API_URL 为实际 IP"
    else
        info "已存在 .env 文件: ${ENV_FILE}"
    fi
}

init_deploy() {
    check_docker
    check_disk

    step "===== 首次部署初始化 ====="

    init_env

    step "检查环境..."
    check_ports

    step "启动基础设施（数据库、缓存、MQTT）..."
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        up -d postgres redis emqx seaweedfs

    step "等待数据库就绪..."
    local retries=30
    while [ $retries -gt 0 ]; do
        if docker compose -f "${COMPOSE_FILE}" exec -T postgres \
            pg_isready -U edge_user -d edge_cloud &>/dev/null; then
            break
        fi
        retries=$((retries - 1))
        sleep 2
    done
    if [ $retries -eq 0 ]; then
        error "数据库启动超时"
    fi
    info "数据库就绪"

    # 等待 SeaweedFS 就绪
    step "等待 SeaweedFS 就绪..."
    sleep 10

    # 初始化 S3 bucket
    step "初始化文件存储..."
    docker compose -f "${COMPOSE_FILE}" exec -T seaweedfs \
        weed shell -master=localhost:9333 -filer=localhost:8888 <<'EOF'
lock
volume.create -replication=000
exit
EOF
    info "文件存储就绪"

    step "启动业务服务..."
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        up -d backend frontend nginx mlflow

    step "等待服务就绪..."
    sleep 15

    show_status

    echo ""
    info "===== 初始化完成 ====="
    info "前端管理界面: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')/"
    info "REST API:     http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')/api/v1/"
    info "API 文档:     http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')/swagger-ui.html"
    info "EMQX 管理:    http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')/emqx/"
    echo ""
    info "API Key 已写入 ${ENV_FILE}，第三方对接请携带 X-API-Key header"
}

deploy_prod() {
    check_docker

    step "===== SkyEdge AI Cloud Platform 生产部署 ====="

    init_env

    # 构建镜像
    build_images

    # 启动服务
    step "启动服务..."
    local profiles=""
    if [ "${GPU_MODE:-false}" = "true" ]; then
        check_gpu && profiles="--profile gpu"
    fi

    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        up -d ${profiles}

    # 等待健康检查
    step "等待服务就绪..."
    sleep 10

    # 显示状态
    show_status

    echo ""
    info "部署完成！"
    info "前端管理界面: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')/"
    info "REST API:     http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')/api/v1/"
    info "EMQX 管理:    http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')/emqx/"
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

backup_db() {
    check_docker
    mkdir -p "${BACKUP_DIR}"

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/edge_cloud_${timestamp}.sql.gz"

    step "备份数据库..."
    docker compose -f "${COMPOSE_FILE}" exec -T postgres \
        pg_dump -U edge_user edge_cloud | gzip > "${backup_file}"

    local size
    size=$(du -h "${backup_file}" | awk '{print $1}')
    info "备份完成: ${backup_file} (${size})"
}

restore_db() {
    check_docker

    if [ -z "${2:-}" ]; then
        error "用法: $0 --restore <backup_file.sql.gz>"
    fi

    local backup_file="$2"
    if [ ! -f "${backup_file}" ]; then
        error "备份文件不存在: ${backup_file}"
    fi

    step "恢复数据库..."
    warn "此操作将覆盖当前数据，3秒后继续..."
    sleep 3

    gunzip -c "${backup_file}" | docker compose -f "${COMPOSE_FILE}" exec -T postgres \
        psql -U edge_user edge_cloud

    info "恢复完成"
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
    --init)
        init_deploy
        ;;
    --backup)
        backup_db
        ;;
    --restore)
        restore_db "$@"
        ;;
    --help|-h)
        echo "用法: $0 [选项]"
        echo ""
        echo "  (无参数)    生产模式部署"
        echo "  --init      首次部署初始化（生成 .env、初始化存储）"
        echo "  --dev       开发模式（挂载源码，热重载）"
        echo "  --stop      停止所有服务"
        echo "  --status    查看服务状态"
        echo "  --logs      查看日志（默认后端）"
        echo "  --rebuild   重新构建镜像并部署"
        echo "  --gpu       含 GPU 训练服务"
        echo "  --backup    备份数据库"
        echo "  --restore   恢复数据库（需指定文件）"
        ;;
    *)
        deploy_prod
        ;;
esac
