# 跨部门算法实施指南（完整版）

> **版本**: V1.0
> **日期**: 2026-03-09
> **目标**: 为所有9个业务部门提供可执行的实施路径、模型交付标准和集成方案
> **适用对象**: 算法工程师、软件工程师、产品工程师

---

## 📋 目录

1. [总览](#1-总览)
2. [模型交付标准](#2-模型交付标准)
3. [9个部门实施策略](#3-9个部门实施策略)
4. [松耦合集成方案](#4-松耦合集成方案)
5. [开发人员工作流程](#5-开发人员工作流程)
6. [质量控制与验收](#6-质量控制与验收)

---

## 1. 总览

### 1.1 部门优先级排序

| 排名 | 部门 | 年度预算 | 算法数 | 实施周期 | 优先级 | 负责人 |
|------|------|----------|--------|---------|--------|--------|
| 1 | **应急管理** | ¥50-100万 | 12种 | 2个月 | **P0** | 算法工程师A |
| 2 | **住建建筑** | ¥5-20万/工地 | 15种 | 2个月 | **P0** | 算法工程师B |
| 3 | **城管部门** | ¥30-100万 | 15种 | 3个月 | **P1** | 算法工程师C |
| 4 | **国土资源** | ¥30-200万 | 10种 | 3个月 | **P1** | 算法工程师A |
| 5 | **环保部门** | ¥20-60万 | 12种 | 3个月 | **P1** | 算法工程师B |
| 6 | **电力部门** | ¥10-50万 | 10种 | 3个月 | **P2** | 算法工程师C |
| 7 | **水利部门** | ¥10-60万 | 10种 | 3个月 | **P2** | 算法工程师A |
| 8 | **农业部门** | ¥10-50万 | 12种 | 3个月 | **P2** | 算法工程师B |
| 9 | **交通部门** | ¥10-40万 | 8种 | 3个月 | **P2** | 算法工程师C |

---

### 1.2 实施原则

```
核心原则：
1. MVP优先（每个部门先实现2-5种核心算法）
2. 渐进式扩展（V1.0 → V2.0 → V3.0）
3. 复用现有能力（优先使用已有模型）
4. 松耦合集成（独立插件，灵活组合）
5. 标准化交付（统一的模型格式和配置）
```

---

### 1.3 技术栈统一

| 层次 | 技术选型 | 说明 |
|------|---------|------|
| **训练框架** | Ultralytics YOLOv8 | 统一训练框架 |
| **模型格式** | .pt (PyTorch) + .onnx | 支持推理和转换 |
| **推理引擎** | TensorRT (边缘) + ONNXRuntime (云端) | 统一推理引擎 |
| **插件框架** | edge_infer plugin system | 松耦合架构 |
| **配置管理** | YAML + JSON | 统一配置格式 |

---

## 2. 模型交付标准

### 2.1 目录结构

每个部门交付的模型必须遵循以下目录结构：

```
models/{department}/
├── v1.0/                           # 版本号
│   ├── weights/                    # 权重文件
│   │   ├── best.pt                 # 最佳模型权重 ✅ 必须
│   │   ├── last.pt                 # 最后一个epoch ⚠️ 可选
│   │   ├── epoch{N}.pt             # checkpoint ⚠️ 可选（关键epoch）
│   │   ├── best.onnx               # ONNX格式 ✅ 必须（边缘部署）
│   │   └── best.engine             # TensorRT引擎 ✅ 必须（边缘部署）
│   ├── config/                     # 配置文件
│   │   ├── model_config.json       # 模型配置 ✅ 必须
│   │   ├── data.yaml               # 数据集配置 ✅ 必须
│   │   ├── train_config.yaml       # 训练配置 ⚠️ 可选
│   │   └── inference_config.yaml   # 推理配置 ✅ 必须
│   ├── docs/                       # 文档
│   │   ├── README.md               # 模型说明 ✅ 必须
│   │   ├── MODEL_CARD.md           # 模型卡片 ✅ 必须
│   │   ├── TRAINING_LOG.md         # 训练日志 ⚠️ 可选
│   │   └── PERFORMANCE.md          # 性能报告 ✅ 必须
│   ├── test/                       # 测试数据
│   │   ├── test_images/            # 测试图片
│   │   ├── test_results/           # 测试结果
│   │   └── test_report.json        # 测试报告
│   └── plugin/                     # 插件代码（edge_infer）
│       ├── __init__.py
│       ├── config.yaml
│       ├── detector.py
│       ├── postprocess.py
│       └── utils.py
```

---

### 2.2 配置文件格式

#### **2.2.1 model_config.json**（必须）

```json
{
  "model_id": "M_EMERGENCY_V1.0_20260315",
  "model_type": "YOLOv8",
  "base_model": "yolov8m.pt",
  "version": "1.0.0",
  
  "architecture": {
    "type": "YOLOv8 Detection",
    "input_size": [640, 640],
    "num_classes": 5,
    "classes": {
      "0": "landslide",
      "1": "mudslide",
      "2": "flood",
      "3": "forest_fire",
      "4": "smoke"
    },
    "task": "detection",
    "backbone": "CSPDarknet53",
    "neck": "PANet",
    "head": "Decoupled Head"
  },
  
  "training": {
    "epochs": 100,
    "batch_size": 16,
    "img_size": 640,
    "optimizer": "AdamW",
    "lr0": 0.01,
    "lr_scheduler": "cosine",
    "weight_decay": 0.0005,
    "augmentation": {
      "mosaic": true,
      "mixup": 0.1,
      "hsv_h": 0.015,
      "hsv_s": 0.7,
      "hsv_v": 0.4
    },
    "dataset_id": "DS_EMERGENCY_20260310",
    "train_samples": 2000,
    "val_samples": 300,
    "test_samples": 300
  },
  
  "metrics": {
    "map50_95": 0.65,
    "map50": 0.88,
    "precision": 0.87,
    "recall": 0.85,
    "f1": 0.86,
    "final_loss": 0.25,
    "best_epoch": 89
  },
  
  "performance": {
    "edge_inference_time_ms": 45,
    "edge_device": "Jetson Orin NX 16GB",
    "edge_fps": 22,
    "cloud_inference_time_ms": 30,
    "cloud_device": "RTX 4090",
    "model_size_mb": 52
  },
  
  "files": {
    "pytorch": "weights/best.pt",
    "onnx": "weights/best.onnx",
    "tensorrt": "weights/best.engine",
    "config": "config/model_config.json"
  },
  
  "usage": {
    "inference": "from ultralytics import YOLO; model = YOLO('weights/best.pt'); results = model('image.jpg')",
    "export_onnx": "model.export(format='onnx', imgsz=640, simplify=True)",
    "export_tensorrt": "trtexec --onnx=weights/best.onnx --saveEngine=weights/best.engine --fp16",
    "requirements": "ultralytics>=8.0.0, tensorrt>=8.6.0"
  },
  
  "deployment": {
    "target": "edge",
    "device": "jetson_orin_nx",
    "memory_footprint_mb": 400,
    "supported_precisions": ["fp32", "fp16", "int8"]
  },
  
  "metadata": {
    "author": "算法工程师A",
    "department": "应急管理",
    "created_date": "2026-03-15",
    "updated_date": "2026-03-15",
    "status": "production",
    "tags": ["emergency", "disaster", "real-time"]
  }
}
```

---

#### **2.2.2 data.yaml**（必须）

```yaml
# 数据集配置
dataset:
  name: "Emergency Disaster Dataset V1.0"
  version: "1.0.0"
  description: "应急管理部门灾害检测数据集"
  
paths:
  train: "data/emergency/train/images"
  val: "data/emergency/val/images"
  test: "data/emergency/test/images"
  
classes:
  names:
    - landslide      # 山体滑坡
    - mudslide       # 泥石流
    - flood          # 洪涝灾害
    - forest_fire    # 森林火灾
    - smoke          # 烟雾
  num: 5
  
annotation:
  format: "YOLO"
  # YOLO格式：class_id center_x center_y width height (归一化)
  
augmentation:
  enabled: true
  methods:
    - mosaic: 0.5
    - mixup: 0.1
    - hsv_h: 0.015
    - hsv_s: 0.7
    - hsv_v: 0.4
    - flipud: 0.0
    - fliplr: 0.5
    
statistics:
  train_samples: 2000
  val_samples: 300
  test_samples: 300
  class_distribution:
    landslide: 400
    mudslide: 300
    flood: 400
    forest_fire: 600
    smoke: 300
```

---

#### **2.2.3 inference_config.yaml**（必须）

```yaml
# 推理配置
inference:
  model:
    path: "weights/best.engine"
    type: "tensorrt"
    precision: "fp16"
    
  input:
    size: [640, 640]
    normalize: true
    mean: [0, 0, 0]
    std: [255, 255, 255]
    
  output:
    confidence_threshold: 0.5
    nms_threshold: 0.4
    max_detections: 100
    
  postprocess:
    enabled: true
    filter_small_objects: true
    min_object_area: 100  # 像素
    
deployment:
  device: "cuda:0"
  batch_size: 1
  num_workers: 2
  
logging:
  enabled: true
  level: "INFO"
  save_results: true
  output_dir: "logs/inference/"
```

---

### 2.3 模型卡片模板

**MODEL_CARD.md**:

```markdown
# 模型卡片：Emergency Disaster Detection V1.0

## 模型概述
- **模型ID**: M_EMERGENCY_V1.0_20260315
- **版本**: 1.0.0
- **类型**: 目标检测
- **任务**: 应急灾害检测（5类）

## 模型详情
- **基础模型**: YOLOv8-m
- **输入尺寸**: 640×640
- **类别数**: 5类（滑坡、泥石流、洪涝、火灾、烟雾）
- **训练数据**: 2,000张训练集
- **训练时间**: 100 epochs

## 性能指标
| 指标 | 数值 |
|------|------|
| mAP@0.5 | 0.88 |
| mAP@0.5:0.95 | 0.65 |
| Precision | 0.87 |
| Recall | 0.85 |
| F1 Score | 0.86 |
| 推理时间 (Jetson) | 45ms |
| FPS | 22 |

## 使用场景
- ✅ 实时灾害监测
- ✅ 应急救援指挥
- ✅ 灾害预警系统

## 限制与注意事项
- ⚠️ 训练数据主要来自中国地区，其他地区可能需要微调
- ⚠️ 夜间场景精度可能下降10-15%
- ⚠️ 极端天气（暴雨、浓雾）可能影响检测效果

## 训练细节
- **优化器**: AdamW
- **学习率**: 0.01 (初始)
- **学习率策略**: Cosine Annealing
- **数据增强**: Mosaic, MixUp, HSV调整

## 评估结果
- **训练集**: mAP@0.5 = 0.90
- **验证集**: mAP@0.5 = 0.88
- **测试集**: mAP@0.5 = 0.86

## 引用
如果使用此模型，请引用：
```
@misc{emergency_disaster_v1.0,
  author = {算法工程师A},
  title = {Emergency Disaster Detection Model V1.0},
  year = {2026},
  publisher = {SkyEdge AI}
}
```

## 联系方式
- **负责人**: 算法工程师A
- **邮箱**: algo-a@skyedge.ai
- **更新日期**: 2026-03-15
```

---

### 2.4 开发人员交付清单

每个部门模型交付时，必须包含以下文件：

| 文件 | 格式 | 必须 | 说明 |
|------|------|------|------|
| **best.pt** | PyTorch权重 | ✅ | 最佳模型权重 |
| **best.onnx** | ONNX模型 | ✅ | ONNX格式（用于转换）|
| **best.engine** | TensorRT引擎 | ✅ | TensorRT引擎（边缘部署）|
| **model_config.json** | JSON | ✅ | 模型配置 |
| **data.yaml** | YAML | ✅ | 数据集配置 |
| **inference_config.yaml** | YAML | ✅ | 推理配置 |
| **README.md** | Markdown | ✅ | 模型说明 |
| **MODEL_CARD.md** | Markdown | ✅ | 模型卡片 |
| **PERFORMANCE.md** | Markdown | ✅ | 性能报告 |
| **test_report.json** | JSON | ✅ | 测试报告 |
| **plugin/** | Python代码 | ✅ | edge_infer插件 |

---

## 3. 9个部门实施策略

### 3.1 应急管理部门

**负责人**: 算法工程师A
**优先级**: P0
**预算**: ¥50-100万/年
**实施周期**: 2个月

---

#### 3.1.1 算法清单

**V1.0 - MVP版本（5种算法，Week 1-2）**:

| 算法 | 类别 | 数据来源 | 实现方式 | 状态 |
|------|------|----------|---------|------|
| **山体滑坡检测** | landslide | LEVIR-CD+自建 | YOLOv8-Seg | ⚠️ 需微调 |
| **洪涝灾害监测** | flood | FloodNet | YOLOv8-Seg | ✅ 有数据 |
| **森林火灾检测** | forest_fire | FLAME | YOLOv8 | ✅ 有数据 |
| **烟雾识别** | smoke | 自建 | YOLOv8 | ⚠️ 需采集 |
| **救援目标识别** | rescue_target | VisDrone+自建 | YOLOv8 | ⚠️ 需补充 |

**V2.0 - 扩展版本（+7种算法，Week 3-8）**:

| 算法 | 类别 | 数据来源 | 优先级 |
|------|------|----------|--------|
| 泥石流检测 | mudslide | 自建 | P0 |
| 道路阻断检测 | road_blocked | 自建 | P1 |
| 人员搜救辅助 | person_search | COCO+自建 | P1 |
| 受灾面积评估 | disaster_area | LEVIR-CD | P1 |
| 人员聚集检测 | crowd_gather | CrowdHuman | P2 |
| 地震损毁评估 | earthquake_damage | 自建 | P2 |
| 台风灾害评估 | typhoon_damage | 自建 | P2 |

---

#### 3.1.2 MVP实施路径

**Week 1: 数据准备**

```bash
# 下载数据集
git clone https://github.com/cvlab-stonybrook/FloodNet-Supervised-v1.0.git
kaggle datasets download -d phylake1337/fire-dataset
git clone https://github.com/justchenhao/BIT_CD.git  # LEVIR-CD

# 数据预处理
python scripts/prepare_data.py \
  --dataset floodnet \
  --output data/emergency/flood/

python scripts/prepare_data.py \
  --dataset flame \
  --output data/emergency/forest_fire/

# 数据增强（扩增到2,000张）
python scripts/augment_data.py \
  --input data/emergency/ \
  --output data/emergency/train/ \
  --methods mosaic,mixup,hsv \
  --multiplier 4
```

**Week 2: 模型训练**

```bash
# 训练应急灾害检测模型（5类）
python train.py \
  --model yolov8m.pt \
  --data config/data.yaml \
  --epochs 100 \
  --batch_size 16 \
  --img_size 640 \
  --device 0 \
  --project models/emergency/v1.0 \
  --name disaster_detection

# 导出ONNX
python export.py \
  --weights models/emergency/v1.0/disaster_detection/weights/best.pt \
  --format onnx \
  --imgsz 640 \
  --simplify

# 转换TensorRT
trtexec \
  --onnx=models/emergency/v1.0/weights/best.onnx \
  --saveEngine=models/emergency/v1.0/weights/best.engine \
  --fp16 \
  --workspace=4096
```

**Week 2: 插件开发**

```python
# edge_infer/plugins/emergency_management/detector.py

from typing import List, Dict
import numpy as np
import tensorrt as trt
import pycuda.driver as cuda

class EmergencyDetector:
    """应急管理检测插件"""
    
    def __init__(self, config):
        self.config = config
        self.model = self.load_model(config['model_path'])
        self.classes = config['classes']
        
    def load_model(self, model_path):
        """加载TensorRT引擎"""
        # TRT引擎加载逻辑
        pass
        
    def detect(self, image: np.ndarray) -> List[Dict]:
        """
        检测应急灾害
        
        Args:
            image: 输入图像 (H, W, 3)
        
        Returns:
            [
                {
                    'class': 'landslide',
                    'confidence': 0.92,
                    'bbox': [x1, y1, x2, y2],
                    'area': 1234.5
                },
                ...
            ]
        """
        # 预处理
        input_tensor = self.preprocess(image)
        
        # 推理
        outputs = self.model.infer(input_tensor)
        
        # 后处理
        detections = self.postprocess(outputs)
        
        return detections
    
    def preprocess(self, image):
        """图像预处理"""
        # resize, normalize, etc.
        pass
        
    def postprocess(self, outputs):
        """后处理（NMS, 过滤等）"""
        pass
```

**插件配置** (`config.yaml`):

```yaml
plugin:
  name: "emergency_management"
  version: "1.0.0"
  description: "应急管理算法包（5种）"
  
model:
  path: "weights/best.engine"
  type: "tensorrt"
  classes:
    - landslide
    - flood
    - forest_fire
    - smoke
    - rescue_target
  
inference:
  device: "cuda:0"
  batch_size: 1
  confidence_threshold: 0.5
  nms_threshold: 0.4
  
algorithms:
  - name: "disaster_detection"
    type: "detection"
    classes: ["landslide", "flood", "forest_fire", "smoke"]
    
  - name: "rescue_detection"
    type: "detection"
    classes: ["rescue_target"]
```

---

#### 3.1.3 交付清单

**开发人员需要交付**:

```
models/emergency/v1.0/
├── weights/
│   ├── best.pt                 ✅
│   ├── best.onnx              ✅
│   └── best.engine            ✅
├── config/
│   ├── model_config.json      ✅
│   ├── data.yaml              ✅
│   └── inference_config.yaml  ✅
├── docs/
│   ├── README.md              ✅
│   ├── MODEL_CARD.md          ✅
│   └── PERFORMANCE.md         ✅
├── test/
│   ├── test_images/
│   ├── test_results/
│   └── test_report.json       ✅
└── plugin/
    ├── __init__.py
    ├── config.yaml            ✅
    ├── detector.py            ✅
    ├── postprocess.py
    └── utils.py
```

---

### 3.2 住建建筑部门

**负责人**: 算法工程师B
**优先级**: P0
**预算**: ¥5-20万/工地/年
**实施周期**: 2个月

---

#### 3.2.1 算法清单

**V1.0 - MVP版本（5种算法，Week 1-2）**:

| 算法 | 类别 | 数据来源 | 实现方式 |
|------|------|----------|---------|
| **安全帽识别** | helmet, head | 已有数据集 | YOLOv8 |
| **反光衣识别** | reflective_vest, no_vest | 已有数据集 | YOLOv8 |
| **违规闯入** | person + 区域判断 | VisDrone | 规则实现 |
| **塔吊检测** | truck + 规则 | VisDrone | 规则实现 |
| **材料堆放** | 多类 + 密度分析 | VisDrone | 规则实现 |

**V2.0 - 扩展版本（+10种算法，Week 3-8）**:

| 算法 | 数据来源 | 优先级 |
|------|----------|--------|
| 消防通道占用 | 自建500张 | P0 |
| 安全带识别 | 自建300张 | P1 |
| 脚手架安全 | 自建500张 | P1 |
| 临边防护 | 自建300张 | P1 |
| 裂缝检测 | 公开+自建 | P1 |
| 基坑监测 | 自建 | P2 |
| 混凝土缺陷 | 自建 | P2 |
| 钢筋检测 | 自建 | P2 |
| 平整度检测 | 自建 | P2 |
| 施工进度 | 自建 | P2 |

---

#### 3.2.2 MVP实施路径

**Week 1: 复用现有模型**

```bash
# 已有13类模型（VisDrone 9类 + helmet 2类 + vest 2类）
# 直接部署，无需重新训练

# 模型路径（已有）
models/construction_safety_v0/
├── weights/
│   ├── best.pt
│   ├── best.onnx
│   └── best.engine

# 配置文件
classes:
  - person
  - bicycle
  - car
  - van
  - truck
  - tricycle
  - awning-tricycle
  - bus
  - motor
  - helmet
  - head
  - reflective_vest
  - no_vest
```

**Week 1-2: 插件开发**

```python
# edge_infer/plugins/construction_safety/detector.py

class ConstructionSafetyDetector:
    """施工安全检测插件"""
    
    def detect_helmet(self, image):
        """安全帽识别"""
        detections = self.yolo.detect(image)
        
        helmets = [d for d in detections if d['class'] == 'helmet']
        heads = [d for d in detections if d['class'] == 'head']
        
        total = len(helmets) + len(heads)
        compliance_rate = len(helmets) / total if total > 0 else 0
        
        return {
            'total': total,
            'with_helmet': len(helmets),
            'without_helmet': len(heads),
            'compliance_rate': compliance_rate
        }
    
    def detect_intrusion(self, image, danger_zones):
        """违规闯入检测"""
        detections = self.yolo.detect(image)
        persons = [d for d in detections if d['class'] == 'person']
        
        intrusions = []
        for person in persons:
            point = (person['center_x'], person['center_y'])
            for zone in danger_zones:
                if self.point_in_polygon(point, zone['points']):
                    intrusions.append({
                        'person': person,
                        'zone': zone['name']
                    })
        
        return intrusions
```

---

#### 3.2.3 交付清单

与应急管理相同格式，包含：
- ✅ 模型权重（best.pt, best.onnx, best.engine）
- ✅ 配置文件（model_config.json, data.yaml, inference_config.yaml）
- ✅ 文档（README.md, MODEL_CARD.md, PERFORMANCE.md）
- ✅ 插件代码（edge_infer/plugins/construction_safety/）

---

### 3.3 城管部门

**负责人**: 算法工程师C
**优先级**: P1
**预算**: ¥30-100万/年
**实施周期**: 3个月

---

#### 3.3.1 算法清单

**V1.0 - MVP版本（5种算法，Week 1-2）**:

| 算法 | 类别 | 数据来源 | 实现方式 |
|------|------|----------|---------|
| **占道经营** | stall | 自建 | YOLOv8 |
| **道路垃圾** | garbage | 自建 | YOLOv8 |
| **路面垃圾** | garbage | 自建 | YOLOv8 |
| **道路占用** | vehicle + 区域判断 | VisDrone | 规则实现 |
| **裸土覆盖** | bare_soil | 自建 | YOLOv8-Seg |

**V2.0 - 扩展版本（+10种算法，Week 3-12）**:

| 算法 | 数据来源 | 优先级 |
|------|----------|--------|
| 违章建筑 | RCMT | P0 |
| 广告牌破损 | 自建 | P1 |
| 私搭乱建 | RCMT | P1 |
| 路灯故障 | 自建 | P2 |
| 交通标志破损 | 自建 | P2 |
| 绿网搭建 | RCMT | P1 |
| 黑网搭建 | RCMT | P1 |
| 脚手架识别 | 自建 | P1 |
| 绿地覆盖 | SegFormer | P2 |
| 违规横幅 | 自建 | P2 |

---

#### 3.3.2 MVP实施路径

**Week 1: 数据采集**

```bash
# 城市管理场景数据采集
采集对象：
- 占道经营（地摊、摊位）
- 道路垃圾（纸屑、塑料袋、烟头）
- 裸土覆盖（施工工地、未绿化区域）

采集方式：
- 城管部门合作（历史执法照片）
- 无人机巡检（500张）
- 网络爬虫（新闻图片，300张）

标注：
- 1,000张 × ¥1/张 = ¥1,000
```

**Week 2: 模型训练**

```bash
# 训练城市管理检测模型（5类）
python train.py \
  --model yolov8m.pt \
  --data config/data_urban.yaml \
  --epochs 100 \
  --batch_size 16
```

---

### 3.4 国土资源部门

**负责人**: 算法工程师A
**优先级**: P1
**预算**: ¥30-200万/年
**实施周期**: 3个月

---

#### 3.4.1 算法清单

**V1.0 - MVP版本（3种算法，Week 1-2）**:

| 算法 | 类别 | 数据来源 | 实现方式 |
|------|------|----------|---------|
| **变化检测** | change | LEVIR-CD | RCMT V3 |
| **违章建筑** | illegal_building | LEVIR-CD | RCMT + YOLOv8 |
| **违法用地** | illegal_land | LEVIR-CD | RCMT + GIS |

**V2.0 - 扩展版本（+7种算法，Week 3-12）**:

| 算法 | 数据来源 | 优先级 |
|------|----------|--------|
| 黑网搭建 | RCMT | P1 |
| 绿网搭建 | RCMT | P1 |
| 采沙识别 | 自建 | P1 |
| 裸土覆盖 | SegFormer | P2 |
| 撂荒地检测 | SegFormer | P2 |
| 农田面积 | SegFormer | P2 |
| 大棚识别 | 自建 | P2 |

---

#### 3.4.2 MVP实施路径

**Week 1: 复用RCMT模型**

```bash
# RCMT V3-Swin已训练完成（F1=0.92）
# 直接部署，无需重新训练

# 模型路径（已有）
models/rcmt_v3/
├── weights/
│   ├── best_model.pth
│   ├── rcmt_v3.onnx
│   └── rcmt_v3.engine

# 部署为云端服务
python deploy_rcmt_cloud.py \
  --model models/rcmt_v3/weights/rcmt_v3.engine \
  --port 8001
```

---

### 3.5 其他部门（环保、电力、水利、农业、交通）

**实施原则相同**：
1. MVP版本（2-5种核心算法）
2. 复用现有模型优先
3. 渐进式扩展
4. 标准化交付

（详细内容略，结构与前4个部门相同）

---

## 4. 松耦合集成方案

### 4.1 插件架构

```
edge_infer/plugins/
├── base/                          # 基础插件类
│   ├── __init__.py
│   ├── base_detector.py           # 检测器基类
│   ├── base_segmenter.py          # 分割器基类
│   └── base_tracker.py            # 跟踪器基类
│
├── emergency_management/          # 应急管理插件
│   ├── __init__.py
│   ├── config.yaml
│   ├── detector.py
│   └── postprocess.py
│
├── construction_safety/           # 住建建筑插件
│   ├── __init__.py
│   ├── config.yaml
│   ├── detector.py
│   └── postprocess.py
│
├── urban_management/              # 城管插件
├── land_monitoring/               # 国土插件
├── environmental_monitoring/      # 环保插件
├── power_inspection/              # 电力插件
├── water_conservancy/             # 水利插件
├── agriculture/                   # 农业插件
└── transportation/                # 交通插件
```

---

### 4.2 统一接口

```python
# edge_infer/plugins/base/base_detector.py

from abc import ABC, abstractmethod
from typing import List, Dict
import numpy as np

class BaseDetector(ABC):
    """检测器基类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.model = self.load_model(config['model_path'])
        self.classes = config['classes']
        
    @abstractmethod
    def load_model(self, model_path: str):
        """加载模型"""
        pass
        
    @abstractmethod
    def detect(self, image: np.ndarray) -> List[Dict]:
        """
        检测接口
        
        Args:
            image: 输入图像 (H, W, 3)
        
        Returns:
            [
                {
                    'class': str,
                    'confidence': float,
                    'bbox': [x1, y1, x2, y2],
                    'extra': dict  # 额外信息
                },
                ...
            ]
        """
        pass
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """预处理（可重写）"""
        # 默认实现
        pass
        
    def postprocess(self, outputs: np.ndarray) -> List[Dict]:
        """后处理（可重写）"""
        # 默认实现
        pass
```

---

### 4.3 插件加载机制

```python
# edge_infer/core/plugin_manager.py

import importlib
from typing import Dict
import yaml

class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins: Dict[str, BaseDetector] = {}
        
    def load_plugin(self, plugin_name: str, config_path: str):
        """加载插件"""
        # 1. 加载配置
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # 2. 动态导入插件模块
        module = importlib.import_module(f'plugins.{plugin_name}.detector')
        
        # 3. 实例化检测器
        detector_class = getattr(module, f'{plugin_name.capitalize()}Detector')
        detector = detector_class(config)
        
        # 4. 注册插件
        self.plugins[plugin_name] = detector
        
        return detector
    
    def get_plugin(self, plugin_name: str) -> BaseDetector:
        """获取插件"""
        return self.plugins.get(plugin_name)
    
    def list_plugins(self) -> List[str]:
        """列出所有插件"""
        return list(self.plugins.keys())

# 使用示例
manager = PluginManager()

# 加载应急管理插件
emergency_detector = manager.load_plugin(
    'emergency_management',
    'plugins/emergency_management/config.yaml'
)

# 加载住建安全插件
construction_detector = manager.load_plugin(
    'construction_safety',
    'plugins/construction_safety/config.yaml'
)

# 执行检测
image = cv2.imread('test.jpg')
results = emergency_detector.detect(image)
```

---

### 4.4 云边协同

```python
# edge_infer/core/cloud_client.py

import requests
from typing import Dict

class CloudClient:
    """云端推理客户端"""
    
    def __init__(self, cloud_api_url: str):
        self.cloud_api_url = cloud_api_url
        
    async def infer(self, image_url: str, algorithm: str) -> Dict:
        """
        调用云端推理
        
        Args:
            image_url: 图像URL
            algorithm: 算法名称（如 'rcmt_change_detection'）
        
        Returns:
            推理结果
        """
        payload = {
            'image_url': image_url,
            'algorithm': algorithm
        }
        
        response = requests.post(
            f'{self.cloud_api_url}/infer',
            json=payload
        )
        
        return response.json()

# 使用示例
cloud_client = CloudClient('https://api.skyedge.ai')

# 边缘检测（快速）
edge_results = emergency_detector.detect(image)

# 如果需要深度分析，调用云端
if needs_deep_analysis(edge_results):
    # 上传图像到云端
    image_url = upload_to_cloud(image)
    
    # 云端推理
    cloud_results = await cloud_client.infer(
        image_url,
        algorithm='rcmt_change_detection'
    )
```

---

## 5. 开发人员工作流程

### 5.1 标准工作流程

```
阶段1: 数据准备（Week 1）
  ├─ 下载数据集（公开）
  ├─ 采集数据（自建）
  ├─ 数据清洗
  ├─ 数据标注
  └─ 数据增强

阶段2: 模型训练（Week 2）
  ├─ 配置训练参数
  ├─ 训练模型
  ├─ 验证模型
  ├─ 超参调优
  └─ 保存最佳模型

阶段3: 模型转换（Week 2）
  ├─ 导出ONNX
  ├─ 转换TensorRT
  ├─ 测试推理性能
  └─ 优化推理速度

阶段4: 插件开发（Week 2）
  ├─ 编写插件代码
  ├─ 编写配置文件
  ├─ 编写文档
  └─ 单元测试

阶段5: 集成测试（Week 2）
  ├─ 边缘设备测试
  ├─ 云边协同测试
  ├─ 性能测试
  └─ 验收测试

阶段6: 交付（Week 2）
  ├─ 打包模型
  ├─ 编写文档
  ├─ 提交代码
  └─ 演示验收
```

---

### 5.2 开发环境要求

```bash
# 软件环境
Python >= 3.8
PyTorch >= 2.0
Ultralytics >= 8.0.0
TensorRT >= 8.6.0
ONNX >= 1.14.0
ONNXRuntime >= 1.15.0

# 硬件环境
训练：RTX 4090 / A100
测试：Jetson Orin NX 16GB
存储：100GB+

# 工具链
Git >= 2.30
Docker >= 20.10
CUDA >= 11.8
cuDNN >= 8.6
```

---

### 5.3 代码仓库结构

```
edge_infer_cloud/
├── models/                        # 模型仓库
│   ├── emergency/
│   ├── construction/
│   ├── urban/
│   └── ...
│
├── datasets/                      # 数据集仓库
│   ├── emergency/
│   ├── construction/
│   └── ...
│
├── scripts/                       # 脚本
│   ├── train.py                   # 训练脚本
│   ├── export.py                  # 导出脚本
│   ├── prepare_data.py            # 数据准备
│   └── test_model.py              # 测试脚本
│
├── config/                        # 配置文件
│   ├── train_config.yaml
│   └── inference_config.yaml
│
└── docs/                          # 文档
    ├── models/                    # 模型文档
    └── plugins/                   # 插件文档
```

---

## 6. 质量控制与验收

### 6.1 模型验收标准

| 指标 | 目标值 | 验收方法 |
|------|--------|----------|
| **精度** | mAP@0.5 > 0.85 | 测试集验证 |
| **推理时间** | < 100ms (Jetson) | 边缘设备测试 |
| **模型大小** | < 100MB | 文件大小检查 |
| **内存占用** | < 1GB (边缘) | 内存监控 |
| **稳定性** | 运行24小时无崩溃 | 稳定性测试 |

---

### 6.2 代码审查清单

```markdown
- [ ] 代码符合PEP8规范
- [ ] 有完整的注释和文档字符串
- [ ] 单元测试覆盖率 > 80%
- [ ] 性能测试通过（推理时间<100ms）
- [ ] 内存泄漏测试通过
- [ ] 配置文件格式正确
- [ ] 错误处理完善
- [ ] 日志记录规范
- [ ] README文档完整
- [ ] MODEL_CARD准确
```

---

### 6.3 交付验收流程

```
1. 代码审查
   └─ Code Review通过

2. 模型测试
   ├─ 精度测试通过（mAP>0.85）
   ├─ 性能测试通过（<100ms）
   └─ 稳定性测试通过

3. 文档审查
   ├─ README完整
   ├─ MODEL_CARD准确
   └─ API文档清晰

4. 集成测试
   ├─ edge_infer集成成功
   ├─ edge_infer_cloud API正常
   └─ 云边协同测试通过

5. 最终验收
   ├─ 产品工程师验收
   ├─ 软件工程师验收
   └─ 算法工程师验收
```

---

## 7. 总结

### 7.1 核心要点

1. ✅ **标准化交付**：统一的模型格式和配置文件
2. ✅ **松耦合架构**：独立插件，灵活组合
3. ✅ **渐进式实施**：MVP → 扩展 → 完整
4. ✅ **复用现有能力**：优先使用已有模型
5. ✅ **数据驱动**：有数据再加算法

---

### 7.2 立即行动

**本周任务**（所有部门）:

```bash
算法工程师A（应急+国土）:
- [ ] 下载FloodNet, FLAME, LEVIR-CD数据集
- [ ] 准备应急管理MVP数据集（2,000张）
- [ ] 开始训练应急管理V1.0模型

算法工程师B（住建+环保+农业）:
- [ ] 部署13类施工安全模型（已有）
- [ ] 开发5种算法的逻辑实现
- [ ] 采集消防通道数据（500张）

算法工程师C（城管+电力+水利+交通）:
- [ ] 采集城市管理数据（1,000张）
- [ ] 开发城市管理插件
- [ ] 集成测试
```

---

**维护者**: 空中智能体团队
**最后更新**: 2026-03-09
**版本**: V1.0
**文档位置**: docs/v2_reorganized/05_business/DEPARTMENT_IMPLEMENTATION_GUIDE.md
