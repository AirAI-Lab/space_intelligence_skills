# Jetson Git 初始化步骤

## 方法1: 直接在Jetson上创建脚本

### 步骤1: SSH到Jetson
```bash
ssh nvidia@192.168.0.104
```

### 步骤2: 进入edge_infer目录并创建脚本
```bash
cd ~/edge_infer

# 创建初始化脚本
cat > init_jetson_git.sh << 'SCRIPT_EOF'
#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Jetson Git 初始化 ===${NC}"

# 配置
REMOTE_REPO="git@github.com:AirAI-Lab/edge_infer.git"
BRANCH="master"

# 初始化或检查Git
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}初始化Git仓库...${NC}"
    git init
    git remote add origin "$REMOTE_REPO"
else
    echo "Git仓库已存在"
    git remote set-url origin "$REMOTE_REPO" 2>/dev/null || \
    git remote add origin "$REMOTE_REPO"
fi

# 创建.gitignore
cat > .gitignore << 'EOF'
build*/
install/
logs/
*.log
models/*.onnx
models/*.engine
models/*/datasets/
__pycache__/
.vscode/
.idea/
EOF

# 拉取远程代码
echo -e "${YELLOW}拉取远程代码...${NC}"
git fetch origin

# 合并远程分支
if git rev-parse --verify origin/$BRANCH &>/dev/null; then
    echo -e "${YELLOW}合并远程分支...${NC}"
    git merge origin/$BRANCH --allow-unrelated-histories -m "Merge remote $BRANCH" || {
        echo "合并冲突，请手动解决"
        exit 1
    }
fi

# 添加并提交本地修改
git add .
git commit -m "feat: Jetson本地修改" || echo "没有新修改"

# 推送
echo -e "${YELLOW}推送到远程...${NC}"
git push -u origin $BRANCH || {
    echo "推送失败，可能需要先pull"
    git pull origin $BRANCH --allow-unrelated-histories
    git push -u origin $BRANCH
}

echo -e "${GREEN}完成！${NC}"
SCRIPT_EOF

# 添加执行权限
chmod +x init_jetson_git.sh

# 执行脚本
./init_jetson_git.sh
```

## 方法2: 从本机复制脚本到Jetson

在本机执行：
```bash
cd D:\github\edge_infer_cloud\scripts\sync

# Windows使用scp（需要WSL或Git Bash）
scp init_jetson_git.sh nvidia@192.168.0.104:~/edge_infer/

# 然后SSH到Jetson执行
ssh nvidia@192.168.0.104 "cd ~/edge_infer && chmod +x init_jetson_git.sh && ./init_jetson_git.sh"
```

## 初始化后的日常同步

### 拉取最新代码
```bash
ssh nvidia@192.168.0.104 "cd ~/edge_infer && git pull origin master"
```

### 推送Jetson修改
```bash
ssh nvidia@192.168.0.104 "cd ~/edge_infer && git add . && git commit -m 'update' && git push origin master"
```

## 一键脚本使用

初始化完成后，使用 `sync_jetson_pull.sh` 进行日常同步：
```bash
# 在Jetson上
cd ~/edge_infer
./sync_jetson_pull.sh
```

## 故障排查

### SSH密钥问题
```bash
# 在Jetson上生成SSH密钥
ssh-keygen -t ed25519 -C "nvidia@jetson"

# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 将公钥添加到GitHub: Settings -> SSH Keys
```

### 权限问题
```bash
# 确认对edge_infer目录有写权限
ls -la ~/edge_infer

# 如需要，修改权限
sudo chown -R nvidia:nvidia ~/edge_infer
```
