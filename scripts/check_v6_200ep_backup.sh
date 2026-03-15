#!/bin/bash
# V6 200 Epoch 自动备份检测脚本
# 用途：当V6训练到达200 epoch时，自动备份best_model.pth为best_model_200ep.pth

CHECKPOINT_DIR="/workspace/rcmt_v3/checkpoints_swin_v6_paper/"
LOG_FILE="/workspace/rcmt_v3/logs_swin_v6_paper/nohup.log"
MARKER_FILE="${CHECKPOINT_DIR}.backup_200ep_done"
BACKUP_FILE="${CHECKPOINT_DIR}best_model_200ep.pth"
SOURCE_FILE="${CHECKPOINT_DIR}best_model.pth"

# 检查是否已备份
if [ -f "$MARKER_FILE" ]; then
    echo "✅ 200 epoch backup already done (marker exists)"
    exit 0
fi

# 获取当前epoch（从日志最新行提取）
CURRENT_EPOCH=$(tail -100 "$LOG_FILE" | grep -oP 'Epoch \[\K[0-9]+' | tail -1)

if [ -z "$CURRENT_EPOCH" ]; then
    echo "⚠️ Cannot determine current epoch"
    exit 1
fi

echo "Current epoch: $CURRENT_EPOCH / 400"

# 检查是否到达200 epoch
if [ "$CURRENT_EPOCH" -ge 200 ]; then
    echo "🎉 Epoch $CURRENT_EPOCH >= 200, starting backup..."

    # 执行备份
    if cp "$SOURCE_FILE" "$BACKUP_FILE"; then
        echo "✅ Backup created: $BACKUP_FILE"

        # 创建标记文件
        touch "$MARKER_FILE"
        echo "✅ Marker created: $MARKER_FILE"

        # 记录备份时间
        echo "Backup completed at $(date '+%Y-%m-%d %H:%M:%S %Z')" > "$MARKER_FILE"

        echo "🎉 200 epoch backup task completed!"
    else
        echo "❌ Backup failed!"
        exit 1
    fi
else
    REMAINING=$((200 - CURRENT_EPOCH))
    echo "⏳ Not yet 200 epoch ($REMAINING epochs remaining)"
fi
