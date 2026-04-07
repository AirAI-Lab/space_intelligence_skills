# 水利巡检智能检测系统 - 完整手册

**版本**: v3.4
**日期**: 2026-04-07
**团队**: 空中智能体团队

---

## 目录

1. [系统概述](#1-系统概述)
2. [任务定义](#2-任务定义)
3. [技术方案](#3-技术方案)
4. [快速开始](#4-快速开始)
5. [数据准备](#5-数据准备)
6. [模型训练](#6-模型训练)
7. [部署指南](#7-部署指南)
8. [API 接口](#8-api-接口)
9. [常见问题](#9-常见问题)

---

## 1. 系统概述

### 1.1 核心方案

| 模型 | 任务 | 类别 | 部署 | FPS |
|------|------|------|------|-----|
| **YOLOv8-Pose** | 检测 | 11类 | 边缘 (Jetson/TensorRT) | 30+ |
| **C-RADIOv4-H + SigLIP2-g** | 分割 | 7类 | 云端 (GPU/MQTT) | 5-10 |

C-RADIOv4 集成教师模型: **SigLIP2-g** (文本对齐), **DINOv3-7B**

### 1.2 v3.4 核心更新

- **v8 智能坝体渗水检测**: `dam_area > water_area` 约束，F1=84.2%
- **统一检测入口**: `unified.py` 开箱即用
- **多标签分类**: 概率阈值 >= 0.3 触发多标签检测

### 1.3 分类标准

| 判断依据 | YOLOv8 检测 | C-RADIOv4 分割 |
|---------|-----------|---------------|
| **有固定形状？** | 是 | 否 |
| **边界清晰？** | 是 | 否（渐变） |
| **核心特征** | 几何形状 | 颜色+纹理+语义 |
| **样本需求** | 200-1000张/类 | **零样本**（文本提示） |

### 1.4 项目结构

```
water_inspection/
├── configs/
│   └── water_inspection.yaml       # v3.4 统一配置
├── models/
│   ├── unified.py                  # 🔥 统一检测入口 (开箱即用)
│   ├── open_vocab/
│   │   ├── radseg_segmentor.py     # RADSeg v8 分割流水线
│   │   ├── radio_backbone.py       # ViT-H backbone
│   │   └── core/backbone.py        # backbone 核心实现
│   ├── classifier/
│   │   ├── lightweight_classifier.pkl  # SVM 分类器
│   │   └── scaler.pkl              # 特征标准化器
│   └── yolo/                       # YOLOv8 训练/推理
├── scripts/
│   ├── evaluate_pipeline_v8_production.py  # v8 评估脚本
│   ├── train_lightweight_classifier.py     # 分类器训练
│   └── _archive_v7/                       # 历史脚本归档
├── data/
│   ├── datasets/                   # 数据集
│   └── processed/                  # 处理后数据
├── outputs/                        # 输出结果
└── docs/
    └── MANUAL.md                   # 本文档
```

---

## 2. 任务定义

### 2.1 YOLOv8（11类检测）— 边缘部署

#### 人员行为（5类）

| ID | 类别 | 英文 | 特征 | 报警级别 |
|----|------|------|------|----------|
| 0 | 人员 | person | 人体形状 | 无 |
| 1 | 钓鱼 | fishing_person | 人+鱼竿 | info |
| 2 | 游泳 | swimming_person | 人+水面 | warning |
| 3 | 嬉水 | playing_person | 人+岸边 | warning |
| 4 | 闯入 | intruding_person | 人+位置 | critical |

#### 基础设施（4类）

| ID | 类别 | 英文 | 特征 | 报警级别 |
|----|------|------|------|----------|
| 5 | 水位尺 | water_gauge | 长条形 | 无 |
| 6 | 排污口 | outlet_pipe | 管道形状 | 无 |
| 7 | 排污中 | outlet_active | 管道+水流 | warning |
| 8 | 管道破损 | pipe_damaged | 管道+破损 | critical |

#### 目标监测（2类）

| ID | 类别 | 英文 | 特征 | 报警级别 |
|----|------|------|------|----------|
| 9 | 船舶 | boat | 船体形状 | 无 |
| 10 | 漂浮物 | floating_debris | 固体目标 | info |

---

### 2.2 C-RADIOv4（7类水质分割）— 云端部署

#### 水质异常（5类）

| 类别 | 英文 | 检测方式 | 报警级别 |
|------|------|---------|----------|
| 黑水 | black_water | RADSeg + SVM | warning |
| 浑浊水 | turbid_water | RADSeg + SVM | info |
| 红水 | red_water | RADSeg + SVM | warning |
| 绿水/藻类 | green_water | RADSeg + SVM | info |
| 乳白水/泡沫 | milky_foam_water | RADSeg + SVM | info |

#### 特殊检测（1类）

| 类别 | 英文 | 检测方式 | 报警级别 |
|------|------|---------|----------|
| 坝体渗水 | dam_seepage | **v8 流水线** (water ∩ dam + dam>water) | critical |

#### 背景（1类）

| 类别 | 英文 | 检测方式 |
|------|------|---------|
| 正常水 | normal_water | 背景类 |

---

## 3. 技术方案

### 3.1 YOLOv8 架构

```
输入图像 (640×640)
    │
    ├─ Backbone (CSPDarknet)
    ├─ Neck (PANet)
    ├─ Head (Detect) → 11类检测
    └─ Pose Head → 关键点（可选）
```

### 3.2 C-RADIOv4 v8 流水线

```
输入图像 (896×896)
    │
    ├─ Stage 1: RADSeg 分割
    │    ├─ C-RADIOv4 ViT-H Backbone → 3136 patch features
    │    ├─ SigLIP2-g 文本编码 → water, dam_concrete 提示
    │    └─ Patch similarity → water_mask, dam_mask
    │
    ├─ Stage 2: 坝体渗水分析
    │    ├─ seepage_mask = water_mask ∩ dam_mask
    │    ├─ 约束: overlap >= 0.5%
    │    ├─ 约束: seepage_area <= 30% * dam_area
    │    └─ 约束: dam_area > water_area ← 核心约束
    │
    └─ Stage 3: 水质分类
         ├─ 提取 67 维特征 (BGR/HSV + 直方图 + 颜色距离)
         ├─ SVM 分类器 → 水质类别
         └─ 多标签检测 (概率 >= 0.3)
```

### 3.3 云边协同

```
边缘设备 (Jetson)                     云端 (GPU Server)
┌─────────────────┐    MQTT     ┌──────────────────────┐
│  YOLOv8 检测     │ ─────────→ │  C-RADIOv4 v8 流水线  │
│  11类 · 30FPS    │ 关键帧上传  │  7类 · 5-10 FPS       │
│                  │ ←───────── │                      │
│  报警 · 可视化   │  分割结果    │  分类 + 渗水检测       │
└─────────────────┘             └──────────────────────┘
         │                               │
         └───────── EMQX Broker ──────────┘
              Topics:
              device/{id}/cloud/frame  → 上传
              device/{id}/cloud/result ← 回传
```

---

## 4. 快速开始

### 4.1 统一检测接口 (推荐)

```python
from models.water_inspection.models.unified import (
    UnifiedWaterInspectionSystem,
    create_system,
    detect_single_image
)

# 方式 1: 便捷函数 (单张图片)
results = detect_single_image(
    image_path="test.jpg",
    config_path="configs/water_inspection.yaml",
    output_path="output.jpg"
)

# 方式 2: 系统实例 (批量处理)
system = create_system("configs/water_inspection.yaml")
results = system.detect(image_bgr, run_water_quality=True)

# 查看结果
print(f"YOLO 检测: {len(results['detections'])} 个")
for det in results['detections']:
    print(f"  - {det.class_name_cn}: {det.confidence:.2f}")

if results['water_quality']:
    wq = results['water_quality']
    print(f"水质检测: {wq['detected_classes_cn']}")
    if wq['has_seepage']:
        print("  [警告] 检测到坝体渗水!")

print(f"报警: {len(results['alerts'])} 个")
for alert in results['alerts']:
    print(f"  - [{alert.level}] {alert.message}")
```

### 4.2 命令行使用

```bash
python models/water_inspection/models/unified.py \
    --config models/water_inspection/configs/water_inspection.yaml \
    --image test.jpg \
    --output result.jpg

# 不运行水质检测 (仅 YOLO)
python models/water_inspection/models/unified.py \
    --config configs/water_inspection.yaml \
    --image test.jpg \
    --no-water
```

---

## 5. 数据准备

### 5.1 数据集规模

| 模型 | 总计 | 说明 |
|------|------|------|
| **YOLOv8** | 5785张 | 边界框标注 |
| **C-RADIOv4** | 不需要 | 零样本，仅配置文本提示 |
| **SVM 分类器** | 200张/类 | 颜色标注 (用于训练分类器) |

### 5.2 YOLOv8 标注规范

**格式**: YOLO 格式
```
# class_id x_center y_center width height (归一化 0-1)
0 0.5 0.6 0.2 0.3    # person
1 0.4 0.5 0.15 0.25  # fishing_person
```

---

## 6. 模型训练

### 6.1 YOLOv8 训练

```bash
python models/water_inspection/models/yolo/train.py \
    --config configs/water_inspection.yaml \
    --data data/processed/data.yaml \
    --epochs 300 \
    --batch 12 \
    --device 0
```

关键参数:
```yaml
training:
  yolo:
    epochs: 300
    batch: 12
    lr0: 0.001
    optimizer: "AdamW"
    augment:
      hsv_h: 0.015
      hsv_s: 0.7
      mosaic: 1.0
      mixup: 0.1
```

### 6.2 SVM 分类器训练

```bash
cd models/water_inspection/scripts
python train_lightweight_classifier.py
```

### 6.3 C-RADIOv4 配置

**无需训练！** 只需在配置文件中编辑文本提示:

```yaml
cloud:
  radio:
    classes:
      black_water:
        zh: "黑水"
        color_hint: [95, 90, 85]  # BGR 颜色参考
        prompts:
          - "dark blackish gray water with all RGB channels below 130"
          - "opaque polluted water with RGB range less than 25"
```

---

## 7. 部署指南

### 7.1 Docker Compose（推荐）

```bash
# 启动基础服务 (数据库、MQTT、前端、后端)
docker compose up -d

# 启动含 GPU 的服务 (训练 + 云端推理)
docker compose --profile gpu up -d

# 仅启动云端推理
docker compose --profile gpu up cloud_infer
```

服务列表:
| 服务 | 端口 | 说明 |
|------|------|------|
| `cloud_infer` | 5003 | C-RADIOv4 推理 (MQTT) |
| `training` | 5002 | YOLOv8 训练 |
| `emqx` | 1883/18083 | MQTT Broker |
| `backend` | 8081 | API 服务 |
| `frontend` | 3000 | 前端界面 |

### 7.2 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MQTT_BROKER_URL` | MQTT broker 地址 | `tcp://emqx:1883` |
| `RADIO_CHECKPOINT` | C-RADIOv4 权重路径 | `/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar` |
| `SIGLIP2_DIR` | SigLIP2 模型目录 | `/app/models/siglip2-giant-opt-patch16-384` |
| `DEVICE` | 推理设备 | `cuda` |
| `INPUT_SIZE` | 输入尺寸 | `896` |

### 7.3 Jetson 边缘部署

```bash
# 导出 ONNX
python deployment/export_model.py --weights best.pt --output models/

# 在 Jetson 上转换 TensorRT
trtexec --onnx=water_inspection.onnx --saveEngine=water_inspection.engine --fp16
```

---

## 8. API 接口

### 8.1 Python 接口

```python
from models.water_inspection.models.unified import create_system

# 创建系统
system = create_system("configs/water_inspection.yaml")

# 检测
results = system.detect(image_bgr)

# 结果结构
results["detections"]     # List[Detection] - YOLO 检测结果
results["water_quality"]  # Dict - 水质检测结果
results["alerts"]         # List[Alert] - 报警信息

# 可视化
vis_image = system.visualize(image_bgr, results, "output.jpg")
```

### 8.2 MQTT 消息格式

**请求** (`device/{id}/cloud/frame`):
```json
{
  "device_id": "jetson-001",
  "frame_id": 12345,
  "image": "<base64 JPEG>",
  "classes": ["black_water", "dam_seepage"]
}
```

**响应** (`device/{id}/cloud/result`):
```json
{
  "device_id": "jetson-001",
  "frame_id": 12345,
  "water_quality": {
    "detected_classes": ["black_water", "dam_seepage"],
    "detected_classes_cn": ["黑水", "坝体渗水"],
    "has_seepage": true,
    "area_ratios": {"black_water": 0.05, "dam_seepage": 0.02}
  },
  "alerts": [
    {"class_name": "dam_seepage", "level": "critical", "message": "检测到坝体渗水 (面积: 2.0%)"}
  ],
  "inference_time_ms": 150.5
}
```

---

## 9. 常见问题

### Q1: v8 坝体渗水检测的 dam>water 约束是什么？

**原理**: 真实坝体渗水场景中，坝体是主体结构，水体是渗出的一小部分；误检场景（如河道旁混凝土护栏）中，水体是主体。

| 场景 | dam_area | water_area | 结果 |
|------|----------|------------|------|
| 真实渗水 | 大 | 小 | ✅ 检出 |
| 河道护栏 | 小 | 大 | ❌ 过滤 |

**效果**: F1=84.2%, Precision=88.9%, Recall=80.0%

### Q2: 如何调整 v8 流水线参数？

编辑 `configs/water_inspection.yaml`:

```yaml
cloud:
  radio:
    v8_pipeline:
      segmentation_threshold: 0.4    # 分割阈值
      seepage:
        min_overlap: 0.005           # 最小渗水面积 (0.5%)
        max_ratio: 0.3               # 最大渗水占坝体比例 (30%)
        require_dam_gt_water: true   # dam>water 约束
      multi_label:
        enabled: true
        threshold: 0.3               # 多标签阈值
```

### Q3: 零样本分割的原理是什么？

C-RADIOv4 的 SigLIP2-g adaptor 将视觉特征和文本特征映射到同一空间。通过计算每个 patch 特征与文本提示的余弦相似度，得到 patch 级别的分类分数，再上采样到像素级 mask。

### Q4: 如何新增一个水质类别？

编辑 `configs/water_inspection.yaml`:

```yaml
cloud:
  radio:
    classes:
      oil_spill:
        zh: "油污"
        color_hint: [100, 150, 180]
        use_color_check: true
        prompts:
          - "rainbow iridescent oil film on water surface"
          - "oil spill floating on water with colorful reflection"
        alert:
          enabled: true
          level: warning
          description: 发现油污，可能存在泄漏
```

### Q5: 模型文件需要多大空间？

| 文件 | 大小 | 说明 |
|------|------|------|
| c-radio_v4-h_half.pth.tar | 1.68 GB | C-RADIOv4 权重 |
| siglip2-giant weights | 7.5 GB | SigLIP2 文本+视觉模型 |
| **总计** | **~9.2 GB** | |

---

**维护者**: 空中智能体团队
**最后更新**: 2026-04-07

---

## 10. 依赖下载指南

本系统依赖以下第三方模型和代码库，需手动下载后配置路径。

### 10.1 模型文件

| 模型 | 大小 | 下载地址 | 配置路径 |
|------|------|----------|----------|
| **C-RADIOv4-H** | 1.68 GB | [NVIDIA C-RADIO](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/seg/models/c_radio_v4-h) | `/app/models/C-RADIOv4-H/` |
| **SigLIP2-Giant** | 7.5 GB | [HuggingFace](https://huggingface.co/google/siglip2-giant-opt-patch16-384) | `/app/models/siglip2-giant-opt-patch16-384/` |
| **DINOv3-7B** | ~7 GB | [Meta DINOv3](https://github.com/facebookresearch/dinov3) | 自动下载 (huggingface) |

### 10.2 下载步骤

#### C-RADIOv4-H

```bash
# 方式 1: NGC CLI (需要 NVIDIA 账号)
ngc registry model download-version nvidia/seg/c-radio_v4-h:1.0

# 方式 2: 直接下载 (从 NGC 网页)
# 访问 https://catalog.ngc.nvidia.com/orgs/nvidia/teams/seg/models/c_radio_v4-h
# 下载 c-radio_v4-h_half.pth.tar

# 放置到指定目录
mkdir -p /app/models/C-RADIOv4-H
mv c-radio_v4-h_half.pth.tar /app/models/C-RADIOv4-H/
```

#### SigLIP2-Giant

```bash
# 方式 1: huggingface-cli (推荐)
pip install huggingface_hub
huggingface-cli download google/siglip2-giant-opt-patch16-384 \
    --local-dir /app/models/siglip2-giant-opt-patch16-384

# 方式 2: 国内镜像 (如果 huggingface 无法访问)
HF_ENDPOINT=https://hf-mirror.com huggingface-cli download google/siglip2-giant-opt-patch16-384 \
    --local-dir /app/models/siglip2-giant-opt-patch16-384

# 方式 3: 手动下载
# 访问 https://huggingface.co/google/siglip2-giant-opt-patch16-384
# 下载所有文件到 /app/models/siglip2-giant-opt-patch16-384/
```

#### NVlabs_RADIO 代码

```bash
# RADIO 官方代码库
git clone https://github.com/NVlabs/RADIO.git /app/models/NVlabs_RADIO
```

### 10.3 完整目录结构

下载完成后的模型目录结构：

```
/app/models/
├── C-RADIOv4-H/
│   └── c-radio_v4-h_half.pth.tar      # 1.68 GB
├── siglip2-giant-opt-patch16-384/
│   ├── config.json
│   ├── model.safetensors              # 主权重文件
│   ├── tokenizer.json
│   └── ...
├── NVlabs_RADIO/
│   ├── radio/
│   ├── hubconf.py
│   └── ...
└── water_inspection/
    └── models/classifier/
        ├── lightweight_classifier.pkl   # 48 KB (本系统训练)
        └── scaler.pkl                   # 2 KB
```

### 10.4 环境变量配置

在 Docker Compose 或 `.env` 中配置：

```bash
# 模型路径
RADIO_CHECKPOINT=/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar
RADIO_CODE_DIR=/app/models/NVlabs_RADIO
SIGLIP2_DIR=/app/models/siglip2-giant-opt-patch16-384

# 或者在 Python 代码中
import os
os.environ['RADIO_CHECKPOINT'] = '/path/to/c-radio_v4-h_half.pth.tar'
os.environ['RADIO_CODE_DIR'] = '/path/to/NVlabs_RADIO'
os.environ['SIGLIP2_DIR'] = '/path/to/siglip2-giant-opt-patch16-384'
```

### 10.5 验证安装

```python
# 测试 C-RADIOv4 加载
from models.water_inspection.models.open_vocab.core.backbone import RadioBackbone
backbone = RadioBackbone(
    checkpoint_path='/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar',
    radio_code_dir='/app/models/NVlabs_RADIO',
    siglip2_dir='/app/models/siglip2-giant-opt-patch16-384',
    device='cuda'
)
print(f"✅ C-RADIOv4 加载成功, 参数量: {backbone.params_m:.1f}M")

# 测试完整分割器
from models.water_inspection.models.open_vocab import RADSegWaterSegmentor
segmentor = RADSegWaterSegmentor(
    checkpoint_path='/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar',
    radio_code_dir='/app/models/NVlabs_RADIO',
    siglip2_dir='/app/models/siglip2-giant-opt-patch16-384',
    device='cuda'
)
print("✅ 分割器加载成功")
```

### 10.6 国内用户加速

如果 HuggingFace 无法访问，可使用镜像：

```bash
# 临时使用镜像
export HF_ENDPOINT=https://hf-mirror.com

# 或在代码中设置
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

常用镜像：
- [hf-mirror.com](https://hf-mirror.com) - 推荐，实时同步
- [ModelScope](https://modelscope.cn) - 阿里云镜像，需注册
