#!/bin/bash
# EMQX 5.x 规则引擎初始化脚本
# 在 EMQX 容器启动后自动创建 MQTT 连接器、动作和规则，用于第三方对接
#
# EMQX 5.5 API 说明:
#   - REST API 需要 JWT token (通过 /api/v5/login 获取) 或 API Key
#   - 动作(Actions) 需要先创建连接器(Connector), 再创建 Action, 最后关联到 Rule
#   - 使用 mqtt 类型连接器实现消息 republish
#
# 规则说明:
#   Rule 1: 边缘结果归一化 → results/{device_id}/{channel_id}/edge
#   Rule 2: 云端结果归一化 → results/{device_id}/{channel_id}/cloud
#   Rule 3a: 边缘告警提取  → alerts/{device_id}/edge
#   Rule 3b: 云端告警提取  → alerts/{device_id}/cloud
#
# 使用:
#   docker compose up -d   # 自动初始化
#   或手动: bash init_rules.sh

set -e

EMQX_HOST="${EMQX_HOST:-localhost}"
EMQX_API="http://${EMQX_HOST}:18083/api/v5"
EMQX_USER="${EMQX_DASHBOARD__DEFAULT_USERNAME:-admin}"
EMQX_PASS="${EMQX_DASHBOARD__DEFAULT_PASSWORD:-admin123456}"

log() { echo "[EMQX-INIT] $*"; }

# 等待 EMQX API 就绪
wait_ready() {
    for i in $(seq 1 30); do
        if curl -sf -X POST "${EMQX_API}/login" \
            -H "Content-Type: application/json" \
            -d "{\"username\":\"${EMQX_USER}\",\"password\":\"${EMQX_PASS}\"}" \
            > /dev/null 2>&1; then
            log "EMQX API 就绪"
            return 0
        fi
        sleep 2
    done
    log "ERROR: EMQX API 未就绪, 跳过规则初始化"
    return 1
}

# 获取 JWT token
get_token() {
    local resp
    resp=$(curl -sf -X POST "${EMQX_API}/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"${EMQX_USER}\",\"password\":\"${EMQX_PASS}\"}")
    echo "$resp" | grep -o '"token":"[^"]*"' | cut -d'"' -f4
}

# 使用 token 执行 API 调用
api_call() {
    local method="$1"
    local path="$2"
    local data="$3"
    local token
    token=$(get_token)
    if [ -z "$token" ]; then
        log "ERROR: 无法获取 JWT token"
        return 1
    fi
    if [ "$method" = "GET" ]; then
        curl -sf -H "Authorization: Bearer $token" "${EMQX_API}${path}"
    else
        curl -sf -H "Authorization: Bearer $token" -X "$method" "${EMQX_API}${path}" \
            -H "Content-Type: application/json" -d "$data"
    fi
}

# 创建 MQTT 连接器 (用于 republish)
create_connector() {
    local name="republish_connector"
    # 检查是否已存在
    if api_call GET "/connectors/mqtt:${name}" > /dev/null 2>&1; then
        log "连接器 ${name} 已存在, 跳过"
        return 0
    fi
    api_call POST "/connectors" "{
        \"type\": \"mqtt\",
        \"name\": \"${name}\",
        \"enable\": true,
        \"server\": \"${EMQX_REPUBLISH_SERVER:-emqx:1883}\"
    }" > /dev/null && log "连接器 ${name} 创建成功" || log "WARNING: 连接器 ${name} 创建失败"
}

# 创建 MQTT 动作
create_action() {
    local name="$1"
    local topic="$2"
    # 检查是否已存在
    if api_call GET "/actions/mqtt:${name}" > /dev/null 2>&1; then
        log "动作 ${name} 已存在, 跳过"
        return 0
    fi
    api_call POST "/actions" "{
        \"type\": \"mqtt\",
        \"name\": \"${name}\",
        \"connector\": \"republish_connector\",
        \"enable\": true,
        \"parameters\": {
            \"topic\": \"${topic}\",
            \"qos\": 1,
            \"retain\": false
        }
    }" > /dev/null && log "动作 ${name} 创建成功" || log "WARNING: 动作 ${name} 创建失败"
}

# 创建规则
create_rule() {
    local id="$1"
    local sql="$2"
    local desc="$3"
    local action="$4"
    # 检查是否已存在
    if api_call GET "/rules/${id}" > /dev/null 2>&1; then
        log "规则 ${id} 已存在, 跳过"
        return 0
    fi
    api_call POST "/rules" "{
        \"id\": \"${id}\",
        \"sql\": ${sql},
        \"description\": \"${desc}\",
        \"actions\": [\"${action}\"]
    }" > /dev/null && log "规则 ${id} 创建成功" || log "WARNING: 规则 ${id} 创建失败"
}

# ─────────────────────────────────────────────
# 主逻辑
# ─────────────────────────────────────────────

log "开始初始化 EMQX 规则引擎..."
wait_ready || exit 0

# Step 1: 创建 MQTT 连接器
log "创建 MQTT 连接器..."
create_connector

# Step 2: 创建动作
log "创建 MQTT 动作..."
create_action "edge_normalize_action" 'results/${payload.device_id}/${payload.channel_id}/edge'
create_action "cloud_normalize_action" 'results/${payload.device_id}/${payload.channel_id}/cloud'
create_action "edge_alerts_action" 'alerts/${payload.device_id}/edge'
create_action "cloud_alerts_action" 'alerts/${payload.device_id}/cloud'

# Step 3: 创建规则
log "创建规则..."
create_rule "rule_edge_normalize" \
    '"SELECT payload FROM \"device/+/inference/results\""' \
    "边缘推理结果归一化" \
    "mqtt:edge_normalize_action"

create_rule "rule_cloud_normalize" \
    '"SELECT payload FROM \"device/+/cloud/result\""' \
    "云端推理结果归一化" \
    "mqtt:cloud_normalize_action"

create_rule "rule_edge_alerts" \
    '"SELECT payload FROM \"device/+/inference/results\" WHERE json_length(payload.detections) > 0"' \
    "边缘告警结果提取" \
    "mqtt:edge_alerts_action"

create_rule "rule_cloud_alerts" \
    '"SELECT payload FROM \"device/+/cloud/result\" WHERE json_length(payload.alerts) > 0"' \
    "云端告警结果提取" \
    "mqtt:cloud_alerts_action"

log "EMQX 规则引擎初始化完成"
log "统一 topic 树:"
log "  results/{device_id}/{channel_id}/edge   ← 边缘推理结果"
log "  results/{device_id}/{channel_id}/cloud  ← 云端推理结果"
log "  alerts/{device_id}/edge                 ← 边缘告警"
log "  alerts/{device_id}/cloud                ← 云端告警"
