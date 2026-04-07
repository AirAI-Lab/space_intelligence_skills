"""
水利巡检 - YOLOv8 训练脚本

功能：
- 训练 YOLOv8-Pose 模型
- 支持 11 类检测任务
- 自动保存最佳模型

作者: 空中智能体团队
日期: 2026-03-26
"""

import os
import yaml
import torch
import argparse
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO


class YOLOTrainer:
    """YOLOv8 训练器"""
    
    def __init__(self, config_path: str):
        """
        初始化训练器
        
        Args:
            config_path: 配置文件路径
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.training_config = self.config.get('training', {}).get('yolo', {})
        self.classes = self.config['yolo']['classes']
        
        print(f"训练配置:")
        print(f"  类别数量: {len(self.classes)}")
        print(f"  类别列表: {[v['name'] for v in self.classes.values()]}")
    
    def train(
        self,
        data_yaml: str,
        epochs: int = None,
        batch: int = None,
        imgsz: int = None,
        device: str = "cuda",
        resume: str = None,
        project: str = "runs/train",
        name: str = None
    ):
        """
        训练模型
        
        Args:
            data_yaml: 数据配置文件
            epochs: 训练轮数
            batch: 批次大小
            imgsz: 图像尺寸
            device: 设备 (cuda/cpu)
            resume: 恢复训练的 checkpoint
            project: 项目目录
            name: 实验名称
        """
        # 参数
        epochs = epochs or self.training_config.get('epochs', 200)
        batch = batch or self.training_config.get('batch', 16)
        imgsz = imgsz or self.training_config.get('imgsz', 640)
        
        if name is None:
            name = f"water_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print("\n" + "=" * 60)
        print("开始训练 YOLOv8-Pose")
        print("=" * 60)
        print(f"数据配置: {data_yaml}")
        print(f"训练轮数: {epochs}")
        print(f"批次大小: {batch}")
        print(f"图像尺寸: {imgsz}")
        print(f"设备: {device}")
        print(f"输出目录: {project}/{name}")
        print("=" * 60 + "\n")
        
        # 初始化模型
        if resume:
            print(f"从 checkpoint 恢复: {resume}")
            model = YOLO(resume)
        else:
            model_type = self.training_config.get('model_type', 'yolov8x-pose')
            print(f"使用预训练模型: {model_type}")
            model = YOLO(f"{model_type}.pt")
        
        # 训练参数
        train_params = {
            "data": data_yaml,
            "epochs": epochs,
            "batch": batch,
            "imgsz": imgsz,
            "device": device,
            "project": project,
            "name": name,
            "exist_ok": True,
            "verbose": True,
            
            # 优化器
            "optimizer": self.training_config.get('optimizer', 'AdamW'),
            "lr0": self.training_config.get('lr0', 0.001),
            "lrf": self.training_config.get('lrf', 0.01),
            "momentum": self.training_config.get('momentum', 0.937),
            "weight_decay": self.training_config.get('weight_decay', 0.0005),
            "warmup_epochs": self.training_config.get('warmup_epochs', 3),
            "patience": self.training_config.get('patience', 50),
            
            # 数据增强
            "hsv_h": self.training_config.get('augment', {}).get('hsv_h', 0.015),
            "hsv_s": self.training_config.get('augment', {}).get('hsv_s', 0.7),
            "hsv_v": self.training_config.get('augment', {}).get('hsv_v', 0.4),
            "degrees": self.training_config.get('augment', {}).get('degrees', 0),
            "translate": self.training_config.get('augment', {}).get('translate', 0.1),
            "scale": self.training_config.get('augment', {}).get('scale', 0.5),
            "fliplr": self.training_config.get('augment', {}).get('fliplr', 0.5),
            "mosaic": self.training_config.get('augment', {}).get('mosaic', 1.0),
            "mixup": self.training_config.get('augment', {}).get('mixup', 0.1),
        }
        
        # 开始训练
        results = model.train(**train_params)
        
        print("\n" + "=" * 60)
        print("训练完成！")
        print("=" * 60)
        print(f"最佳模型: {project}/{name}/weights/best.pt")
        print(f"最后模型: {project}/{name}/weights/last.pt")
        print("=" * 60)
        
        return results
    
    def validate(self, weights: str, data_yaml: str):
        """
        验证模型
        
        Args:
            weights: 权重路径
            data_yaml: 数据配置
        """
        print(f"\n验证模型: {weights}")
        
        model = YOLO(weights)
        results = model.val(data=data_yaml)
        
        print("\n验证结果:")
        print(f"  mAP@50:    {results.box.map50:.4f}")
        print(f"  mAP@50:95: {results.box.map:.4f}")
        print(f"  Precision: {results.box.mp:.4f}")
        print(f"  Recall:    {results.box.mr:.4f}")
        
        return results
    
    def export(self, weights: str, format: str = "onnx", simplify: bool = True):
        """
        导出模型
        
        Args:
            weights: 权重路径
            format: 导出格式 (onnx, torchscript, engine)
            simplify: 是否简化
        """
        print(f"\n导出模型: {weights} -> {format}")
        
        model = YOLO(weights)
        export_path = model.export(format=format, simplify=simplify)
        
        print(f"导出完成: {export_path}")
        return export_path


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="YOLOv8 训练脚本")
    
    parser.add_argument("--config", type=str, 
                       default="configs/water_inspection.yaml",
                       help="配置文件")
    parser.add_argument("--data", type=str, required=True,
                       help="数据配置文件 (data.yaml)")
    parser.add_argument("--mode", type=str, default="train",
                       choices=["train", "val", "export"],
                       help="运行模式")
    
    # 训练参数
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--resume", type=str, help="恢复训练")
    parser.add_argument("--project", type=str, default="runs/train")
    parser.add_argument("--name", type=str, help="实验名称")
    
    # 导出参数
    parser.add_argument("--weights", type=str, help="权重路径")
    parser.add_argument("--format", type=str, default="onnx",
                       choices=["onnx", "torchscript"])
    
    args = parser.parse_args()
    
    # 初始化
    trainer = YOLOTrainer(args.config)
    
    if args.mode == "train":
        trainer.train(
            data_yaml=args.data,
            epochs=args.epochs,
            batch=args.batch,
            imgsz=args.imgsz,
            device=args.device,
            resume=args.resume,
            project=args.project,
            name=args.name
        )
    
    elif args.mode == "val":
        if not args.weights:
            print("错误: 需要 --weights")
            return
        trainer.validate(args.weights, args.data)
    
    elif args.mode == "export":
        if not args.weights:
            print("错误: 需要 --weights")
            return
        trainer.export(args.weights, args.format)


if __name__ == "__main__":
    main()
