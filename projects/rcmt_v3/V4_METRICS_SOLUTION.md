# V4训练日志指标缺失问题分析与解决方案

**发现时间**: 2026-03-10 11:41
**问题提出**: 算法工程师

---

## 🔍 问题分析

### 当前状态

1. **✅ 代码中有完整的指标计算**
   - 位置: `d:/github/edge_infer/rcmt_v3/utils/metrics.py`
   - 指标: Precision, Recall, F1, IoU, OA, mF1, mIoU
   - 功能: `MetricsCalculator` 类已实现

2. **❌ 训练日志缺少详细指标**
   - 当前日志只记录: `Train Loss` + `F1`
   - 缺少: IoU, Precision, Recall, OA等关键指标
   - 原因: `train()` 方法中只打印了F1

3. **❌ 没有历史记录文件**
   - 缺少JSON格式的训练历史
   - 无法生成论文所需的训练曲线图

### 代码问题位置

**文件**: `d:/github/edge_infer/rcmt_v3/train_rcmt_v4_optimized.py`

**问题代码** (第383-384行):
```python
self._log(f"  Train Loss: {train_loss:.4f} | F1: {train_metrics['f1']:.4f}\n")
self._log(f"  Val Loss: {val_loss:.4f} | F1: {val_metrics['f1']:.4f}\n")
```

**应该记录**:
```python
# 训练集指标
Train Loss, F1, IoU, Precision, Recall, OA

# 验证集指标
Val Loss, F1, IoU, Precision, Recall, OA

# 保存到JSON历史记录
{
  "epoch": 1,
  "train": {"loss": 0.5, "f1": 0.85, "iou": 0.78, ...},
  "val": {"loss": 0.48, "f1": 0.87, "iou": 0.80, ...}
}
```

---

## 💡 解决方案

### 方案1: 修改训练代码 + 续训（推荐）

**优点**:
- ✅ 从现有checkpoint续训，保留已训练的207 epochs
- ✅ 记录完整的训练历史
- ✅ 生成论文所需的图表数据

**步骤**:
1. 修改 `train_rcmt_v4_optimized.py`，添加完整指标记录
2. 从 `latest_checkpoint.pth` 续训
3. 记录剩余epochs的完整指标
4. 生成训练历史JSON文件

**时间**: ~4小时（剩余93 epochs）

---

### 方案2: 评估现有checkpoint（快速）

**优点**:
- ✅ 立即获得当前模型的完整指标
- ✅ 无需续训
- ✅ 快速生成论文数据

**缺点**:
- ❌ 没有完整的训练历史曲线
- ❌ 只有最终指标，没有中间过程

**步骤**:
1. 加载 `best_model.pth` 和 `latest_checkpoint.pth`
2. 在验证集上评估所有指标
3. 生成评估报告
4. 如果需要训练曲线，可以选择方案1续训

**时间**: ~10分钟

---

### 方案3: 从头训练（不推荐）

**优点**:
- ✅ 完整的训练历史
- ✅ 所有指标都有

**缺点**:
- ❌ 需要重新训练300 epochs（~6.7小时）
- ❌ 浪费已训练的207 epochs

**时间**: ~6.7小时

---

## 🎯 推荐方案: 方案1 + 方案2组合

### 阶段1: 立即评估（方案2）
**目的**: 获得当前最佳模型的完整指标，用于论文

**执行**:
```bash
# 创建评估脚本
python scripts/evaluate_checkpoint.py \
    --checkpoint d:/github/edge_infer/rcmt_v3/checkpoints_swin_v4/best_model.pth \
    --data-root /home/developer/workspace/datasets/LEVIR-CD256 \
    --output d:/github/edge_infer_cloud/projects/rcmt_v3/paper_writing/experiments/evaluation_results.json
```

**输出**:
- `evaluation_results.json`: 完整的指标报告
- `confusion_matrix.png`: 混淆矩阵可视化
- `metrics_summary.md`: 指标摘要（用于论文）

---

### 阶段2: 修改代码并续训（方案1）
**目的**: 获得完整的训练历史，生成训练曲线

**步骤1: 修改训练代码**
添加以下功能：
1. 完整指标记录
2. JSON历史文件
3. TensorBoard日志（可选）

**步骤2: 续训**
```bash
# 从epoch 207续训到300
python train_rcmt_v4_optimized.py \
    --resume d:/github/edge_infer/rcmt_v3/checkpoints_swin_v4/latest_checkpoint.pth \
    --epochs 300 \
    --log-interval 1  # 每个epoch记录一次
```

**步骤3: 生成训练曲线**
```bash
python scripts/generate_training_curves.py \
    --history d:/github/edge_infer/rcmt_v3/logs_swin_v4/training_history.json \
    --output d:/github/edge_infer_cloud/projects/rcmt_v3/paper_writing/figures/
```

**输出**:
- `training_history.json`: 完整训练历史
- `f1_curve.png`: F1分数训练曲线
- `iou_curve.png`: IoU训练曲线
- `loss_curve.png`: Loss训练曲线
- `all_metrics.png`: 所有指标对比图

---

## 📊 需要添加的指标

### 论文需要的核心指标

| 指标 | 缩写 | 用途 | SOTA对比必需 |
|------|------|------|-------------|
| F1 Score | F1 | 主要指标 | ✅ |
| IoU | IoU | 空间重叠 | ✅ |
| Precision | Prec | 精确率 | ✅ |
| Recall | Rec | 召回率 | ✅ |
| Overall Accuracy | OA | 整体准确度 | ✅ |
| Mean F1 | mF1 | 平均F1 | ⚠️ 可选 |
| Mean IoU | mIoU | 平均IoU | ⚠️ 可选 |

### 论文需要的图表

1. **训练曲线图** (Figure 3)
   - F1 vs Epoch
   - IoU vs Epoch
   - Loss vs Epoch
   - Learning Rate vs Epoch

2. **消融研究表** (Table 3)
   - 各优化策略的F1/IoU对比

3. **SOTA对比表** (Table 2)
   - RCMT-V3 vs BIT vs ChangeFormer
   - 指标: F1, IoU, Params, FPS

4. **可视化结果图** (Figure 4-6)
   - 定性对比图
   - 混淆矩阵
   - PR曲线（可选）

---

## 🛠️ 具体实施方案

### 步骤1: 创建评估脚本（10分钟）

```python
# scripts/evaluate_checkpoint.py
import torch
import json
from models.model import build_rcmt_v3_hybrid
from datasets.dataset import create_dataloaders
from utils.metrics import MetricsCalculator

def evaluate_checkpoint(checkpoint_path, data_root, output_path):
    # 加载模型
    model = build_rcmt_v3_hybrid(drop_path=0.3)
    checkpoint = torch.load(checkpoint_path)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    # 数据
    _, val_loader = create_dataloaders(data_root, batch_size=16)
    
    # 评估
    metrics_calc = MetricsCalculator()
    
    with torch.no_grad():
        for batch in val_loader:
            img1, img2, labels = batch['img1'], batch['img2'], batch['label']
            outputs = model(img1, img2)
            metrics_calc.update(outputs, labels)
    
    metrics = metrics_calc.compute()
    
    # 保存结果
    results = {
        'checkpoint': checkpoint_path,
        'epoch': checkpoint['epoch'],
        'best_f1': checkpoint['best_f1'],
        'metrics': metrics
    }
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    return metrics

if __name__ == "__main__":
    metrics = evaluate_checkpoint(
        "d:/github/edge_infer/rcmt_v3/checkpoints_swin_v4/best_model.pth",
        "/home/developer/workspace/datasets/LEVIR-CD256",
        "evaluation_results.json"
    )
    print(f"F1: {metrics['f1']:.4f}")
    print(f"IoU: {metrics['iou']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"OA: {metrics['oa']:.4f}")
```

---

### 步骤2: 修改训练代码（30分钟）

**修改文件**: `train_rcmt_v4_optimized.py`

**修改1: 添加训练历史记录**
```python
class V4Trainer:
    def __init__(self, config: V4Config):
        # ... 现有代码 ...
        
        # 添加：训练历史
        self.training_history = {
            'train': [],
            'val': [],
            'config': vars(config)
        }
    
    def record_epoch(self, epoch, train_loss, train_metrics, val_loss, val_metrics):
        """记录每个epoch的完整指标"""
        epoch_data = {
            'epoch': epoch,
            'train': {
                'loss': train_loss,
                **train_metrics  # f1, iou, precision, recall, oa
            },
            'val': {
                'loss': val_loss,
                **val_metrics
            }
        }
        
        self.training_history['train'].append(epoch_data['train'])
        self.training_history['val'].append(epoch_data['val'])
        
        # 保存历史
        history_path = f"{self.config.log_dir}/training_history.json"
        with open(history_path, 'w') as f:
            json.dump(self.training_history, f, indent=2)
```

**修改2: 增强日志输出**
```python
def train(self):
    # ... 现有代码 ...
    
    for epoch in range(self.start_epoch, self.config.epochs):
        train_loss, train_metrics = self.train_epoch(epoch)
        val_loss, val_metrics = self.validate(epoch)
        
        # 记录完整指标
        self.record_epoch(epoch, train_loss, train_metrics, val_loss, val_metrics)
        
        # 增强日志
        self._log(f"\n{'='*80}\n")
        self._log(f"Epoch {epoch+1}/{self.config.epochs} Summary:\n")
        self._log(f"  Train:\n")
        self._log(f"    Loss: {train_loss:.4f}\n")
        self._log(f"    F1: {train_metrics['f1']:.4f}\n")
        self._log(f"    IoU: {train_metrics['iou']:.4f}\n")
        self._log(f"    Precision: {train_metrics['precision']:.4f}\n")
        self._log(f"    Recall: {train_metrics['recall']:.4f}\n")
        self._log(f"    OA: {train_metrics['oa']:.4f}\n")
        self._log(f"  Val:\n")
        self._log(f"    Loss: {val_loss:.4f}\n")
        self._log(f"    F1: {val_metrics['f1']:.4f}\n")
        self._log(f"    IoU: {val_metrics['iou']:.4f}\n")
        self._log(f"    Precision: {val_metrics['precision']:.4f}\n")
        self._log(f"    Recall: {val_metrics['recall']:.4f}\n")
        self._log(f"    OA: {val_metrics['oa']:.4f}\n")
```

---

### 步骤3: 生成训练曲线脚本（20分钟）

```python
# scripts/generate_training_curves.py
import json
import matplotlib.pyplot as plt
import numpy as np

def plot_training_curves(history_path, output_dir):
    # 加载历史
    with open(history_path) as f:
        history = json.load(f)
    
    epochs = range(1, len(history['train']) + 1)
    
    # F1曲线
    plt.figure(figsize=(10, 6))
    plt.plot(epochs, [e['f1'] for e in history['train']], label='Train F1')
    plt.plot(epochs, [e['f1'] for e in history['val']], label='Val F1')
    plt.xlabel('Epoch')
    plt.ylabel('F1 Score')
    plt.title('F1 Score Training Curve')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'{output_dir}/f1_curve.png', dpi=300)
    
    # IoU曲线
    plt.figure(figsize=(10, 6))
    plt.plot(epochs, [e['iou'] for e in history['train']], label='Train IoU')
    plt.plot(epochs, [e['iou'] for e in history['val']], label='Val IoU')
    plt.xlabel('Epoch')
    plt.ylabel('IoU')
    plt.title('IoU Training Curve')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'{output_dir}/iou_curve.png', dpi=300)
    
    # Loss曲线
    plt.figure(figsize=(10, 6))
    plt.plot(epochs, [e['loss'] for e in history['train']], label='Train Loss')
    plt.plot(epochs, [e['loss'] for e in history['val']], label='Val Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Loss Training Curve')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'{output_dir}/loss_curve.png', dpi=300)
    
    # 所有指标对比
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    metrics = ['f1', 'iou', 'precision', 'recall', 'oa', 'loss']
    
    for idx, metric in enumerate(metrics):
        ax = axes[idx // 3, idx % 3]
        ax.plot(epochs, [e[metric] for e in history['train']], label='Train')
        ax.plot(epochs, [e[metric] for e in history['val']], label='Val')
        ax.set_xlabel('Epoch')
        ax.set_ylabel(metric.upper())
        ax.set_title(f'{metric.upper()} Training Curve')
        ax.legend()
        ax.grid(True)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/all_metrics.png', dpi=300)
    
    print(f"训练曲线已保存到: {output_dir}")

if __name__ == "__main__":
    plot_training_curves(
        "d:/github/edge_infer/rcmt_v3/logs_swin_v4/training_history.json",
        "d:/github/edge_infer_cloud/projects/rcmt_v3/paper_writing/figures/"
    )
```

---

## 📋 执行计划

### 立即执行（今天）

1. **创建评估脚本** (10分钟)
   - 文件: `scripts/evaluate_checkpoint.py`
   - 功能: 评估best_model.pth的完整指标

2. **评估当前模型** (5分钟)
   ```bash
   python scripts/evaluate_checkpoint.py
   ```
   - 输出: `evaluation_results.json`

3. **生成评估报告** (5分钟)
   - 更新论文表格数据
   - 确认当前F1=0.9196的IoU等指标

### 后续执行（明天）

4. **修改训练代码** (30分钟)
   - 添加完整指标记录
   - 添加JSON历史文件

5. **续训V4** (4小时)
   ```bash
   python train_rcmt_v4_optimized.py --resume latest_checkpoint.pth
   ```
   - 从epoch 207续训到300
   - 记录完整指标

6. **生成训练曲线** (10分钟)
   ```bash
   python scripts/generate_training_curves.py
   ```
   - 输出: 论文所需的图表

---

## 📊 预期输出

### 立即可得（方案2）

```json
// evaluation_results.json
{
  "checkpoint": "best_model.pth",
  "epoch": 207,
  "metrics": {
    "f1": 0.9196,
    "iou": 0.8508,  // 估算
    "precision": 0.9234,  // 估算
    "recall": 0.9158,  // 估算
    "oa": 0.9912  // 估算
  }
}
```

### 续训后可得（方案1）

```
logs_swin_v4/
├── train.log                      # 完整训练日志
├── training_history.json          # JSON格式历史
├── best_model.pth                 # 最佳模型
└── latest_checkpoint.pth          # 最新checkpoint

paper_writing/figures/
├── f1_curve.png                   # F1曲线
├── iou_curve.png                  # IoU曲线
├── loss_curve.png                 # Loss曲线
├── all_metrics.png                # 所有指标
└── confusion_matrix.png           # 混淆矩阵

paper_writing/experiments/
├── evaluation_results.json        # 评估结果
├── training_history.json          # 训练历史
└── metrics_summary.md             # 指标摘要
```

---

## ✅ 建议行动

**我的建议**: 方案1 + 方案2组合

1. **立即执行方案2**（15分钟）
   - 获得当前模型的完整指标
   - 确认IoU、Precision、Recall等指标
   - 更新论文表格

2. **随后执行方案1**（4.5小时）
   - 修改代码（30分钟）
   - 续训到300 epochs（4小时）
   - 生成训练曲线（10分钟）

**理由**:
- ✅ 方案2立即可得论文所需的核心指标
- ✅ 方案1补充完整的训练历史和曲线
- ✅ 不浪费已训练的207 epochs
- ✅ 论文数据完整且有说服力

---

**分析完成时间**: 2026-03-10 11:41
**优先级**: P0（论文必需）
**预计总时间**: 15分钟（方案2）+ 4.5小时（方案1）= 4.75小时
