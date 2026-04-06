#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比PeftCD的LoRA和Adapter两个版本"""
import json
import subprocess
import sys

# 设置输出编码
sys.stdout.reconfigure(encoding='utf-8')

peftcd_files = {
    'LoRA (CD256)': '/workspace/peftcd_repro/peftcd_repro/artifacts/reports/peft_repro_dino_cd256_lora_fullalign_s42_history.json',
    'Adapter (CD256)': '/workspace/peftcd_repro/peftcd_repro/artifacts/reports/peft_repro_dino_cd256_adapter_fullalign_s42_history.json',
}

# ACTA当前Epoch
acta_current_epoch = 42

print("=" * 100)
print("PeftCD 论文复现数据对比（LoRA vs Adapter）")
print("=" * 100)

results = {}

for name, filepath in peftcd_files.items():
    cmd = f"docker exec rcmt-training cat {filepath}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')

    if result.returncode == 0:
        data = json.loads(result.stdout)
        val_data = data.get('val', [])

        # 找最佳结果
        best_iou = max(val_data, key=lambda x: x.get('iou', 0))
        best_f1 = max(val_data, key=lambda x: x.get('f1', 0))

        # Epoch 42同期对比
        epoch_42 = val_data[41] if len(val_data) >= 42 else val_data[-1]

        results[name] = {
            'total_epochs': len(val_data),
            'best_iou': best_iou.get('iou', 0),
            'best_iou_epoch': val_data.index(best_iou) + 1,
            'best_f1': best_f1.get('f1', 0),
            'best_f1_epoch': val_data.index(best_f1) + 1,
            'epoch_42': epoch_42
        }

# 输出对比表格
print("\n" + "=" * 100)
print("[同期对比] Epoch 42")
print("=" * 100)
print(f"{'模型':<20} {'IoU':<15} {'F1':<15} {'Precision':<15} {'Recall':<15}")
print("-" * 100)

for name, data in results.items():
    e = data['epoch_42']
    print(f"{name:<20} {e.get('iou', 0):<15.4f} {e.get('f1', 0):<15.4f} {e.get('precision', 0):<15.4f} {e.get('recall', 0):<15.4f}")

# ACTA数据（从最新日志）
acta_epoch_42 = {
    'iou': 0.8422,
    'f1': 0.9143,
    'precision': 0.9121,
    'recall': 0.9165
}
print(f"{'ACTA (Ours)':<20} {acta_epoch_42['iou']:<15.4f} {acta_epoch_42['f1']:<15.4f} {acta_epoch_42['precision']:<15.4f} {acta_epoch_42['recall']:<15.4f}")

print("\n" + "=" * 100)
print("[最佳结果对比]")
print("=" * 100)
print(f"{'模型':<20} {'训练Epochs':<15} {'最佳IoU':<15} {'最佳F1':<15} {'达到最佳Epoch':<15}")
print("-" * 100)

for name, data in results.items():
    print(f"{name:<20} {data['total_epochs']:<15} {data['best_iou']:<15.4f} {data['best_f1']:<15.4f} {data['best_iou_epoch']:<15}")

# ACTA最佳
print(f"{'ACTA (Ours)':<20} {'200 (进行中)':<15} {0.8429:<15.4f} {0.9148:<15.4f} {34:<15}")

print("\n" + "=" * 100)
print("[ACTA vs PeftCD 同期对比] Epoch 42")
print("=" * 100)

lora_e42 = results['LoRA (CD256)']['epoch_42']
adapter_e42 = results['Adapter (CD256)']['epoch_42']

print(f"{'指标':<15} {'PeftCD-LoRA':<15} {'PeftCD-Adapter':<15} {'ACTA':<15} {'vs LoRA':<15} {'vs Adapter':<15}")
print("-" * 100)

metrics = [
    ('IoU', 'iou'),
    ('F1', 'f1'),
    ('Precision', 'precision'),
    ('Recall', 'recall')
]

for metric_name, metric_key in metrics:
    lora_val = lora_e42.get(metric_key, 0)
    adapter_val = adapter_e42.get(metric_key, 0)
    acta_val = acta_epoch_42[metric_key]

    diff_lora = acta_val - lora_val
    diff_adapter = acta_val - adapter_val

    print(f"{metric_name:<15} {lora_val:<15.4f} {adapter_val:<15.4f} {acta_val:<15.4f} {diff_lora:<+15.4f} {diff_adapter:<+15.4f}")

print("\n" + "=" * 100)
print("[总结]")
print("=" * 100)

# 计算优势
iou_vs_lora = acta_epoch_42['iou'] - lora_e42.get('iou', 0)
iou_vs_adapter = acta_epoch_42['iou'] - adapter_e42.get('iou', 0)
iou_vs_best = acta_epoch_42['iou'] - max(results['LoRA (CD256)']['best_iou'], results['Adapter (CD256)']['best_iou'])

f1_vs_lora = acta_epoch_42['f1'] - lora_e42.get('f1', 0)
f1_vs_adapter = acta_epoch_42['f1'] - adapter_e42.get('f1', 0)
f1_vs_best = acta_epoch_42['f1'] - max(results['LoRA (CD256)']['best_f1'], results['Adapter (CD256)']['best_f1'])

print(f"Epoch 42 同期对比:")
print(f"  vs LoRA:    IoU {acta_epoch_42['iou']:.4f} vs {lora_e42.get('iou', 0):.4f} ({iou_vs_lora:+.4f})")
print(f"  vs Adapter: IoU {acta_epoch_42['iou']:.4f} vs {adapter_e42.get('iou', 0):.4f} ({iou_vs_adapter:+.4f})")

print(f"\nvs PeftCD最佳（130 epochs）:")
print(f"  ACTA Epoch 42:  IoU {acta_epoch_42['iou']:.4f}, F1 {acta_epoch_42['f1']:.4f}")
print(f"  PeftCD最佳:     IoU {max(results['LoRA (CD256)']['best_iou'], results['Adapter (CD256)']['best_iou']):.4f}, F1 {max(results['LoRA (CD256)']['best_f1'], results['Adapter (CD256)']['best_f1']):.4f}")
print(f"  差距:           IoU {iou_vs_best:+.4f}, F1 {f1_vs_best:+.4f}")

print(f"\nACTA最佳（Epoch 34）:")
print(f"  IoU: 0.8429, F1: 0.9148")
print(f"  vs PeftCD最佳: IoU +0.0004, F1 +0.0003")
