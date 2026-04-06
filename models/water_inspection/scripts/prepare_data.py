"""
水利巡检 - 数据集准备工具

功能：
1. 格式转换（COCO/VOC -> YOLO）
2. 数据集划分（train/val/test）
3. 标注验证

作者: 空中智能体团队
日期: 2026-03-26
"""

import os
import cv2
import json
import yaml
import random
import shutil
import argparse
import numpy as np
from pathlib import Path
from tqdm import tqdm
from xml.etree import ElementTree as ET


class DatasetPreparer:
    """数据集准备器"""
    
    def __init__(self, project_name: str, project_dir: str):
        """
        初始化
        
        Args:
            project_name: 项目名称
            project_dir: 项目根目录
        """
        self.project_name = project_name
        self.project_dir = Path(project_dir)
        
        # 加载配置
        config_path = self.project_dir / "configs" / f"{project_name}.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 获取类别
        self.classes = self.config['yolo']['classes']
        self.class_names = {k: v['name'] for k, v in self.classes.items()}
        print(f"类别数量: {len(self.classes)}")
        print(f"类别列表: {list(self.class_names.values())}")
    
    def convert_coco_to_yolo(
        self,
        coco_json: str,
        output_dir: str,
        images_dir: str = None
    ):
        """
        COCO 格式转 YOLO 格式
        
        Args:
            coco_json: COCO 标注文件
            output_dir: 输出目录
            images_dir: 图像目录（可选，用于验证）
        """
        print(f"\n转换 COCO -> YOLO: {coco_json}")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        (output_path / "images").mkdir(exist_ok=True)
        (output_path / "labels").mkdir(exist_ok=True)
        
        # 读取 COCO
        with open(coco_json, 'r') as f:
            coco = json.load(f)
        
        # 构建类别映射
        categories = {cat['id']: cat['name'] for cat in coco['categories']}
        
        # 构建图像映射
        images = {img['id']: img for img in coco['images']}
        
        # 按图像分组标注
        annotations_by_image = {}
        for ann in coco['annotations']:
            img_id = ann['image_id']
            if img_id not in annotations_by_image:
                annotations_by_image[img_id] = []
            annotations_by_image[img_id].append(ann)
        
        # 转换
        success_count = 0
        
        for img_id, annotations in tqdm(annotations_by_image.items(), desc="转换中"):
            img_info = images[img_id]
            img_name = Path(img_info['file_name']).stem
            
            # 复制图像
            if images_dir:
                src_img = Path(images_dir) / img_info['file_name']
                if src_img.exists():
                    dst_img = output_path / "images" / src_img.name
                    shutil.copy(src_img, dst_img)
            
            # 转换标注
            label_path = output_path / "labels" / f"{img_name}.txt"
            
            with open(label_path, 'w') as f:
                img_w = img_info['width']
                img_h = img_info['height']
                
                for ann in annotations:
                    cat_id = ann['category_id']
                    cat_name = categories[cat_id]
                    
                    # 找到对应的 YOLO 类别ID
                    yolo_id = None
                    for k, v in self.class_names.items():
                        if v == cat_name:
                            yolo_id = k
                            break
                    
                    if yolo_id is None:
                        continue
                    
                    # COCO bbox: [x, y, w, h] (左上角 + 宽高)
                    # YOLO bbox: [cx, cy, w, h] (中心点 + 宽高，归一化)
                    x, y, w, h = ann['bbox']
                    
                    cx = (x + w / 2) / img_w
                    cy = (y + h / 2) / img_h
                    w_norm = w / img_w
                    h_norm = h / img_h
                    
                    f.write(f"{yolo_id} {cx:.6f} {cy:.6f} {w_norm:.6f} {h_norm:.6f}\n")
            
            success_count += 1
        
        print(f"转换完成: {success_count} 张图像")
    
    def split_dataset(
        self,
        images_dir: str,
        labels_dir: str,
        output_dir: str,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ):
        """
        划分数据集
        
        Args:
            images_dir: 图像目录
            labels_dir: 标注目录
            output_dir: 输出目录
            train_ratio: 训练集比例
            val_ratio: 验证集比例
            test_ratio: 测试集比例
        """
        print(f"\n划分数据集: {images_dir}")
        
        # 获取所有图像
        image_files = list(Path(images_dir).glob("*.jpg")) + \
                     list(Path(images_dir).glob("*.png"))
        
        print(f"总图像数: {len(image_files)}")
        
        # 打乱
        random.shuffle(image_files)
        
        # 划分
        n = len(image_files)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        
        train_files = image_files[:n_train]
        val_files = image_files[n_train:n_train + n_val]
        test_files = image_files[n_train + n_val:]
        
        print(f"训练集: {len(train_files)}")
        print(f"验证集: {len(val_files)}")
        print(f"测试集: {len(test_files)}")
        
        # 创建目录
        output_path = Path(output_dir)
        for split in ['train', 'val', 'test']:
            (output_path / "images" / split).mkdir(parents=True, exist_ok=True)
            (output_path / "labels" / split).mkdir(parents=True, exist_ok=True)
        
        # 复制文件
        def copy_files(files, split):
            for img_file in tqdm(files, desc=f"复制{split}"):
                # 复制图像
                dst_img = output_path / "images" / split / img_file.name
                shutil.copy(img_file, dst_img)
                
                # 复制标注
                label_file = Path(labels_dir) / f"{img_file.stem}.txt"
                if label_file.exists():
                    dst_label = output_path / "labels" / split / label_file.name
                    shutil.copy(label_file, dst_label)
        
        copy_files(train_files, 'train')
        copy_files(val_files, 'val')
        copy_files(test_files, 'test')
        
        # 生成 data.yaml
        data_yaml = {
            'path': str(output_path.absolute()),
            'train': 'images/train',
            'val': 'images/val',
            'test': 'images/test',
            'nc': len(self.classes),
            'names': self.class_names
        }
        
        yaml_path = output_path / "data.yaml"
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data_yaml, f, default_flow_style=False, allow_unicode=True)
        
        print(f"\n生成配置文件: {yaml_path}")
        print("划分完成！")
    
    def validate_annotations(self, data_dir: str):
        """
        验证标注
        
        Args:
            data_dir: 数据目录
        """
        print(f"\n验证标注: {data_dir}")
        
        data_path = Path(data_dir)
        
        # 检查每个 split
        for split in ['train', 'val', 'test']:
            images_dir = data_path / "images" / split
            labels_dir = data_path / "labels" / split
            
            if not images_dir.exists():
                continue
            
            # 统计
            total = 0
            valid = 0
            invalid = 0
            empty = 0
            
            for img_file in images_dir.glob("*"):
                if img_file.suffix not in ['.jpg', '.png', '.jpeg']:
                    continue
                
                total += 1
                
                label_file = labels_dir / f"{img_file.stem}.txt"
                
                if not label_file.exists():
                    empty += 1
                    continue
                
                # 验证标注格式
                with open(label_file, 'r') as f:
                    lines = f.readlines()
                
                if len(lines) == 0:
                    empty += 1
                    continue
                
                is_valid = True
                for line in lines:
                    parts = line.strip().split()
                    
                    if len(parts) < 5:
                        is_valid = False
                        break
                    
                    try:
                        class_id = int(parts[0])
                        cx, cy, w, h = map(float, parts[1:5])
                        
                        # 检查范围
                        if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 <= w <= 1 and 0 <= h <= 1):
                            is_valid = False
                            break
                        
                        # 检查类别
                        if class_id not in self.classes:
                            is_valid = False
                            break
                    except:
                        is_valid = False
                        break
                
                if is_valid:
                    valid += 1
                else:
                    invalid += 1
            
            print(f"\n{split}:")
            print(f"  总数: {total}")
            print(f"  有效: {valid}")
            print(f"  无效: {invalid}")
            print(f"  空标注: {empty}")
    
    def analyze_dataset(self, data_dir: str):
        """
        分析数据集
        
        Args:
            data_dir: 数据目录
        """
        print(f"\n分析数据集: {data_dir}")
        
        data_path = Path(data_dir)
        
        # 统计每个类别的数量
        class_counts = {k: 0 for k in self.classes.keys()}
        
        for split in ['train', 'val', 'test']:
            labels_dir = data_path / "labels" / split
            
            if not labels_dir.exists():
                continue
            
            for label_file in labels_dir.glob("*.txt"):
                with open(label_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            class_id = int(parts[0])
                            if class_id in class_counts:
                                class_counts[class_id] += 1
        
        # 打印结果
        print("\n类别分布:")
        for class_id, count in sorted(class_counts.items()):
            class_name = self.class_names[class_id]
            print(f"  {class_id}: {class_name:20s} - {count:5d} 个实例")
        
        # 可视化（保存到文件）
        self._visualize_distribution(class_counts, data_path / "class_distribution.png")
    
    def _visualize_distribution(self, class_counts: dict, output_path: str):
        """可视化类别分布"""
        try:
            import matplotlib.pyplot as plt
            
            names = [self.class_names[k] for k in sorted(class_counts.keys())]
            counts = [class_counts[k] for k in sorted(class_counts.keys())]
            
            plt.figure(figsize=(12, 6))
            plt.bar(range(len(names)), counts)
            plt.xticks(range(len(names)), names, rotation=45, ha='right')
            plt.xlabel('类别')
            plt.ylabel('实例数量')
            plt.title('数据集类别分布')
            plt.tight_layout()
            plt.savefig(output_path, dpi=150)
            plt.close()
            
            print(f"\n类别分布图已保存: {output_path}")
        except:
            pass


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="数据集准备工具")
    
    parser.add_argument("--project", type=str, required=True,
                       choices=["water_inspection", "park_monitoring", "construction_safety"])
    parser.add_argument("--project-dir", type=str, required=True)
    parser.add_argument("--mode", type=str, required=True,
                       choices=["convert", "split", "validate", "analyze"])
    
    # COCO 转换
    parser.add_argument("--coco-json", type=str, help="COCO 标注文件")
    parser.add_argument("--images-dir", type=str, help="图像目录")
    
    # 划分
    parser.add_argument("--input-images", type=str, help="输入图像目录")
    parser.add_argument("--input-labels", type=str, help="输入标注目录")
    parser.add_argument("--output-dir", type=str, help="输出目录")
    
    # 比例
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    
    args = parser.parse_args()
    
    # 初始化
    preparer = DatasetPreparer(args.project, args.project_dir)
    
    if args.mode == "convert":
        if not args.coco_json or not args.output_dir:
            print("错误: 需要 --coco-json 和 --output-dir")
            return
        
        preparer.convert_coco_to_yolo(
            coco_json=args.coco_json,
            output_dir=args.output_dir,
            images_dir=args.images_dir
        )
    
    elif args.mode == "split":
        if not args.input_images or not args.input_labels or not args.output_dir:
            print("错误: 需要 --input-images, --input-labels, --output-dir")
            return
        
        preparer.split_dataset(
            images_dir=args.input_images,
            labels_dir=args.input_labels,
            output_dir=args.output_dir,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio
        )
    
    elif args.mode == "validate":
        if not args.output_dir:
            print("错误: 需要 --output-dir")
            return
        
        preparer.validate_annotations(args.output_dir)
    
    elif args.mode == "analyze":
        if not args.output_dir:
            print("错误: 需要 --output-dir")
            return
        
        preparer.analyze_dataset(args.output_dir)


if __name__ == "__main__":
    main()
