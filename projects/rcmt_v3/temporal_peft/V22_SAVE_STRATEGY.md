# v2.2保存策略改进 - 参考V6

## 改进时间
2026-03-16 22:26 UTC+8

## 参考模型
V6 (Swin-Temporal)

## 关键改进

### 1. 模型保存策略
```python
# v2.1（旧） - 每10轮保存
if epoch % 10 == 0:
    torch.save(checkpoint, f'checkpoint_epoch_{epoch}.pth')

# v2.2（新） - 只保存best和latest
if is_best:
    torch.save(checkpoint, 'best_model.pth')  # 最佳模型
torch.save(checkpoint, 'checkpoint_latest.pth')  # 最新checkpoint
```

**节省空间**: ~15GB → ~1.5GB（仅保留2个模型文件）

### 2. 训练历史保存（用于论文画图）

#### TrainingHistory类
```python
class TrainingHistory:
    """完整的训练历史记录器"""
    
    def __init__(self, save_dir: str):
        self.history = {
            'train': [],      # 每个epoch的训练指标
            'val': [],        # 每个epoch的验证指标
            'lr': [],         # 学习率变化
            'best_info': {},  # 最佳模型信息
            'config': {},     # 训练配置
            'start_time': '', # 开始时间
            'end_time': ''    # 结束时间
        }
```

#### 保存的指标
每个epoch保存：
```json
{
  "train": [
    {
      "epoch": 1,
      "loss": 0.6856,
      "f1": 0.0839,
      "iou": 0.0437,
      "precision": 0.0421,
      "recall": 0.2248,
      "oa": 0.1234
    }
  ],
  "val": [
    {
      "epoch": 1,
      "loss": 0.6234,
      "f1": 0.1234,
      "iou": 0.0656,
      "precision": 0.0823,
      "recall": 0.2345,
      "oa": 0.1567
    }
  ],
  "lr": [
    {
      "epoch": 1,
      "lr": 0.0001
    }
  ],
  "best_info": {
    "epoch": 150,
    "val_f1": 0.9012,
    "val_iou": 0.8201,
    "timestamp": "2026-03-17 15:30:00"
  }
}
```

### 3. 论文画图示例

#### F1曲线
```python
import json
import matplotlib.pyplot as plt

# 加载训练历史
with open('training_history.json', 'r') as f:
    history = json.load(f)

# 提取数据
epochs = [h['epoch'] for h in history['train']]
train_f1 = [h['f1'] for h in history['train']]
val_f1 = [h['f1'] for h in history['val']]

# 画图
plt.figure(figsize=(10, 6))
plt.plot(epochs, train_f1, label='Train F1', linewidth=2)
plt.plot(epochs, val_f1, label='Val F1', linewidth=2)
plt.xlabel('Epoch', fontsize=14)
plt.ylabel('F1 Score', fontsize=14)
plt.title('Temporal PEFT v2.2 Training Curve', fontsize=16)
plt.legend(fontsize=12)
plt.grid(True, alpha=0.3)
plt.savefig('f1_curve.pdf', dpi=300, bbox_inches='tight')
plt.show()
```

#### Loss曲线
```python
train_loss = [h['loss'] for h in history['train']]
val_loss = [h['loss'] for h in history['val']]

plt.figure(figsize=(10, 6))
plt.plot(epochs, train_loss, label='Train Loss', linewidth=2)
plt.plot(epochs, val_loss, label='Val Loss', linewidth=2)
plt.xlabel('Epoch', fontsize=14)
plt.ylabel('Loss', fontsize=14)
plt.title('Temporal PEFT v2.2 Loss Curve', fontsize=16)
plt.legend(fontsize=12)
plt.grid(True, alpha=0.3)
plt.savefig('loss_curve.pdf', dpi=300, bbox_inches='tight')
```

#### 学习率曲线
```python
lr_values = [h['lr'] for h in history['lr']]

plt.figure(figsize=(10, 6))
plt.plot(epochs, lr_values, linewidth=2, color='orange')
plt.xlabel('Epoch', fontsize=14)
plt.ylabel('Learning Rate', fontsize=14)
plt.title('Learning Rate Schedule (Cosine Annealing)', fontsize=16)
plt.grid(True, alpha=0.3)
plt.savefig('lr_curve.pdf', dpi=300, bbox_inches='tight')
```

### 4. 与V6对比

| 项目 | V6 | v2.2 |
|------|----|----|
| **模型保存** | best + latest | best + latest ✅ |
| **训练历史** | JSON格式 | JSON格式 ✅ |
| **保存频率** | 每个epoch | 每个epoch ✅ |
| **包含指标** | F1, IoU, Loss | F1, IoU, Loss, Precision, Recall, OA ✅ |
| **额外信息** | 时间戳 | 时间戳 + 配置 ✅ |

### 5. 文件对比

#### v2.1输出（旧）
```
/tmp/temporal_peft_v2_200ep/
├── best_model.pth (674MB)
├── checkpoint_latest.pth (674MB)
├── checkpoint_epoch_10.pth (674MB)  ← 冗余
├── checkpoint_epoch_20.pth (674MB)  ← 冗余
├── checkpoint_epoch_30.pth (674MB)  ← 冗余
├── ...
└── logs/
    └── events.out.tfevents...

总计: ~15GB
```

#### v2.2输出（新）
```
/tmp/temporal_peft_v2_200ep/
├── best_model.pth (674MB)
├── checkpoint_latest.pth (674MB)
├── training_history.json (50KB)  ← 新增！用于画图
└── logs/
    └── events.out.tfevents...

总计: ~1.5GB
```

**节省空间**: 90% ↓

### 6. training_history.json示例

```json
{
  "train": [
    {"epoch": 1, "loss": 0.6856, "f1": 0.0839, ...},
    {"epoch": 2, "loss": 0.6234, "f1": 0.1234, ...},
    ...
  ],
  "val": [
    {"epoch": 1, "loss": 0.6543, "f1": 0.0921, ...},
    {"epoch": 2, "loss": 0.6012, "f1": 0.1423, ...},
    ...
  ],
  "lr": [
    {"epoch": 1, "lr": 0.0001},
    {"epoch": 2, "lr": 0.000099},
    ...
  ],
  "best_info": {
    "epoch": 150,
    "val_f1": 0.9012,
    "val_iou": 0.8201,
    "val_precision": 0.9123,
    "val_recall": 0.8901,
    "val_loss": 0.2134,
    "timestamp": "2026-03-17 15:30:00"
  },
  "config": {
    "epochs": 200,
    "batch_size": 16,
    "learning_rate": 0.0001,
    "weight_decay": 0.05,
    "early_stopping_patience": 30
  },
  "start_time": "2026-03-16 22:30:00",
  "end_time": "2026-03-17 16:30:00",
  "total_epochs": 200,
  "early_stop_epoch": 0
}
```

### 7. 优势总结

| 改进点 | v2.1 | v2.2 |
|--------|------|------|
| **磁盘空间** | ~15GB | ~1.5GB ✅ |
| **训练历史** | TensorBoard only | JSON + TensorBoard ✅ |
| **论文画图** | 需要解析TensorBoard | 直接用JSON ✅ |
| **可读性** | 二进制 | JSON（可读）✅ |
| **续训支持** | ✅ | ✅ |
| **配置记录** | 部分 | 完整 ✅ |

---

**创建者**: OpenClaw Innovation Team  
**创建时间**: 2026-03-16 22:26  
**状态**: ✅ v2.2已启动
