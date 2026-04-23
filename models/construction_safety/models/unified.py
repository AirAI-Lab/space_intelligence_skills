#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
施工安全监测统一检测系统 v2.0

整合:
  1. YOLOv8-Pose 目标检测 (15类) - 边缘侧
  2. C-RADIOv4 零样本场景检测 (4类) - 云端侧
  3. 云边协同: 定期/事件触发 RADIO 分割

新增 RADIO 零样本检测:
  - 裸土未覆盖 (bare_soil_uncovered)
  - 扬尘污染 (dust_pollution)
  - 坑内积水 (pit_water_accumulation)
  - 基坑边材料堆放 (material_near_pit)

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
from dataclasses import dataclass, field

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
    class_name_cn: str
    confidence: float
    bbox: List[float]
    keypoints: Optional[List[Tuple[float, float]]] = None


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


@dataclass
class Compliance:
    """合规统计"""
    total_persons: int
    persons_with_helmet: int
    persons_with_vest: int
    helmet_rate: float
    vest_rate: float


# ==============================================================================
# RADIO 零样本检测类别
# ==============================================================================

RADIO_CLASSES = {
    "bare_soil_uncovered": {
        "zh": "裸土未覆盖", "color": (0, 200, 200), "alert": True, "level": "warning"
    },
    "dust_pollution": {
        "zh": "扬尘污染", "color": (200, 200, 0), "alert": True, "level": "warning"
    },
    "pit_water_accumulation": {
        "zh": "坑内积水", "color": (200, 100, 0), "alert": True, "level": "info"
    },
    "material_near_pit": {
        "zh": "基坑边材料堆放", "color": (0, 100, 255), "alert": True, "level": "warning"
    },
}

# 排除背景类
BACKGROUND_CLASSES = {"background"}


# ==============================================================================
# RADIO 零样本检测流水线
# ==============================================================================

class RadioConstructionPipeline:
    """
    施工场景 RADIO 零样本检测流水线

    复用 C-RADIOv4 + SigLIP2-g 语义分割能力,
    通过文本提示实现裸土/扬尘/积水/材料堆放的零样本检测。
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

        # 从配置加载类别提示词
        self.classes_config = config['cloud']['radio']['classes']

        # 延迟加载
        self._segmentor = None

        logger.info("施工场景 RADIO 流水线初始化完成")
        logger.info(f"  检测类别: {[k for k in self.classes_config if k not in BACKGROUND_CLASSES]}")

    def _load_segmentor(self):
        """延迟加载 RADIO 分割器"""
        if self._segmentor is not None:
            return

        logger.info("加载 C-RADIOv4 分割器 (施工场景)...")
        # 导入路径指向 water_inspection 下的共享模块
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
        """
        处理单张图像, 返回检测到的场景异常

        Args:
            image: BGR 图像

        Returns:
            List[RadioDetection]: 检测到的异常列表
        """
        if self._segmentor is None:
            self._load_segmentor()

        h, w = image.shape[:2]
        total_pixels = h * w

        # 构建 prompts 配置 (正面 + 负面)
        prompts_config = {}
        for cls_name, cls_cfg in self.classes_config.items():
            if cls_name in BACKGROUND_CLASSES:
                continue
            entry = {"prompts": cls_cfg.get("prompts", [])}
            if "prompts_negative" in cls_cfg:
                entry["negative"] = cls_cfg["prompts_negative"]
            prompts_config[cls_name] = entry

        # 添加背景类用于对比
        bg_cfg = self.classes_config.get("background", {})
        if bg_cfg:
            prompts_config["background"] = {"prompts": bg_cfg.get("prompts", [])}

        # 计算 patch 级别相似度
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

class UnifiedConstructionSafetySystem:
    """
    施工安全统一检测系统 v2.0

    整合:
      1. YOLOv8-Pose 目标检测 (边端, 15类)
      2. C-RADIOv4 零样本场景检测 (云端, 4类)

    云边协同:
      - 边端实时检测人员/装备/机械
      - 云端零样本检测裸土/扬尘/积水/材料堆放
    """

    def __init__(self, config_path: str):
        self.config_path = config_path
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.classes = self.config['yolo']['classes']
        self.class_names = {k: v['name'] for k, v in self.classes.items()}
        self.class_names_cn = {k: v['zh'] for k, v in self.classes.items()}

        # 延迟加载
        self.yolo_model = None
        self.radio_pipeline = None
        self.alert_history: Dict[str, datetime] = {}
        self.frame_count = 0

        logger.info("施工安全统一检测系统初始化完成")

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
            logger.info("  YOLO 加载完成")
        except Exception as e:
            logger.error(f"YOLO 加载失败: {e}")

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
        self.radio_pipeline = RadioConstructionPipeline(self.config)
        logger.info("  RADIO 流水线加载完成")

    def detect(
        self,
        image: np.ndarray,
        run_radio: bool = True,
    ) -> Dict[str, Any]:
        """
        统一检测接口

        Args:
            image: BGR 图像
            run_radio: 是否运行 RADIO 云端检测

        Returns:
            dict: {
                "detections": List[Detection],
                "radio_detections": List[RadioDetection],
                "compliance": Compliance,
                "alerts": List[Alert],
                "danger_zones": List,
                "machinery": List,
            }
        """
        results = {
            "detections": [],
            "radio_detections": [],
            "compliance": None,
            "alerts": [],
            "danger_zones": [],
            "machinery": [],
        }

        if self.yolo_model is None:
            self._load_yolo()

        # 1. YOLO 检测
        detections = self._detect_yolo(image)
        results["detections"] = detections

        # 2. 机械跟踪
        machinery = self._track_machinery(detections)
        results["machinery"] = machinery

        # 3. 危险区域检查
        danger_alerts = self._check_danger_zones(detections, machinery)

        # 4. 行为报警
        behavior_alerts = self._generate_alerts(detections)

        # 5. RADIO 云端检测
        radio_detections = []
        if run_radio and self._should_run_radio(detections):
            if self.radio_pipeline is None:
                self._load_radio()
            if self.radio_pipeline is not None:
                radio_detections = self.radio_pipeline.process(image)
                results["radio_detections"] = radio_detections

        # 6. 合并报警
        radio_alerts = self._generate_radio_alerts(radio_detections)
        results["alerts"] = danger_alerts + behavior_alerts + radio_alerts

        # 7. 合规率
        results["compliance"] = self._calculate_compliance(detections)

        self.frame_count += 1
        return results

    def _should_run_radio(self, detections: List[Detection]) -> bool:
        """判断是否触发 RADIO 检测"""
        # 定期检测 (每 30 帧)
        frame_interval = self.config.get('deployment', {}).get('cloud', {}).get('frame_interval', 30)
        if self.frame_count % frame_interval == 0:
            return True
        return False

    def _detect_yolo(self, image: np.ndarray) -> List[Detection]:
        detections = []
        if self.yolo_model is None:
            return detections
        try:
            infer_cfg = self.config['yolo']['inference']
            if isinstance(self.yolo_model, dict):
                pass  # TensorRT
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
                        class_id = int(box.cls)
                        confidence = float(box.conf)
                        bbox = box.xyxy.tolist()[0]
                        keypoints = None
                        if hasattr(result, 'keypoints') and result.keypoints is not None:
                            if len(result.keypoints) > 0:
                                kps = result.keypoints[0].data.tolist()
                                if kps:
                                    keypoints = [(kp[0], kp[1]) for kp in kps[0]]
                        detections.append(Detection(
                            class_id=class_id,
                            class_name=self.class_names.get(class_id, f"class_{class_id}"),
                            class_name_cn=self.class_names_cn.get(class_id, f"类别{class_id}"),
                            confidence=confidence,
                            bbox=bbox,
                            keypoints=keypoints,
                        ))
        except Exception as e:
            logger.error(f"YOLO 检测失败: {e}")
        return detections

    def _track_machinery(self, detections: List[Detection]) -> List[Dict]:
        machinery_classes = [12, 13, 14]
        machinery_list = []
        for det in detections:
            if det.class_id in machinery_classes:
                x1, y1, x2, y2 = det.bbox
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                machinery_list.append({
                    "class_id": det.class_id,
                    "class_name": det.class_name,
                    "class_name_cn": det.class_name_cn,
                    "position": (cx, cy),
                    "bbox": det.bbox,
                    "confidence": det.confidence,
                })
        return machinery_list

    def _check_danger_zones(self, detections, machinery):
        alerts = []
        danger_cfg = self.config.get('danger_zones', {})
        static_zones = danger_cfg.get('static', {})
        for zone_id, zone_info in static_zones.items():
            polygon = np.array(zone_info['points'])
            for det in detections:
                if det.class_id in [0, 1, 2, 3]:
                    center = ((det.bbox[0]+det.bbox[2])/2, (det.bbox[1]+det.bbox[3])/2)
                    if self._point_in_polygon(center, polygon):
                        alerts.append(Alert(
                            alert_type="danger_zone",
                            class_name=det.class_name,
                            message=f"{zone_info['name']}: 检测到{det.class_name_cn}",
                            level="critical",
                            timestamp=datetime.now().isoformat(),
                            bbox=det.bbox,
                        ))
        return alerts

    def _point_in_polygon(self, point, polygon):
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

    def _generate_alerts(self, detections):
        alerts = []
        alert_cfg = self.config.get('alerts', {})
        alert_levels = {
            "critical": alert_cfg.get('critical', {}).get('classes', []),
            "serious": alert_cfg.get('serious', {}).get('classes', []),
            "warning": alert_cfg.get('warning', {}).get('classes', []),
        }
        for det in detections:
            level = None
            for lvl, class_ids in alert_levels.items():
                if det.class_id in class_ids:
                    level = lvl
                    break
            if level is None:
                continue
            key = f"safety_{det.class_name}"
            if key in self.alert_history:
                if (datetime.now() - self.alert_history[key]).total_seconds() < 180:
                    continue
            alerts.append(Alert(
                alert_type="safety",
                class_name=det.class_name,
                message=f"检测到{det.class_name_cn}",
                level=level,
                timestamp=datetime.now().isoformat(),
                bbox=det.bbox,
            ))
            self.alert_history[key] = datetime.now()
        return alerts

    def _generate_radio_alerts(self, radio_detections: List[RadioDetection]) -> List[Alert]:
        alerts = []
        for rd in radio_detections:
            info = RADIO_CLASSES.get(rd.class_name, {})
            level = info.get("level", "warning")
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

    def _calculate_compliance(self, detections):
        persons_with_helmet = 0
        persons_with_vest = 0
        total_persons = 0
        for det in detections:
            if det.class_id == 0:
                persons_with_helmet += 1
                total_persons += 1
            elif det.class_id == 1:
                total_persons += 1
            if det.class_id == 2:
                persons_with_vest += 1
            elif det.class_id == 3:
                if det.class_id not in [0, 1]:
                    total_persons += 1
        return Compliance(
            total_persons=total_persons,
            persons_with_helmet=persons_with_helmet,
            persons_with_vest=persons_with_vest,
            helmet_rate=persons_with_helmet / total_persons if total_persons > 0 else 1.0,
            vest_rate=persons_with_vest / total_persons if total_persons > 0 else 1.0,
        )

    def visualize(self, image: np.ndarray, results: Dict, output_path: Optional[str] = None):
        vis = image.copy()
        h, w = vis.shape[:2]

        # 绘制危险区域
        for zone_id, zone_info in self.config.get('danger_zones', {}).get('static', {}).items():
            polygon = np.array(zone_info['points']).astype(np.int32)
            color = (0, 0, 200) if zone_info.get('level') == 'critical' else (0, 200, 200)
            cv2.polylines(vis, [polygon], True, color, 2)

        # 绘制 YOLO 检测
        for det in results["detections"]:
            x1, y1, x2, y2 = [int(v) for v in det.bbox]
            color = (0, 0, 255) if det.class_id in [1, 3, 4, 6, 7, 8, 9, 10, 11] else (0, 255, 0)
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            label = f"{det.class_name_cn} {det.confidence:.2f}"
            cv2.putText(vis, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 绘制 RADIO 零样本检测结果 (半透明掩码)
        for rd in results["radio_detections"]:
            if rd.mask is not None and rd.mask.any():
                overlay = vis.copy()
                overlay[rd.mask] = rd.color
                vis = cv2.addWeighted(vis, 0.7, overlay, 0.3, 0)
                # 标注
                ys, xs = np.where(rd.mask)
                if len(ys) > 0:
                    cy, cx = int(ys.mean()), int(xs.mean())
                    label = f"{rd.class_name_cn} {rd.confidence:.2f} ({rd.area_ratio:.1%})"
                    cv2.putText(vis, label, (max(0, cx-80), max(15, cy-10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, rd.color, 2)

        # 合规率
        if results["compliance"]:
            c = results["compliance"]
            lines = [f"Persons: {c.total_persons}", f"Helmet: {c.helmet_rate:.1%}", f"Vest: {c.vest_rate:.1%}"]
            for i, text in enumerate(lines):
                cv2.putText(vis, text, (10, 30+i*25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        if output_path:
            cv2.imwrite(output_path, vis)
        return vis


# ==============================================================================
# 便捷 API
# ==============================================================================

def create_system(config_path: str = "configs/construction_safety.yaml"):
    return UnifiedConstructionSafetySystem(config_path)


def detect_single_image(
    image_path: str,
    config_path: str = "configs/construction_safety.yaml",
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

    parser = argparse.ArgumentParser(description="施工安全统一检测系统 v2.0")
    parser.add_argument("--config", default="configs/construction_safety.yaml")
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
        print(f"    - {det.class_name_cn}: {det.confidence:.2f}")

    if results['radio_detections']:
        print(f"\n  RADIO 零样本检测: {len(results['radio_detections'])} 个")
        for rd in results['radio_detections']:
            print(f"    - {rd.class_name_cn}: {rd.confidence:.2f} (面积: {rd.area_ratio:.1%})")

    if results['compliance']:
        c = results['compliance']
        print(f"\n  合规率: 安全帽 {c.helmet_rate:.1%}, 反光衣 {c.vest_rate:.1%}")

    print(f"\n  报警: {len(results['alerts'])} 个")
    for alert in results['alerts']:
        print(f"    - [{alert.level}] {alert.message}")

    system.visualize(image, results, args.output)
    print(f"\n结果已保存到: {args.output}")
