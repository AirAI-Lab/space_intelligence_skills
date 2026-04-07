# Deployment 目录说明

**目的**: 为算法人员和软件人员提供集成接口

---

## 📂 目录结构

```
models/
├── deployment/                    # 通用工具（共享）
│   ├── README.md                 # 使用说明
│   ├── INTERFACE.md              # 接口文档（给软件人员）
│   ├── export_onnx.py            # ONNX 导出工具
│   └── generate_config.py        # 配置生成工具
│
├── water_inspection/
│   └── deployment/
│       └── export_model.py       # 一键导出脚本
│
├── park_monitoring/
│   └── deployment/
│       └── export_model.py
│
└── construction_safety/
    └── deployment/
        └── export_model.py
```

---

## 🎯 角色分工

### 算法人员

**使用**:
- `export_model.py` - 一键导出所有文件
- `export_onnx.py` - 单独导出 ONNX
- `generate_config.py` - 单独生成配置

**输出**:
- `*.onnx` - ONNX 模型
- `*.json` - 模型配置
- `*.names` - 类别名称
- `*_rules.json` - 报警规则

### 软件人员

**参考**:
- `INTERFACE.md` - 完整接口文档

**输入**:
- 算法人员提供的所有文件

**实现**:
- 插件代码 (`*.cpp`, `*.h`)
- CMake 配置
- 集成到框架

---

## 🚀 快速开始

### 算法人员

```bash
# 1. 训练完成，导出模型
cd models/water_inspection
python deployment/export_model.py --weights runs/train/exp/weights/best.pt

# 2. 生成的文件（在 models/ 目录）
# - water_inspection.onnx
# - water_inspection.json
# - water_inspection.names
# - water_inspection_rules.json

# 3. 提交给软件人员
```

### 软件人员

```bash
# 1. 接收文件
# - water_inspection.onnx
# - water_inspection.json
# - water_inspection.names
# - water_inspection_rules.json

# 2. 阅读接口文档
cat models/deployment/INTERFACE.md

# 3. 实现插件
cd D:\github\edge_infer\src\plugins
mkdir water_inspection
# 参考 helmet_detect 实现

# 4. 测试和集成
```

---

## 📖 文档

- **INTERFACE.md** - 完整接口说明（必读）
- **README.md** - 使用指南
- **示例** - `D:\github\edge_infer\src\plugins\helmet_detect\`

---

**维护者**: 空中智能体团队
