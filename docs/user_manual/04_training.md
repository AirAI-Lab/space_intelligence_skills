# 模型训练指南

本指南介绍如何使用平台的训练功能，参考YOLOv8的训练流程。

## 训练前准备

### 1. 准备数据集

参考《数据管理指南》创建并配置数据集。

### 2. 选择训练方式

#### 方式A：宿主机训练（小规模）

**适用场景**：
- 快速实验
- 小数据集（<5000张）
- 模型微调

**硬件要求**：
- GPU: RTX 4060 Ti 16GB 或更高
- 内存: 32GB+
- 存储: 500GB SSD

#### 方式B：云端GPU训练（大规模）

**适用场景**：
- 大规模数据集（>5000张）
- 复杂模型训练
- 多GPU并行训练

**云端GPU选项**：

| 云厂商 | 产品 | GPU选项 | 价格 |
|--------|------|---------|------|
| 阿里云 | PAI-EAS | P100/V100/A10 | ¥10-30/小时 |
| 华为云 | ModelArts | 昇腾/CUDA GPU | ¥8-25/小时 |
| 腾讯云 | GPU云服务器 | T4/V100 | ¥10-35/小时 |
| AutoDL | 租赁平台 | RTX 3090/4090 | ¥2-5/小时 |

## 训练流程

### 第一步：创建训练任务

#### 通过Web界面

1. 点击"训练管理" → "创建训练任务"
2. 填写训练配置：

**基础配置**：

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| 任务名称 | 训练任务显示名称 | my_training_job |
| 数据集 | 选择已准备的数据集 | my_dataset |
| 基础模型 | 预训练模型 | yolov8n.pt |

**训练参数**：

| 参数 | 说明 | 推荐值 | 范围 |
|------|------|--------|------|
| epochs | 训练轮数 | 100 | 50-300 |
| batch | 批量大小 | 16 | 8-64 |
| imgsz | 图像大小 | 640 | 320-1280 |
| lr0 | 初始学习率 | 0.01 | 0.001-0.1 |
| optimizer | 优化器 | AdamW | SGD/Adam/AdamW |
| device | GPU设备 | 0 | 0,1,2... |

**高级参数**：

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| patience | 早停耐心值 | 50 |
| save_period | 保存频率 | 10 |
| cache | 数据缓存 | ram/disk/false |
| amp | 混合精度 | true |
| cos_lr | 余弦学习率 | true |
| warmup_epochs | 预热轮数 | 3 |

3. 点击"开始训练"

#### 通过CLI

```bash
# 基础训练
edge-train train \
    --data /datasets/my_dataset/data.yaml \
    --model yolov8n.pt \
    --epochs 100 \
    --batch 16 \
    --imgsz 640 \
    --device 0

# 多GPU训练
edge-train train \
    --data /datasets/my_dataset/data.yaml \
    --model yolov8n.pt \
    --device 0,1

# 恢复训练
edge-train train resume \
    --model runs/train/exp/weights/last.pt
```

### 第二步：监控训练进度

#### 实时监控

训练任务页面显示：

**训练进度**：
- 当前epoch：50/100
- 训练时间：01:23:45
- 预计剩余：00:45:30

**实时指标**：
- loss：总损失
- box_loss：边界框损失
- cls_loss：分类损失
- dfl_loss：分布焦点损失

**学习率**：
- 当前学习率曲线
- 预热阶段

#### TensorBoard可视化

启动TensorBoard：

```bash
# 在宿主机或训练容器中
tensorboard --logdir runs/train
```

访问 http://localhost:6006 查看：

- 损失曲线
- 精确率-召回率曲线
- mAP曲线
- 学习率变化
- 验证结果对比
- 预测示例

#### 训练指标说明

| 指标 | 说明 | 目标值 | 计算方式 |
|------|------|--------|---------|
| loss | 总损失 | 越低越好 | 所有损失加权和 |
| mAP50 | mAP@0.5 | >0.9 | IoU=0.5时的mAP |
| mAP50-95 | mAP@0.5:0.95 | >0.7 | IoU从0.5到0.95的mAP |
| precision | 精确率 | >0.8 | TP/(TP+FP) |
| recall | 召回率 | >0.8 | TP/(TP+FN) |

### 第三步：验证模型

训练完成后，自动运行验证。

#### 通过Web界面

1. 训练任务完成后，点击"查看详情"
2. 查看"验证结果"标签页

#### 通过CLI

```bash
edge-train val \
    --model runs/train/exp/weights/best.pt \
    --data /datasets/my_dataset/data.yaml \
    --batch 16 \
    --imgsz 640 \
    --device 0 \
    --plots true \
    --save_json true
```

#### 验证结果

| 类别 | precision | recall | mAP50 | mAP50-95 |
|------|----------|--------|-------|---------|
| person | 0.85 | 0.82 | 0.91 | 0.72 |
| car | 0.88 | 0.85 | 0.93 | 0.75 |
| dog | 0.80 | 0.78 | 0.88 | 0.68 |

#### 混淆矩阵

系统自动生成混淆矩阵，显示：
- 各类别检测准确率
- 误检情况
- 漏检情况

### 第四步：导出模型

训练完成后，导出模型用于部署。

#### 导出选项

| 格式 | 扩展名 | 特点 | 推荐场景 |
|------|--------|------|---------|
| PyTorch | .pt | 原始格式 | 继续训练 |
| TorchScript | .torchscript | Python部署 | 服务器部署 |
| ONNX | .onnx | 跨平台 | 通用部署 |
| TensorRT | .engine | 最快推理 | 边缘部署 |

#### 通过Web界面导出

1. 进入"训练任务"详情
2. 点击"导出模型"
3. 选择导出格式和参数：

**ONNX导出**：
- 动态输入：是/否
- 简化模型：是/否
- 半精度(FP16)：是/否

**TensorRT导出**：
- 半精度(FP16)：是/否
- 量化(INT8)：是/否
- 工作空间大小：4GB

4. 点击"开始导出"

#### 通过CLI导出

```bash
# 导出为ONNX
edge-train export \
    --model runs/train/exp/weights/best.pt \
    --format onnx \
    --imgsz 640 \
    --half true \
    --dynamic true \
    --simplify true

# 导出为TensorRT
edge-train export \
    --model runs/train/exp/weights/best.pt \
    --format engine \
    --half true \
    --int8 true \
    --workspace 4
```

## 云端GPU训练

### 阿里云PAI-EAS

#### 配置步骤

1. 登录阿里云控制台
2. 进入PAI-EAS页面
3. 创建训练任务：
   - 选择GPU实例类型
   - 配置镜像（包含训练环境）
   - 挂载数据集OSS
4. 启动训练

#### 通过平台集成

```bash
# 配置云端训练
edge-train cloud setup \
    --provider aliyun \
    --instance gpu.p100 \
    --region cn-hangzhou

# 启动云端训练
edge-train cloud start \
    --data oss://my-bucket/dataset \
    --config configs/train.yaml
```

### 华为云ModelArts

#### 配置步骤

1. 登录华为云控制台
2. 进入ModelArts页面
3. 创建训练作业：
   - 选择昇腾或CUDA GPU
   - 配置训练脚本
   - 设置数据路径
4. 提交训练

### AutoDL（推荐）

AutoDL提供高性价比的GPU租赁：

#### 优势
- 价格低（RTX 3090约¥2/小时）
- 按小时计费
- 支持多种GPU
- 预装深度学习环境

#### 使用步骤

1. 注册AutoDL账号
2. 租用GPU实例
3. 选择镜像（PyTorch + CUDA）
4. Jupyter连接或SSH连接
5. 上传数据和代码
6. 运行训练

## 训练最佳实践

### 1. 数据准备

- 数据量充足（每类>500张）
- 标注准确
- 数据多样性（不同场景、角度）
- 数据均衡（各类别数量相近）

### 2. 超参数调优

| 参数 | 初始值 | 调优策略 |
|------|--------|---------|
| lr0 | 0.01 | 收敛慢→增大，震荡→减小 |
| batch | 16 | 显存够→增大 |
| weight_decay | 0.0005 | 过拟合→增大 |
| mosaic | 1.0 | 小目标多→保持 |

### 3. 训练技巧

- **预训练**：使用COCO预训练权重
- **渐进式训练**：小图像→大图像
- **混合精度**：启用AMP加速
- **数据缓存**：使用RAM缓存加速

### 4. 故障排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| loss不下降 | 学习率过小 | 增大lr0 |
| loss震荡 | 学习率过大 | 减小lr0 |
| 过拟合 | 数据不足 | 增加数据增强 |
| 欠拟合 | 模型太小 | 使用更大模型 |

## 下一步

- 阅读 [模型部署指南](05_model_deploy.md)
- 阅读 [OTA升级指南](06_ota_upgrade.md)
