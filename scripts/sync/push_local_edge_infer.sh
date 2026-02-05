#!/bin/bash
# 本机edge_infer代码推送脚本
# 用于将本机的edge_infer修改推送到远程仓库，供Jetson设备拉取

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}edge_infer 代码同步 - 本机推送${NC}"
echo -e "${GREEN}========================================${NC}"

# 项目路径
EDGE_INFER_PATH="D:/github/edge_infer"
cd "$EDGE_INFER_PATH" || exit 1

echo -e "\n${YELLOW}1. 检查当前分支...${NC}"
CURRENT_BRANCH=$(git branch --show-current)
echo "当前分支: $CURRENT_BRANCH"

echo -e "\n${YELLOW}2. 检查Jetson是否有未推送的修改...${NC}"
echo "请在Jetson上先运行 sync_jeton_pull.sh 脚本，确保Jetson的修改已推送"

echo -e "\n${YELLOW}3. 拉取远程最新代码（如有冲突需手动解决）...${NC}"
git pull origin "$CURRENT_BRANCH" || {
    echo -e "${RED}拉取失败，可能有冲突，请手动解决后重新运行${NC}"
    exit 1
}

echo -e "\n${YELLOW}4. 添加所有修改文件...${NC}"
# 添加MQTT相关文件
git add include/mqtt/ src/mqtt/ config/cloud_config.json 2>/dev/null || true
# 添加其他修改
git add -A

echo -e "\n${YELLOW}5. 查看状态...${NC}"
git status --short

echo -e "\n${YELLOW}6. 提交修改...${NC}"
COMMIT_MSG="feat: 添加云边协同MQTT OTA支持

- 添加MQTT客户端和OTA处理器实现
- 添加云端配置文件 cloud_config.json
- 支持设备通过MQTT接收OTA升级命令
- 支持模型下载、MD5校验、热重载

Authored-By: AirAI-Lab <wennu1989@gmail.com>"

git commit -m "$COMMIT_MSG" || {
    echo -e "${YELLOW}没有新的修改需要提交${NC}"
}

echo -e "\n${YELLOW}7. 推送到远程仓库...${NC}"
git push origin "$CURRENT_BRANCH"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}推送完成！现在可以在Jetson上运行: ${NC}"
echo -e "${GREEN}./sync_jetson_pull.sh${NC}"
echo -e "${GREEN}========================================${NC}"
