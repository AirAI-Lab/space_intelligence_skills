# 算法人员 → 软件人员接口文档

## 概述

本文档说明算法人员需要提供什么给软件人员，以便他们将模型集成到 AI 推理框架。

---

## 1. 算法人员需要提供的内容

### 1.1 模型文件

**必须提供**:
```
models/
├── water_inspection.pt      # PyTorch 权重（训练用）
├── water_inspection.onnx    # ONNX 模型（推理用）
└── water_inspection.engine  # TensorRT 引擎（Jetson 用，可选）
```

**生成方法**:
```bash
# PyTorch → ONNX
python export_onnx.py --weights runs/train/exp/weights/best.pt --output models/water_inspection.onnx

# ONNX → TensorRT（Jetson）
trtexec --onnx=models/water_inspection.onnx --saveEngine=models/water_inspection.engine --fp16
```

---

### 1.2 类别名称文件

**文件**: `models/water_inspection.names`

**格式**:
```
person
fishing_person
swimming_person
playing_person
intruding
water_gauge
outlet_pipe
outlet_active
pipe_damaged
dam_seepage
boat
floating_debris
```

**说明**: 每行一个类别名，顺序与训练时的类别 ID 对应。

---

### 1.3 模型配置文件

**文件**: `models/water_inspection.json`

**格式**:
```json
{
  "model_name": "water_inspection",
  "version": "2.0",
  "task_type": "detection",

  "input": {
    "width": 640,
    "height": 640,
    "channels": 3,
    "format": "BGR",
    "batch_size": 1
  },

  "output": {
    "type": "detection",
    "num_classes": 12,
    "format": "YOLOv8"
  },

  "classes": [
    {"id": 0, "name": "person", "zh": "人员"},
    {"id": 1, "name": "fishing_person", "zh": "钓鱼"},
    {"id": 2, "name": "swimming_person", "zh": "游泳"},
    {"id": 3, "name": "playing_person", "zh": "嬉水"},
    {"id": 4, "name": "intruding", "zh": "闯入"},
    {"id": 5, "name": "water_gauge", "zh": "水位尺"},
    {"id": 6, "name": "outlet_pipe", "zh": "排污管道"},
    {"id": 7, "name": "outlet_active", "zh": "正在排污"},
    {"id": 8, "name": "pipe_damaged", "zh": "管道破损"},
    {"id": 9, "name": "dam_seepage", "zh": "坝体渗水"},
    {"id": 10, "name": "boat", "zh": "船舶"},
    {"id": 11, "name": "floating_debris", "zh": "漂浮物"}
  ],

  "postprocess": {
    "conf_threshold": 0.25,
    "iou_threshold": 0.45,
    "max_detections": 300
  },

  "performance": {
    "target_fps": 30,
    "device": "cuda"
  }
}
```

---

### 1.4 后处理规则

**文件**: `models/water_inspection_rules.json`

**格式**:
```json
{
  "alert_rules": [
    {
      "class_id": 1,
      "class_name": "fishing_person",
      "level": "warning",
      "message": "检测到违规钓鱼",
      "suppress_minutes": 5
    },
    {
      "class_id": 2,
      "class_name": "swimming_person",
      "level": "critical",
      "message": "检测到违规游泳",
      "suppress_minutes": 3
    },
    {
      "class_id": 7,
      "class_name": "outlet_active",
      "level": "critical",
      "message": "检测到正在排污",
      "suppress_minutes": 1
    }
  ],

  "association_rules": {
    "person_classes": [0, 1, 2, 3, 4],
    "facility_classes": [5, 6, 7, 8, 9],
    "target_classes": [10, 11]
  }
}
```

---

## 2. 软件人员需要的接口

### 2.1 输入格式

**单张图像推理**:
```json
{
  "image": "base64_string_or_file_path",
  "timestamp": 1700000000,
  "camera_id": "camera_001"
}
```

**视频流推理**:
```cpp
cv::Mat frame; // BGR 图像
```

---

### 2.2 输出格式

**检测结果**:
```json
{
  "detections": [
    {
      "class_id": 1,
      "class_name": "fishing_person",
      "confidence": 0.93,
      "bbox": [x1, y1, x2, y2],
      "bbox_center": [cx, cy],
      "bbox_area": 1234.5
    }
  ],
  "alerts": [
    {
      "class_name": "fishing_person",
      "level": "warning",
      "message": "检测到违规钓鱼",
      "timestamp": 1700000000
    }
  ],
  "stats": {
    "total_detections": 5,
    "person_behavior": 3,
    "facilities": 1,
    "targets": 1
  },
  "meta": {
    "frame_id": 123,
    "timestamp": 1700000000,
    "inference_time_ms": 15.3
  }
}
```

---

### 2.3 C++ 接口示例

**头文件** (`water_inspection.h`):
```cpp
#ifndef WATER_INSPECTION_H
#define WATER_INSPECTION_H

#include "plugin/plugin_base.h"
#include <vector>
#include <string>

namespace framework {
namespace plugin {

struct Detection {
    int class_id;
    std::string class_name;
    float confidence;
    std::vector<float> bbox;  // [x1, y1, x2, y2]
};

struct Alert {
    std::string class_name;
    std::string level;
    std::string message;
    long timestamp;
};

class WaterInspection : public PluginBase {
public:
    WaterInspection() = default;
    ~WaterInspection() override = default;

    bool init(const std::string& plugin_config) override;
    bool execute(const void* input_data, void* output_data) override;
    void deinit() override;

    std::string get_plugin_name() const override;
    PluginType get_plugin_type() const override;
    std::string get_plugin_version() const override;

    void SetInferModule(void* infer_mod) override;

private:
    void* infer_mod_;
    std::vector<std::string> class_names_;
    std::map<int, AlertRule> alert_rules_;
};

} // namespace plugin
} // namespace framework

#endif // WATER_INSPECTION_H
```

---

## 3. 部署流程

### 3.1 算法人员

1. **训练模型**
   ```bash
   python models/yolo/train.py --config configs/water_inspection.yaml --data data.yaml
   ```

2. **导出 ONNX**
   ```bash
   python deployment/export_onnx.py --weights runs/train/exp/weights/best.pt --output models/water_inspection.onnx
   ```

3. **生成配置文件**
   ```bash
   python deployment/generate_config.py --project water_inspection
   ```

4. **提交以下文件给软件人员**:
   - `models/water_inspection.onnx`
   - `models/water_inspection.names`
   - `models/water_inspection.json`
   - `models/water_inspection_rules.json`

---

### 3.2 软件人员

1. **创建插件**
   ```bash
   cd D:\github\edge_infer\src\plugins
   mkdir water_inspection
   ```

2. **复制模型和配置**
   ```bash
   cp models/water_inspection.onnx water_inspection/
   cp models/water_inspection.names water_inspection/
   cp models/water_inspection.json water_inspection/
   ```

3. **实现插件**
   - 参考 `helmet_detect` 插件
   - 实现 `water_inspection.cpp` 和 `water_inspection.h`
   - 编写 `CMakeLists.txt`

4. **编译和测试**
   ```bash
   mkdir build && cd build
   cmake ..
   make
   ```

---

## 4. 文件清单

### 算法人员提供

| 文件 | 必需 | 说明 |
|------|------|------|
| `*.onnx` | ✅ | ONNX 模型文件 |
| `*.names` | ✅ | 类别名称列表 |
| `*.json` | ✅ | 模型配置 |
| `*_rules.json` | ✅ | 报警规则 |
| `*.engine` | ⭕ | TensorRT 引擎（Jetson） |

### 软件人员实现

| 文件 | 说明 |
|------|------|
| `*.h` | 插件头文件 |
| `*.cpp` | 插件实现 |
| `CMakeLists.txt` | 编译配置 |
| `README.md` | 使用文档 |

---

## 5. 示例

完整示例见: `D:\github\edge_infer\src\plugins\helmet_detect\`

---

**最后更新**: 2026-03-26
**维护者**: 空中智能体团队
