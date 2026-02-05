#!/usr/bin/env bash
# 验证存储配置并测试文件上传下载功能

set -euo pipefail

# 配置
CLOUD_BASE_URL="${CLOUD_BASE_URL:-http://localhost:8081}"
TEST_FILE="${TEST_FILE:-scripts/test_conversion_upload.sh}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}==========================================${NC}"
}

# ============================================
# 1. 检查后端服务是否运行
# ============================================
log_header "1. 检查后端服务"

if curl -s -f "${CLOUD_BASE_URL}/actuator/health" > /dev/null 2>&1; then
    log_info "✓ 后端服务运行正常"
    HEALTH=$(curl -s "${CLOUD_BASE_URL}/actuator/health" | jq '.' 2>/dev/null || echo "{}")
    echo "$HEALTH" | jq -r '.status // "unknown"' 2>/dev/null && echo "$HEALTH" 2>/dev/null
else
    log_warn "后端服务可能未运行或 actuator 端点未启用"
    log_info "尝试访问主页..."
    if curl -s -f "${CLOUD_BASE_URL}/" > /dev/null 2>&1; then
        log_info "✓ 后端服务可访问"
    else
        log_error "✗ 无法连接到后端服务: $CLOUD_BASE_URL"
        exit 1
    fi
fi

# ============================================
# 2. 检查存储配置
# ============================================
log_header "2. 检查存储配置"

log_info "检查环境变量配置..."

echo ""
echo "当前配置:"
echo "  CLOUD_BASE_URL = $CLOUD_BASE_URL"
echo "  FILE_STORAGE_TYPE = ${FILE_STORAGE_TYPE:-未设置 (默认: local)}"
echo ""

if [ "${FILE_STORAGE_TYPE:-local}" = "s3" ]; then
    echo "S3 配置:"
    echo "  S3_ENDPOINT = ${S3_ENDPOINT:-未设置}"
    echo "  S3_BUCKET = ${S3_BUCKET:-未设置}"
    echo "  S3_ACCESS_KEY = ${S3_ACCESS_KEY:+已设置}"
    echo ""
else
    echo "使用本地存储，文件将保存在: data/files/"
    echo ""
fi

# ============================================
# 3. 创建测试文件
# ============================================
log_header "3. 创建测试文件"

TEST_FILE_DIR="data/test"
mkdir -p "$TEST_FILE_DIR"

TEST_ONNX="$TEST_FILE_DIR/test_model.onnx"

# 创建一个简单的 ONNX 测试文件（实际使用时应该用真实文件）
if [ ! -f "$TEST_ONNX" ]; then
    log_info "创建测试 ONNX 文件..."
    # 创建一个 1MB 的测试文件
    dd if=/dev/zero of="$TEST_ONNX" bs=1024 count=1024 2>/dev/null
    log_info "✓ 测试文件已创建: $TEST_ONNX"
else
    log_info "使用现有测试文件: $TEST_ONNX"
fi

# ============================================
# 4. 测试存储服务直接上传
# ============================================
log_header "4. 测试存储服务"

log_info "创建测试模型记录..."

# 首先创建一个模型记录
CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    "${CLOUD_BASE_URL}/api/v1/models" \
    -H "Content-Type: application/json" \
    -d '{
        "modelName": "test_storage_model",
        "modelType": "DETECTION",
        "framework": "ONNX",
        "version": "1.0.0"
    }')

CREATE_HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
CREATE_BODY=$(echo "$CREATE_RESPONSE" | head -n-1)

if [ "$CREATE_HTTP_CODE" = "200" ]; then
    TEST_MODEL_ID=$(echo "$CREATE_BODY" | jq -r '.data.modelId // empty')
    log_info "✓ 测试模型创建成功: $TEST_MODEL_ID"
else
    log_error "✗ 创建测试模型失败 (HTTP $CREATE_HTTP_CODE)"
    echo "$CREATE_BODY"
    exit 1
fi

# 上传测试文件
log_info "上传测试文件..."

UPLOAD_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    "${CLOUD_BASE_URL}/api/v1/models/${TEST_MODEL_ID}/upload" \
    -F "file=@$TEST_ONNX")

UPLOAD_HTTP_CODE=$(echo "$UPLOAD_RESPONSE" | tail -n1)
UPLOAD_BODY=$(echo "$UPLOAD_RESPONSE" | head -n-1)

if [ "$UPLOAD_HTTP_CODE" = "200" ]; then
    log_info "✓ 文件上传成功"

    # 获取上传后的文件路径
    UPLOADED_PATH=$(echo "$UPLOAD_BODY" | jq -r '.data.ptFilePath // .data.onnxFilePath // empty')
    log_info "上传后的文件路径: $UPLOADED_PATH"
else
    log_error "✗ 文件上传失败 (HTTP $UPLOAD_HTTP_CODE)"
    echo "$UPLOAD_BODY"
    exit 1
fi

# ============================================
# 5. 测试文件下载
# ============================================
log_header "5. 测试文件下载"

log_info "测试下载 ONNX 格式..."

# 测试下载（只获取前 1KB）
DOWNLOAD_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X GET \
    "${CLOUD_BASE_URL}/api/v1/models/${TEST_MODEL_ID}/download?format=onnx" \
    -H "Range: bytes=0-1023" \
    --max-time 10)

DOWNLOAD_HTTP_CODE=$(echo "$DOWNLOAD_RESPONSE" | tail -n1)

if [ "$DOWNLOAD_HTTP_CODE" = "206" ] || [ "$DOWNLOAD_HTTP_CODE" = "200" ]; then
    log_info "✓ 文件下载成功 (HTTP $DOWNLOAD_HTTP_CODE)"
else
    log_error "✗ 文件下载失败 (HTTP $DOWNLOAD_HTTP_CODE)"
fi

# ============================================
# 6. 测试存在性检查
# ============================================
log_header "6. 测试文件存在性检查"

log_info "检查文件是否存在..."

# 通过存储服务检查文件是否存在
EXISTS_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X GET \
    "${CLOUD_BASE_URL}/api/v1/models/${TEST_MODEL_ID}/download-info")

EXISTS_HTTP_CODE=$(echo "$EXISTS_RESPONSE" | tail -n1)

if [ "$EXISTS_HTTP_CODE" = "200" ]; then
    log_info "✓ 模型下载信息获取成功"
    EXISTS_BODY=$(echo "$EXISTS_RESPONSE" | head -n-1)
    echo "$EXISTS_BODY" | jq '.' 2>/dev/null || echo "$EXISTS_BODY"
else
    log_warn "无法获取模型下载信息 (HTTP $EXISTS_HTTP_CODE)"
fi

# ============================================
# 7. 清理测试数据
# ============================================
log_header "7. 清理测试数据"

log_info "删除测试模型..."

DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X DELETE \
    "${CLOUD_BASE_URL}/api/v1/models/${TEST_MODEL_ID}")

DELETE_HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)

if [ "$DELETE_HTTP_CODE" = "200" ]; then
    log_info "✓ 测试模型已删除"
else
    log_warn "删除测试模型失败 (HTTP $DELETE_HTTP_CODE)"
    log_info "请手动删除模型: $TEST_MODEL_ID"
fi

# ============================================
# 8. 总结
# ============================================
log_header "测试总结"

log_info "存储服务配置:"
echo "  存储类型: ${FILE_STORAGE_TYPE:-local (default)}"
echo "  后端地址: $CLOUD_BASE_URL"
echo ""

log_info "建议:"
if [ "${FILE_STORAGE_TYPE:-local}" = "local" ]; then
    echo "  - 当前使用本地存储，文件保存在 data/files/ 目录"
    echo "  - 生产环境建议配置 S3 存储"
    echo "  - 设置环境变量 FILE_STORAGE_TYPE=s3 启用 S3"
elif [ "${FILE_STORAGE_TYPE}" = "s3" ]; then
    echo "  - 使用 S3 存储"
    echo "  - 确保 S3_ENDPOINT, S3_BUCKET 等配置正确"
fi

echo ""
log_info "下一步:"
echo "  1. 使用 bash scripts/test_conversion_upload.sh <task_id> <onnx_file> 测试转换上传"
echo "  2. 启动前端验证完整的上传-下载流程"
echo "  3. 检查 S3 控制台确认文件已上传"
