#!/bin/bash
# 将更新后的 edge_infer 源码打包并同步到 Jetson

set -e

echo "=== 同步 edge_infer 源码到 Jetson ==="

# 源码目录
SRC_DIR="D:/github/edge_infer"
JETSON_IP="192.168.0.104"
JETSON_USER="nvidia"
JETSON_DIR="/home/nvidia/edge_infer"

# 临时打包目录
TEMP_DIR="/tmp/edge_infer_sync_$$"
mkdir -p "$TEMP_DIR"

echo "1. 打包源码..."
# 只传输源码文件（不包含 build/, .venv/, 模型文件等）
cp -r "$SRC_DIR/src" "$TEMP_DIR/"
cp -r "$SRC_DIR/include" "$TEMP_DIR/"
cp -r "$SRC_DIR/config" "$TEMP_DIR/"
cp -r "$SRC_DIR/CMakeLists.txt" "$TEMP_DIR/"
cp -r "$SRC_DIR/scripts" "$TEMP_DIR/" 2>/dev/null || true

echo "2. 创建压缩包..."
cd /tmp
tar -czf "edge_infer_sync.tar.gz" -C "$TEMP_DIR" .
rm -rf "$TEMP_DIR"

echo "3. 传输到 Jetson..."
scp "edge_infer_sync.tar.gz" "${JETSON_USER}@${JETSON_IP}:~/"

echo "4. 在 Jetson 上解压..."
ssh "${JETSON_USER}@${JETSON_IP}" << 'EOF'
set -e
cd ~
rm -rf edge_infer_backup
mv edge_infer edge_infer_backup 2>/dev/null || true
mkdir -p edge_infer
tar -xzf edge_infer_sync.tar.gz -C edge_infer/
rm edge_infer_sync.tar.gz
echo "源码已同步到 ~/edge_infer"
EOF

# 清理临时文件
rm -f "/tmp/edge_infer_sync.tar.gz"

echo "=== 同步完成 ==="
echo ""
echo "请在 Jetson 上执行以下命令重新编译:"
echo ""
echo "  cd ~/edge_infer"
echo "  sudo rm -rf build"
echo "  mkdir build && cd build"
echo "  cmake .. -DUSE_TENSORRT=ON"
echo "  make -j\$(nproc)"
echo ""
