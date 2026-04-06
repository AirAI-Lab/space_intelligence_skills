# 水利巡检智能检测系统 - 技术方案

> **版本**: V1.0
> **日期**: 2026-03-25
> **目标**: 单一模型解决水利巡检全场景实时检测

---

## 1. 方案概述

### 1.1 核心思路

借鉴 **DART** (Detect Anything in Real Time) 和 **C-RADIOv4** 的思路：

- **DART**: 将 SAM3 分割模型转换为实时多类别检测器
  - 55.8 AP @ COCO，15.8 FPS（4类，1008px，RTX 4080）
  - 训练无关（training-free）：直接使用文本提示
  - TensorRT FP16 加速

- **C-RADIOv4**: 多任务蒸馏
  - 一个模型支持检测、分割、嵌入
  - 共享视觉编码器，多任务头

### 1.2 技术选型

| 方案 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| **DART-SAM3** | 开放词汇，无需训练，灵活扩展 | 精度略低 | 类别多变的场景 |
| **YOLOv8-Seg** | 精度高，成熟稳定 | 需要标注训练 | 类别稳定的场景 |
| **混合方案** | 兼顾精度和灵活性 | 复杂度高 | 复杂业务场景 |

**水利巡检推荐**: YOLOv8-m-Seg（类别相对稳定，精度要求高）

---

## 2. 检测类别设计

### 2.1 边缘实时检测（8类）

| ID | 类别 | 英文提示 | 说明 |
|----|------|----------|------|
| 0 | 河道漂浮物 | floating debris in river | 塑料、泡沫、垃圾等 |
| 1 | 垃圾堆放 | garbage pile near river | 河道两岸垃圾堆 |
| 2 | 排污口 | sewage outlet pipe | 排污管道 |
| 3 | 堤坝裂缝 | dam crack damage | 堤坝结构损伤 |
| 4 | 水位异常 | abnormal water level | 洪水/干涸 |
| 5 | 黑臭水体 | black odorous water | 水质污染 |
| 6 | 违章建筑 | illegal building near river | 河道违建 |
| 7 | 裸土覆盖 | exposed soil erosion | 水土流失 |

### 2.2 云端深度分析（4类）

| 类别 | 技术 | 说明 |
|------|------|------|
| 堤坝变化检测 | RCMT-V3 | 堤坝形变、塌陷 |
| 水体面积变化 | RCMT-V3 + SegFormer | 水域面积监测 |
| 植被覆盖变化 | SegFormer | 河岸植被 |
| 污染扩散分析 | RCMT-V3 + 颜色分析 | 污染范围 |

---

## 3. 项目结构

### 3.1 云边协同平台 (edge_infer_cloud)

```
D:\github\edge_infer_cloud\models\water_inspection\
├── configs/
│   ├── water_dart.yaml              # DART配置
│   ├── water_yolo.yaml              # YOLO配置
│   └── cloud_services.yaml          # 云端服务配置
├── weights/                          # 模型权重
│   ├── yolo_water_seg.pt            # YOLO分割模型
│   ├── yolo_water_seg.engine        # TensorRT引擎
│   └── enc_dec_water.engine         # DART编解码器
├── training/                         # 训练脚本
│   ├── yolo_train_water.py          # YOLO训练
│   └── datasets/                    # 数据集
├── inference.py                      # 推理服务
├── service.py                        # FastAPI服务
└── README.md                        # 文档
```

### 3.2 边缘推理框架 (edge_infer)

```
D:\github\edge_infer\src\plugins\water_inspection\
├── CMakeLists.txt                   # 构建配置
├── water_inspection.h               # 接口定义
├── water_inspection.cpp             # 主实现
├── postprocess.h/cpp                # 后处理（NMS等）
├── cloud_client.h/cpp               # 云端服务客户端
├── config.yaml                      # 插件配置
└── README.md                        # 文档
```

---

## 4. 性能预估

### 4.1 边缘推理（Jetson Orin NX 16GB）

| 配置 | 模式 | 分辨率 | 类别数 | FPS | AP |
|------|------|--------|--------|-----|-----|
| **推荐** | YOLOv8-m-Seg | 640 | 8 | 30+ | 85+ |
| 高速 | YOLOv8-s | 640 | 8 | 50+ | 78+ |
| 高精度 | YOLOv8-l-Seg | 640 | 8 | 20+ | 88+ |

### 4.2 云端分析（RTX 4090）

| 服务 | 模型 | 推理时间 | 精度 |
|------|------|----------|------|
| 变化检测 | RCMT-V3-Swin | <2s | F1 > 0.92 |
| 语义分割 | SegFormer-B5 | <1s | mIoU > 0.80 |

---

## 5. 实施步骤

### Phase 1: 数据准备（1周）

1. 收集水利巡检图像数据
2. 标注8类目标
3. 数据增强和清洗
4. 划分训练/验证/测试集

### Phase 2: 模型训练（2周）

1. 训练 YOLOv8-m-Seg 模型
2. 评估和调优
3. 导出 TensorRT 引擎

### Phase 3: 边缘部署（1周）

1. 开发 water_inspection 插件
2. 集成到 edge_infer 框架
3. 边缘设备测试

### Phase 4: 云边协同（1周）

1. 集成 RCMT-V3 云端服务
2. 开发云边通信接口
3. 端到端测试

---

## 6. API 接口

### 6.1 边缘推理

```python
# 本地推理
POST http://localhost:8000/detect
Content-Type: multipart/form-data

file: <image>
```

**响应**:
```json
{
  "detections": [
    {
      "class_id": 0,
      "class_name": "floating_debris",
      "class_name_cn": "河道漂浮物",
      "confidence": 0.85,
      "bbox": [x1, y1, x2, y2]
    }
  ],
  "inference_time_ms": 32.5,
  "fps": 30.8
}
```

### 6.2 云端分析

```python
# 变化检测
POST http://cloud-server:8001/api/rcmt/change_detect
Content-Type: application/json

{
  "t1_image": "<base64>",
  "t2_image": "<base64>"
}
```

**响应**:
```json
{
  "change_ratio": 0.15,
  "change_mask": "<base64>",
  "inference_time_ms": 1850
}
```

---

## 7. 快速开始

### 7.1 云端服务

```bash
cd D:\github\edge_infer_cloud\models\water_inspection

# 安装依赖
pip install ultralytics fastapi uvicorn opencv-python

# 启动服务
python inference.py --serve --port 8000

# 测试
python inference.py --image test.jpg --output result.jpg
```

### 7.2 边缘推理

```bash
cd D:\github\edge_infer\src\plugins\water_inspection

# 构建
mkdir build && cd build
cmake ..
make -j$(nproc)

# 运行
./water_inspection --config config.yaml --video rtsp://camera-url
```

---

## 8. 后续优化

1. **模型蒸馏**: 使用 DART 将 SAM3 蒸馏为轻量模型
2. **数据增强**: 添加更多水利场景数据
3. **多尺度检测**: 支持不同高度无人机图像
4. **增量学习**: 持续学习新类别

---

**维护者**: 空中智能体团队
**最后更新**: 2026-03-25
