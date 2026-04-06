#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一水质分割器 v1.0

整合多个先前版本的最佳实践:
1. RADSeg 风格的对比提示词匹配 (Contrastive Prompt Matching)
2. 两阶段分割 (水体定位 + 水质分类)
3. 颜色一致性校验 (Color Consistency Validation)
4. 多 adaptor 支持 (SigLIP2, DINOv3, SAM3)

7 类水质检测:
- 黑水 (black_water)
- 浑浊水 (turbid_water)
- 红水 (red_water)
- 绿水 (green_water)
- 乳白水 (milky_foam_water)
- 坝体渗水 (dam_seepage)
- 正常水质 (normal_water)

作者: 空中智能体团队
日期: 2026-04-05
"""

import os
import torch
import torch.nn.functional as F
import numpy as np
import cv2
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
import yaml

from .backbone import RadioBackbone
from .classifier import SigLIP2Classifier, ColorValidator

logger = logging.getLogger(__name__)


def _odd_kernel(v: int, default: int) -> int:
    """将核大小规范为 >=3 的奇数"""
    try:
        x = max(3, int(v))
        return x + 1 if x % 2 == 0 else x
    except Exception:
        return default


@dataclass
class SegmentResult:
    """分割结果"""
    class_name: str
    class_name_cn: str
    mask: np.ndarray        # [H, W] bool
    area_ratio: float       # 占图像面积比
    score: float            # 置信度
    water_iou: float = 0.0  # 水体提取 IoU (两阶段模式)
    color_ok: bool = True   # 颜色验证是否通过
    color_score: float = 0.0  # 颜色验证得分
    patch_scores: Optional[np.ndarray] = None


class WaterQualitySegmentor:
    """
    统一水质分割器 v1.0

    核心流程:
      1. RADIO 提取 patch 特征
      2. SigLIP2 adaptor 对齐到语言空间
      3. 与文本嵌入计算相似度 (对比提示词)
      4. 颜色一致性校验
      5. 后处理 (形态学 + 水体约束)

    支持两种模式:
      - 单阶段: 直接使用 RADIO 特征进行分割
      - 两阶段: 先提取水体区域, 再进行水质分类
    """

    # 7 类水质颜色映射 (BGR)
    CLASS_COLORS = {
        "black_water": (0, 0, 180),           # 深蓝色 - 黑水
        "turbid_water": (42, 100, 170),       # 茶色 - 浑浊水
        "red_water": (0, 0, 255),             # 红色 - 红水
        "green_water": (0, 200, 0),           # 绿色 - 绿水/藻类
        "milky_foam_water": (200, 200, 200),  # 浅灰色 - 乳白水/泡沫水
        "dam_seepage": (100, 100, 100),       # 深灰色 - 坝体渗水
        "normal_water": (200, 200, 100),      # 淡黄色 - 正常水质
    }


    def _load_lightweight_classifier(self):
        """加载训练好的轻量化分类器"""
        import pickle
        from pathlib import Path
        
        model_dir = Path('/app/water_inspection/models/classifier')
        model_path = model_dir / 'lightweight_classifier.pkl'
        scaler_path = model_dir / 'scaler.pkl'
        
        if model_path.exists() and scaler_path.exists():
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
                self.lightweight_clf = model_data['classifier']
                self.lightweight_clf_name = model_data['name']
            
            with open(scaler_path, 'rb') as f:
                self.lightweight_scaler = pickle.load(f)
            
            print(f"  ✅ 轻量化分类器已加载: {self.lightweight_clf_name}")
        else:
            self.lightweight_clf = None
            self.lightweight_scaler = None
            print(f"  ⚠️ 轻量化分类器未找到")
    
    def classify_by_lightweight_clf(self, image: np.ndarray, mask: np.ndarray = None) -> Tuple[str, float]:
        """
        使用轻量化分类器进行分类 (方案3)
        
        Args:
            image: RGB图像
            mask: 分割掩码
            
        Returns:
            (class_name, confidence)
        """
        import cv2
        
        if self.lightweight_clf is None:
            return "normal_water", 0.5
        
        # 提取特征 (与训练时相同)
        features = self.extract_color_features(image, mask)
        
        if not features:
            return "normal_water", 0.5
        
        # 构建特征向量 (与训练时相同顺序)
        bgr_mean = features['bgr_mean']
        bgr_std = features['bgr_std']
        hsv_mean = features['hsv_mean']
        hsv_std = features['hsv_std']
        b_hist = features['b_hist']
        g_hist = features['g_hist']
        r_hist = features['r_hist']
        
        # 计算与各类别的颜色距离
        CLASS_COLORS_BGR = {
            "black_water": np.array([90, 95, 85]),
            "turbid_water": np.array([119, 140, 130]),
            "red_water": np.array([100, 80, 140]),
            "green_water": np.array([117, 156, 130]),
            "milky_foam_water": np.array([180, 190, 195]),
            "dam_seepage": np.array([130, 135, 140]),
            "normal_water": np.array([118, 124, 107]),
        }
        
        color_dists = []
        for cls_name in ["black_water", "turbid_water", "red_water", 
                         "green_water", "milky_foam_water", "dam_seepage", "normal_water"]:
            std_color = CLASS_COLORS_BGR[cls_name]
            dist = np.linalg.norm(bgr_mean - std_color)
            color_dists.append(dist)
        
        # 合并特征
        feature_vector = np.concatenate([
            bgr_mean,      # 3
            bgr_std,       # 3
            hsv_mean,      # 3
            hsv_std,       # 3
            b_hist,        # 16
            g_hist,        # 16
            r_hist,        # 16
            np.array(color_dists),  # 7
        ])
        
        # 标准化
        feature_scaled = self.lightweight_scaler.transform(feature_vector.reshape(1, -1))
        
        # 预测
        class_idx = self.lightweight_clf.predict(feature_scaled)[0]
        
        # 获取置信度 (SVM使用decision_function)
        if hasattr(self.lightweight_clf, 'predict_proba'):
            proba = self.lightweight_clf.predict_proba(feature_scaled)[0]
            confidence = proba[class_idx]
        elif hasattr(self.lightweight_clf, 'decision_function'):
            decision = self.lightweight_clf.decision_function(feature_scaled)[0]
            # 转换为概率
            from scipy.special import softmax
            proba = softmax(decision)
            confidence = proba[class_idx]
        else:
            confidence = 0.7  # 默认置信度
        
        CLASS_NAMES = [
            "black_water", "turbid_water", "red_water",
            "green_water", "milky_foam_water", "dam_seepage", "normal_water"
        ]
        
        class_name = CLASS_NAMES[class_idx]
        
        return class_name, float(confidence)


    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        radio_code_dir: Optional[str] = None,
        siglip2_dir: Optional[str] = None,
        device: str = "cuda",
        input_size: int = 896,
        config: Optional[Dict] = None,
        mode: str = "single_stage",  # "single_stage" or "two_stage"
    ):
        """
        Args:
            checkpoint_path: C-RADIOv4 checkpoint 路径 (.pth.tar)
            radio_code_dir: NVlabs/RADIO 代码目录
            siglip2_dir: SigLIP2 模型目录
            device: 推理设备
            input_size: 输入尺寸
            config: 配置字典
            mode: 分割模式 ("single_stage" 或 "two_stage")
        """
        self.device = device
        self.input_size = input_size
        self.config = config or {}
        self.mode = mode

        # 加载 RADIO backbone
        self.backbone = RadioBackbone(
            checkpoint_path=checkpoint_path,
            radio_code_dir=radio_code_dir,
            siglip2_dir=siglip2_dir,
            device=device,
        )

        # 初始化分类器
        self.text_classifier = SigLIP2Classifier(
            backbone=self.backbone,
            temperature=self._get_prompt_temperature(),
            negative_weight=self._get_negative_weight(),
        )

        # 初始化颜色校验器
        self.color_validator = ColorValidator()

        # 加载默认配置（如果未提供）
        if not self.config or not self.config.get("cloud", {}).get("radio", {}).get("classes"):
            self._load_default_config()

        # 加载推理参数
        self._load_inference_config()

        print(f"统一水质分割器初始化完成:")
        print(f"  模式: {mode}")
        print(f"  设备: {device}")
        print(f"  输入尺寸: {input_size}")
        print(f"  类别数: {len(self.CLASS_COLORS)}")

    def _load_inference_config(self):
        """加载推理配置参数"""
        radio_cfg = self.config.get("cloud", {}).get("radio", {})
        infer_cfg = radio_cfg.get("inference", {})

        # 基础参数
        self.threshold = infer_cfg.get("threshold", 0.30)
        self.min_area = infer_cfg.get("min_area", 0.005)
        self.image_gate = infer_cfg.get("image_gate", 0.08)
        self.class_thresholds = infer_cfg.get("class_thresholds", {}) or {}

        # 后处理参数
        post_cfg = infer_cfg.get("postprocess", {})
        self.post_erode_kernel = post_cfg.get("erode_kernel", 2)
        self.post_open_kernel = post_cfg.get("open_kernel", 2)
        self.post_max_components = post_cfg.get("max_components", 3)
        self.post_min_component_pixels = post_cfg.get("min_component_pixels", 50)

        # 水体识别参数
        water_cfg = infer_cfg.get("water", {})
        self.water_min_ratio = water_cfg.get("min_ratio", 0.05)
        self.water_erode_kernel = water_cfg.get("erode_kernel", 7)

        # 正常标签输出
        self.emit_normal_label = infer_cfg.get("emit_normal_label", True)
        self.normal_label_min_prob = infer_cfg.get("normal_label_min_prob", 0.45)
        self.normal_label_max_anomaly_prob = infer_cfg.get("normal_label_max_anomaly_prob", 0.35)

        # Patch 分类参数
        patch_cfg = infer_cfg.get("patch", {})
        self.num_patches = patch_cfg.get("num_patches", 64)
        self.min_overlap_threshold = patch_cfg.get("min_overlap_threshold", 0.50)
        self.patch_selection_strategy = patch_cfg.get("patch_selection_strategy", "top_k")
        self.top_k_patches = patch_cfg.get("top_k_patches", 10)
        self.overlap_weight = patch_cfg.get("overlap_weight", 1.5)

        # 颜色校验参数
        color_cfg = infer_cfg.get("color", {})
        self.color_max_dist = color_cfg.get("max_dist", 100)
        self.color_strict_prob = color_cfg.get("strict_prob", 0.65)
        self.color_enable_per_class = color_cfg.get("enable_per_class", True)
        self.color_fusion_alpha = float(color_cfg.get("fusion_alpha", 0.20))

    def _get_prompt_temperature(self) -> float:
        """获取提示词温度"""
        radio_cfg = self.config.get("cloud", {}).get("radio", {})
        return radio_cfg.get("inference", {}).get("prompt", {}).get("temperature", 3.0)

    def _get_negative_weight(self) -> float:
        """获取负提示词权重"""
        radio_cfg = self.config.get("cloud", {}).get("radio", {})
        return radio_cfg.get("inference", {}).get("prompt", {}).get("negative_weight", 0.6)

    def _load_default_config(self):
        """加载默认的7类水质配置"""
        # 默认配置文件路径
        prompts_path = Path(__file__).parent.parent / "prompts" / "water_quality.yaml"

        if prompts_path.exists():
            with open(prompts_path, 'r', encoding='utf-8') as f:
                prompts_config = yaml.safe_load(f)

            # 构建 classes_config
            self.config = {
                "cloud": {
                    "radio": {
                        "classes": {
                            cls_name: {
                                "prompts": cfg.get("positive", []),
                                "is_background": cls_name == "normal_water"
                            }
                            for cls_name, cfg in prompts_config.get("water_quality_detection", {}).items()
                        }
                    }
                }
            }
            print(f"  ✓ 加载默认配置: {len(self.config['cloud']['radio']['classes'])} 类")
        else:
            # 硬编码最小配置
            print(f"  ⚠️ 未找到配置文件: {prompts_path}, 使用硬编码配置")
            self.config = {
                "cloud": {
                    "radio": {
                        "classes": {
                            "black_water": {"prompts": ["black water"], "is_background": False},
                            "turbid_water": {"prompts": ["turbid water"], "is_background": False},
                            "red_water": {"prompts": ["red water"], "is_background": False},
                            "green_water": {"prompts": ["green water"], "is_background": False},
                            "milky_foam_water": {"prompts": ["milky water"], "is_background": False},
                            "dam_seepage": {"prompts": ["dam seepage"], "is_background": False},
                            "normal_water": {"prompts": ["normal water"], "is_background": True},
                        }
                    }
                }
            }

    def get_classes_config(self) -> Dict[str, dict]:
        """获取类别配置"""
        radio_cfg = self.config.get("cloud", {}).get("radio", {})
        return radio_cfg.get("classes", {})

    # ─────────────────────────────────────────────────────────────────────
    # 核心分割方法
    # ─────────────────────────────────────────────────────────────────────


    def _load_lightweight_classifier(self):
        """加载训练好的轻量化分类器"""
        import pickle
        from pathlib import Path
        
        model_dir = Path('/app/water_inspection/models/classifier')
        model_path = model_dir / 'lightweight_classifier.pkl'
        scaler_path = model_dir / 'scaler.pkl'
        
        if model_path.exists() and scaler_path.exists():
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
                self.lightweight_clf = model_data['classifier']
                self.lightweight_clf_name = model_data['name']
            
            with open(scaler_path, 'rb') as f:
                self.lightweight_scaler = pickle.load(f)
            
            print(f"  ✅ 轻量化分类器已加载: {self.lightweight_clf_name}")
        else:
            self.lightweight_clf = None
            self.lightweight_scaler = None
            print(f"  ⚠️ 轻量化分类器未找到")

    def segment(
        self,
        image: np.ndarray,
        classes_config: Optional[Dict[str, dict]] = None,
        prompts_config: Optional[Dict[str, dict]] = None,
        class_thresholds: Optional[Dict[str, float]] = None,
        threshold: Optional[float] = None,
        min_area: Optional[float] = None,
        use_color_classifier: bool = True,  # 方案1: 使用颜色分类器
    ) -> Dict[str, SegmentResult]:
        """
        水质异常分割
        
        方案1 (推荐): RADIO分割 + 颜色规则分类

        Args:
            image: BGR 图像 [H, W, 3]
            classes_config: 类别配置 (可选, 默认使用配置文件)
            prompts_config: 提示词配置
            threshold: 百分位阈值
            min_area: 最小面积占比
            use_color_classifier: 是否使用颜色分类器 (方案1)

        Returns:
            {class_name: SegmentResult}
        """
        classes_config = classes_config or self.get_classes_config()
        
        # 过滤背景类，只保留检测类
        detection_config = {k: v for k, v in classes_config.items() if not v.get("is_background", False)}
        detection_prompts = None
        if prompts_config:
            detection_prompts = {k: v for k, v in prompts_config.items() if k in detection_config}

        threshold = threshold if threshold is not None else 0.35  # 提高阈值
        min_area = min_area if min_area is not None else self.min_area
        class_thresholds = class_thresholds or self.class_thresholds

        orig_h, orig_w = image.shape[:2]

        # 获取请求的异常类别 (排除背景类)
        requested_classes = [
            k for k, v in classes_config.items()
            if not v.get("is_background", False)
        ]

        # 检查空类别列表
        if not requested_classes:
            logger.warning("没有配置检测类别，返回空结果")
            return {}

        # ━━━ 第 1 步: 图像级分类 (排除背景类) + 颜色验证 ━━━
        class_probs = self.text_classifier.classify_image(
            image, detection_config, detection_prompts
        )

        # 颜色验证 - 参考v4.1
        if class_probs:
            # 计算图像主要区域的颜色
            try:
                img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                mean_color = cv2.mean(img_bgr)[:3]  # BGR

                # 根据颜色特征调整分类分数
                for cls_name in class_probs.keys():
                    if cls_name in ColorValidator.COLOR_STATS:
                        stats = ColorValidator.COLOR_STATS[cls_name]
                        expected = np.array(stats["mean"])
                        std = np.array(stats["std"])

                        # 计算颜色距离
                        color_dist = np.linalg.norm(np.array(mean_color) - expected)

                        # 颜色越接近，给予小幅度加成
                        if color_dist < 50:  # 颜色匹配
                            class_probs[cls_name] *= 1.1
                        elif color_dist > 100:  # 颜色不匹配
                            class_probs[cls_name] *= 0.9
            except:
                pass  # 颜色验证失败不影响主流程

        # 图像级门控
        img_anomaly_prob = max([class_probs.get(c, 0.0) for c in requested_classes] or [0.0])
        low_image_conf = img_anomaly_prob < self.image_gate

        # ━━━ 第 2 步: Patch 级相似度计算 (排除背景类) ━━━
        class_heatmaps = self.text_classifier.compute_patch_similarity(
            image, detection_config, detection_prompts, self.input_size
        )

        # 应用颜色软融合 (使用检测类)
        class_heatmaps = self._apply_color_soft_fusion(
            image, class_heatmaps, detection_config
        )

        if not class_heatmaps:
            return self._maybe_emit_normal_label(
                class_probs, requested_classes, classes_config, orig_h, orig_w
            )

        # ━━━ 第 3 步: 构建异常热图 ━━━
        anomaly_heatmap = np.zeros((orig_h, orig_w), dtype=np.float32)
        best_class_map = np.zeros((orig_h, orig_w), dtype=np.int32)
        class_list = list(requested_classes)
        class_to_idx = {c: i for i, c in enumerate(class_list)}

        for cls_name in requested_classes:
            if cls_name not in class_heatmaps:
                continue
            heatmap = class_heatmaps[cls_name]

            cls_cfg = classes_config.get(cls_name, {})
            cls_thr = threshold
            if class_thresholds and cls_name in class_thresholds:
                cls_thr = float(class_thresholds[cls_name])
            elif "min_prob" in cls_cfg:
                cls_thr = float(cls_cfg.get("min_prob", threshold))
            heatmap = np.where(heatmap >= cls_thr, heatmap, 0.0)

            # 更新热图 (取最大值)
            better_mask = heatmap > anomaly_heatmap
            anomaly_heatmap = np.where(better_mask, heatmap, anomaly_heatmap)
            best_class_map = np.where(better_mask, class_to_idx[cls_name], best_class_map)

        # ━━━ 第 4 步: 识别水体区域 ━━━
        water_mask = self._identify_water_region(class_heatmaps, orig_h, orig_w)

        water_ratio = water_mask.sum() / water_mask.size
        if water_ratio < self.water_min_ratio:
            return self._maybe_emit_normal_label(
                class_probs, requested_classes, classes_config, orig_h, orig_w
            )

        # ━━━ 第 5 步: 阈值分割异常区域 ━━━
        anomaly_mask = anomaly_heatmap > 0
        anomaly_mask = anomaly_mask & water_mask

        if not anomaly_mask.any():
            return self._maybe_emit_normal_label(
                class_probs, requested_classes, classes_config, orig_h, orig_w
            )

        # ━━━ 第 6 步: 后处理 ━━━
        anomaly_mask = self._postprocess_mask(anomaly_mask, anomaly_heatmap)

        area = anomaly_mask.sum() / anomaly_mask.size
        if area < min_area:
            return self._maybe_emit_normal_label(
                class_probs, requested_classes, classes_config, orig_h, orig_w
            )

        # ━━━ 第 7 步: 确定标签 + 颜色校验 ━━━
        masked_class_map = best_class_map[anomaly_mask]
        if masked_class_map.size > 0:
            valid_mask = masked_class_map >= 0
            if valid_mask.any():
                valid_classes = masked_class_map[valid_mask]
                class_counts = np.bincount(valid_classes, minlength=len(class_list))
                best_idx = np.argmax(class_counts)
                best_anomaly_class = class_list[best_idx] if class_counts[best_idx] > 0 else None
            else:
                best_anomaly_class = None
        else:
            best_anomaly_class = None

        if best_anomaly_class is None:
            # 使用图像级分类结果
            for cls_name in requested_classes:
                if class_probs.get(cls_name, 0) > class_probs.get("normal_water", 0):
                    best_anomaly_class = cls_name
                    break

        if best_anomaly_class is None:
            if low_image_conf:
                return {}
            return self._maybe_emit_normal_label(
                class_probs, requested_classes, classes_config, orig_h, orig_w
            )

        # 颜色一致性校验
        region_bgr = self._get_region_bgr(image, anomaly_mask)
        color_ok, adjusted_score = self.color_validator.validate_color_consistency(
            best_anomaly_class,
            float(anomaly_heatmap[anomaly_mask].mean()),
            region_bgr,
            classes_config,
            self.color_max_dist,
        )

        # 计算置信度
        best_score = adjusted_score if not color_ok else float(anomaly_heatmap[anomaly_mask].mean())

        cfg = classes_config.get(best_anomaly_class, {})
        zh_name = cfg.get("zh", best_anomaly_class)

        return {
            best_anomaly_class: SegmentResult(
                class_name=best_anomaly_class,
                class_name_cn=zh_name,
                mask=anomaly_mask,
                area_ratio=float(area),
                score=float(best_score),
                water_iou=float(water_ratio),
                color_ok=color_ok,
                color_score=adjusted_score,
                patch_scores=anomaly_heatmap,
            )
        }

    # ─────────────────────────────────────────────────────────────────────
    # 辅助方法
    # ─────────────────────────────────────────────────────────────────────

    def _identify_water_region(
        self,
        class_heatmaps: Dict[str, np.ndarray],
        orig_h: int,
        orig_w: int,
    ) -> np.ndarray:
        """识别可信水体区域"""
        trusted_water = np.zeros((orig_h, orig_w), dtype=bool)

        # 从 normal_water 热图构建
        if "normal_water" in class_heatmaps:
            normal_heatmap = class_heatmaps["normal_water"]
            trusted_water = normal_heatmap > 0.3

        trusted_ratio = trusted_water.sum() / trusted_water.size

        # 如果没有正常水区域, 使用底部启发式
        if trusted_ratio < self.water_min_ratio:
            y_cutoff = int(orig_h * 0.25)
            trusted_water = np.zeros((orig_h, orig_w), dtype=bool)
            trusted_water[y_cutoff:, :] = True

        # 水体边界收缩
        kernel_size = _odd_kernel(self.water_erode_kernel, 7)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        water_eroded = cv2.erode(trusted_water.astype(np.uint8), kernel).astype(bool)

        # 保留最大连通域
        if water_eroded.any():
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
                water_eroded.astype(np.uint8), connectivity=8
            )
            if num_labels > 1:
                areas = stats[1:, cv2.CC_STAT_AREA]
                largest = int(np.argmax(areas)) + 1
                water_eroded = labels == largest

        return water_eroded

    def _apply_color_soft_fusion(
        self,
        image: np.ndarray,
        class_heatmaps: Dict[str, np.ndarray],
        classes_config: Dict[str, dict],
    ) -> Dict[str, np.ndarray]:
        """颜色先验软融合"""
        if self.color_fusion_alpha <= 0:
            return class_heatmaps

        fused = {}
        for cls_name, heatmap in class_heatmaps.items():
            cfg = classes_config.get(cls_name, {})
            if not cfg.get("use_color_check", False):
                fused[cls_name] = heatmap
                continue

            color_hint = cfg.get("color_hint")
            if color_hint is None or len(color_hint) != 3:
                fused[cls_name] = heatmap
                continue

            color_sim = self._build_color_similarity_map(image, color_hint)
            fused_map = (1.0 - self.color_fusion_alpha) * heatmap + self.color_fusion_alpha * (heatmap * color_sim)
            fused[cls_name] = fused_map.astype(np.float32)

        return fused

    def _build_color_similarity_map(
        self,
        image: np.ndarray,
        color_hint: List[int],
    ) -> np.ndarray:
        """构建像素级颜色相似度图"""
        hint = np.asarray(color_hint, dtype=np.float32).reshape(1, 1, 3)
        img = image.astype(np.float32)
        dist = np.linalg.norm(img - hint, axis=2)
        sigma = max(25.0, float(self.color_max_dist) * 0.8)
        sim = np.exp(-0.5 * (dist / sigma) ** 2)
        return sim.astype(np.float32)

    def _postprocess_mask(
        self,
        mask: np.ndarray,
        conf_map: np.ndarray,
    ) -> np.ndarray:
        """后处理: 形态学操作 + 保留高分连通域"""
        # 腐蚀
        erode_k = _odd_kernel(self.post_erode_kernel, 2)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_k, erode_k))
        mask = cv2.erode(mask.astype(np.uint8), kernel).astype(bool)

        if not mask.any():
            return mask

        # 开运算
        open_k = _odd_kernel(self.post_open_kernel, 2)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_k, open_k))
        mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel).astype(bool)

        if not mask.any():
            return mask

        # 保留高分连通域
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask.astype(np.uint8), connectivity=8
        )

        if num_labels <= 2:
            return mask

        candidates = []
        for lid in range(1, num_labels):
            comp = labels == lid
            area_px = int(stats[lid, cv2.CC_STAT_AREA])
            if area_px < self.post_min_component_pixels:
                continue
            comp_conf = conf_map[comp]
            if comp_conf.size > 0:
                score = float(comp_conf.mean())
                candidates.append((lid, score, area_px))

        if not candidates:
            areas = stats[1:, cv2.CC_STAT_AREA]
            lid = int(np.argmax(areas)) + 1
            return labels == lid

        candidates.sort(key=lambda x: -x[1])
        top_labels = [lid for lid, _, _ in candidates[:self.post_max_components]]
        return np.isin(labels, top_labels)

    def _get_region_bgr(
        self,
        image: np.ndarray,
        mask: np.ndarray,
    ) -> Optional[np.ndarray]:
        """获取区域的平均 BGR 颜色"""
        ys, xs = np.where(mask)
        if len(ys) == 0:
            return None
        pixels = image[ys, xs].astype(np.float32)
        return pixels.mean(axis=0)

    def _maybe_emit_normal_label(
        self,
        class_probs: Dict[str, float],
        requested_classes: set,
        classes_config: Dict[str, dict],
        orig_h: int,
        orig_w: int,
    ) -> Dict[str, SegmentResult]:
        """在无异常时输出正常水体标签"""
        if not self.emit_normal_label:
            return {}

        normal_prob = class_probs.get("normal_water", 0.0)
        max_anomaly_prob = max(class_probs.get(c, 0.0) for c in requested_classes)

        if (normal_prob >= self.normal_label_min_prob and
            max_anomaly_prob <= self.normal_label_max_anomaly_prob):
            cfg = classes_config.get("normal_water", {})
            return {
                "normal_water": SegmentResult(
                    class_name="normal_water",
                    class_name_cn=cfg.get("zh", "正常水体"),
                    mask=np.zeros((orig_h, orig_w), dtype=bool),
                    area_ratio=0.0,
                    score=normal_prob,
                )
            }

        return {}

    # ─────────────────────────────────────────────────────────────────────
    # 可视化
    # ─────────────────────────────────────────────────────────────────────


    def classify_by_color(self, image: np.ndarray, mask: np.ndarray = None) -> Tuple[str, float]:
        """
        基于颜色的简单规则分类器 (方案1)
        
        策略:
        1. 计算区域平均颜色
        2. 与7类标准颜色比较
        3. 返回最匹配的类别
        
        Args:
            image: RGB图像
            mask: 分割掩码 (可选)
            
        Returns:
            (class_name, confidence)
        """
        import cv2
        
        # 转换为BGR
        if image.shape[2] == 3:
            img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = image
        
        # 计算平均颜色
        if mask is not None and mask.any():
            mean_color = cv2.mean(img_bgr, mask.astype(np.uint8))[:3]
        else:
            mean_color = cv2.mean(img_bgr)[:3]
        
        mean_bgr = np.array(mean_color)
        
        # 7类标准颜色 (BGR) - 基于109张样本统计
        CLASS_COLORS_BGR = {
            "black_water": np.array([90, 95, 85]),
            "turbid_water": np.array([119, 140, 130]),
            "red_water": np.array([100, 80, 140]),
            "green_water": np.array([117, 156, 130]),
            "milky_foam_water": np.array([180, 190, 195]),
            "dam_seepage": np.array([130, 135, 140]),
            "normal_water": np.array([118, 124, 107]),
        }
        
        # 计算与各类别的颜色距离
        distances = {}
        for cls_name, std_color in CLASS_COLORS_BGR.items():
            dist = np.linalg.norm(mean_bgr - std_color)
            distances[cls_name] = dist
        
        # 找到最接近的类别
        best_class = min(distances.keys(), key=lambda k: distances[k])
        best_dist = distances[best_class]
        
        # 转换为置信度 (距离越小置信度越高)
        max_dist = 150.0  # 假设最大距离
        confidence = max(0.0, 1.0 - best_dist / max_dist)
        
        return best_class, confidence
    

    def extract_color_features(self, image: np.ndarray, mask: np.ndarray = None) -> dict:
        """
        提取多维度颜色特征
        
        特征:
        1. BGR均值和标准差
        2. HSV均值和标准差  
        3. 颜色直方图特征
        """
        import cv2
        
        # 转BGR
        if len(image.shape) == 3 and image.shape[2] == 3:
            img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if image.dtype == np.uint8 else image
        else:
            img_bgr = image
        
        # 应用mask
        if mask is not None and mask.any():
            masked_img = img_bgr * mask[:, :, np.newaxis]
            pixels = masked_img[mask > 0]
        else:
            pixels = img_bgr.reshape(-1, 3)
        
        if len(pixels) == 0:
            return {}
        
        # BGR统计
        bgr_mean = pixels.mean(axis=0)
        bgr_std = pixels.std(axis=0)
        
        # 转HSV
        hsv_img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        if mask is not None and mask.any():
            hsv_pixels = hsv_img[mask > 0]
        else:
            hsv_pixels = hsv_img.reshape(-1, 3)
        
        hsv_mean = hsv_pixels.mean(axis=0)
        hsv_std = hsv_pixels.std(axis=0)
        
        # 颜色直方图 (简化版)
        # B通道分布
        b_hist = np.histogram(pixels[:, 0], bins=3, range=(0, 255))[0]
        g_hist = np.histogram(pixels[:, 1], bins=3, range=(0, 255))[0]
        r_hist = np.histogram(pixels[:, 2], bins=3, range=(0, 255))[0]
        
        # 归一化
        b_hist = b_hist / (b_hist.sum() + 1e-6)
        g_hist = g_hist / (g_hist.sum() + 1e-6)
        r_hist = r_hist / (r_hist.sum() + 1e-6)
        
        return {
            'bgr_mean': bgr_mean,
            'bgr_std': bgr_std,
            'hsv_mean': hsv_mean,
            'hsv_std': hsv_std,
            'b_hist': b_hist,
            'g_hist': g_hist,
            'r_hist': r_hist,
        }
    
    def classify_by_enhanced_features(self, image: np.ndarray, mask: np.ndarray = None) -> Tuple[str, float]:
        """
        增强的颜色分类器 - 多特征融合
        
        策略:
        1. 提取多维度颜色特征
        2. 基于规则的决策树
        3. 置信度评估
        """
        features = self.extract_color_features(image, mask)
        
        if not features:
            return "normal_water", 0.5
        
        bgr_mean = features['bgr_mean']
        hsv_mean = features['hsv_mean']
        b, g, r = bgr_mean
        h, s, v = hsv_mean
        
        # 基于规则的决策树分类
        # 规则基于109张样本的统计特征
        
        # 1. 黑水: 整体暗，BGR都低
        if v < 100 and b < 110 and g < 115 and r < 105:
            return "black_water", 0.85
        
        # 2. 乳白水: 高亮度，低饱和度
        if v > 170 and s < 40:
            return "milky_foam_water", 0.80
        
        # 3. 红水: R通道主导，H在红色范围
        if r > b + 20 and r > g + 20 and h > 170:
            return "red_water", 0.75
        
        # 4. 绿水: G通道主导，H在绿色范围
        if g > b + 15 and g > r + 10 and 35 < h < 85:
            return "green_water", 0.75
        
        # 5. 浑浊水: 黄褐色，H在黄色范围
        if 15 < h < 35 and s > 30 and v > 90:
            return "turbid_water", 0.70
        
        # 6. 坝体渗水: 中等亮度，低饱和度，灰度
        if 100 < v < 160 and s < 50 and abs(b - g) < 30 and abs(g - r) < 30:
            return "dam_seepage", 0.65
        
        # 7. 正常水: 默认
        return "normal_water", 0.60


    def segment_with_color_classify(
        self,
        image: np.ndarray,
        classes_config: Optional[Dict[str, dict]] = None,
        prompts_config: Optional[Dict[str, dict]] = None,
        threshold: Optional[float] = None,
    ) -> Dict[str, 'SegmentResult']:
        """
        方案1主流程: RADIO分割 + 颜色分类
        
        流程:
        1. RADIO提取水体区域
        2. 颜色规则分类水质
        3. 返回分割+分类结果
        
        Args:
            image: BGR图像
            classes_config: 类别配置
            prompts_config: 提示词配置
            threshold: 分割阈值
            
        Returns:
            {class_name: SegmentResult}
        """
        import cv2
        
        orig_h, orig_w = image.shape[:2]
        
        # 过滤背景类
        classes_config = classes_config or self.get_classes_config()
        detection_config = {k: v for k, v in classes_config.items() if not v.get("is_background", False)}
        detection_prompts = None
        if prompts_config:
            detection_prompts = {k: v for k, v in prompts_config.items() if k in detection_config}
        
        # Step 1: RADIO水体分割 (使用water vs background对比)
        # 简化为water提取
        water_prompts = {
            "water": {
                "prompts": [
                    "water surface in natural environment",
                    "river or lake water body",
                    "flowing or standing water",
                ]
            }
        }
        
        # 计算水体热图
        heatmaps = self.text_classifier.compute_patch_similarity(
            image, {"water": {"prompts": water_prompts["water"]["prompts"]}}, None, self.input_size
        )
        
        if "water" not in heatmaps:
            return {}
        
        water_heatmap = heatmaps["water"]
        
        # 阈值化得到水体mask
        threshold = threshold or 0.35
        water_mask = water_heatmap > threshold
        
        # 后处理
        water_mask = self._postprocess_mask(water_mask, min_area=0.01)
        
        if not water_mask.any():
            return {}
        
        # Step 2: 轻量化分类器 (方案3)
        pred_class, confidence = self.classify_by_lightweight_clf(image, water_mask)
        
        # Step 3: 构造结果
        result = SegmentResult(
            class_name=pred_class,
            class_name_cn=self.CLASS_COLORS.get(pred_class, pred_class),
            mask=water_mask,
            area_ratio=water_mask.sum() / water_mask.size,
            score=confidence,
            water_iou=0.0,
            color_ok=True
        )
        
        return {pred_class: result}


    def visualize(
        self,
        image: np.ndarray,
        segments: Dict[str, SegmentResult],
        output_path: Optional[str] = None,
        font_path: Optional[str] = None,
    ) -> np.ndarray:
        """可视化分割结果"""
        from PIL import Image, ImageDraw, ImageFont

        vis = image.copy()
        h, w = image.shape[:2]

        if font_path is None:
            font_path = self._find_chinese_font()
        try:
            font = ImageFont.truetype(font_path, 24)
            font_small = ImageFont.truetype(font_path, 18)
        except Exception:
            font = ImageFont.load_default()
            font_small = font

        for name, seg in segments.items():
            color = self.CLASS_COLORS.get(name, (128, 128, 128))

            mask_uint8 = seg.mask.astype(np.uint8) * 255
            overlay = np.zeros_like(vis)
            overlay[mask_uint8 > 0] = color
            vis = cv2.addWeighted(vis, 0.6, overlay, 0.4, 0)

            contours, _ = cv2.findContours(
                mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(vis, contours, -1, color, 2)

            ys, xs = np.where(seg.mask)
            if len(ys) > 0:
                cy, cx = int(ys.mean()), int(xs.mean())
                label = f"{seg.class_name_cn} {seg.area_ratio:.1%}"
                score_label = f"conf: {seg.score:.1%}"

                vis_pil = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(vis_pil)

                bbox = draw.textbbox((0, 0), label, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                tx = max(5, min(cx - tw // 2, w - tw - 5))
                ty = max(5, min(cy - th - 10, h - th - 30))

                draw.rectangle(
                    [tx - 4, ty - 2, tx + tw + 4, ty + th + 24],
                    fill=(0, 0, 0, 180),
                )
                draw.text((tx + 1, ty + 1), label, font=font, fill=(0, 0, 0))
                draw.text((tx, ty), label, font=font, fill=(255, 255, 255))
                draw.text((tx + 1, ty + th + 3), score_label, font=font_small, fill=(200, 200, 200))

                vis = cv2.cvtColor(np.array(vis_pil), cv2.COLOR_RGB2BGR)

        if output_path:
            cv2.imwrite(output_path, vis)

        return vis

    @staticmethod
    def _find_chinese_font() -> str:
        """查找中文字体"""
        import platform
        candidates = [
            "C:/windows/Fonts/msyh.ttc",
            "C:/windows/Fonts/simhei.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        ] if platform.system() == "Windows" else [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return ""


# ─────────────────────────────────────────────────────────────────────────
# 兼容性别名
# ─────────────────────────────────────────────────────────────────────────

UnifiedWaterSegmentor = WaterQualitySegmentor
