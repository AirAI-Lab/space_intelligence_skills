#!/usr/bin/env bash
# ============================================
# SkyEdge AI Cloud Platform 部署脚本
# ============================================
# 在 Linux 服务器上执行:
#   ./deploy.sh              # 生产部署（自动检测 GPU）
#   ./deploy.sh --dev        # 开发模式部署
#   ./deploy.sh --stop       # 停止所有服务
#   ./deploy.sh --status     # 查看服务状态
#   ./deploy.sh --logs       # 查看后端日志
#   ./deploy.sh --rebuild    # 重新构建镜像并部署
#   ./deploy.sh --backup     # 备份数据库
#   ./deploy.sh --restore    # 恢复数据库
# ============================================

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"
DEV_COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
ENV_FILE="${SCRIPT_DIR}/.env"
BACKUP_DIR="${SCRIPT_DIR}/backups"

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
    local ports=(80 1883 5432 6379 8333 1935)
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

init_db() {
    # 检查 devices 表是否存在，不存在则执行建表
    local table_exists
    table_exists=$(docker compose -f "${COMPOSE_FILE}" exec -T postgres \
        psql -U edge_user -d edge_cloud -tAc "SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = 'devices')" 2>/dev/null || echo "false")

    if [ "${table_exists}" = "t" ] || [ "${table_exists}" = "true" ]; then
        info "数据库表已存在，跳过建表"
        return
    fi

    local schema_dir="${SCRIPT_DIR}/../../backend/src/main/resources"
    local schema_file="${schema_dir}/schema.sql"
    if [ ! -f "${schema_file}" ]; then
        warn "未找到 schema.sql: ${schema_file}，请手动建表"
        return
    fi

    step "首次部署，初始化数据库表..."

    # 1) 基础建表
    docker exec -i edge_cloud_postgres psql -U edge_user -d edge_cloud < "${schema_file}"

    # 2) 执行 migration 脚本
    local migration_dir="${schema_dir}/db/migration"
    if [ -d "${migration_dir}" ]; then
        for f in "${migration_dir}"/V*.sql; do
            [ -f "$f" ] || continue
            info "  执行 migration: $(basename "$f")"
            docker exec -i edge_cloud_postgres psql -U edge_user -d edge_cloud < "$f" 2>/dev/null
        done
    fi

    # 3) 补全后端实体新增但 schema.sql 未覆盖的字段
    docker exec -i edge_cloud_postgres psql -U edge_user -d edge_cloud <<'EOSQL'
ALTER TABLE training_jobs ADD COLUMN IF NOT EXISTS base_model VARCHAR(200);
ALTER TABLE training_jobs ADD COLUMN IF NOT EXISTS dataset_name VARCHAR(200);
ALTER TABLE training_jobs ADD COLUMN IF NOT EXISTS dataset_path VARCHAR(500);
ALTER TABLE training_jobs ADD COLUMN IF NOT EXISTS dataset_source VARCHAR(50);
ALTER TABLE training_jobs ADD COLUMN IF NOT EXISTS dataset_url VARCHAR(500);
ALTER TABLE training_jobs ADD COLUMN IF NOT EXISTS enable_smart_optimization BOOLEAN DEFAULT FALSE;
ALTER TABLE training_jobs ADD COLUMN IF NOT EXISTS final_map50 DOUBLE PRECISION;
ALTER TABLE training_jobs ADD COLUMN IF NOT EXISTS resume BOOLEAN DEFAULT FALSE;
ALTER TABLE training_jobs ADD COLUMN IF NOT EXISTS resume_job_id VARCHAR(50);
ALTER TABLE ota_tasks ADD COLUMN IF NOT EXISTS progress DOUBLE PRECISION DEFAULT 0;
ALTER TABLE models ADD COLUMN IF NOT EXISTS map50 DOUBLE PRECISION;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS dataset_source VARCHAR(50);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_category VARCHAR(30);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS capabilities VARCHAR(200);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS protocol VARCHAR(30);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS labels TEXT;

-- 补全 schema.sql 缺失的表（后端实体 @Table 定义但 schema.sql 未包含）
CREATE TABLE IF NOT EXISTS model_deployment (
    deployment_id VARCHAR(50) PRIMARY KEY,
    model_id VARCHAR(50),
    model_name VARCHAR(200),
    device_id VARCHAR(50),
    device_name VARCHAR(200),
    previous_model_id VARCHAR(50),
    previous_model_name VARCHAR(200),
    deployment_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'PENDING',
    deployed_by VARCHAR(100),
    deployed_at TIMESTAMP,
    completed_at TIMESTAMP,
    rollback_at TIMESTAMP,
    error_message TEXT,
    inference_fps DOUBLE PRECISION,
    gpu_utilization DOUBLE PRECISION,
    memory_usage_mb DOUBLE PRECISION,
    ota_task_id VARCHAR(50),
    is_ab_test BOOLEAN DEFAULT FALSE,
    ab_test_group VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_model_deployment_model_id ON model_deployment(model_id);
CREATE INDEX IF NOT EXISTS idx_model_deployment_device_id ON model_deployment(device_id);

CREATE TABLE IF NOT EXISTS device_commands (
    id BIGSERIAL PRIMARY KEY,
    command_id VARCHAR(50) NOT NULL UNIQUE,
    device_id VARCHAR(50) NOT NULL,
    command_type VARCHAR(50) NOT NULL,
    task_id VARCHAR(50),
    params TEXT,
    status VARCHAR(50) DEFAULT 'PENDING',
    expire_at TIMESTAMP,
    sent_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_device_commands_device_id ON device_commands(device_id);

CREATE TABLE IF NOT EXISTS device_tags (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    tag_key VARCHAR(100) NOT NULL,
    tag_value VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(device_id, tag_key)
);
CREATE INDEX IF NOT EXISTS idx_device_tags_device_id ON device_tags(device_id);
EOSQL

    info "数据库表初始化完成"

    # 重启后端让 JPA 同步实体
    docker restart edge_cloud_backend 2>/dev/null || true
    info "正在重启后端服务..."
    sleep 15
}

build_images() {
    step "构建生产镜像..."
    local build_targets="backend frontend"
    if check_gpu; then
        build_targets="${build_targets} training"
    fi
    docker compose -f "${COMPOSE_FILE}" build ${build_targets}
    info "镜像构建完成"
}

init_env() {
    if [ ! -f "${ENV_FILE}" ]; then
        warn "未找到 .env 文件，从模板生成..."
        cp "${SCRIPT_DIR}/.env.example" "${ENV_FILE}"

        # 自动检测云端 IP
        local cloud_ip
        cloud_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [ -n "$cloud_ip" ]; then
            sed -i "s|CLOUD_API_URL=.*|CLOUD_API_URL=http://${cloud_ip}|" "${ENV_FILE}"
            info "已自动设置 CLOUD_API_URL=http://${cloud_ip}"
        else
            warn "无法自动获取 IP，请手动设置 CLOUD_API_URL"
        fi

        info "已生成 .env 文件: ${ENV_FILE}"
        info "默认账号密码均为 admin / admin123456，如需自定义请编辑 .env"
    else
        info "已存在 .env 文件: ${ENV_FILE}"
    fi
}

deploy_prod() {
    check_docker
    check_disk

    step "===== SkyEdge AI Cloud Platform 生产部署 ====="

    init_env

    # 检查环境
    check_ports

    # 构建镜像
    build_images

    # 自动检测 GPU，决定是否启用 training 服务
    local profiles=""
    if check_gpu; then
        profiles="--profile gpu"
        info "将启用 GPU 训练/推理服务"
    fi

    # 启动所有服务
    step "启动服务..."
    docker compose ${profiles} -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        up -d

    # 等待健康检查
    step "等待服务就绪..."
    sleep 10

    # 首次部署自动建表
    init_db

    # 显示状态
    show_status

    local ip
    ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')
    echo ""
    info "===== 部署完成 ====="
    info "前端管理界面: http://${ip}/"
    info "REST API:     http://${ip}/api/v1/"
    info "API 文档:     http://${ip}/swagger-ui.html"
    info "EMQX 管理:    http://${ip}/emqx/"
    echo ""
    info "API Key 在 ${ENV_FILE} 中配置，第三方对接请携带 X-API-Key header"
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
    --backup)
        backup_db
        ;;
    --restore)
        restore_db "$@"
        ;;
    --help|-h)
        echo "用法: $0 [选项]"
        echo ""
        echo "  (无参数)    生产部署（自动检测 GPU，一次性启动全部服务）"
        echo "  --dev       开发模式（挂载源码，热重载）"
        echo "  --stop      停止所有服务"
        echo "  --status    查看服务状态"
        echo "  --logs      查看日志（默认后端）"
        echo "  --rebuild   重新构建镜像并部署"
        echo "  --backup    备份数据库"
        echo "  --restore   恢复数据库（需指定文件）"
        ;;
    *)
        deploy_prod
        ;;
esac
