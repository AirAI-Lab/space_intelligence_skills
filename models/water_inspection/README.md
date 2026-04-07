# 水利巡检模块 (Water Inspection) v3.4

> **版本**: v3.4 | **更新**: 2026-04-07

整合 C-RADIOv4 + YOLO 云边协同方案，支持 11 类目标检测 + 7 类水质分割。

## 目录结构

```
models/water_inspection/
├── configs/
│   └── water_inspection.yaml          # v3.4 统一配置文件
├── models/
│   ├── unified.py                     # 🔥 统一检测入口 (开箱即用)
│   ├── open_vocab/
│   │   ├── radseg_segmentor.py        # RADSeg v8 分割流水线
│   │   ├── radio_backbone.py          # C-RADIOv4 ViT-H backbone
│   │   └── core/
│   │       └── backbone.py            # backbone 核心实现
│   ├── classifier/
│   │   ├── lightweight_classifier.pkl # SVM 水质分类器
│   │   └── scaler.pkl                 # 特征标准化器
│   └── yolo/                          # YOLOv8 训练/推理 (可选)
├── scripts/
│   ├── evaluate_pipeline_v8_production.py  # v8 评估脚本
│   ├── train_lightweight_classifier.py     # 分类器训练
│   └── _archive_v7/                       # 历史脚本归档
├── data/
│   ├── datasets/                      # 数据集
│   └── processed/                     # 处理后数据
├── outputs/                           # 输出结果
└── docs/                              # 文档
```

## 快速开始

### 统一检测接口 (推荐)

```python
from models.water_inspection.models.unified import (
    UnifiedWaterInspectionSystem,
    create_system,
    detect_single_image
)

# 方式 1: 便捷函数
results = detect_single_image(
    image_path="test.jpg",
    config_path="configs/water_inspection.yaml",
    output_path="output.jpg"
)

# 方式 2: 系统实例
system = create_system("configs/water_inspection.yaml")
results = system.detect(image_bgr)

# 查看结果
print(f"YOLO 检测: {len(results['detections'])} 个")
print(f"水质检测: {results['water_quality']['detected_classes_cn']}")
print(f"报警: {len(results['alerts'])} 个")
```

### 命令行使用

```bash
python models/water_inspection/models/unified.py \
    --config models/water_inspection/configs/water_inspection.yaml \
    --image test.jpg \
    --output result.jpg
```

## 核心功能

### 1. YOLOv8 目标检测 (11 类)

| ID | 类别 | 说明 |
|----|------|------|
| 0 | person | 人员 |
| 1 | fishing_person | 钓鱼 |
| 2 | swimming_person | 游泳 |
| 3 | playing_person | 嬉水 |
| 4 | intruding_person | 闯入 |
| 5 | water_gauge | 水位尺 |
| 6 | outlet_pipe | 排污口 |
| 7 | outlet_active | 排污中 |
| 8 | pipe_damaged | 管道破损 |
| 9 | boat | 船舶 |
| 10 | floating_debris | 漂浮物 |

### 2. C-RADIOv4 水质分割 (7 类)

| 类别 | 中文名 | 检测方式 |
|------|--------|---------|
| black_water | 黑水 | RADSeg + SVM |
| turbid_water | 浑浊水 | RADSeg + SVM |
| red_water | 红水 | RADSeg + SVM |
| green_water | 绿水/藻类 | RADSeg + SVM |
| milky_foam_water | 乳白水/泡沫 | RADSeg + SVM |
| dam_seepage | 坝体渗水 | v8 流水线 (dam>water 约束) |
| normal_water | 正常水 | 背景类 |

### 3. v8 智能坝体渗水检测

**核心约束**: `dam_area > water_area`

| 参数 | 值 | 说明 |
|------|-----|------|
| segmentation_threshold | 0.4 | 水体/坝体分割阈值 |
| min_overlap | 0.005 | 渗水区域最小占图像比例 (0.5%) |
| max_ratio | 0.3 | 渗水面积不超过坝体面积 30% |
| require_dam_gt_water | true | 坝体面积 > 水体面积 |

**效果**: F1=84.2%, Precision=88.9%, Recall=80.0%

## 配置文件

主要配置在 `configs/water_inspection.yaml`:

```yaml
cloud:
  radio:
    v8_pipeline:
      segmentation_threshold: 0.4
      seepage:
        min_overlap: 0.005
        max_ratio: 0.3
        require_dam_gt_water: true
      multi_label:
        enabled: true
        threshold: 0.3

edge:
  yolo:
    inference:
      conf_threshold: 0.25
      iou_threshold: 0.45
```

## 训练分类器

```bash
cd models/water_inspection/scripts
python train_lightweight_classifier.py
```

## 评估脚本

```bash
# 评估 v8 流水线
python scripts/evaluate_pipeline_v8_production.py \
    --config configs/water_inspection.yaml \
    --output_dir outputs/pipeline_v8_production
```

## 云边协同架构

```
边缘设备 (Jetson)                     云端 (GPU Server)
┌─────────────────┐    MQTT     ┌──────────────────────┐
│  YOLOv8 检测     │ ─────────→ │  C-RADIOv4 + SigLIP2  │
│  11类 · 30FPS    │ 关键帧上传  │  7类 · v8 流水线      │
│  本地实时报警    │ ←───────── │  分类 + 渗水检测       │
└─────────────────┘  分割结果    └──────────────────────┘
```

## 更新历史

- 2026-04-07: v3.4 - 统一检测入口 (unified.py), v8 流水线参数配置化
- 2026-04-06: v3.3 - 代码结构整理，移动核心文件到 models/water_inspection
- 2026-04-05: v3.2 - 完成 v8 智能坝体渗水检测，F1=84%
- 2026-04-04: v3.1 - 代码架构重构，统一为 7 类水质检测
