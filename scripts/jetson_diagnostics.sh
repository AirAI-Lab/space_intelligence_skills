#!/bin/bash
# Jetson 诊断脚本

echo "=== Jetson 诊断 ==="
echo ""

cd ~/edge_infer 2>/dev/null || cd ~/edge_infer_backup* 2>/dev/null || cd ~/edge_infer

echo "1. 检查 Git 状态"
git status --short
git log --oneline -1

echo ""
echo "2. 检查配置文件"
ls -la config/

echo ""
echo "3. 检查 cloud_config.json"
if [ -f "config/cloud_config.json" ]; then
    cat config/cloud_config.json
else
    echo "cloud_config.json 不存在！"
fi

echo ""
echo "4. 测试 MQTT 连接"
timeout 3 bash -c "cat < /dev/null > /dev/tcp/192.168.0.103/1883" 2>&1 && echo "MQTT 端口可达" || echo "MQTT 端口不可达"

echo ""
echo "5. 检查编译产物"
ls -la build/edge_framework 2>/dev/null || echo "edge_framework 未找到"

echo ""
echo "6. 检查运行中的进程"
ps aux | grep edge_framework | grep -v grep || echo "未运行"

echo ""
echo "=== 诊断完成 ==="
