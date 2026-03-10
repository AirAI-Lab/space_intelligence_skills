# RCMT-Swin 新训练启动命令

## ✅ 训练命令（简化版，无脚本）

```bash
docker exec -d aaf2c9c5d4f5 bash -c "cd /home/developer/workspace/rcmt_v3 && nohup python3 -u train_rcmt_swin.py --data-root /home/developer/workspace/datasets/LEVIR-CD256 --batch-size 16 --epochs 300 --lr 1e-4 --warmup-epochs 10 --bce-weight 1.0 --dice-weight 0.3 --focal-weight 0.1 --label-smoothing 0.05 --mixup-prob 0.5 --cutmix-prob 0.3 --drop-path 0.3 --log-dir /home/developer/workspace/rcmt_v3/logs_swin_new --checkpoint-dir /home/developer/workspace/rcmt_v3/checkpoints_swin_new --device cuda > /home/developer/workspace/rcmt_v3/logs_swin_new/train.log 2>&1 &"
```

## 📊 监控命令

### 查看训练进程
```bash
docker exec aaf2c9c5d4f5 bash -c "ps aux | grep python3 | grep train_rcmt_swin | grep -v grep"
```

### 查看训练日志
```bash
docker exec aaf2c9c5d4f5 bash -c "cd /home/developer/workspace/rcmt_v3 && tail -f logs_swin_new/train.log"
```

### 查看GPU使用
```bash
docker exec aaf2c9c5d4f5 nvidia-smi
```

### 查看checkpoint
```bash
docker exec aaf2c9c5d4f5 bash -c "cd /home/developer/workspace/rcmt_v3 && ls -lh checkpoints_swin_new/rcmt_swin_*/"
```

### 查看训练历史
```bash
docker exec aaf2c9c5d4f5 bash -c "cd /home/developer/workspace/rcmt_v3 && cat logs_swin_new/rcmt_swin_*/training_history.json | python3 -m json.tool | tail -n 50"
```

## 🛑 停止训练

```bash
docker exec aaf2c9c5d4f5 bash -c "pkill -f train_rcmt_swin"
```

## ⚙️ 训练配置

- **自适应pos_weight**: 5.0（自动计算）
- **Batch size**: 16
- **Epochs**: 300
- **学习率**: 1e-4
- **Warmup**: 10 epochs
- **优化策略**:
  - 损失: BCE(1.0) + Dice(0.3) + Focal(0.1)
  - 增强: MixUp(0.5) + CutMix(0.3)
  - 正则化: DropPath(0.3) + Label Smoothing(0.05)

## 📁 文件位置

- **日志**: `/home/developer/workspace/rcmt_v3/logs_swin_new/`
- **Checkpoint**: `/home/developer/workspace/rcmt_v3/checkpoints_swin_new/`
- **训练历史**: `training_history.json`（在每个rcmt_swin_*子目录中）

---

**创建时间**: 2026-03-10 14:48
**容器ID**: aaf2c9c5d4f5
