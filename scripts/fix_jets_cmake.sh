#!/bin/bash
# Jetson CMake 权限修复脚本

set -e

echo "=== 修复 CMake 权限问题 ==="

cd ~/edge_infer

echo "1. 清理旧的 build 目录..."
sudo rm -rf build
sudo rm -f CMakeCache.txt CMakeFiles/

echo "2. 重新创建 build 目录..."
mkdir -p build
cd build

echo "3. 运行 CMake..."
cmake .. -DUSE_MQTT=ON -DUSE_TENSORRT=ON

echo "4. 编译..."
make -j$(nproc)

echo ""
echo "=== 编译完成 ==="
echo ""
echo "启动命令:"
echo "  cd ~/edge_infer/build"
echo "  ./edge_framework"
echo ""
