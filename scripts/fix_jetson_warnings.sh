#!/bin/bash
# Jetson 编译警告修复脚本

set -e

echo "=== Jetson 编译警告修复 ==="
echo ""

cd ~/edge_infer

# 1. 取消合并冲突
echo "1. 取消合并冲突..."
git merge --abort 2>/dev/null || true

# 2. 重置到远程版本
echo "2. 重置到远程版本..."
git reset --hard origin/master

# 3. 清理并重新编译
echo "3. 清理构建目录..."
rm -rf build
mkdir build
cd build

echo "4. 运行 CMake..."
cmake .. -DUSE_TENSORRT=ON 2>&1 | tee cmake.log

echo "5. 编译（捕获警告）..."
make -j$(nproc) 2>&1 | tee compile.log

echo ""
echo "=== 编译完成 ==="
echo ""

# 提取警告信息
echo "=== 编译警告摘要 ==="
grep -i "warning" compile.log | head -20 || echo "没有发现警告"

echo ""
echo "=== 编译错误摘要 ==="
grep -i "error" compile.log | head -10 || echo "没有发现错误"

echo ""
echo "=== 检查 edge_framework ==="
if [ -f "edge_framework" ]; then
    echo "✓ edge_framework 编译成功"
    ls -lh edge_framework
    echo ""
    echo "启动命令:"
    echo "  ./edge_framework"
else
    echo "✗ edge_framework 编译失败"
    echo ""
    echo "请检查 compile.log 中的错误信息"
fi

echo ""
echo "=== 完成 ==="
