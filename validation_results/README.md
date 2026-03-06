# RCMT-V3 验证结果目录

本目录包含 RCMT-V3 模型在各类数据集上的验证结果。

## 📁 目录结构

```
validation_results/
├── README.md                    # 本文件
├── quick_validate.py           # 快速验证脚本
├── validate_on_datasets.py     # 数据集验证脚本
├── sysu_cd_demo/               # SYSU-CD 验证结果示例
└── validation_YYYYMMDD_HHMMSS/ # 历史验证结果
    ├── XXXX_t1.png            # 时相1图像
    ├── XXXX_t2.png            # 时相2图像
    ├── XXXX_gt.png            # 真实标签
    ├── XXXX_pred.png          # 预测结果
    ├── XXXX_comparison.png    # 对比可视化
    ├── XXXX_vis.png           # 详细可视化
    └── report.json            # 验证报告
```

## 🚀 快速使用

### 1. 检查 GPU 显存

```bash
nvidia-smi
```

**如果显存充足（空闲 > 2GB），可以直接运行验证脚本。**

### 2. 运行验证

#### 在 LEVIR-CD 数据集上验证（训练数据集）

```bash
cd D:\github\edge_infer_cloud\validation_results

python quick_validate.py \
    --data-dir /data/LEVIR-CD256 \
    --config ../models/rcmt_v3/configs/rcmt_v3_swin.yaml \
    --model-path D:/github/edge_infer/rcmt_v3/checkpoints_swin_final/best_model.pth \
    --num-samples 5 \
    --output-dir ./
```

#### 在 SYSU-CD 数据集上验证（验证数据集）

```bash
python quick_validate.py \
    --data-dir /data/SYSU-CD \
    --config ../models/rcmt_v3/configs/rcmt_v3_swin.yaml \
    --model-path D:/github/edge_infer/rcmt_v3/checkpoints_swin_final/best_model.pth \
    --num-samples 5 \
    --output-dir ./
```

### 3. 查看结果

验证完成后，会在当前目录生成：

- **对比图像** (`*_comparison.png`): T1 | T2 | GT | Pred 四联图
- **详细可视化** (`*_vis.png`): 带颜色编码的可视化
- **报告文件** (`report.json`): 包含所有指标

## ⚠️ GPU 显存不足时的解决方案

### 方案 1: 暂停训练 → 推理 → 恢复训练

```bash
# 1. 停止训练进程
pkill -f train_rcmt_v3

# 2. 等待进程结束（约 10 秒）
sleep 10

# 3. 清理 GPU 缓存
python -c "import torch; torch.cuda.empty_cache()"

# 4. 运行验证
python quick_validate.py --num-samples 5

# 5. 恢复训练
python train_rcmt_v3_swin_temporal.py --resume checkpoints_swin_final/latest_checkpoint.pth
```

### 方案 2: 使用 CPU 推理（慢但稳定）

```bash
python quick_validate.py --num-samples 3 --device cpu
```

**注意：CPU 推理速度约为 GPU 的 1/10 到 1/20。**

### 方案 3: 减小推理批大小

如果只是想快速验证，可以减少样本数量：

```bash
python quick_validate.py --num-samples 2
```

## 📊 当前训练状态

```
更新时间: 2026-03-04 13:30
训练进度: Epoch 146/300 (48.7%)
最佳 F1:  0.8962 (Epoch 144)
GPU 显存: 15909MiB / 16311MiB (97.5%)
GPU 利用: 89%
```

**建议：等待训练完成后再进行大规模验证，或暂停训练进行小规模测试。**

## 📈 验证结果示例

### LEVIR-CD (训练数据集)

| Epoch | F1 | IoU | Precision | Recall |
|-------|-----|-----|-----------|--------|
| 93 | 0.8931 | 0.8068 | 0.8963 | 0.8899 |
| 100 | 0.8909 | 0.8033 | 0.9240 | 0.8601 |
| 144 | 0.8962 | 0.8119 | 0.9217 | 0.8721 |

### SYSU-CD (验证数据集)

等待验证...

## 🔧 集成到推理服务

验证脚本也可以作为推理服务的一部分：

```python
from validation_results.quick_validate import quick_validate

# 在服务启动时验证
report = quick_validate(
    data_root="/data/SYSU-CD",
    config_path="models/rcmt_v3/configs/rcmt_v3_swin.yaml",
    model_path="checkpoints_swin_final/best_model.pth",
    num_samples=5,
)

print(f"平均 F1: {report['avg_f1']:.4f}")
print(f"平均 IoU: {report['avg_iou']:.4f}")
```

## 📞 联系方式

如有问题，请联系 RCMT-V3 团队。

---

**最后更新**: 2026-03-04 13:30
