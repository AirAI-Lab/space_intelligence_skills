# BTFormer完整训练命令（可复现）

**生成时间**: 2026-03-14 20:15 UTC+8  
**训练状态**: Epoch 288/400 (Best F1: 92.22%)

---

## 🚀 快速开始

### 1. Docker环境准备

```bash
# 启动训练容器
docker run -d \
  --name rcmt-training \
  --gpus all \
  -v D:/github/edge_infer:/workspace \
  -v D:/datasets:/datasets \
  rcmt-training-backup:20260216_124600

# 进入容器
docker exec -it rcmt-training bash
```

### 2. 开始训练

```bash
cd /workspace/rcmt_v3
python train_rcmt_v4_paper.py
```

### 3. 断点续训

```bash
python train_rcmt_v4_paper.py \
  --resume checkpoints_swin_v4_paper/latest_checkpoint.pth
```

---

## 📝 完整配置详情

### 模型配置

| 配置项 | 值 |
|--------|-----|
| 架构 | RCMT-V3-Hybrid (混合CNN-Transformer) |
| 参数量 | 11,772,452 (11.8M) |
| 输入分辨率 | 256×256 |
| Encoder | CNN (Stage 1-2) + Transformer (Stage 3-4) |
| BTF Module | Bidirectional Temporal Fusion |
| Decoder | Multi-Scale Decoder |

### 训练超参数

| 配置项 | 值 | 说明 |
|--------|-----|------|
| Epochs | 400 | 强正则化需要充分收敛 |
| Batch Size | 16 | RTX 4060 Ti (16GB) 最优 |
| Learning Rate | 1e-4 (初始) | 标准微调学习率 |
| Weight Decay | 0.05 | 强正则化 |
| Warmup Epochs | 10 | 稳定启动 |
| DropPath | 0.3 | Transformer正则化 |
| Optimizer | AdamW (β₁=0.9, β₂=0.999) | 稳定梯度更新 |

### 损失函数

```python
CombinedLoss:
  BCE Loss:
    weight: 1.0
    pos_weight: 3.0  # 处理类别不平衡
    
  Dice Loss:
    weight: 0.3
    smooth: 1.0
    
  Focal Loss:
    weight: 0.1
    alpha: 0.25
    gamma: 2.0
    
  Label Smoothing:
    epsilon: 0.05
```

### 数据增强

```python
MixUp:
  probability: 0.5
  alpha: 0.4
  
CutMix:
  probability: 0.3
  alpha: 1.0
  
基础增强:
  Random Horizontal Flip: 0.5
  Random Vertical Flip: 0.5
```

### 学习率调度

```
Scheduler: Cosine Annealing with Warmup

Phase 1: Warmup (Epoch 0-9)
  LR: 1e-6 → 1e-4 (linear)

Phase 2: Cosine Annealing (Epoch 10-399)
  LR: 1e-4 → 1e-6 (cosine decay)
```

---

## 📂 数据集配置

### LEVIR-CD数据集

| 数据集 | 路径 | 样本数 |
|--------|------|--------|
| Train | `/home/developer/workspace/datasets/LEVIR-CD256/train` | 10,192 pairs |
| Val | `/home/developer/workspace/datasets/LEVIR-CD256/val` | 10,192 pairs |
| Test | `/home/developer/workspace/datasets/LEVIR-CD256/test` | 2,048 pairs |

**数据集特性**:
- 分辨率: 256×256
- 空间分辨率: 0.5m/pixel
- 变化区域占比: ~15%

---

## 📁 输出目录结构

```
D:\github\edge_infer\rcmt_v3\
├── train_rcmt_v4_paper.py         # 训练脚本
├── logs_swin_v4_paper/
│   └── training_history.json      # 完整训练历史（JSON格式）
├── checkpoints_swin_v4_paper/
│   ├── best_model.pth             # 最佳模型（按Val F1）
│   └── latest_checkpoint.pth      # 最新检查点（用于续训）
└── models/
    └── model.py                   # 模型定义（build_rcmt_v3_hybrid）
```

---

## 🎯 训练目标与结果

### 目标指标
- **Val F1**: > 92.0% ✅ (当前: 92.22%)
- **Val IoU**: > 85.0% ✅ (当前: 85.56%)
- **Val Recall**: > 96.0% ✅ (当前: 96.86%)
- **参数效率**: < 15M ✅ (当前: 11.8M)

### 当前最佳结果 (Epoch 288)

```
Val F1:        0.922184 (92.22%)
Val IoU:       0.855605 (85.56%)
Val Precision: 0.879974 (88.00%)
Val Recall:    0.968648 (96.86%)
Val OA:        0.992397 (99.24%)
```

---

## 🔧 训练脚本关键代码

### 损失函数定义

```python
class CombinedLoss(nn.Module):
    def __init__(self, bce_weight=1.0, dice_weight=0.3, focal_weight=0.1, 
                 pos_weight=3.0, label_smoothing=0.05):
        super().__init__()
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight
        self.focal_weight = focal_weight
        self.pos_weight = torch.tensor([pos_weight])
        self.label_smoothing = label_smoothing
        
        self.dice_loss = DiceLoss()
        self.focal_loss = FocalLoss()
    
    def forward(self, pred, target):
        if self.label_smoothing > 0:
            target = target * (1 - self.label_smoothing) + 0.5 * self.label_smoothing
        
        bce = nn.functional.binary_cross_entropy_with_logits(
            pred, target, 
            pos_weight=self.pos_weight.to(pred.device)
        )
        dice = self.dice_loss(pred, target)
        focal = self.focal_loss(pred, target)
        
        return (self.bce_weight * bce + 
                self.dice_weight * dice + 
                self.focal_weight * focal)
```

### 数据增强实现

```python
def mixup_data(x1, x2, y, alpha=0.4):
    lam = np.random.beta(alpha, alpha)
    batch_size = x1.size(0)
    index = torch.randperm(batch_size)
    
    mixed_x1 = lam * x1 + (1 - lam) * x1[index]
    mixed_x2 = lam * x2 + (1 - lam) * x2[index]
    mixed_y = lam * y + (1 - lam) * y[index]
    
    return mixed_x1, mixed_x2, mixed_y

def cutmix_data(x1, x2, y, alpha=1.0):
    lam = np.random.beta(alpha, alpha)
    batch_size = x1.size(0)
    index = torch.randperm(batch_size)
    
    # Generate random box
    W, H = x1.size(2), x1.size(3)
    cut_rat = np.sqrt(1. - lam)
    cut_w = int(W * cut_rat)
    cut_h = int(H * cut_rat)
    
    cx = np.random.randint(W)
    cy = np.random.randint(H)
    
    bbx1 = np.clip(cx - cut_w // 2, 0, W)
    bby1 = np.clip(cy - cut_h // 2, 0, H)
    bbx2 = np.clip(cx + cut_w // 2, 0, W)
    bby2 = np.clip(cy + cut_h // 2, 0, H)
    
    # Apply CutMix
    x1[:, :, bbx1:bbx2, bby1:bby2] = x1[index, :, bbx1:bbx2, bby1:bby2]
    x2[:, :, bbx1:bbx2, bby1:bby2] = x2[index, :, bbx1:bbx2, bby1:bby2]
    
    lam = 1 - ((bbx2 - bbx1) * (bby2 - bby1) / (W * H))
    y = lam * y + (1 - lam) * y[index]
    
    return x1, x2, y
```

---

## 📊 训练监控

### 查看实时日志

```bash
# 进入容器
docker exec -it rcmt-training bash

# 实时查看训练日志
tail -f /workspace/rcmt_v3/logs_swin_v4_paper/training_history.json

# 查看GPU使用情况
watch -n 1 nvidia-smi
```

### 查看训练历史

```bash
# 查看最佳结果
cat /workspace/rcmt_v3/logs_swin_v4_paper/training_history.json | \
  jq '.best_result'
```

---

## ⚠️ 注意事项

1. **GPU内存**: 确保GPU内存 ≥ 16GB (Batch Size 16)
2. **训练时长**: 400 epochs ≈ 14小时 (RTX 4060 Ti)
3. **检查点**: 每50个epoch自动保存检查点
4. **中断恢复**: 支持从任意检查点恢复训练
5. **Volume映射**: 数据集和代码通过Volume映射（零延迟）

---

## 🔗 相关文件

- 训练脚本: `D:\github\edge_infer\rcmt_v3\train_rcmt_v4_paper.py`
- 模型定义: `D:\github\edge_infer\rcmt_v3\models\model.py`
- 训练历史: `D:\github\edge_infer\rcmt_v3\logs_swin_v4_paper\training_history.json`
- 最佳模型: `D:\github\edge_infer\rcmt_v3\checkpoints_swin_v4_paper\best_model.pth`

---

**最后更新**: 2026-03-14 20:15 UTC+8  
**训练进度**: Epoch 288/400 (72.0%)  
**最佳F1**: 92.22% ✅
