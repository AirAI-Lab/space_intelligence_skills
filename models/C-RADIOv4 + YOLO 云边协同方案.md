# C-RADIOv4 + YOLO 云边协同方案

> **版本**: v3.4 | **更新**: 2026-04-07
> **对齐仓库**: `edge_infer_cloud`（云边协同平台，Python）+ `edge_infer`（边缘推理平台，C++）
>
> **v3.4 核心更新**: v8 智能坝体渗水检测 (`dam_area > water_area` 约束, F1=84%)

---

## 目录

1. [方案概述](#一方案概述)
2. [快速开始](#二快速开始)
3. [零样本分割原理（必读）](#三零样本分割原理必读)
4. [模型加载机制](#四模型加载机制)
5. [数据集准备与标注](#五数据集准备与标注)
6. [训练与验证](#六训练与验证)
7. [部署指南](#七部署指南)
8. [推理服务](#八推理服务)
9. [三大场景差异化设计](#九三大场景差异化设计)
10. [工程化保障](#十工程化保障)
11. [常见问题](#十一常见问题)

---

## 一、方案概述

### 核心架构

```
边缘设备 (Jetson)                     云端 (GPU Server)
┌─────────────────┐    MQTT     ┌──────────────────────┐
│  YOLOv8 检测     │ ─────────→ │  C-RADIOv4 + SigLIP2  │
│  11类 · 30FPS    │ 关键帧上传  │  8类 · 零样本         │
│  固定形状目标    │ ←───────── │  无固定形状目标       │
│  本地实时报警    │  分割结果    │  分类 + 异常分割       │
└─────────────────┘             └──────────────────────┘
         │                               │
         └───────── EMQX Broker ──────────┘
```

### 分工原则

| 判断依据 | YOLOv8 检测（边缘） | C-RADIOv4 分割（云端） |
|---------|-------------------|---------------------|
| **有固定形状？** | ✅ 人、车、管道 | ❌ 水色、渗水区域 |
| **边界清晰？** | ✅ 矩形框即可 | ❌ 渐变、模糊边界 |
| **需要训练数据？** | ✅ 200+张/类 | ❌ **零样本**，只需文本描述 |
| **部署位置** | Jetson TensorRT FP16 | 云端 GPU |

### C-RADIOv4 集成的教师模型

C-RADIOv4 由 NVIDIA 通过知识蒸馏整合了三个教师模型的能力：

| 教师模型 | 能力 | 在本项目中的作用 |
|---------|------|----------------|
| **SigLIP2-g** | 文本-视觉对齐 | 将文本描述（"黑色的水"）和图像 patch 匹配到同一特征空间 |
| **DINOv3-7B** | 视觉特征提取 | 提供强大的视觉语义理解 |
| **SAM3** | 分割能力 | 提供精确的空间定位能力 |

加载 C-RADIOv4 时指定 `adaptor_names=['siglip2-g']`，即可获得文本编码能力。

---

## 二、快速开始

### 环境要求

- **Docker** + **Docker Compose** + **NVIDIA Container Toolkit**
- **GPU**: 训练需要 RTX 3090/4090/A100，推理支持 Jetson Orin
- **磁盘**: 预留 10GB+（模型缓存 2.6GB + Docker 镜像）

### 30 秒启动

```bash
# 1. 克隆仓库
git clone https://github.com/AirAI-Lab/edge_infer_cloud.git
cd edge_infer_cloud

# 2. 启动所有服务
cd deployment/docker
docker compose up -d                        # 基础服务 (数据库/MQTT/前端/后端)
docker compose --profile gpu up -d          # 含 GPU 服务 (训练 + 云端推理)

# 3. 验证
docker compose ps                           # 查看服务状态
# cloud_infer 服务会自动加载 C-RADIOv4 并监听 MQTT
```

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| EMQX MQTT | 1883 | MQTT Broker |
| EMQX 管理 | 18083 | MQTT 管理界面 (admin/admin123456) |
| 后端 API | 8081 | Spring Boot 后端 |
| 前端 | 3000 | Vue 前端 |
| 训练服务 | 5002 | YOLO 训练 |
| 云端推理 | 5003 | C-RADIOv4 MQTT 推理 |
| MLflow | 5000 | 训练实验管理 |

### 目录结构

```
edge_infer_cloud/
├── models/
│   ├── NVlabs_RADIO/                    # 官方 RADIO 代码 (本地)
│   │   ├── hubconf.py                   # torch.hub 入口
│   │   └── radio/                       # RADIO 核心包
│   ├── C-RADIOv4-H/                     # C-RADIOv4 权重
│   │   └── c-radio_v4-h_half.pth.tar   # 半精度 checkpoint (1.68GB)
│   ├── siglip2-giant-opt-patch16-384/   # SigLIP2 文本模型 (本地)
│   │   ├── model-*.safetensors          # 权重 (7.5GB)
│   │   └── tokenizer.json              # 分词器
│   ├── water_inspection/                # 水利巡检场景
│   │   ├── configs/water_inspection.yaml    # v3.4 统一配置
│   │   ├── models/
│   │   │   ├── unified.py                   # 🔥 统一检测入口 (YOLO + v8)
│   │   │   ├── open_vocab/                  # C-RADIOv4 分割
│   │   │   │   ├── radseg_segmentor.py      # RADSeg v8 流水线
│   │   │   │   ├── radio_backbone.py        # ViT-H backbone 封装
│   │   │   │   └── inference.py             # 统一接口
│   │   │   └── classifier/                  # 水质分类器 (SVM)
│   │   │       ├── lightweight_classifier.pkl
│   │   │       └── scaler.pkl
│   │   ├── scripts/
│   │   │   ├── evaluate_pipeline_v8_production.py  # v8 评估脚本
│   │   │   ├── train_lightweight_classifier.py     # 分类器训练
│   │   │   └── _archive_v7/                       # 历史脚本归档
│   │   └── data/                             # 数据集
│   └── pretrained_models/                   # YOLO 预训练模型缓存
├── cloud/
│   └── radio_infer_server.py               # 云端 MQTT 推理服务
└── deployment/docker/
    ├── docker-compose.yml                   # 编排文件
    ├── cloud_infer.Dockerfile               # 云端推理镜像
    └── cloud_requirements.txt               # 云端依赖
```

---

## 三、零样本分割原理（必读）

### 什么是「零样本」？

**零样本（Zero-shot）= 不需要任何标注数据即可识别。**

传统方法（如 YOLO）需要：
1. 采集数百张图片
2. 人工标注边界框
3. 训练模型（数小时到数天）
4. 验证、调优
5. 如果新增一个类别，重复上述全部步骤

C-RADIOv4 的零样本方法只需要：
1. **用自然语言描述你想识别的目标**
2. 完成。模型自动匹配

### 它是怎么做到的？

### 零样本分割原理（混合方法）

C-RADIOv4 的零样本水质检测采用**分类+分割**混合方法：

1. **SigLIP2-giant 图像-文本匹配** — 判断水质类别
   - 图像整体 → SigLIP2 视觉编码 → 图像特征
   - 文本描述 → SigLIP2 文本编码 → 文本特征
   - 图像特征 @ 文本特征 → sigmoid → 分类概率
   - 准确率高：实测 **80-97% 置信度**检测红水、绿水等

2. **C-RADIOv4 ViT-H 异常分割** — 定位异常区域
   - 图像 → RADIO backbone → 3136 个 patch 特征 (56×56, 1280 维)
   - 计算 patch 特征与全局均值的相似度 → 异常 patch (低于均值)
   - 双线性插值 → 像素级异常 mask
   - 优势：RADIO 提供高质量的通用视觉特征

```
步骤 1: 图像级分类 (SigLIP2)
  image → SigLIP2 vision encoder → pooler output
  text prompts → SigLIP2 text encoder → text embeddings  
  cosine similarity × logit_scale + logit_bias → sigmoid → 概率

步骤 2: 空间异常分割 (RADIO)
  image → RADIO ViT-H → 3136 patch features (1280 维)
  每个 patch 与全局均值比较 → 距离大的为异常
  56×56 分数图 → 双线性插值 → 原图大小 mask

步骤 3: 组合结果
  SigLIP2 分类结果 + RADIO 异常 mask → 区域级水质异常报告
```

### 7 类水质检测 (v3.4)

| 类别 | 英文名 | 文本提示 |
|------|--------|---------|
| 黑水 | black_water | "dark blackish gray water with all RGB channels below 130" |
| 浑浊水 | turbid_water | "yellowish brown muddy water with R channel around 142" |
| 红水 | red_water | "bright vivid red rust colored water with R channel above 170" |
| 绿水/藻类 | green_water | "thick bright green algae bloom with G channel around 136" |
| 乳白水/泡沫 | milky_foam_water | "milky white gray turbid water with brightness above 145" |
| 坝体渗水 | dam_seepage | v8 流水线: water ∩ dam_concrete + dam>water 约束 |
| 正常水 | normal_water | "clear transparent river water with balanced RGB channels" |

### v8 智能坝体渗水检测

**核心发现**: 坝体渗水场景中 `dam_area > water_area`，误检场景（河道旁混凝土护栏）中 `water_area > dam_area`。

| 参数 | 值 | 说明 |
|------|-----|------|
| `segmentation_threshold` | 0.4 | 水体/坝体分割阈值 |
| `min_overlap` | 0.005 | 渗水区域最小占图像比例 (0.5%) |
| `max_ratio` | 0.3 | 渗水面积不能超过坝体面积的 30% |
| `require_dam_gt_water` | true | 核心约束: 坝体面积 > 水体面积 |

**效果**: F1=84.2%, Precision=88.9%, Recall=80.0%

### 实测结果 (10 张测试图片)

| 图片 | 分类结果 | 置信度 | 异常面积 |
|------|---------|--------|---------|
| test_01.jpg | 红水 | 47.7% | 18.0% |
| test_02.jpg | 绿水/藻类 | 56.4% | 8.9% |
| test_03.jpg | 红水 | 80.1% | 11.7% |
| test_04.jpg | 红水 | 95.0% | 14.9% |
| test_05.jpg | 红水 | 96.6% | 11.2% |
| test_06.jpg | 红水 | 68.0% | 13.0% |
| test_07.jpg | 红水 | 86.5% | 18.2% |
| test_08.jpg | 水质正常 | — | — |
| test_09.jpg | 水质正常 | — | — |
| test_10.jpg | 水质正常 | — | — |

### 具体操作流程

**不需要任何训练数据！** 只需编辑配置文件中的文本提示：

```yaml
# configs/water_inspection.yaml → cloud.radio.classes

cloud:
  radio:
    classes:
      # 你想识别什么，就用文字描述它
      black_water:
        zh: "黑水"
        prompts:
          - "dark black or brown polluted water surface with oil film"
          - "black contaminated water with dark color and poor visibility"

      # 新增一个类别？直接加就行
      oil_spill:
        zh: "油污"
        prompts:
          - "rainbow oil film floating on water surface"
          - "iridescent oil slick on water"
```

**配置完即可使用，无需训练。**

### 如果分割效果不好怎么办？

调整三个参数：

| 参数 | 位置 | 作用 | 调整方法 |
|------|------|------|---------|
| **文本提示** | `classes.*.prompts` | 影响匹配准确性 | 更具体、多角度描述，每个类 2-3 条 |
| **阈值** | `inference.threshold` | 影响分割灵敏度 | 降低 → 检测更多（误检增）；提高 → 更精确（漏检增） |
| **最小面积** | `inference.min_area` | 过滤小区域 | 0.01 = 忽略面积 <1% 的区域 |

### 那数据完全不需要吗？

**C-RADIOv4 分割：不需要训练数据。** 但以下场景可能需要少量参考数据：

| 用途 | 需要数据？ | 说明 |
|------|----------|------|
| 零样本分割推理 | ❌ 不需要 | 配置 prompts 即可 |
| 评估分割效果 | ⚠️ 可选 | 几张真实标注图用于量化 mIoU |
| 优化文本提示 | ⚠️ 可选 | 看实际图调整 prompt 描述 |
| 训练新模型权重 | ❌ 不需要 | C-RADIOv4 使用 NVIDIA 预训练权重，无需微调 |

### 如何验证分割效果？

```bash
# 在 cloud_infer 容器内或本地 GPU 环境中
cd /app  # 或 edge_infer_cloud 项目根目录

# 用真实图片测试
python models/water_inspection/models/open_vocab/radio_segmentor.py \
    --model-path models/water_inspection/checkpoints/model.safetensors \
    --config models/water_inspection/configs/water_inspection.yaml \
    --image your_test_image.jpg \
    --output output_segment.jpg

# 或用端到端测试
python models/water_inspection/tests/test_e2e.py \
    --model-path models/water_inspection/checkpoints/model.safetensors \
    --image your_test_image.jpg
```

### 如何更新/改进模型？

C-RADIOv4 不需要「更新模型权重」。改进方向是：

1. **优化文本提示** — 最直接有效，针对实际场景调整描述
2. **调整阈值参数** — 根据误检/漏检情况微调
3. **等待 NVIDIA 发布新版 RADIO** — 如有新版，替换 safetensors 文件即可

---

## 四、模型加载机制

### 本地文件加载（当前方案）

所有模型文件已下载到本地，完全离线加载：

```
models/
├── NVlabs_RADIO/                          # 官方 RADIO 代码
│   ├── hubconf.py                         # torch.hub 入口
│   └── radio/                             # RADIO 核心包
│       ├── radio_model.py
│       ├── siglip2_adaptor.py
│       └── ...
├── C-RADIOv4-H/                           # C-RADIOv4 权重
│   ├── c-radio_v4-h_half.pth.tar          # 半精度 checkpoint (1.68GB)
│   └── config.json
├── siglip2-giant-opt-patch16-384/         # SigLIP2 文本模型
│   ├── model-00001-of-00002.safetensors   # (7.5GB)
│   ├── tokenizer.json
│   └── config.json
└── water_inspection/
    └── models/open_vocab/
        ├── radio_backbone.py              # backbone 封装
        └── radio_segmentor.py             # 分割器 (分类+分割)
```

### 加载流程

```
1. torch.hub.load(local_code, source='local')
   → 从本地 NVlabs_RADIO 代码加载 RADIO 模型
   → 加载 c-radio_v4-h_half.pth.tar 权重
   → 包含 siglip2-g adaptor

2. Monkey-patch HuggingFace from_pretrained
   → 将 SigLIP2 模型加载重定向到本地目录
   → 支持 AutoModel 和 AutoProcessor 离线加载

3. SigLIP2 完整模型独立加载
   → 用于图像-文本匹配 (水质分类)
   → 包含 logit_scale (4.69) 和 logit_bias (-15.98)
```

### Docker 卷映射

```yaml
# docker-compose.yml
volumes:
  - ../../models/NVlabs_RADIO:/app/models/NVlabs_RADIO:ro
  - ../../models/C-RADIOv4-H:/app/models/C-RADIOv4-H:ro
  - ../../models/siglip2-giant-opt-patch16-384:/app/models/siglip2-giant-opt-patch16-384:ro
  - ../../models/water_inspection/configs:/app/models/water_inspection/configs:ro
```

---

## 五、数据集准备与标注

### 5.1 两类模型的数据需求

| 模型 | 训练数据 | 标注方式 | 标注量 |
|------|---------|---------|--------|
| **YOLOv8** (11类检测) | ✅ **必须** | 边界框 (YOLO格式) | 200-1000张/类 |
| **C-RADIOv4** (5类分割) | ❌ **不需要** | 无需标注 | 零样本 |

### 5.2 YOLOv8 数据集格式

```
data/processed/
├── images/
│   ├── train/    ← 训练图片 (jpg/png)
│   ├── val/      ← 验证图片
│   └── test/     ← 测试图片
└── labels/
    ├── train/    ← 标注文件 (.txt，与图片同名)
    ├── val/
    └── test/
```

**标注格式** (YOLO TXT，每行一个目标):

```
class_id x_center y_center width height
# 所有坐标归一化到 0~1

# 示例:
0 0.5 0.6 0.2 0.3     # person
1 0.4 0.5 0.15 0.25   # fishing_person
7 0.7 0.3 0.1 0.15    # outlet_active
```

### 5.3 水利巡检 11 类标注规范

| ID | 类别 | 英文名 | 标注要点 |
|----|------|--------|---------|
| 0 | 人员 | person | 人体完整边界框 |
| 1 | 钓鱼 | fishing_person | 人 + 鱼竿可见 |
| 2 | 游泳 | swimming_person | 人在水面中 |
| 3 | 嬉水 | playing_person | 人在岸边/浅水 |
| 4 | 闯入 | intruding_person | 人在警戒线内 |
| 5 | 水位尺 | water_gauge | 长条形标尺 |
| 6 | 排污口 | outlet_pipe | 管道出口 |
| 7 | 排污中 | outlet_active | 管道 + 可见水流 |
| 8 | 管道破损 | pipe_damaged | 管道 + 破损处 |
| 9 | 船舶 | boat | 船体 |
| 10 | 漂浮物 | floating_debris | 水面固体漂浮物 |

### 5.4 数据集划分建议

```
训练集 : 验证集 : 测试集 = 7 : 1.5 : 1.5
```

每类建议样本数：

| 难度 | 类别 | 建议样本数 |
|------|------|----------|
| 易 | person, boat, water_gauge | 500-1000 |
| 中 | fishing, swimming, floating_debris | 300-500 |
| 难 | outlet_active, pipe_damaged | 200-300 |

### 5.5 数据来源

| 类别 | 推荐来源 | 说明 |
|------|---------|------|
| person, boat | COCO / VisDrone | 公开数据集直接使用 |
| fishing/swimming | 现场采集 | 需实拍 |
| pipe_damaged | 3D 渲染增强 | 样本稀缺 |
| water_gauge | 现场采集 | 固定设施 |
| water_quality | **不需要** | C-RADIOv4 零样本 |

### 5.6 准备好数据后的操作

```bash
# 1. 将图片和标注放入对应目录
cp your_images/* data/processed/images/train/
cp your_labels/* data/processed/labels/train/

# 2. 检查数据完整性
python scripts/analyze_data.py --data data/processed

# 3. 开始训练（见下一节）
```

---

## 六、训练与验证

### 6.1 YOLOv8 训练

```bash
# 在 training 容器内或本地 GPU 环境
python models/yolo/train.py \
    --config configs/water_inspection.yaml \
    --data data/processed/data.yaml \
    --epochs 300 \
    --batch 12 \
    --device 0
```

**关键参数** (`configs/water_inspection.yaml`):

```yaml
training:
  yolo:
    epochs: 300
    batch: 12
    optimizer: "AdamW"
    lr0: 0.001
    warmup_epochs: 5
    patience: 50          # 早停耐心值
    augment:
      hsv_h: 0.015        # 色调增强
      hsv_s: 0.7          # 饱和度增强
      mosaic: 1.0         # Mosaic 混合
      mixup: 0.1          # MixUp 混合
```

**预期结果**: mAP@50 ≥ 0.80

### 6.2 C-RADIOv4 验证（非训练）

C-RADIOv4 **不需要训练**，但需要验证分割效果：

```bash
# 用真实图片验证
python models/water_inspection/tests/test_e2e.py \
    --model-path checkpoints/model.safetensors \
    --image your_real_photo.jpg

# 输出示例:
# 分割结果: 2 个区域
#   黑水 (black_water): 面积=5.2%, 置信度=0.782
#   绿水 (green_water): 面积=12.1%, 置信度=0.653
```

**验证清单**:

| 检查项 | 方法 | 通过标准 |
|--------|------|---------|
| 漏检率 | 用真实污染图片测试 | 主要污染区域能检出 |
| 误检率 | 用正常水面图片测试 | 不应误报为污染 |
| 边界质量 | 可视化 mask 检查 | 分割边界合理 |
| 面积估算 | 与人工估算对比 | 误差 <20% |

**如果效果不好**，调整提示词（见第三章），不需要重新训练。

### 6.3 模型导出（YOLOv8 → ONNX）

```bash
# 训练完成后导出
python deployment/export_onnx.py \
    --weights runs/train/exp/weights/best.pt \
    --output water_inspection.onnx \
    --imgsz 640

# 生成边缘推理平台配置
python deployment/generate_config.py \
    --project water_inspection \
    --output models/
```

**交付物**:

| 文件 | 格式 | 用途 |
|------|------|------|
| `*.onnx` | ONNX | 模型权重（边缘端自动转 TensorRT Engine） |
| `*_config.json` | JSON | model_config.json 配置片段 |
| `*.names` | 文本 | 类别名称列表 |
| `*_rules.json` | JSON | 报警规则 |

---

## 七、部署指南

### 7.1 Docker Compose 部署（推荐）

```bash
cd deployment/docker

# 基础服务
docker compose up -d

# 含 GPU 的服务（训练 + 云端推理）
docker compose --profile gpu up -d

# 仅重启云端推理（修改配置后）
docker compose --profile gpu restart cloud_infer

# 查看云端推理日志
docker compose logs -f cloud_infer
```

### 7.2 云端推理服务环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MQTT_BROKER_URL` | `tcp://emqx:1883` | MQTT Broker 地址 |
| `MQTT_USERNAME` | `admin` | MQTT 用户名 |
| `MQTT_PASSWORD` | `admin123456` | MQTT 密码 |
| `RADIO_CODE_DIR` | `/app/models/NVlabs_RADIO` | RADIO 官方代码目录 |
| `RADIO_CHECKPOINT_PATH` | `/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar` | C-RADIOv4 权重路径 |
| `SIGLIP2_DIR` | `/app/models/siglip2-giant-opt-patch16-384` | SigLIP2 文本模型目录 |
| `CONFIG_PATH` | `configs/water_inspection.yaml` | 配置文件路径 |
| `DEVICE` | `cuda` | 推理设备 |
| `INPUT_SIZE` | `896` | 输入尺寸（16 的倍数） |
| `ALERT_MIN_AREA` | `0.01` | 报警最小面积占比 |

### 7.3 边缘端 (Jetson) 部署

```bash
# 1. 通过 OTA 推送 ONNX 模型到边缘设备
#    (在后端 API 或通过 MQTT 命令触发)

# 2. 边缘设备自动: 下载 ONNX → 校验 MD5 → 转换 TensorRT Engine → 热加载

# 3. 验证
#    边缘推理平台自动加载新模型，无需手动操作
```

---

## 八、推理服务

### 8.1 MQTT 通信协议

| Topic | 方向 | 用途 |
|-------|------|------|
| `device/{id}/cloud/frame` | 边缘 → 云端 | 上传关键帧 |
| `device/{id}/cloud/result` | 云端 → 边缘 | 回传分割结果 |
| `device/{id}/ota/command` | 云端 → 边缘 | OTA 模型更新命令 |
| `device/{id}/ota/status` | 边缘 → 云端 | OTA 更新状态 |

### 8.2 请求格式（关键帧上传）

```json
{
  "device_id": "jetson-001",
  "frame_id": 12345,
  "timestamp": "2026-04-01T10:00:00",
  "image": "<base64 JPEG>",
  "classes": ["black_water", "green_water"]
}
```

### 8.3 响应格式（分割结果回传）

```json
{
  "device_id": "jetson-001",
  "frame_id": 12345,
  "timestamp": "2026-04-01T10:00:00.123",
  "segments": {
    "black_water": {
      "area": 0.05,
      "score": 0.82,
      "bbox": [120, 200, 450, 380],
      "class_name_cn": "黑水"
    }
  },
  "alerts": [
    {
      "class_name": "black_water",
      "class_name_cn": "黑水",
      "level": "critical",
      "message": "黑水污染，面积占比 5.0%"
    }
  ],
  "inference_time_ms": 150.5
}
```

### 8.4 Python API 接口

```python
from models.water_inspection.models.unified import (
    UnifiedWaterInspectionSystem,
    create_system,
    detect_single_image
)

# 方式 1: 便捷函数 (推荐)
results = detect_single_image(
    image_path="test.jpg",
    config_path="configs/water_inspection.yaml",
    output_path="output.jpg"
)

# 方式 2: 系统实例 (批量处理)
system = create_system("configs/water_inspection.yaml")

# 统一检测（YOLO + v8 水质流水线）
results = system.detect(image_bgr, run_water_quality=True)

# 结果结构
results["detections"]      # YOLO 检测结果 [Detection(class_id, class_name, confidence, bbox)]
results["water_quality"]   # v8 水质检测结果
  ├── detected_classes     # 检测到的类别列表
  ├── detected_classes_cn  # 中文类名
  ├── has_seepage          # 是否检测到坝体渗水
  ├── water_mask           # 水体掩码
  ├── dam_mask             # 坝体掩码
  └── seepage_mask         # 渗水掩码
results["alerts"]          # 报警 [Alert(alert_type, class_name, message, level)]

# 可视化
vis_image = system.visualize(image_bgr, results, "output.jpg")

# 命令行使用
python models/water_inspection/models/unified.py \
    --config configs/water_inspection.yaml \
    --image test.jpg \
    --output result.jpg
```

---

## 九、三大场景差异化设计

| 维度 | 水利巡检 | 园区监测 | 施工安全 |
|------|---------|---------|---------|
| **边缘模型** | YOLOv8-Pose (11类) | YOLOv8-Pose + OBB (12+1类) | YOLOv8-Pose (15类) |
| **云端模型** | **C-RADIOv4 (5类分割)** | 无 | 无 |
| **MQTT 联动** | 开启 | 关闭 | 关闭 |
| **训练数据** | YOLO 需要，C-RADIOv4 不需要 | YOLO 需要 | YOLO 需要 |

### 9.1 水利巡检（11 检测 + 7 水质分类）

**边缘检测 (YOLOv8, 11 类)**: person, fishing, swimming, playing, intruding, water_gauge, outlet_pipe, outlet_active, pipe_damaged, boat, floating_debris

**云端分割 (C-RADIOv4 + SigLIP2, v8 流水线)**:

| 类别 | 中文名 | 检测方式 |
|------|--------|---------|
| black_water | 黑水 | RADSeg 分割 + SVM 分类 |
| turbid_water | 浑浊水 | RADSeg 分割 + SVM 分类 |
| red_water | 红水 | RADSeg 分割 + SVM 分类 |
| green_water | 绿水/藻类 | RADSeg 分割 + SVM 分类 |
| milky_foam_water | 乳白水/泡沫 | RADSeg 分割 + SVM 分类 |
| dam_seepage | 坝体渗水 | **v8 流水线** (water ∩ dam_concrete + dam>water 约束) |
| normal_water | 正常水 | 背景类 |

**v8 坝体渗水检测参数** (见 `configs/water_inspection.yaml`):

```yaml
v8_pipeline:
  segmentation_threshold: 0.4
  seepage:
    min_overlap: 0.005          # 渗水区域最小占图像比例 (0.5%)
    max_ratio: 0.3              # 渗水面积不超过坝体面积 30%
    require_dam_gt_water: true  # 核心约束: 坝体面积 > 水体面积
  multi_label:
    enabled: true
    threshold: 0.3              # 多标签检测阈值
```

### 9.2 园区监测（12 检测 + 1 OBB）

**检测 (YOLOv8, 12 类)**:
- P0 紧急: 非法闯入、翻越围墙、破窗盗窃、撬门盗窃、人员摔倒、打架斗殴、车辆闯入
- P1 警告: 违规吸烟、异常徘徊、违停车辆
- P2 提示: 快速奔跑、车辆计数

**OBB (YOLOv8-Obb, 1 类)**: parking_spot（停车位旋转框）

### 9.3 施工安全（15 检测）

**检测 (YOLOv8, 15 类)**:
- P0 紧急: 未戴安全帽、进入危险区、攀爬、坠落、违规用火、不安全距离、跨越警戒线
- P1 严重: 未穿反光衣、脱岗作业、非授权人员
- P2 提示: 塔吊/挖掘机/运输车作业

---

## 十、工程化保障

### 10.1 双平台技术栈

| 维度 | 云边协同平台 (Python) | 边缘推理平台 (C++) |
|------|----------------------|-------------------|
| 语言 | Python (PyTorch) | C++ (TensorRT) |
| 职责 | 训练、验证、导出、云端推理 | 实时推理、插件处理、OTA |
| 模型格式 | .pt → .onnx | .onnx → .engine (FP16) |
| 通信 | MQTT / HTTP API | MQTT |
| 配置 | YAML | JSON |
| 扩展 | 新增场景目录 | 新增 Plugin (.so) |

### 10.2 性能指标

| 指标 | 边缘 (Jetson Orin NX) | 云端 (RTX 4090/A10) |
|------|----------------------|---------------------|
| 推理 | YOLO 30+ FPS (FP16) | C-RADIOv4 5-10 FPS |
| 显存 | ≤ 4GB | ≤ 24GB |
| 延迟 | ≤ 35ms/帧 | ≤ 200ms/帧 |
| 功耗 | ≤ 20W | — |

### 10.3 OTA 模型更新流程

```
云边协同平台 → MQTT Broker → 边缘推理平台
     │              │              │
     │ OTA 命令     │              │
     ├─────────────→│─────────────→│ 下载 ONNX
     │              │              │ MD5 校验
     │              │              │ ONNX → Engine
     │              │              │ 热加载
     │              │←─────────────│ 上报状态
```

---

## 十一、常见问题

### Q1: C-RADIOv4 零样本分割需要什么数据？

**不需要任何训练数据。** 只需要在配置文件中用自然语言描述目标（text prompts），模型会自动将文本与图像匹配。这是 C-RADIOv4 集成 SigLIP2-g adaptor 的核心能力。

### Q2: 零样本分割效果能达到什么水平？

对于有明显颜色/纹理特征的目标（如黑水、绿水），零样本效果已经很好。对于与背景高度相似的目标，可以通过优化文本提示来提高。

### Q3: 如何新增一个分割类别？

编辑 `configs/water_inspection.yaml`，在 `cloud.radio.classes` 下添加：

```yaml
oil_spill:
  zh: "油污"
  color_hint: [100, 150, 180]   # BGR 颜色参考
  use_color_check: true
  prompts:
    - "rainbow iridescent oil film on water surface"
    - "oil spill floating on water with colorful reflection"
  alert:
    enabled: true
    level: warning
    description: 发现油污，可能存在泄漏
```

保存后重启 `cloud_infer` 服务即可。

### Q4: 坝体渗水检测为什么用 dam>water 约束？

**原理**: 坝体渗水场景中，坝体是主体结构，水体是渗出的一小部分；误检场景（如河道旁混凝土护栏）中，水体是主体，坝体是护栏。

| 场景 | dam_area | water_area | 结果 |
|------|----------|------------|------|
| 真实渗水 | 大 | 小 | ✅ 检出 |
| 河道护栏 | 小 | 大 | ❌ 过滤 |

实测效果: F1=84.2%, Precision=88.9%, Recall=80.0%

### Q5: C-RADIOv4 + SigLIP2 如何协同工作？

**v8 流水线** (当前方案):

1. **Stage 1: RADSeg 分割** — 计算 water 和 dam_concrete 的空间热力图
2. **Stage 2: 渗水分析** — water ∩ dam_concrete + dam>water 约束
3. **Stage 3: 水质分类** — SVM 分类器 (67 维特征: BGR/HSV 统计 + 颜色直方图 + 颜色距离)

### Q6: 所有模型文件需要多大空间？

| 文件 | 大小 | 说明 |
|------|------|------|
| c-radio_v4-h_half.pth.tar | 1.68 GB | C-RADIOv4 权重 (半精度) |
| siglip2-giant model weights | 7.5 GB | SigLIP2 文本+视觉模型 |
| NVlabs_RADIO 代码 | ~1 MB | 官方 RADIO Python 包 |
| **总计** | **~9.2 GB** | |

### Q7: 为什么水质分割放云端而非边缘？

1. 水质分割模型 (C-RADIOv4 ViT-H) 有 630M 参数，Jetson 无法实时运行
2. 水质变化较慢，每 30 帧分析一次即可（10 FPS），不需要每帧都做
3. 云端 GPU 有足够显存运行大模型
4. 边缘只做 YOLO 快速检测（30 FPS），延迟更低

### Q8: 如何快速上手？

```bash
# 1. 安装依赖
pip install torch ultralytics opencv-python pyyaml

# 2. 下载模型 (首次运行)
# C-RADIOv4-H, SigLIP2-giant 需要手动下载到 models/ 目录

# 3. 运行检测
python models/water_inspection/models/unified.py \
    --config models/water_inspection/configs/water_inspection.yaml \
    --image your_test.jpg \
    --output result.jpg
```

### Q9: Docker 缓存在本地哪个目录？

```
D:\github\edge_infer_cloud\models\pretrained_models\
```

通过 docker-compose bind mount 映射到容器内 `/root/.cache/`。首次下载后持久化，容器重建不会丢失。

---

## 附录 A: 实施计划（8 周）

| 周次 | 核心任务 | 执行人 |
|------|---------|--------|
| W1-2 | YOLO 数据标注 + 训练/验证（三大场景） | 算法 |
| W3 | ONNX 导出 + 配置生成 | 算法 |
| W4 | C-RADIOv4 提示词调优 + 云端推理服务 | 算法 |
| W5 | C++ Plugin 开发（参考 helmet_detect） | 软件 |
| W6 | OTA 联调 + 云边 MQTT 联动 | 联合 |
| W7 | 功能测试 + 性能优化 | 全员 |
| W8 | 现场部署 + 验收 | 全员 |

## 附录 B: 依赖清单

**边缘推理平台 (C++)**:
TensorRT 8.6+, OpenCV 4.8+, mosquitto, libcurl, jsoncpp, FFmpeg

**云边协同平台 (Python)**:
torch>=2.0.0, ultralytics>=8.0.180, paho-mqtt>=1.6.0, transformers>=4.36.0, safetensors>=0.4.0, opencv-python>=4.8.0, pyyaml>=6.0
