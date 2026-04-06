#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取PeftCD论文复现的真实训练数据"""
import json
import subprocess

# PeftCD论文复现的训练历史文件
peftcd_file = '/workspace/peftcd_repro/peftcd_repro/artifacts/reports/peft_repro_dino_cd256_lora_fullalign_s42_history.json'

cmd = f"docker exec rcmt-training cat {peftcd_file}"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')

if result.returncode == 0:
    data = json.loads(result.stdout)

    print("=" * 80)
    print("PeftCD LoRA (CD256) 训练历史")
    print("=" * 80)
    print(f"数据结构: {list(data.keys())}")

    # 读取val数据
    val_data = data.get('val', [])
    print(f"\n总Epochs: {len(val_data)}")

    if val_data:
        print(f"\n{'Epoch':<6} {'Val IoU':<10} {'Val F1':<10} {'Val Loss':<10}")
        print("-" * 80)

        for i, val in enumerate(val_data[:30]):
            print(f"{i+1:<6} {val.get('iou', 0):<10.4f} {val.get('f1', 0):<10.4f} {val.get('loss', 0):<10.5f}")

        # 找最佳结果
        best_iou = max(val_data, key=lambda x: x.get('iou', 0))
        best_f1 = max(val_data, key=lambda x: x.get('f1', 0))

        print("\n" + "=" * 80)
        print("最佳结果:")
        print(f"最佳 IoU: {best_iou.get('iou', 0):.4f}")
        print(f"最佳 F1: {best_f1.get('f1', 0):.4f}")

        # Epoch 22 对比
        if len(val_data) >= 22:
            epoch22 = val_data[21]
            print("\n" + "=" * 80)
            print("Epoch 22 数据 (用于对比ACTA):")
            print(f"IoU: {epoch22.get('iou', 0):.4f}")
            print(f"F1: {epoch22.get('f1', 0):.4f}")
            print(f"Precision: {epoch22.get('precision', 0):.4f}")
            print(f"Recall: {epoch22.get('recall', 0):.4f}")

            # ACTA Epoch 22 数据
            acta_epoch22 = {
                'iou': 0.8375,
                'f1': 0.9115,
                'precision': 0.9099,
                'recall': 0.9132
            }

            print("\n" + "=" * 80)
            print("Epoch 22 对比: ACTA vs PeftCD")
            print("=" * 80)
            print(f"{'指标':<15} {'PeftCD':<15} {'ACTA':<15} {'差距':<15}")
            print("-" * 80)
            print(f"{'IoU':<15} {epoch22.get('iou', 0):<15.4f} {acta_epoch22['iou']:<15.4f} {acta_epoch22['iou']-epoch22.get('iou', 0):<+15.4f}")
            print(f"{'F1':<15} {epoch22.get('f1', 0):<15.4f} {acta_epoch22['f1']:<15.4f} {acta_epoch22['f1']-epoch22.get('f1', 0):<+15.4f}")
            print(f"{'Precision':<15} {epoch22.get('precision', 0):<15.4f} {acta_epoch22['precision']:<15.4f} {acta_epoch22['precision']-epoch22.get('precision', 0):<+15.4f}")
            print(f"{'Recall':<15} {epoch22.get('recall', 0):<15.4f} {acta_epoch22['recall']:<15.4f} {acta_epoch22['recall']-epoch22.get('recall', 0):<+15.4f}")

else:
    print(f"读取失败: {result.stderr}")
