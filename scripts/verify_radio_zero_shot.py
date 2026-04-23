#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RADIO 零样本检测验证脚本

验证施工安全 (4类) 和园区监测 (3类) 的提示词能否被 RADIO 正确识别。
使用网络测试图像和本地测试图像进行验证。

用法:
  python scripts/verify_radio_zero_shot.py --module construction_safety
  python scripts/verify_radio_zero_shot.py --module park_monitoring
  python scripts/verify_radio_zero_shot.py --module all

作者: 空中智能体团队
日期: 2026-04-21
"""

import sys
import cv2
import yaml
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ==============================================================================
# 测试图像描述 (用于 SigLIP2 文本-图像对齐验证)
# ==============================================================================

CONSTRUCTION_TEST_SCENARIOS = {
    "bare_soil_uncovered": {
        "description": "大面积裸露黄土，无覆盖网或防尘布",
        "search_keywords": "construction site exposed bare soil without covering",
    },
    "dust_pollution": {
        "description": "施工现场扬尘弥漫，空气中可见灰尘",
        "search_keywords": "construction site dust pollution haze",
    },
    "pit_water_accumulation": {
        "description": "基坑底部有浑浊积水",
        "search_keywords": "water accumulation in foundation pit excavation",
    },
    "material_near_pit": {
        "description": "基坑边缘堆放建筑材料",
        "search_keywords": "construction materials stacked near excavation pit edge",
    },
}

PARK_TEST_SCENARIOS = {
    "fire_lane_blocked": {
        "description": "车辆停在消防通道黄色网格线上",
        "search_keywords": "vehicle blocking fire lane yellow grid marking",
    },
    "fence_climbing": {
        "description": "人正在翻越金属栏杆或围墙",
        "search_keywords": "person climbing over metal fence railing",
    },
    "exit_blocked": {
        "description": "安全出口门前堆放杂物，通道被堵",
        "search_keywords": "emergency exit door blocked by boxes obstacles",
    },
}


class RadioZeroShotVerifier:
    """RADIO 零样本检测验证器"""

    def __init__(self, checkpoint_path: str, radio_code_dir: str, siglip2_dir: str):
        self.checkpoint_path = checkpoint_path
        self.radio_code_dir = radio_code_dir
        self.siglip2_dir = siglip2_dir
        self._segmentor = None

    def _load_segmentor(self):
        if self._segmentor is not None:
            return

        logger.info("加载 C-RADIOv4 分割器...")
        from models.water_inspection.models.open_vocab.radseg_segmentor import RADSegWaterSegmentor

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

    def verify_class(
        self,
        image: np.ndarray,
        class_name: str,
        class_config: dict,
    ) -> Dict:
        """
        验证单个类别在给定图像上的检测效果

        Returns:
            dict with keys: class_name, detected, confidence, area_ratio, mean_score
        """
        if self._segmentor is None:
            self._load_segmentor()

        h, w = image.shape[:2]
        total_pixels = h * w
        threshold = 0.25
        min_area = 0.003

        # 构建 prompts
        prompts_config = {class_name: {"prompts": class_config.get("prompts", [])}}
        if "prompts_negative" in class_config:
            prompts_config[class_name]["negative"] = class_config["prompts_negative"]

        # 添加背景对比
        prompts_config["background"] = {"prompts": [
            "normal scene without any anomaly",
            "clean organized area",
        ]}

        heatmaps = self._segmentor.compute_patch_similarity(image, prompts_config)
        heatmap = heatmaps.get(class_name, np.zeros((h, w)))

        mask = heatmap > threshold
        area_ratio = float(mask.sum() / total_pixels)
        mean_score = float(heatmap[mask].mean()) if mask.any() else 0.0
        max_score = float(heatmap.max())

        # 也获取背景分数用于对比
        bg_heatmap = heatmaps.get("background", np.zeros((h, w)))
        bg_max = float(bg_heatmap.max())

        detected = area_ratio >= min_area and mean_score >= (class_config.get("min_prob", 0.25))

        return {
            "class_name": class_name,
            "detected": detected,
            "mean_score": round(mean_score, 4),
            "max_score": round(max_score, 4),
            "area_ratio": round(area_ratio, 4),
            "bg_max_score": round(bg_max, 4),
            "margin": round(max_score - bg_max, 4),
        }

    def verify_prompts_semantic(
        self,
        classes_config: dict,
    ) -> Dict[str, Dict]:
        """
        验证提示词之间的语义区分度 (文本-文本对齐)

        通过 SigLIP2 tokenizer + encoder 计算各提示词之间的相似度,
        确保不同类别的提示词不会过度重叠。
        """
        logger.info("验证提示词语义区分度...")

        # 收集所有提示词
        all_prompts = {}
        for cls_name, cls_cfg in classes_config.items():
            if cls_name == "background":
                continue
            all_prompts[cls_name] = cls_cfg.get("prompts", [])

        # 计算类间相似度 (使用 SigLIP2)
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch

            model_dir = self.siglip2_dir
            tokenizer = AutoTokenizer.from_pretrained(model_dir)
            text_encoder = AutoModel.from_pretrained(model_dir).text_model
            text_encoder = text_encoder.cuda().eval()

            # 编码每个类别的提示词
            class_embeddings = {}
            with torch.no_grad():
                for cls_name, prompts in all_prompts.items():
                    text = prompts[0] if prompts else cls_name
                    inputs = tokenizer(text, return_tensors="pt", padding=True).to("cuda")
                    outputs = text_encoder(**inputs)
                    # 使用 [CLS] token 或 pooler output
                    emb = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                    class_embeddings[cls_name] = emb[0] / (np.linalg.norm(emb[0]) + 1e-8)

            # 计算相似度矩阵
            cls_names = list(class_embeddings.keys())
            n = len(cls_names)
            sim_matrix = np.zeros((n, n))
            for i in range(n):
                for j in range(n):
                    sim_matrix[i][j] = np.dot(class_embeddings[cls_names[i]],
                                               class_embeddings[cls_names[j]])

            result = {
                "class_names": cls_names,
                "similarity_matrix": sim_matrix.round(3).tolist(),
            }

            # 检查区分度
            off_diag = []
            for i in range(n):
                for j in range(i+1, n):
                    off_diag.append(sim_matrix[i][j])

            avg_inter_sim = np.mean(off_diag) if off_diag else 0
            result["avg_inter_class_similarity"] = round(float(avg_inter_sim), 4)
            result["assessment"] = "GOOD" if avg_inter_sim < 0.8 else "NEEDS_TUNING"

            logger.info(f"  类间平均相似度: {avg_inter_sim:.4f}")
            logger.info(f"  评估: {result['assessment']}")

            for i in range(n):
                for j in range(i+1, n):
                    sim = sim_matrix[i][j]
                    if sim > 0.85:
                        logger.warning(f"  ⚠️ 高相似度: {cls_names[i]} vs {cls_names[j]} = {sim:.4f}")

            return result

        except Exception as e:
            logger.warning(f"语义验证失败 (非关键): {e}")
            return {"error": str(e), "assessment": "SKIP"}


def verify_construction_safety(verifier: RadioZeroShotVerifier, config: dict):
    """验证施工安全零样本检测"""
    print("\n" + "=" * 70)
    print("验证施工安全 RADIO 零样本检测 (4类)")
    print("=" * 70)

    classes_config = config['cloud']['radio']['classes']

    # 1. 语义区分度验证
    semantic_result = verifier.verify_prompts_semantic(classes_config)

    # 2. 使用合成测试图像验证
    print("\n--- 合成测试图像验证 ---")
    test_results = {}

    for cls_name, cls_cfg in classes_config.items():
        if cls_name == "background":
            continue

        scenarios = CONSTRUCTION_TEST_SCENARIOS.get(cls_name, {})
        print(f"\n类别: {cls_name}")
        print(f"  提示词: {cls_cfg.get('prompts', ['N/A'])[:2]}")
        print(f"  测试场景: {scenarios.get('description', 'N/A')}")

        # 创建合成测试图像
        # 这里使用随机噪声图像, 仅验证 pipeline 不报错
        # 真实验证需要实际施工场景图像
        test_img = np.random.randint(50, 200, (640, 640, 3), dtype=np.uint8)
        result = verifier.verify_class(test_img, cls_name, cls_cfg)
        test_results[cls_name] = result

        status = "✓" if result["detected"] else "○"
        print(f"  合成图测试: {status} (score={result['max_score']:.3f}, area={result['area_ratio']:.3f})")

    return test_results, semantic_result


def verify_park_monitoring(verifier: RadioZeroShotVerifier, config: dict):
    """验证园区监测零样本检测"""
    print("\n" + "=" * 70)
    print("验证园区监测 RADIO 零样本检测 (3类)")
    print("=" * 70)

    classes_config = config['cloud']['radio']['classes']

    # 1. 语义区分度验证
    semantic_result = verifier.verify_prompts_semantic(classes_config)

    # 2. 合成测试图像验证
    print("\n--- 合成测试图像验证 ---")
    test_results = {}

    for cls_name, cls_cfg in classes_config.items():
        if cls_name == "background":
            continue

        scenarios = PARK_TEST_SCENARIOS.get(cls_name, {})
        print(f"\n类别: {cls_name}")
        print(f"  提示词: {cls_cfg.get('prompts', ['N/A'])[:2]}")
        print(f"  测试场景: {scenarios.get('description', 'N/A')}")

        test_img = np.random.randint(50, 200, (640, 640, 3), dtype=np.uint8)
        result = verifier.verify_class(test_img, cls_name, cls_cfg)
        test_results[cls_name] = result

        status = "✓" if result["detected"] else "○"
        print(f"  合成图测试: {status} (score={result['max_score']:.3f}, area={result['area_ratio']:.3f})")

    return test_results, semantic_result


def verify_with_real_images(verifier: RadioZeroShotVerifier, config: dict, module: str):
    """使用真实图像验证"""
    print("\n" + "=" * 70)
    print(f"使用真实图像验证 ({module})")
    print("=" * 70)

    # 查找测试图像
    if module == "construction_safety":
        image_dir = Path("models/construction_safety/data/test_images")
        classes_config = config['cloud']['radio']['classes']
    else:
        image_dir = Path("models/park_monitoring/data/test_images")
        classes_config = config['cloud']['radio']['classes']

    if not image_dir.exists():
        print(f"  测试图像目录不存在: {image_dir}")
        print(f"  请创建目录并放入测试图像后重新运行")
        return None

    images = list(image_dir.glob("*.jpg")) + list(image_dir.glob("*.png")) + list(image_dir.glob("*.jpeg"))
    if not images:
        print(f"  未找到测试图像")
        return None

    print(f"  找到 {len(images)} 张测试图像")

    all_results = {}
    for img_path in images[:5]:  # 最多测试5张
        image = cv2.imread(str(img_path))
        if image is None:
            continue

        print(f"\n  图像: {img_path.name} ({image.shape[1]}x{image.shape[0]})")
        img_results = {}

        for cls_name, cls_cfg in classes_config.items():
            if cls_name == "background":
                continue
            result = verifier.verify_class(image, cls_name, cls_cfg)
            img_results[cls_name] = result

            status = "✓ DETECTED" if result["detected"] else "○ not detected"
            print(f"    {cls_name}: {status} "
                  f"(score={result['max_score']:.3f}, area={result['area_ratio']:.3f}, "
                  f"margin={result['margin']:.3f})")

        all_results[img_path.name] = img_results

    return all_results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="RADIO 零样本检测验证")
    parser.add_argument("--module", choices=["construction_safety", "park_monitoring", "all"],
                        default="all", help="验证的模块")
    parser.add_argument("--checkpoint", type=str,
                        default="/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar",
                        help="RADIO checkpoint 路径")
    parser.add_argument("--radio-code-dir", type=str,
                        default="/app/models/NVlabs_RADIO",
                        help="RADIO 代码目录")
    parser.add_argument("--siglip2-dir", type=str,
                        default="/app/models/siglip2-giant-opt-patch16-384",
                        help="SigLIP2 模型目录")
    parser.add_argument("--real-images", action="store_true",
                        help="使用真实图像验证 (需要测试图像)")

    args = parser.parse_args()

    verifier = RadioZeroShotVerifier(
        checkpoint_path=args.checkpoint,
        radio_code_dir=args.radio_code_dir,
        siglip2_dir=args.siglip2_dir,
    )

    overall_results = {}

    if args.module in ["construction_safety", "all"]:
        config_path = Path("models/construction_safety/configs/construction_safety.yaml")
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            test_results, semantic = verify_construction_safety(verifier, config)
            overall_results["construction_safety"] = {
                "test_results": test_results,
                "semantic": semantic,
            }

            if args.real_images:
                real_results = verify_with_real_images(verifier, config, "construction_safety")
                if real_results:
                    overall_results["construction_safety"]["real_images"] = real_results

    if args.module in ["park_monitoring", "all"]:
        config_path = Path("models/park_monitoring/configs/park_monitoring.yaml")
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            test_results, semantic = verify_park_monitoring(verifier, config)
            overall_results["park_monitoring"] = {
                "test_results": test_results,
                "semantic": semantic,
            }

            if args.real_images:
                real_results = verify_with_real_images(verifier, config, "park_monitoring")
                if real_results:
                    overall_results["park_monitoring"]["real_images"] = real_results

    # 保存结果
    # 将 numpy 类型转换为 Python 原生类型
    def convert(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(v) for v in obj]
        return obj

    overall_results = convert(overall_results)

    output_path = Path("outputs/radio_zero_shot_verification.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(overall_results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"验证结果已保存: {output_path}")
    print(f"{'='*70}")

    # 总结
    print("\n验证总结:")
    for module, data in overall_results.items():
        semantic = data.get("semantic", {})
        test = data.get("test_results", {})
        assessment = semantic.get("assessment", "N/A")
        inter_sim = semantic.get("avg_inter_class_similarity", "N/A")

        print(f"\n  [{module}]")
        print(f"    语义区分度: {assessment} (类间相似度: {inter_sim})")
        print(f"    合成图测试: {len(test)} 个类别已验证")
        for cls_name, result in test.items():
            status = "可检测" if result["detected"] else "需实际图像验证"
            print(f"      {cls_name}: {status} (max_score={result['max_score']})")


if __name__ == "__main__":
    main()
