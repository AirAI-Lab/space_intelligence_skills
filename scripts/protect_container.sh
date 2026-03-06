#!/bin/bash
# 快捷启动脚本 - 容器保护

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/protect_training_container.sh" "$@"
