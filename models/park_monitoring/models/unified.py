"""
园区监测系统 - 统一检测器

功能:
1. 周界安全检测（4类）
2. 人员行为识别（5类）
3. 车辆管理（3类）
4. 停车位检测（1类，OBB）

作者: 空中智能体团队
日期: 2026-03-26
"""

import cv2
import torch
import yaml
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Detection:
    """检测结果"""
    class_id: int
    class_name: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    bbox_type: str = "hbb"  # hbb: 水平框, obb: 旋转框


@dataclass
class Alert:
    """报警信息"""
    alert_type: str
    class_name: str
    message: str
    level: str  # critical, warning, info
    timestamp: str
    bbox: Optional[List[float]] = None


class ParkDetector:
    """园区监测统一检测器"""
    
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
        self.yolo_model = self._load_yolo_model()
        self.yolo_obb_model = self._load_yolo_obb_model()
        
        # 报警配置
        self.alert_config = self.config['alerts']
        
        # 停车位占用状态
        self.parking_spots = {}
        
        # 报警历史（用于抑制）
        self.alert_history = {}
    
    def _load_yolo_model(self):
        """加载 YOLOv8-Pose 模型"""
        try:
            from ultralytics import YOLO
            
            weights_path = self.config['yolo']['model']['weights']
            
            # 检查是否是 TensorRT 引擎
            if weights_path.endswith('.engine'):
                # TensorRT 推理需要特殊处理
                return self._load_tensorrt_model(weights_path)
            else:
                # ONNX 或 PyTorch 模型
                model = YOLO(weights_path)
                return model
        except Exception as e:
            print(f"加载 YOLO 模型失败: {e}")
            return None
    
    def _load_yolo_obb_model(self):
        """加载 YOLOv8-Obb 模型"""
        try:
            from ultralytics import YOLO
            
            weights_path = self.config['yolo_obb']['model']['weights']
            model = YOLO(weights_path)
            return model
        except Exception as e:
            print(f"加载 YOLO-Obb 模型失败: {e}")
            return None
    
    def _load_tensorrt_model(self, engine_path):
        """加载 TensorRT 模型"""
        # TensorRT 推理实现
        try:
            import tensorrt as trt
            import pycuda.driver as cuda
            
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
                "parking_spots": Dict,
                "alerts": List[Alert],
                "stats": Dict
            }
        """
        results = {
            "detections": [],
            "parking_spots": {},
            "alerts": [],
            "stats": {
                "total_persons": 0,
                "total_vehicles": 0,
                "compliance_rate": 0.0
            }
        }
        
        # 1. YOLOv8-Pose 检测
        yolo_detections = self._detect_yolo(image)
        results["detections"].extend(yolo_detections)
        
        # 2. YOLOv8-Obb 停车位检测
        parking_detections = self._detect_parking_spots(image)
        results["parking_spots"] = parking_detections
        
        # 3. 生成报警
        alerts = self._generate_alerts(yolo_detections, image)
        results["alerts"] = alerts
        
        # 4. 统计信息
        results["stats"] = self._calculate_stats(yolo_detections)
        
        return results
    
    def _detect_yolo(self, image: np.ndarray) -> List[Detection]:
        """YOLOv8-Pose 检测"""
        detections = []
        
        if self.yolo_model is None:
            return detections
        
        # 推理
        inference_config = self.config['yolo']['inference']
        
        if isinstance(self.yolo_model, dict):
            # TensorRT 推理
            results_list = self._infer_tensorrt(image)
        else:
            # YOLO 推理
            results_list = self.yolo_model.predict(
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
                
                detection = Detection(
                    class_id=class_id,
                    class_name=self.class_names.get(class_id, f"class_{class_id}"),
                    confidence=confidence,
                    bbox=bbox,
                    bbox_type="hbb"
                )
                detections.append(detection)
        
        return detections
    
    def _detect_parking_spots(self, image: np.ndarray) -> Dict:
        """停车位检测（OBB）"""
        parking_spots = {}
        
        if self.yolo_obb_model is None:
            return parking_spots
        
        # 推理
        inference_config = self.config['yolo_obb']['inference']
        
        results_list = self.yolo_obb_model.predict(
            image,
            conf=inference_config['conf_threshold'],
            iou=inference_config['iou_threshold'],
            device=self.device,
            verbose=False
        )
        
        # 解析结果
        spot_id = 0
        for result in results_list:
            if hasattr(result, 'obb') and result.obb is not None:
                for obb in result.obb:
                    # OBB 格式: [cx, cy, w, h, angle] 或 [x1,y1, x2,y2, x3,y3, x4,y4]
                    confidence = float(obb.conf)
                    
                    # 获取旋转框的四角坐标
                    if hasattr(obb, 'xyxyxyxy'):
                        polygon = obb.xyxyxyxy.tolist()[0]  # 8个值
                    else:
                        # 从 cx, cy, w, h, angle 计算
                        cx, cy, w, h, angle = obb.xywhr.tolist()[0]
                        polygon = self._obb_to_polygon(cx, cy, w, h, angle)
                    
                    parking_spots[spot_id] = {
                        "polygon": polygon,
                        "confidence": confidence,
                        "occupied": False  # 后续根据车辆检测结果判断
                    }
                    spot_id += 1
        
        # 判断停车位占用
        parking_spots = self._check_parking_occupancy(parking_spots, image)
        
        return parking_spots
    
    def _obb_to_polygon(self, cx, cy, w, h, angle):
        """将 OBB 转换为四角坐标"""
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        
        # 四个角的相对坐标
        corners = [
            (-w/2, -h/2),
            (w/2, -h/2),
            (w/2, h/2),
            (-w/2, h/2)
        ]
        
        # 旋转并平移
        polygon = []
        for dx, dy in corners:
            x = cx + dx * cos_a - dy * sin_a
            y = cy + dx * sin_a + dy * cos_a
            polygon.extend([x, y])
        
        return polygon
    
    def _check_parking_occupancy(self, parking_spots: Dict, image: np.ndarray) -> Dict:
        """检查停车位占用状态"""
        if not parking_spots:
            return parking_spots
        
        # 获取图像中的车辆
        vehicles = []
        for det in self._detect_yolo(image):
            if det.class_name in ["vehicle_counting", "illegal_parking", "vehicle_intrusion"]:
                vehicles.append(det.bbox)
        
        # 判断每个停车位是否被占用
        iou_threshold = self.config['parking']['occupancy']['iou_threshold']
        
        for spot_id, spot_info in parking_spots.items():
            spot_polygon = np.array(spot_info["polygon"]).reshape(-1, 2)
            spot_bbox = self._polygon_to_bbox(spot_polygon)
            
            max_iou = 0
            for vehicle_bbox in vehicles:
                iou = self._calculate_iou(spot_bbox, vehicle_bbox)
                max_iou = max(max_iou, iou)
            
            spot_info["occupied"] = max_iou > iou_threshold
            spot_info["iou"] = max_iou
        
        return parking_spots
    
    def _polygon_to_bbox(self, polygon: np.ndarray) -> List[float]:
        """多边形转边界框"""
        x_coords = polygon[:, 0]
        y_coords = polygon[:, 1]
        return [x_coords.min(), y_coords.min(), x_coords.max(), y_coords.max()]
    
    def _calculate_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """计算两个边界框的 IoU"""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _generate_alerts(self, detections: List[Detection], image: np.ndarray) -> List[Alert]:
        """生成报警"""
        alerts = []
        
        # 报警级别映射
        alert_levels = {
            "critical": self.alert_config['critical']['classes'],
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
            
            if level is None:
                continue
            
            # 检查报警抑制
            if self._should_suppress_alert(det):
                continue
            
            # 生成报警
            alert = Alert(
                alert_type="security",
                class_name=det.class_name,
                message=f"检测到{self.class_names_cn.get(det.class_id, det.class_name)}",
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
        same_target_minutes = suppress_config.get('same_target_minutes', 5)
        
        # 检查同类报警时间间隔
        if detection.class_id in self.alert_history:
            last_alert_time = self.alert_history[detection.class_id]
            elapsed = (datetime.now() - last_alert_time).total_seconds() / 60
            
            if elapsed < same_target_minutes:
                return True
        
        return False
    
    def _calculate_stats(self, detections: List[Detection]) -> Dict:
        """计算统计信息"""
        stats = {
            "total_persons": 0,
            "total_vehicles": 0,
            "compliance_rate": 0.0
        }
        
        # 人员行为类别
        person_classes = [0, 1, 2, 3, 4, 5, 6, 7, 8]
        # 车辆类别
        vehicle_classes = [9, 10, 11]
        
        person_count = 0
        vehicle_count = 0
        
        for det in detections:
            if det.class_id in person_classes:
                person_count += 1
            elif det.class_id in vehicle_classes:
                vehicle_count += 1
        
        stats["total_persons"] = person_count
        stats["total_vehicles"] = vehicle_count
        
        return stats
    
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
        
        # 绘制检测结果
        for det in results["detections"]:
            x1, y1, x2, y2 = [int(v) for v in det.bbox]
            
            # 根据报警级别选择颜色
            if det.class_id in self.alert_config['critical']['classes']:
                color = (0, 0, 255)  # 红色
            elif det.class_id in self.alert_config['warning']['classes']:
                color = (0, 255, 255)  # 黄色
            else:
                color = (0, 255, 0)  # 绿色
            
            # 绘制边界框
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)
            
            # 绘制标签
            label = f"{self.class_names_cn.get(det.class_id, det.class_name)} {det.confidence:.2f}"
            cv2.putText(vis_image, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # 绘制停车位
        for spot_id, spot_info in results["parking_spots"].items():
            polygon = np.array(spot_info["polygon"]).reshape(-1, 2).astype(np.int32)
            
            # 占用: 红色, 空闲: 绿色
            color = (0, 0, 255) if spot_info["occupied"] else (0, 255, 0)
            
            cv2.polylines(vis_image, [polygon], True, color, 2)
            
            # 标注占用状态
            cx = int(np.mean(polygon[:, 0]))
            cy = int(np.mean(polygon[:, 1]))
            status = "占用" if spot_info["occupied"] else "空闲"
            cv2.putText(vis_image, status, (cx - 20, cy),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # 保存
        if output_path:
            cv2.imwrite(output_path, vis_image)
        
        return vis_image


def main():
    """测试入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="园区监测检测器")
    parser.add_argument("--config", type=str, default="configs/park_monitoring.yaml")
    parser.add_argument("--image", type=str, required=True)
    parser.add_argument("--output", type=str, default="output.jpg")
    
    args = parser.parse_args()
    
    # 初始化检测器
    detector = ParkDetector(args.config)
    
    # 加载图像
    image = cv2.imread(args.image)
    
    # 检测
    results = detector.detect(image)
    
    # 打印结果
    print(f"检测到 {len(results['detections'])} 个目标")
    print(f"停车位: {len(results['parking_spots'])} 个")
    print(f"报警: {len(results['alerts'])} 个")
    
    for alert in results['alerts']:
        print(f"  [{alert.level}] {alert.message}")
    
    # 可视化
    detector.visualize(image, results, args.output)
    print(f"结果已保存到 {args.output}")


if __name__ == "__main__":
    main()
