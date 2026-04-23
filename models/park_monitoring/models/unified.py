#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
园区监测统一检测系统 v2.0

整合:
  1. YOLOv8-Pose 目标检测 (12类) - 边缘侧
  2. YOLOv8-Obb 停车位检测 (1类) - 边缘侧
  3. C-RADIOv4 零样本场景检测 (3类) - 云端侧

新增 RADIO 零样本检测:
  - 消防通道堵塞 (fire_lane_blocked)
  - 翻越栏杆围墙 (fence_climbing)
  - 安全出口堵塞 (exit_blocked)

作者: 空中智能体团队
日期: 2026-04-21
"""

import sys
import cv2
import yaml
import logging
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==============================================================================
# 数据类定义
# ==============================================================================

@dataclass
class Detection:
    """YOLO 检测结果"""
    class_id: int
    class_name: str
    confidence: float
    bbox: List[float]
    bbox_type: str = "hbb"


@dataclass
class RadioDetection:
    """RADIO 零样本检测结果"""
    class_name: str
    class_name_cn: str
    confidence: float
    area_ratio: float
    mask: Optional[np.ndarray] = None
    color: Tuple[int, int, int] = (0, 255, 0)


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


# ==============================================================================
# RADIO 零样本检测类别
# ==============================================================================

RADIO_CLASSES = {
    "fire_lane_blocked": {
        "zh": "消防通道堵塞", "color": (0, 0, 255), "alert": True, "level": "critical"
    },
    "fence_climbing": {
        "zh": "翻越栏杆围墙", "color": (0, 100, 255), "alert": True, "level": "critical"
    },
    "exit_blocked": {
        "zh": "安全出口堵塞", "color": (0, 200, 255), "alert": True, "level": "critical"
    },
}

BACKGROUND_CLASSES = {"background"}


# ==============================================================================
# RADIO 零样本检测流水线
# ==============================================================================

class RadioParkPipeline:
    """
    园区场景 RADIO 零样本检测流水线

    复用 C-RADIOv4 + SigLIP2-g 语义分割能力,
    通过文本提示实现消防通道堵塞/翻越栏杆/安全出口堵塞的零样本检测。

    核心能力: 组合推理 (标识+障碍物 / 栏杆+人 / 出口+堵塞)
    """

    def __init__(self, config: Dict):
        self.config = config
        model_cfg = config['cloud']['radio']['model']
        infer_cfg = config['cloud']['radio']['inference']

        self.checkpoint_path = model_cfg['path']
        self.radio_code_dir = model_cfg['radio_code_dir']
        self.siglip2_dir = model_cfg['siglip2_dir']
        self.input_size = infer_cfg.get('input_size', 896)
        self.threshold = infer_cfg.get('threshold', 0.25)
        self.min_area = infer_cfg.get('min_area', 0.003)

        self.classes_config = config['cloud']['radio']['classes']
        self._segmentor = None

        logger.info("园区场景 RADIO 流水线初始化完成")
        logger.info(f"  检测类别: {[k for k in self.classes_config if k not in BACKGROUND_CLASSES]}")

    def _load_segmentor(self):
        if self._segmentor is not None:
            return

        logger.info("加载 C-RADIOv4 分割器 (园区场景)...")
        water_model_dir = Path(__file__).parent.parent.parent / "water_inspection" / "models"
        if str(water_model_dir) not in sys.path:
            sys.path.insert(0, str(water_model_dir))

        from open_vocab.radseg_segmentor import RADSegWaterSegmentor

        self._segmentor = RADSegWaterSegmentor(
            checkpoint_path=self.checkpoint_path,
            radio_code_dir=self.radio_code_dir,
            siglip2_dir=self.siglip2_dir,
            device='cuda',
            use_scra=True,
            use_dino=False,
            use_sam=False,
            temperature=50.0,
        )
        logger.info("  分割器加载完成")

    def process(self, image: np.ndarray) -> List[RadioDetection]:
        if self._segmentor is None:
            self._load_segmentor()

        h, w = image.shape[:2]
        total_pixels = h * w

        # 构建 prompts
        prompts_config = {}
        for cls_name, cls_cfg in self.classes_config.items():
            if cls_name in BACKGROUND_CLASSES:
                continue
            entry = {"prompts": cls_cfg.get("prompts", [])}
            if "prompts_negative" in cls_cfg:
                entry["negative"] = cls_cfg["prompts_negative"]
            prompts_config[cls_name] = entry

        bg_cfg = self.classes_config.get("background", {})
        if bg_cfg:
            prompts_config["background"] = {"prompts": bg_cfg.get("prompts", [])}

        heatmaps = self._segmentor.compute_patch_similarity(image, prompts_config)

        results = []
        for cls_name, cls_cfg in self.classes_config.items():
            if cls_name in BACKGROUND_CLASSES:
                continue

            heatmap = heatmaps.get(cls_name, np.zeros((h, w)))
            mask = heatmap > self.threshold
            area_ratio = mask.sum() / total_pixels

            min_prob = cls_cfg.get("min_prob", 0.25)
            mean_score = float(heatmap[mask].mean()) if mask.any() else 0.0

            if area_ratio >= self.min_area and mean_score >= min_prob:
                info = RADIO_CLASSES.get(cls_name, {})
                results.append(RadioDetection(
                    class_name=cls_name,
                    class_name_cn=info.get("zh", cls_name),
                    confidence=mean_score,
                    area_ratio=area_ratio,
                    mask=mask,
                    color=info.get("color", (0, 255, 0)),
                ))

        return results


# ==============================================================================
# 统一检测系统
# ==============================================================================

class UnifiedParkMonitoringSystem:
    """
    园区监测统一检测系统 v2.0

    整合:
      1. YOLOv8-Pose 目标检测 (边端, 12类)
      2. YOLOv8-Obb 停车位检测 (边端, 1类)
      3. C-RADIOv4 零样本场景检测 (云端, 3类)
    """

    def __init__(self, config_path: str):
        self.config_path = config_path
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.classes = self.config['yolo']['classes']
        self.class_names = {k: v['name'] for k, v in self.classes.items()}
        self.class_names_cn = {k: v['zh'] for k, v in self.classes.items()}

        self.yolo_model = None
        self.yolo_obb_model = None
        self.radio_pipeline = None
        self.alert_history: Dict[str, datetime] = {}
        self.parking_spots = {}
        self.frame_count = 0

        logger.info("园区监测统一检测系统初始化完成")

    def _load_yolo(self):
        if self.yolo_model is not None:
            return
        logger.info("加载 YOLOv8-Pose 模型...")
        try:
            from ultralytics import YOLO
            weights = self.config['yolo']['model']['weights']
            if weights.endswith('.engine'):
                self.yolo_model = self._load_tensorrt(weights)
            else:
                self.yolo_model = YOLO(weights)
            logger.info("  YOLO-Pose 加载完成")
        except Exception as e:
            logger.error(f"YOLO 加载失败: {e}")

    def _load_yolo_obb(self):
        if self.yolo_obb_model is not None:
            return
        logger.info("加载 YOLOv8-Obb 模型...")
        try:
            from ultralytics import YOLO
            weights = self.config['yolo_obb']['model']['weights']
            self.yolo_obb_model = YOLO(weights)
            logger.info("  YOLO-Obb 加载完成")
        except Exception as e:
            logger.error(f"YOLO-Obb 加载失败: {e}")

    def _load_tensorrt(self, path):
        import tensorrt as trt
        logger_obj = trt.Logger(trt.Logger.INFO)
        with open(path, 'rb') as f:
            runtime = trt.Runtime(logger_obj)
            engine = runtime.deserialize_cuda_engine(f.read())
        return {'engine': engine, 'context': engine.create_execution_context()}

    def _load_radio(self):
        if self.radio_pipeline is not None:
            return
        cloud_cfg = self.config.get('deployment', {}).get('cloud', {})
        if not cloud_cfg.get('enabled', False):
            return
        if 'radio' not in cloud_cfg:
            return
        logger.info("加载 RADIO 零样本检测流水线...")
        self.radio_pipeline = RadioParkPipeline(self.config)
        logger.info("  RADIO 流水线加载完成")

    def detect(
        self,
        image: np.ndarray,
        run_radio: bool = True,
    ) -> Dict[str, Any]:
        results = {
            "detections": [],
            "radio_detections": [],
            "parking_spots": {},
            "alerts": [],
            "stats": {"total_persons": 0, "total_vehicles": 0},
        }

        if self.yolo_model is None:
            self._load_yolo()

        # 1. YOLO 检测
        detections = self._detect_yolo(image)
        results["detections"] = detections

        # 2. 停车位检测
        if self.yolo_obb_model is None:
            self._load_yolo_obb()
        results["parking_spots"] = self._detect_parking_spots(image)

        # 3. RADIO 云端检测
        if run_radio and self._should_run_radio():
            if self.radio_pipeline is None:
                self._load_radio()
            if self.radio_pipeline is not None:
                results["radio_detections"] = self.radio_pipeline.process(image)

        # 4. 报警
        yolo_alerts = self._generate_alerts(detections)
        radio_alerts = self._generate_radio_alerts(results["radio_detections"])
        results["alerts"] = yolo_alerts + radio_alerts

        # 5. 统计
        results["stats"] = self._calculate_stats(detections)

        self.frame_count += 1
        return results

    def _should_run_radio(self) -> bool:
        frame_interval = self.config.get('deployment', {}).get('cloud', {}).get('frame_interval', 30)
        if self.frame_count % frame_interval == 0:
            return True
        return False

    def _detect_yolo(self, image):
        detections = []
        if self.yolo_model is None:
            return detections
        try:
            infer_cfg = self.config['yolo']['inference']
            if isinstance(self.yolo_model, dict):
                pass
            else:
                results_list = self.yolo_model.predict(
                    image,
                    conf=infer_cfg['conf_threshold'],
                    iou=infer_cfg['iou_threshold'],
                    device=self.config['yolo']['inference']['device'],
                    verbose=False,
                )
                for result in results_list:
                    for box in result.boxes:
                        detections.append(Detection(
                            class_id=int(box.cls),
                            class_name=self.class_names.get(int(box.cls), f"class_{int(box.cls)}"),
                            confidence=float(box.conf),
                            bbox=box.xyxy.tolist()[0],
                            bbox_type="hbb",
                        ))
        except Exception as e:
            logger.error(f"YOLO 检测失败: {e}")
        return detections

    def _detect_parking_spots(self, image):
        spots = {}
        if self.yolo_obb_model is None:
            return spots
        try:
            infer_cfg = self.config['yolo_obb']['inference']
            results_list = self.yolo_obb_model.predict(
                image, conf=infer_cfg['conf_threshold'],
                iou=infer_cfg['iou_threshold'], verbose=False,
            )
            spot_id = 0
            for result in results_list:
                if hasattr(result, 'obb') and result.obb is not None:
                    for obb in result.obb:
                        if hasattr(obb, 'xyxyxyxy'):
                            polygon = obb.xyxyxyxy.tolist()[0]
                        else:
                            cx, cy, w, h, angle = obb.xywhr.tolist()[0]
                            polygon = self._obb_to_polygon(cx, cy, w, h, angle)
                        spots[spot_id] = {
                            "polygon": polygon,
                            "confidence": float(obb.conf),
                            "occupied": False,
                        }
                        spot_id += 1
        except Exception as e:
            logger.error(f"停车位检测失败: {e}")
        return spots

    def _obb_to_polygon(self, cx, cy, w, h, angle):
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        corners = [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)]
        polygon = []
        for dx, dy in corners:
            polygon.extend([cx + dx*cos_a - dy*sin_a, cy + dx*sin_a + dy*cos_a])
        return polygon

    def _generate_alerts(self, detections):
        alerts = []
        alert_cfg = self.config.get('alerts', {})
        alert_levels = {
            "critical": alert_cfg.get('critical', {}).get('classes', []),
            "warning": alert_cfg.get('warning', {}).get('classes', []),
            "info": alert_cfg.get('info', {}).get('classes', []),
        }
        for det in detections:
            level = None
            for lvl, class_ids in alert_levels.items():
                if det.class_id in class_ids:
                    level = lvl
                    break
            if level is None:
                continue
            key = f"security_{det.class_name}"
            if key in self.alert_history:
                if (datetime.now() - self.alert_history[key]).total_seconds() < 300:
                    continue
            alerts.append(Alert(
                alert_type="security",
                class_name=det.class_name,
                message=f"检测到{self.class_names_cn.get(det.class_id, det.class_name)}",
                level=level,
                timestamp=datetime.now().isoformat(),
                bbox=det.bbox,
            ))
            self.alert_history[key] = datetime.now()
        return alerts

    def _generate_radio_alerts(self, radio_detections):
        alerts = []
        for rd in radio_detections:
            info = RADIO_CLASSES.get(rd.class_name, {})
            level = info.get("level", "critical")
            key = f"radio_{rd.class_name}"
            if key in self.alert_history:
                if (datetime.now() - self.alert_history[key]).total_seconds() < 300:
                    continue
            alerts.append(Alert(
                alert_type="radio_scene",
                class_name=rd.class_name,
                message=f"检测到{rd.class_name_cn} (面积: {rd.area_ratio:.1%})",
                level=level,
                timestamp=datetime.now().isoformat(),
                area=rd.area_ratio,
            ))
            self.alert_history[key] = datetime.now()
        return alerts

    def _calculate_stats(self, detections):
        person_count = sum(1 for d in detections if d.class_id in range(9))
        vehicle_count = sum(1 for d in detections if d.class_id in [9, 10, 11])
        return {"total_persons": person_count, "total_vehicles": vehicle_count}

    def visualize(self, image, results, output_path=None):
        vis = image.copy()

        # YOLO 检测
        for det in results["detections"]:
            x1, y1, x2, y2 = [int(v) for v in det.bbox]
            alert_cfg = self.config.get('alerts', {})
            if det.class_id in alert_cfg.get('critical', {}).get('classes', []):
                color = (0, 0, 255)
            elif det.class_id in alert_cfg.get('warning', {}).get('classes', []):
                color = (0, 255, 255)
            else:
                color = (0, 255, 0)
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            label = f"{self.class_names_cn.get(det.class_id, det.class_name)} {det.confidence:.2f}"
            cv2.putText(vis, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 停车位
        for spot_id, spot_info in results["parking_spots"].items():
            polygon = np.array(spot_info["polygon"]).reshape(-1, 2).astype(np.int32)
            color = (0, 0, 255) if spot_info["occupied"] else (0, 255, 0)
            cv2.polylines(vis, [polygon], True, color, 2)

        # RADIO 零样本检测 (半透明掩码)
        for rd in results["radio_detections"]:
            if rd.mask is not None and rd.mask.any():
                overlay = vis.copy()
                overlay[rd.mask] = rd.color
                vis = cv2.addWeighted(vis, 0.7, overlay, 0.3, 0)
                ys, xs = np.where(rd.mask)
                if len(ys) > 0:
                    cy, cx = int(ys.mean()), int(xs.mean())
                    label = f"{rd.class_name_cn} {rd.confidence:.2f} ({rd.area_ratio:.1%})"
                    cv2.putText(vis, label, (max(0, cx-80), max(15, cy-10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, rd.color, 2)

        if output_path:
            cv2.imwrite(output_path, vis)
        return vis


# ==============================================================================
# 便捷 API
# ==============================================================================

def create_system(config_path: str = "configs/park_monitoring.yaml"):
    return UnifiedParkMonitoringSystem(config_path)


def detect_single_image(
    image_path: str,
    config_path: str = "configs/park_monitoring.yaml",
    output_path: Optional[str] = None,
    run_radio: bool = True,
) -> Dict:
    system = create_system(config_path)
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"无法加载图像: {image_path}")
    results = system.detect(image, run_radio=run_radio)
    if output_path:
        system.visualize(image, results, output_path)
    return results


# ==============================================================================
# 主程序
# ==============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="园区监测统一检测系统 v2.0")
    parser.add_argument("--config", default="configs/park_monitoring.yaml")
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", default="output.jpg")
    parser.add_argument("--no-radio", action="store_true", help="不运行 RADIO 云端检测")

    args = parser.parse_args()
    system = create_system(args.config)
    image = cv2.imread(args.image)
    if image is None:
        logger.error(f"无法加载图像: {args.image}")
        sys.exit(1)

    results = system.detect(image, run_radio=not args.no_radio)

    print(f"\n检测结果:")
    print(f"  YOLO 检测: {len(results['detections'])} 个")
    for det in results['detections']:
        print(f"    - {det.class_name}: {det.confidence:.2f}")

    if results['radio_detections']:
        print(f"\n  RADIO 零样本检测: {len(results['radio_detections'])} 个")
        for rd in results['radio_detections']:
            print(f"    - {rd.class_name_cn}: {rd.confidence:.2f} (面积: {rd.area_ratio:.1%})")

    if results['parking_spots']:
        occupied = sum(1 for s in results['parking_spots'].values() if s.get('occupied'))
        print(f"\n  停车位: {len(results['parking_spots'])} 个, 占用 {occupied} 个")

    print(f"\n  报警: {len(results['alerts'])} 个")
    for alert in results['alerts']:
        print(f"    - [{alert.level}] {alert.message}")

    system.visualize(image, results, args.output)
    print(f"\n结果已保存到: {args.output}")
