#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取PeftCD训练历史并对比ACTA"""
import json
import subprocess

# 读取PeftCD训练历史 - 使用最完整的训练数据
peftcd_file = "/workspace/peftcd_repro/output/ablation_nodice_noboundary/artifacts/training_history.json"

cmd = f"docker exec rcmt-training cat {peftcd_file}"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')

if result.returncode == 0:
    data = json.loads(result.stdout)
    epochs = data['epochs']

    print("=" * 60)
    print("PeftCD 训练历史（前30个epochs）")
    print("=" * 60)
    print(f"{'Epoch':<6} {'Val IoU':<10} {'Val F1':<10} {'Val Loss':<10}")
    print("-" * 60)

    for i, e in enumerate(epochs[:30]):
        val = e['val']
        print(f"{i+1:<6} {val['iou']:<10.4f} {val['f1']:<10.4f} {val['loss']:<10.5f}")

    print("\n" + "=" * 60)
    print("最佳结果")
    print("=" * 60)

    best_iou = max(epochs, key=lambda x: x['val']['iou'])
    best_f1 = max(epochs, key=lambda x: x['val']['f1'])

    print(f"最佳 IoU: {best_iou['val']['iou']:.4f} (Epoch {best_iou['epoch']})")
    print(f"最佳 F1: {best_f1['val']['f1']:.4f} (Epoch {best_f1['epoch']})")

    print("\n" + "=" * 60)
    print("Epoch 22 对比（ACTA vs PeftCD）")
    print("=" * 60)

    # ACTA Epoch 22 数据
    acta_epoch22 = {
        'iou': 0.8375,
        'f1': 0.9115,
        'precision': 0.9099,
        'recall': 0.9132
    }

    # PeftCD Epoch 22 数据
    peftcd_epoch22 = epochs[21]['val']  # index 21 = epoch 22

    print(f"{'指标':<15} {'PeftCD':<15} {'ACTA':<15} {'差距':<15}")
    print("-" * 60)
    print(f"{'IoU':<15} {peftcd_epoch22['iou']:<15.4f} {acta_epoch22['iou']:<15.4f} {acta_epoch22['iou']-peftcd_epoch22['iou']:<+15.4f}")
    print(f"{'F1':<15} {peftcd_epoch22['f1']:<15.4f} {acta_epoch22['f1']:<15.4f} {acta_epoch22['f1']-peftcd_epoch22['f1']:<+15.4f}")
    print(f"{'Precision':<15} {peftcd_epoch22['precision']:<15.4f} {acta_epoch22['precision']:<15.4f} {acta_epoch22['precision']-peftcd_epoch22['precision']:<+15.4f}")
    print(f"{'Recall':<15} {peftcd_epoch22['recall']:<15.4f} {acta_epoch22['recall']:<15.4f} {acta_epoch22['recall']-peftcd_epoch22['recall']:<+15.4f}")

    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    if acta_epoch22['iou'] > peftcd_epoch22['iou']:
        diff = (acta_epoch22['iou'] - peftcd_epoch22['iou']) * 100
        print(f"✅ ACTA Epoch 22 的 IoU 领先 PeftCD Epoch 22 共 {diff:.2f}%")
    if acta_epoch22['f1'] > peftcd_epoch22['f1']:
        diff = (acta_epoch22['f1'] - peftcd_epoch22['f1']) * 100
        print(f"✅ ACTA Epoch 22 的 F1 领先 PeftCD Epoch 22 共 {diff:.2f}%")

else:
    print(f"读取失败: {result.stderr}")
