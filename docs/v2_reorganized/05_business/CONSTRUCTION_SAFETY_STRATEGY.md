# 施工安全检测 - 渐进式实施策略

> **版本**: V1.0
> **日期**: 2026-03-09
> **核心问题**: 业务需求15种算法 vs 实际能力9类检测 vs 数据缺失
> **目标**: 快速上线 + 渐进扩展 + 数据优先级

---

## 📋 目录

1. [现状分析](#1-现状分析)
2. [渐进式实施策略](#2-渐进式实施策略)
3. [数据优先级排序](#3-数据优先级排序)
4. [模型演进路线](#4-模型演进路线)
5. [快速上线方案](#5-快速上线方案)
6. [通用策略框架](#6-通用策略框架)

---

## 1. 现状分析

### 1.1 业务需求 vs 实际能力

**业务需求（住建建筑部门）**：

| 优先级 | 算法 | 业务场景 | 边缘/云端 |
|--------|------|----------|----------|
| P0 | 安全帽识别 | 人员安全 | 边缘 |
| P0 | 反光衣识别 | 人员安全 | 边缘 |
| P0 | 消防通道占用 | 安全监管 | 边缘 |
| P1 | 安全带识别 | 高空作业 | 边缘 |
| P1 | 违规闯入 | 危险区域 | 边缘 |
| P1 | 脚手架安全 | 施工安全 | 边缘 |
| P1 | 临边防护 | 安全防护 | 边缘 |
| P2 | 基坑监测 | 结构安全 | 云端 |
| P2 | 墙面裂缝 | 质量检测 | 云端 |
| P2 | 混凝土缺陷 | 质量检测 | 云端 |
| P2 | 钢筋检测 | 质量检测 | 云端 |
| P2 | 平整度检测 | 质量检测 | 云端 |
| P2 | 施工进度 | 进度管理 | 云端 |
| P2 | 塔吊检测 | 设备管理 | 边缘 |
| P2 | 材料堆放 | 现场管理 | 边缘 |

**总计**：15种算法（9种边缘 + 6种云端）

---

**实际能力（当前模型）**：

| 类别 | 类名 | 数据来源 | 能力 |
|------|------|----------|------|
| 1 | person | VisDrone | ✅ 人员检测 |
| 2 | bicycle | VisDrone | ✅ 自行车 |
| 3 | car | VisDrone | ✅ 汽车 |
| 4 | van | VisDrone | ✅ 面包车 |
| 5 | truck | VisDrone | ✅ 卡车 |
| 6 | tricycle | VisDrone | ✅ 三轮车 |
| 7 | awning-tricycle | VisDrone | ✅ 遮阳三轮车 |
| 8 | bus | VisDrone | ✅ 公交车 |
| 9 | motor | VisDrone | ✅ 摩托车 |
| 10 | helmet | 安全帽数据集 | ✅ 安全帽检测 |
| 11 | reflective_vest | 反光衣数据集 | ✅ 反光衣检测 |
| 12 | head | 人头数据集 | ✅ 人头检测（未戴安全帽）|
| 13 | no_vest | 反光衣数据集 | ✅ 未穿反光衣 |

**总计**：13类检测能力

---

**能力缺口**：

| 业务需求 | 当前能力 | 缺口 | 优先级 |
|---------|---------|------|--------|
| ✅ 安全帽识别 | helmet + head | 已覆盖 | P0 |
| ✅ 反光衣识别 | reflective_vest + no_vest | 已覆盖 | P0 |
| ❌ 消防通道占用 | - | **缺失** | P0 |
| ❌ 安全带识别 | - | **缺失** | P1 |
| ⚠️ 违规闯入 | person + 区域判断 | 可实现 | P1 |
| ❌ 脚手架安全 | - | **缺失** | P1 |
| ❌ 临边防护 | - | **缺失** | P1 |
| ❌ 基坑监测 | - | **缺失** | P2 |
| ❌ 墙面裂缝 | - | **缺失** | P2 |
| ❌ 混凝土缺陷 | - | **缺失** | P2 |
| ❌ 钢筋检测 | - | **缺失** | P2 |
| ❌ 平整度检测 | - | **缺失** | P2 |
| ❌ 施工进度 | - | **缺失** | P2 |
| ⚠️ 塔吊检测 | truck + 车辆检测 | 部分覆盖 | P2 |
| ⚠️ 材料堆放 | 各类物体检测 | 部分覆盖 | P2 |

**结论**：
- ✅ **已覆盖**：2/15（安全帽、反光衣）
- ⚠️ **可实现**：3/15（违规闯入、塔吊、材料堆放）
- ❌ **缺失**：10/15（需要新增数据集）

---

### 1.2 数据现状

**已有数据集**：
- **VisDrone**：10,209张，9类（人、车、自行车等）
- **安全帽数据集**：~5,000张，4类（戴安全帽、未戴、颜色分类）
- **反光衣数据集**：~3,000张，2类（穿、未穿）
- **人头数据集**：~2,000张，1类（人头检测）

**缺失数据集**：
- 消防通道占用数据集 ❌
- 安全帶数据集 ❌
- 脚手架安全数据集 ❌
- 临边防护数据集 ❌
- 基坑监测数据集 ❌
- 裂缝检测数据集 ⚠️（有部分公开数据）
- 混凝土缺陷数据集 ❌
- 钢筋检测数据集 ❌

---

## 2. 渐进式实施策略

### 2.1 核心原则

```
快速上线 → 验证价值 → 渐进扩展 → 持续优化

原则1：不追求一次实现所有15种算法
原则2：优先实现有数据的算法（2+3=5种）
原则3：复用现有模型（VisDrone + 安全帽 + 反光衣）
原则4：数据驱动的渐进扩展（有数据再加算法）
```

---

### 2.2 三阶段实施

#### **阶段1：MVP上线（2周）** - 5种算法

**目标**：快速上线验证业务价值

| 算法 | 技术方案 | 数据来源 | 状态 |
|------|---------|---------|------|
| **安全帽识别** | YOLOv8（13类模型）| 安全帽数据集 | ✅ 已有 |
| **反光衣识别** | YOLOv8（13类模型）| 反光衣数据集 | ✅ 已有 |
| **违规闯入** | YOLOv8（person）+ 区域判断 | VisDrone | ✅ 可实现 |
| **塔吊检测** | YOLOv8（truck）+ 规则过滤 | VisDrone | ⚠️ 部分实现 |
| **材料堆放** | YOLOv8（多类）+ 场景分析 | VisDrone | ⚠️ 部分实现 |

**MVP价值**：
- ✅ 快速验证市场需求（2周上线）
- ✅ 获取客户反馈
- ✅ 验证技术可行性
- ✅ 收集真实场景数据

**模型策略**：
- 使用现有13类模型（VisDrone + helmet + vest + head）
- 不新增训练，直接部署
- 通过规则和逻辑组合实现业务功能

---

#### **阶段2：核心补充（1个月）** - +5种算法

**目标**：补充P0/P1优先级算法

| 算法 | 数据来源 | 标注成本 | 时间 |
|------|---------|---------|------|
| **消防通道占用** | 自建（500张）| ¥1,000 | 1周 |
| **安全带识别** | 自建（300张）| ¥600 | 1周 |
| **脚手架安全** | 自建（500张）| ¥1,000 | 1周 |
| **临边防护** | 自建（300张）| ¥600 | 1周 |
| **裂缝检测** | 公开+自建（500张）| ¥800 | 1周 |

**数据采集策略**：
- Week 1: 消防通道（工地现场采集500张）
- Week 2: 安全带（高空作业场景300张）
- Week 3: 脚手架+临边防护（施工现场800张）
- Week 4: 裂缝检测（公开数据+补充）

**总成本**：¥4,000 + 1个月

**模型扩展**：
- 在13类基础上扩展到18类
- 增量训练（冻结backbone，只训练新类别）

---

#### **阶段3：完整实现（2个月）** - +5种算法

**目标**：实现全部15种算法

| 算法 | 数据来源 | 难度 | 时间 |
|------|---------|------|------|
| **基坑监测** | 自建（1,000张）| 高 | 2周 |
| **混凝土缺陷** | 自建（800张）| 中 | 1周 |
| **钢筋检测** | 自建（600张）| 中 | 1周 |
| **平整度检测** | 自建（400张）| 高 | 2周 |
| **施工进度** | 自建（500张）| 高 | 2周 |

**总成本**：¥8,000 + 2个月

---

### 2.3 时间线

```
Week 1-2: MVP上线（5种算法）
  ↓ 验证市场价值
Week 3-6: 核心补充（+5种算法）
  ↓ 扩展核心能力
Week 7-14: 完整实现（+5种算法）
  ↓ 全功能上线
Week 15+: 持续优化
```

**总计**：3.5个月实现15种算法

---

## 3. 数据优先级排序

### 3.1 优先级评估矩阵

| 算法 | 业务价值 | 数据可得性 | 实现难度 | 优先级 |
|------|---------|-----------|---------|--------|
| 安全帽识别 | ⭐⭐⭐⭐⭐ | ✅ 已有 | 低 | **P0** |
| 反光衣识别 | ⭐⭐⭐⭐⭐ | ✅ 已有 | 低 | **P0** |
| 违规闯入 | ⭐⭐⭐⭐ | ✅ 已有 | 低 | **P0** |
| 消防通道占用 | ⭐⭐⭐⭐⭐ | ⚠️ 易采集 | 中 | **P0** |
| 安全带识别 | ⭐⭐⭐⭐ | ⚠️ 需采集 | 中 | **P1** |
| 脚手架安全 | ⭐⭐⭐ | ⚠️ 需采集 | 中 | **P1** |
| 临边防护 | ⭐⭐⭐ | ⚠️ 需采集 | 中 | **P1** |
| 裂缝检测 | ⭐⭐⭐ | ✅ 有公开 | 中 | **P1** |
| 塔吊检测 | ⭐⭐ | ✅ 部分覆盖 | 低 | **P2** |
| 材料堆放 | ⭐⭐ | ✅ 部分覆盖 | 低 | **P2** |
| 基坑监测 | ⭐⭐⭐ | ⚠️ 需采集 | 高 | **P2** |
| 混凝土缺陷 | ⭐⭐ | ⚠️ 需采集 | 中 | **P2** |
| 钢筋检测 | ⭐⭐ | ⚠️ 需采集 | 中 | **P2** |
| 平整度检测 | ⭐ | ⚠️ 需采集 | 高 | **P2** |
| 施工进度 | ⭐⭐⭐ | ⚠️ 需采集 | 高 | **P2** |

---

### 3.2 数据获取策略

#### **策略1：复用现有数据（优先）**

| 算法 | 复用数据 | 实现方式 |
|------|---------|---------|
| 违规闯入 | VisDrone (person) | person + 区域多边形判断 |
| 塔吊检测 | VisDrone (truck) | 大型车辆 + 高度判断 |
| 材料堆放 | VisDrone (多类) | 物体密度 + 场景分析 |

**违规闯入实现示例**:

```python
class IntrusionDetector:
    def __init__(self, danger_zones):
        """
        danger_zones: 危险区域多边形列表
        [
            {"name": "zone1", "points": [[x1,y1], [x2,y2], ...]},
            ...
        ]
        """
        self.danger_zones = danger_zones
        self.yolo = YOLOv8('construction_safety.engine')  # 13类模型
        
    def detect(self, image):
        """检测违规闯入"""
        # 1. YOLOv8检测所有目标
        detections = self.yolo.detect(image)
        
        # 2. 筛选person类别
        persons = [d for d in detections if d['class'] == 'person']
        
        # 3. 判断是否在危险区域内
        intrusions = []
        for person in persons:
            point = (person['center_x'], person['center_y'])
            
            for zone in self.danger_zones:
                if self.point_in_polygon(point, zone['points']):
                    intrusions.append({
                        'person': person,
                        'zone': zone['name'],
                        'type': 'intrusion'
                    })
        
        return intrusions
    
    def point_in_polygon(self, point, polygon):
        """判断点是否在多边形内"""
        from shapely.geometry import Point, Polygon
        return Polygon(polygon).contains(Point(point))
```

**优势**：
- ✅ 无需新增数据
- ✅ 立即可用
- ✅ 成本为零

---

#### **策略2：快速采集（1-2周）**

**消防通道占用**：

```
采集对象：
- 被占用的消防通道（车辆、杂物）
- 正常消防通道（对比）

采集方式：
- 工地现场拍摄（500张）
- 网络爬虫（新闻图片，300张）
- 合成数据（Blender仿真，200张）

标注方式：
- 检测框：消防通道区域
- 分类：占用/未占用

标注成本：
- 1,000张 × ¥1/张 = ¥1,000
```

**数据增强策略**:
```python
# 消防通道数据增强
augmentations = [
    RandomCrop(height=640, width=640),  # 裁剪
    HorizontalFlip(p=0.5),              # 翻转
    RandomBrightnessContrast(p=0.3),    # 亮度对比度
    Mosaic(p=0.5),                      # Mosaic增强
]
# 1,000张 → 4,000张（增强后）
```

---

#### **策略3：迁移学习（低成本）**

**裂缝检测**：

```
公开数据集：
- SDNET2018: 56,000张裂缝图像（混凝土桥面、路面）
- CFD: 1,188张裂缝图像
- DeepCrack: 300张路面裂缝

迁移学习策略：
1. 在SDNET2018上预训练
2. 在施工场景裂缝上微调（500张）
3. 部署到边缘

成本：
- 数据采集：¥500（补充标注）
- 训练时间：1天
```

---

#### **策略4：规则+模型组合（无需数据）**

**部分算法可以通过规则实现，无需新增数据**：

| 算法 | 规则策略 | 所需数据 |
|------|---------|---------|
| **施工进度** | 时序变化检测（RCMT）+ 建筑物计数 | RCMT已有 |
| **平整度检测** | 深度估计 + 统计分析 | 无需标注 |

---

## 4. 模型演进路线

### 4.1 版本规划

#### **V1.0 - MVP版本（Week 1-2）**

**模型**: YOLOv8-m (13类)

```
classes = [
    # VisDrone (9类)
    'person', 'bicycle', 'car', 'van', 'truck',
    'tricycle', 'awning-tricycle', 'bus', 'motor',
    
    # 安全+反光衣 (4类)
    'helmet', 'reflective_vest', 'head', 'no_vest'
]
```

**能力**:
- ✅ 安全帽识别（helmet + head）
- ✅ 反光衣识别（reflective_vest + no_vest）
- ✅ 违规闯入（person + 区域判断）
- ⚠️ 塔吊检测（truck + 规则）
- ⚠️ 材料堆放（多类 + 场景分析）

**部署**: edge_infer/plugins/construction_safety_v1/

---

#### **V2.0 - 扩展版本（Week 3-6）**

**模型**: YOLOv8-m (18类)

```
classes = [
    # V1.0 (13类)
    'person', 'bicycle', 'car', 'van', 'truck',
    'tricycle', 'awning-tricycle', 'bus', 'motor',
    'helmet', 'reflective_vest', 'head', 'no_vest',
    
    # V2.0新增 (5类)
    'fire_extinguisher',    # 消防通道占用（间接判断）
    'safety_belt',          # 安全带
    'scaffolding',          # 脚手架
    'edge_protection',      # 临边防护
    'crack'                 # 裂缝
]
```

**增量训练策略**:
```python
# 1. 加载V1.0模型
model = YOLO('construction_safety_v1.pt')

# 2. 修改最后一层（13类 → 18类）
model.model.nc = 18  # 类别数

# 3. 冻结backbone，只训练新类别
for param in model.model.parameters():
    param.requires_grad = False
    
# 解冻最后一层
for param in model.model.head.parameters():
    param.requires_grad = True

# 4. 增量训练
model.train(
    data='construction_v2.yaml',
    epochs=50,
    freeze=10  # 冻结前10层
)
```

**优势**:
- ✅ 保留V1.0能力
- ✅ 快速扩展新类别
- ✅ 训练时间短（50 epochs）

---

#### **V3.0 - 完整版本（Week 7-14）**

**模型**: YOLOv8-m (23类) + 专业模型

```
# 边缘检测模型（23类）
edge_classes = [
    # V1.0 (13类)
    ...,
    # V2.0 (5类)
    ...,
    # V3.0新增 (5类)
    'tower_crane',          # 塔吊
    'material_pile',        # 材料堆放
    'excavator',            # 挖掘机
    'crane',                # 起重机
    'concrete_mixer'        # 混凝土搅拌机
]

# 云端专业模型
cloud_models = {
    'foundation_monitor': '基坑监测模型',
    'concrete_defect': '混凝土缺陷模型',
    'rebar_detection': '钢筋检测模型',
    'flatness_check': '平整度检测模型',
    'progress_tracking': '施工进度模型'
}
```

---

### 4.2 模型部署策略

**边缘设备（Jetson Orin NX）**:

```
内存分配：
- 常驻模型（V1.0）: 13类，~400MB
- 动态加载（V2.0/V3.0）: 按需加载

加载策略：
- 实时任务：加载V1.0（常驻）
- 巡检任务：按需加载V2.0/V3.0
- 专业分析：云端推理
```

---

## 5. 快速上线方案

### 5.1 MVP配置（Week 1-2）

**edge_infer插件**: `construction_safety_v1`

**config.yaml**:

```yaml
plugin:
  name: "construction_safety"
  version: "1.0.0"
  description: "施工安全检测MVP版本（5种算法）"

model:
  path: "models/construction_safety_v1.engine"
  type: "yolov8"
  classes:
    - name: person
      description: "人员检测（用于违规闯入）"
    - name: helmet
      description: "安全帽检测"
    - name: head
      description: "未戴安全帽的人头"
    - name: reflective_vest
      description: "反光衣检测"
    - name: no_vest
      description: "未穿反光衣"
    - name: truck
      description: "卡车（用于塔吊初步检测）"
  
algorithms:
  - name: "helmet_detection"
    type: "composite"
    description: "安全帽识别"
    logic:
      - "检测helmet类别"
      - "检测head类别（未戴安全帽）"
      - "计算佩戴率：helmet / (helmet + head)"
      
  - name: "vest_detection"
    type: "composite"
    description: "反光衣识别"
    logic:
      - "检测reflective_vest类别"
      - "检测no_vest类别（未穿反光衣）"
      - "计算穿着率：vest / (vest + no_vest)"
      
  - name: "intrusion_detection"
    type: "composite"
    description: "违规闯入检测"
    logic:
      - "检测person类别"
      - "判断person是否在danger_zone内"
      - "输出闯入事件"
    config:
      danger_zones:
        - name: "zone1"
          points: [[100, 100], [200, 100], [200, 200], [100, 200]]
        - name: "zone2"
          points: [[300, 300], [400, 300], [400, 400], [300, 400]]
          
  - name: "tower_crane_detection"
    type: "rule_based"
    description: "塔吊检测（初步）"
    logic:
      - "检测truck类别"
      - "过滤：体积 > 阈值 且 高度 > 阈值"
      - "输出疑似塔吊目标"
    config:
      min_area: 10000  # 最小面积
      min_height: 100  # 最小高度
      
  - name: "material_pile_detection"
    type: "scene_analysis"
    description: "材料堆放检测（初步）"
    logic:
      - "检测所有物体类别"
      - "计算物体密度"
      - "密度 > 阈值 → 材料堆放"
    config:
      density_threshold: 0.3

deployment:
  device: "jetson_orin_nx"
  inference_time: "<100ms"
  model_size: "400MB"
```

---

### 5.2 API接口

**edge_infer_cloud API**:

```python
# edge_infer_cloud/api/routes/construction.py

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/construction", tags=["施工安全"])

class HelmetDetectionRequest(BaseModel):
    device_id: str
    image: str  # 图像URL或base64
    
class IntrusionZone(BaseModel):
    name: str
    points: List[List[float]]

class IntrusionDetectionRequest(BaseModel):
    device_id: str
    image: str
    danger_zones: List[IntrusionZone]

@router.post("/helmet")
async def helmet_detection(request: HelmetDetectionRequest):
    """
    安全帽识别
    
    返回：
    - 总人数
    - 戴安全帽数量
    - 未戴安全帽数量
    - 佩戴率
    """
    # 调用边缘推理
    result = await edge_infer(request.device_id, 'helmet_detection', request.image)
    
    return {
        "total": result['total'],
        "with_helmet": result['helmet'],
        "without_helmet": result['head'],
        "compliance_rate": result['helmet'] / result['total']
    }

@router.post("/vest")
async def vest_detection(request: HelmetDetectionRequest):
    """
    反光衣识别
    """
    result = await edge_infer(request.device_id, 'vest_detection', request.image)
    
    return {
        "total": result['total'],
        "with_vest": result['vest'],
        "without_vest": result['no_vest'],
        "compliance_rate": result['vest'] / result['total']
    }

@router.post("/intrusion")
async def intrusion_detection(request: IntrusionDetectionRequest):
    """
    违规闯入检测
    """
    result = await edge_infer(
        request.device_id, 
        'intrusion_detection', 
        request.image,
        config={'danger_zones': request.danger_zones}
    )
    
    return {
        "intrusion_count": len(result['intrusions']),
        "intrusions": result['intrusions'],
        "alert": len(result['intrusions']) > 0
    }
```

---

### 5.3 前端展示

**检测界面**:

```
┌─────────────────────────────────────┐
│  施工安全监测                        │
├─────────────────────────────────────┤
│  [实时画面]                          │
│  ┌─────────────────────────────┐   │
│  │  👷 👷 (安全帽)              │   │
│  │  👷 👷 (无安全帽) ⚠️         │   │
│  │  🚧 (危险区域)               │   │
│  └─────────────────────────────┘   │
├─────────────────────────────────────┤
│  统计信息：                          │
│  ✅ 安全帽佩戴率：85% (17/20)       │
│  ✅ 反光衣穿着率：90% (18/20)       │
│  ⚠️  违规闯入：2人                  │
├─────────────────────────────────────┤
│  [历史记录] [导出报告] [设置]       │
└─────────────────────────────────────┘
```

---

## 6. 通用策略框架

### 6.1 数据缺失 → 算法实现的通用策略

```
流程：
1. 检查数据可用性
   ├─ ✅ 有数据 → 直接训练
   ├─ ⚠️ 部分数据 → 迁移学习
   └─ ❌ 无数据 → 规则/组合实现
   
2. 选择实现策略
   ├─ 策略1：复用现有模型（零成本）
   ├─ 策略2：快速采集数据（1-2周）
   ├─ 策略3：迁移学习（低成本）
   ├─ 策略4：规则+模型组合（无需数据）
   └─ 策略5：暂缓实现（等数据）
   
3. MVP快速验证
   ├─ 先上核心功能（2-5种算法）
   ├─ 获取客户反馈
   └─ 基于反馈扩展
   
4. 渐进式扩展
   ├─ 收集真实场景数据
   ├─ 增量训练新类别
   └─ 持续优化模型
```

---

### 6.2 决策树

```
是否需要新增算法？
  ├─ 有现成数据？
  │  ├─ YES → 直接训练（1-2周）
  │  └─ NO → 是否可复用现有模型？
  │     ├─ YES → 规则/组合实现（1-3天）
  │     └─ NO → 数据采集难度？
  │        ├─ 低（1-2周采集）→ 快速采集+训练（2-3周）
  │        ├─ 中（1个月采集）→ 暂缓，等MVP验证
  │        └─ 高（>2个月）→ 降级为云端服务
```

---

### 6.3 适用于所有部门的通用框架

| 部门 | 已有能力 | 需要新增 | MVP策略 | 扩展策略 |
|------|---------|---------|---------|---------|
| **应急管理** | 通用检测 | 灾害专用 | 通用检测+规则 | 采集灾害数据 |
| **住建建筑** | 13类检测 | 10类专用 | 5类MVP | 渐进扩展 |
| **城管** | 通用检测 | 违建检测 | 变化检测（RCMT）| 采集违建数据 |
| **国土** | RCMT | 无 | RCMT直接使用 | - |
| **环保** | 通用检测 | 专用检测 | 水体/烟雾检测 | 采集环保数据 |
| **电力** | 通用检测 | 电力设施 | 绝缘子检测 | 采集电力数据 |

---

## 7. 总结与建议

### 7.1 核心策略

```diff
❌ 错误思路：
- 追求一次实现15种算法
- 等所有数据集准备好再开始
- 从零开始训练每个模型

✅ 正确思路：
+ MVP快速上线（5种算法，2周）
+ 复用现有模型（VisDrone + 安全帽 + 反光衣）
+ 渐进式扩展（V1.0 → V2.0 → V3.0）
+ 数据驱动的算法扩展（有数据再加）
```

---

### 7.2 立即行动

**Week 1-2（MVP上线）**:

```bash
算法工程师：
- [ ] 部署13类模型到边缘设备
- [ ] 实现5种算法的逻辑（helmet, vest, intrusion, crane, material）
- [ ] 测试边缘推理性能（<100ms）

软件工程师：
- [ ] 开发construction_safety_v1插件
- [ ] 开发3个API接口（/helmet, /vest, /intrusion）
- [ ] 前端展示界面

产品工程师：
- [ ] 对接客户，部署MVP版本
- [ ] 收集客户反馈
- [ ] 收集真实场景数据（消防通道、安全带等）
```

**Week 3-6（核心补充）**:

```bash
- [ ] 采集消防通道数据（500张）
- [ ] 采集安全帽数据（300张）
- [ ] 采集脚手架数据（500张）
- [ ] 增量训练V2.0模型（18类）
- [ ] 部署V2.0版本
```

---

### 7.3 成功关键

1. ✅ **快速上线验证价值**（2周MVP）
2. ✅ **复用现有能力**（13类模型）
3. ✅ **数据驱动扩展**（有数据再加算法）
4. ✅ **渐进式迭代**（V1.0 → V2.0 → V3.0）
5. ✅ **客户反馈导向**（基于真实需求调整）

---

**维护者**: 空中智能体团队
**最后更新**: 2026-03-09
**版本**: V1.0
**文档位置**: docs/v2_reorganized/05_business/CONSTRUCTION_SAFETY_STRATEGY.md
