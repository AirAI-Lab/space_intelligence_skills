# 架构澄清：云边分离开发模式

> **版本**: V1.0
> **日期**: 2026-03-09
> **目的**: 明确算法工程师和软件工程师的工作边界和代码仓库划分

---

## 📋 问题背景

在实施方案中，原计划将 Python 插件代码放在 `edge_infer/plugins/` 目录下，但这会导致以下问题：

1. **架构混乱**：edge_infer 是 C++ 边缘推理框架，不应该有 Python 代码
2. **职责不清**：算法工程师和软件工程师的代码混在一起
3. **部署困难**：边缘设备需要的是编译后的 C++ 插件，不是 Python 代码

---

## ✅ 正确的架构

### **云边分离架构**

```
┌─────────────────────────────────────────────────────────┐
│          edge_infer_cloud (云端/PC端 - Python)          │
├─────────────────────────────────────────────────────────┤
│  仓库：D:\github\edge_infer_cloud                       │
│  负责人：算法工程师                                      │
│  职责：数据准备、模型训练、验证、导出、云端API           │
│  语言：Python                                           │
│  目录：models/construction_safety/                      │
└─────────────────────────────────────────────────────────┘
                        ↓ 导出 ONNX/Engine
┌─────────────────────────────────────────────────────────┐
│          edge_infer (边缘端 - C++)                      │
├─────────────────────────────────────────────────────────┤
│  仓库：D:\github\edge_infer                             │
│  负责人：软件工程师                                      │
│  职责：插件开发、推理实现、边缘部署                      │
│  语言：C++                                              │
│  目录：src/plugins/construction_safety/                 │
└─────────────────────────────────────────────────────────┘
```

---

## 📂 目录结构对比

### **edge_infer_cloud（算法工程师）**

```
edge_infer_cloud/
├── models/
│   └── construction_safety/
│       ├── v1.0/
│       │   ├── weights/              # 模型权重（算法工程师交付）
│       │   │   ├── best.pt           # PyTorch权重
│       │   │   ├── best.onnx         # ONNX格式（软件工程师输入）
│       │   │   └── best.engine       # TensorRT引擎（边缘部署）
│       │   ├── config/               # 配置文件
│       │   │   ├── model_config.json
│       │   │   ├── data.yaml
│       │   │   └── train_config.yaml
│       │   ├── scripts/              # Python脚本（算法工程师）
│       │   │   ├── train.py          # 训练
│       │   │   ├── export_onnx.py    # 导出ONNX
│       │   │   ├── validate.py       # 验证
│       │   │   └── inference_demo.py # 推理演示
│       │   ├── tests/                # Python测试
│       │   │   ├── test_model.py
│       │   │   └── test_accuracy.py
│       │   ├── docs/                 # 文档
│       │   │   ├── README.md
│       │   │   └── MODEL_CARD.md
│       │   └── test_results/         # 测试结果
│       └── README.md
├── backend/                          # 云端API（FastAPI）
│   └── api/routes/construction.py
└── datasets/                         # 数据集
    └── construction_safety/
```

### **edge_infer（软件工程师）**

```
edge_infer/
├── src/plugins/
│   └── construction_safety/          # C++ 插件（软件工程师）
│       ├── CMakeLists.txt            # 编译配置
│       ├── construction_safety.h     # C++ 头文件
│       ├── construction_safety.cpp   # C++ 主实现
│       ├── algorithms/               # 算法实现（C++）
│       │   ├── helmet_detection.cpp
│       │   ├── vest_detection.cpp
│       │   └── intrusion_detection.cpp
│       ├── utils/                    # 工具函数
│       │   ├── nms.cpp
│       │   └── postprocess.cpp
│       ├── config/
│       │   └── config.yaml           # 插件配置
│       └── README.md
└── build/
    └── plugins/
        └── libconstruction_safety.so # 编译后的插件（边缘部署）
```

---

## 🔄 工作流程

### **算法工程师（Python）**

```bash
# 1. 数据准备
cd edge_infer_cloud
python datasets/prepare_construction_safety.py

# 2. 训练模型
python models/construction_safety/v1.0/scripts/train.py \
  --config models/construction_safety/v1.0/config/train_config.yaml

# 3. 验证模型
python models/construction_safety/v1.0/scripts/validate.py \
  --weights models/construction_safety/v1.0/weights/best.pt \
  --data models/construction_safety/v1.0/config/data.yaml

# 4. 导出ONNX
python models/construction_safety/v1.0/scripts/export_onnx.py \
  --weights models/construction_safety/v1.0/weights/best.pt \
  --output models/construction_safety/v1.0/weights/

# 5. 交付给软件工程师
# - models/construction_safety/v1.0/weights/best.onnx
# - models/construction_safety/v1.0/weights/best.engine
# - models/construction_safety/v1.0/config/model_config.json
```

### **软件工程师（C++）**

```bash
# 1. 接收算法工程师交付物
# - best.onnx
# - best.engine
# - model_config.json

# 2. 开发C++插件
cd edge_infer
vim src/plugins/construction_safety/construction_safety.cpp

# 3. 编译插件
bash scripts/build_construction_safety.sh

# 4. 部署到边缘设备
scp build/plugins/libconstruction_safety.so jetson@192.168.1.100:/opt/edge_infer/plugins/
scp models/construction_safety/v1.0/weights/best.engine jetson@192.168.1.100:/opt/edge_infer/models/

# 5. 测试
ssh jetson@192.168.1.100
cd /opt/edge_infer
./edge_infer --plugin construction_safety --config models/construction_safety/v1.0/config/model_config.json
```

---

## 👥 角色分工

| 角色 | 工作目录 | 语言 | 职责 | 交付物 |
|------|---------|------|------|--------|
| **算法工程师** | `edge_infer_cloud/models/` | Python | 数据准备、模型训练、验证、导出 | best.onnx, best.engine, model_config.json |
| **软件工程师** | `edge_infer/src/plugins/` | C++ | 插件开发、推理实现、边缘部署 | libconstruction_safety.so |

---

## 📋 交付清单

### **算法工程师交付给软件工程师**

```markdown
- [ ] 模型权重
  - [ ] best.pt (PyTorch)
  - [ ] best.onnx (ONNX) ✅ 必须
  - [ ] best.engine (TensorRT) ✅ 必须

- [ ] 配置文件
  - [ ] model_config.json ✅ 必须
  - [ ] data.yaml
  - [ ] train_config.yaml

- [ ] 文档
  - [ ] README.md ✅ 必须
  - [ ] MODEL_CARD.md ✅ 必须
  - [ ] PERFORMANCE.md ✅ 必须

- [ ] 测试结果
  - [ ] test_results/validation_report.json ✅ 必须
  - [ ] test_results/accuracy_metrics.json
```

### **软件工程师部署到边缘设备**

```markdown
- [ ] 编译后的插件
  - [ ] libconstruction_safety.so ✅ 必须

- [ ] 模型文件
  - [ ] best.engine ✅ 必须

- [ ] 配置文件
  - [ ] config.yaml ✅ 必须

- [ ] 测试验证
  - [ ] 边缘推理测试通过
  - [ ] 性能测试通过（<100ms）
```

---

## ⚠️ 重要说明

### **不要混用**

❌ **错误**：在 `edge_infer/plugins/` 下放 Python 代码
```python
# ❌ 错误：edge_infer/plugins/construction_safety/detector.py
class ConstructionSafetyDetector:
    def __init__(self):
        # ...
```

✅ **正确**：Python 代码在 `edge_infer_cloud/models/`
```python
# ✅ 正确：edge_infer_cloud/models/construction_safety/v1.0/scripts/train.py
def train_construction_safety_model():
    # ...
```

✅ **正确**：C++ 代码在 `edge_infer/src/plugins/`
```cpp
// ✅ 正确：edge_infer/src/plugins/construction_safety/construction_safety.cpp
class ConstructionSafetyPlugin : public PluginBase {
    // ...
};
```

---

## 📚 相关文档

- [施工安全实施方案](./CONSTRUCTION_SAFETY_IMPLEMENTATION_PLAN.md)
- [软件工程师工作流程](./SOFTWARE_ENGINEER_WORKFLOW.md)
- [跨部门实施指南](./DEPARTMENT_IMPLEMENTATION_GUIDE.md)

---

**维护者**: 空中智能体团队
**最后更新**: 2026-03-09
**版本**: V1.0
