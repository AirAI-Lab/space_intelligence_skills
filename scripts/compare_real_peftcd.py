#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取PeftCD论文复现的真实训练数据"""
import json
import subprocess

# PeftCD论文复现的训练历史文件
peftcd_files = {
    'LoRA (CD256)': '/workspace/peftcd_repro/peftcd_repro/artifacts/reports/peft_repro_dino_cd256_lora_fullalign_s42_history.json',
    'Adapter (CD256)': '/workspace/peftcd_repro/peftcd_repro/artifacts/reports/peft_repro_dino_cd256_adapter_fullalign_s42_history.json',
    'LoRA (Raw637)': '/workspace/peftcd_repro/peftcd_repro/artifacts/reports/peft_repro_dino_raw637_lora_fullalign_s42_history.json',
    'Adapter (Raw637)': '/workspace/peftcd_repro/peftcd_repro/artifacts/reports/peft_repro_dino_raw637_adapter_fullalign_s42_history.json',
}

for name, filepath in peftcd_files.items():
    print("=" * 80)
    print(f"PeftCD {name} 训练历史")
    print("=" * 80)

    cmd = f"docker exec rcmt-training cat {filepath}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')

    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)

            # 检查数据结构
            if 'epochs' in data:
                epochs = data['epochs']
            elif isinstance(data, list):
                epochs = data
            else:
                print(f"未知数据格式: {list(data.keys())}")
                continue

            print(f"总Epochs: {len(epochs)}")

            # 显示前30个epoch
            print(f"\n{'Epoch':<6} {'Val IoU':<10} {'Val F1':<10} {'Val Loss':<10}")
            print("-" * 80)

            for i, e in enumerate(epochs[:30]):
                if 'val' in e:
                    val = e['val']
                    epoch_num = e.get('epoch', i+1)
                    print(f"{epoch_num:<6} {val.get('iou', 0):<10.4f} {val.get('f1', 0):<10.4f} {val.get('loss', 0):<10.5f}")

            # 找最佳结果
            if epochs:
                best_iou = max(epochs, key=lambda x: x.get('val', {}).get('iou', 0))
                best_f1 = max(epochs, key=lambda x: x.get('val', {}).get('f1', 0))

                print("\n" + "=" * 80)
                print("最佳结果:")
                print(f"最佳 IoU: {best_iou.get('val', {}).get('iou', 0):.4f} (Epoch {best_iou.get('epoch', 'N/A')})")
                print(f"最佳 F1: {best_f1.get('val', {}).get('f1', 0):.4f} (Epoch {best_f1.get('epoch', 'N/A')})")

                # Epoch 22 对比
                if len(epochs) >= 22:
                    epoch22 = epochs[21]
                    val22 = epoch22.get('val', {})
                    print("\n" + "=" * 80)
                    print("Epoch 22 数据 (用于对比ACTA):")
                    print(f"IoU: {val22.get('iou', 0):.4f}")
                    print(f"F1: {val22.get('f1', 0):.4f}")
                    print(f"Precision: {val22.get('precision', 0):.4f}")
                    print(f"Recall: {val22.get('recall', 0):.4f}")

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
    else:
        print(f"读取失败: {result.stderr}")

    print("\n")
