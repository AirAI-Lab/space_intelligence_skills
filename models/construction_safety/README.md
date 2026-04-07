# 施工安全监测系统

**版本**: v1.0
**团队**: 空中智能体团队

---

## 方案

| 模型 | 任务 | 类别 | 数据集 | FPS |
|------|------|------|--------|-----|
| **YOLOv8-Pose** | 检测+行为 | 15类 | 6600张 | 30+ |

---

## 特点

**为什么只需要1个模型？**
- 所有目标都有固定形状（人员、装备、机械）
- 样本充足（现场采集）
- 不需要开放词汇分割

---

## 任务

### 安全装备（4类）
- person_with_helmet, person_no_helmet
- person_with_vest, person_no_vest

### 危险区域（3类）
- person_in_danger_zone, unauthorized_access, cross_safety_line

### 危险行为（5类）
- climbing_ladder, fall_detection, smoking_fire
- not_watching_machine, unsafe_distance

### 机械设备（3类）
- crane_operation, excavator_operation, truck_operation

---

## 快速开始

```bash
# 安装
pip install -r requirements.txt

# 训练
python models/yolo/train.py --config configs/construction_safety.yaml

# 推理
python models/unified.py --config configs/construction_safety.yaml
```

---

## 文档

- **[完整手册](docs/MANUAL.md)** - 技术细节、训练、部署

---

## 结构

```
construction_safety/
├── configs/
│   └── construction_safety.yaml
├── models/
├── scripts/
├── deployment/
└── docs/
    └── MANUAL.md
```

---

**维护者**: 空中智能体团队
