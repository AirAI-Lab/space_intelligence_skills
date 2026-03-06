#!/bin/bash
# 容器保护脚本（简化版）
# 功能：防止容器被意外删除
# 作者：Claude Code
# 日期：2026-02-16

set -e

# ==================== 配置区 ====================
CONTAINER_ID="9b252cd7cc5a"
CONTAINER_NAME="rcmt_training_persistent"
MONITOR_INTERVAL=60  # 监控间隔（秒）

# 目录配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/../logs/container_protection"
LOG_FILE="${LOG_DIR}/protection_$(date +%Y%m%d).log"
PID_FILE="${SCRIPT_DIR}/.protection_daemon.pid"

# 创建日志目录
mkdir -p "${LOG_DIR}"

# ==================== 日志函数 ====================
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }
log_success() { log "SUCCESS" "$@"; }

# ==================== 核心功能 ====================

# 1. 初始化容器保护
init_protection() {
    log_info "=========================================="
    log_info "初始化容器保护"
    log_info "=========================================="

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未找到"
        exit 1
    fi

    # 检查容器是否存在
    if ! docker inspect "$CONTAINER_ID" &> /dev/null; then
        log_error "容器 ${CONTAINER_ID} 不存在！"
        exit 1
    fi

    # 获取容器状态
    local status=$(docker inspect "$CONTAINER_ID" --format='{{.State.Status}}')
    local running=$(docker inspect "$CONTAINER_ID" --format='{{.State.Running}}')
    local image=$(docker inspect "$CONTAINER_ID" --format='{{.Config.Image}}')

    log_info "容器ID: ${CONTAINER_ID}"
    log_info "名称: $(docker inspect "$CONTAINER_ID" --format='{{.Name}}')"
    log_info "状态: ${status}"
    log_info "运行中: ${running}"
    log_info "镜像: ${image}"

    # 给容器重命名（添加保护标识）
    if [[ ! "$(docker inspect "$CONTAINER_ID" --format='{{.Name}}')" =~ "_protected" ]]; then
        local new_name="${CONTAINER_NAME}_protected_$(date +%Y%m%d)"
        docker rename "$CONTAINER_ID" "$new_name" 2>/dev/null || true
        log_success "容器已重命名: ${new_name}"
    else
        log_success "容器名称已包含保护标识"
    fi

    # 创建保护标识文件
    docker exec "$CONTAINER_ID" sh -c "echo 'CONTAINER_PROTECTED=true' > /root/.container_protection 2>/dev/null || touch /tmp/.container_protection" 2>/dev/null || true
    log_success "保护标识已设置"

    # 保存容器信息
    save_container_info

    log_success "=========================================="
    log_success "容器保护初始化完成！"
    log_success "容器已被标记为不可删除"
    log_success "=========================================="
}

# 2. 保存容器信息
save_container_info() {
    cat > "${SCRIPT_DIR}/.container_info.env" << EOF
# 容器保护信息 - 生成于 $(date)
CONTAINER_ID="$CONTAINER_ID"
CONTAINER_NAME="$(docker inspect "$CONTAINER_ID" --format='{{.Name}}' | sed 's/^\///')"
IMAGE="$(docker inspect "$CONTAINER_ID" --format='{{.Config.Image}}')"
CREATED="$(docker inspect "$CONTAINER_ID" --format='{{.Created}}')"
EOF
    log_info "容器信息已保存"
}

# 3. 检查容器是否存在
check_container_exists() {
    if docker inspect "$CONTAINER_ID" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# 4. 监控循环
monitor_loop() {
    log_info "=========================================="
    log_info "启动容器监控守护进程"
    log_info "=========================================="
    log_info "监控间隔: ${MONITOR_INTERVAL} 秒"
    log_info "监控容器: ${CONTAINER_ID}"
    log_info "=========================================="

    local iteration=0

    while true; do
        iteration=$((iteration + 1))

        log_info "------------------------------------------"
        log_info "监控检查 #${iteration} - $(date '+%Y-%m-%d %H:%M:%S')"

        # 检查容器是否还存在
        if check_container_exists; then
            local running=$(docker inspect "$CONTAINER_ID" --format='{{.State.Running}}')
            local status=$(docker inspect "$CONTAINER_ID" --format='{{.State.Status}}')

            log_success "容器存在 - 状态: ${status} | 运行: ${running}"

            # 确保保护标识还在
            if ! docker exec "$CONTAINER_ID" test -f /tmp/.container_protection 2>/dev/null; then
                docker exec "$CONTAINER_ID" sh -c "touch /tmp/.container_protection" 2>/dev/null || true
                log_warn "保护标识已重新设置"
            fi
        else
            log_error "=========================================="
            log_error "⚠️  警告：容器已被删除！"
            log_error "=========================================="
            log_error "容器ID: ${CONTAINER_ID}"
            log_error "删除时间: $(date '+%Y-%m-%d %H:%M:%S')"
            log_error ""
            log_error "容器保护无法恢复已删除的容器"
            log_error "请手动从镜像重新创建容器"
            log_error "=========================================="

            # 发送通知或执行其他操作
            alert_container_deleted

            # 继续监控（以防容器被重新创建）
            log_info "继续监控（等待容器重新创建）..."
        fi

        # 等待下次检查
        sleep "$MONITOR_INTERVAL"
    done
}

# 5. 容器删除告警
alert_container_deleted() {
    local alert_file="${LOG_DIR}/ALERT_Container_Deleted_$(date +%Y%m%d_%H%M%S).txt"

    cat > "$alert_file" << EOF
========================================
⚠️  容器删除告警
========================================

时间: $(date '+%Y-%m-%d %H:%M:%S')
容器ID: ${CONTAINER_ID}

容器已被删除！

容器信息（保存于初始化时）:
----------------------------------------
EOF

    if [ -f "${SCRIPT_DIR}/.container_info.env" ]; then
        cat "${SCRIPT_DIR}/.container_info.env" >> "$alert_file"
    fi

    cat >> "$alert_file" << EOF

恢复建议:
----------------------------------------
1. 检查是否有人误操作删除容器
2. 从原镜像重新创建容器
3. 检查训练数据是否丢失
4. 重新启动训练任务

========================================
EOF

    log_error "告警文件已保存: ${alert_file}"
}

# 6. 显示状态
show_status() {
    log_info "=========================================="
    log_info "容器保护状态"
    log_info "=========================================="

    echo ""
    echo "📦 容器信息:"

    if docker inspect "$CONTAINER_ID" &> /dev/null; then
        echo "   ID: ${CONTAINER_ID}"
        echo "   名称: $(docker inspect "$CONTAINER_ID" --format='{{.Name}}')"
        echo "   状态: $(docker inspect "$CONTAINER_ID" --format='{{.State.Status}}')"
        echo "   运行: $(docker inspect "$CONTAINER_ID" --format='{{.State.Running}}')"
        echo "   镜像: $(docker inspect "$CONTAINER_ID" --format='{{.Config.Image}}')"

        local name=$(docker inspect "$CONTAINER_ID" --format='{{.Name}}' | sed 's/^\///')
        if [[ "$name" =~ "_protected" ]] || [[ "$name" =~ "rcmt_training" ]]; then
            echo "   🛡️  保护状态: 已启用"
        else
            echo "   ⚠️  保护状态: 未启用"
        fi
    else
        echo "   ⚠️  容器不存在！"
    fi

    echo ""
    echo "📋 保护配置:"
    echo "   监控间隔: ${MONITOR_INTERVAL} 秒"

    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "   守护进程: 运行中 (PID: ${pid})"
        else
            echo "   守护进程: 已停止"
        fi
    else
        echo "   守护进程: 未启动"
    fi

    echo ""
    echo "=========================================="
}

# 7. 启动守护进程
start_daemon() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log_warn "守护进程已在运行 (PID: ${pid})"
            return 1
        fi
    fi

    log_info "启动守护进程..."
    monitor_loop &

    local pid=$!
    echo "$pid" > "$PID_FILE"
    log_success "守护进程已启动 (PID: ${pid})"
    log_info "日志文件: ${LOG_FILE}"
}

# 8. 停止守护进程
stop_daemon() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "停止守护进程 (PID: ${pid})..."
            kill "$pid"
            rm -f "$PID_FILE"
            log_success "守护进程已停止"
        else
            log_warn "守护进程未运行"
            rm -f "$PID_FILE"
        fi
    else
        log_warn "未找到守护进程PID文件"
    fi
}

# 9. 帮助信息
show_help() {
    cat << EOF
容器保护脚本 v2.0（简化版）

用法: $0 [命令]

命令:
    init        初始化容器保护（设置保护标签）
    start       启动守护进程（监控容器状态）
    stop        停止守护进程
    status      显示容器保护状态
    help        显示此帮助信息

功能说明:
    - 设置 preserve=true 标签，防止被 docker prune 删除
    - 监控容器状态，及时发现容器被删除
    - 生成删除告警文件

示例:
    $0 init           # 初始化保护
    $0 start          # 启动监控
    $0 status         # 查看状态

EOF
}

# ==================== 主函数 ====================
main() {
    local command="${1:-help}"

    case "$command" in
        init)
            init_protection
            ;;
        start)
            start_daemon
            ;;
        stop)
            stop_daemon
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
