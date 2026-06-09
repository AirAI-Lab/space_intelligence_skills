#!/usr/bin/env bash
# ============================================
# SkyEdge AI Cloud - 统一 IP 地址配置脚本
# ============================================
# 用法:
#   ./configure_ip.sh                                    # 交互式配置
#   ./configure_ip.sh --cloud 192.168.1.123              # 只改云端 IP
#   ./configure_ip.sh --edge 192.168.0.1                 # 只改边缘 IP
#   ./configure_ip.sh --cloud 192.168.1.123 --edge 192.168.0.1  # 同时指定
#   ./configure_ip.sh --auto                             # 自动检测本机 IP 作为云端 IP
#   ./configure_ip.sh --show                             # 显示当前 IP 配置
# ============================================

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
ENV_IP_FILE="${PROJECT_ROOT}/.env.ip"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
step()  { echo -e "${BLUE}[STEP]${NC} $1"; }

# ========== 读取当前 .env.ip ==========
read_env_ip() {
    if [ ! -f "${ENV_IP_FILE}" ]; then
        # 创建默认 .env.ip
        cat > "${ENV_IP_FILE}" << 'EOF'
# ========================================
# 统一 IP 地址配置
# ========================================
# 修改这些 IP 地址后，运行 scripts/configure_ip.sh 同步到所有配置文件
# 适用于：docker-compose、云端推理配置、边缘端配置等

# 云端服务器 IP 地址（本机运行云端服务的地方）
CLOUD_IP=192.168.1.123

# 边缘设备 IP 地址（Jetson / 边缘推理设备）
EDGE_IP=192.168.0.1

# 端口配置（一般不需要修改）
CLOUD_API_PORT=8081
CLOUD_MQTT_PORT=1883
CLOUD_RTMP_PORT=1935
EOF
        info "已创建默认 .env.ip 文件"
    fi

    # 解析 .env.ip 中的值
    CLOUD_IP=$(grep "^CLOUD_IP=" "${ENV_IP_FILE}" | cut -d'=' -f2 | tr -d ' ')
    EDGE_IP=$(grep "^EDGE_IP=" "${ENV_IP_FILE}" 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || grep "^JETSON_IP=" "${ENV_IP_FILE}" | cut -d'=' -f2 | tr -d ' ')
    CLOUD_API_PORT=$(grep "^CLOUD_API_PORT=" "${ENV_IP_FILE}" | cut -d'=' -f2 | tr -d ' ')
    CLOUD_MQTT_PORT=$(grep "^CLOUD_MQTT_PORT=" "${ENV_IP_FILE}" | cut -d'=' -f2 | tr -d ' ')
    CLOUD_RTMP_PORT=$(grep "^CLOUD_RTMP_PORT=" "${ENV_IP_FILE}" | cut -d'=' -f2 | tr -d ' ')
}

# ========== 更新 .env.ip 文件 ==========
update_env_ip() {
    local cloud_ip="${1}"
    local edge_ip="${2}"

    # 读取端口（保持不变）
    local api_port="${CLOUD_API_PORT:-8081}"
    local mqtt_port="${CLOUD_MQTT_PORT:-1883}"
    local rtmp_port="${CLOUD_RTMP_PORT:-1935}"

    cat > "${ENV_IP_FILE}" << EOF
# ========================================
# 统一 IP 地址配置
# ========================================
# 修改这些 IP 地址后，运行 scripts/configure_ip.sh 同步到所有配置文件
# 适用于：docker-compose、云端推理配置、边缘端配置等

# 云端服务器 IP 地址（本机运行云端服务的地方）
CLOUD_IP=${cloud_ip}

# 边缘设备 IP 地址（Jetson / 边缘推理设备）
EDGE_IP=${edge_ip}

# 端口配置（一般不需要修改）
CLOUD_API_PORT=${api_port}
CLOUD_MQTT_PORT=${mqtt_port}
CLOUD_RTMP_PORT=${rtmp_port}
EOF

    info ".env.ip 已更新: 云端=${cloud_ip}, 边缘=${edge_ip}"
}

# ========== 同步 IP 到所有配置文件 ==========
sync_all_configs() {
    local cloud_ip="${1}"
    local edge_ip="${2}"
    local changed=0

    step "===== 同步 IP 配置到所有文件 ====="
    echo ""

    # 1. deployment/docker/.env - CLOUD_API_URL
    local docker_env="${PROJECT_ROOT}/deployment/docker/.env"
    if [ -f "${docker_env}" ]; then
        local old_cloud_url
        old_cloud_url=$(grep "^CLOUD_API_URL=" "${docker_env}" | cut -d'=' -f2)
        local new_cloud_url="http://${cloud_ip}"
        if [ "${old_cloud_url}" != "${new_cloud_url}" ]; then
            sed -i "s|^CLOUD_API_URL=.*|CLOUD_API_URL=${new_cloud_url}|" "${docker_env}"
            info "[.env] CLOUD_API_URL: ${old_cloud_url} → ${new_cloud_url}"
            changed=$((changed + 1))
        else
            info "[.env] CLOUD_API_URL 已是最新: ${new_cloud_url}"
        fi
    else
        warn "[.env] 未找到: ${docker_env}"
    fi

    # 2. deployment/docker/docker-compose.yml - S3_EXTERNAL_ENDPOINT
    local compose_file="${PROJECT_ROOT}/deployment/docker/docker-compose.yml"
    if [ -f "${compose_file}" ]; then
        # 替换硬编码 IP（不管是否已有环境变量引用）
        if grep -q "192\.168\." "${compose_file}"; then
            sed -i "s|http://192\.168\.[0-9]\+\.[0-9]\+:8333|http://${cloud_ip}:8333|g" "${compose_file}"
            info "[docker-compose.yml] S3_EXTERNAL_ENDPOINT → http://${cloud_ip}:8333"
            changed=$((changed + 1))
        else
            info "[docker-compose.yml] 无硬编码 IP（已使用环境变量）"
        fi
    fi

    # 3. docker-compose.prod.yml (如果也有硬编码)
    local prod_compose="${PROJECT_ROOT}/deployment/docker/docker-compose.prod.yml"
    if [ -f "${prod_compose}" ] && grep -q "192\.168\." "${prod_compose}"; then
        sed -i "s|http://192\.168\.[0-9]\+\.[0-9]\+:8333|http://${cloud_ip}:8333|g" "${prod_compose}"
        info "[docker-compose.prod.yml] S3_EXTERNAL_ENDPOINT → http://${cloud_ip}:8333"
        changed=$((changed + 1))
    fi

    # 4. models/construction_safety/configs/construction_safety.yaml - fallback_stream
    local yaml_file="${PROJECT_ROOT}/models/construction_safety/configs/construction_safety.yaml"
    if [ -f "${yaml_file}" ]; then
        if grep -q "rtmp://192\.168\." "${yaml_file}"; then
            sed -i "s|rtmp://192\.168\.[0-9]\+\.[0-9]\+:1935|rtmp://${cloud_ip}:1935|g" "${yaml_file}"
            info "[construction_safety.yaml] fallback_stream → rtmp://${cloud_ip}:1935"
            changed=$((changed + 1))
        else
            info "[construction_safety.yaml] 已是最新"
        fi
    fi

    # 5. backend/src/main/java/com/edge/cloud/service/OtaService.java - 默认值
    local ota_java="${PROJECT_ROOT}/backend/src/main/java/com/edge/cloud/service/OtaService.java"
    if [ -f "${ota_java}" ]; then
        if grep -q "192\.168\." "${ota_java}"; then
            sed -i "s|http://192\.168\.[0-9]\+\.[0-9]\+:8333|http://${cloud_ip}:8333|g" "${ota_java}"
            info "[OtaService.java] S3_EXTERNAL_ENDPOINT 默认值 → http://${cloud_ip}:8333"
            changed=$((changed + 1))
        else
            info "[OtaService.java] 已是最新"
        fi
    fi

    # 6. 扫描其他 YAML 场景配置文件
    for scene_yaml in "${PROJECT_ROOT}"/models/*/configs/*.yaml; do
        [ -f "${scene_yaml}" ] || continue
        local basename
        basename=$(basename "${scene_yaml}")
        if grep -q "192\.168\." "${scene_yaml}"; then
            sed -i "s|192\.168\.[0-9]\+\.[0-9]\+|${cloud_ip}|g" "${scene_yaml}"
            info "[${basename}] IP 已更新 → ${cloud_ip}"
            changed=$((changed + 1))
        fi
    done

    echo ""
    if [ ${changed} -gt 0 ]; then
        info "共更新 ${changed} 个文件"
    else
        info "所有文件已是最新，无需更新"
    fi
}

# ========== 显示当前配置 ==========
show_config() {
    read_env_ip
    echo ""
    echo "========== 当前 IP 配置 =========="
    echo "云端服务器:  ${CLOUD_IP}"
    echo "边缘设备:    ${EDGE_IP}"
    echo "API 端口:    ${CLOUD_API_PORT}"
    echo "MQTT 端口:   ${CLOUD_MQTT_PORT}"
    echo "RTMP 端口:   ${CLOUD_RTMP_PORT}"
    echo "=================================="
    echo ""
    echo "--- 关联配置文件 ---"
    echo "  CLOUD_API_URL      = http://${CLOUD_IP}"
    echo "  CLOUD_MQTT_BROKER  = tcp://${CLOUD_IP}:${CLOUD_MQTT_PORT}"
    echo "  CLOUD_RTMP_URL     = rtmp://${CLOUD_IP}:${CLOUD_RTMP_PORT}"
    echo "  S3_EXTERNAL        = http://${CLOUD_IP}:8333"
    echo ""
}

# ========== 自动检测本机 IP ==========
auto_detect_ip() {
    local detected_ip
    detected_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "${detected_ip}" ]; then
        # macOS fallback
        detected_ip=$(ifconfig 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
    fi
    if [ -z "${detected_ip}" ]; then
        error "无法自动检测本机 IP，请手动指定: --cloud <IP>"
    fi
    echo "${detected_ip}"
}

# ========== 主入口 ==========
main() {
    local cloud_ip=""
    local edge_ip=""

    # 解析参数
    while [ $# -gt 0 ]; do
        case "$1" in
            --cloud)
                cloud_ip="${2}"
                shift 2
                ;;
            --edge)
                edge_ip="${2}"
                shift 2
                ;;
            --auto)
                cloud_ip=$(auto_detect_ip)
                info "自动检测云端 IP: ${cloud_ip}"
                shift
                ;;
            --show)
                show_config
                exit 0
                ;;
            --help|-h)
                echo "用法: $0 [选项]"
                echo ""
                echo "  --cloud <IP>       设置云端服务器 IP"
                echo "  --edge <IP>        设置边缘设备 IP"
                echo "  --auto             自动检测本机 IP 作为云端 IP"
                echo "  --show             显示当前 IP 配置"
                echo "  --help             显示帮助"
                echo ""
                echo "示例:"
                echo "  $0 --cloud 192.168.1.123 --edge 192.168.0.1"
                echo "  $0 --auto"
                exit 0
                ;;
            *)
                error "未知参数: $1 (使用 --help 查看帮助)"
                ;;
        esac
    done

    # 读取当前值
    read_env_ip

    # 如果没有指定参数，交互式询问
    if [ -z "${cloud_ip}" ] && [ -z "${edge_ip}" ]; then
        echo ""
        echo "========== IP 地址配置 =========="
        echo "当前云端 IP: ${CLOUD_IP}"
        echo "当前边缘 IP: ${EDGE_IP}"
        echo ""
        read -rp "请输入云端服务器 IP [${CLOUD_IP}]: " input_cloud
        read -rp "请输入边缘设备 IP [${EDGE_IP}]: " input_edge
        cloud_ip="${input_cloud:-${CLOUD_IP}}"
        edge_ip="${input_edge:-${EDGE_IP}}"
    fi

    # 使用当前值作为默认
    cloud_ip="${cloud_ip:-${CLOUD_IP}}"
    edge_ip="${edge_ip:-${EDGE_IP}}"

    # 验证 IP 格式
    local ip_regex='^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'
    if ! [[ "${cloud_ip}" =~ ${ip_regex} ]]; then
        error "云端 IP 格式错误: ${cloud_ip}"
    fi
    if ! [[ "${edge_ip}" =~ ${ip_regex} ]]; then
        error "边缘 IP 格式错误: ${edge_ip}"
    fi

    echo ""
    info "云端 IP: ${cloud_ip}"
    info "边缘 IP: ${edge_ip}"
    echo ""

    # 1. 更新 .env.ip
    update_env_ip "${cloud_ip}" "${edge_ip}"

    # 2. 同步到所有配置文件
    sync_all_configs "${cloud_ip}" "${edge_ip}"

    echo ""
    info "===== IP 配置完成 ====="
    info "所有配置文件已同步更新"
    echo ""
}

main "$@"
