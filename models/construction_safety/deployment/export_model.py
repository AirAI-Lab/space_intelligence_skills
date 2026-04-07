#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水利巡检 - 模型导出脚本

一键导出:
1. PyTorch → ONNX
2. 生成配置文件
3. 生成类别文件
4. 生成报警规则

作者: 空中智能体团队
日期: 2026-03-26
"""

import os
import sys
import argparse
from pathlib import Path

# 添加 deployment 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from export_onnx import export_yolo_to_onnx
from generate_config import generate_model_config


def export_all(
    weights_path: str,
    output_dir: str,
    imgsz: int = 640
):
    """
    一键导出所有文件

    Args:
        weights_path: PyTorch 权重路径
        output_dir: 输出目录
        imgsz: 输入图像尺寸
    """
    project_name = "water_inspection"
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"水利巡检 - 模型导出")
    print(f"{'='*60}")
    print(f"权重: {weights_path}")
    print(f"输出: {output_dir}")
    print(f"尺寸: {imgsz}x{imgsz}")

    # 1. 导出 ONNX
    print(f"\n{'─'*60}")
    print("步骤 1/4: 导出 ONNX 模型")
    print(f"{'─'*60}")

    onnx_path = output_path / f"{project_name}.onnx"

    export_yolo_to_onnx(
        weights_path=weights_path,
        output_path=str(onnx_path),
        simplify_onnx=True,
        opset_version=12,
        imgsz=imgsz
    )

    # 2. 生成配置文件
    print(f"\n{'─'*60}")
    print("步骤 2/4: 生成配置文件")
    print(f"{'─'*60}")

    config_yaml = Path(__file__).parent.parent / "configs" / f"{project_name}.yaml"

    if not config_yaml.exists():
        print(f"错误: 找不到配置文件 {config_yaml}")
        return False

    result = generate_model_config(
        project_name=project_name,
        config_yaml=str(config_yaml),
        output_dir=output_dir
    )

    # 3. 复制类别名称
    print(f"\n{'─'*60}")
    print("步骤 3/4: 复制类别名称")
    print(f"{'─'*60}")

    import shutil
    names_src = Path(result['names_file'])
    names_dst = output_path / f"{project_name}.names"
    shutil.copy(names_src, names_dst)
    print(f"   ✓ {names_dst}")

    # 4. 生成 TensorRT 提示
    print(f"\n{'─'*60}")
    print("步骤 4/4: TensorRT 转换提示")
    print(f"{'─'*60}")

    engine_path = output_path / f"{project_name}.engine"

    print("\n在 Jetson 设备上运行:")
    print(f"\n  trtexec \\")
    print(f"    --onnx={onnx_path} \\")
    print(f"    --saveEngine={engine_path} \\")
    print("    --fp16 \\")
    print("    --workspace=4096")

    # 5. 总结
    print(f"\n{'='*60}")
    print("✓ 导出完成")
    print(f"{'='*60}")
    print("\n生成的文件:")
    print(f"  - {onnx_path.name} (ONNX 模型)")
    print(f"  - {project_name}.json (模型配置)")
    print(f"  - {project_name}.names (类别名称)")
    print(f"  - {project_name}_rules.json (报警规则)")

    print(f"\n下一步:")
    print(f"  1. 将以上文件提交给软件人员")
    print(f"  2. 软件人员参考: deployment/INTERFACE.md")
    print(f"  3. 在 Jetson 上运行 trtexec 生成 engine 文件")

    print(f"{'='*60}\n")

    return True


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="水利巡检 - 模型导出")

    parser.add_argument("--weights", type=str, required=True,
                       help="PyTorch 权重路径")
    parser.add_argument("--output", type=str, default="models",
                       help="输出目录")
    parser.add_argument("--imgsz", type=int, default=640,
                       help="输入图像尺寸")

    args = parser.parse_args()

    export_all(
        weights_path=args.weights,
        output_dir=args.output,
        imgsz=args.imgsz
    )


if __name__ == "__main__":
    main()
