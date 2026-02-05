# edge_infer 代码同步指南

## 概述

当本机和Jetson设备都对edge_infer项目有修改时，需要通过Git仓库进行代码同步。

## 同步策略

```
┌─────────────────┐         Git远程仓库         ┌─────────────────┐
│  本机 (开发机)   │ ◄───────────────────────► │  Jetson设备     │
│  edge_infer     │                           │  edge_infer     │
└─────────────────┘                           └─────────────────┘
```

## 场景一：本机有修改，需要同步到Jetson

### 步骤1: 本机推送

在本机运行：

```bash
# 方式1: 使用脚本（推荐）
cd D:\github\edge_infer_cloud\scripts\sync
bash push_local_edge_infer.sh

# 方式2: 手动命令
cd D:\github\edge_infer
git add .
git commit -m "feat: 描述你的修改"
git push origin master
```

### 步骤2: Jetson拉取

在Jetson设备上运行：

```bash
# 方式1: 使用脚本（推荐）
cd ~/edge_infer
./sync_jetson_pull.sh

# 方式2: 手动命令
cd ~/edge_infer
git fetch origin
git pull origin master
mkdir -p build_mqtt && cd build_mqtt
cmake -DUSE_MQTT=ON ..
make -j$(nproc)
```

## 场景二：Jetson有修改，需要同步到本机

### 步骤1: Jetson推送

在Jetson设备上运行：

```bash
cd ~/edge_infer
git add .
git commit -m "feat: 描述Jetson上的修改"
git push origin master
```

### 步骤2: 本机拉取

在本机运行：

```bash
cd D:\github\edge_infer
git pull origin master
```

## 场景三：两边都有修改（需要合并）

### 推荐流程：

1. **先在Jetson上推送修改**
   ```bash
   # Jetson
   cd ~/edge_infer
   git add .
   git commit -m "feat: Jetson修改"
   git push origin master
   ```

2. **在本机拉取并合并**
   ```bash
   # 本机
   cd D:\github\edge_infer
   git pull origin master
   # 如有冲突，手动解决后:
   # git add .
   # git commit
   ```

3. **本机推送合并后的代码**
   ```bash
   git push origin master
   ```

4. **Jetson拉取最终合并版本**
   ```bash
   # Jetson
   cd ~/edge_infer
   git pull origin master
   ```

## 快速同步命令

### 本机一键推送

```bash
cd D:\github\edge_infer
git add -A && git commit -m "sync: 本机修改同步" && git push origin master
```

### Jetson一键拉取编译

```bash
cd ~/edge_infer
git pull origin master && cd build_mqtt && make -j$(nproc)
```

## 常见问题

### Q1: 推送时提示 "fatal: remote origin already exists"

```bash
# 检查远程仓库
git remote -v

# 如需更新
git remote set-url origin git@github.com:AirAI-Lab/edge_infer.git
```

### Q2: 拉取时出现冲突

```bash
# 保留本地修改
git pull --rebase origin master

# 或使用stash保存本地修改
git stash
git pull origin master
git stash pop
```

### Q3: 编译时找不到MQTT库

```bash
# 在Jetson上安装MQTT库
sudo apt-get update
sudo apt-get install -y libmosquitto-dev libmosquitto1
```

## 自动化脚本

| 脚本 | 位置 | 说明 |
|------|------|------|
| push_local_edge_infer.sh | scripts/sync/ | 本机推送edge_infer代码 |
| sync_jetson_pull.sh | scripts/sync/ | Jetson拉取并编译代码 |

## 配置文件更新

每次拉取代码后，需要检查并更新：

1. **config/cloud_config.json** - 云端服务器IP
2. **config/framework_config.json** - 框架配置

示例更新cloud_config.json中的IP：

```bash
# 在Jetson上
cd ~/edge_infer
sed -i 's/172\.28\.192\.1/你的云服务器IP/g' config/cloud_config.json
```

## 验证同步

同步后验证：

```bash
# 检查代码版本
git log --oneline -1

# 检查MQTT功能是否编译
strings build_mqtt/bin/edge_framework | grep -i mqtt
```
