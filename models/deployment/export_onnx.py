#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型导出工具 - ONNX 格式

功能:
- PyTorch → ONNX 转换
- ONNX 简化
- 元数据注入

作者: 空中智能体团队
日期: 2026-03-26
"""

import os
import sys
import json
import yaml
import argparse
from pathlib import Path

try:
    import torch
    from ultralytics import YOLO
    import onnx
    from onnxsim import simplify
except ImportError as e:
    print(f"错误: 缺少依赖 - {e}")
    print("请安装: pip install onnx onnx-simplifier")
    sys.exit(1)


def export_yolo_to_onnx(
    weights_path: str,
    output_path: str,
    simplify_onnx: bool = True,
    opset_version: int = 12,
    imgsz: int = 640
):
    """
    导出 YOLOv8 模型为 ONNX

    Args:
        weights_path: PyTorch 权重路径
        output_path: ONNX 输出路径
        simplify_onnx: 是否简化 ONNX
        opset_version: ONNX opset 版本
        imgsz: 输入图像尺寸
    """
    print(f"\n{'='*60}")
    print("导出 ONNX 模型")
    print(f"{'='*60}")
    print(f"输入: {weights_path}")
    print(f"输出: {output_path}")
    print(f"尺寸: {imgsz}x{imgsz}")
    print(f"Opset: {opset_version}")
    print(f"简化: {simplify_onnx}")

    # 加载模型
    print("\n1. 加载 PyTorch 模型...")
    model = YOLO(weights_path)
    print("   ✓ 加载完成")

    # 导出 ONNX
    print("\n2. 导出 ONNX...")
    onnx_path = model.export(
        format="onnx",
        imgsz=imgsz,
        opset=opset_version,
        simplify=simplify_onnx,
        output=str(Path(output_path).parent)
    )
    print(f"   ✓ 导出完成: {onnx_path}")

    # 重命名（如果需要）
    if Path(onnx_path) != Path(output_path):
        import shutil
        shutil.move(onnx_path, output_path)
        print(f"   ✓ 重命名: {output_path}")

    # 验证
    print("\n3. 验证 ONNX...")
    onnx_model = onnx.load(output_path)
    onnx.checker.check_model(onnx_model)
    print("   ✓ ONNX 模型有效")

    # 打印信息
    print("\n4. 模型信息:")
    inputs = onnx_model.graph.input
    outputs = onnx_model.graph.output

    for inp in inputs:
        shape = [d.dim_value for d in inp.type.tensor_type.shape.dim]
        print(f"   输入: {inp.name} - {shape}")

    for out in outputs:
        shape = [d.dim_value for d in out.type.tensor_type.shape.dim]
        print(f"   输出: {out.name} - {shape}")

    # 文件大小
    file_size = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"\n   文件大小: {file_size:.2f} MB")

    print(f"\n{'='*60}")
    print("✓ 导出完成")
    print(f"{'='*60}\n")

    return output_path


def export_to_tensorrt(onnx_path: str, engine_path: str, fp16: bool = True):
    """
    转换 ONNX 为 TensorRT 引擎（仅提示，需要 Jetson）

    Args:
        onnx_path: ONNX 模型路径
        engine_path: TensorRT 引擎输出路径
        fp16: 是否使用 FP16
    """
    print(f"\n{'='*60}")
    print("TensorRT 转换提示")
    print(f"{'='*60}")
    print(f"ONNX: {onnx_path}")
    print(f"引擎: {engine_path}")

    print("\n在 Jetson 设备上运行:")
    print(f"\n  trtexec \\")
    print(f"    --onnx={onnx_path} \\")
    print(f"    --saveEngine={engine_path} \\")
    if fp16:
        print("    --fp16 \\")
    print("    --workspace=4096")

    print(f"\n{'='*60}\n")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="模型导出工具")

    parser.add_argument("--weights", type=str, required=True,
                       help="PyTorch 权重路径 (.pt)")
    parser.add_argument("--output", type=str, required=True,
                       help="ONNX 输出路径 (.onnx)")
    parser.add_argument("--imgsz", type=int, default=640,
                       help="输入图像尺寸")
    parser.add_argument("--opset", type=int, default=12,
                       help="ONNX opset 版本")
    parser.add_argument("--no-simplify", action="store_true",
                       help="不简化 ONNX")
    parser.add_argument("--tensorrt", type=str,
                       help="同时生成 TensorRT 引擎（仅提示）")
    parser.add_argument("--fp16", action="store_true",
                       help="TensorRT 使用 FP16")

    args = parser.parse_args()

    # 导出 ONNX
    onnx_path = export_yolo_to_onnx(
        weights_path=args.weights,
        output_path=args.output,
        simplify_onnx=not args.no_simplify,
        opset_version=args.opset,
        imgsz=args.imgsz
    )

    # TensorRT 提示
    if args.tensorrt:
        export_to_tensorrt(onnx_path, args.tensorrt, args.fp16)


if __name__ == "__main__":
    main()
