"""
施工安全监测系统 - 统一检测器

功能:
1. 安全装备检测（4类）
2. 危险区域管控（3类）
3. 危险行为识别（5类）
4. 机械与设备（3类）

作者: 空中智能体团队
日期: 2026-03-26
"""

import cv2
import torch
import yaml
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Detection:
    """检测结果"""
    class_id: int
    class_name: str
    class_name_cn: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    keypoints: Optional[List[Tuple[float, float]]] = None  # 关键点（可选）


@dataclass
class Alert:
    """报警信息"""
    alert_type: str
    class_name: str
    message: str
    level: str  # critical, serious, warning, info
    timestamp: str
    bbox: Optional[List[float]] = None


@dataclass
class Compliance:
    """合规统计"""
    total_persons: int
    persons_with_helmet: int
    persons_with_vest: int
    helmet_rate: float
    vest_rate: float


class SafetyDetector:
    """施工安全统一检测器"""
    
    def __init__(self, config_path: str, device: str = "cuda"):
        """
        初始化检测器
        
        Args:
            config_path: 配置文件路径
            device: 运行设备 (cuda/cpu)
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.device = device
        
        # 加载类别映射
        self.classes = self.config['yolo']['classes']
        self.class_names = {k: v['name'] for k, v in self.classes.items()}
        self.class_names_cn = {k: v['zh'] for k, v in self.classes.items()}
        
        # 加载模型
        self.model = self._load_model()
        
        # 报警配置
        self.alert_config = self.config['alerts']
        
        # 危险区域配置
        self.danger_zones = self.config.get('danger_zones', {})
        
        # 报警历史（用于抑制）
        self.alert_history = {}
        
        # 机械位置跟踪（用于动态危险区域）
        self.machinery_positions = {}
    
    def _load_model(self):
        """加载 YOLOv8-Pose 模型"""
        try:
            from ultralytics import YOLO
            
            weights_path = self.config['yolo']['model']['weights']
            
            # 检查是否是 TensorRT 引擎
            if weights_path.endswith('.engine'):
                return self._load_tensorrt_model(weights_path)
            else:
                model = YOLO(weights_path)
                return model
        except Exception as e:
            print(f"加载模型失败: {e}")
            return None
    
    def _load_tensorrt_model(self, engine_path):
        """加载 TensorRT 模型"""
        try:
            import tensorrt as trt
            
            logger = trt.Logger(trt.Logger.INFO)
            with open(engine_path, 'rb') as f:
                runtime = trt.Runtime(logger)
                engine = runtime.deserialize_cuda_engine(f.read())
            
            return {'engine': engine, 'context': engine.create_execution_context()}
        except Exception as e:
            print(f"加载 TensorRT 模型失败: {e}")
            return None
    
    def detect(self, image: np.ndarray) -> Dict[str, Any]:
        """
        统一检测接口
        
        Args:
            image: BGR 图像 (numpy array)
        
        Returns:
            {
                "detections": List[Detection],
                "compliance": Compliance,
                "alerts": List[Alert],
                "danger_zones": Dict,
                "machinery": List
            }
        """
        results = {
            "detections": [],
            "compliance": None,
            "alerts": [],
            "danger_zones": [],
            "machinery": []
        }
        
        # 1. YOLOv8-Pose 检测
        detections = self._detect_yolo(image)
        results["detections"] = detections
        
        # 2. 更新机械位置（用于动态危险区域）
        machinery = self._track_machinery(detections)
        results["machinery"] = machinery
        
        # 3. 检查危险区域
        danger_zone_alerts = self._check_danger_zones(detections, machinery)
        
        # 4. 生成报警
        behavior_alerts = self._generate_alerts(detections, image)
        results["alerts"] = danger_zone_alerts + behavior_alerts
        
        # 5. 计算合规率
        results["compliance"] = self._calculate_compliance(detections)
        
        return results
    
    def _detect_yolo(self, image: np.ndarray) -> List[Detection]:
        """YOLOv8-Pose 检测"""
        detections = []
        
        if self.model is None:
            return detections
        
        # 推理配置
        inference_config = self.config['yolo']['inference']
        
        if isinstance(self.model, dict):
            # TensorRT 推理
            results_list = self._infer_tensorrt(image)
        else:
            # YOLO 推理
            results_list = self.model.predict(
                image,
                conf=inference_config['conf_threshold'],
                iou=inference_config['iou_threshold'],
                device=self.device,
                verbose=False
            )
        
        # 解析结果
        for result in results_list:
            for box in result.boxes:
                class_id = int(box.cls)
                confidence = float(box.conf)
                bbox = box.xyxy.tolist()[0]
                
                # 获取关键点（如果有）
                keypoints = None
                if hasattr(result, 'keypoints') and result.keypoints is not None:
                    if len(result.keypoints) > 0:
                        kps = result.keypoints[0].data.tolist()
                        if kps:
                            keypoints = [(kp[0], kp[1]) for kp in kps[0]]
                
                detection = Detection(
                    class_id=class_id,
                    class_name=self.class_names.get(class_id, f"class_{class_id}"),
                    class_name_cn=self.class_names_cn.get(class_id, f"类别{class_id}"),
                    confidence=confidence,
                    bbox=bbox,
                    keypoints=keypoints
                )
                detections.append(detection)
        
        return detections
    
    def _track_machinery(self, detections: List[Detection]) -> List[Dict]:
        """跟踪机械位置"""
        machinery_classes = [12, 13, 14]  # crane, excavator, truck
        
        machinery_list = []
        
        for det in detections:
            if det.class_id in machinery_classes:
                # 计算机械中心点
                x1, y1, x2, y2 = det.bbox
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                
                machinery_info = {
                    "class_id": det.class_id,
                    "class_name": det.class_name,
                    "class_name_cn": det.class_name_cn,
                    "position": (cx, cy),
                    "bbox": det.bbox,
                    "confidence": det.confidence
                }
                
                machinery_list.append(machinery_info)
                
                # 更新位置历史
                self.machinery_positions[det.class_id] = {
                    "position": (cx, cy),
                    "timestamp": datetime.now()
                }
        
        return machinery_list
    
    def _check_danger_zones(
        self,
        detections: List[Detection],
        machinery: List[Dict]
    ) -> List[Alert]:
        """检查危险区域"""
        alerts = []
        
        # 1. 检查静态危险区域
        static_zones = self.danger_zones.get('static', {})
        
        for zone_id, zone_info in static_zones.items():
            polygon = np.array(zone_info['points'])
            
            # 检查每个人员是否在危险区域
            for det in detections:
                if det.class_id in [0, 1, 2, 3]:  # 人员类别
                    person_center = self._get_bbox_center(det.bbox)
                    
                    if self._point_in_polygon(person_center, polygon):
                        alert = Alert(
                            alert_type="danger_zone",
                            class_name=det.class_name,
                            message=f"{zone_info['name']}: 检测到{det.class_name_cn}",
                            level="critical",
                            timestamp=datetime.now().isoformat(),
                            bbox=det.bbox
                        )
                        alerts.append(alert)
        
        # 2. 检查动态危险区域（机械联动）
        if self.danger_zones.get('dynamic', {}).get('enabled'):
            alerts.extend(self._check_dynamic_danger_zones(detections, machinery))
        
        return alerts
    
    def _check_dynamic_danger_zones(
        self,
        detections: List[Detection],
        machinery: List[Dict]
    ) -> List[Alert]:
        """检查动态危险区域（机械作业范围）"""
        alerts = []
        
        for m in machinery:
            class_id = m['class_id']
            cx, cy = m['position']
            
            # 获取动态危险区域配置
            if class_id == 12:  # 塔吊
                config = self.danger_zones['dynamic'].get('crane', {})
            elif class_id == 13:  # 挖掘机
                config = self.danger_zones['dynamic'].get('excavator', {})
            else:
                continue
            
            radius = config.get('radius', 5)  # 默认5米
            level = config.get('level', 'serious')
            
            # 检查人员是否在机械危险范围内
            for det in detections:
                if det.class_id in [0, 1, 2, 3]:  # 人员类别
                    person_center = self._get_bbox_center(det.bbox)
                    
                    # 计算距离（需要知道实际像素到米的比例）
                    distance = self._calculate_distance(m['position'], person_center)
                    
                    if distance < radius:
                        alert = Alert(
                            alert_type="unsafe_distance",
                            class_name="unsafe_distance",
                            message=f"距离{m['class_name_cn']}过近({distance:.1f}m)",
                            level=level,
                            timestamp=datetime.now().isoformat(),
                            bbox=det.bbox
                        )
                        alerts.append(alert)
        
        return alerts
    
    def _generate_alerts(self, detections: List[Detection], image: np.ndarray) -> List[Alert]:
        """生成行为报警"""
        alerts = []
        
        # 报警级别映射
        alert_levels = {
            "critical": self.alert_config['critical']['classes'],
            "serious": self.alert_config['serious']['classes'],
            "warning": self.alert_config['warning']['classes'],
            "info": self.alert_config['info']['classes']
        }
        
        for det in detections:
            # 确定报警级别
            level = None
            for lvl, class_ids in alert_levels.items():
                if det.class_id in class_ids:
                    level = lvl
                    break
            
            if level is None or level == "info":
                continue
            
            # 检查报警抑制
            if self._should_suppress_alert(det):
                continue
            
            # 生成报警
            alert = Alert(
                alert_type="safety",
                class_name=det.class_name,
                message=f"检测到{det.class_name_cn}",
                level=level,
                timestamp=datetime.now().isoformat(),
                bbox=det.bbox
            )
            alerts.append(alert)
            
            # 记录报警历史
            self.alert_history[det.class_id] = datetime.now()
        
        return alerts
    
    def _should_suppress_alert(self, detection: Detection) -> bool:
        """检查是否应该抑制报警"""
        suppress_config = self.alert_config.get('suppress', {})
        same_target_minutes = suppress_config.get('same_target_minutes', 3)
        
        # 使用类别ID和位置作为唯一标识
        alert_key = f"{detection.class_id}_{int(detection.bbox[0]/50)}_{int(detection.bbox[1]/50)}"
        
        if alert_key in self.alert_history:
            last_alert_time = self.alert_history[alert_key]
            elapsed = (datetime.now() - last_alert_time).total_seconds() / 60
            
            if elapsed < same_target_minutes:
                return True
        
        return False
    
    def _calculate_compliance(self, detections: List[Detection]) -> Compliance:
        """计算合规率"""
        # 安全装备类别
        with_helmet_id = 0
        no_helmet_id = 1
        with_vest_id = 2
        no_vest_id = 3
        
        # 统计
        persons_with_helmet = 0
        persons_with_vest = 0
        total_persons = 0
        
        for det in detections:
            if det.class_id == with_helmet_id:
                persons_with_helmet += 1
                total_persons += 1
            elif det.class_id == no_helmet_id:
                total_persons += 1
            
            if det.class_id == with_vest_id:
                persons_with_vest += 1
            elif det.class_id == no_vest_id:
                # 如果没有反光衣但没被计入总人数，加1
                if det.class_id not in [with_helmet_id, no_helmet_id]:
                    total_persons += 1
        
        # 计算合规率
        # 注意：同一个人可能被检测为 with_helmet 或 no_helmet
        helmet_rate = persons_with_helmet / total_persons if total_persons > 0 else 1.0
        vest_rate = persons_with_vest / total_persons if total_persons > 0 else 1.0
        
        return Compliance(
            total_persons=total_persons,
            persons_with_helmet=persons_with_helmet,
            persons_with_vest=persons_with_vest,
            helmet_rate=helmet_rate,
            vest_rate=vest_rate
        )
    
    def _get_bbox_center(self, bbox: List[float]) -> Tuple[float, float]:
        """获取边界框中心点"""
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    
    def _point_in_polygon(self, point: Tuple[float, float], polygon: np.ndarray) -> bool:
        """判断点是否在多边形内"""
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if point[1] > min(p1y, p2y):
                if point[1] <= max(p1y, p2y):
                    if point[0] <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (point[1] - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or point[0] <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def _calculate_distance(
        self,
        point1: Tuple[float, float],
        point2: Tuple[float, float]
    ) -> float:
        """计算两点距离（需要像素到米的比例）"""
        # 简单实现：假设 100 像素 = 1 米（实际需要根据相机标定）
        pixel_per_meter = 100
        dx = point1[0] - point2[0]
        dy = point1[1] - point2[1]
        distance_pixels = np.sqrt(dx**2 + dy**2)
        return distance_pixels / pixel_per_meter
    
    def visualize(
        self,
        image: np.ndarray,
        results: Dict,
        output_path: Optional[str] = None
    ) -> np.ndarray:
        """
        可视化检测结果
        
        Args:
            image: 原始图像
            results: 检测结果
            output_path: 输出路径（可选）
        
        Returns:
            可视化后的图像
        """
        vis_image = image.copy()
        
        # 绘制危险区域
        static_zones = self.danger_zones.get('static', {})
        for zone_id, zone_info in static_zones.items():
            polygon = np.array(zone_info['points']).astype(np.int32)
            
            # 根据级别选择颜色
            if zone_info.get('level') == 'critical':
                color = (0, 0, 200)  # 红色
            else:
                color = (0, 200, 200)  # 黄色
            
            cv2.polylines(vis_image, [polygon], True, color, 2)
            cv2.fillPoly(vis_image, [polygon], (color[0], color[1], color[2], 50))
        
        # 绘制动态危险区域
        for m in results.get('machinery', []):
            if m['class_id'] == 12:  # 塔吊
                radius = self.danger_zones.get('dynamic', {}).get('crane', {}).get('radius', 10)
            elif m['class_id'] == 13:  # 挖掘机
                radius = self.danger_zones.get('dynamic', {}).get('excavator', {}).get('radius', 5)
            else:
                continue
            
            cx, cy = m['position']
            radius_pixels = int(radius * 100)  # 假设100像素=1米
            
            cv2.circle(vis_image, (int(cx), int(cy)), radius_pixels, (0, 165, 255), 2)
        
        # 绘制检测结果
        for det in results["detections"]:
            x1, y1, x2, y2 = [int(v) for v in det.bbox]
            
            # 根据类别选择颜色
            if det.class_id == 1:  # 未佩戴安全帽
                color = (0, 0, 255)  # 红色
            elif det.class_id == 3:  # 未穿反光衣
                color = (0, 255, 255)  # 黄色
            elif det.class_id in [4, 5, 6, 7, 8, 9, 10, 11]:  # 危险行为
                color = (0, 0, 255)  # 红色
            else:
                color = (0, 255, 0)  # 绿色
            
            # 绘制边界框
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)
            
            # 绘制标签
            label = f"{det.class_name_cn} {det.confidence:.2f}"
            cv2.putText(vis_image, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # 绘制合规率
        if results["compliance"]:
            compliance = results["compliance"]
            
            # 在左上角显示合规率
            y_offset = 30
            texts = [
                f"总人数: {compliance.total_persons}",
                f"安全帽: {compliance.helmet_rate:.1%}",
                f"反光衣: {compliance.vest_rate:.1%}"
            ]
            
            for i, text in enumerate(texts):
                cv2.putText(vis_image, text, (10, y_offset + i * 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 保存
        if output_path:
            cv2.imwrite(output_path, vis_image)
        
        return vis_image


def main():
    """测试入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="施工安全检测器")
    parser.add_argument("--config", type=str, default="configs/construction_safety.yaml")
    parser.add_argument("--image", type=str, required=True)
    parser.add_argument("--output", type=str, default="output.jpg")
    
    args = parser.parse_args()
    
    # 初始化检测器
    detector = SafetyDetector(args.config)
    
    # 加载图像
    image = cv2.imread(args.image)
    
    # 检测
    results = detector.detect(image)
    
    # 打印结果
    print(f"检测到 {len(results['detections'])} 个目标")
    print(f"合规率:")
    print(f"  总人数: {results['compliance'].total_persons}")
    print(f"  安全帽佩戴率: {results['compliance'].helmet_rate:.1%}")
    print(f"  反光衣穿戴率: {results['compliance'].vest_rate:.1%}")
    
    print(f"\n报警: {len(results['alerts'])} 个")
    for alert in results['alerts']:
        print(f"  [{alert.level}] {alert.message}")
    
    # 可视化
    detector.visualize(image, results, args.output)
    print(f"\n结果已保存到 {args.output}")


if __name__ == "__main__":
    main()
