# 多智能体系统技术设计文档

> **项目代号**: SkyEdge Multi-Agent System  
> **版本**: V1.0  
> **日期**: 2026-02-15  
> **状态**: 设计阶段

---

## 📋 目录

1. [系统概述](#1-系统概述)
2. [智能体架构](#2-智能体架构)
3. [协同机制设计](#3-协同机制设计)
4. [通讯协议设计](#4-通讯协议设计)
5. [决策算法设计](#5-决策算法设计)
6. [具身智能扩展](#6-具身智能扩展)
7. [仿真与测试](#7-仿真与测试)

---

## 1. 系统概述

### 1.1 设计目标

构建一个**分布式、自适应、可扩展**的多智能体系统，实现：

- ✅ 多无人机协同作业
- ✅ 自组织通讯网络（Mesh）
- ✅ 智能任务分配与执行
- ✅ 实时冲突检测与解决
- ✅ 环境自适应学习

### 1.2 系统特性

| 特性 | 说明 | 技术方案 |
|------|------|----------|
| **分布式** | 无中心节点，抗毁性强 | 共识算法、P2P通讯 |
| **自适应** | 根据环境动态调整 | 强化学习、在线优化 |
| **可扩展** | 支持大规模智能体 | 分层架构、模块化设计 |
| **实时性** | 毫秒级响应 | 优化算法、边缘计算 |
| **容错性** | 单点故障不影响系统 | 冗余设计、故障恢复 |

### 1.3 应用场景

| 场景 | 智能体数量 | 任务类型 | 协同模式 |
|------|-----------|----------|----------|
| 应急救援 | 10-20架 | 搜救、物资投送 | 分区协同 |
| 农业巡检 | 5-10架 | 喷洒、监测 | 并行作业 |
| 边境监控 | 20-50架 | 巡航、预警 | 分层监控 |
| 测绘建模 | 3-5架 | 三维建模 | 编队飞行 |
| 电力巡检 | 5-8架 | 线路检测 | 分段巡检 |

---

## 2. 智能体架构

### 2.1 智能体层次结构

```
┌─────────────────────────────────────────────────────────┐
│              Multi-Agent System (MAS)                  │
│                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  Mission    │  │ Collaboration│  │  Resource   │   │
│  │  Agent      │  │  Agent      │  │  Agent      │   │
│  └─────────────┘  └─────────────┘  └─────────────┘   │
│       │                │                │             │
│  ┌────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐        │
│  │ Flight    │  │ Perception│  │ Communication│     │
│  │ Agent     │  │ Agent     │  │ Agent       │     │
│  └───────────┘  └───────────┘  └─────────────┘    │
│       │                │                │             │
│  ┌────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐        │
│  │ Decision  │  │ Learning   │  │ Monitoring  │     │
│  │ Agent     │  │ Agent      │  │ Agent       │     │
│  └───────────┘  └───────────┘  └─────────────┘    │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │          Shared Memory / Knowledge Base        │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 2.2 智能体定义

#### 2.2.1 基础智能体 (BaseAgent)

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from enum import Enum

class AgentState(Enum):
    """智能体状态"""
    INIT = "init"
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"

class MessageType(Enum):
    """消息类型"""
    TASK_ASSIGN = "task_assign"
    STATUS_UPDATE = "status_update"
    DATA_SHARE = "data_share"
    COORDINATE = "coordinate"
    ALERT = "alert"
    HEARTBEAT = "heartbeat"

class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.state = AgentState.INIT
        self.capabilities = []
        self.message_queue = []
        self.knowledge_base = {}
        
    @abstractmethod
    def perceive(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """感知环境"""
        pass
    
    @abstractmethod
    def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """制定决策"""
        pass
    
    @abstractmethod
    def act(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """执行动作"""
        pass
    
    @abstractmethod
    def communicate(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """通讯交互"""
        pass
    
    def update_state(self, new_state: AgentState):
        """更新状态"""
        self.state = new_state
        
    def add_capability(self, capability: str):
        """添加能力"""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
    
    def receive_message(self, message: Dict[str, Any]):
        """接收消息"""
        self.message_queue.append(message)
    
    def process_messages(self) -> List[Dict[str, Any]]:
        """处理消息队列"""
        responses = []
        while self.message_queue:
            message = self.message_queue.pop(0)
            response = self.communicate(message)
            responses.append(response)
        return responses
```

#### 2.2.2 飞行控制智能体 (FlightControlAgent)

```python
class FlightMode(Enum):
    """飞行模式"""
    MANUAL = "manual"
    AUTO = "auto"
    HOVER = "hover"
    FOLLOW = "follow"
    FORMATION = "formation"
    EMERGENCY = "emergency"

class Position:
    """位置信息"""
    def __init__(self, lat: float, lon: float, alt: float):
        self.lat = lat    # 纬度（RTK）
        self.lon = lon    # 经度（RTK）
        self.alt = alt    # 高度（米）
    
    def distance_to(self, other: 'Position') -> float:
        """计算距离（米）"""
        # 使用Haversine公式
        from math import radians, sin, cos, sqrt, asin
        
        lat1, lon1 = radians(self.lat), radians(self.lon)
        lat2, lon2 = radians(other.lat), radians(other.lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # 地球半径（米）
        R = 6371000
        distance = R * c
        
        # 考虑高度差
        alt_diff = self.alt - other.alt
        distance = sqrt(distance**2 + alt_diff**2)
        
        return distance

class Velocity:
    """速度信息"""
    def __init__(self, x: float, y: float, z: float):
        self.x = x  # 东向速度 (m/s)
        self.y = y  # 北向速度 (m/s)
        self.z = z  # 垂直速度 (m/s)
    
    @property
    def magnitude(self) -> float:
        """速度大小"""
        return sqrt(self.x**2 + self.y**2 + self.z**2)

class PIDController:
    """PID控制器"""
    
    def __init__(self, kp: float, ki: float, kd: float):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0
    
    def compute(self, error: float, dt: float) -> float:
        """计算控制输出"""
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt
        
        output = (self.kp * error + 
                  self.ki * self.integral + 
                  self.kd * derivative)
        
        self.prev_error = error
        return output

class FlightControlAgent(BaseAgent):
    """飞行控制智能体"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "flight_control")
        
        # 飞行状态
        self.flight_mode = FlightMode.MANUAL
        self.position = Position(0.0, 0.0, 0.0)
        self.target_position = Position(0.0, 0.0, 0.0)
        self.velocity = Velocity(0.0, 0.0, 0.0)
        
        # PID控制器
        self.pid_x = PIDController(kp=1.0, ki=0.1, kd=0.5)
        self.pid_y = PIDController(kp=1.0, ki=0.1, kd=0.5)
        self.pid_z = PIDController(kp=1.5, ki=0.1, kd=0.5)
        
        # 能力
        self.add_capability("position_control")
        self.add_capability("velocity_control")
        self.add_capability("waypoint_follow")
        self.add_capability("formation_fly")
    
    def perceive(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """感知飞行状态"""
        # RTK定位数据
        if "rtk" in sensor_data:
            self.position = Position(
                lat=sensor_data["rtk"]["lat"],
                lon=sensor_data["rtk"]["lon"],
                alt=sensor_data["rtk"]["alt"]
            )
        
        # IMU数据
        if "imu" in sensor_data:
            self.velocity = Velocity(
                x=sensor_data["imu"]["vx"],
                y=sensor_data["imu"]["vy"],
                z=sensor_data["imu"]["vz"]
            )
        
        # 飞行模式
        if "flight_mode" in sensor_data:
            try:
                self.flight_mode = FlightMode(sensor_data["flight_mode"])
            except ValueError:
                self.flight_mode = FlightMode.MANUAL
        
        return {
            "position": {
                "lat": self.position.lat,
                "lon": self.position.lon,
                "alt": self.position.alt
            },
            "velocity": {
                "x": self.velocity.x,
                "y": self.velocity.y,
                "z": self.velocity.z
            },
            "flight_mode": self.flight_mode.value
        }
    
    def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """飞行决策"""
        if self.flight_mode != FlightMode.AUTO:
            return {}
        
        # 计算位置误差
        delta_x = (self.target_position.lon - self.position.lon) * 111320  # m
        delta_y = (self.target_position.lat - self.position.lat) * 111320  # m
        delta_z = self.target_position.alt - self.position.alt
        
        # PID控制
        dt = 0.1  # 控制周期
        roll = -self.pid_x.compute(delta_x, dt)    # 横滚角（弧度）
        pitch = self.pid_y.compute(delta_y, dt)    # 俯仰角（弧度）
        thrust = self.pid_z.compute(delta_z, dt)    # 推力 (0-1)
        
        # 限制范围
        roll = max(-0.5, min(0.5, roll))
        pitch = max(-0.5, min(0.5, pitch))
        thrust = max(0.3, min(1.0, thrust))
        
        return {
            "control_cmd": {
                "roll": roll,
                "pitch": pitch,
                "thrust": thrust,
                "yaw": 0.0
            }
        }
    
    def act(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """执行飞行控制"""
        if "control_cmd" not in action:
            return {"status": "no_command"}
        
        cmd = action["control_cmd"]
        
        # 发送控制指令到飞控
        send_to_flight_controller(
            roll=cmd["roll"],
            pitch=cmd["pitch"],
            thrust=cmd["thrust"],
            yaw=cmd["yaw"]
        )
        
        return {"status": "success"}
    
    def communicate(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理飞行相关通讯"""
        msg_type = message.get("type")
        
        if msg_type == "waypoint_update":
            self.target_position = Position(
                lat=message["waypoint"]["lat"],
                lon=message["waypoint"]["lon"],
                alt=message["waypoint"]["alt"]
            )
            return {"status": "waypoint_updated"}
        
        elif msg_type == "mode_change":
            try:
                self.flight_mode = FlightMode(message["mode"])
                return {"status": "mode_changed"}
            except ValueError:
                return {"status": "error", "message": "invalid_mode"}
        
        elif msg_type == "formation_update":
            if "formation_offset" in message:
                # 相对队形偏移
                offset = message["formation_offset"]
                # 实现队形保持逻辑
                return {"status": "formation_updated"}
        
        return {"status": "unknown_message"}
    
    def set_waypoint(self, position: Position):
        """设置航点"""
        self.target_position = position
    
    def set_flight_mode(self, mode: FlightMode):
        """设置飞行模式"""
        self.flight_mode = mode
```

#### 2.2.3 感知智能体 (PerceptionAgent)

```python
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

@dataclass
class Detection:
    """检测框"""
    class_id: int
    class_name: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    position: Optional[Position]  # 3D位置（如果可用）

@dataclass
class Track:
    """跟踪目标"""
    track_id: int
    class_name: str
    detections: List[Detection]
    last_seen: float
    position: Position
    velocity: Optional[Velocity]
    
    @property
    def age(self) -> float:
        """跟踪时长（秒）"""
        return self.last_seen - self.detections[0].timestamp if self.detections else 0

@dataclass
class SceneChange:
    """场景变化"""
    change_type: str
    confidence: float
    bbox: List[float]
    timestamp: float

class PerceptionAgent(BaseAgent):
    """感知智能体"""
    
    def __init__(self, agent_id: str, model_path: str = None):
        super().__init__(agent_id, "perception")
        
        # 检测器
        self.detector = None
        if model_path:
            from edge_infer.plugins.yolov8 import YOLOv8Detector
            self.detector = YOLOv8Detector(model_path=model_path)
        
        # 跟踪器
        self.tracker = DeepSORTTracker()
        
        # 场景分析器
        from edge_infer.models.rcmt import RCMTAnalyzer
        self.scene_analyzer = RCMTAnalyzer()
        
        # 状态
        self.detections = []
        self.tracks = []
        self.scene_changes = []
        self.history = []  # 历史帧（用于时序分析）
        
        # 能力
        self.add_capability("object_detection")
        self.add_capability("object_tracking")
        self.add_capability("scene_analysis")
        self.add_capability("change_detection")
    
    def perceive(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """感知环境"""
        if "image" not in sensor_data:
            return {"error": "no_image_data"}
        
        image = sensor_data["image"]
        timestamp = sensor_data.get("timestamp", time.time())
        
        # 1. 目标检测
        if self.detector:
            self.detections = self.detector.detect(image)
        else:
            self.detections = []
        
        # 2. 目标跟踪
        self.tracks = self.tracker.update(
            detections=self.detections,
            image=image
        )
        
        # 3. 场景分析（时序变化检测）
        if self.history and self.scene_analyzer:
            # 取最近N帧
            history_images = [h["image"] for h in self.history[-10:]]
            
            # RCMT时序分析
            self.scene_changes = self.scene_analyzer.analyze(
                earlier_images=history_images,
                later_image=image
            )
        
        # 保存到历史
        self.history.append({
            "image": image,
            "timestamp": timestamp,
            "detections": self.detections,
            "tracks": self.tracks,
            "scene_changes": self.scene_changes
        })
        
        # 限制历史长度
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        return {
            "detections": [self._detection_to_dict(d) for d in self.detections],
            "tracks": [self._track_to_dict(t) for t in self.tracks],
            "scene_changes": [self._change_to_dict(c) for c in self.scene_changes],
            "timestamp": timestamp
        }
    
    def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """感知决策"""
        alerts = []
        
        # 1. 距离过近警告
        for track in self.tracks:
            if track.position:
                dist = track.position.distance_to(context["my_position"])
                if dist < 5.0:  # 5米内
                    alerts.append({
                        "type": "proximity_warning",
                        "track_id": track.track_id,
                        "class": track.class_name,
                        "distance": dist
                    })
        
        # 2. 异常检测
        for change in self.scene_changes:
            if change.confidence > 0.8:  # 高置信度变化
                alerts.append({
                    "type": "anomaly_detected",
                    "change_type": change.change_type,
                    "confidence": change.confidence
                })
        
        # 3. 目标丢失警告
        for track in self.tracks:
            if track.age > 5.0:  # 超过5秒未见
                alerts.append({
                    "type": "target_lost",
                    "track_id": track.track_id,
                    "age": track.age
                })
        
        return {"alerts": alerts}
    
    def act(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """执行感知动作"""
        if action.get("type") == "clear_history":
            self.history = []
            return {"status": "history_cleared"}
        
        elif action.get("type") == "set_model":
            model_path = action.get("model_path")
            if model_path:
                from edge_infer.plugins.yolov8 import YOLOv8Detector
                self.detector = YOLOv8Detector(model_path=model_path)
                return {"status": "model_updated"}
        
        return {"status": "no_action"}
    
    def communicate(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理感知通讯"""
        msg_type = message.get("type")
        
        if msg_type == "request_detections":
            return {
                "detections": [self._detection_to_dict(d) for d in self.detections]
            }
        
        elif msg_type == "request_tracks":
            return {
                "tracks": [self._track_to_dict(t) for t in self.tracks]
            }
        
        elif msg_type == "share_detections":
            # 共享检测结果给其他智能体
            other_agents = message.get("target_agents", [])
            shared_data = {
                "source": self.agent_id,
                "detections": [self._detection_to_dict(d) for d in self.detections],
                "timestamp": time.time()
            }
            # 发送给其他智能体（通过通讯层）
            return {"status": "shared"}
        
        return {"status": "unknown_message"}
    
    def _detection_to_dict(self, detection: Detection) -> Dict:
        """检测框转字典"""
        return {
            "class_id": detection.class_id,
            "class_name": detection.class_name,
            "confidence": detection.confidence,
            "bbox": detection.bbox
        }
    
    def _track_to_dict(self, track: Track) -> Dict:
        """跟踪目标转字典"""
        return {
            "track_id": track.track_id,
            "class_name": track.class_name,
            "age": track.age,
            "position": {
                "lat": track.position.lat if track.position else None,
                "lon": track.position.lon if track.position else None,
                "alt": track.position.alt if track.position else None
            }
        }
    
    def _change_to_dict(self, change: SceneChange) -> Dict:
        """场景变化转字典"""
        return {
            "change_type": change.change_type,
            "confidence": change.confidence,
            "bbox": change.bbox,
            "timestamp": change.timestamp
        }
```

#### 2.2.4 决策智能体 (DecisionAgent)

```python
from typing import List, Optional, Tuple
from dataclasses import dataclass
import heapq

@dataclass
class Task:
    """任务"""
    task_id: str
    task_type: str
    priority: int  # 优先级 (1-10)
    urgency: float  # 紧急性 (0-1)
    location: Position
    requirements: Dict[str, Any]
    assigned_agent: Optional[str] = None
    status: str = "pending"

@dataclass
class Waypoint:
    """航点"""
    position: Position
    speed: float
    altitude: float
    action: Optional[str] = None

class MissionPlanner:
    """任务规划器"""
    
    def __init__(self):
        self.active_missions = []
    
    def plan(self, goal: Dict, obstacles: List, team_state: Dict) -> List[Waypoint]:
        """规划任务路径"""
        # 简化版：直线规划
        # 实际实现应该考虑障碍物、能源、协同等
        
        start_pos = Position(
            lat=goal.get("start_lat", 0),
            lon=goal.get("start_lon", 0),
            alt=goal.get("start_alt", 0)
        )
        
        end_pos = Position(
            lat=goal.get("end_lat", 0),
            lon=goal.get("end_lon", 0),
            alt=goal.get("end_alt", 0)
        )
        
        # 简单的两点规划
        waypoints = [
            Waypoint(position=start_pos, speed=10, altitude=start_pos.alt),
            Waypoint(position=end_pos, speed=10, altitude=end_pos.alt)
        ]
        
        return waypoints

class PathPlanner:
    """路径规划器"""
    
    def __init__(self):
        self.current_waypoints = []
        self.current_index = 0
    
    def plan(self, start: Position, goal: Position, 
             constraints: Dict = None) -> List[Waypoint]:
        """规划路径"""
        # 简化版：使用A*或RRT*
        # 这里只返回起点和终点
        
        return [
            Waypoint(position=start, speed=10, altitude=start.alt),
            Waypoint(position=goal, speed=10, altitude=goal.alt)
        ]
    
    def get_next(self, current_pos: Position, waypoints: List[Waypoint]) -> Optional[Waypoint]:
        """获取下一个航点"""
        if not waypoints:
            return None
        
        # 找到最近的未完成航点
        min_dist = float('inf')
        next_waypoint = None
        
        for wp in waypoints:
            dist = current_pos.distance_to(wp.position)
            if dist < min_dist and dist > 5.0:  # 5米内认为已到达
                min_dist = dist
                next_waypoint = wp
        
        return next_waypoint

class DecisionAgent(BaseAgent):
    """决策智能体"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "decision")
        
        self.mission_planner = MissionPlanner()
        self.path_planner = PathPlanner()
        
        self.current_task = None
        self.current_waypoints = []
        self.current_waypoint_index = 0
        
        # 能力
        self.add_capability("mission_planning")
        self.add_capability("path_planning")
        self.add_capability("task_allocation")
        self.add_capability("conflict_resolution")
    
    def perceive(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """感知环境"""
        # 决策智能体不需要直接感知，主要依赖其他智能体的数据
        return {"status": "ok"}
    
    def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """决策制定"""
        # 1. 任务规划
        if self.current_task is None:
            # 等待任务分配
            return {"status": "waiting_for_task"}
        
        # 2. 路径规划
        if context.get("mission_status") == "planning":
            goal = {
                "end_lat": self.current_task.location.lat,
                "end_lon": self.current_task.location.lon,
                "end_alt": self.current_task.location.alt
            }
            
            self.current_waypoints = self.mission_planner.plan(
                goal=goal,
                obstacles=context.get("obstacles", []),
                team_state=context.get("team_state", {})
            )
            
            return {
                "status": "waypoints_planned",
                "waypoints": self._waypoints_to_dict(self.current_waypoints)
            }
        
        # 3. 执行任务
        elif context.get("mission_status") == "executing":
            current_pos = context.get("position")
            next_wp = self.path_planner.get_next(
                current_pos=current_pos,
                waypoints=self.current_waypoints
            )
            
            if next_wp:
                return {
                    "status": "flying_to_waypoint",
                    "target": self._waypoint_to_dict(next_wp)
                }
            else:
                return {
                    "status": "mission_complete"
                }
        
        return {"status": "idle"}
    
    def act(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """执行决策"""
        if action.get("type") == "assign_task":
            self.current_task = Task(
                task_id=action["task"]["task_id"],
                task_type=action["task"]["task_type"],
                priority=action["task"].get("priority", 5),
                urgency=action["task"].get("urgency", 0.5),
                location=Position(
                    lat=action["task"]["location"]["lat"],
                    lon=action["task"]["location"]["lon"],
                    alt=action["task"]["location"]["alt"]
                ),
                requirements=action["task"].get("requirements", {}),
                assigned_agent=self.agent_id
            )
            return {"status": "task_assigned"}
        
        elif action.get("type") == "clear_task":
            self.current_task = None
            self.current_waypoints = []
            self.current_waypoint_index = 0
            return {"status": "task_cleared"}
        
        return {"status": "no_action"}
    
    def communicate(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理决策通讯"""
        msg_type = message.get("type")
        
        if msg_type == "task_request":
            # 收到任务请求，计算估值并返回
            task = message["task"]
            bid = self._calculate_bid(task)
            
            return {
                "agent_id": self.agent_id,
                "bid": bid,
                "task_id": task["task_id"]
            }
        
        elif msg_type == "task_assigned":
            # 任务被分配
            task = message["task"]
            self.current_task = Task(
                task_id=task["task_id"],
                task_type=task["task_type"],
                priority=task.get("priority", 5),
                urgency=task.get("urgency", 0.5),
                location=Position(
                    lat=task["location"]["lat"],
                    lon=task["location"]["lon"],
                    alt=task["location"]["alt"]
                ),
                requirements=task.get("requirements", {}),
                assigned_agent=self.agent_id
            )
            
            return {"status": "task_accepted"}
        
        elif msg_type == "status_request":
            return {
                "agent_id": self.agent_id,
                "current_task": self._task_to_dict(self.current_task) if self.current_task else None,
                "waypoint_index": self.current_waypoint_index,
                "status": "active" if self.current_task else "idle"
            }
        
        return {"status": "unknown_message"}
    
    def _calculate_bid(self, task: Task) -> float:
        """计算任务估值"""
        if not self.current_task:
            # 空闲智能体，优先执行
            return 100.0
        
        # 计算距离
        current_pos = self._get_current_position()
        distance = current_pos.distance_to(task.location)
        
        # 计算估值（距离越近估值越高）
        bid = 100.0 - distance * 0.1
        
        # 考虑任务优先级
        bid += task.priority * 5.0
        
        # 考虑任务紧急性
        bid += task.urgency * 10.0
        
        return max(0.0, bid)
    
    def _get_current_position(self) -> Position:
        """获取当前位置（简化版）"""
        # 实际应该从飞行控制智能体获取
        return Position(0.0, 0.0, 0.0)
    
    def _task_to_dict(self, task: Task) -> Dict:
        """任务转字典"""
        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "priority": task.priority,
            "location": {
                "lat": task.location.lat,
                "lon": task.location.lon,
                "alt": task.location.alt
            },
            "status": task.status
        }
    
    def _waypoints_to_dict(self, waypoints: List[Waypoint]) -> List[Dict]:
        """航点列表转字典"""
        return [
            {
                "position": {
                    "lat": wp.position.lat,
                    "lon": wp.position.lon,
                    "alt": wp.position.alt
                },
                "speed": wp.speed,
                "altitude": wp.altitude,
                "action": wp.action
            }
            for wp in waypoints
        ]
    
    def _waypoint_to_dict(self, waypoint: Waypoint) -> Dict:
        """单个航点转字典"""
        return {
            "position": {
                "lat": waypoint.position.lat,
                "lon": waypoint.position.lon,
                "alt": waypoint.position.alt
            },
            "speed": waypoint.speed,
            "altitude": waypoint.altitude,
            "action": waypoint.action
        }
```

#### 2.2.5 通讯管理智能体 (CommunicationAgent)

```python
from enum import Enum

class CommMode(Enum):
    """通讯模式"""
    AUTO = "auto"
    FIVE_G = "5g"
    MESH = "mesh"
    HYBRID = "hybrid"

class CommAgent(BaseAgent):
    """通讯管理智能体"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "communication")
        
        self.comm_5g = Comm5GModule()
        self.comm_mesh = CommMeshModule()
        
        self.current_mode = CommMode.AUTO
        self.message_queue = []
        self.neighbor_table = {}
        
        # 能力
        self.add_capability("5g_comm")
        self.add_capability("mesh_comm")
        self.add_capability("auto_switch")
        self.add_capability("message_routing")
    
    def perceive(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """感知通讯状态"""
        # 5G信号强度
        five_g_signal = self.comm_5g.get_signal_strength()
        
        # Mesh网络状态
        mesh_neighbors = self.comm_mesh.get_neighbors()
        mesh_quality = self.comm_mesh.get_network_quality()
        
        # 更新邻居表
        self.neighbor_table = {
            agent_id: {
                "signal": neighbor["signal"],
                "latency": neighbor["latency"],
                "last_seen": time.time()
            }
            for agent_id, neighbor in mesh_neighbors.items()
        }
        
        return {
            "five_g": {
                "signal_strength": five_g_signal,
                "available": five_g_signal > -90  # dBm阈值
            },
            "mesh": {
                "neighbor_count": len(mesh_neighbors),
                "network_quality": mesh_quality,
                "neighbors": mesh_neighbors
            },
            "current_mode": self.current_mode.value
        }
    
    def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """通讯决策"""
        if self.current_mode == CommMode.AUTO:
            # 自动选择最佳通讯方式
            five_g_available = context["five_g"]["available"]
            mesh_available = len(context["mesh"]["neighbors"]) > 0
            
            if five_g_available and mesh_available:
                # 5G和Mesh都可用，使用混合模式
                self.current_mode = CommMode.HYBRID
            
            elif five_g_available:
                # 只有5G可用
                self.current_mode = CommMode.FIVE_G
            
            elif mesh_available:
                # 只有Mesh可用
                self.current_mode = CommMode.MESH
            
            else:
                # 都不可用，切换到离线模式
                return {"mode": "offline", "status": "no_connection"}
            
            return {
                "mode": self.current_mode.value,
                "status": "switched"
            }
        
        return {"mode": self.current_mode.value, "status": "ok"}
    
    def act(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """执行通讯动作"""
        if action.get("type") == "send_message":
            message = action["message"]
            target = action.get("target", "broadcast")
            
            # 根据模式选择发送方式
            if self.current_mode == CommMode.FIVE_G:
                result = self.comm_5g.send(message, target)
            elif self.current_mode == CommMode.MESH:
                result = self.comm_mesh.send(message, target)
            elif self.current_mode == CommMode.HYBRID:
                # 智能路由
                if self._use_mesh_for_target(target):
                    result = self.comm_mesh.send(message, target)
                else:
                    result = self.comm_5g.send(message, target)
            else:
                result = {"status": "no_connection"}
            
            return result
        
        return {"status": "no_action"}
    
    def communicate(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理通讯消息"""
        msg_type = message.get("type")
        
        if msg_type == "route_message":
            # 路由消息
            target = message.get("target")
            msg_content = message.get("message")
            
            # 根据路由决策发送
            if self.current_mode == CommMode.MESH:
                # 通过Mesh路由
                self.comm_mesh.route(target, msg_content)
            elif self.current_mode == CommMode.FIVE_G:
                # 通过5G发送
                self.comm_5g.send(target, msg_content)
            
            return {"status": "routed"}
        
        elif msg_type == "broadcast":
            # 广播消息
            msg_content = message.get("message")
            
            if self.current_mode in [CommMode.MESH, CommMode.HYBRID]:
                self.comm_mesh.broadcast(msg_content)
            
            return {"status": "broadcasted"}
        
        return {"status": "unknown_message"}
    
    def _use_mesh_for_target(self, target: str) -> bool:
        """判断是否使用Mesh发送到目标"""
        # 检查目标是否在Mesh网络中
        if target in self.neighbor_table:
            # 计算跳数
            hop_count = self.neighbor_table[target].get("hop_count", 1)
            
            # 如果跳数<=3，使用Mesh
            return hop_count <= 3
        
        return False

class Comm5GModule:
    """5G通讯模块"""
    
    def __init__(self):
        self.module = None  # 实际硬件模块
        self.signal_strength = -100  # dBm
    
    def get_signal_strength(self) -> float:
        """获取信号强度"""
        # 实际实现读取5G模块AT指令
        # 这里返回模拟值
        return self.signal_strength
    
    def send(self, message: Dict, target: str) -> Dict:
        """发送消息"""
        # 实际实现通过5G模块发送
        return {"status": "sent", "mode": "5g"}

class CommMeshModule:
    """Mesh通讯模块"""
    
    def __init__(self):
        self.neighbors = {}
        self.routing_table = {}
    
    def get_neighbors(self) -> Dict:
        """获取邻居节点"""
        # 实际实现读取Mesh模块状态
        return self.neighbors
    
    def get_network_quality(self) -> float:
        """获取网络质量"""
        # 计算网络质量指标
        neighbor_count = len(self.neighbors)
        if neighbor_count == 0:
            return 0.0
        
        # 简化的质量计算
        avg_signal = sum(n.get("signal", -80) for n in self.neighbors.values()) / neighbor_count
        quality = (avg_signal + 100) / 20  # 归一化到0-1
        return min(1.0, max(0.0, quality))
    
    def send(self, message: Dict, target: str) -> Dict:
        """发送消息"""
        # 实际实现通过Mesh模块发送
        return {"status": "sent", "mode": "mesh"}
    
    def broadcast(self, message: Dict):
        """广播消息"""
        # 实际实现广播到所有邻居
        pass
    
    def route(self, target: str, message: Dict):
        """路由消息"""
        # 实际实现根据路由表路由
        pass
```

---

## 3. 协同机制设计

### 3.1 任务分配（拍卖算法）

```python
from typing import List, Dict
import copy

class AuctionBasedTaskAllocation:
    """基于拍卖的任务分配算法"""
    
    def __init__(self, agents: List[BaseAgent]):
        self.agents = agents
        self.active_tasks = []
        self.allocations = {}
    
    def allocate(self, tasks: List[Task]) -> Dict[str, str]:
        """分配任务"""
        self.allocations = {}
        
        for task in tasks:
            # 1. 广播任务
            self._broadcast_task(task)
            
            # 2. 收集竞价
            bids = self._collect_bids(task)
            
            # 3. 选择赢家
            winner = self._select_winner(task, bids)
            
            # 4. 分配任务
            self._assign_task(task, winner)
        
        return self.allocations
    
    def _broadcast_task(self, task: Task):
        """广播任务"""
        for agent in self.agents:
            # 发送任务请求
            agent.receive_message({
                "type": "task_request",
                "task": task
            })
            
            # 处理并获取响应
            responses = agent.process_messages()
            
            # 记录竞价
            for response in responses:
                if response.get("type") == "bid":
                    task.bids[response["agent_id"]] = response["bid"]
    
    def _collect_bids(self, task: Task) -> Dict[str, float]:
        """收集竞价"""
        return task.bids
    
    def _select_winner(self, task: Task, bids: Dict[str, float]) -> str:
        """选择赢家"""
        if not bids:
            return None
        
        # 最高出价者获胜
        winner = max(bids, key=bids.get)
        
        # 检查是否超过阈值
        if bids[winner] > 50.0:  # 阈值
            return winner
        
        return None
    
    def _assign_task(self, task: Task, winner: str):
        """分配任务"""
        if winner:
            task.assigned_agent = winner
            task.status = "assigned"
            self.allocations[task.task_id] = winner
            
            # 通知赢家
            for agent in self.agents:
                if agent.agent_id == winner:
                    agent.receive_message({
                        "type": "task_assigned",
                        "task": task
                    })
                    agent.process_messages()
        else:
            task.status = "unassigned"
```

### 3.2 状态同步（共识算法）

```python
import numpy as np
from typing import List, Dict

class ConsensusAlgorithm:
    """共识算法"""
    
    def __init__(self, agents: List[BaseAgent], max_iterations=100):
        self.agents = agents
        self.max_iterations = max_iterations
        self.convergence_threshold = 0.001
    
    def sync_states(self) -> Dict[str, Dict]:
        """同步状态"""
        converged = False
        iterations = 0
        
        while not converged and iterations < self.max_iterations:
            # 1. 交换状态
            self._exchange_states()
            
            # 2. 计算新状态
            self._update_states()
            
            # 3. 检查收敛
            converged = self._check_convergence()
            
            iterations += 1
        
        # 返回最终状态
        return {a.agent_id: a.state for a in self.agents}
    
    def _exchange_states(self):
        """交换状态"""
        # 每个智能体与邻居交换状态
        for agent in self.agents:
            neighbors = self._get_neighbors(agent)
            
            for neighbor in neighbors:
                # 交换状态
                agent.receive_message({
                    "type": "state_sync",
                    "state": neighbor.state,
                    "from": neighbor.agent_id
                })
    
    def _update_states(self):
        """更新状态"""
        for agent in self.agents:
            # 处理状态消息
            responses = agent.process_messages()
            
            # 计算共识状态
            neighbor_states = []
            for response in responses:
                if response.get("type") == "state_sync":
                    neighbor_states.append(response["state"])
            
            # 加权平均
            if neighbor_states:
                new_state = self._compute_consensus(agent.state, neighbor_states)
                agent.state = new_state
    
    def _compute_consensus(self, current: Dict, neighbor_states: List[Dict]) -> Dict:
        """计算共识状态"""
        # 简化版：加权平均
        all_states = [current] + neighbor_states
        weights = [0.4] + [0.6 / len(neighbor_states)] * len(neighbor_states)
        
        consensus_state = {}
        for key in current.keys():
            values = [s[key] for s in all_states if key in s]
            if values:
                consensus_state[key] = sum(v * w for v, w in zip(values, weights))
        
        return consensus_state
    
    def _check_convergence(self) -> bool:
        """检查收敛"""
        # 计算所有智能体状态的差异
        states = [a.state for a in self.agents]
        
        max_diff = 0
        for i in range(len(states)):
            for j in range(i+1, len(states)):
                diff = self._state_distance(states[i], states[j])
                max_diff = max(max_diff, diff)
        
        return max_diff < self.convergence_threshold
    
    def _state_distance(self, state1: Dict, state2: Dict) -> float:
        """计算状态距离"""
        # 简化版：L2距离
        diff = 0
        for key in state1.keys():
            if key in state2:
                diff += (state1[key] - state2[key]) ** 2
        
        return diff ** 0.5
    
    def _get_neighbors(self, agent: BaseAgent) -> List[BaseAgent]:
        """获取邻居智能体"""
        # 简化版：所有其他智能体都是邻居
        return [a for a in self.agents if a.agent_id != agent.agent_id]
```

### 3.3 冲突解决（优先级仲裁）

```python
from dataclasses import dataclass

@dataclass
class Conflict:
    """冲突"""
    conflict_id: str
    resource: str  # 冲突资源（如: 空域、路径）
    agents: List[str]  # 涉及的智能体
    timestamp: float

@dataclass
class Resolution:
    """解决方案"""
    conflict_id: str
    winner: str  # 获胜的智能体
    action: str  # 解决动作
    timestamp: float

class ConflictResolver:
    """冲突解决器"""
    
    def __init__(self):
        self.conflicts = []
        self.resolutions = []
    
    def detect_conflicts(self, agents: List[BaseAgent]) -> List[Conflict]:
        """检测冲突"""
        conflicts = []
        
        # 1. 距离冲突检测
        conflicts.extend(self._detect_proximity_conflicts(agents))
        
        # 2. 路径冲突检测
        conflicts.extend(self._detect_path_conflicts(agents))
        
        # 3. 资源冲突检测
        conflicts.extend(self._detect_resource_conflicts(agents))
        
        self.conflicts = conflicts
        return conflicts
    
    def _detect_proximity_conflicts(self, agents: List[BaseAgent]) -> List[Conflict]:
        """检测距离冲突"""
        conflicts = []
        min_distance = 5.0  # 5米
        
        for i, agent_a in enumerate(agents):
            for agent_b in agents[i+1:]:
                # 获取位置
                pos_a = agent_a.position if hasattr(agent_a, 'position') else None
                pos_b = agent_b.position if hasattr(agent_b, 'position') else None
                
                if pos_a and pos_b:
                    distance = pos_a.distance_to(pos_b)
                    
                    if distance < min_distance:
                        conflict = Conflict(
                            conflict_id=f"proximity_{agent_a.agent_id}_{agent_b.agent_id}",
                            resource="airspace",
                            agents=[agent_a.agent_id, agent_b.agent_id],
                            timestamp=time.time()
                        )
                        conflicts.append(conflict)
        
        return conflicts
    
    def _detect_path_conflicts(self, agents: List[BaseAgent]) -> List[Conflict]:
        """检测路径冲突"""
        conflicts = []
        
        # 获取所有智能体的路径
        paths = {}
        for agent in agents:
            if hasattr(agent, 'current_waypoints') and agent.current_waypoints:
                paths[agent.agent_id] = agent.current_waypoints
        
        # 检查路径交叉
        agent_ids = list(paths.keys())
        for i, id_a in enumerate(agent_ids):
            for id_b in agent_ids[i+1:]:
                # 检查路径交叉点
                intersections = self._find_intersections(paths[id_a], paths[id_b])
                
                if intersections:
                    for intersection in intersections:
                        conflict = Conflict(
                            conflict_id=f"path_{id_a}_{id_b}",
                            resource=f"waypoint_{intersection}",
                            agents=[id_a, id_b],
                            timestamp=time.time()
                        )
                        conflicts.append(conflict)
        
        return conflicts
    
    def _detect_resource_conflicts(self, agents: List[BaseAgent]) -> List[Conflict]:
        """检测资源冲突"""
        conflicts = []
        
        # 资源分配表
        resources = {}
        for agent in agents:
            if hasattr(agent, 'allocated_resources'):
                for resource in agent.allocated_resources:
                    if resource not in resources:
                        resources[resource] = []
                    resources[resource].append(agent.agent_id)
        
        # 检查资源冲突
        for resource, agent_ids in resources.items():
            if len(agent_ids) > 1:
                conflict = Conflict(
                    conflict_id=f"resource_{resource}",
                    resource=resource,
                    agents=agent_ids,
                    timestamp=time.time()
                )
                conflicts.append(conflict)
        
        return conflicts
    
    def _find_intersections(self, path_a: List, path_b: List) -> List[str]:
        """查找路径交叉点"""
        intersections = []
        
        # 简化版：检查相同的航点
        for i, wp_a in enumerate(path_a):
            for j, wp_b in enumerate(path_b):
                # 检查位置是否相同
                if wp_a.position.distance_to(wp_b.position) < 1.0:  # 1米内
                    intersection = f"{i}_{j}"
                    intersections.append(intersection)
        
        return intersections
    
    def resolve(self, conflicts: List[Conflict], agents: List[BaseAgent]) -> List[Resolution]:
        """解决冲突"""
        resolutions = []
        
        for conflict in conflicts:
            # 计算每个智能体的优先级
            priorities = {}
            for agent_id in conflict.agents:
                agent = self._find_agent(agent_id, agents)
                priority = self._calculate_priority(agent, conflict)
                priorities[agent_id] = priority
            
            # 高优先级智能体获胜
            winner = max(priorities, key=priorities.get)
            
            # 创建解决方案
            resolution = Resolution(
                conflict_id=conflict.conflict_id,
                winner=winner,
                action="grant_access",
                timestamp=time.time()
            )
            resolutions.append(resolution)
            
            # 通知相关智能体
            self._notify_resolution(conflict, resolution, agents)
        
        self.resolutions = resolutions
        return resolutions
    
    def _find_agent(self, agent_id: str, agents: List[BaseAgent]) -> BaseAgent:
        """查找智能体"""
        for agent in agents:
            if agent.agent_id == agent_id:
                return agent
        return None
    
    def _calculate_priority(self, agent: BaseAgent, conflict: Conflict) -> float:
        """计算优先级"""
        # 简化版：基于重要性、紧急性、能力
        importance = getattr(agent, 'importance', 5.0)  # 1-10
        urgency = getattr(agent, 'urgency', 0.5)  # 0-1
        capability = len(agent.capabilities)  # 能力数量
        
        priority = (
            importance * 0.4 +
            urgency * 10 * 0.3 +
            capability * 0.3
        )
        
        return priority
    
    def _notify_resolution(self, conflict: Conflict, resolution: Resolution, agents: List[BaseAgent]):
        """通知解决方案"""
        for agent in agents:
            if agent.agent_id in conflict.agents:
                agent.receive_message({
                    "type": "conflict_resolution",
                    "conflict_id": conflict.conflict_id,
                    "winner": resolution.winner,
                    "action": resolution.action
                })
                agent.process_messages()
```

---

## 4. 通讯协议设计

### 4.1 消息格式

```python
from typing import Any, Optional
from dataclasses import dataclass, asdict
import time
import json

@dataclass
class Message:
    """智能体间消息"""
    msg_id: str
    msg_type: MessageType
    sender_id: str
    receiver_id: str  # "broadcast" 或具体的agent_id
    timestamp: float
    payload: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """转字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转JSON"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        """从字典创建"""
        return cls(
            msg_id=data["msg_id"],
            msg_type=MessageType(data["msg_type"]),
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            timestamp=data["timestamp"],
            payload=data["payload"]
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """从JSON创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)

# 消息工厂
class MessageFactory:
    """消息工厂"""
    
    @staticmethod
    def create_message(msg_type: MessageType, sender_id: str, receiver_id: str,
                     payload: Dict[str, Any]) -> Message:
        """创建消息"""
        import uuid
        return Message(
            msg_id=str(uuid.uuid4()),
            msg_type=msg_type,
            sender_id=sender_id,
            receiver_id=receiver_id,
            timestamp=time.time(),
            payload=payload
        )
    
    @staticmethod
    def create_heartbeat(sender_id: str) -> Message:
        """创建心跳消息"""
        return MessageFactory.create_message(
            msg_type=MessageType.HEARTBEAT,
            sender_id=sender_id,
            receiver_id="broadcast",
            payload={"status": "alive"}
        )
    
    @staticmethod
    def create_status_update(sender_id: str, status: Dict) -> Message:
        """创建状态更新消息"""
        return MessageFactory.create_message(
            msg_type=MessageType.STATUS_UPDATE,
            sender_id=sender_id,
            receiver_id="broadcast",
            payload=status
        )
    
    @staticmethod
    def create_task_assign(sender_id: str, receiver_id: str, task: Task) -> Message:
        """创建任务分配消息"""
        return MessageFactory.create_message(
            msg_type=MessageType.TASK_ASSIGN,
            sender_id=sender_id,
            receiver_id=receiver_id,
            payload={"task": task.__dict__}
        )
    
    @staticmethod
    def create_alert(sender_id: str, alert_type: str, details: Dict) -> Message:
        """创建警报消息"""
        return MessageFactory.create_message(
            msg_type=MessageType.ALERT,
            sender_id=sender_id,
            receiver_id="broadcast",
            payload={
                "alert_type": alert_type,
                "details": details
            }
        )
```

### 4.2 通讯接口

```python
class CommunicationInterface:
    """通讯接口"""
    
    def __init__(self, agent: BaseAgent):
        self.agent = agent
        self.message_handlers = {}
        
        # 注册默认消息处理器
        self._register_default_handlers()
    
    def send_message(self, message: Message):
        """发送消息"""
        # 根据通讯模式选择发送方式
        if isinstance(self.agent, CommunicationAgent):
            # 使用通讯智能体发送
            self.agent.act({"type": "send_message", "message": message})
        else:
            # 默认通过MQTT发送
            self._send_via_mqtt(message)
    
    def receive_message(self, message: Message):
        """接收消息"""
        # 添加到消息队列
        self.agent.receive_message(message.to_dict())
    
    def process_messages(self) -> List[Dict]:
        """处理消息"""
        return self.agent.process_messages()
    
    def register_handler(self, msg_type: MessageType, handler):
        """注册消息处理器"""
        self.message_handlers[msg_type] = handler
    
    def _send_via_mqtt(self, message: Message):
        """通过MQTT发送"""
        # 实际实现：发布到MQTT Broker
        topic = f"agent/{message.receiver_id}/{message.msg_type.value}"
        payload = message.to_json()
        
        # 发布消息
        # mqtt_client.publish(topic, payload)
    
    def _register_default_handlers(self):
        """注册默认消息处理器"""
        self.register_handler(MessageType.HEARTBEAT, self._handle_heartbeat)
        self.register_handler(MessageType.STATUS_UPDATE, self._handle_status_update)
        self.register_handler(MessageType.ALERT, self._handle_alert)
    
    def _handle_heartbeat(self, message: Message) -> Dict:
        """处理心跳"""
        return {"status": "ack", "to": message.sender_id}
    
    def _handle_status_update(self, message: Message) -> Dict:
        """处理状态更新"""
        # 更新智能体状态
        if "state" in message.payload:
            self.agent.state = AgentState(message.payload["state"])
        
        return {"status": "updated"}
    
    def _handle_alert(self, message: Message) -> Dict:
        """处理警报"""
        alert_type = message.payload.get("alert_type")
        details = message.payload.get("details", {})
        
        # 根据警报类型处理
        if alert_type == "proximity_warning":
            # 距离警告
            print(f"Proximity warning from {message.sender_id}: {details}")
        elif alert_type == "anomaly_detected":
            # 异常检测
            print(f"Anomaly detected: {details}")
        
        return {"status": "ack"}
```

---

## 5. 决策算法设计

### 5.1 强化学习决策

```python
import numpy as np
from typing import List, Tuple, Dict

class QLearningAgent:
    """Q-Learning智能体"""
    
    def __init__(self, state_space: int, action_space: int, 
                 learning_rate: float = 0.1, 
                 discount_factor: float = 0.95,
                 exploration_rate: float = 0.1):
        self.state_space = state_space
        self.action_space = action_space
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        
        # Q表
        self.q_table = np.zeros((state_space, action_space))
    
    def choose_action(self, state: int, explore: bool = True) -> int:
        """选择动作"""
        if explore and np.random.random() < self.exploration_rate:
            # 探索：随机选择
            return np.random.randint(self.action_space)
        else:
            # 利用：选择Q值最大的动作
            return np.argmax(self.q_table[state])
    
    def learn(self, state: int, action: int, reward: float, 
             next_state: int) -> None:
        """学习更新"""
        # Q-Learning更新公式
        best_next_action = np.argmax(self.q_table[next_state])
        td_target = reward + self.discount_factor * self.q_table[next_state, best_next_action]
        td_error = td_target - self.q_table[state, action]
        
        self.q_table[state, action] += self.learning_rate * td_error
    
    def get_policy(self) -> np.ndarray:
        """获取策略"""
        return np.argmax(self.q_table, axis=1)

class DQN:
    """深度Q网络"""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dims: List[int] = None):
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # 构建网络
        if hidden_dims is None:
            hidden_dims = [128, 128]
        
        layers = []
        prev_dim = state_dim
        for dim in hidden_dims:
            layers.append(tf.keras.layers.Dense(dim, activation='relu'))
            prev_dim = dim
        
        layers.append(tf.keras.layers.Dense(action_dim, activation='linear'))
        
        self.model = tf.keras.Sequential(layers)
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss='mse'
        )
    
    def predict(self, state: np.ndarray) -> np.ndarray:
        """预测Q值"""
        return self.model.predict(state[np.newaxis, :])[0]
    
    def train(self, states: np.ndarray, actions: np.ndarray, 
              rewards: np.ndarray, next_states: np.ndarray,
              dones: np.ndarray) -> float:
        """训练网络"""
        # 计算目标Q值
        next_q_values = self.model.predict(next_states)
        max_next_q_values = np.max(next_q_values, axis=1)
        target_q_values = rewards + (1 - dones) * 0.95 * max_next_q_values
        
        # 预测当前Q值
        current_q_values = self.model.predict(states)
        
        # 更新目标Q值
        for i in range(len(states)):
            current_q_values[i, actions[i]] = target_q_values[i]
        
        # 训练
        history = self.model.fit(states, current_q_values, verbose=0)
        return history.history['loss'][0]
```

---

## 6. 具身智能扩展

### 6.1 记忆系统

```python
from typing import List, Dict
import numpy as np

class EpisodicMemory:
    """情景记忆系统"""
    
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.episodes = []
    
    def store(self, episode: Dict) -> None:
        """存储情景"""
        self.episodes.append(episode)
        
        # 限制容量
        if len(self.episodes) > self.capacity:
            self.episodes.pop(0)
    
    def retrieve(self, query: Dict, k: int = 5) -> List[Dict]:
        """检索相关情景"""
        # 简化版：随机采样
        import random
        if len(self.episodes) <= k:
            return self.episodes.copy()
        
        return random.sample(self.episodes, k)
    
    def search(self, key: str, value: Any) -> List[Dict]:
        """搜索情景"""
        return [ep for ep in self.episodes if ep.get(key) == value]

class SemanticMemory:
    """语义记忆系统"""
    
    def __init__(self):
        self.facts = {}
        self.rules = {}
    
    def add_fact(self, key: str, value: Any):
        """添加事实"""
        self.facts[key] = value
    
    def add_rule(self, key: str, rule: callable):
        """添加规则"""
        self.rules[key] = rule
    
    def query(self, key: str) -> Any:
        """查询"""
        if key in self.facts:
            return self.facts[key]
        elif key in self.rules:
            return self.rules[key]
        else:
            return None
```

### 6.2 规划系统

```python
class HierarchicalPlanner:
    """分层规划器"""
    
    def __init__(self):
        self.high_level_planner = HighLevelPlanner()
        self.low_level_planner = LowLevelPlanner()
    
    def plan(self, task: Task, perception: Dict, memory: EpisodicMemory) -> Dict:
        """规划"""
        # 高层规划
        high_level_plan = self.high_level_planner.plan(task, perception, memory)
        
        # 低层规划
        low_level_plan = self.low_level_planner.plan(
            high_level_plan,
            perception,
            memory
        )
        
        return {
            "high_level": high_level_plan,
            "low_level": low_level_plan
        }

class HighLevelPlanner:
    """高层规划器"""
    
    def plan(self, task: Task, perception: Dict, memory: EpisodicMemory) -> Dict:
        """高层规划"""
        # 简化版：返回主要步骤
        return {
            "steps": [
                {"step": 1, "action": "navigate", "target": task.location},
                {"step": 2, "action": "perform_task", "type": task.task_type}
            ]
        }

class LowLevelPlanner:
    """低层规划器"""
    
    def plan(self, high_level: Dict, perception: Dict, memory: EpisodicMemory) -> List:
        """低层规划"""
        # 简化版：生成航点序列
        waypoints = []
        for step in high_level["steps"]:
            if step["action"] == "navigate":
                waypoints.append(step["target"])
        
        return waypoints
```

---

## 7. 仿真与测试

### 7.1 仿真环境

```python
class SimulationEnvironment:
    """仿真环境"""
    
    def __init__(self, num_drones: int = 5):
        self.num_drones = num_drones
        self.drones = []
        self.obstacles = []
        self.targets = []
        
        # 初始化无人机
        for i in range(num_drones):
            drone = {
                "id": f"drone_{i}",
                "position": Position(0.0, 0.0, 0.0),
                "velocity": Velocity(0.0, 0.0, 0.0),
                "state": "idle"
            }
            self.drones.append(drone)
    
    def reset(self):
        """重置环境"""
        # 重置所有无人机位置
        for i, drone in enumerate(self.drones):
            drone["position"] = Position(
                lat=31.2304 + i * 0.0001,
                lon=121.4737 + i * 0.0001,
                alt=10.0
            )
            drone["velocity"] = Velocity(0.0, 0.0, 0.0)
            drone["state"] = "idle"
    
    def step(self, actions: Dict) -> Dict:
        """执行一步"""
        # 执行动作
        for drone_id, action in actions.items():
            drone = self._get_drone(drone_id)
            if drone:
                self._execute_action(drone, action)
        
        # 更新状态
        for drone in self.drones:
            self._update_drone(drone)
        
        # 返回观察
        return self._get_observations()
    
    def _get_drone(self, drone_id: str) -> Dict:
        """获取无人机"""
        for drone in self.drones:
            if drone["id"] == drone_id:
                return drone
        return None
    
    def _execute_action(self, drone: Dict, action: Dict):
        """执行动作"""
        if action.get("type") == "move_to":
            target = action.get("target")
            if target:
                # 简化版：直接设置为目标位置
                drone["target_position"] = Position(
                    lat=target["lat"],
                    lon=target["lon"],
                    alt=target["alt"]
                )
    
    def _update_drone(self, drone: Dict):
        """更新无人机状态"""
        if "target_position" in drone:
            # 简化版：朝目标移动
            target = drone["target_position"]
            
            # 移动
            drone["position"] = Position(
                lat=drone["position"].lat + (target.lat - drone["position"].lat) * 0.1,
                lon=drone["position"].lon + (target.lon - drone["position"].lon) * 0.1,
                alt=drone["position"].alt + (target.alt - drone["position"].alt) * 0.1
            )
            
            # 检查是否到达
            if drone["position"].distance_to(target) < 1.0:
                drone["state"] = "arrived"
    
    def _get_observations(self) -> Dict:
        """获取观察"""
        return {
            "drones": [
                {
                    "id": d["id"],
                    "position": {
                        "lat": d["position"].lat,
                        "lon": d["position"].lon,
                        "alt": d["position"].alt
                    },
                    "state": d["state"]
                }
                for d in self.drones
            ],
            "obstacles": self.obstacles,
            "targets": self.targets
        }
```

### 7.2 测试框架

```python
class TestFramework:
    """测试框架"""
    
    def __init__(self, agents: List[BaseAgent], environment: SimulationEnvironment):
        self.agents = agents
        self.environment = environment
        self.test_results = []
    
    def run_test(self, test_name: str, num_steps: int = 100) -> Dict:
        """运行测试"""
        # 重置环境
        self.environment.reset()
        
        # 运行仿真
        for step in range(num_steps):
            # 获取观察
            observations = self.environment._get_observations()
            
            # 每个智能体决策
            actions = {}
            for agent in self.agents:
                perception = agent.perceive(observations)
                decision = agent.decide(perception)
                actions[agent.agent_id] = decision
            
            # 执行动作
            self.environment.step(actions)
        
        # 收集结果
        result = {
            "test_name": test_name,
            "num_steps": num_steps,
            "final_state": self.environment._get_observations()
        }
        
        self.test_results.append(result)
        return result
```

---

**文档状态**: V1.0  
**最后更新**: 2026-02-15  
**维护者**: Development Team
