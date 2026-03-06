# -*- coding: utf-8 -*-
"""
RCMT-V3 数据集验证脚本

在多个数据集上验证模型效果，包括：
- LEVIR-CD (训练数据集)
- SYSU-CD (验证数据集)
- 其他变化检测数据集

使用方法:
    python validate_on_datasets.py --dataset LEVIR-CD --num-samples 5
    python validate_on_datasets.py --dataset SYSU-CD --num-samples 5
"""

import os
import sys
import argparse
import random
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent / "models" / "rcmt_v3"))

# 导入推理引擎
from inference import InferenceEngine


class DatasetValidator:
    """数据集验证器"""
    
    def __init__(self, config_path: str, model_path: str, device: str = "cuda"):
        """
        初始化验证器
        
        Args:
            config_path: 配置文件路径
            model_path: 模型权重路径
            device: 设备类型
        """
        self.device = device
        self.output_dir = Path(__file__).parent / "validation_results"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载模型
        print(f"🔧 加载模型...")
        self.engine = InferenceEngine(config_path, model_path, device)
        print(f"✅ 模型加载完成")
    
    def validate_levir_cd(self, data_root: str, num_samples: int = 5):
        """
        验证 LEVIR-CD 数据集
        
        Args:
            data_root: 数据集根目录
            num_samples: 验证样本数量
        """
        print(f"\n{'='*60}")
        print(f"📂 验证 LEVIR-CD 数据集")
        print(f"   数据目录: {data_root}")
        print(f"   样本数量: {num_samples}")
        print(f"{'='*60}\n")
        
        data_root = Path(data_root)
        
        # 检查数据集格式
        if (data_root / "test" / "A").exists():
            # ChangeFormer 格式: test/A, test/B, test/label
            test_dir = data_root / "test"
            images_a = sorted(list((test_dir / "A").glob("*.png")))
            images_b = sorted(list((test_dir / "B").glob("*.png")))
            labels = sorted(list((test_dir / "label").glob("*.png")))
        else:
            # 标准格式: A/, B/, label/, list/test.txt
            images_a = sorted(list((data_root / "A").glob("*.png")))
            images_b = sorted(list((data_root / "B").glob("*.png")))
            labels = sorted(list((data_root / "label").glob("*.png")))
        
        if len(images_a) == 0:
            print(f"❌ 未找到图像文件")
            return None
        
        # 随机选择样本
        indices = random.sample(range(len(images_a)), min(num_samples, len(images_a)))
        
        # 创建输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = self.output_dir / f"levir_cd_{timestamp}"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        for idx, i in enumerate(indices):
            print(f"\n[{idx+1}/{len(indices)}] 处理: {images_a[i].name}")
            
            # 读取图像
            image_t1 = cv2.imread(str(images_a[i]))
            image_t1 = cv2.cvtColor(image_t1, cv2.COLOR_BGR2RGB)
            image_t2 = cv2.imread(str(images_b[i]))
            image_t2 = cv2.cvtColor(image_t2, cv2.COLOR_BGR2RGB)
            gt_mask = cv2.imread(str(labels[i]), cv2.IMREAD_GRAYSCALE)
            gt_mask = (gt_mask > 127).astype(np.uint8)
            
            # 推理
            result = self.engine.infer_pair(image_t1, image_t2)
            pred_mask = result['mask']
            
            # 计算指标
            from models.rcmt_v3.inference import Evaluator
            metrics = Evaluator.compute_metrics(pred_mask, gt_mask)
            
            print(f"   F1: {metrics['f1']:.4f} | IoU: {metrics['iou']:.4f} | "
                  f"Precision: {metrics['precision']:.4f} | Recall: {metrics['recall']:.4f}")
            
            # 保存结果
            name = images_a[i].stem
            cv2.imwrite(str(save_dir / f"{name}_t1.png"), cv2.cvtColor(image_t1, cv2.COLOR_RGB2BGR))
            cv2.imwrite(str(save_dir / f"{name}_t2.png"), cv2.cvtColor(image_t2, cv2.COLOR_RGB2BGR))
            cv2.imwrite(str(save_dir / f"{name}_gt.png"), gt_mask * 255)
            cv2.imwrite(str(save_dir / f"{name}_pred.png"), pred_mask * 255)
            
            # 可视化
            self.engine.visualize(image_t1, image_t2, pred_mask, str(save_dir / f"{name}_vis.png"))
            
            # 对比可视化 (T1 | T2 | GT | Pred)
            comparison = self._create_comparison(image_t1, image_t2, gt_mask, pred_mask)
            cv2.imwrite(str(save_dir / f"{name}_comparison.png"), comparison)
            
            results.append({
                'name': name,
                'metrics': metrics,
                'inference_time': result['inference_time'],
            })
        
        # 保存汇总报告
        self._save_report(results, save_dir, "LEVIR-CD")
        
        return results
    
    def validate_sysu_cd(self, data_root: str, num_samples: int = 5):
        """
        验证 SYSU-CD 数据集
        
        Args:
            data_root: 数据集根目录
            num_samples: 验证样本数量
        """
        print(f"\n{'='*60}")
        print(f"📂 验证 SYSU-CD 数据集")
        print(f"   数据目录: {data_root}")
        print(f"   样本数量: {num_samples}")
        print(f"{'='*60}\n")
        
        data_root = Path(data_root)
        
        # SYSU-CD 格式
        if (data_root / "test" / "A").exists():
            test_dir = data_root / "test"
            images_a = sorted(list((test_dir / "A").glob("*.png")))
            images_b = sorted(list((test_dir / "B").glob("*.png")))
            labels = sorted(list((test_dir / "label").glob("*.png")))
        else:
            images_a = sorted(list((data_root / "A").glob("*.png")))
            images_b = sorted(list((data_root / "B").glob("*.png")))
            labels = sorted(list((data_root / "label").glob("*.png")))
        
        if len(images_a) == 0:
            print(f"❌ 未找到图像文件")
            return None
        
        # 随机选择样本
        indices = random.sample(range(len(images_a)), min(num_samples, len(images_a)))
        
        # 创建输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = self.output_dir / f"sysu_cd_{timestamp}"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        for idx, i in enumerate(indices):
            print(f"\n[{idx+1}/{len(indices)}] 处理: {images_a[i].name}")
            
            # 读取图像
            image_t1 = cv2.imread(str(images_a[i]))
            image_t1 = cv2.cvtColor(image_t1, cv2.COLOR_BGR2RGB)
            image_t2 = cv2.imread(str(images_b[i]))
            image_t2 = cv2.cvtColor(image_t2, cv2.COLOR_BGR2RGB)
            gt_mask = cv2.imread(str(labels[i]), cv2.IMREAD_GRAYSCALE)
            gt_mask = (gt_mask > 127).astype(np.uint8)
            
            # 推理
            result = self.engine.infer_pair(image_t1, image_t2)
            pred_mask = result['mask']
            
            # 计算指标
            from models.rcmt_v3.inference import Evaluator
            metrics = Evaluator.compute_metrics(pred_mask, gt_mask)
            
            print(f"   F1: {metrics['f1']:.4f} | IoU: {metrics['iou']:.4f} | "
                  f"Precision: {metrics['precision']:.4f} | Recall: {metrics['recall']:.4f}")
            
            # 保存结果
            name = images_a[i].stem
            cv2.imwrite(str(save_dir / f"{name}_t1.png"), cv2.cvtColor(image_t1, cv2.COLOR_RGB2BGR))
            cv2.imwrite(str(save_dir / f"{name}_t2.png"), cv2.cvtColor(image_t2, cv2.COLOR_RGB2BGR))
            cv2.imwrite(str(save_dir / f"{name}_gt.png"), gt_mask * 255)
            cv2.imwrite(str(save_dir / f"{name}_pred.png"), pred_mask * 255)
            
            # 可视化
            self.engine.visualize(image_t1, image_t2, pred_mask, str(save_dir / f"{name}_vis.png"))
            
            # 对比可视化
            comparison = self._create_comparison(image_t1, image_t2, gt_mask, pred_mask)
            cv2.imwrite(str(save_dir / f"{name}_comparison.png"), comparison)
            
            results.append({
                'name': name,
                'metrics': metrics,
                'inference_time': result['inference_time'],
            })
        
        # 保存汇总报告
        self._save_report(results, save_dir, "SYSU-CD")
        
        return results
    
    def _create_comparison(self, t1, t2, gt, pred):
        """创建对比可视化 (T1 | T2 | GT | Pred)"""
        h, w = t1.shape[:2]
        
        # 创建彩色掩码
        gt_colored = np.zeros((h, w, 3), dtype=np.uint8)
        gt_colored[gt == 1] = [255, 0, 0]  # 红色表示变化
        gt_colored[gt == 0] = [0, 255, 0]  # 绿色表示无变化
        
        pred_colored = np.zeros((h, w, 3), dtype=np.uint8)
        pred_colored[pred == 1] = [255, 0, 0]
        pred_colored[pred == 0] = [0, 255, 0]
        
        # 拼接
        comparison = np.hstack([t1, t2, gt_colored, pred_colored])
        
        # 添加标签
        label_height = 30
        labels = np.zeros((label_height, w * 4, 3), dtype=np.uint8)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(labels, "Time 1", (10, 20), font, 0.6, (255, 255, 255), 2)
        cv2.putText(labels, "Time 2", (w + 10, 20), font, 0.6, (255, 255, 255), 2)
        cv2.putText(labels, "Ground Truth", (w * 2 + 10, 20), font, 0.6, (255, 255, 255), 2)
        cv2.putText(labels, "Prediction", (w * 3 + 10, 20), font, 0.6, (255, 255, 255), 2)
        
        comparison_with_labels = np.vstack([labels, comparison])
        
        return comparison_with_labels
    
    def _save_report(self, results, save_dir, dataset_name):
        """保存汇总报告"""
        import json
        
        # 计算平均指标
        avg_metrics = {
            'f1': np.mean([r['metrics']['f1'] for r in results]),
            'iou': np.mean([r['metrics']['iou'] for r in results]),
            'precision': np.mean([r['metrics']['precision'] for r in results]),
            'recall': np.mean([r['metrics']['recall'] for r in results]),
        }
        
        avg_time = np.mean([r['inference_time'] for r in results])
        
        report = {
            'dataset': dataset_name,
            'num_samples': len(results),
            'avg_metrics': avg_metrics,
            'avg_inference_time': avg_time,
            'fps': 1.0 / avg_time,
            'samples': results,
        }
        
        # 保存 JSON
        with open(save_dir / "report.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        # 保存文本报告
        with open(save_dir / "report.txt", 'w') as f:
            f.write(f"{'='*60}\n")
            f.write(f"RCMT-V3 验证报告 - {dataset_name}\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"样本数量: {len(results)}\n")
            f.write(f"平均推理时间: {avg_time*1000:.2f} ms\n")
            f.write(f"平均 FPS: {1.0/avg_time:.2f}\n\n")
            f.write(f"平均指标:\n")
            f.write(f"  F1:        {avg_metrics['f1']:.4f}\n")
            f.write(f"  IoU:       {avg_metrics['iou']:.4f}\n")
            f.write(f"  Precision: {avg_metrics['precision']:.4f}\n")
            f.write(f"  Recall:    {avg_metrics['recall']:.4f}\n\n")
            f.write(f"详细结果:\n")
            f.write(f"{'-'*60}\n")
            for r in results:
                f.write(f"{r['name']}: ")
                f.write(f"F1={r['metrics']['f1']:.4f}, IoU={r['metrics']['iou']:.4f}, ")
                f.write(f"Time={r['inference_time']*1000:.2f}ms\n")
        
        print(f"\n{'='*60}")
        print(f"📊 验证完成 - {dataset_name}")
        print(f"{'='*60}")
        print(f"   平均 F1:        {avg_metrics['f1']:.4f}")
        print(f"   平均 IoU:       {avg_metrics['iou']:.4f}")
        print(f"   平均 Precision: {avg_metrics['precision']:.4f}")
        print(f"   平均 Recall:    {avg_metrics['recall']:.4f}")
        print(f"   平均推理时间:   {avg_time*1000:.2f} ms")
        print(f"   结果保存至:     {save_dir}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='RCMT-V3 数据集验证')
    parser.add_argument('--dataset', type=str, default='LEVIR-CD', 
                       choices=['LEVIR-CD', 'SYSU-CD'], help='数据集名称')
    parser.add_argument('--data-dir', type=str, required=True, help='数据集目录')
    parser.add_argument('--config', type=str, 
                       default='models/rcmt_v3/configs/rcmt_v3_swin.yaml',
                       help='配置文件路径')
    parser.add_argument('--model-path', type=str, 
                       default='checkpoints_swin_final/best_model.pth',
                       help='模型权重路径')
    parser.add_argument('--num-samples', type=int, default=5, help='验证样本数量')
    parser.add_argument('--device', type=str, default='cuda', help='设备类型')
    args = parser.parse_args()
    
    # 初始化验证器
    validator = DatasetValidator(args.config, args.model_path, args.device)
    
    # 验证数据集
    if args.dataset == 'LEVIR-CD':
        validator.validate_levir_cd(args.data_dir, args.num_samples)
    elif args.dataset == 'SYSU-CD':
        validator.validate_sysu_cd(args.data_dir, args.num_samples)


if __name__ == '__main__':
    main()
