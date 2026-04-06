"""
水利巡检系统 - 统一检测器

功能:
1. YOLOv8 检测（11类）— 边缘侧
2. C-RADIOv4 开放词汇分割（5类）— 云端侧
3. 边缘+云端协同

作者: 空中智能体团队
日期: 2026-04-01
"""

import cv2
import torch
import yaml
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """检测结果"""
    class_id: int
    class_name: str
    class_name_cn: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    bbox_type: str = "hbb"


@dataclass
class Segment:
    """分割结果"""
    class_name: str
    class_name_cn: str
    mask: np.ndarray
    area_ratio: float
    score: float


@dataclass
class Alert:
    """报警信息"""
    alert_type: str
    class_name: str
    message: str
    level: str
    timestamp: str
    bbox: Optional[List[float]] = None
    area: Optional[float] = None


class WaterInspectionSystem:
    """水利巡检统一检测系统"""

    def __init__(self, config_path: str, device: str = "cuda"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.device = device

        # 加载类别映射
        self.yolo_classes = self.config['yolo']['classes']
        self.yolo_names = {k: v['name'] for k, v in self.yolo_classes.items()}
        self.yolo_names_cn = {k: v['zh'] for k, v in self.yolo_classes.items()}

        # 加载 YOLO 模型
        self.yolo_model = self._load_yolo_model()
        self.segmentor = None  # 延迟加载

        # 报警配置
        self.alert_config = self.config['deployment']['alerts']

        # 报警历史 (抑制重复报警)
        self.alert_history = {}

        # 云端配置
        self.cloud_enabled = self.config['deployment']['cloud']['enabled']
        self.upload_interval = self.config['deployment']['cloud']['upload_interval']

    def _load_yolo_model(self):
        """加载 YOLOv8-Pose 模型"""
        try:
            from ultralytics import YOLO

            weights_path = self.config['yolo']['model']['weights']

            if weights_path.endswith('.engine'):
                return self._load_tensorrt_model(weights_path)
            else:
                return YOLO(weights_path)
        except Exception as e:
            logger.error("加载 YOLO 模型失败: %s", e)
            return None

    def _load_tensorrt_model(self, engine_path):
        """加载 TensorRT 模型"""
        try:
            import tensorrt as trt

            logger_obj = trt.Logger(trt.Logger.INFO)
            with open(engine_path, 'rb') as f:
                runtime = trt.Runtime(logger_obj)
                engine = runtime.deserialize_cuda_engine(f.read())

            return {'engine': engine, 'context': engine.create_execution_context()}
        except Exception as e:
            logger.error("加载 TensorRT 模型失败: %s", e)
            return None

    def _load_segmentor(self):
        """加载 C-RADIOv4 开放词汇分割器（延迟加载）"""
        if self.segmentor is not None:
            return

        try:
            from models.open_vocab.inference import OpenVocabSegmentor

            # 兼容新旧配置格式
            radio_config = (
                self.config.get("cloud", {}).get("radio")
                or self.config.get("dinov3_sam3", {})
            )

            self.segmentor = OpenVocabSegmentor(
                config=radio_config,
                device=self.device,
            )
            logger.info("C-RADIOv4 分割器加载完成")

        except Exception as e:
            logger.warning("C-RADIOv4 分割器加载失败: %s", e)
            self.segmentor = None

    def detect(self, image: np.ndarray, frame_id: int = 0) -> Dict[str, Any]:
        """
        统一检测接口

        Args:
            image: BGR 图像
            frame_id: 帧 ID（用于云端推理频率控制）

        Returns:
            {"detections": [...], "segments": {...}, "alerts": [...], "stats": {...}}
        """
        results = {
            "detections": [],
            "segments": {},
            "alerts": [],
            "stats": {
                "person_behavior": 0,
                "facilities": 0,
                "targets": 0,
                "water_quality": 0,
            }
        }

        # 1. YOLOv8 检测（每帧）
        yolo_detections = self._detect_yolo(image)
        results["detections"] = yolo_detections

        # 2. C-RADIOv4 分割（每N帧）
        should_segment = self._should_run_segmentation(frame_id, yolo_detections)

        if should_segment:
            segments = self._segment_water_quality(image)
            results["segments"] = segments

        # 3. 生成报警
        alerts = self._generate_alerts(yolo_detections, results["segments"])
        results["alerts"] = alerts

        # 4. 统计
        results["stats"] = self._calculate_stats(yolo_detections, results["segments"])

        return results

    def _detect_yolo(self, image: np.ndarray) -> List[Detection]:
        """YOLOv8-Pose 检测"""
        detections = []

        if self.yolo_model is None:
            return detections

        inference_config = self.config['yolo']['inference']

        if isinstance(self.yolo_model, dict):
            results_list = self._infer_tensorrt(image)
        else:
            results_list = self.yolo_model.predict(
                image,
                conf=inference_config['conf_threshold'],
                iou=inference_config['iou_threshold'],
                device=self.device,
                verbose=False
            )

        for result in results_list:
            for box in result.boxes:
                class_id = int(box.cls)
                confidence = float(box.conf)
                bbox = box.xyxy.tolist()[0]

                detection = Detection(
                    class_id=class_id,
                    class_name=self.yolo_names.get(class_id, f"class_{class_id}"),
                    class_name_cn=self.yolo_names_cn.get(class_id, f"类别{class_id}"),
                    confidence=confidence,
                    bbox=bbox
                )
                detections.append(detection)

        return detections

    def _should_run_segmentation(self, frame_id: int, detections: List[Detection]) -> bool:
        """判断是否需要运行分割"""
        if frame_id % self.upload_interval == 0:
            return True

        alert_classes = self.alert_config['facility'] + self.alert_config['water_quality']

        # water_quality 是类别名列表，转为 class_id 不太合理，此处按 class_name 判断
        alert_names = set(self.alert_config.get('person_behavior', [])
                        + self.alert_config.get('facility', [])
                        + self.alert_config.get('water_quality', []))

        for det in detections:
            if det.class_name in alert_names:
                return True

        return False

    def _segment_water_quality(self, image: np.ndarray) -> Dict[str, Segment]:
        """水质分割 (C-RADIOv4)"""
        segments = {}

        if self.segmentor is None:
            self._load_segmentor()

        if self.segmentor is None:
            return segments

        try:
            results = self.segmentor.segment(image)
        except Exception as e:
            logger.error("分割失败: %s", e)
            return segments

        for class_name, info in results.items():
            segment = Segment(
                class_name=class_name,
                class_name_cn=info.get("class_name_cn", class_name),
                mask=info["mask"],
                area_ratio=info["area"],
                score=info["score"],
            )
            segments[class_name] = segment

        return segments

    def _generate_alerts(
        self,
        detections: List[Detection],
        segments: Dict[str, Segment]
    ) -> List[Alert]:
        """生成报警"""
        alerts = []

        # 检测报警
        alert_names = set(
            self.alert_config.get('person_behavior', [])
            + self.alert_config.get('facility', [])
        )

        for det in detections:
            if det.class_name in alert_names:
                if self._should_suppress_alert(det):
                    continue

                alert = Alert(
                    alert_type="detection",
                    class_name=det.class_name,
                    message=f"检测到{det.class_name_cn}",
                    level="critical",
                    timestamp=datetime.now().isoformat(),
                    bbox=det.bbox
                )
                alerts.append(alert)
                self._record_alert(det)

        # 分割报警
        min_area = self.alert_config.get('min_area', 0.01)

        for class_name, segment in segments.items():
            if segment.area_ratio >= min_area:
                alert = Alert(
                    alert_type="segmentation",
                    class_name=class_name,
                    message=f"检测到{segment.class_name_cn}，面积占比: {segment.area_ratio:.1%}",
                    level="critical",
                    timestamp=datetime.now().isoformat(),
                    area=segment.area_ratio
                )
                alerts.append(alert)

        return alerts

    def _should_suppress_alert(self, detection: Detection) -> bool:
        """检查是否应该抑制报警 (5分钟内不重复)"""
        suppress_minutes = 5
        alert_key = f"{detection.class_id}_{int(detection.bbox[0]/50)}_{int(detection.bbox[1]/50)}"

        if alert_key in self.alert_history:
            last_time = self.alert_history[alert_key]
            elapsed = (datetime.now() - last_time).total_seconds() / 60

            if elapsed < suppress_minutes:
                return True

        return False

    def _record_alert(self, detection: Detection):
        """记录报警"""
        alert_key = f"{detection.class_id}_{int(detection.bbox[0]/50)}_{int(detection.bbox[1]/50)}"
        self.alert_history[alert_key] = datetime.now()

    def _calculate_stats(
        self,
        detections: List[Detection],
        segments: Dict[str, Segment]
    ) -> Dict:
        """计算统计信息"""
        stats = {
            "person_behavior": 0,
            "facilities": 0,
            "targets": 0,
            "water_quality": len(segments)
        }

        person_behavior_ids = [0, 1, 2, 3, 4]
        facilities_ids = [5, 6, 7, 8, 9]
        targets_ids = [9, 10]

        for det in detections:
            if det.class_id in person_behavior_ids:
                stats["person_behavior"] += 1
            elif det.class_id in facilities_ids:
                stats["facilities"] += 1
            elif det.class_id in targets_ids:
                stats["targets"] += 1

        return stats

    def visualize(
        self,
        image: np.ndarray,
        results: Dict,
        output_path: Optional[str] = None
    ) -> np.ndarray:
        """可视化检测结果"""
        vis_image = image.copy()

        # 绘制检测结果
        for det in results["detections"]:
            x1, y1, x2, y2 = [int(v) for v in det.bbox]

            if det.class_id in [1, 2, 3, 4]:
                color = (0, 0, 255)
            elif det.class_id in [7, 8]:
                color = (0, 165, 255)
            else:
                color = (0, 255, 0)

            cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)
            label = f"{det.class_name_cn} {det.confidence:.2f}"
            cv2.putText(vis_image, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 绘制分割结果
        colors = {
            "black_water": (0, 0, 0),
            "green_water": (0, 255, 0),
            "red_water": (0, 0, 255),
            "milky_water": (200, 200, 200),
            "dam_seepage": (100, 100, 100)
        }

        for class_name, segment in results["segments"].items():
            mask = segment.mask.astype(np.uint8) * 255
            color = colors.get(class_name, (128, 128, 128))

            colored_mask = np.zeros_like(vis_image)
            colored_mask[mask > 0] = color
            vis_image = cv2.addWeighted(vis_image, 0.7, colored_mask, 0.3, 0)

            label = f"{segment.class_name_cn} {segment.area_ratio:.1%}"
            y, x = np.where(mask > 0)
            if len(y) > 0:
                cy, cx = int(y.mean()), int(x.mean())
                cv2.putText(vis_image, label, (cx - 50, cy),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if output_path:
            cv2.imwrite(output_path, vis_image)

        return vis_image


def main():
    """测试入口"""
    import argparse

    parser = argparse.ArgumentParser(description="水利巡检系统")
    parser.add_argument("--config", type=str, default="configs/water_inspection.yaml")
    parser.add_argument("--image", type=str, required=True)
    parser.add_argument("--output", type=str, default="output.jpg")

    args = parser.parse_args()

    system = WaterInspectionSystem(args.config)
    image = cv2.imread(args.image)
    results = system.detect(image)

    print(f"检测到 {len(results['detections'])} 个目标")
    print(f"分割: {len(results['segments'])} 个区域")
    print(f"报警: {len(results['alerts'])} 个")

    for alert in results['alerts']:
        print(f"  [{alert.level}] {alert.message}")

    system.visualize(image, results, args.output)
    print(f"结果已保存到 {args.output}")


if __name__ == "__main__":
    main()
