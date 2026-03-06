# 算法开发指南

> **负责模块**: RCMT变化检测、模型训练、算法优化
> **代码仓库**: `edge_infer/models/rcmt`, `edge_infer_cloud/models`, `rcmt_v3`

---

## 1. RCMT框架

### 1.1 算法概述

**RCMT (Recurrent Cross-Memory Transformer for Spatio-Temporal Change Detection)**

核心创新：
- **时序记忆机制** (Temporal Memory): 跨越时间的长期记忆
- **空间记忆机制** (Spatial Memory): 跨越空间的空间记忆
- **交叉记忆机制** (Cross-Memory): 时序和空间的交叉融合
- **循环注意力机制** (Recurrent Attention): 循环迭代，持续优化

### 1.2 性能指标

| 数据集 | mIoU | F1 | 对比SOTA |
|--------|------|-----|----------|
| LEVIR-CD | 78.1% | 0.8924 | +2.9% |
| SYSU-CD | - | - | - |

**训练状态 (2026-03-06)**:
```
Swin V2 训练:
- 进度: Epoch 130/300
- 最佳F1: 0.8924 (Epoch 113)
- 当前F1: ~0.88
- 目标: F1 > 0.92
```

### 1.3 代码结构

```
edge_infer/models/rcmt/
├── net/              # 网络定义
│   ├── rcmt.py       # RCMT主网络
│   ├── swin.py       # Swin Transformer
│   └── modules/      # 各模块
├── configs/          # 配置文件
├── train/            # 训练脚本
├── dataset/          # 数据集加载
├── losses/           # 损失函数
└── utils/            # 工具函数

rcmt_v3/              # V3版本 (独立目录)
├── models/           # 模型定义
├── datasets/         # 数据集
├── losses/           # 损失函数
├── scripts/          # 训练脚本
├── configs/          # 配置
└── checkpoints_*/    # 检查点
```

---

## 2. 训练流程

### 2.1 数据集准备

```bash
# 数据集结构
datasets/LEVIR-MCD/
├── train/
│   ├── A/           # 时相1图像
│   ├── B/           # 时相2图像
│   └── label/       # 变化标签
├── val/
└── test/
```

### 2.2 训练命令

```bash
cd D:\github\edge_infer\rcmt_v3

# 训练 Swin V2
python train_swin_final_v2.py \
    --config configs/swin_final_v2.yaml \
    --epochs 300 \
    --batch_size 16 \
    --lr 0.0001
```

### 2.3 配置文件

```yaml
# configs/swin_final_v2.yaml
model:
  type: "swin_temporal"
  pretrained: "swin_base_patch4_window7_224.pth"

training:
  epochs: 300
  batch_size: 16
  lr: 0.0001
  scheduler: "cosine_warmup"
  
optimizer:
  type: "AdamW"
  weight_decay: 0.05

data:
  train_dir: "datasets/LEVIR-MCD/train"
  val_dir: "datasets/LEVIR-MCD/val"
  img_size: 256
```

---

## 3. 模型部署

### 3.1 模型转换流程

```
训练 (.pth) → 导出ONNX → TensorRT优化 → 边缘部署
```

### 3.2 转换脚本

```bash
# 1. 导出ONNX
python export_onnx.py \
    --weights checkpoints/best_model.pth \
    --output models/rcmt.onnx

# 2. TensorRT优化
trtexec --onnx=models/rcmt.onnx \
        --saveEngine=models/rcmt.engine \
        --fp16

# 3. 部署到边缘
cp models/rcmt.engine edge_infer/models/rcmt/
```

---

## 4. 算法开发任务

### 4.1 高优先级

- [ ] 完成Swin V2训练 (F1 > 0.92)
- [ ] 模型量化 (FP16/INT8)
- [ ] TensorRT推理优化
- [ ] 边缘部署测试

### 4.2 中优先级

- [ ] 论文撰写 (CVPR/ICCV)
- [ ] 新数据集验证
- [ ] 多尺度推理优化
- [ ] 模型蒸馏

### 4.3 低优先级

- [ ] 自监督预训练
- [ ] 多任务学习
- [ ] 主动学习策略

---

## 5. 性能监控

### 5.1 训练日志

```
logs_swin_final_v2/train.log
```

### 5.2 关键指标

| 指标 | 说明 | 目标 |
|------|------|------|
| **F1** | 变化检测精度 | > 0.92 |
| **IoU** | 交并比 | > 0.85 |
| **OA** | 总体精度 | > 0.99 |
| **FPS** | 推理速度 | > 30 |

### 5.3 可视化

```bash
# TensorBoard
tensorboard --logdir logs_swin_final_v2/

# 或查看训练日志
tail -f logs_swin_final_v2/train.log
```

---

## 6. 调用此代理

使用 `@delegate` 命令：

```
@delegate 算法开发代理: 检查当前训练状态
@delegate 算法开发代理: 优化RCMT训练参数
@delegate 算法开发代理: 导出模型到ONNX格式
@delegate 算法开发代理: 对比Swin V1和V2性能
```

---

## 7. 相关论文

1. RCMT: Recurrent Cross-Memory Transformer for Spatio-Temporal Change Detection (准备中)
2. Swin Transformer: Liu et al., ICCV 2021
3. ChangeFormer: ICCV 2023

---

**相关文档**:
- [系统总览](../01_architecture/OVERVIEW.md)
- [边缘推理框架](../02_software/EDGE_INFER_FRAMEWORK.md)
- [技术护城河](../01_architecture/TECHNICAL_MOAT.md)
