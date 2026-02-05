#!/bin/bash
# Jetson设备上运行 - 拉取edge_infer最新代码并编译
#
# 使用方法：
# 1. 将此脚本复制到Jetson的edge_infer项目根目录
# 2. chmod +x sync_jetson_pull.sh
# 3. ./sync_jetson_pull.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}edge_infer 代码同步 - Jetson拉取${NC}"
echo -e "${GREEN}========================================${NC}"

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

# 云端服务器配置
CLOUD_SERVER_IP="172.28.192.1"  # 修改为您的云服务器IP
EDGE_CLOUD_REPO="git@github.com:AirAI-Lab/edge_infer_cloud.git"

echo -e "\n${YELLOW}1. 保存本地修改（如有）...${NC}"
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "发现本地修改，创建stash..."
    git stash push -m "auto-stash-$(date +%Y%m%d_%H%M%S)"
fi

echo -e "\n${YELLOW}2. 获取远程最新代码...${NC}"
git fetch origin

echo -e "\n${YELLOW}3. 检查当前分支...${NC}"
CURRENT_BRANCH=$(git branch --show-current)
echo "当前分支: $CURRENT_BRANCH"

# 检查是否有远程更新
if [ $(git rev-list HEAD...origin/$CURRENT_BRANCH --count) -eq 0 ]; then
    echo -e "${GREEN}已是最新代码，无需更新${NC}"
else
    echo -e "\n${YELLOW}4. 拉取并合并远程代码...${NC}"
    git pull origin "$CURRENT_BRANCH" || {
        echo -e "${RED}拉取失败，可能有冲突${NC}"
        echo "请手动解决冲突后运行: git add . && git commit"
        exit 1
    }
fi

echo -e "\n${YELLOW}5. 更新云端配置...${NC}"
CLOUD_CONFIG_FILE="config/cloud_config.json"

if [ ! -f "$CLOUD_CONFIG_FILE" ]; then
    echo -e "${RED}警告: cloud_config.json 不存在，请手动创建${NC}"
else
    # 询问是否更新服务器IP
    read -p "是否更新云服务器IP? (当前: $CLOUD_SERVER_IP) [y/N]: " UPDATE_IP
    if [[ "$UPDATE_IP" =~ ^[Yy]$ ]]; then
        read -p "请输入云服务器IP: " NEW_IP
        if [ -n "$NEW_IP" ]; then
            CLOUD_SERVER_IP="$NEW_IP"
            # 使用sed更新配置文件中的IP
            if command -v sed &> /dev/null; then
                sed -i "s/172\.28\.192\.1/$CLOUD_SERVER_IP/g" "$CLOUD_CONFIG_FILE"
                echo -e "${GREEN}云服务器IP已更新为: $CLOUD_SERVER_IP${NC}"
            fi
        fi
    fi
fi

echo -e "\n${YELLOW}6. 编译项目（启用MQTT支持）...${NC}"
BUILD_DIR="build_mqtt"

if [ -d "$BUILD_DIR" ]; then
    echo "清理旧的编译目录..."
    rm -rf "$BUILD_DIR"
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "配置CMake (启用MQTT)..."
cmake -DUSE_MQTT=ON .. || {
    echo -e "${RED}CMake配置失败${NC}"
    exit 1
}

echo "编译中..."
make -j$(nproc) || {
    echo -e "${RED}编译失败${NC}"
    exit 1
}

echo -e "\n${YELLOW}7. 安装到目标目录...${NC}"
cd ..
mkdir -p install
# 如果有install步骤
if [ -f "$BUILD_DIR/Makefile" ]; then
    cd "$BUILD_DIR"
    make install || echo -e "${YELLOW}警告: make install 失败，可能需要手动安装${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}同步完成！${NC}"
echo -e "${GREEN}编译输出: $SCRIPT_DIR/$BUILD_DIR${NC}"
echo -e "${GREEN}安装目录: $SCRIPT_DIR/install${NC}"
echo -e "\n${YELLOW}下一步：${NC}"
echo -e "1. 更新设备ID（如需要）：编辑 config/cloud_config.json"
echo -e "2. 启动程序: cd $SCRIPT_DIR && ./install/bin/edge_framework"
echo -e "${GREEN}========================================${NC}"
