#!/usr/bin/env bash
# 测试转换完成文件上传功能
#
# 用法:
#   bash scripts/test_conversion_upload.sh <task_id> <onnx_file_path>
#
# 示例:
#   bash scripts/test_conversion_upload.sh CONV2026010112000012345 models/helmet_detect/best.onnx

set -euo pipefail

# 配置
CLOUD_BASE_URL="${CLOUD_BASE_URL:-http://localhost:8080}"
TASK_ID="${1:-}"
ONNX_FILE="${2:-}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat <<EOF
用法: $0 <task_id> <onnx_file_path>

测试模型转换完成后的文件上传功能

参数:
  task_id          转换任务 ID (如: CONV2026010112000012345)
  onnx_file_path   要上传的 ONNX 文件路径

环境变量:
  CLOUD_BASE_URL   后端服务地址 (默认: http://localhost:8080)

示例:
  # 创建测试转换任务并上传文件
  bash scripts/test_conversion_upload.sh CONV2026010112000012345 models/helmet_detect/best.onnx

  # 使用自定义后端地址
  CLOUD_BASE_URL=http://192.168.1.100:8080 bash scripts/test_conversion_upload.sh ...
EOF
    exit 1
}

# 参数检查
if [ -z "$TASK_ID" ]; then
    log_error "缺少 task_id 参数"
    usage
fi

if [ -z "$ONNX_FILE" ]; then
    log_error "缺少 onnx_file_path 参数"
    usage
fi

if [ ! -f "$ONNX_FILE" ]; then
    log_error "文件不存在: $ONNX_FILE"
    exit 1
fi

# 获取文件大小和扩展名
FILE_SIZE=$(stat -f%z "$ONNX_FILE" 2>/dev/null || stat -c%s "$ONNX_FILE" 2>/dev/null || echo "0")
FILE_EXT="${ONNX_FILE##*.}"

log_info "测试配置:"
echo "  后端地址: $CLOUD_BASE_URL"
echo "  任务 ID: $TASK_ID"
echo "  文件路径: $ONNX_FILE"
echo "  文件大小: $FILE_SIZE bytes"
echo "  文件类型: $FILE_EXT"
echo ""

# ============================================
# 测试 1: 检查转换任务状态
# ============================================
log_info "测试 1: 检查转换任务状态..."

TASK_STATUS=$(curl -s "${CLOUD_BASE_URL}/api/v1/conversion/tasks/${TASK_ID}" | jq -r '.data.status // empty')

if [ -z "$TASK_STATUS" ]; then
    log_warn "无法获取任务状态，可能任务不存在"
else
    log_info "任务当前状态: $TASK_STATUS"
fi

# ============================================
# 测试 2: 上传转换完成的文件
# ============================================
log_info "测试 2: 上传转换完成的文件..."

UPLOAD_START=$(date +%s)

UPLOAD_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    "${CLOUD_BASE_URL}/api/v1/conversion/internal/${TASK_ID}/complete-with-file" \
    -F "file=@${ONNX_FILE}" \
    -F "optimization_time_seconds=60")

UPLOAD_END=$(date +%s)
UPLOAD_TIME=$((UPLOAD_END - UPLOAD_START))

# 分离响应体和状态码
UPLOAD_HTTP_CODE=$(echo "$UPLOAD_RESPONSE" | tail -n1)
UPLOAD_BODY=$(echo "$UPLOAD_RESPONSE" | head -n-1)

echo "HTTP 状态码: $UPLOAD_HTTP_CODE"
echo "响应内容:"
echo "$UPLOAD_BODY" | jq '.' 2>/dev/null || echo "$UPLOAD_BODY"
echo "上传耗时: ${UPLOAD_TIME}s"

# 检查上传是否成功
if [ "$UPLOAD_HTTP_CODE" = "200" ]; then
    log_info "✓ 文件上传成功"

    # 从响应中获取上传的 S3 key
    UPLOAD_SUCCESS=$(echo "$UPLOAD_BODY" | jq -r '.success // false')
    if [ "$UPLOAD_SUCCESS" = "true" ]; then
        log_info "上传已确认为成功"
    fi
else
    log_error "✗ 文件上传失败 (HTTP $UPLOAD_HTTP_CODE)"
    exit 1
fi

# ============================================
# 测试 3: 验证模型记录已更新
# ============================================
log_info "测试 3: 验证模型记录已更新..."

sleep 2  # 等待数据库更新

# 获取任务详情以获取 model_id
TASK_DETAIL=$(curl -s "${CLOUD_BASE_URL}/api/v1/conversion/tasks/${TASK_ID}")
MODEL_ID=$(echo "$TASK_DETAIL" | jq -r '.data.modelId // empty')

if [ -n "$MODEL_ID" ]; then
    log_info "关联的模型 ID: $MODEL_ID"

    # 获取模型详情
    MODEL_DETAIL=$(curl -s "${CLOUD_BASE_URL}/api/v1/models/${MODEL_ID}")

    # 检查 ONNX 文件路径
    ONNX_PATH=$(echo "$MODEL_DETAIL" | jq -r '.data.onnxFilePath // empty')
    ONNX_SIZE=$(echo "$MODEL_DETAIL" | jq -r '.data.onnxFileSizeBytes // 0')
    MODEL_STATUS=$(echo "$MODEL_DETAIL" | jq -r '.data.status // empty')

    echo "  模型状态: $MODEL_STATUS"
    echo "  ONNX 路径: $ONNX_PATH"
    echo "  ONNX 大小: $ONNX_SIZE bytes"

    if [ -n "$ONNX_PATH" ]; then
        log_info "✓ 模型记录已更新，文件路径已设置"

        # 检查是否是 S3 key (包含 models/ 或 uuid)
        if [[ "$ONNX_PATH" =~ ^models/ ]] || [[ "$ONNX_PATH" =~ ^[a-f0-9-]{36} ]]; then
            log_info "✓ 文件路径是 S3 key 格式"
        else
            log_warn "文件路径可能不是 S3 key 格式: $ONNX_PATH"
        fi
    else
        log_error "✗ 模型记录未更新，ONNX 路径为空"
    fi
else
    log_warn "无法获取模型 ID"
fi

# ============================================
# 测试 4: 验证文件下载功能
# ============================================
log_info "测试 4: 验证文件下载功能..."

if [ -n "$MODEL_ID" ]; then
    # 尝试下载 ONNX 文件（只下载前 1000 字节进行验证）
    DOWNLOAD_RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X GET \
        "${CLOUD_BASE_URL}/api/v1/models/${MODEL_ID}/download?format=onnx" \
        -H "Range: bytes=0-999" \
        --max-time 10)

    DOWNLOAD_HTTP_CODE=$(echo "$DOWNLOAD_RESPONSE" | tail -n1)

    if [ "$DOWNLOAD_HTTP_CODE" = "206" ] || [ "$DOWNLOAD_HTTP_CODE" = "200" ]; then
        log_info "✓ 文件下载功能正常 (HTTP $DOWNLOAD_HTTP_CODE)"

        # 检查 Content-Type
        CONTENT_TYPE=$(curl -s -I "${CLOUD_BASE_URL}/api/v1/models/${MODEL_ID}/download?format=onnx" \
            | grep -i "content-type" | head -1)
        echo "  Content-Type: $CONTENT_TYPE"

        if echo "$CONTENT_TYPE" | grep -qi "application/octet-stream"; then
            log_info "✓ Content-Type 正确"
        else
            log_warn "Content-Type 可能不正确"
        fi
    elif [ "$DOWNLOAD_HTTP_CODE" = "404" ]; then
        log_warn "✗ 文件未找到 (可能存储配置问题)"
    else
        log_error "✗ 下载失败 (HTTP $DOWNLOAD_HTTP_CODE)"
    fi
fi

# ============================================
# 测试总结
# ============================================
echo ""
log_info "=========================================="
log_info "测试总结"
log_info "=========================================="
log_info "任务 ID: $TASK_ID"
log_info "文件: $ONNX_FILE ($FILE_SIZE bytes)"
log_info "上传耗时: ${UPLOAD_TIME}s"
log_info "HTTP 状态: $UPLOAD_HTTP_CODE"
log_info ""
log_info "所有测试完成！"
