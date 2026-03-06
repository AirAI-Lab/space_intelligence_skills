#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成论文图片
Generate Paper Figures

生成以下图片:
1. 网络架构图
2. 结果对比表
3. 消融实验图
4. 可视化结果

作者: RCMT-V3 Team
日期: 2026-03-05
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import json
import os
from pathlib import Path


def create_architecture_diagram(output_path='figures/architecture/RCMT_V3_Architecture.pdf'):
    """创建网络架构图"""
    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # 标题
    ax.text(8, 9.5, 'RCMT-V3: Hybrid CNN-Transformer Network with Bidirectional Temporal Fusion',
            ha='center', va='top', fontsize=16, fontweight='bold')
    
    # ========== 输入层 ==========
    # T1输入
    t1_box = FancyBboxPatch((1, 7), 2, 1, boxstyle="round,pad=0.1",
                            facecolor='lightblue', edgecolor='black', linewidth=2)
    ax.add_patch(t1_box)
    ax.text(2, 7.5, 'T1 Image\n(256×256×3)', ha='center', va='center', fontsize=10)
    
    # T2输入
    t2_box = FancyBboxPatch((1, 5), 2, 1, boxstyle="round,pad=0.1",
                            facecolor='lightblue', edgecolor='black', linewidth=2)
    ax.add_patch(t2_box)
    ax.text(2, 5.5, 'T2 Image\n(256×256×3)', ha='center', va='center', fontsize=10)
    
    # ========== CNN编码器 (Stage 1-2) ==========
    # T1 CNN
    cnn1_box = FancyBboxPatch((4, 7), 2.5, 1, boxstyle="round,pad=0.1",
                              facecolor='lightgreen', edgecolor='darkgreen', linewidth=2)
    ax.add_patch(cnn1_box)
    ax.text(5.25, 7.5, 'CNN Encoder\n(ResNet Stage 1-2)\n64→128 channels',
            ha='center', va='center', fontsize=9)
    
    # T2 CNN
    cnn2_box = FancyBboxPatch((4, 5), 2.5, 1, boxstyle="round,pad=0.1",
                              facecolor='lightgreen', edgecolor='darkgreen', linewidth=2)
    ax.add_patch(cnn2_box)
    ax.text(5.25, 5.5, 'CNN Encoder\n(ResNet Stage 1-2)\n64→128 channels',
            ha='center', va='center', fontsize=9)
    
    # ========== Transformer编码器 (Stage 3-4) ==========
    # T1 Transformer
    trans1_box = FancyBboxPatch((7.5, 7), 2.5, 1, boxstyle="round,pad=0.1",
                                facecolor='lightyellow', edgecolor='orange', linewidth=2)
    ax.add_patch(trans1_box)
    ax.text(8.75, 7.5, 'Transformer\n(Swin Stage 3-4)\n256→512 channels',
            ha='center', va='center', fontsize=9)
    
    # T2 Transformer
    trans2_box = FancyBboxPatch((7.5, 5), 2.5, 1, boxstyle="round,pad=0.1",
                                facecolor='lightyellow', edgecolor='orange', linewidth=2)
    ax.add_patch(trans2_box)
    ax.text(8.75, 5.5, 'Transformer\n(Swin Stage 3-4)\n256→512 channels',
            ha='center', va='center', fontsize=9)
    
    # ========== 双向时序融合 (BTF) ==========
    btf_box = FancyBboxPatch((11, 5.5), 3, 2, boxstyle="round,pad=0.1",
                             facecolor='lightcoral', edgecolor='red', linewidth=3)
    ax.add_patch(btf_box)
    ax.text(12.5, 6.5, 'Bidirectional\nTemporal Fusion\n(BTF Module)\n\nT1↔T2 Attention',
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # ========== 解码器 ==========
    decoder_box = FancyBboxPatch((11, 2), 3, 2.5, boxstyle="round,pad=0.1",
                                 facecolor='lightgray', edgecolor='black', linewidth=2)
    ax.add_patch(decoder_box)
    ax.text(12.5, 3.25, 'Multi-Scale\nDecoder\n\nUpsample ×4\n512→32→1',
            ha='center', va='center', fontsize=9)
    
    # ========== 输出 ==========
    output_box = FancyBboxPatch((11, 0.5), 3, 1, boxstyle="round,pad=0.1",
                                facecolor='white', edgecolor='blue', linewidth=2)
    ax.add_patch(output_box)
    ax.text(12.5, 1, 'Change Map\n(256×256×1)', ha='center', va='center', fontsize=10)
    
    # ========== 连接箭头 ==========
    # 输入到CNN
    ax.annotate('', xy=(4, 7.5), xytext=(3, 7.5),
                arrowprops=dict(arrowstyle='->', color='black', lw=2))
    ax.annotate('', xy=(4, 5.5), xytext=(3, 5.5),
                arrowprops=dict(arrowstyle='->', color='black', lw=2))
    
    # CNN到Transformer
    ax.annotate('', xy=(7.5, 7.5), xytext=(6.5, 7.5),
                arrowprops=dict(arrowstyle='->', color='black', lw=2))
    ax.annotate('', xy=(7.5, 5.5), xytext=(6.5, 5.5),
                arrowprops=dict(arrowstyle='->', color='black', lw=2))
    
    # Transformer到BTF
    ax.annotate('', xy=(11, 7), xytext=(10, 7.5),
                arrowprops=dict(arrowstyle='->', color='red', lw=2))
    ax.annotate('', xy=(11, 6), xytext=(10, 5.5),
                arrowprops=dict(arrowstyle='->', color='red', lw=2))
    
    # BTF到解码器
    ax.annotate('', xy=(12.5, 4.5), xytext=(12.5, 5.5),
                arrowprops=dict(arrowstyle='->', color='black', lw=2))
    
    # 解码器到输出
    ax.annotate('', xy=(12.5, 1.5), xytext=(12.5, 2),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    
    # ========== 图例 ==========
    legend_elements = [
        mpatches.Patch(facecolor='lightblue', edgecolor='black', label='Input'),
        mpatches.Patch(facecolor='lightgreen', edgecolor='darkgreen', label='CNN Encoder'),
        mpatches.Patch(facecolor='lightyellow', edgecolor='orange', label='Transformer Encoder'),
        mpatches.Patch(facecolor='lightcoral', edgecolor='red', label='Bidirectional Fusion (Ours)'),
        mpatches.Patch(facecolor='lightgray', edgecolor='black', label='Decoder'),
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=9)
    
    plt.tight_layout()
    
    # 保存
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.replace('.pdf', '.png'), dpi=300, bbox_inches='tight')
    print(f"[OK] Architecture diagram saved to {output_path}")
    
    plt.close()


def create_comparison_table(
    results_path='experiments/rcmt_v3_optimized_results.json',
    output_path='figures/results/Comparison_Table.pdf'
):
    """创建结果对比表"""
    # 加载结果
    with open(results_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # 准备数据
    methods = ['FC-EF', 'FC-Siam', 'SNUNet', 'BIT', 'ChangeFormer', 'TinyCD', 'Ours (Hybrid)']
    data = []
    
    for method in results['sota_comparison']:
        data.append([
            method['method'],
            method['year'],
            method['f1'],
            method['iou'],
            method['params_M'],
            method['fps']
        ])
    
    # 添加我们的方法
    our_method = results['main_results']['our_method']
    data.append([
        our_method['model'],
        2026,
        our_method['f1'],
        our_method['iou'],
        our_method['params_M'],
        our_method['fps']
    ])
    
    # 创建表格
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    ax.axis('off')
    
    columns = ['Method', 'Year', 'F1 (%)', 'IoU (%)', 'Params (M)', 'FPS']
    
    table = ax.table(
        cellText=data,
        colLabels=columns,
        loc='center',
        cellLoc='center',
        colColours=['#40466e'] * len(columns),
    )
    
    # 设置样式
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)
    
    # 标题
    ax.text(0.5, 0.95, 'Table I: Performance Comparison on LEVIR-CD Test Set',
            ha='center', va='top', fontsize=14, fontweight='bold', transform=ax.transAxes)
    
    # 高亮我们的方法
    for j in range(len(columns)):
        table[(len(data), j)].set_facecolor('#ffff99')
    
    plt.tight_layout()
    
    # 保存
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.replace('.pdf', '.png'), dpi=300, bbox_inches='tight')
    print(f"[OK] Comparison table saved to {output_path}")
    
    plt.close()


def create_ablation_figure(
    results_path='experiments/rcmt_v3_optimized_results.json',
    output_path='figures/results/Ablation_Study.pdf'
):
    """创建消融实验图"""
    # 加载结果
    with open(results_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # ========== 优化策略消融 ==========
    ax1 = axes[0]
    opt_data = results['ablation_studies']['optimization_strategy']
    configs = [d['config'].replace('+ ', '\n+ ') for d in opt_data]
    f1_scores = [d['f1'] for d in opt_data]
    
    bars1 = ax1.bar(range(len(configs)), f1_scores, color='steelblue', alpha=0.7)
    ax1.set_xticks(range(len(configs)))
    ax1.set_xticklabels(configs, rotation=45, ha='right', fontsize=8)
    ax1.set_ylabel('F1 Score (%)', fontsize=10)
    ax1.set_title('(a) Optimization Strategy Ablation', fontsize=11, fontweight='bold')
    ax1.set_ylim([87, 91])
    ax1.grid(axis='y', alpha=0.3)
    
    # 添加数值标签
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=8)
    
    # ========== 时序融合消融 ==========
    ax2 = axes[1]
    fusion_data = results['ablation_studies']['temporal_fusion']
    methods = [d['method'].replace('(', '\n(') for d in fusion_data]
    f1_scores = [d['f1'] for d in fusion_data]
    
    colors = ['lightgray'] * (len(methods) - 1) + ['lightcoral']
    bars2 = ax2.bar(range(len(methods)), f1_scores, color=colors, alpha=0.7)
    ax2.set_xticks(range(len(methods)))
    ax2.set_xticklabels(methods, rotation=45, ha='right', fontsize=8)
    ax2.set_ylabel('F1 Score (%)', fontsize=10)
    ax2.set_title('(b) Temporal Fusion Ablation', fontsize=11, fontweight='bold')
    ax2.set_ylim([86, 91])
    ax2.grid(axis='y', alpha=0.3)
    
    # 添加数值标签
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=8)
    
    # ========== 架构组件消融 ==========
    ax3 = axes[2]
    arch_data = results['ablation_studies']['architecture_components']
    configs = [d['config'].replace('(', '\n(') for d in arch_data]
    f1_scores = [d['f1'] for d in arch_data]
    
    colors = ['lightgray'] * (len(configs) - 1) + ['lightgreen']
    bars3 = ax3.bar(range(len(configs)), f1_scores, color=colors, alpha=0.7)
    ax3.set_xticks(range(len(configs)))
    ax3.set_xticklabels(configs, rotation=45, ha='right', fontsize=8)
    ax3.set_ylabel('F1 Score (%)', fontsize=10)
    ax3.set_title('(c) Architecture Component Ablation', fontsize=11, fontweight='bold')
    ax3.set_ylim([88, 91])
    ax3.grid(axis='y', alpha=0.3)
    
    # 添加数值标签
    for bar in bars3:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    
    # 保存
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.replace('.pdf', '.png'), dpi=300, bbox_inches='tight')
    print(f"[OK] Ablation study figure saved to {output_path}")
    
    plt.close()


def generate_all_figures():
    """生成所有论文图片"""
    print("="*60)
    print("Generating RCMT-V3 Paper Figures")
    print("="*60)
    
    # 1. 架构图
    print("\n[1/3] Creating architecture diagram...")
    create_architecture_diagram()
    
    # 2. 结果对比表
    print("\n[2/3] Creating comparison table...")
    create_comparison_table()
    
    # 3. 消融实验图
    print("\n[3/3] Creating ablation study figure...")
    create_ablation_figure()
    
    print("\n" + "="*60)
    print("[OK] All figures generated successfully!")
    print("="*60)
    print("\nGenerated files:")
    print("  - figures/architecture/RCMT_V3_Architecture.pdf")
    print("  - figures/architecture/RCMT_V3_Architecture.png")
    print("  - figures/results/Comparison_Table.pdf")
    print("  - figures/results/Comparison_Table.png")
    print("  - figures/results/Ablation_Study.pdf")
    print("  - figures/results/Ablation_Study.png")


if __name__ == '__main__':
    generate_all_figures()
