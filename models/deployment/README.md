# Deployment - 部署接口

本目录包含**算法人员**需要提供的文件和工具。

---

## 📦 算法人员需要提供的内容

### 1. 模型文件

| 文件 | 必需 | 格式 | 说明 |
|------|------|------|------|
| `*.onnx` | ✅ | ONNX | ONNX 模型（通用推理） |
| `*.engine` | ⭕ | TensorRT | TensorRT 引擎（Jetson 高性能） |

### 2. 配置文件

| 文件 | 必需 | 格式 | 说明 |
|------|------|------|------|
| `*.json` | ✅ | JSON | 模型配置（输入输出、类别等） |
| `*.names` | ✅ | TXT | 类别名称列表 |
| `*_rules.json` | ✅ | JSON | 报警规则 |

---

## 🛠️ 导出工具

### 1. 一键导出

```bash
cd models/water_inspection
python deployment/export_model.py --weights runs/train/exp/weights/best.pt --output models
```

**生成的文件**:
- `water_inspection.onnx` - ONNX 模型
- `water_inspection.json` - 模型配置
- `water_inspection.names` - 类别名称
- `water_inspection_rules.json` - 报警规则

### 2. 单独导出

```bash
# 仅导出 ONNX
python deployment/export_onnx.py --weights best.pt --output water_inspection.onnx

# 仅生成配置
python deployment/generate_config.py --project water_inspection --output models
```

---

## 📋 配置文件格式

### 模型配置 (`*.json`)

```json
{
  "model_name": "water_inspection",
  "version": "2.0",
  "task_type": "detection",

  "input": {
    "width": 640,
    "height": 640,
    "channels": 3,
    "format": "BGR"
  },

  "output": {
    "type": "detection",
    "num_classes": 12
  },

  "classes": [
    {"id": 0, "name": "person", "zh": "人员"},
    {"id": 1, "name": "fishing_person", "zh": "钓鱼"},
    ...
  ]
}
```

### 类别名称 (`*.names`)

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

### 报警规则 (`*_rules.json`)

```json
{
  "project": "water_inspection",
  "version": "1.0",
  "rules": [
    {
      "name": "critical_alert",
      "level": "critical",
      "classes": [1, 2, 3, 4, 8, 9],
      "actions": ["sound_light", "app_push", "sms"],
      "suppress_seconds": 300
    },
    {
      "name": "warning_alert",
      "level": "warning",
      "classes": [7, 10, 11],
      "actions": ["app_push"],
      "suppress_seconds": 600
    }
  ]
}
```

---

## 🔧 TensorRT 转换

在 Jetson 设备上运行:

```bash
# ONNX → TensorRT
trtexec \
  --onnx=water_inspection.onnx \
  --saveEngine=water_inspection.engine \
  --fp16 \
  --workspace=4096
```

---

## 📁 提交给软件人员

将以下文件打包:

```
water_inspection/
├── water_inspection.onnx         # ONNX 模型
├── water_inspection.engine       # TensorRT 引擎（可选）
├── water_inspection.json         # 模型配置
├── water_inspection.names        # 类别名称
└── water_inspection_rules.json   # 报警规则
```

**文档**:
- `deployment/INTERFACE.md` - 接口说明

---

## 📖 参考

- **完整接口文档**: `deployment/INTERFACE.md`
- **插件示例**: `D:\github\edge_infer\src\plugins\helmet_detect\`

---

**维护者**: 空中智能体团队
