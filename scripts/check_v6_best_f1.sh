#!/bin/bash
# V6 新Best F1检测脚本
# 用途：检测是否有新的Best F1记录，如果有则发送通知

STATE_FILE="d:/github/edge_infer_cloud/memory/v6_best_f1_state.json"
CHECKPOINT_DIR="/workspace/rcmt_v3/checkpoints_swin_v6_paper/"
LOG_FILE="/workspace/rcmt_v3/logs_swin_v6_paper/nohup.log"
BEST_MODEL="${CHECKPOINT_DIR}best_model.pth"

# 获取best_model的修改时间（Unix时间戳）
CURRENT_MTIME=$(docker exec rcmt-training stat -c '%Y' "$BEST_MODEL" 2>/dev/null)

if [ -z "$CURRENT_MTIME" ]; then
    echo "⚠️ Cannot get best_model modification time"
    exit 1
fi

# 从状态文件读取上次的修改时间
if [ -f "$STATE_FILE" ]; then
    LAST_MTIME=$(cat "$STATE_FILE" | grep -oP '"last_model_mtime_unix":\s*\K[0-9]+' || echo "0")
else
    LAST_MTIME=0
fi

# 比较修改时间
if [ "$CURRENT_MTIME" -gt "$LAST_MTIME" ]; then
    echo "🎉 New best model detected!"

    # 从日志提取最新的Best F1
    NEW_BEST_F1=$(docker exec rcmt-training tail -200 "$LOG_FILE" | grep -oP 'New Best Model! F1: \K[0-9.]+' | tail -1)
    NEW_EPOCH=$(docker exec rcmt-training tail -200 "$LOG_FILE" | grep -B10 "New Best Model" | grep -oP 'Epoch \[\K[0-9]+' | tail -1)

    if [ -n "$NEW_BEST_F1" ] && [ -n "$NEW_EPOCH" ]; then
        echo "New Best F1: $NEW_BEST_F1 (Epoch $NEW_EPOCH)"

        # 更新状态文件
        cat > "$STATE_FILE" << EOF
{
  "task": "v6_best_f1_monitor",
  "last_best_f1": $NEW_BEST_F1,
  "last_epoch": $NEW_EPOCH,
  "last_model_mtime_unix": $CURRENT_MTIME,
  "last_check": "$(date -Iseconds)",
  "checkpoint_dir": "$CHECKPOINT_DIR",
  "log_file": "$LOG_FILE",
  "notification": "NEW_BEST_F1"
}
EOF

        # 输出标记（供heartbeat检测）
        echo "::NEW_BEST_F1::$NEW_BEST_F1::$NEW_EPOCH::"
        exit 0
    else
        echo "⚠️ Cannot extract new Best F1 from log"
        exit 1
    fi
else
    echo "✅ No new best model (last checked: $(date -d "@$LAST_MTIME" '+%Y-%m-%d %H:%M:%S'))"

    # 更新检查时间
    if [ -f "$STATE_FILE" ]; then
        sed -i "s/\"last_check\": \"[^\"]*\"/\"last_check\": \"$(date -Iseconds)\"/" "$STATE_FILE"
    fi

    exit 0
fi
