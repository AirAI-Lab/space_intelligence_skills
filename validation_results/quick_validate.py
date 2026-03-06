# -*- coding: utf-8 -*-
"""
RCMT-V3 快速验证脚本

在 LEVIR-CD 数据集上随机抽取样本进行推理验证

使用方法:
    python quick_validate.py --num-samples 5
"""

import os
import sys
import random
import json
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
import torch

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "models" / "rcmt_v3"))

from inference import InferenceEngine, Evaluator


def quick_validate(
    data_root: str = "/data/LEVIR-CD256",
    config_path: str = "models/rcmt_v3/configs/rcmt_v3_swin.yaml",
    model_path: str = "checkpoints_swin_final/best_model.pth",
    num_samples: int = 5,
    device: str = "cuda",
    output_dir: str = None,
):
    """
    快速验证
    
    Args:
        data_root: 数据集根目录
        config_path: 配置文件路径
        model_path: 模型权重路径
        num_samples: 样本数量
        device: 设备
        output_dir: 输出目录
    """
    # 设置输出目录
    if output_dir is None:
        output_dir = Path(__file__).parent
    else:
        output_dir = Path(output_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = output_dir / f"validation_{timestamp}"
    save_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🚀 RCMT-V3 快速验证")
    print("=" * 60)
    print(f"数据目录: {data_root}")
    print(f"配置文件: {config_path}")
    print(f"模型权重: {model_path}")
    print(f"样本数量: {num_samples}")
    print(f"输出目录: {save_dir}")
    print("=" * 60)
    
    # 加载模型
    print("\n⏳ 加载模型...")
    engine = InferenceEngine(config_path, model_path, device)
    print("✅ 模型加载完成")
    
    # 查找数据集
    data_root = Path(data_root)
    
    # 尝试不同的数据集格式
    if (data_root / "test" / "A").exists():
        test_dir = data_root / "test"
        images_a = sorted(list((test_dir / "A").glob("*.png")))
        images_b = sorted(list((test_dir / "B").glob("*.png")))
        labels = sorted(list((test_dir / "label").glob("*.png")))
    elif (data_root / "A").exists():
        images_a = sorted(list((data_root / "A").glob("*.png")))
        images_b = sorted(list((data_root / "B").glob("*.png")))
        labels = sorted(list((data_root / "label").glob("*.png")))
    else:
        print(f"❌ 未找到数据集")
        return
    
    if len(images_a) == 0:
        print(f"❌ 未找到图像文件")
        return
    
    print(f"\n📂 找到 {len(images_a)} 个测试样本")
    
    # 随机选择
    indices = random.sample(range(len(images_a)), min(num_samples, len(images_a)))
    
    results = []
    
    print(f"\n🔍 开始推理...\n")
    
    for idx, i in enumerate(indices):
        print(f"[{idx+1}/{len(indices)}] {images_a[i].name}")
        
        # 读取图像
        t1 = cv2.imread(str(images_a[i]))
        t1 = cv2.cvtColor(t1, cv2.COLOR_BGR2RGB)
        t2 = cv2.imread(str(images_b[i]))
        t2 = cv2.cvtColor(t2, cv2.COLOR_BGR2RGB)
        gt = cv2.imread(str(labels[i]), cv2.IMREAD_GRAYSCALE)
        gt = (gt > 127).astype(np.uint8)
        
        # 推理
        result = engine.infer_pair(t1, t2)
        pred = result['mask']
        
        # 计算指标
        metrics = Evaluator.compute_metrics(pred, gt)
        
        print(f"   F1: {metrics['f1']:.4f} | IoU: {metrics['iou']:.4f} | "
              f"Prec: {metrics['precision']:.4f} | Rec: {metrics['recall']:.4f}")
        
        # 保存结果
        name = images_a[i].stem
        
        # 保存单张结果
        cv2.imwrite(str(save_dir / f"{name}_t1.png"), cv2.cvtColor(t1, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(save_dir / f"{name}_t2.png"), cv2.cvtColor(t2, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(save_dir / f"{name}_gt.png"), gt * 255)
        cv2.imwrite(str(save_dir / f"{name}_pred.png"), pred * 255)
        
        # 创建对比图 (T1 | T2 | GT | Pred)
        h, w = t1.shape[:2]
        
        # 彩色掩码
        gt_color = np.zeros((h, w, 3), dtype=np.uint8)
        gt_color[gt == 1] = [0, 0, 255]  # 红色 = 变化
        gt_color[gt == 0] = [0, 255, 0]  # 绿色 = 无变化
        
        pred_color = np.zeros((h, w, 3), dtype=np.uint8)
        pred_color[pred == 1] = [0, 0, 255]
        pred_color[pred == 0] = [0, 255, 0]
        
        # 添加边界区分
        border = 5
        border_color = [255, 255, 255]
        
        t1_b = cv2.copyMakeBorder(t1, 0, 0, 0, border, cv2.BORDER_CONSTANT, border_color)
        t2_b = cv2.copyMakeBorder(t2, 0, 0, 0, border, cv2.BORDER_CONSTANT, border_color)
        gt_b = cv2.copyMakeBorder(gt_color, 0, 0, 0, border, cv2.BORDER_CONSTANT, border_color)
        
        comparison = np.hstack([t1_b, t2_b, gt_b, pred_color])
        
        # 添加标签
        label_h = 30
        labels_img = np.zeros((label_h, comparison.shape[1], 3), dtype=np.uint8)
        cv2.putText(labels_img, "Time 1", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(labels_img, "Time 2", (w + border + 10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(labels_img, "Ground Truth", (2 * (w + border) + 10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(labels_img, "Prediction", (3 * (w + border) + 10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        final = np.vstack([labels_img, comparison])
        cv2.imwrite(str(save_dir / f"{name}_comparison.png"), final)
        
        # 保存可视化
        engine.visualize(t1, t2, pred, str(save_dir / f"{name}_vis.png"))
        
        results.append({
            'name': name,
            'metrics': metrics,
            'inference_time': result['inference_time'],
        })
    
    # 计算平均值
    avg_f1 = np.mean([r['metrics']['f1'] for r in results])
    avg_iou = np.mean([r['metrics']['iou'] for r in results])
    avg_prec = np.mean([r['metrics']['precision'] for r in results])
    avg_rec = np.mean([r['metrics']['recall'] for r in results])
    avg_time = np.mean([r['inference_time'] for r in results])
    
    # 保存报告
    report = {
        'timestamp': timestamp,
        'num_samples': len(results),
        'avg_f1': avg_f1,
        'avg_iou': avg_iou,
        'avg_precision': avg_prec,
        'avg_recall': avg_rec,
        'avg_inference_time_ms': avg_time * 1000,
        'fps': 1.0 / avg_time,
        'samples': results,
    }
    
    with open(save_dir / "report.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("📊 验证摘要")
    print("=" * 60)
    print(f"样本数量:       {len(results)}")
    print(f"平均 F1:        {avg_f1:.4f}")
    print(f"平均 IoU:       {avg_iou:.4f}")
    print(f"平均 Precision: {avg_prec:.4f}")
    print(f"平均 Recall:    {avg_rec:.4f}")
    print(f"平均推理时间:   {avg_time*1000:.2f} ms")
    print(f"平均 FPS:       {1.0/avg_time:.2f}")
    print(f"\n结果保存至:     {save_dir}")
    print("=" * 60)
    
    return report


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='RCMT-V3 快速验证')
    parser.add_argument('--data-dir', type=str, default='/data/LEVIR-CD256', help='数据集目录')
    parser.add_argument('--config', type=str, default='models/rcmt_v3/configs/rcmt_v3_swin.yaml', help='配置文件')
    parser.add_argument('--model-path', type=str, default='checkpoints_swin_final/best_model.pth', help='模型权重')
    parser.add_argument('--num-samples', type=int, default=5, help='样本数量')
    parser.add_argument('--device', type=str, default='cuda', help='设备')
    parser.add_argument('--output-dir', type=str, default=None, help='输出目录')
    
    args = parser.parse_args()
    
    quick_validate(
        data_root=args.data_dir,
        config_path=args.config,
        model_path=args.model_path,
        num_samples=args.num_samples,
        device=args.device,
        output_dir=args.output_dir,
    )
