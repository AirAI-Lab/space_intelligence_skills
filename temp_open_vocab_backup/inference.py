#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
开放词汇分割器 - C-RADIOv4

对外接口保持 OpenVocabSegmentor 类名不变，
内部使用 C-RADIOv4 + siglip2-g 实现零样本分割。
无 GPU 时回退到颜色阈值分割。

作者: 空中智能体团队
日期: 2026-04-01
"""

import numpy as np
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class OpenVocabSegmentor:
    """
    开放词汇分割器 (C-RADIOv4)

    优先使用 C-RADIOv4 backbone + siglip2-g 进行零样本语义分割。
    无 GPU 或模型不可用时，回退到基于颜色阈值的简单分割。
    """

    def __init__(
        self,
        config: Dict[str, Any],
        device: str = "cuda",
    ):
        """
        Args:
            config: 配置字典，包含 radio 段或 dinov3_sam3 段
            device: 推理设备
        """
        self.config = config
        self.device = device
        self._segmentor = None
        self._fallback = False

        # 提取类别配置
        self.classes_config = config.get("classes", {})

        # 推理参数
        self.threshold = config.get("inference", {}).get("threshold", 0.3)
        self.min_area = config.get("inference", {}).get("min_area", 0.01)
        self.input_size = config.get("inference", {}).get("input_size", 896)

        # 尝试加载 C-RADIOv4
        self._try_load_radio()

    def _try_load_radio(self):
        """尝试加载 C-RADIOv4 分割器"""
        try:
            from .radio_segmentor import CRadioV4Segmentor

            model_path = self.config.get("model", {}).get("path")
            prefer_online = self.config.get("model", {}).get("prefer_online", False)

            self._segmentor = CRadioV4Segmentor(
                model_path=model_path,
                device=self.device,
                input_size=self.input_size,
                prefer_online=prefer_online,
            )
            print("C-RADIOv4 分割器加载成功")

        except Exception as e:
            logger.warning(f"C-RADIOv4 加载失败，使用颜色阈值回退: {e}")
            self._segmentor = None
            self._fallback = True
            print(f"C-RADIOv4 不可用 ({e})，已启用颜色阈值回退")

    def segment(
        self,
        image: np.ndarray,
        classes: Optional[List[str]] = None,
    ) -> Dict[str, dict]:
        """
        开放词汇分割

        Args:
            image: BGR 图像 [H, W, 3]
            classes: 指定类别列表 (None = 全部)

        Returns:
            {class_name: {"mask": np.ndarray, "area": float, "score": float}}
        """
        if self._fallback:
            return self._segment_fallback(image, classes)

        # 过滤类别
        classes_config = self.classes_config
        if classes:
            classes_config = {k: v for k, v in classes_config.items() if k in classes}

        if not classes_config:
            return {}

        # C-RADIOv4 分割
        results = self._segmentor.segment(
            image, classes_config,
            threshold=self.threshold,
            min_area=self.min_area,
        )

        # 转换为统一输出格式
        output = {}
        for name, seg in results.items():
            output[name] = {
                "mask": seg.mask,
                "area": seg.area_ratio,
                "score": seg.score,
                "class_name_cn": seg.class_name_cn,
            }

        return output

    def segment_batch(
        self,
        images: List[np.ndarray],
        classes: Optional[List[str]] = None,
    ) -> List[Dict[str, dict]]:
        """批量分割"""
        if self._fallback:
            return [self._segment_fallback(img, classes) for img in images]

        classes_config = self.classes_config
        if classes:
            classes_config = {k: v for k, v in classes_config.items() if k in classes}

        batch_results = self._segmentor.segment_batch(
            images, classes_config,
            threshold=self.threshold,
            min_area=self.min_area,
        )

        outputs = []
        for results in batch_results:
            output = {}
            for name, seg in results.items():
                output[name] = {
                    "mask": seg.mask,
                    "area": seg.area_ratio,
                    "score": seg.score,
                    "class_name_cn": seg.class_name_cn,
                }
            outputs.append(output)

        return outputs

    # ── 颜色阈值回退 ──

    def _segment_fallback(
        self,
        image: np.ndarray,
        classes: Optional[List[str]] = None,
    ) -> Dict[str, dict]:
        """基于颜色阈值的简单分割 (无 GPU 回退)"""
        import cv2

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, w = image.shape[:2]

        # 颜色范围 (HSV)
        color_ranges = {
            "black_water": ([0, 0, 0], [180, 50, 50]),
            "green_water": ([35, 50, 50], [85, 255, 255]),
            "red_water": ([0, 50, 50], [10, 255, 255]),
            "milky_water": ([0, 0, 150], [180, 50, 240]),
            "dam_seepage": ([0, 0, 30], [180, 80, 120]),
        }

        target_classes = classes or list(color_ranges.keys())
        results = {}

        for class_name in target_classes:
            if class_name not in color_ranges:
                continue

            lower, upper = color_ranges[class_name]
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))

            # 形态学清理
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            mask_bool = mask > 0
            area_ratio = mask_bool.sum() / (h * w)

            if area_ratio < self.min_area:
                continue

            config = self.classes_config.get(class_name, {})
            results[class_name] = {
                "mask": mask_bool,
                "area": float(area_ratio),
                "score": float(area_ratio),
                "class_name_cn": config.get("zh", class_name),
            }

        return results


def main():
    """测试入口"""
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description="开放词汇分割器测试")
    parser.add_argument("--config", type=str, default="configs/water_inspection.yaml")
    parser.add_argument("--image", type=str, default=None)
    parser.add_argument("--device", type=str, default="cuda")
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 兼容旧配置格式
    radio_config = config.get("cloud", {}).get("radio", config.get("dinov3_sam3", {}))

    segmentor = OpenVocabSegmentor(radio_config, device=args.device)

    import cv2
    if args.image:
        image = cv2.imread(args.image)
    else:
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        image[:, :, 0] = 200
        image[100:300, 200:400, 1] = 180
        print("使用合成测试图像")

    results = segmentor.segment(image)
    print(f"\n分割结果: {len(results)} 个区域")
    for name, info in results.items():
        print(f"  {info['class_name_cn']} ({name}): 面积={info['area']:.1%}, 置信度={info['score']:.3f}")


if __name__ == "__main__":
    main()
