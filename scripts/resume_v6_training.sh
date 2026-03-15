#!/bin/bash
# RCMT V6 续训脚本 - 使用追加模式
# 用法: ./scripts/resume_v6_training.sh [checkpoint_path]

CONTAINER="rcmt-training"
LOG_DIR="logs_swin_v6_paper"
CKPT_DIR="checkpoints_swin_v6_paper"

# 检查容器状态
if ! docker ps | grep -q $CONTAINER; then
    echo "❌ 容器 $CONTAINER 未运行"
    exit 1
fi

# 获取最新的checkpoint
if [ -z "$1" ]; then
    LATEST_CKPT=$(docker exec $CONTAINER bash -c "ls -t $CKPT_DIR/*.pth 2>/dev/null | head -1")
    if [ -z "$LATEST_CKPT" ]; then
        echo "❌ 未找到checkpoint"
        exit 1
    fi
else
    LATEST_CKPT="$1"
fi

echo "📁 使用checkpoint: $LATEST_CKPT"
echo "📝 日志将追加到: $LOG_DIR/nohup.log"

# 停止当前训练进程
echo "🛑 停止当前训练..."
docker exec $CONTAINER pkill -f train_rcmt_v6_paper.py
sleep 3

# 等待进程完全停止
docker exec $CONTAINER bash -c "while pgrep -f train_rcmt_v6_paper.py > /dev/null; do sleep 1; done"
echo "✅ 训练进程已停止"

# 添加续训标记到日志
docker exec $CONTAINER bash -c "echo '' >> $LOG_DIR/nohup.log"
docker exec $CONTAINER bash -c "echo '========================================' >> $LOG_DIR/nohup.log"
docker exec $CONTAINER bash -c "echo '续训 - '$(date) >> $LOG_DIR/nohup.log"
docker exec $CONTAINER bash -c "echo 'Checkpoint: $LATEST_CKPT' >> $LOG_DIR/nohup.log"
docker exec $CONTAINER bash -c "echo '========================================' >> $LOG_DIR/nohup.log"
docker exec $CONTAINER bash -c "echo '' >> $LOG_DIR/nohup.log"

# 使用追加模式启动续训
echo "🚀 启动续训..."
docker exec -d $CONTAINER bash -c "cd /workspace/rcmt_v3 && nohup python3 train_rcmt_v6_paper.py \
    --data-root /home/developer/workspace/datasets/LEVIR-CD256 \
    --use-changeformer-format \
    --batch-size 16 \
    --epochs 400 \
    --lr 0.0001 \
    --drop-path 0.3 \
    --depths 2 2 2 2 \
    --num-heads 2 4 8 16 \
    --log-dir $LOG_DIR \
    --checkpoint-dir $CKPT_DIR \
    --resume $LATEST_CKPT \
    >> $LOG_DIR/nohup.log 2>&1 &"

echo "✅ 续训已启动 (日志追加模式)"
