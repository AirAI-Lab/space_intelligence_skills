#!/bin/bash
# SAM3对比评估 - 容器执行脚本
# 作者: 空中智能体团队
# 日期: 2026-04-06

echo "=========================================="
echo "RADIO + SAM3 对比评估"
echo "=========================================="

# 设置工作目录
cd /app/water_inspection

# 检查评估脚本是否存在
if [ ! -f "evaluate_sam3_comparison.py" ]; then
    echo "❌ 评估脚本不存在"
    exit 1
fi

echo "✅ 评估脚本已就绪"
echo ""

# 运行评估
echo "开始评估..."
python evaluate_sam3_comparison.py

# 检查结果
if [ -f "outputs/sam3_comparison_results.json" ]; then
    echo ""
    echo "✅ 评估完成!"
    echo ""
    echo "结果摘要:"
    cat outputs/sam3_comparison_results.json
else
    echo "❌ 评估失败,未生成结果文件"
fi
