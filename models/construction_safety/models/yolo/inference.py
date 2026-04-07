"""
水利巡检 - YOLOv8 推理脚本

功能：
- 单张图像推理
- 批量推理
- 可视化结果
- 性能评估

作者: 空中智能体团队
日期: 2026-03-26
"""

import cv2
import yaml
import torch
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from ultralytics import YOLO
from dataclasses import dataclass
import json


@dataclass
class Detection:
    """检测结果"""
    class_id: int
    class_name: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    bbox_center: List[float]  # [cx, cy]
    bbox_area: float


class YOLOInference:
    """YOLOv8 推理器"""
    
    def __init__(self, config_path: str, weights: str = None, device: str = "cuda"):
        """
        初始化推理器
        
        Args:
            config_path: 配置文件路径
            weights: 权重路径
            device: 运行设备
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.device = device
        
        # 加载类别
        self.classes = self.config['yolo']['classes']
        self.class_names = {k: v['name'] for k, v in self.classes.items()}
        self.class_names_cn = {k: v['zh'] for k, v in self.classes.items()}
        
        # 加载模型
        if weights:
            self.model = YOLO(weights)
        else:
            weights_path = self.config['yolo']['model']['weights']
            if Path(weights_path).exists():
                self.model = YOLO(weights_path)
            else:
                print(f"警告: 权重文件不存在: {weights_path}")
                self.model = None
        
        print(f"推理器初始化完成")
        print(f"  类别数量: {len(self.classes)}")
        print(f"  设备: {device}")
    
    def infer_single(self, image_path: str, conf_threshold: float = 0.25) -> List[Detection]:
        """
        单张图像推理
        
        Args:
            image_path: 图像路径
            conf_threshold: 置信度阈值
        
        Returns:
            检测结果列表
        """
        if self.model is None:
            print("错误: 模型未加载")
            return []
        
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            print(f"错误: 无法读取图像: {image_path}")
            return []
        
        # 推理
        inference_config = self.config['yolo']['inference']
        
        results_list = self.model.predict(
            image,
            conf=conf_threshold,
            iou=inference_config.get('iou_threshold', 0.45),
            device=self.device,
            verbose=False
        )
        
        # 解析结果
        detections = []
        
        for result in results_list:
            for box in result.boxes:
                class_id = int(box.cls)
                confidence = float(box.conf)
                bbox = box.xyxy.tolist()[0]  # [x1, y1, x2, y2]
                
                # 计算中心点和面积
                cx = (bbox[0] + bbox[2]) / 2
                cy = (bbox[1] + bbox[3]) / 2
                area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                
                detection = Detection(
                    class_id=class_id,
                    class_name=self.class_names.get(class_id, f"class_{class_id}"),
                    confidence=confidence,
                    bbox=bbox,
                    bbox_center=[cx, cy],
                    bbox_area=area
                )
                detections.append(detection)
        
        return detections
    
    def infer_batch(self, image_dir: str, conf_threshold: float = 0.25) -> Dict[str, List[Detection]]:
        """
        批量推理
        
        Args:
            image_dir: 图像目录
            conf_threshold: 置信度阈值
        
        Returns:
            {图像路径: 检测结果}
        """
        image_dir = Path(image_dir)
        
        # 支持的格式
        extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        
        results = {}
        
        for ext in extensions:
            for img_path in image_dir.glob(f"*{ext}"):
                detections = self.infer_single(str(img_path), conf_threshold)
                results[str(img_path)] = detections
        
        return results
    
    def visualize(
        self,
        image_path: str,
        detections: List[Detection],
        output_path: str,
        show_labels: bool = True,
        show_conf: bool = True
    ):
        """
        可视化检测结果
        
        Args:
            image_path: 原始图像路径
            detections: 检测结果
            output_path: 输出路径
            show_labels: 显示标签
            show_conf: 显示置信度
        """
        image = cv2.imread(image_path)
        
        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det.bbox]
            
            # 根据类别选择颜色
            color = self._get_color(det.class_id)
            
            # 绘制边界框
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            
            # 绘制标签
            if show_labels or show_conf:
                label_parts = []
                
                if show_labels:
                    label_parts.append(det.class_name)
                
                if show_conf:
                    label_parts.append(f"{det.confidence:.2f}")
                
                label = " ".join(label_parts)
                
                # 文字背景
                (text_w, text_h), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                )
                cv2.rectangle(
                    image,
                    (x1, y1 - text_h - 8),
                    (x1 + text_w, y1),
                    color,
                    -1
                )
                
                # 绘制文字
                cv2.putText(
                    image,
                    label,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1
                )
        
        # 保存
        cv2.imwrite(output_path, image)
        print(f"可视化结果已保存: {output_path}")
    
    def evaluate(self, test_dir: str, conf_threshold: float = 0.25):
        """
        评估模型性能
        
        Args:
            test_dir: 测试数据目录
            conf_threshold: 置信度阈值
        """
        print("\n评估模型性能...")
        
        # 批量推理
        results = self.infer_batch(test_dir, conf_threshold)
        
        # 统计
        total_images = len(results)
        total_detections = sum(len(dets) for dets in results.values())
        
        # 按类别统计
        class_counts = {}
        for detections in results.values():
            for det in detections:
                class_name = det.class_name
                if class_name not in class_counts:
                    class_counts[class_name] = 0
                class_counts[class_name] += 1
        
        # 打印统计
        print(f"\n统计结果:")
        print(f"  总图像数: {total_images}")
        print(f"  总检测数: {total_detections}")
        print(f"  平均每张: {total_detections/total_images:.1f}")
        
        print(f"\n类别分布:")
        for class_name, count in sorted(class_counts.items(), key=lambda x: -x[1]):
            print(f"  {class_name:20s}: {count:5d}")
        
        return {
            "total_images": total_images,
            "total_detections": total_detections,
            "class_counts": class_counts
        }
    
    def export_results(self, results: Dict, output_json: str):
        """
        导出检测结果到 JSON
        
        Args:
            results: 检测结果
            output_json: 输出 JSON 路径
        """
        export_data = {}
        
        for img_path, detections in results.items():
            export_data[img_path] = [
                {
                    "class_id": det.class_id,
                    "class_name": det.class_name,
                    "confidence": det.confidence,
                    "bbox": det.bbox,
                    "bbox_center": det.bbox_center,
                    "bbox_area": det.bbox_area
                }
                for det in detections
            ]
        
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"结果已导出: {output_json}")
    
    def _get_color(self, class_id: int):
        """根据类别获取颜色"""
        # 定义颜色映射
        color_map = {
            # 人员行为 - 红色系
            0: (255, 0, 0),      # person - 蓝色
            1: (0, 0, 255),      # fishing - 红色
            2: (0, 0, 255),      # swimming - 红色
            3: (0, 0, 255),      # playing - 红色
            4: (0, 0, 255),      # intruding - 红色
            
            # 基础设施 - 黄色系
            5: (0, 255, 255),    # water_gauge - 黄色
            6: (0, 255, 255),    # outlet_pipe - 黄色
            7: (0, 165, 255),    # outlet_active - 橙色
            8: (0, 165, 255),    # pipe_damaged - 橙色
            9: (0, 165, 255),    # dam_seepage - 橙色
            
            # 目标监测 - 绿色系
            10: (0, 255, 0),     # boat - 绿色
            11: (0, 255, 0),     # floating_debris - 绿色
        }
        
        return color_map.get(class_id, (128, 128, 128))


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="YOLOv8 推理脚本")
    
    parser.add_argument("--config", type=str,
                       default="configs/water_inspection.yaml")
    parser.add_argument("--weights", type=str, required=True,
                       help="模型权重路径")
    parser.add_argument("--device", type=str, default="cuda")
    
    subparsers = parser.add_subparsers(dest="mode", help="运行模式")
    
    # 单张推理
    single_parser = subparsers.add_parser("single", help="单张图像推理")
    single_parser.add_argument("--image", type=str, required=True)
    single_parser.add_argument("--output", type=str, default="result.jpg")
    single_parser.add_argument("--conf", type=float, default=0.25)
    
    # 批量推理
    batch_parser = subparsers.add_parser("batch", help="批量推理")
    batch_parser.add_argument("--image-dir", type=str, required=True)
    batch_parser.add_argument("--output-dir", type=str, default="results")
    batch_parser.add_argument("--conf", type=float, default=0.25)
    
    # 评估
    eval_parser = subparsers.add_parser("evaluate", help="评估模型")
    eval_parser.add_argument("--test-dir", type=str, required=True)
    eval_parser.add_argument("--conf", type=float, default=0.25)
    
    args = parser.parse_args()
    
    # 初始化
    inferencer = YOLOInference(args.config, args.weights, args.device)
    
    if args.mode == "single":
        # 单张推理
        detections = inferencer.infer_single(args.image, args.conf)
        
        print(f"\n检测结果: {len(detections)} 个目标")
        for det in detections:
            print(f"  {det.class_name}: {det.confidence:.2f}")
        
        # 可视化
        inferencer.visualize(args.image, detections, args.output)
    
    elif args.mode == "batch":
        # 批量推理
        results = inferencer.infer_batch(args.image_dir, args.conf)
        
        print(f"\n批量推理完成: {len(results)} 张图像")
        
        # 保存结果
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        for img_path, detections in results.items():
            output_name = Path(img_path).stem + "_det.jpg"
            output_path = output_dir / output_name
            inferencer.visualize(img_path, detections, str(output_path))
        
        # 导出 JSON
        inferencer.export_results(results, str(output_dir / "results.json"))
    
    elif args.mode == "evaluate":
        # 评估
        inferencer.evaluate(args.test_dir, args.conf)


if __name__ == "__main__":
    main()
