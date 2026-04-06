# 水利巡检智能检测系统 - 完整手册

**版本**: v3.0
**日期**: 2026-04-01
**团队**: 空中智能体团队

---

## 目录

1. [系统概述](#1-系统概述)
2. [任务定义](#2-任务定义)
3. [技术方案](#3-技术方案)
4. [数据准备](#4-数据准备)
5. [模型训练](#5-模型训练)
6. [部署指南](#6-部署指南)
7. [API 接口](#7-api-接口)
8. [常见问题](#8-常见问题)

---

## 1. 系统概述

### 1.1 核心方案

| 模型 | 任务 | 类别 | 部署 | FPS |
|------|------|------|------|-----|
| **YOLOv8-Pose** | 检测 | 11类 | 边缘 (Jetson/TensorRT) | 30+ |
| **C-RADIOv4-H** | 分割 | 5类 | 云端 (GPU/MQTT) | 5-10 |

C-RADIOv4 集成教师模型: **SigLIP2-g** (文本对齐), **DINOv3-7B**, **SAM3**

### 1.2 分类标准

| 判断依据 | YOLOv8 检测 | C-RADIOv4 分割 |
|---------|-----------|---------------|
| **有固定形状？** | 是 | 否 |
| **边界清晰？** | 是 | 否（渐变） |
| **核心特征** | 几何形状 | 颜色+纹理+语义 |
| **样本需求** | 200-1000张/类 | **零样本**（文本提示） |

### 1.3 项目结构

```
water_inspection/
├── configs/
│   └── water_inspection.yaml       # 统一配置
├── models/
│   ├── yolo/                       # YOLOv8 训练/推理
│   ├── open_vocab/                 # C-RADIOv4 分割
│   │   ├── radio_backbone.py       # ViT-H backbone (官方库/safetensors)
│   │   ├── radio_segmentor.py      # 零样本分割器
│   │   └── inference.py            # 统一接口 (含颜色回退)
│   └── unified.py                  # 统一检测系统
├── deployment/                     # 部署工具
├── tests/
│   └── test_e2e.py                 # 端到端测试
└── docs/
    └── MANUAL.md                   # 本文档
```

---

## 2. 任务定义

### 2.1 YOLOv8（11类检测）— 边缘部署

#### 人员行为（5类）

| ID | 类别 | 英文 | 特征 | 样本数 |
|----|------|------|------|--------|
| 0 | 人员 | person | 人体形状 | 1300 |
| 1 | 钓鱼 | fishing_person | 人+鱼竿 | 650 |
| 2 | 游泳 | swimming_person | 人+水面 | 520 |
| 3 | 嬉水 | playing_person | 人+岸边 | 390 |
| 4 | 闯入 | intruding_person | 人+位置 | 390 |

#### 基础设施（4类）

| ID | 类别 | 英文 | 特征 | 样本数 |
|----|------|------|------|--------|
| 5 | 水位尺 | water_gauge | 长条形 | 520 |
| 6 | 排污口 | outlet_pipe | 管道形状 | 390 |
| 7 | 排污中 | outlet_active | 管道+水流 | 260 |
| 8 | 管道破损 | pipe_damaged | 管道+破损 | 195 |

#### 目标监测（2类）

| ID | 类别 | 英文 | 特征 | 样本数 |
|----|------|------|------|--------|
| 9 | 船舶 | boat | 船体形状 | 650 |
| 10 | 漂浮物 | floating_debris | 固体目标 | 520 |

---

### 2.2 C-RADIOv4（5类零样本分割）— 云端部署

#### 水质异常（4类）

| 类别 | 英文 | 文本提示 |
|------|------|---------|
| 黑水 | black_water | "dark black or brown polluted water surface with oil film" |
| 红水 | red_water | "red or pink colored water from industrial pollution" |
| 绿水 | green_water | "deep green water surface with algae blooming" |
| 乳白水 | milky_water | "turbid milky white or gray water with suspended particles" |

#### 基础设施异常（1类）

| 类别 | 英文 | 文本提示 |
|------|------|---------|
| 坝体渗水 | dam_seepage | "wet dark water stains and seepage marks on concrete dam surface" |

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

### 3.2 C-RADIOv4 架构

C-RADIOv4 是 NVIDIA 的视觉 backbone，通过蒸馏集成多个教师模型:

```
输入图像 (896×896)
    │
    ├─ ViT-H Backbone (32层, 1280维)
    │    ├─ Patch Embedding (16×16)
    │    ├─ 32× Transformer Blocks
    │    └─ Register Tokens (10个)
    │
    ├─ SigLIP2-g Adaptor (文本对齐)
    │    ├─ 视觉特征 → 对齐空间
    │    └─ 文本编码 → 对齐空间
    │
    └─ 零样本分割
         ├─ Patch features ↔ Text features (cosine similarity)
         ├─ Patch-level 分数图
         └─ 双线性插值 → 像素级 mask
```

**模型加载方式（按优先级）**:
1. `torch.hub.load('NVlabs/RADIO', 'radio_model', version='c-radio_v4-h', adaptor_names=['siglip2-g'])`
2. `AutoModel.from_pretrained('nvidia/C-RADIOv4-H', trust_remote_code=True)`
3. 本地 `safetensors` 权重重建（离线回退）

### 3.3 云边协同

```
边缘设备 (Jetson)                     云端 (GPU Server)
┌─────────────────┐    MQTT     ┌──────────────────────┐
│  YOLOv8 检测     │ ─────────→ │  C-RADIOv4 分割       │
│  11类 · 30FPS    │ 关键帧上传  │  5类 · 零样本         │
│                  │ ←───────── │                      │
│  报警 · 可视化   │  分割结果    │  SigLIP2-g 文本匹配   │
└─────────────────┘             └──────────────────────┘
         │                               │
         └───────── EMQX Broker ──────────┘
              Topics:
              device/{id}/cloud/frame  → 上传
              device/{id}/cloud/result ← 回传
```

---

## 4. 数据准备

### 4.1 数据集规模

| 模型 | 总计 | 说明 |
|------|------|------|
| **YOLOv8** | 5785张 | 边界框标注 |
| **C-RADIOv4** | 不需要 | 零样本，仅配置文本提示 |

### 4.2 YOLOv8 标注规范

**格式**: YOLO 格式
```
# class_id x_center y_center width height (归一化 0-1)
0 0.5 0.6 0.2 0.3    # person
1 0.4 0.5 0.15 0.25  # fishing_person
```

---

## 5. 模型训练

### 5.1 YOLOv8 训练

```bash
# 训练
python models/yolo/train.py \
    --config configs/water_inspection.yaml \
    --data data/processed/data.yaml \
    --epochs 200 \
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

### 5.2 C-RADIOv4 配置

**无需训练！** 只需在配置文件中编辑文本提示:

```yaml
cloud:
  radio:
    classes:
      black_water:
        zh: "黑水"
        prompts:
          - "dark black or brown polluted water surface with oil film"
          - "black contaminated water with dark color and poor visibility"

      green_water:
        zh: "绿水"
        prompts:
          - "deep green water surface with algae blooming"
```

---

## 6. 部署指南

### 6.1 Docker Compose（推荐）

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

### 6.2 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MQTT_BROKER_URL` | MQTT broker 地址 | `tcp://emqx:1883` |
| `MODEL_PATH` | C-RADIOv4 权重路径 | `checkpoints/model.safetensors` |
| `DEVICE` | 推理设备 | `cuda` |
| `INPUT_SIZE` | 输入尺寸 | `896` |
| `OFFLINE` | 离线模式 | `false` |
| `ALERT_MIN_AREA` | 报警最小面积 | `0.01` |

### 6.3 Jetson 边缘部署

```bash
# 导出 ONNX
python deployment/export_model.py --weights best.pt --output models/

# 在 Jetson 上转换 TensorRT
trtexec --onnx=water_inspection.onnx --saveEngine=water_inspection.engine --fp16
```

---

## 7. API 接口

### 7.1 Python 接口

```python
from models.unified import WaterInspectionSystem

system = WaterInspectionSystem("configs/water_inspection.yaml")
result = system.detect(image)

# result["detections"] - YOLOv8 检测结果
# result["segments"]   - C-RADIOv4 分割结果
# result["alerts"]     - 报警信息
```

### 7.2 MQTT 消息格式

**请求** (`device/{id}/cloud/frame`):
```json
{
  "device_id": "jetson-001",
  "frame_id": 12345,
  "image": "<base64 JPEG>",
  "classes": ["black_water", "green_water"]
}
```

**响应** (`device/{id}/cloud/result`):
```json
{
  "device_id": "jetson-001",
  "frame_id": 12345,
  "segments": {
    "black_water": {"area": 0.05, "score": 0.8, "bbox": [x1,y1,x2,y2]}
  },
  "alerts": [
    {"class_name": "black_water", "level": "critical", "message": "黑水面积5%"}
  ],
  "inference_time_ms": 150.5
}
```

---

## 8. 常见问题

### Q1: C-RADIOv4 和 DINOv3+SAM3 是什么关系？

C-RADIOv4 通过知识蒸馏集成了多个教师模型，包括 **SigLIP2-g**、**DINOv3-7B** 和 **SAM3**。它用一个统一的 ViT-H backbone 替代了分别加载 DINOv3 和 SAM3 的方案，更高效且文本对齐能力由 SigLIP2-g 原生提供。

### Q2: 零样本分割的原理是什么？

C-RADIOv4 的 SigLIP2-g adaptor 将视觉特征和文本特征映射到同一空间。通过计算每个 patch 特征与文本提示的余弦相似度，得到 patch 级别的分类分数，再上采样到像素级 mask。

### Q3: 无 GPU 时能用吗？

可以。`OpenVocabSegmentor` 在 C-RADIOv4 不可用时自动回退到基于颜色阈值（HSV）的简单分割。

### Q4: 如何调整分割效果？

修改 `configs/water_inspection.yaml` 中:
- `cloud.radio.inference.threshold` — 降低阈值检测更多区域，提高阈值减少误检
- `cloud.radio.classes.*.prompts` — 优化文本提示描述

### Q5: safetensors 和官方库有什么区别？

| 特性 | 官方 RADIO 库 | safetensors 回退 |
|------|-------------|-----------------|
| 加载方式 | torch.hub / HuggingFace | 本地文件 |
| 文本编码 | SigLIP2-g 内置 | 不支持 |
| 网络需求 | 首次需要下载 | 完全离线 |
| 分割能力 | 零样本 | 仅颜色阈值 |

---

**维护者**: 空中智能体团队
**最后更新**: 2026-04-01
