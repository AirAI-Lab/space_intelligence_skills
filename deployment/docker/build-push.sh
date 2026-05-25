#!/usr/bin/env bash
# ============================================
# SkyEdge AI Cloud Platform — 镜像构建与推送
# ============================================
#
# 用法:
#   ./build-push.sh                    # 构建 latest
#   ./build-push.sh v1.0.0             # 构建指定版本
#   REGISTRY=registry.example.com ./build-push.sh v1.0.0
#
# 前置条件:
#   - Docker 已安装并登录到目标仓库
#   - 在项目根目录执行
#
# ============================================

set -euo pipefail

VERSION=${1:-latest}
REGISTRY=${REGISTRY:-}
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
step()  { echo -e "${BLUE}[STEP]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

tag() {
    if [ -n "$REGISTRY" ]; then
        echo "${REGISTRY}/edge-cloud/${1}:${VERSION}"
    else
        echo "edge-cloud/${1}:${VERSION}"
    fi
}

cd "$PROJECT_ROOT"

# ---- 后端 ----
step "构建后端镜像: $(tag backend)"
docker build \
    -f deployment/docker/backend.Dockerfile \
    -t "$(tag backend)" \
    backend/

# ---- 前端 ----
step "构建前端镜像: $(tag frontend)"
docker build \
    -f deployment/docker/frontend.Dockerfile \
    -t "$(tag frontend)" \
    frontend/

# ---- 推送 ----
if [ -n "$REGISTRY" ]; then
    step "推送镜像到 ${REGISTRY}..."
    docker push "$(tag backend)"
    docker push "$(tag frontend)"
    info "推送完成"
else
    info "未设置 REGISTRY，跳过推送"
fi

echo ""
info "构建完成！镜像列表:"
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" \
    | grep "edge-cloud" | head -5
echo ""
info "部署方式:"
if [ -n "$REGISTRY" ]; then
    echo "  REGISTRY=${REGISTRY} VERSION=${VERSION} deployment/docker/deploy.sh"
else
    echo "  deployment/docker/deploy.sh"
fi
