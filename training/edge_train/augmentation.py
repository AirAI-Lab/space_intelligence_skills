"""
数据增强配置
支持Albumentations和Ultralytics原生增强
参考: https://docs.ultralytics.com/guides/yolo-data-augmentation/
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AugmentationConfig:
    """数据增强配置"""

    # 基础增强
    hsv_h: float = 0.015  # 色调增强范围
    hsv_s: float = 0.7    # 饱和度增强范围
    hsv_v: float = 0.4    # 明度增强范围

    # 几何变换
    degrees: float = 0.0   # 旋转角度 (+/- deg)
    translate: float = 0.1 # 平移 (+/- fraction)
    scale: float = 0.5     # 缩放 (gain)
    shear: float = 0.0     # 剪切角度 (+/- deg)
    perspective: float = 0.0  # 透视变换 (+/- fraction)

    # 翻转
    flipud: float = 0.0    # 上下翻转概率
    fliplr: float = 0.5    # 左右翻转概率

    # Mosaic和Mixup
    mosaic: float = 1.0    # Mosaic概率 (0-1)
    mixup: float = 0.0     # Mixup概率 (0-1)

    # Albumentations增强
    use_albumentations: bool = False
    albumentations_config: Dict[str, Any] = field(default_factory=dict)

    def to_ultralytics_dict(self) -> Dict[str, Any]:
        """转换为Ultralytics格式的超参数字典"""
        return {
            'hsv_h': self.hsv_h,
            'hsv_s': self.hsv_s,
            'hsv_v': self.hsv_v,
            'degrees': self.degrees,
            'translate': self.translate,
            'scale': self.scale,
            'shear': self.shear,
            'perspective': self.perspective,
            'flipud': self.flipud,
            'fliplr': self.fliplr,
            'mosaic': self.mosaic,
            'mixup': self.mixup,
        }

    def get_albumentations_pipeline(self):
        """获取Albumentations增强管道"""
        if not self.use_albumentations:
            return None

        try:
            import albumentations as A
        except ImportError:
            logger.warning("Albumentations未安装，跳过Albumentations增强")
            return None

        config = self.albumentations_config or {}

        # 构建增强管道
        transforms = []

        # 基础颜色变换
        transforms.append(
            A.RandomBrightnessContrast(
                brightness_limit=config.get('brightness_limit', 0.2),
                contrast_limit=config.get('contrast_limit', 0.2),
                p=0.5
            )
        )

        transforms.append(
            A.HueSaturationValue(
                hue_shift_limit=config.get('hue_shift_limit', 20),
                sat_shift_limit=config.get('sat_shift_limit', 30),
                val_shift_limit=config.get('val_shift_limit', 20),
                p=0.5
            )
        )

        # 高级噪声
        transforms.append(
            A.OneOf([
                A.GaussNoise(p=1.0),
                A.ISONoise(p=1.0),
                A.MultiplicativeNoise(p=1.0),
            ], p=config.get('noise_prob', 0.3))
        )

        # 模糊
        transforms.append(
            A.OneOf([
                A.MotionBlur(p=1.0),
                A.MedianBlur(p=1.0),
                A.GaussianBlur(p=1.0),
            ], p=config.get('blur_prob', 0.3))
        )

        # 几何变换
        transforms.append(
            A.ShiftScaleRotate(
                shift_limit=config.get('shift_limit', 0.1),
                scale_limit=config.get('scale_limit', 0.1),
                rotate_limit=config.get('rotate_limit', 15),
                p=0.5
            )
        )

        # 弹性变换
        transforms.append(
            A.ElasticTransform(
                alpha=config.get('elastic_alpha', 1),
                sigma=config.get('elastic_sigma', 50),
                alpha_affine=config.get('elastic_alpha_affine', 50),
                p=config.get('elastic_prob', 0.2)
            )
        )

        # 网格失真
        transforms.append(
            A.GridDistortion(
                num_steps=config.get('grid_num_steps', 5),
                distort_limit=config.get('grid_distort_limit', 0.3),
                p=config.get('grid_prob', 0.2)
            )
        )

        # CoarseDropout (模拟遮挡)
        transforms.append(
            A.CoarseDropout(
                max_holes=config.get('coarse_max_holes', 8),
                max_height=config.get('coarse_max_height', 32),
                max_width=config.get('coarse_max_width', 32),
                p=config.get('coarse_prob', 0.3)
            )
        )

        pipeline = A.Compose(
            transforms,
            bbox_params=A.BboxParams(
                format='yolo',
                label_fields=['class_labels'],
                min_visibility=config.get('min_visibility', 0.3)
            )
        )

        return pipeline

    def validate(self) -> List[str]:
        """验证配置参数是否合法"""
        errors = []

        # 检查范围
        if not 0 <= self.hsv_h <= 1:
            errors.append("hsv_h 必须在 [0, 1] 范围内")
        if not 0 <= self.hsv_s <= 1:
            errors.append("hsv_s 必须在 [0, 1] 范围内")
        if not 0 <= self.hsv_v <= 1:
            errors.append("hsv_v 必须在 [0, 1] 范围内")

        if not 0 <= self.flipud <= 1:
            errors.append("flipud 必须在 [0, 1] 范围内")
        if not 0 <= self.fliplr <= 1:
            errors.append("fliplr 必须在 [0, 1] 范围内")
        if not 0 <= self.mosaic <= 1:
            errors.append("mosaic 必须在 [0, 1] 范围内")
        if not 0 <= self.mixup <= 1:
            errors.append("mixup 必须在 [0, 1] 范围内")

        return errors


# 预定义增强策略
AUGMENTATION_PRESETS: Dict[str, AugmentationConfig] = {
    "none": AugmentationConfig(
        hsv_h=0.0,
        hsv_s=0.0,
        hsv_v=0.0,
        degrees=0.0,
        translate=0.0,
        scale=0.0,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.0,
        mosaic=0.0,
        mixup=0.0
    ),

    "light": AugmentationConfig(
        hsv_h=0.01,
        hsv_s=0.5,
        hsv_v=0.3,
        degrees=5.0,
        translate=0.05,
        scale=0.2,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.0
    ),

    "medium": AugmentationConfig(
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,
        translate=0.1,
        scale=0.5,
        shear=2.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1
    ),

    "heavy": AugmentationConfig(
        hsv_h=0.02,
        hsv_s=0.9,
        hsv_v=0.5,
        degrees=15.0,
        translate=0.2,
        scale=0.9,
        shear=5.0,
        perspective=0.001,
        fliplr=0.5,
        flipud=0.1,
        mosaic=1.0,
        mixup=0.15
    ),

    "classification": AugmentationConfig(
        hsv_h=0.01,
        hsv_s=0.5,
        hsv_v=0.4,
        degrees=15.0,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        use_albumentations=True,
        albumentations_config={
            'brightness_limit': 0.3,
            'contrast_limit': 0.3,
            'rotate_limit': 30
        }
    ),
}


def get_augmentation_config(preset: str = "medium") -> AugmentationConfig:
    """
    获取增强配置

    Args:
        preset: 预设名称 (none/light/medium/heavy/classification)

    Returns:
        AugmentationConfig 实例
    """
    return AUGMENTATION_PRESETS.get(preset, AUGMENTATION_PRESETS["medium"])


def create_custom_config(
    preset: str = "medium",
    **kwargs
) -> AugmentationConfig:
    """
    创建自定义增强配置

    Args:
        preset: 基础预设名称
        **kwargs: 要覆盖的参数

    Returns:
        AugmentationConfig 实例
    """
    base_config = get_augmentation_config(preset)

    for key, value in kwargs.items():
        if hasattr(base_config, key):
            setattr(base_config, key, value)

    return base_config
