# 园区监测系统

**版本**: v1.0
**团队**: 空中智能体团队

---

## 方案

| 模型 | 任务 | 类别 | 数据集 | FPS |
|------|------|------|--------|-----|
| **YOLOv8-Pose** | 检测+行为 | 12类 | 4500张 | 30+ |
| **YOLOv8-Obb** | 停车位 | 1类 | 500张 | 25+ |

---

## 任务

### 周界安全（4类）
- intruding_person, climbing_wall, smashing_window, prying_door

### 人员行为（5类）
- person_fall, fighting, smoking, abnormal_loitering, running

### 车辆管理（3类）
- illegal_parking, vehicle_intrusion, vehicle_counting

### 停车位（1类）- OBB
- parking_spot（旋转框检测）

---

## 快速开始

```bash
# 安装
pip install -r requirements.txt

# 训练
python models/yolo/train.py --config configs/park_monitoring.yaml

# 推理
python models/unified.py --config configs/park_monitoring.yaml
```

---

## 文档

- **[完整手册](docs/MANUAL.md)** - 技术细节、训练、部署

---

## 结构

```
park_monitoring/
├── configs/
│   └── park_monitoring.yaml
├── models/
├── scripts/
├── deployment/
└── docs/
    └── MANUAL.md
```

---

**维护者**: 空中智能体团队
