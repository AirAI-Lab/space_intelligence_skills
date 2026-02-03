#!/bin/bash
# 开发模式快速重启脚本
# 用于快速重新构建并重启后端服务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  云边协同平台 - 开发模式快速重启"
echo "=========================================="
echo ""

# 检查参数
if [ "$1" = "backend" ] || [ "$1" = "b" ]; then
    echo "🔧 重新构建并重启后端服务..."
    cd "$PROJECT_ROOT"
    docker-compose build backend
    docker-compose up -d backend
    echo "✅ 后端服务已重启"
    echo ""
    echo "📊 后端日志:"
    docker-compose logs -f backend
elif [ "$1" = "training" ] || [ "$1" = "t" ]; then
    echo "🔧 重新构建并重启训练服务..."
    cd "$PROJECT_ROOT"
    docker-compose --profile gpu build training
    docker-compose --profile gpu up -d training
    echo "✅ 训练服务已重启"
    echo ""
    echo "📊 训练日志:"
    docker-compose logs -f training
elif [ "$1" = "frontend" ] || [ "$1" = "f" ]; then
    echo "🔧 重新构建并重启前端服务..."
    cd "$PROJECT_ROOT"
    docker-compose build frontend
    docker-compose up -d frontend
    echo "✅ 前端服务已重启"
elif [ "$1" = "all" ] || [ "$1" = "a" ]; then
    echo "🔧 重新构建并重启所有服务..."
    cd "$PROJECT_ROOT"
    docker-compose build
    docker-compose up -d
    echo "✅ 所有服务已重启"
else
    echo "用法: $0 [backend|training|frontend|all]"
    echo ""
    echo "选项:"
    echo "  backend, b    - 仅重启后端服务"
    echo "  training, t   - 仅重启训练服务 (需要 --profile gpu)"
    echo "  frontend, f  - 仅重启前端服务"
    echo "  all, a       - 重启所有服务"
    echo ""
    echo "示例:"
    echo "  $0 backend     # 修改 Java 代码后使用"
    echo "  $0 training    # 修改 Python 代码后使用"
    echo "  $0 frontend    # 修改 Vue 代码后使用"
    echo "  $0 all         # 修改多个服务后使用"
fi
