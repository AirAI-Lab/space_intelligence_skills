#!/bin/bash
# Jetson设备上运行 - 初始化Git并关联远程仓库
#
# 使用方法：
# 1. 将此脚本复制到Jetson的edge_infer项目根目录
# 2. chmod +x init_jetson_git.sh
# 3. ./init_jetson_git.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}edge_infer - Jetson Git 初始化${NC}"
echo -e "${GREEN}========================================${NC}"

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

echo -e "\n当前目录: $SCRIPT_DIR"

# 远程仓库配置
REMOTE_REPO="git@github.com:AirAI-Lab/edge_infer.git"
BRANCH_NAME="master"

echo -e "\n${YELLOW}1. 检查是否已是Git仓库...${NC}"
if [ -d ".git" ]; then
    echo -e "${YELLOW}检测到.git目录已存在${NC}"

    # 检查远程仓库
    if git remote get-url origin &>/dev/null; then
        CURRENT_REMOTE=$(git remote get-url origin)
        echo "当前远程仓库: $CURRENT_REMOTE"

        if [[ "$CURRENT_REMOTE" == *"edge_infer"* ]]; then
            echo -e "${GREEN}远程仓库已正确配置${NC}"
        else
            echo -e "\n${YELLOW}更新远程仓库URL...${NC}"
            git remote set-url origin "$REMOTE_REPO"
            echo -e "${GREEN}远程仓库已更新为: $REMOTE_REPO${NC}"
        fi
    else
        echo -e "\n${YELLOW}添加远程仓库...${NC}"
        git remote add origin "$REMOTE_REPO"
        echo -e "${GREEN}远程仓库已添加${NC}"
    fi
else
    echo -e "\n${YELLOW}2. 初始化Git仓库...${NC}"
    git init

    echo -e "\n${YELLOW}3. 添加远程仓库...${NC}"
    git remote add origin "$REMOTE_REPO"
    echo -e "${GREEN}Git仓库初始化完成${NC}"
fi

echo -e "\n${YELLOW}4. 创建.gitignore（如果不存在）...${NC}"
if [ ! -f ".gitignore" ]; then
    cat > .gitignore << 'EOF'
# 编译产物
build*/
install/
*.o
*.a
*.so

# 日志文件
logs/
*.log

# 模型文件（通常很大）
models/*.onnx
models/*.engine
models/*.pt
models/*.pth

# 数据集
models/*/datasets/

# Python缓存
__pycache__/
*.pyc
*.pyo

# IDE配置
.vscode/
.idea/
*.swp

# 临时文件
*.tmp
.DS_Store
EOF
    echo -e "${GREEN}.gitignore已创建${NC}"
else
    echo ".gitignore已存在"
fi

echo -e "\n${YELLOW}5. 添加当前文件到Git...${NC}"
# 先拉取远程分支信息
git fetch origin || echo -e "${YELLOW}远程仓库可能为空或无权限访问${NC}"

# 检查远程分支是否存在
if git rev-parse --verify origin/$BRANCH_NAME &>/dev/null; then
    echo -e "\n${YELLOW}6. 检测到远程分支 $BRANCH_NAME${NC}"

    # 保存当前可能的本地修改
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo -e "${YELLOW}保存本地修改...${NC}"
        git stash push -m "local-changes-before-init-$(date +%Y%m%d_%H%M%S)"
    fi

    echo -e "\n${YELLOW}7. 合并远程代码（保留本地文件）...${NC}"
    git merge origin/$BRANCH_NAME --allow-unrelated-histories -m "Merge remote tracking branch $BRANCH_NAME" || {
        echo -e "${RED}合并失败，请手动解决冲突${NC}"
        echo "冲突文件: "
        git diff --name-only --diff-filter=U
        exit 1
    }

    # 恢复本地修改
    if git stash list | grep -q "local-changes-before-init"; then
        echo -e "\n${YELLOW}恢复本地修改...${NC}"
        git stash pop
    fi
else
    echo -e "\n${YELLOW}6. 远程分支不存在，初始化为第一个提交...${NC}"
    git add .
    git commit -m "init: 初始化Jetson edge_infer仓库" || echo "没有文件需要提交"
fi

echo -e "\n${YELLOW}8. 推送到远程仓库...${NC}"
# 设置上游分支
git branch --set-upstream-to=origin/$BRANCH_NAME $BRANCH_NAME 2>/dev/null || true

# 尝试推送
if git push origin $BRANCH_NAME; then
    echo -e "${GREEN}推送成功${NC}"
else
    echo -e "${YELLOW}推送失败，可能需要先拉取远程代码${NC}"
    echo "请手动执行: git pull origin $BRANCH_NAME --allow-unrelated-histories"
    echo "然后: git push origin $BRANCH_NAME"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Git初始化完成！${NC}"
echo -e "\n${YELLOW}后续同步操作：${NC}"
echo -e "  拉取: git pull origin $BRANCH_NAME"
echo -e "  推送: git push origin $BRANCH_NAME"
echo -e "  状态: git status"
echo -e "${GREEN}========================================${NC}"
