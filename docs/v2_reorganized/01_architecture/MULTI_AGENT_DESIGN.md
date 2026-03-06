# 空中空间智能体 - 技术架构设计

> **项目**: SkyEdge AI System  
> **版本**: V2.0 (3智能体架构)  
> **更新日期**: 2026-03-06  
> **状态**: 设计阶段

---

## 目录

1. [架构概述](#1-架构概述)
2. [感知智能体设计](#2-感知智能体设计)
3. [认知智能体设计](#3-认知智能体设计)
4. [行动智能体设计](#4-行动智能体设计)
5. [云边协同设计](#5-云边协同设计)
6. [智能体通信](#6-智能体通信)
7. [接口规范](#7-接口规范)

---

## 1. 架构概述

### 1.1 设计原则

| 原则 | 说明 |
|------|------|
| **简洁** | 3个核心智能体，清晰的"看-想-做"逻辑 |
| **解耦** | 智能体之间通过消息通信，松耦合 |
| **可扩展** | 每个智能体内部可添加新的能力模块 |
| **渐进式** | 支持分阶段实现和部署 |

### 1.2 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        空中空间智能体系统                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     云边协同平台                          │   │
│  │                                                         │   │
│  │   设备管理 │ 模型管理 │ 训练服务 │ OTA升级 │ 监控告警    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↕ MQTT/HTTP                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     边缘智能体系统                        │   │
│  │                                                         │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐  │   │
│  │  │   感知智能体   │ │   认知智能体   │ │   行动智能体   │  │   │
│  │  │  Perception   │ │   Cognition   │ │    Action     │  │   │
│  │  │               │ │               │ │               │  │   │
│  │  │  目标识别     │ │  空间推理     │ │  自主飞行     │  │   │
│  │  │  变化检测     │ │  路径规划     │ │  协同作业     │  │   │
│  │  │  语义分割     │ │  任务分配     │ │  避障导航     │  │   │
│  │  │  三维重建     │ │  风险评估     │ │  人机交互     │  │   │
│  │  │  目标跟踪     │ │  变化分析     │ │  应急处理     │  │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘  │   │
│  │         ↕                  ↕                  ↕         │   │
│  │                    智能体消息总线                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 智能体职责

| 智能体 | 核心职责 | 输入 | 输出 |
|--------|----------|------|------|
| **感知智能体** | 理解环境 | 图像/视频/传感器数据 | 检测结果/变化掩码/语义图 |
| **认知智能体** | 分析决策 | 感知结果 + 任务目标 | 路径/任务分配/决策 |
| **行动智能体** | 执行任务 | 认知决策 + 控制指令 | 飞行动作/协同行为 |

---

## 2. 感知智能体设计

### 2.1 能力模块

感知智能体内部采用**模块化设计**，每个能力独立实现：

```
┌─────────────────────────────────────────────┐
│              感知智能体 (Perception)         │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │          能力调度器                  │   │
│  │   根据任务选择合适的能力模块          │   │
│  └─────────────────────────────────────┘   │
│                    ↓                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │目标识别 │ │变化检测 │ │语义分割 │ ...   │
│  │ Module  │ │ Module  │ │ Module  │       │
│  └─────────┘ └─────────┘ └─────────┘       │
│                    ↓                        │
│  ┌─────────────────────────────────────┐   │
│  │          结果融合器                  │   │
│  │   整合多模块输出，生成统一感知结果     │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

### 2.2 核心接口

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

class PerceptionCapability(Enum):
    """感知能力类型"""
    OBJECT_DETECTION = "object_detection"
    CHANGE_DETECTION = "change_detection"
    SEMANTIC_SEGMENTATION = "semantic_segmentation"
    THREED_RECONSTRUCTION = "3d_reconstruction"
    OBJECT_TRACKING = "object_tracking"
    POSE_ESTIMATION = "pose_estimation"

@dataclass
class PerceptionResult:
    """感知结果"""
    capability: PerceptionCapability
    timestamp: float
    confidence: float
    data: Dict[str, Any]  # 具体结果数据
    
class PerceptionModule(ABC):
    """感知模块基类"""
    
    @property
    @abstractmethod
    def capability(self) -> PerceptionCapability:
        """模块能力"""
        pass
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> PerceptionResult:
        """处理输入数据"""
        pass
    
    @abstractmethod
    def update_model(self, model_path: str) -> bool:
        """更新模型（支持OTA）"""
        pass


class PerceptionAgent:
    """感知智能体"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.modules: Dict[PerceptionCapability, PerceptionModule] = {}
        self.active_capabilities: List[PerceptionCapability] = []
        
    def register_module(self, module: PerceptionModule):
        """注册能力模块"""
        self.modules[module.capability] = module
        
    def activate(self, capability: PerceptionCapability):
        """激活能力"""
        if capability in self.modules and capability not in self.active_capabilities:
            self.active_capabilities.append(capability)
    
    def deactivate(self, capability: PerceptionCapability):
        """停用能力"""
        if capability in self.active_capabilities:
            self.active_capabilities.remove(capability)
    
    def perceive(self, sensor_data: Dict[str, Any]) -> List[PerceptionResult]:
        """执行感知"""
        results = []
        
        for capability in self.active_capabilities:
            module = self.modules.get(capability)
            if module:
                result = module.process(sensor_data)
                results.append(result)
        
        return results
    
    def update_model(self, capability: PerceptionCapability, model_path: str) -> bool:
        """更新模型（OTA）"""
        module = self.modules.get(capability)
        if module:
            return module.update_model(model_path)
        return False
```

### 2.3 能力模块实现示例

#### 目标识别模块

```python
class ObjectDetectionModule(PerceptionModule):
    """目标识别模块"""
    
    @property
    def capability(self) -> PerceptionCapability:
        return PerceptionCapability.OBJECT_DETECTION
    
    def __init__(self, model_path: str = None):
        self.model = None
        self.class_names = []
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """加载模型"""
        # 实际实现加载YOLOv8或其他检测模型
        from edge_infer.plugins.object_detection import YOLOv8Detector
        self.model = YOLOv8Detector(model_path)
        
    def process(self, input_data: Dict[str, Any]) -> PerceptionResult:
        """处理图像"""
        image = input_data.get("image")
        if image is None:
            return PerceptionResult(
                capability=self.capability,
                timestamp=time.time(),
                confidence=0.0,
                data={"error": "no image"}
            )
        
        # 执行检测
        detections = self.model.detect(image)
        
        return PerceptionResult(
            capability=self.capability,
            timestamp=time.time(),
            confidence=max([d.confidence for d in detections], default=0.0),
            data={
                "detections": [
                    {
                        "class_name": d.class_name,
                        "confidence": d.confidence,
                        "bbox": d.bbox
                    }
                    for d in detections
                ]
            }
        )
    
    def update_model(self, model_path: str) -> bool:
        """热更新模型"""
        try:
            self.load_model(model_path)
            return True
        except Exception as e:
            print(f"Model update failed: {e}")
            return False
```

#### 变化检测模块

```python
class ChangeDetectionModule(PerceptionModule):
    """变化检测模块"""
    
    @property
    def capability(self) -> PerceptionCapability:
        return PerceptionCapability.CHANGE_DETECTION
    
    def __init__(self, model_path: str = None):
        self.model = None
        self.history_images = []
        self.max_history = 10
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """加载RCMT模型"""
        from edge_infer.plugins.change_detection import RCMTDetector
        self.model = RCMTDetector(model_path)
        
    def process(self, input_data: Dict[str, Any]) -> PerceptionResult:
        """检测变化"""
        current_image = input_data.get("image")
        if current_image is None:
            return PerceptionResult(
                capability=self.capability,
                timestamp=time.time(),
                confidence=0.0,
                data={"error": "no image"}
            )
        
        # 如果有历史图像，执行变化检测
        changes = None
        if self.history_images:
            earlier_image = self.history_images[-1]  # 最近的历史图像
            changes = self.model.detect(earlier_image, current_image)
        
        # 更新历史
        self.history_images.append(current_image)
        if len(self.history_images) > self.max_history:
            self.history_images.pop(0)
        
        return PerceptionResult(
            capability=self.capability,
            timestamp=time.time(),
            confidence=changes.confidence if changes else 0.0,
            data={
                "change_mask": changes.mask if changes else None,
                "change_regions": changes.regions if changes else []
            }
        )
    
    def update_model(self, model_path: str) -> bool:
        """热更新模型"""
        try:
            self.load_model(model_path)
            return True
        except Exception as e:
            print(f"Model update failed: {e}")
            return False
```

---

## 3. 认知智能体设计

### 3.1 能力模块

```
┌─────────────────────────────────────────────┐
│              认知智能体 (Cognition)          │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │          认知调度器                  │   │
│  │   根据场景选择合适的认知能力          │   │
│  └─────────────────────────────────────┘   │
│                    ↓                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │路径规划 │ │任务分配 │ │风险评估 │ ...   │
│  │ Module  │ │ Module  │ │ Module  │       │
│  └─────────┘ └─────────┘ └─────────┘       │
│                    ↓                        │
│  ┌─────────────────────────────────────┐   │
│  │          决策融合器                  │   │
│  │   综合多维度认知，生成最优决策        │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

### 3.2 核心接口

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

class CognitionCapability(Enum):
    """认知能力类型"""
    PATH_PLANNING = "path_planning"
    TASK_ALLOCATION = "task_allocation"
    RISK_ASSESSMENT = "risk_assessment"
    CHANGE_ANALYSIS = "change_analysis"
    SPATIAL_REASONING = "spatial_reasoning"

@dataclass
class CognitionResult:
    """认知结果"""
    capability: CognitionCapability
    timestamp: float
    confidence: float
    action: Dict[str, Any]  # 推荐的行动

class CognitionModule(ABC):
    """认知模块基类"""
    
    @property
    @abstractmethod
    def capability(self) -> CognitionCapability:
        """模块能力"""
        pass
    
    @abstractmethod
    def process(self, perception_results: List[PerceptionResult], 
                context: Dict[str, Any]) -> CognitionResult:
        """处理感知结果，生成决策"""
        pass


class CognitionAgent:
    """认知智能体"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.modules: Dict[CognitionCapability, CognitionModule] = {}
        
    def register_module(self, module: CognitionModule):
        """注册能力模块"""
        self.modules[module.capability] = module
        
    def think(self, perception_results: List[PerceptionResult], 
              context: Dict[str, Any]) -> List[CognitionResult]:
        """执行认知"""
        results = []
        
        # 根据感知结果和上下文选择激活的模块
        active_modules = self._select_modules(perception_results, context)
        
        for capability in active_modules:
            module = self.modules.get(capability)
            if module:
                result = module.process(perception_results, context)
                results.append(result)
        
        return results
    
    def _select_modules(self, perception_results: List[PerceptionResult], 
                       context: Dict[str, Any]) -> List[CognitionCapability]:
        """选择激活的模块"""
        # 简化版：根据任务类型选择
        task_type = context.get("task_type")
        
        if task_type == "patrol":
            return [CognitionCapability.PATH_PLANNING]
        elif task_type == "multi_agent":
            return [CognitionCapability.TASK_ALLOCATION, CognitionCapability.PATH_PLANNING]
        elif task_type == "monitoring":
            return [CognitionCapability.CHANGE_ANALYSIS]
        else:
            return [CognitionCapability.SPATIAL_REASONING]
```

### 3.3 能力模块实现示例

#### 路径规划模块

```python
import heapq
from typing import List, Tuple

@dataclass
class Position:
    """位置"""
    lat: float
    lon: float
    alt: float
    
    def distance_to(self, other: 'Position') -> float:
        """计算距离"""
        # Haversine公式
        from math import radians, sin, cos, sqrt, asin
        lat1, lon1 = radians(self.lat), radians(self.lon)
        lat2, lon2 = radians(other.lat), radians(other.lon)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        R = 6371000
        return R * c

@dataclass
class Waypoint:
    """航点"""
    position: Position
    action: str = None

class PathPlanningModule(CognitionModule):
    """路径规划模块"""
    
    @property
    def capability(self) -> CognitionCapability:
        return CognitionCapability.PATH_PLANNING
    
    def process(self, perception_results: List[PerceptionResult], 
                context: Dict[str, Any]) -> CognitionResult:
        """规划路径"""
        start = context.get("start_position")
        goal = context.get("goal_position")
        obstacles = context.get("obstacles", [])
        
        # A*路径规划
        path = self._astar(start, goal, obstacles)
        
        return CognitionResult(
            capability=self.capability,
            timestamp=time.time(),
            confidence=0.9,
            action={
                "type": "follow_path",
                "waypoints": [
                    {"lat": wp.position.lat, "lon": wp.position.lon, "alt": wp.position.alt}
                    for wp in path
                ]
            }
        )
    
    def _astar(self, start: Position, goal: Position, obstacles: List) -> List[Waypoint]:
        """A*算法"""
        # 简化实现
        # 实际应考虑障碍物、禁飞区等
        
        # 简单返回直线路径
        return [
            Waypoint(position=start),
            Waypoint(position=goal)
        ]
```

#### 任务分配模块

```python
class TaskAllocationModule(CognitionModule):
    """任务分配模块（拍卖算法）"""
    
    @property
    def capability(self) -> CognitionCapability:
        return CognitionCapability.TASK_ALLOCATION
    
    def process(self, perception_results: List[PerceptionResult], 
                context: Dict[str, Any]) -> CognitionResult:
        """分配任务"""
        tasks = context.get("tasks", [])
        agents = context.get("agents", [])
        
        # 拍卖算法分配
        allocations = self._auction_allocate(tasks, agents)
        
        return CognitionResult(
            capability=self.capability,
            timestamp=time.time(),
            confidence=0.85,
            action={
                "type": "task_allocation",
                "allocations": allocations
            }
        )
    
    def _auction_allocate(self, tasks: List, agents: List) -> Dict[str, str]:
        """拍卖算法"""
        allocations = {}
        
        for task in tasks:
            # 收集竞价
            bids = {}
            for agent in agents:
                bid = self._calculate_bid(agent, task)
                bids[agent["id"]] = bid
            
            # 最高价中标
            if bids:
                winner = max(bids, key=bids.get)
                allocations[task["id"]] = winner
        
        return allocations
    
    def _calculate_bid(self, agent: Dict, task: Dict) -> float:
        """计算竞价"""
        # 基于距离、能力、负载计算
        distance = self._get_distance(agent["position"], task["location"])
        capability_match = len(set(agent["capabilities"]) & set(task["requirements"]))
        current_load = agent.get("current_tasks", 0)
        
        bid = 100 - distance * 0.1 + capability_match * 10 - current_load * 5
        return max(0, bid)
    
    def _get_distance(self, pos1: Dict, pos2: Dict) -> float:
        """计算距离"""
        p1 = Position(pos1["lat"], pos1["lon"], pos1.get("alt", 0))
        p2 = Position(pos2["lat"], pos2["lon"], pos2.get("alt", 0))
        return p1.distance_to(p2)
```

---

## 4. 行动智能体设计

### 4.1 能力模块

```
┌─────────────────────────────────────────────┐
│              行动智能体 (Action)             │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │          行动调度器                  │   │
│  │   根据决策选择合适的行动模块          │   │
│  └─────────────────────────────────────┘   │
│                    ↓                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │自主飞行 │ │协同作业 │ │避障导航 │ ...   │
│  │ Module  │ │ Module  │ │ Module  │       │
│  └─────────┘ └─────────┘ └─────────┘       │
│                    ↓                        │
│  ┌─────────────────────────────────────┐   │
│  │          飞控接口                    │   │
│  │   与底层飞控系统通信                  │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

### 4.2 核心接口

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum

class ActionCapability(Enum):
    """行动能力类型"""
    AUTONOMOUS_FLIGHT = "autonomous_flight"
    COLLABORATIVE_WORK = "collaborative_work"
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"
    HUMAN_INTERACTION = "human_interaction"
    EMERGENCY_HANDLING = "emergency_handling"

@dataclass
class ActionResult:
    """行动结果"""
    capability: ActionCapability
    success: bool
    timestamp: float
    details: Dict[str, Any]

class ActionModule(ABC):
    """行动模块基类"""
    
    @property
    @abstractmethod
    def capability(self) -> ActionCapability:
        """模块能力"""
        pass
    
    @abstractmethod
    def execute(self, action: Dict[str, Any]) -> ActionResult:
        """执行行动"""
        pass

class ActionAgent:
    """行动智能体"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.modules: Dict[ActionCapability, ActionModule] = {}
        self.current_action = None
        
    def register_module(self, module: ActionModule):
        """注册能力模块"""
        self.modules[module.capability] = module
        
    def act(self, cognition_results: List[CognitionResult]) -> List[ActionResult]:
        """执行行动"""
        results = []
        
        for cognition in cognition_results:
            action = cognition.action
            action_type = action.get("type")
            
            # 选择对应的模块
            module = self._select_module(action_type)
            if module:
                result = module.execute(action)
                results.append(result)
        
        return results
    
    def _select_module(self, action_type: str) -> ActionModule:
        """选择模块"""
        mapping = {
            "follow_path": ActionCapability.AUTONOMOUS_FLIGHT,
            "task_allocation": ActionCapability.COLLABORATIVE_WORK,
            "avoid_obstacle": ActionCapability.OBSTACLE_AVOIDANCE,
            "emergency": ActionCapability.EMERGENCY_HANDLING
        }
        
        capability = mapping.get(action_type)
        return self.modules.get(capability)
```

---

## 5. 云边协同设计

### 5.1 云端职责

```
┌─────────────────────────────────────────────┐
│                  云端平台                    │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────┐  ┌─────────────┐          │
│  │  设备管理   │  │  模型管理   │          │
│  │  - 注册     │  │  - 存储     │          │
│  │  - 状态     │  │  - 版本     │          │
│  │  - 监控     │  │  - 分发     │          │
│  └─────────────┘  └─────────────┘          │
│                                             │
│  ┌─────────────┐  ┌─────────────┐          │
│  │  训练服务   │  │  OTA升级    │          │
│  │  - 任务     │  │  - 模型更新 │          │
│  │  - 进度     │  │  - 配置更新 │          │
│  │  - 指标     │  │  - 回滚     │          │
│  └─────────────┘  └─────────────┘          │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │           数据存储                   │   │
│  │   模型文件 │ 数据集 │ 训练输出       │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

### 5.2 边缘职责

```
┌─────────────────────────────────────────────┐
│                  边缘设备                    │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │           智能体系统                 │   │
│  │   感知智能体 │ 认知智能体 │ 行动智能体 │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │           推理引擎                   │   │
│  │   TensorRT │ ONNX Runtime           │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │           通信模块                   │   │
│  │   MQTT Client │ HTTP Client         │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

### 5.3 通信协议

| 通信方向 | 协议 | 用途 |
|----------|------|------|
| 云端 → 边缘 | MQTT | 命令下发、OTA推送 |
| 边缘 → 云端 | MQTT | 心跳、状态上报 |
| 边缘 → 云端 | HTTP | 文件上传、结果提交 |
| 云端 → 边缘 | HTTP | 模型下载 |

---

## 6. 智能体通信

### 6.1 消息格式

```python
from dataclasses import dataclass
from typing import Dict, Any
import time
import uuid

@dataclass
class AgentMessage:
    """智能体消息"""
    msg_id: str
    msg_type: str
    sender: str
    receiver: str  # "perception" | "cognition" | "action" | "all"
    timestamp: float
    payload: Dict[str, Any]
    
    @classmethod
    def create(cls, msg_type: str, sender: str, receiver: str, payload: Dict) -> 'AgentMessage':
        return cls(
            msg_id=str(uuid.uuid4()),
            msg_type=msg_type,
            sender=sender,
            receiver=receiver,
            timestamp=time.time(),
            payload=payload
        )

# 消息类型
class MessageType:
    # 感知 → 认知
    PERCEPTION_RESULT = "perception_result"
    
    # 认知 → 行动
    COGNITION_DECISION = "cognition_decision"
    
    # 行动 → 认知（反馈）
    ACTION_FEEDBACK = "action_feedback"
    
    # 云端 → 边缘
    OTA_COMMAND = "ota_command"
    MODEL_UPDATE = "model_update"
    
    # 边缘 → 云端
    HEARTBEAT = "heartbeat"
    STATUS_REPORT = "status_report"
```

### 6.2 消息总线

```python
from typing import Callable, Dict, List

class MessageBus:
    """智能体消息总线"""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        
    def subscribe(self, msg_type: str, handler: Callable):
        """订阅消息"""
        if msg_type not in self.subscribers:
            self.subscribers[msg_type] = []
        self.subscribers[msg_type].append(handler)
        
    def publish(self, message: AgentMessage):
        """发布消息"""
        handlers = self.subscribers.get(message.msg_type, [])
        for handler in handlers:
            handler(message)
        
        # 广播消息
        broadcast_handlers = self.subscribers.get("all", [])
        for handler in broadcast_handlers:
            handler(message)
    
    def send_to(self, receiver: str, message: AgentMessage):
        """发送给特定智能体"""
        handlers = self.subscribers.get(receiver, [])
        for handler in handlers:
            handler(message)
```

---

## 7. 接口规范

### 7.1 感知智能体接口

| 接口 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `perceive(sensor_data)` | 图像/视频/传感器数据 | `PerceptionResult[]` | 执行感知 |
| `activate(capability)` | 能力类型 | - | 激活能力 |
| `deactivate(capability)` | 能力类型 | - | 停用能力 |
| `update_model(capability, path)` | 能力类型, 模型路径 | success | OTA更新模型 |

### 7.2 认知智能体接口

| 接口 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `think(perception_results, context)` | 感知结果, 上下文 | `CognitionResult[]` | 执行认知 |
| `set_goal(goal)` | 目标 | - | 设置目标 |

### 7.3 行动智能体接口

| 接口 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `act(cognition_results)` | 认知结果 | `ActionResult[]` | 执行行动 |
| `abort()` | - | - | 中止当前行动 |
| `get_status()` | - | 状态 | 获取状态 |

---

## 8. 实现状态

| 组件 | 状态 | 说明 |
|------|------|------|
| **感知智能体** | | |
| - 目标识别模块 | ✅ 完成 | YOLOv8 |
| - 变化检测模块 | ✅ 完成 | RCMT V3 |
| - 语义分割模块 | ✅ 完成 | SegFormer |
| - 目标跟踪模块 | ✅ 完成 | DeepSORT |
| - 三维重建模块 | 📝 规划 | - |
| **认知智能体** | | |
| - 路径规划模块 | 📝 规划 | - |
| - 任务分配模块 | 📝 规划 | - |
| - 变化分析模块 | 📝 规划 | - |
| **行动智能体** | | |
| - 自主飞行模块 | 📝 规划 | - |
| - 协同作业模块 | 📝 规划 | - |
| **云边协同** | | |
| - 云端平台 | ✅ 完成 | Spring Boot + Vue3 |
| - 边缘通信 | ✅ 完成 | MQTT |
| - OTA升级 | ✅ 完成 | - |

**图例**：
- ✅ 完成 - 已实现并验证
- 🚧 进行中 - 正在开发
- 📝 规划 - 已规划，待开发

---

**文档状态**: V2.0  
**最后更新**: 2026-03-06  
**维护者**: SkyEdge AI Team
