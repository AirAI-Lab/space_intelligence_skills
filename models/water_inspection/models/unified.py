#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水利巡检统一检测系统 v3.4

整合:
  1. YOLOv8 目标检测 (11类) - 边缘侧
  2. C-RADIOv4 水质分类 + 坝体渗水检测 (v8 流水线) - 云端侧
  3. 云边协同: YOLO 检测触发 RADIO 分割

核心特性:
  - 开箱即用: 简单 API，统一配置文件
  - dam>water 约束: 智能坝体渗水检测
  - 多标签分类: 单图多异常类型

作者: 空中智能体团队
日期: 2026-04-07
"""

import sys
import cv2
import pickle
import yaml
import logging
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
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
    bbox: List[float]  # [x1, y1, x2, y2]


@dataclass
class WaterQualityResult:
    """水质检测结果"""
    detected_classes: List[str]
    detected_classes_cn: List[str]
    water_mask: Optional[np.ndarray] = None
    dam_mask: Optional[np.ndarray] = None
    seepage_mask: Optional[np.ndarray] = None
    has_seepage: bool = False
    confidence: Dict[str, float] = field(default_factory=dict)
    area_ratios: Dict[str, float] = field(default_factory=dict)


@dataclass
class Alert:
    """报警信息"""
    alert_type: str  # "detection" or "water_quality"
    class_name: str
    message: str
    level: str  # "info", "warning", "critical"
    timestamp: str
    bbox: Optional[List[float]] = None
    area: Optional[float] = None


# ==============================================================================
# 类别定义
# ==============================================================================

# YOLO 检测类别 (11类)
YOLO_CLASSES = {
    0: {"name": "person", "zh": "人员", "weight": 1.0},
    1: {"name": "fishing_person", "zh": "钓鱼", "weight": 2.0, "alert": True},
    2: {"name": "swimming_person", "zh": "游泳", "weight": 2.0, "alert": True},
    3: {"name": "playing_person", "zh": "嬉水", "weight": 2.5, "alert": True},
    4: {"name": "intruding_person", "zh": "闯入", "weight": 2.5, "alert": True, "level": "critical"},
    5: {"name": "water_gauge", "zh": "水位尺", "weight": 1.5},
    6: {"name": "outlet_pipe", "zh": "排污口", "weight": 1.5},
    7: {"name": "outlet_active", "zh": "排污中", "weight": 3.0, "alert": True, "level": "warning"},
    8: {"name": "pipe_damaged", "zh": "管道破损", "weight": 5.0, "alert": True, "level": "critical"},
    9: {"name": "boat", "zh": "船舶", "weight": 1.0},
    10: {"name": "floating_debris", "zh": "漂浮物", "weight": 2.0, "alert": True},
}

# 水质类别 (7类)
WATER_QUALITY_CLASSES = {
    "black_water": {"zh": "黑水", "color": (0, 0, 200), "alert": True},
    "turbid_water": {"zh": "浑浊水", "color": (42, 100, 170), "alert": True},
    "red_water": {"zh": "红水", "color": (0, 0, 255), "alert": True},
    "green_water": {"zh": "绿水/藻类", "color": (0, 200, 0), "alert": True},
    "milky_foam_water": {"zh": "乳白水/泡沫", "color": (200, 200, 200), "alert": True},
    "dam_seepage": {"zh": "坝体渗水", "color": (0, 100, 255), "alert": True, "level": "critical"},
    "normal_water": {"zh": "正常水", "color": (200, 200, 100), "alert": False},
}

# Stage 1 提示词
DETECTION_PROMPTS = {
    "water": {
        "prompts": [
            "water surface in natural river",
            "water body in lake or reservoir",
            "flowing water in channel",
            "standing water",
            "green algae water surface",
            "turbid murky water",
            "aerial view of water body",
        ]
    },
    "dam_concrete": {
        "prompts": [
            "concrete dam structure",
            "concrete embankment wall",
            "dam surface from aerial view",
            "concrete structure near water",
            "dam wall concrete surface",
            "concrete water control structure",
        ]
    },
    "background": {
        "prompts": [
            "vegetation and trees",
            "sky and clouds",
            "buildings and houses",
            "grass and soil",
        ]
    }
}


# ==============================================================================
# v8 智能坝体渗水检测流水线
# ==============================================================================

class V8WaterQualityPipeline:
    """
    v8 水质检测流水线

    核心改进:
      - dam > water 约束: 坝体渗水检测精确率从 23% 提升到 73%
      - 多标签分类: 攣率阈值 >= 0.3 触发多标签
    """

    def __init__(self, config: Dict):
        self.config = config
        self.threshold = config.get('segmentation_threshold', 0.4)
        self.seepage_min_overlap = config.get('seepage_min_overlap', 0.005)
        self.seepage_max_ratio = config.get('seepage_max_ratio', 0.3)
        self.require_dam_gt_water = config.get('require_dam_gt_water', True)
        self.multi_label_threshold = config.get('multi_label_threshold', 0.3)

        # 娡型路径
        self.checkpoint_path = config.get('checkpoint_path', '')
        self.radio_code_dir = config.get('radio_code_dir', '')
        self.siglip2_dir = config.get('siglip2_dir', '')

        # 延迟加载的组件
        self._segmentor = None
        self._classifier = None
        self._scaler = None

        logger.info("v8 流水线初始化完成")
        logger.info(f"  阈值: {self.threshold}")
        logger.info(f"  坝体渗水约束: overlap>={self.seepage_min_overlap*100:.3f}%, "
                    f"ratio<={self.seepage_max_ratio*100:.0f}%, dam>water={self.require_dam_gt_water}")

    def _load_segmentor(self):
        """延迟加载分割器"""
        if self._segmentor is not None:
            return

        logger.info("加载 C-RADIOv4 分割器...")
        from models.open_vocab.radseg_segmentor import RADSegWaterSegmentor

        self._segmentor = RADSegWaterSegmentor(
            checkpoint_path=self.checkpoint_path,
            radio_code_dir=self.radio_code_dir,
            siglip2_dir=self.siglip2_dir,
            device='cuda',
            use_scra=True,
            use_dino=True,
            use_sam=False,
            temperature=50.0,
        )
        logger.info("  分割器加载完成")

    def _load_classifier(self):
        """延迟加载分类器"""
        if self._classifier is not None:
            return

        logger.info("加载水质分类器...")
        classifier_dir = Path(self.config.get('classifier_dir', 'models/classifier'))

        with open(classifier_dir / 'lightweight_classifier.pkl', 'rb') as f:
            clf_data = pickle.load(f)
            self._classifier = clf_data['classifier']

        with open(classifier_dir / 'scaler.pkl', 'rb') as f:
            self._scaler = pickle.load(f)

        logger.info("  分类器加载完成")

    def process(self, image: np.ndarray) -> Dict:
        """
        处理单张图像

        Args:
            image: BGR 图像

        Returns:
            dict: 包含检测结果的字典
        """
        h, w = image.shape[:2]
        total_pixels = h * w

        # 确保模型已加载
        if self._segmentor is None:
            self._load_segmentor()
        if self._classifier is None:
            self._load_classifier()

        # Stage 1: 分割
        heatmaps = self._segmentor.compute_patch_similarity(image, DETECTION_PROMPTS)

        water_mask = (heatmaps.get('water', np.zeros((h, w))) > self.threshold)
        dam_mask = (heatmaps.get('dam_concrete', np.zeros((h, w))) > self.threshold)

        # Stage 2: 分析
        seepage_mask = water_mask & dam_mask
        seepage_area = seepage_mask.sum()
        dam_area = dam_mask.sum()
        water_area = water_mask.sum()

        # 噶体渗水检测
        has_seepage = False
        if seepage_area > 0:
            overlap_ratio = seepage_area / total_pixels
            seepage_to_dam = seepage_area / dam_area if dam_area > 0 else 0

            if (overlap_ratio >= self.seepage_min_overlap and
                seepage_to_dam <= self.seepage_max_ratio):

                if self.require_dam_gt_water:
                    if dam_area > water_area:
                        has_seepage = True
                else:
                    has_seepage = True

        # 水质分类
        combined_mask = water_mask | dam_mask
        water_quality, all_probs = self._classify_water(image, combined_mask)

        # 合并结果
        detected = list(water_quality)
        if has_seepage and 'dam_seepage' not in detected:
            detected.append('dam_seepage')

        # 计算面积比例
        area_ratios = {}
        for cls in detected:
            if cls == 'dam_seepage':
                area_ratios[cls] = seepage_area / total_pixels
            elif cls == 'normal_water':
                area_ratios[cls] = water_area / total_pixels
            else:
                area_ratios[cls] = water_area / total_pixels

        # 构建置信度
        confidence = {cls: all_probs.get(cls, 0.0) for cls in detected}

        # 中文类名
        detected_cn = [WATER_QUALITY_CLASSES.get(c, {}).get('zh', c) for c in detected]

        return {
            'detected_classes': detected,
            'detected_classes_cn': detected_cn,
            'water_mask': water_mask,
            'dam_mask': dam_mask,
            'seepage_mask': seepage_mask,
            'has_seepage': has_seepage,
            'confidence': confidence,
            'area_ratios': area_ratios,
        }

    def _classify_water(self, image: np.ndarray, mask: np.ndarray) -> Tuple[List[str], Dict]:
        """多标签水质分类"""
        if not mask.any():
            return [], {}

        pixels = image[mask]
        if len(pixels) == 0:
            return [], {}

        # 提取特征
        features = self._extract_features(image, mask)
        if features is None:
            return [], {}

        # 预测
        features_scaled = self._scaler.transform(features.reshape(1, -1))
        pred_idx = self._classifier.predict(features_scaled)[0]

        class_names = list(WATER_QUALITY_CLASSES.keys())
        pred_class = class_names[pred_idx]

        # 多标签检测
        if hasattr(self._classifier, 'predict_proba'):
            proba = self._classifier.predict_proba(features_scaled)[0]
            all_probs = {class_names[i]: float(proba[i]) for i in range(len(class_names))}

            # 概率 >= 0.3 的异常类 (不含 dam_seepage)
            detected = [cls for cls in class_names
                      if cls in ['black_water', 'turbid_water', 'red_water', 'green_water', 'milky_foam_water']
                      and all_probs.get(cls, 0) >= self.multi_label_threshold]

            if not detected and pred_class in ['black_water', 'turbid_water', 'red_water', 'green_water', 'milky_foam_water']:
                detected = [pred_class]
        else:
            detected = [pred_class] if pred_class != 'normal_water' else []
            all_probs = {}

        return detected, all_probs

    def _extract_features(self, image: np.ndarray, mask: np.ndarray) -> Optional[np.ndarray]:
        """提取 67 维特征"""
        pixels = image[mask]
        if len(pixels) == 0:
            return None

        # BGR 统计
        bgr_mean = pixels.mean(axis=0)
        bgr_std = pixels.std(axis=0)

        # HSV 统计
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hsv_pixels = hsv[mask]
        hsv_mean = hsv_pixels.mean(axis=0)
        hsv_std = hsv_pixels.std(axis=0)

        # 颜色直方图
        hist_b, _ = np.histogram(pixels[:, 0], bins=16, range=(0, 256))
        hist_g, _ = np.histogram(pixels[:, 1], bins=16, range=(0, 256))
        hist_r, _ = np.histogram(pixels[:, 2], bins=16, range=(0, 256))

        hist_b = hist_b.astype(np.float32) / (hist_b.sum() + 1e-6)
        hist_g = hist_g.astype(np.float32) / (hist_g.sum() + 1e-6)
        hist_r = hist_r.astype(np.float32) / (hist_r.sum() + 1e-6)

        # 颜色距离
        color_ref = {
            "black_water": np.array([90, 95, 85]),
            "turbid_water": np.array([119, 140, 130]),
            "red_water": np.array([100, 80, 140]),
            "green_water": np.array([117, 156, 130]),
            "milky_foam_water": np.array([180, 190, 195]),
            "dam_seepage": np.array([130, 135, 140]),
            "normal_water": np.array([118, 124, 107]),
        }
        color_dists = [np.linalg.norm(bgr_mean - color_ref[cls]) for cls in color_ref]

        return np.concatenate([
            bgr_mean, bgr_std, hsv_mean, hsv_std,
            hist_b, hist_g, hist_r, np.array(color_dists)
        ])


# ==============================================================================
# 统一检测系统
# ==============================================================================

class UnifiedWaterInspectionSystem:
    """
    水利巡检统一检测系统

    整合:
      1. YOLOv8 目标检测 (边端)
      2. C-RADIOv4 水质分类 (云端)

    云边协同:
      - YOLO 检测到人员/设施异常时, 触发云端水质分割
      - 水质异常时, 生成报警
    """

    def __init__(self, config_path: str = "configs/water_inspection.yaml"):
        """初始化系统"""
        self.config_path = config_path
        self.config = self._load_config(config_path)

        # 组件
        self.yolo_model = None
        self.water_quality_pipeline = None

        # 报警历史 (抑制重复)
        self.alert_history: Dict[str, datetime] = {}
        self.alert_cooldown = 300  # 5分钟

        # 帧计数 (用于控制云端检测频率)
        self.frame_count = 0

        logger.info("水利巡检系统初始化完成")

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_yolo_model(self):
        """延迟加载 YOLO 模型"""
        if self.yolo_model is not None:
            return

        logger.info("加载 YOLO 模型...")
        try:
            from ultralytics import YOLO

            weights_path = self.config['yolo']['model']['weights']

            if weights_path.endswith('.engine'):
                self.yolo_model = self._load_tensorrt_model(weights_path)
            else:
                self.yolo_model = YOLO(weights_path)

            logger.info("  YOLO 模型加载完成")
        except Exception as e:
            logger.error(f"加载 YOLO 模型失败: {e}")

    def _load_tensorrt_model(self, engine_path: str):
        """加载 TensorRT 模型"""
        try:
            import tensorrt as trt

            logger_obj = trt.Logger(trt.Logger.INFO)
            with open(engine_path, 'rb') as f:
                runtime = trt.Runtime(logger_obj)
                engine = runtime.deserialize_cuda_engine(f.read())

            return {'engine': engine, 'context': engine.create_execution_context()}
        except Exception as e:
            logger.error(f"加载 TensorRT 模型失败: {e}")
            return None

    def _load_water_quality_pipeline(self):
        """延迟加载水质检测流水线"""
        if self.water_quality_pipeline is not None:
            return

        logger.info("加载 v8 水质检测流水线...")

        v8_config = self.config['cloud']['radio']['v8_pipeline']

        # 获取模型路径
        model_config = self.config['cloud']['radio']['model']

        self.water_quality_pipeline = V8WaterQualityPipeline({
            'segmentation_threshold': v8_config['segmentation_threshold'],
            'seepage_min_overlap': v8_config['seepage']['min_overlap'],
            'seepage_max_ratio': v8_config['seepage']['max_ratio'],
            'require_dam_gt_water': v8_config['seepage']['require_dam_gt_water'],
            'multi_label_threshold': v8_config['multi_label_threshold'],
            'checkpoint_path': model_config['path'],
            'radio_code_dir': model_config['radio_code_dir'],
            'siglip2_dir': model_config['siglip2_dir'],
            'classifier_dir': self.config['data']['classifier_dir'],
        })

        logger.info("  v8 流水线加载完成")

    def detect(self, image: np.ndarray, run_water_quality: bool = True) -> Dict:
        """
        统一检测接口

        Args:
            image: BGR 图像
            run_water_quality: 是否运行水质检测 (云端)

        Returns:
            dict: 包含检测结果
        """
        results = {
            'detections': [],
            'water_quality': None,
            'alerts': [],
        }

        # 加载模型
        if self.yolo_model is None:
            self._load_yolo_model()

        # 1. YOLO 检测
        detections = self._detect_yolo(image)
        results['detections'] = detections

        # 2. 判断是否需要水质检测
        should_run_water = run_water_quality and self._should_run_water_quality(detections)

        # 3. 水质检测 (云端)
        if should_run_water:
            if self.water_quality_pipeline is None:
                self._load_water_quality_pipeline()

            water_result = self.water_quality_pipeline.process(image)
            results['water_quality'] = water_result

            # 4. 生成报警
            alerts = self._generate_alerts(detections, water_result)
            results['alerts'] = alerts

        self.frame_count += 1

        return results

    def _detect_yolo(self, image: np.ndarray) -> List[Detection]:
        """YOLO 检测"""
        detections = []

        if self.yolo_model is None:
            return detections

        try:
            inference_config = self.config['yolo']['inference']

            if isinstance(self.yolo_model, dict):
                # TensorRT 推理
                inputs = self.yolo_model['engine'].get_binding_shape(0)
                input_tensor = np.zeros(inputs, dtype=np.float32)

                # 预处理
                input_img = cv2.resize(image, (inputs[2], inputs[3]))
                input_img = input_img.transpose(2, 0, 1) / 255.0

                # 推理
                outputs = self.yolo_model['context'].execute_v2(list(input_tensor), [input_img])
                # 后处理...
            else:
                # PyTorch 推理
                results = self.yolo_model.predict(
                    image,
                    conf=inference_config['conf_threshold'],
                    iou=inference_config['iou_threshold'],
                    device=self.config['yolo']['inference']['device'],
                    verbose=False,
                )

                for r in results[0].boxes.data:
                    det = Detection(
                        class_id=int(r.cls),
                        class_name=YOLO_CLASSES[int(r.cls)]['name'],
                        class_name_cn=YOLO_CLASSES[int(r.cls)]['zh'],
                        confidence=float(r.conf),
                        bbox=r.xyxy.tolist(),
                    )
                    detections.append(det)

        except Exception as e:
            logger.error(f"YOLO 检测失败: {e}")

        return detections

    def _should_run_water_quality(self, detections: List[Detection]) -> bool:
        """判断是否需要运行水质检测"""
        # 策略1: 检测到人员行为时触发
        for det in detections:
            if det.class_name in ['fishing_person', 'swimming_person', 'playing_person', 'intruding_person']:
                return True

        # 策略2: 检测到设施异常时触发
        for det in detections:
            if det.class_name in ['outlet_active', 'pipe_damaged']:
                return True

        # 策略3: 定期检测 (每 N 帧)
        frame_interval = self.config['deployment']['cloud'].get('frame_interval', 30)
        if self.frame_count % frame_interval == 0:
            return True

        return False

    def _generate_alerts(
        self,
        detections: List[Detection],
        water_result: Optional[Dict]
    ) -> List[Alert]:
        """生成报警"""
        alerts = []

        # YOLO 检测报警
        for det in detections:
            class_info = YOLO_CLASSES.get(det.class_id, {})
            if class_info.get('alert', False):
                continue

            # 检查抑制
            if self._should_suppress_alert(f"detection_{det.class_name}"):
                continue

            level = class_info.get('level', 'info')
            alerts.append(Alert(
                alert_type="detection",
                class_name=det.class_name,
                message=f"检测到{det.class_name_cn}",
                level=level,
                timestamp=datetime.now().isoformat(),
                bbox=det.bbox,
            ))

            self._record_alert(f"detection_{det.class_name}")

        # 水质报警
        if water_result:
            for cls in water_result.get('detected_classes', []):
                if cls == 'normal_water':
                    continue

                class_info = WATER_QUALITY_CLASSES.get(cls, {})
                if not class_info.get('alert', False):
                    continue

                # 检查抑制
                if self._should_suppress_alert(f"water_{cls}"):
                    continue

                level = class_info.get('level', 'warning')
                area = water_result.get('area_ratios', {}).get(cls, 0.0)

                alerts.append(Alert(
                    alert_type="water_quality",
                    class_name=cls,
                    message=f"检测到{class_info['zh']} (面积: {area:.1%})",
                    level=level,
                    timestamp=datetime.now().isoformat(),
                    area=area,
                ))

                self._record_alert(f"water_{cls}")

        return alerts

    def _should_suppress_alert(self, alert_key: str) -> bool:
        """检查是否应该抑制报警"""
        if alert_key not in self.alert_history:
                time_since = (datetime.now() - self.alert_history[alert_key]).total_seconds()
                if time_since < self.alert_cooldown:
                    return True
        return False

    def _record_alert(self, alert_key: str):
        """记录报警"""
        self.alert_history[alert_key] = datetime.now()

    def visualize(
        self,
        image: np.ndarray,
        results: Dict,
        output_path: Optional[str] = None
    ) -> np.ndarray:
        """可视化结果"""
        vis_image = image.copy()

        # 绘制 YOLO 检测框
        for det in results.get('detections', []):
            x1, y1, x2, y2 = [int(v) for v in det.bbox]
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 255, 0), 2)

            label = f"{det.class_name_cn} {det.confidence:.2f}"
            cv2.putText(vis_image, label, (x1, y1 - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

        # 绘制水质分割
        water_result = results.get('water_quality')
        if water_result:
            # 水体掩码
            water_mask = water_result.get('water_mask')
            if water_mask is not None and water_mask.any():
                colored_mask = np.zeros_like(vis_image)
                detected_classes = water_result.get('detected_classes', [])

                if detected_classes:
                    main_class = detected_classes[0]
                    color = WATER_QUALITY_CLASSES.get(main_class, {}).get('color', (100, 100, 100))
                    colored_mask[water_mask] = color

                    vis_image = cv2.addWeighted(vis_image, 0.0, colored_mask, 0.0, 0.0)

            # 坝体渗水标注
            if water_result.get('has_seepage'):
                seepage_mask = water_result.get('seepage_mask')
                if seepage_mask is not None and seepage_mask.any():
                    colored_mask = np.zeros_like(vis_image)
                    colored_mask[seepage_mask] = (0, 100, 255)
                    vis_image = cv2.addWeighted(vis_image, 0.0, colored_mask, 0.0, 1.0)

        # 保存
        if output_path:
            cv2.imwrite(output_path, vis_image)

        return vis_image


# ==============================================================================
# 便捷 API
# ==============================================================================

def create_system(config_path: str = "configs/water_inspection.yaml") -> UnifiedWaterInspectionSystem:
    """
    创建水利巡检系统

    Args:
        config_path: 配置文件路径

    Returns:
        UnifiedWaterInspectionSystem: 系统实例
    """
    return UnifiedWaterInspectionSystem(config_path)


def detect_single_image(
    image_path: str,
    config_path: str = "configs/water_inspection.yaml",
    output_path: Optional[str] = None
) -> Dict:
    """
    检测单张图像 (便捷接口)

    Args:
        image_path: 图像路径
        config_path: 配置文件路径
        output_path: 输出路径

    Returns:
        dict: 检测结果
    """
    system = create_system(config_path)

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"无法加载图像: {image_path}")

    results = system.detect(image)

    if output_path:
        system.visualize(image, results, output_path)

    return results


# ==============================================================================
# 主程序
# ==============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="水利巡检统一检测系统")
    parser.add_argument("--config", type=str, default="configs/water_inspection.yaml")
    parser.add_argument("--image", type=str, required=True)
    parser.add_argument("--output", type=str, default="output.jpg")
    parser.add_argument("--no-water", action="store_true", help="不运行水质检测")

    args = parser.parse_args()

    # 创建系统
    system = create_system(args.config)

    # 加载图像
    image = cv2.imread(args.image)
    if image is None:
        logger.error(f"无法加载图像: {args.image}")
        sys.exit(1)

    # 检测
    results = system.detect(image, run_water_quality=not args.no_water)

    # 打印结果
    print(f"\n检测结果:")
    print(f"  YOLO 检测: {len(results['detections'])} 个")
    for det in results['detections']:
        print(f"    - {det.class_name_cn}: {det.confidence:.2f}")

    if results['water_quality']:
        wq = results['water_quality']
        print(f"\n  水质检测: {wq.get('detected_classes_cn', [])}")
        if wq.get('has_seepage'):
            print(f"    [警告] 检测到坝体渗水!")

    if results['alerts']:
        print(f"\n  报警: {len(results['alerts'])} 个")
        for alert in results['alerts']:
            print(f"    - [{alert.level}] {alert.message}")

    # 可视化
    system.visualize(image, results, args.output)
    print(f"\n结果已保存到: {args.output}")
