#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
姿态识别 + 行为分析 + ID追踪

作者: 空中智能体团队
日期: 2026-03-25
"""

import os
import sys
import cv2
import torch
import numpy as np
from PIL import Image
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
import yaml

# YOLOv8-Pose
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# ByteTrack（假设已安装）
# from bytetrack import ByteTracker


@dataclass
class PersonState:
    """人员状态"""
    track_id: int
    keypoints: np.ndarray  # (17, 3) - (x, y, confidence)
    bbox: List[float]
    history: List[Dict]  # 历史帧信息
    action: Optional[str] = None
    action_confidence: float = 0.0
    duration: float = 0.0  # 行为持续时间


class PoseTracker:
    """姿态追踪器"""
    
    def __init__(
        self,
        config: Dict[str, Any],
        device: str = "cuda"
    ):
        """
        初始化姿态追踪器
        
        Args:
            config: 配置字典
            device: 推理设备
        """
        self.config = config
        self.device = device
        
        # 加载YOLOv8-Pose
        pose_config = config.get("pose", {})
        model_path = pose_config.get("model", "yolov8x-pose.pt")
        
        if YOLO_AVAILABLE:
            self.pose_model = YOLO(model_path)
            print(f"✓ YOLOv8-Pose加载完成: {model_path}")
        else:
            raise ImportError("ultralytics未安装，无法使用姿态检测")
        
        # 行为识别配置
        self.actions_config = config.get("actions", {})
        
        # 人员状态缓存
        self.person_states: Dict[int, PersonState] = {}
        
        # 帧计数器
        self.frame_count = 0
    
    def analyze(
        self,
        image: Any,
        person_detections: List[Dict],
        water_rois: Dict,
        warning_lines: Dict
    ) -> List[Dict]:
        """
        分析人员行为
        
        Args:
            image: 输入图像
            person_detections: YOLO检测的人员结果
            water_rois: 水面区域定义
            warning_lines: 警戒线定义
        
        Returns:
            行为识别结果列表
        """
        self.frame_count += 1
        
        # 1. 姿态检测
        pose_results = self._detect_poses(image)
        
        # 2. ID追踪（使用YOLO内置追踪）
        tracked_poses = self._track_poses(pose_results)
        
        # 3. 更新人员状态
        self._update_person_states(tracked_poses)
        
        # 4. 行为识别
        behavior_results = []
        
        for track_id, state in self.person_states.items():
            # 检测各类行为
            actions = []
            
            # 钓鱼
            if self.actions_config.get("fishing", {}).get("enabled", True):
                fishing_score = self._detect_fishing(state)
                if fishing_score > 0.6:
                    actions.append(("fishing", fishing_score))
            
            # 游泳
            if self.actions_config.get("swimming", {}).get("enabled", True):
                swimming_score = self._detect_swimming(state, water_rois)
                if swimming_score > 0.7:
                    actions.append(("swimming", swimming_score))
            
            # 嬉水
            if self.actions_config.get("playing", {}).get("enabled", True):
                playing_score = self._detect_playing(state, water_rois)
                if playing_score > 0.5:
                    actions.append(("playing", playing_score))
            
            # 闯入
            if self.actions_config.get("intrusion", {}).get("enabled", True):
                intrusion_score = self._detect_intrusion(state, warning_lines)
                if intrusion_score > 0.8:
                    actions.append(("intrusion", intrusion_score))
            
            # 选择得分最高的行为
            if actions:
                best_action, best_score = max(actions, key=lambda x: x[1])
                state.action = best_action
                state.action_confidence = best_score
                
                behavior_results.append({
                    "track_id": track_id,
                    "action": best_action,
                    "action_confidence": best_score,
                    "duration": state.duration,
                    "keypoints": state.keypoints.tolist(),
                    "bbox": state.bbox
                })
        
        return behavior_results
    
    def _detect_poses(self, image: Any) -> List[Dict]:
        """检测姿态"""
        results = self.pose_model.predict(
            image,
            conf=0.5,
            device=self.device,
            verbose=False
        )
        
        poses = []
        if len(results) > 0:
            result = results[0]
            
            if result.keypoints is not None:
                for i in range(len(result.keypoints)):
                    kpts = result.keypoints[i].data[0].cpu().numpy()  # (17, 3)
                    box = result.boxes[i]
                    
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])
                    
                    poses.append({
                        "keypoints": kpts,
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "confidence": conf
                    })
        
        return poses
    
    def _track_poses(self, pose_results: List[Dict]) -> List[Dict]:
        """追踪姿态（使用YOLO内置追踪）"""
        # 简化实现：实际应使用ByteTrack
        # 这里使用简化的ID分配
        
        for i, pose in enumerate(pose_results):
            # 简化：使用索引作为ID
            pose["track_id"] = i
        
        return pose_results
    
    def _update_person_states(self, tracked_poses: List[Dict]):
        """更新人员状态"""
        # 更新现有状态
        for pose in tracked_poses:
            track_id = pose["track_id"]
            
            if track_id in self.person_states:
                # 更新现有状态
                state = self.person_states[track_id]
                state.keypoints = pose["keypoints"]
                state.bbox = pose["bbox"]
                
                # 添加到历史
                state.history.append({
                    "frame": self.frame_count,
                    "keypoints": pose["keypoints"],
                    "bbox": pose["bbox"]
                })
                
                # 保持历史长度
                if len(state.history) > 100:
                    state.history.pop(0)
            else:
                # 创建新状态
                self.person_states[track_id] = PersonState(
                    track_id=track_id,
                    keypoints=pose["keypoints"],
                    bbox=pose["bbox"],
                    history=[{
                        "frame": self.frame_count,
                        "keypoints": pose["keypoints"],
                        "bbox": pose["bbox"]
                    }]
                )
        
        # 清理丢失的ID
        # 简化：实际应根据丢失时间清理
    
    def _detect_fishing(self, state: PersonState) -> float:
        """
        检测钓鱼行为
        
        规则：
        1. 手臂举高（手腕Y < 肩膀Y - 50）
        2. 持续静止 > 30秒
        3. 手持细长物体（可选）
        """
        kpts = state.keypoints
        
        # COCO关键点索引
        # 5: left_shoulder, 6: right_shoulder
        # 9: left_wrist, 10: right_wrist
        
        left_wrist = kpts[9]
        right_wrist = kpts[10]
        left_shoulder = kpts[5]
        right_shoulder = kpts[6]
        
        # 检查关键点置信度
        if left_wrist[2] < 0.5 or right_wrist[2] < 0.5:
            return 0.0
        
        # 规则1: 手臂举高
        shoulder_y = max(left_shoulder[1], right_shoulder[1])
        wrist_y = min(left_wrist[1], right_wrist[1])
        
        arms_raised = wrist_y < shoulder_y - 50
        arms_score = 0.3 if arms_raised else 0.0
        
        # 规则2: 持续静止
        static_score = 0.0
        if len(state.history) >= 30:  # 至少30帧（约1秒）
            # 计算历史位置方差
            positions = [h["keypoints"][0] for h in state.history[-30:]]  # nose
            positions = np.array(positions)
            
            variance = np.var(positions[:, :2], axis=0).sum()
            
            if variance < 100:  # 阈值
                static_score = 0.5
                state.duration = len(state.history) / 30.0  # 秒
        
        # 规则3: 手持物体（简化：检测手腕附近是否有细长物体）
        # 实际需要额外的目标检测
        object_score = 0.0
        
        # 综合得分
        total_score = arms_score + static_score + object_score
        
        return min(total_score, 1.0)
    
    def _detect_swimming(
        self,
        state: PersonState,
        water_rois: Dict
    ) -> float:
        """
        检测游泳行为
        
        规则：
        1. 人员在水面区域内
        2. 肢体有周期性运动
        3. 身体水平姿态
        """
        kpts = state.keypoints
        
        # 规则1: 在水面区域内
        in_water_score = 0.0
        if water_rois:
            # 使用人体中心判断
            person_center = np.mean(kpts[:, :2], axis=0)
            
            # 检查是否在任意ROI内
            for roi_name, roi_config in water_rois.items():
                if self._point_in_roi(person_center, roi_config):
                    in_water_score = 0.4
                    break
        
        # 规则2: 周期性运动
        periodic_score = 0.0
        if len(state.history) >= 60:  # 至少2秒
            # 检测手腕的周期性运动
            left_wrists = [h["keypoints"][9] for h in state.history[-60:]]
            right_wrists = [h["keypoints"][10] for h in state.history[-60:]]
            
            # 使用FFT检测周期性（简化）
            # 实际应使用更复杂的动作识别
            periodic_score = 0.3  # placeholder
        
        # 规则3: 身体姿态
        posture_score = 0.0
        # COCO: 5-6 shoulder, 11-12 hip
        if kpts[5][2] > 0.5 and kpts[11][2] > 0.5:
            shoulder_center = (kpts[5][:2] + kpts[6][:2]) / 2
            hip_center = (kpts[11][:2] + kpts[12][:2]) / 2
            
            # 计算身体角度
            delta = hip_center - shoulder_center
            angle = np.abs(np.arctan2(delta[1], delta[0]))
            
            # 水平姿态（角度接近90度）
            if angle > np.pi / 3:  # > 60度
                posture_score = 0.3
        
        # 综合得分
        total_score = in_water_score + periodic_score + posture_score
        
        return min(total_score, 1.0)
    
    def _detect_playing(
        self,
        state: PersonState,
        water_rois: Dict
    ) -> float:
        """检测嬉水行为"""
        # 类似swimming，但动作更剧烈
        swimming_score = self._detect_swimming(state, water_rois)
        
        # 检测突然运动
        sudden_motion_score = 0.0
        if len(state.history) >= 10:
            # 计算最近帧的运动幅度
            recent_speeds = []
            for i in range(-9, 0):
                pos1 = state.history[i]["keypoints"][0][:2]
                pos2 = state.history[i+1]["keypoints"][0][:2]
                speed = np.linalg.norm(pos2 - pos1)
                recent_speeds.append(speed)
            
            avg_speed = np.mean(recent_speeds)
            if avg_speed > 10:  # 快速运动
                sudden_motion_score = 0.3
        
        total_score = swimming_score * 0.7 + sudden_motion_score * 0.3
        
        return min(total_score, 1.0)
    
    def _detect_intrusion(
        self,
        state: PersonState,
        warning_lines: Dict
    ) -> float:
        """
        检测闯入行为
        
        规则：
        1. 人员越过警戒线
        2. 人员在禁入区域内
        """
        kpts = state.keypoints
        
        # 规则1: 越过警戒线
        cross_line_score = 0.0
        if warning_lines and len(state.history) >= 2:
            # 使用人体中心
            current_center = np.mean(kpts[:, :2], axis=0)
            prev_center = np.mean(state.history[-2]["keypoints"][:, :2], axis=0)
            
            for line_name, line_config in warning_lines.items():
                if self._crossed_line(prev_center, current_center, line_config):
                    cross_line_score = 0.7
                    break
        
        # 规则2: 在禁入区域（简化：与water_rois类似）
        # ...
        
        return cross_line_score
    
    def _point_in_roi(self, point: np.ndarray, roi_config: Dict) -> bool:
        """判断点是否在ROI内"""
        roi_type = roi_config.get("type", "rectangle")
        
        if roi_type == "rectangle":
            x, y = point
            return (roi_config["x"] <= x <= roi_config["x"] + roi_config["width"] and
                    roi_config["y"] <= y <= roi_config["y"] + roi_config["height"])
        
        elif roi_type == "polygon":
            import cv2
            points = np.array(roi_config["points"], dtype=np.int32)
            return cv2.pointPolygonTest(points, tuple(point), False) >= 0
        
        return False
    
    def _crossed_line(
        self,
        prev_point: np.ndarray,
        curr_point: np.ndarray,
        line_config: Dict
    ) -> bool:
        """判断是否越过线"""
        start = np.array(line_config["start"])
        end = np.array(line_config["end"])
        
        # 简化：使用向量叉积判断
        # 实际应考虑方向
        
        def side_of_line(point, line_start, line_end):
            return ((line_end[0] - line_start[0]) * (point[1] - line_start[1]) - 
                    (line_end[1] - line_start[1]) * (point[0] - line_start[0]))
        
        prev_side = side_of_line(prev_point, start, end)
        curr_side = side_of_line(curr_point, start, end)
        
        # 跨越线
        return prev_side * curr_side < 0


def main():
    """测试入口"""
    # 示例配置
    config = {
        "pose": {
            "model": "yolov8x-pose.pt"
        },
        "actions": {
            "fishing": {"enabled": True},
            "swimming": {"enabled": True},
            "playing": {"enabled": True},
            "intrusion": {"enabled": True}
        }
    }
    
    # 初始化
    tracker = PoseTracker(config, device="cuda")
    
    # 测试图像
    test_image = "data/test/person.jpg"
    if os.path.exists(test_image):
        image = cv2.imread(test_image)
        
        # 模拟人员检测
        person_detections = [{"class_name": "person", "bbox": [100, 100, 200, 300]}]
        
        # 分析行为
        results = tracker.analyze(
            image,
            person_detections,
            water_rois={},
            warning_lines={}
        )
        
        print("\n行为识别结果:")
        for res in results:
            print(f"  ID {res['track_id']}: {res['action']} ({res['action_confidence']:.2f})")


if __name__ == "__main__":
    main()
