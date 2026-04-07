# 边缘推理云 - 项目总览

**版本**: v3.4
**更新**: 2026-04-07

---

## 项目列表

本项目包含三个智能检测系统：

### 智能检测系统

| 项目 | 类别 | 模型 | 状态 |
|------|------|------|------|
| **水利巡检** | 18类 (11检测+7水质) | YOLOv8-Pose + C-RADIOv4 + SigLIP2 | ✅ 完成 |
| **园区监测** | 13类 (12检测+1 OBB) | YOLOv8-Pose + YOLOv8-Obb | ✅ 完成 |
| **施工安全** | 15类 (全检测) | YOLOv8-Pose | ✅ 完成 |

---

## 快速开始

### 水利巡检 (推荐)

```bash
cd models/water_inspection

# 统一检测接口
python models/unified.py \
    --config configs/water_inspection.yaml \
    --image test.jpg \
    --output result.jpg
```

### Python API

```python
from models.water_inspection.models.unified import create_system, detect_single_image

# 便捷函数
results = detect_single_image("test.jpg", output_path="output.jpg")

# 或使用系统实例
system = create_system("configs/water_inspection.yaml")
results = system.detect(image_bgr)
```

### YOLO 训练

```bash
python models/water_inspection/models/yolo/train.py \
    --config configs/water_inspection.yaml \
    --data data/processed/data.yaml \
    --epochs 300
```

---

## 项目结构

```
models/
├── NVlabs_RADIO/                    # RADIO 官方代码
├── C-RADIOv4-H/                     # C-RADIOv4 权重
├── siglip2-giant-opt-patch16-384/   # SigLIP2 文本模型
├── water_inspection/                # 水利巡检 (v3.4)
│   ├── configs/water_inspection.yaml    # 统一配置
│   ├── models/
│   │   ├── unified.py                   # 统一检测入口
│   │   ├── open_vocab/                  # C-RADIOv4 分割
│   │   └── classifier/                  # SVM 分类器
│   └── scripts/
├── park_monitoring/                 # 园区监测
├── construction_safety/             # 施工安全
└── deployment/                      # 部署配置
```

---

## 核心功能

### 水利巡检 (v3.4)

**云边协同架构**:

```
边缘设备 (Jetson)                     云端 (GPU Server)
┌─────────────────┐    MQTT     ┌──────────────────────┐
│  YOLOv8 检测     │ ─────────→ │  C-RADIOv4 + SigLIP2  │
│  11类 · 30FPS    │ 关键帧上传  │  7类 · v8 流水线      │
│  本地实时报警    │ ←───────── │  分类 + 渗水检测       │
└─────────────────┘  分割结果    └──────────────────────┘
```

**v8 智能坝体渗水检测**:
- 核心约束: `dam_area > water_area`
- 效果: F1=84.2%, Precision=88.9%, Recall=80.0%

### 通用功能

- ✅ YOLOv8-Pose 训练/推理
- ✅ ONNX 导出
- ✅ 数据准备与增强
- ✅ 模型评估

---

## 依赖

**核心依赖**:

```txt
torch>=2.0.0
ultralytics>=8.0.180
opencv-python>=4.8.0
pyyaml>=6.0
transformers>=4.36.0
safetensors>=0.4.0
```

---

## 性能指标

| 项目 | 边缘 (YOLO) | 云端 (分割) |
|------|-------------|-------------|
| 水利巡检 | 30+ FPS | 5-10 FPS |
| 园区监测 | 30+ FPS | - |
| 施工安全 | 30+ FPS | - |

---

## 文档

- [C-RADIOv4 + YOLO 云边协同方案](C-RADIOv4%20+%20YOLO%20云边协同方案.md)
- [水利巡检手册](water_inspection/README.md)
- [部署接口](deployment/INTERFACE.md)

---

**团队**: 空中智能体团队
