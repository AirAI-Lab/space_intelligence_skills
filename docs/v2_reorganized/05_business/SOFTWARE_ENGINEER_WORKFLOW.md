# 软件工程师工作流程 - 模型转换与推理集成

> **版本**: V1.0
> **日期**: 2026-03-09
> **目标**: 软件工程师如何利用算法人员交付的模型，实现转换和推理集成
> **参考案例**: 安全帽检测、河道检测、RCMT变化检测

---

## 📋 目录

1. [工作流程总览](#1-工作流程总览)
2. [算法工程师交付物验收](#2-算法工程师交付物验收)
3. [模型转换流程](#3-模型转换流程)
4. [推理集成流程](#4-推理集成流程)
5. [完整实现案例：应急管理插件](#5-完整实现案例应急管理插件)
6. [测试与验证](#6-测试与验证)
7. [常见问题与解决方案](#7-常见问题与解决方案)

---

## 1. 工作流程总览

### 1.1 软件工程师工作流程

```
输入：算法工程师交付的模型包
  ├─ best.pt (PyTorch权重)
  ├─ model_config.json (模型配置)
  ├─ data.yaml (数据集配置)
  └─ docs/ (文档)

流程：
  阶段1: 验收检查（0.5天）
    └─ 检查文件完整性、配置正确性

  阶段2: 模型转换（0.5天）
    ├─ PT → ONNX
    ├─ ONNX → TensorRT
    └─ 性能测试

  阶段3: 插件开发（1天）
    ├─ 编写插件代码（C++）
    ├─ 编写配置文件
    └─ 编写测试代码

  阶段4: 集成测试（0.5天）
    ├─ 边缘设备测试
    ├─ 性能测试
    └─ 稳定性测试

  阶段5: 部署上线（0.5天）
    ├─ 打包发布
    ├─ 文档更新
    └─ 客户部署

输出：可部署的edge_infer插件
  ├─ plugin.so (编译后的插件)
  ├─ best.engine (TensorRT引擎)
  ├─ config.yaml (插件配置)
  └─ docs/ (文档)
```

**总计**: 3天/每个部门

---

## 2. 算法工程师交付物验收

### 2.1 文件完整性检查

**验收脚本** (`scripts/verify_model_delivery.py`):

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型交付验收脚本
验证算法工程师交付的模型包是否符合标准
"""

import os
import json
import yaml
from pathlib import Path
from typing import List, Dict

class ModelDeliveryVerifier:
    """模型交付验收器"""
    
    def __init__(self, model_dir: str):
        self.model_dir = Path(model_dir)
        self.errors = []
        self.warnings = []
        
    def verify(self) -> bool:
        """
        验收模型包
        
        Returns:
            True: 验收通过
            False: 验收失败
        """
        print(f"\n{'='*60}")
        print(f"模型包验收: {self.model_dir.name}")
        print(f"{'='*60}\n")
        
        # 1. 检查目录结构
        self.check_directory_structure()
        
        # 2. 检查必需文件
        self.check_required_files()
        
        # 3. 检查配置文件格式
        self.check_config_files()
        
        # 4. 检查模型文件
        self.check_model_files()
        
        # 5. 检查文档
        self.check_documentation()
        
        # 打印结果
        self.print_results()
        
        return len(self.errors) == 0
    
    def check_directory_structure(self):
        """检查目录结构"""
        print("✓ 检查目录结构...")
        
        required_dirs = ['weights', 'config', 'docs', 'plugin']
        for dir_name in required_dirs:
            dir_path = self.model_dir / dir_name
            if not dir_path.exists():
                self.errors.append(f"缺少目录: {dir_name}/")
            else:
                print(f"  ✓ {dir_name}/")
    
    def check_required_files(self):
        """检查必需文件"""
        print("\n✓ 检查必需文件...")
        
        required_files = {
            'weights/best.pt': '模型权重',
            'weights/best.onnx': 'ONNX模型',
            'config/model_config.json': '模型配置',
            'config/data.yaml': '数据集配置',
            'config/inference_config.yaml': '推理配置',
            'docs/README.md': '说明文档',
            'docs/MODEL_CARD.md': '模型卡片',
            'docs/PERFORMANCE.md': '性能报告',
            'plugin/config.yaml': '插件配置'
        }
        
        for file_path, desc in required_files.items():
            full_path = self.model_dir / file_path
            if not full_path.exists():
                self.errors.append(f"缺少文件: {file_path} ({desc})")
            else:
                size_mb = full_path.stat().st_size / (1024 * 1024)
                print(f"  ✓ {file_path} ({size_mb:.2f} MB)")
    
    def check_config_files(self):
        """检查配置文件格式"""
        print("\n✓ 检查配置文件格式...")
        
        # 检查model_config.json
        config_path = self.model_dir / 'config' / 'model_config.json'
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 检查必需字段
                required_fields = [
                    'model_id', 'model_type', 'version',
                    'architecture', 'training', 'metrics'
                ]
                
                for field in required_fields:
                    if field not in config:
                        self.errors.append(f"model_config.json缺少字段: {field}")
                    else:
                        print(f"  ✓ {field}")
                
                # 检查类别信息
                if 'architecture' in config and 'classes' in config['architecture']:
                    num_classes = config['architecture']['num_classes']
                    classes = config['architecture']['classes']
                    print(f"  ✓ 类别数: {num_classes}")
                    print(f"  ✓ 类别: {list(classes.values())}")
                    
            except json.JSONDecodeError as e:
                self.errors.append(f"model_config.json格式错误: {e}")
        
        # 检查data.yaml
        data_yaml_path = self.model_dir / 'config' / 'data.yaml'
        if data_yaml_path.exists():
            try:
                with open(data_yaml_path, 'r', encoding='utf-8') as f:
                    data_config = yaml.safe_load(f)
                
                if 'classes' in data_config:
                    print(f"  ✓ data.yaml类别数: {data_config['classes']['num']}")
                    
            except yaml.YAMLError as e:
                self.errors.append(f"data.yaml格式错误: {e}")
    
    def check_model_files(self):
        """检查模型文件"""
        print("\n✓ 检查模型文件...")
        
        # 检查PT文件
        pt_path = self.model_dir / 'weights' / 'best.pt'
        if pt_path.exists():
            try:
                import torch
                checkpoint = torch.load(pt_path, map_location='cpu')
                print(f"  ✓ best.pt加载成功")
                
                # 检查模型结构
                if 'model' in checkpoint:
                    print(f"  ✓ 模型结构完整")
                    
            except Exception as e:
                self.errors.append(f"best.pt加载失败: {e}")
        
        # 检查ONNX文件
        onnx_path = self.model_dir / 'weights' / 'best.onnx'
        if onnx_path.exists():
            try:
                import onnx
                model = onnx.load(str(onnx_path))
                onnx.checker.check_model(model)
                print(f"  ✓ best.onnx格式正确")
                
                # 打印输入输出信息
                input_shape = model.graph.input[0].type.tensor_type.shape
                print(f"  ✓ 输入尺寸: {input_shape}")
                
            except Exception as e:
                self.errors.append(f"best.onnx格式错误: {e}")
    
    def check_documentation(self):
        """检查文档"""
        print("\n✓ 检查文档...")
        
        docs = {
            'docs/README.md': '模型说明',
            'docs/MODEL_CARD.md': '模型卡片',
            'docs/PERFORMANCE.md': '性能报告'
        }
        
        for doc_path, desc in docs.items():
            full_path = self.model_dir / doc_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = len(content.split('\n'))
                    print(f"  ✓ {doc_path} ({lines}行)")
            else:
                self.warnings.append(f"缺少文档: {doc_path}")
    
    def print_results(self):
        """打印验收结果"""
        print(f"\n{'='*60}")
        
        if self.errors:
            print(f"❌ 验收失败: {len(self.errors)}个错误")
            for error in self.errors:
                print(f"  ❌ {error}")
        else:
            print(f"✅ 验收通过")
        
        if self.warnings:
            print(f"\n⚠️  警告: {len(self.warnings)}个")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")
        
        print(f"{'='*60}\n")


# 使用示例
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python verify_model_delivery.py <model_dir>")
        sys.exit(1)
    
    model_dir = sys.argv[1]
    verifier = ModelDeliveryVerifier(model_dir)
    success = verifier.verify()
    
    sys.exit(0 if success else 1)
```

**使用方法**:

```bash
# 验收应急管理模型包
python scripts/verify_model_delivery.py models/emergency/v1.0/

# 输出示例
============================================================
模型包验收: v1.0
============================================================

✓ 检查目录结构...
  ✓ weights/
  ✓ config/
  ✓ docs/
  ✓ plugin/

✓ 检查必需文件...
  ✓ weights/best.pt (52.34 MB)
  ✓ weights/best.onnx (51.98 MB)
  ...

✓ 检查配置文件格式...
  ✓ model_id
  ✓ model_type
  ✓ 类别数: 5
  ✓ 类别: ['landslide', 'flood', 'forest_fire', 'smoke', 'rescue_target']

✓ 检查模型文件...
  ✓ best.pt加载成功
  ✓ best.onnx格式正确
  ✓ 输入尺寸: [1, 3, 640, 640]

============================================================
✅ 验收通过
============================================================
```

---

## 3. 模型转换流程

### 3.1 PT → ONNX转换

**转换脚本** (`scripts/convert_to_onnx.py`):

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyTorch模型转ONNX
参考：YOLOv8官方导出方法
"""

import os
import sys
import json
import yaml
from pathlib import Path
import torch

def convert_pt_to_onnx(
    pt_path: str,
    output_dir: str,
    imgsz: int = 640,
    simplify: bool = True,
    opset: int = 12
):
    """
    PT模型转ONNX
    
    Args:
        pt_path: PyTorch模型路径
        output_dir: 输出目录
        imgsz: 输入图像尺寸
        simplify: 是否简化ONNX模型
        opset: ONNX opset版本
    """
    print(f"\n{'='*60}")
    print(f"PT → ONNX转换")
    print(f"{'='*60}\n")
    
    # 加载模型
    print(f"✓ 加载模型: {pt_path}")
    
    # 根据模型类型选择加载方式
    if 'yolo' in pt_path.lower():
        # YOLOv8模型
        from ultralytics import YOLO
        model = YOLO(pt_path)
        
        # 导出ONNX
        print(f"✓ 导出ONNX...")
        model.export(
            format='onnx',
            imgsz=imgsz,
            simplify=simplify,
            opset=opset,
            dynamic=False,  # 固定输入尺寸
            device='cpu'
        )
        
        # ONNX文件路径
        onnx_path = pt_path.replace('.pt', '.onnx')
        
    else:
        # 自定义模型（如RCMT）
        print(f"⚠️  非YOLO模型，使用通用转换方法")
        
        # 加载checkpoint
        checkpoint = torch.load(pt_path, map_location='cpu')
        
        # 创建dummy input
        dummy_input = torch.randn(1, 3, imgsz, imgsz)
        
        # 导出ONNX
        onnx_path = os.path.join(output_dir, 'best.onnx')
        torch.onnx.export(
            checkpoint['model'] if 'model' in checkpoint else checkpoint,
            dummy_input,
            onnx_path,
            export_params=True,
            opset_version=opset,
            do_constant_folding=True,
            input_names=['images'],
            output_names=['output'],
            dynamic_axes=None  # 固定尺寸
        )
    
    # 验证ONNX
    print(f"\n✓ 验证ONNX模型...")
    import onnx
    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)
    
    # 打印信息
    print(f"✓ ONNX模型信息:")
    print(f"  - 文件: {onnx_path}")
    print(f"  - 大小: {os.path.getsize(onnx_path) / (1024*1024):.2f} MB")
    print(f"  - Opset: {opset}")
    print(f"  - 输入: {onnx_model.graph.input[0].name}")
    print(f"  - 输出: {onnx_model.graph.output[0].name}")
    
    # 简化（可选）
    if simplify:
        try:
            import onnxsim
            print(f"\n✓ 简化ONNX模型...")
            onnx_model_simplified, check = onnxsim.simplify(onnx_model)
            
            simplified_path = onnx_path.replace('.onnx', '_simplified.onnx')
            onnx.save(onnx_model_simplified, simplified_path)
            print(f"✓ 简化后: {simplified_path}")
            
        except ImportError:
            print(f"⚠️  未安装onnx-simplifier，跳过简化")
    
    print(f"\n{'='*60}")
    print(f"✅ PT → ONNX转换完成")
    print(f"{'='*60}\n")
    
    return onnx_path


# 使用示例
if __name__ == "__main__":
    # 读取配置
    with open('config/model_config.json', 'r') as f:
        config = json.load(f)
    
    imgsz = config['architecture']['input_size'][0]
    
    # 转换
    convert_pt_to_onnx(
        pt_path='weights/best.pt',
        output_dir='weights/',
        imgsz=imgsz,
        simplify=True
    )
```

---

### 3.2 ONNX → TensorRT转换

**转换脚本** (`scripts/convert_to_tensorrt.py`):

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ONNX模型转TensorRT引擎
支持FP32/FP16/INT8精度
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def convert_onnx_to_tensorrt(
    onnx_path: str,
    output_path: str,
    precision: str = 'fp16',
    workspace: int = 4096,
    min_batch: int = 1,
    opt_batch: int = 1,
    max_batch: int = 1
):
    """
    ONNX转TensorRT引擎
    
    Args:
        onnx_path: ONNX模型路径
        output_path: TensorRT引擎输出路径
        precision: 精度（fp32/fp16/int8）
        workspace: GPU工作空间大小（MB）
        min_batch: 最小batch size
        opt_batch: 最优batch size
        max_batch: 最大batch size
    """
    print(f"\n{'='*60}")
    print(f"ONNX → TensorRT转换")
    print(f"{'='*60}\n")
    
    # 检查ONNX文件
    if not os.path.exists(onnx_path):
        raise FileNotFoundError(f"ONNX文件不存在: {onnx_path}")
    
    print(f"✓ ONNX文件: {onnx_path}")
    print(f"✓ 输出路径: {output_path}")
    print(f"✓ 精度: {precision}")
    
    # 构建trtexec命令
    cmd = [
        'trtexec',
        f'--onnx={onnx_path}',
        f'--saveEngine={output_path}',
        f'--workspace={workspace}',
        f'--minShapes=images:{min_batch}x3x640x640',
        f'--optShapes=images:{opt_batch}x3x640x640',
        f'--maxShapes=images:{max_batch}x3x640x640',
        '--buildOnly',
        '--verbose'
    ]
    
    # 添加精度参数
    if precision == 'fp16':
        cmd.append('--fp16')
    elif precision == 'int8':
        cmd.append('--int8')
        # 需要校准数据
        # cmd.append('--calib=calibration_cache.txt')
    
    # 执行转换
    print(f"\n✓ 执行命令:")
    print(f"  {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ 转换失败:")
        print(result.stderr)
        raise RuntimeError("TensorRT转换失败")
    
    # 检查输出
    if not os.path.exists(output_path):
        raise FileNotFoundError(f"TensorRT引擎生成失败: {output_path}")
    
    # 打印信息
    engine_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\n✓ TensorRT引擎信息:")
    print(f"  - 文件: {output_path}")
    print(f"  - 大小: {engine_size_mb:.2f} MB")
    print(f"  - 精度: {precision}")
    print(f"  - Batch Size: {min_batch}-{max_batch}")
    
    print(f"\n{'='*60}")
    print(f"✅ ONNX → TensorRT转换完成")
    print(f"{'='*60}\n")
    
    return output_path


# Python API方式（推荐用于高级定制）
def convert_onnx_to_tensorrt_python(
    onnx_path: str,
    output_path: str,
    precision: str = 'fp16'
):
    """
    使用Python API转换（高级方式）
    需要安装: pip install tensorrt
    """
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit
    
    print(f"\n{'='*60}")
    print(f"ONNX → TensorRT转换 (Python API)")
    print(f"{'='*60}\n")
    
    # 创建logger
    TRT_LOGGER = trt.Logger(trt.Logger.VERBOSE)
    
    # 创建builder
    builder = trt.Builder(TRT_LOGGER)
    network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser = trt.OnnxParser(network, TRT_LOGGER)
    
    # 解析ONNX
    print(f"✓ 解析ONNX模型...")
    with open(onnx_path, 'rb') as f:
        if not parser.parse(f.read()):
            for error in range(parser.num_errors):
                print(trt.Logger.ERROR, parser.get_error(error))
            raise RuntimeError("ONNX解析失败")
    
    print(f"✓ ONNX解析成功")
    
    # 配置builder
    config = builder.create_builder_config()
    config.max_workspace_size = 4 << 30  # 4GB
    
    # 设置精度
    if precision == 'fp16':
        config.set_flag(trt.BuilderFlag.FP16)
        print(f"✓ 启用FP16精度")
    elif precision == 'int8':
        config.set_flag(trt.BuilderFlag.INT8)
        print(f"✓ 启用INT8精度")
    
    # 构建引擎
    print(f"\n✓ 构建TensorRT引擎...")
    engine = builder.build_engine(network, config)
    
    # 保存引擎
    print(f"✓ 保存引擎: {output_path}")
    with open(output_path, 'wb') as f:
        f.write(engine.serialize())
    
    print(f"\n{'='*60}")
    print(f"✅ 转换完成")
    print(f"{'='*60}\n")
    
    return output_path


# 使用示例
if __name__ == "__main__":
    # 方式1：使用trtexec（推荐）
    convert_onnx_to_tensorrt(
        onnx_path='weights/best.onnx',
        output_path='weights/best.engine',
        precision='fp16',
        workspace=4096
    )
    
    # 方式2：使用Python API（高级）
    # convert_onnx_to_tensorrt_python(
    #     onnx_path='weights/best.onnx',
    #     output_path='weights/best.engine',
    #     precision='fp16'
    # )
```

---

### 3.3 性能测试

**性能测试脚本** (`scripts/test_model_performance.py`):

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型性能测试
测试推理时间、FPS、内存占用等指标
"""

import os
import sys
import time
import json
import numpy as np
import cv2
from pathlib import Path

class ModelPerformanceTester:
    """模型性能测试器"""
    
    def __init__(self, engine_path: str, config_path: str):
        self.engine_path = engine_path
        self.config = self.load_config(config_path)
        
    def load_config(self, config_path: str) -> dict:
        """加载配置"""
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def test_tensorrt_performance(
        self,
        test_images: list,
        warmup: int = 10,
        test_runs: int = 100
    ):
        """
        测试TensorRT模型性能
        
        Args:
            test_images: 测试图像路径列表
            warmup: 预热次数
            test_runs: 测试次数
        """
        print(f"\n{'='*60}")
        print(f"TensorRT性能测试")
        print(f"{'='*60}\n")
        
        # 加载TensorRT引擎
        import tensorrt as trt
        import pycuda.driver as cuda
        import pycuda.autoinit
        
        TRT_LOGGER = trt.Logger(trt.Logger.INFO)
        
        # 反序列化引擎
        print(f"✓ 加载引擎: {self.engine_path}")
        with open(self.engine_path, 'rb') as f:
            engine = trt.Runtime(TRT_LOGGER).deserialize_cuda_engine(f.read())
        
        context = engine.create_execution_context()
        
        # 获取输入输出信息
        input_name = engine.get_binding_name(0)
        output_name = engine.get_binding_name(1)
        input_shape = engine.get_binding_shape(0)
        output_shape = engine.get_binding_shape(1)
        
        print(f"✓ 输入: {input_name}, 形状: {input_shape}")
        print(f"✓ 输出: {output_name}, 形状: {output_shape}")
        
        # 准备buffer
        input_size = trt.volume(input_shape) * np.dtype(np.float32).itemsize
        output_size = trt.volume(output_shape) * np.dtype(np.float32).itemsize
        
        d_input = cuda.mem_alloc(input_size)
        d_output = cuda.mem_alloc(output_size)
        
        bindings = [int(d_input), int(d_output)]
        
        # 准备测试数据
        test_image = cv2.imread(test_images[0])
        input_tensor = self.preprocess(test_image, input_shape)
        
        # 预热
        print(f"\n✓ 预热 {warmup} 次...")
        for _ in range(warmup):
            cuda.memcpy_htod(d_input, input_tensor)
            context.execute_v2(bindings)
        
        # 正式测试
        print(f"✓ 测试 {test_runs} 次...")
        inference_times = []
        
        for _ in range(test_runs):
            start = time.perf_counter()
            
            # 推理
            cuda.memcpy_htod(d_input, input_tensor)
            context.execute_v2(bindings)
            cuda.memcpy_dtoh(np.empty(output_shape, dtype=np.float32), d_output)
            
            end = time.perf_counter()
            inference_times.append((end - start) * 1000)  # ms
        
        # 统计结果
        inference_times = np.array(inference_times)
        
        print(f"\n{'='*60}")
        print(f"性能测试结果:")
        print(f"{'='*60}")
        print(f"  平均推理时间: {inference_times.mean():.2f} ms")
        print(f"  最小推理时间: {inference_times.min():.2f} ms")
        print(f"  最大推理时间: {inference_times.max():.2f} ms")
        print(f"  标准差: {inference_times.std():.2f} ms")
        print(f"  FPS: {1000 / inference_times.mean():.1f}")
        print(f"  P95: {np.percentile(inference_times, 95):.2f} ms")
        print(f"  P99: {np.percentile(inference_times, 99):.2f} ms")
        print(f"{'='*60}\n")
        
        # 保存结果
        results = {
            'model': self.engine_path,
            'test_runs': test_runs,
            'avg_inference_time_ms': float(inference_times.mean()),
            'min_inference_time_ms': float(inference_times.min()),
            'max_inference_time_ms': float(inference_times.max()),
            'std_ms': float(inference_times.std()),
            'fps': float(1000 / inference_times.mean()),
            'p95_ms': float(np.percentile(inference_times, 95)),
            'p99_ms': float(np.percentile(inference_times, 99))
        }
        
        with open('test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        return results
    
    def preprocess(self, image, input_shape):
        """图像预处理"""
        # resize
        h, w = input_shape[2], input_shape[3]
        image = cv2.resize(image, (w, h))
        
        # BGR → RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # normalize
        image = image.astype(np.float32) / 255.0
        
        # HWC → CHW
        image = np.transpose(image, (2, 0, 1))
        
        # batch
        image = np.expand_dims(image, axis=0)
        
        # contiguous
        image = np.ascontiguousarray(image, dtype=np.float32)
        
        return image


# 使用示例
if __name__ == "__main__":
    tester = ModelPerformanceTester(
        engine_path='weights/best.engine',
        config_path='config/model_config.json'
    )
    
    test_images = ['test/test1.jpg', 'test/test2.jpg']
    results = tester.test_tensorrt_performance(test_images)
```

---

## 4. 推理集成流程

### 4.1 插件架构（C++）

**参考：安全帽检测插件**

edge_infer使用C++插件架构，每个插件继承自`PluginBase`基类。

**插件基类** (`src/plugins/plugin_base.h`):

```cpp
// src/plugins/plugin_base.h

#ifndef PLUGIN_BASE_H
#define PLUGIN_BASE_H

#include <string>
#include "common.h"

namespace framework {
namespace plugin {

enum class PluginType {
    DETECTION,
    SEGMENTATION,
    TRACKING,
    CLASSIFICATION
};

class PluginBase {
public:
    virtual ~PluginBase() = default;
    
    // 初始化
    virtual bool init(const std::string& plugin_config) = 0;
    
    // 执行推理
    virtual bool execute(const void* input_data, void* output_data) = 0;
    
    // 反初始化
    virtual void deinit() = 0;
    
    // 插件信息
    virtual std::string get_plugin_name() const = 0;
    virtual PluginType get_plugin_type() const = 0;
    virtual std::string get_plugin_version() const = 0;
    
    // 注入推理模块
    virtual void SetInferModule(void* infer_mod) = 0;
};

// 插件工厂函数
extern "C" {
    PluginBase* create_plugin();
    void destroy_plugin(PluginBase* p);
}

} // namespace plugin
} // namespace framework

#endif // PLUGIN_BASE_H
```

---

### 4.2 完整插件实现（C++）

**以应急管理插件为例** (`src/plugins/emergency_management/`):

#### **4.2.1 插件头文件**

```cpp
// src/plugins/emergency_management/emergency_detect.h

#ifndef EMERGENCY_DETECT_H
#define EMERGENCY_DETECT_H

#include "plugin/plugin_base.h"
#include "common.h"
#include "core/model_infer.h"
#include <vector>
#include <jsoncpp/json/json.h>
#include <unordered_map>

namespace framework {
namespace plugin {

/**
 * 应急管理检测插件
 * 支持5类灾害检测：landslide, mudslide, flood, forest_fire, smoke
 */
class EmergencyDetect : public PluginBase {
public:
    EmergencyDetect() = default;
    ~EmergencyDetect() override = default;

    // 插件生命周期
    bool init(const std::string& plugin_config) override;
    bool execute(const void* input_data, void* output_data) override;
    void deinit() override;

    // 插件信息
    std::string get_plugin_name() const override { return "emergency_detect"; }
    PluginType get_plugin_type() const override { return PluginType::DETECTION; }
    std::string get_plugin_version() const override { return "1.0.0"; }

    // 注入推理模块
    void SetInferModule(void* infer_mod) override {
        infer_mod_ = static_cast<framework::core::ModelInferModule*>(infer_mod);
    }

private:
    // 推理模块（由框架注入）
    framework::core::ModelInferModule* infer_mod_ = nullptr;

    // 配置参数
    float conf_threshold_ = 0.5f;
    float nms_threshold_ = 0.45f;
    std::vector<std::string> class_names_;
    
    // 类别索引
    int idx_landslide_ = -1;
    int idx_mudslide_ = -1;
    int idx_flood_ = -1;
    int idx_forest_fire_ = -1;
    int idx_smoke_ = -1;
    
    // 后处理方法
    std::vector<Detection> postprocess(
        const float* output,
        int num_detections,
        int num_classes,
        float conf_thresh,
        float nms_thresh
    );
    
    // NMS
    std::vector<int> nms(
        const std::vector<cv::Rect>& boxes,
        const std::vector<float>& scores,
        float nms_thresh
    );
};

} // namespace plugin
} // namespace framework

// 插件工厂导出
extern "C" framework::plugin::PluginBase* create_plugin();
extern "C" void destroy_plugin(framework::plugin::PluginBase* p);

#endif // EMERGENCY_DETECT_H
```

---

#### **4.2.2 插件实现**

```cpp
// src/plugins/emergency_management/emergency_detect.cpp

#include "emergency_detect.h"
#include <fstream>
#include <opencv2/opencv.hpp>
#include <algorithm>

namespace framework {
namespace plugin {

bool EmergencyDetect::init(const std::string& plugin_config) {
    /**
     * 初始化插件
     * 1. 读取配置文件
     * 2. 加载类别信息
     * 3. 设置阈值参数
     */
    
    // 读取配置文件
    Json::Value config;
    std::ifstream config_file(plugin_config);
    config_file >> config;
    
    // 读取阈值
    if (config.isMember("inference")) {
        conf_threshold_ = config["inference"]["confidence_threshold"].asFloat();
        nms_threshold_ = config["inference"]["nms_threshold"].asFloat();
    }
    
    // 读取类别信息
    if (config.isMember("model") && config["model"].isMember("classes")) {
        for (const auto& cls : config["model"]["classes"]) {
            class_names_.push_back(cls.asString());
        }
        
        // 建立类别索引
        for (int i = 0; i < class_names_.size(); i++) {
            if (class_names_[i] == "landslide") idx_landslide_ = i;
            else if (class_names_[i] == "mudslide") idx_mudslide_ = i;
            else if (class_names_[i] == "flood") idx_flood_ = i;
            else if (class_names_[i] == "forest_fire") idx_forest_fire_ = i;
            else if (class_names_[i] == "smoke") idx_smoke_ = i;
        }
    }
    
    LOG(INFO) << "EmergencyDetect初始化完成";
    LOG(INFO) << "  - 类别数: " << class_names_.size();
    LOG(INFO) << "  - 置信度阈值: " << conf_threshold_;
    LOG(INFO) << "  - NMS阈值: " << nms_threshold_;
    
    return true;
}

bool EmergencyDetect::execute(const void* input_data, void* output_data) {
    /**
     * 执行推理
     * 1. 获取输入图像
     * 2. 调用推理模块
     * 3. 后处理（NMS、过滤）
     * 4. 输出结果
     */
    
    // 输入数据转换
    const cv::Mat* input_image = static_cast<const cv::Mat*>(input_data);
    std::vector<Detection>* output_detections = static_cast<std::vector<Detection>*>(output_data);
    
    if (!infer_mod_) {
        LOG(ERROR) << "推理模块未初始化";
        return false;
    }
    
    // 调用推理模块
    InferenceResult infer_result;
    if (!infer_mod_->Infer(*input_image, infer_result)) {
        LOG(ERROR) << "推理失败";
        return false;
    }
    
    // 后处理
    *output_detections = postprocess(
        infer_result.output_data,
        infer_result.num_detections,
        infer_result.num_classes,
        conf_threshold_,
        nms_threshold_
    );
    
    return true;
}

void EmergencyDetect::deinit() {
    // 清理资源
    class_names_.clear();
    LOG(INFO) << "EmergencyDetect反初始化完成";
}

std::vector<Detection> EmergencyDetect::postprocess(
    const float* output,
    int num_detections,
    int num_classes,
    float conf_thresh,
    float nms_thresh
) {
    /**
     * 后处理：NMS + 过滤
     * YOLOv8输出格式: [x, y, w, h, conf, cls1, cls2, ...]
     */
    
    std::vector<cv::Rect> boxes;
    std::vector<float> scores;
    std::vector<int> class_ids;
    
    // 解析输出
    for (int i = 0; i < num_detections; i++) {
        const float* det = output + i * (5 + num_classes);
        
        float confidence = det[4];
        if (confidence < conf_thresh) continue;
        
        // 找到最大类别分数
        int class_id = 0;
        float max_class_score = 0;
        for (int c = 0; c < num_classes; c++) {
            if (det[5 + c] > max_class_score) {
                max_class_score = det[5 + c];
                class_id = c;
            }
        }
        
        // 坐标转换（center → corner）
        float cx = det[0];
        float cy = det[1];
        float w = det[2];
        float h = det[3];
        
        int x = static_cast<int>(cx - w / 2);
        int y = static_cast<int>(cy - h / 2);
        
        boxes.push_back(cv::Rect(x, y, static_cast<int>(w), static_cast<int>(h)));
        scores.push_back(confidence);
        class_ids.push_back(class_id);
    }
    
    // NMS
    std::vector<int> indices = nms(boxes, scores, nms_thresh);
    
    // 构建输出
    std::vector<Detection> detections;
    for (int idx : indices) {
        Detection det;
        det.bbox = boxes[idx];
        det.confidence = scores[idx];
        det.class_id = class_ids[idx];
        det.class_name = class_names_[class_ids[idx]];
        detections.push_back(det);
    }
    
    return detections;
}

std::vector<int> EmergencyDetect::nms(
    const std::vector<cv::Rect>& boxes,
    const std::vector<float>& scores,
    float nms_thresh
) {
    /**
     * 非极大值抑制（NMS）
     */
    
    std::vector<int> indices;
    std::vector<float> areas;
    
    // 计算面积
    for (const auto& box : boxes) {
        areas.push_back(box.width * box.height);
    }
    
    // 按分数排序
    std::vector<int> order(scores.size());
    std::iota(order.begin(), order.end(), 0);
    std::sort(order.begin(), order.end(), [&scores](int a, int b) {
        return scores[a] > scores[b];
    });
    
    // NMS
    std::vector<bool> suppressed(scores.size(), false);
    
    for (int i = 0; i < order.size(); i++) {
        int idx = order[i];
        
        if (suppressed[idx]) continue;
        
        indices.push_back(idx);
        
        for (int j = i + 1; j < order.size(); j++) {
            int idx_j = order[j];
            
            if (suppressed[idx_j]) continue;
            
            // 计算IoU
            int xx1 = std::max(boxes[idx].x, boxes[idx_j].x);
            int yy1 = std::max(boxes[idx].y, boxes[idx_j].y);
            int xx2 = std::min(boxes[idx].x + boxes[idx].width, 
                              boxes[idx_j].x + boxes[idx_j].width);
            int yy2 = std::min(boxes[idx].y + boxes[idx].height,
                              boxes[idx_j].y + boxes[idx_j].height);
            
            int w = std::max(0, xx2 - xx1);
            int h = std::max(0, yy2 - yy1);
            float inter = w * h;
            float iou = inter / (areas[idx] + areas[idx_j] - inter);
            
            if (iou > nms_thresh) {
                suppressed[idx_j] = true;
            }
        }
    }
    
    return indices;
}

} // namespace plugin
} // namespace framework

// 插件工厂函数
extern "C" framework::plugin::PluginBase* create_plugin() {
    return new framework::plugin::EmergencyDetect();
}

extern "C" void destroy_plugin(framework::plugin::PluginBase* p) {
    delete p;
}
```

---

#### **4.2.3 插件配置文件**

```yaml
# src/plugins/emergency_management/config.yaml

plugin:
  name: "emergency_management"
  version: "1.0.0"
  description: "应急管理部门算法包（5种灾害检测）"
  
model:
  path: "weights/best.engine"
  type: "tensorrt"
  precision: "fp16"
  classes:
    - landslide
    - mudslide
    - flood
    - forest_fire
    - smoke
  
inference:
  device: "cuda:0"
  batch_size: 1
  confidence_threshold: 0.5
  nms_threshold: 0.45
  max_detections: 100
  
input:
  size: [640, 640]
  normalize: true
  mean: [0, 0, 0]
  std: [255, 255, 255]
  
output:
  format: "json"
  save_results: true
  visualizations: true
  output_dir: "logs/emergency/"
  
algorithms:
  - name: "disaster_detection"
    type: "detection"
    classes: ["landslide", "mudslide", "flood", "forest_fire", "smoke"]
    priority: "P0"
    
deployment:
  target: "edge"
  device: "jetson_orin_nx"
  memory_footprint_mb: 400
```

---

### 4.3 编译与部署

#### **4.3.1 CMakeLists.txt**

```cmake
# src/plugins/emergency_management/CMakeLists.txt

cmake_minimum_required(VERSION 3.10)
project(emergency_management_plugin)

# C++ 标准
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 依赖
find_package(OpenCV REQUIRED)
find_package(JsonCpp REQUIRED)
find_package(CUDA REQUIRED)
find_package(TensorRT REQUIRED)

# 源文件
set(SOURCES
    emergency_detect.cpp
)

# 头文件
set(HEADERS
    emergency_detect.h
)

# 编译插件库
add_library(emergency_detect SHARED ${SOURCES} ${HEADERS})

# 链接库
target_link_libraries(emergency_detect
    ${OpenCV_LIBS}
    ${JsonCpp_LIBRARIES}
    ${CUDA_LIBRARIES}
    ${TensorRT_LIBRARIES}
    framework_core  # edge_infer核心库
)

# 包含目录
target_include_directories(emergency_detect
    PRIVATE
    ${OpenCV_INCLUDE_DIRS}
    ${JsonCpp_INCLUDE_DIRS}
    ${CUDA_INCLUDE_DIRS}
    ${TensorRT_INCLUDE_DIRS}
    ${CMAKE_SOURCE_DIR}/src/core
    ${CMAKE_SOURCE_DIR}/src/common
)

# 安装
install(TARGETS emergency_detect
    LIBRARY DESTINATION plugins
)
```

#### **4.3.2 编译脚本**

```bash
#!/bin/bash
# build_plugin.sh

set -e

# 编译emergency_management插件
mkdir -p build/plugins/emergency_management
cd build/plugins/emergency_management

cmake ../../src/plugins/emergency_management \
    -DCMAKE_BUILD_TYPE=Release \
    -DTensorRT_ROOT=/usr/local/TensorRT \
    -DCUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda

make -j$(nproc)

# 安装到edge_infer/plugins/
cp libemergency_detect.so ../../../edge_infer/plugins/

echo "✓ emergency_management插件编译完成"
```

---

## 5. 完整实现案例：应急管理插件

### 5.1 端到端流程

```bash
# Step 1: 验收算法工程师交付的模型包
python scripts/verify_model_delivery.py models/emergency/v1.0/

# Step 2: 转换模型（PT → ONNX → TensorRT）
cd models/emergency/v1.0/

# PT → ONNX
python ../../../scripts/convert_to_onnx.py \
    --pt weights/best.pt \
    --output weights/ \
    --imgsz 640

# ONNX → TensorRT
python ../../../scripts/convert_to_tensorrt.py \
    --onnx weights/best.onnx \
    --output weights/best.engine \
    --precision fp16

# Step 3: 性能测试
python ../../../scripts/test_model_performance.py \
    --engine weights/best.engine \
    --config config/model_config.json \
    --test_images test/test_images/

# Step 4: 编译插件
cd ../../../
bash scripts/build_plugin.sh emergency_management

# Step 5: 部署测试
./edge_infer --plugin emergency_management --config models/emergency/v1.0/plugin/config.yaml

# Step 6: 集成测试
python tests/test_emergency_plugin.py

# Step 7: 打包发布
tar -czf emergency_management_v1.0.tar.gz \
    models/emergency/v1.0/weights/best.engine \
    models/emergency/v1.0/plugin/ \
    models/emergency/v1.0/config/ \
    models/emergency/v1.0/docs/
```

---

### 5.2 测试代码

```python
#!/usr/bin/env python
# tests/test_emergency_plugin.py

import cv2
import sys
import json
sys.path.append('..')

from edge_infer import EdgeInfer

def test_emergency_plugin():
    """测试应急管理插件"""
    
    # 初始化推理引擎
    infer = EdgeInfer(
        plugin_name='emergency_management',
        config_path='models/emergency/v1.0/plugin/config.yaml'
    )
    
    # 加载测试图像
    test_images = [
        'test/images/landslide_001.jpg',
        'test/images/flood_002.jpg',
        'test/images/forest_fire_003.jpg'
    ]
    
    # 批量测试
    results = []
    
    for img_path in test_images:
        image = cv2.imread(img_path)
        
        # 推理
        detections = infer.detect(image)
        
        # 打印结果
        print(f"\n{'='*60}")
        print(f"图像: {img_path}")
        print(f"检测到 {len(detections)} 个目标:")
        
        for det in detections:
            print(f"  - {det['class_name']}: {det['confidence']:.2f}")
            print(f"    位置: {det['bbox']}")
        
        # 可视化
        vis_image = infer.visualize(image, detections)
        cv2.imwrite(f"test/results/{os.path.basename(img_path)}", vis_image)
        
        results.append({
            'image': img_path,
            'detections': detections
        })
    
    # 保存结果
    with open('test/results/test_report.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ 测试完成，结果保存在 test/results/")

if __name__ == "__main__":
    test_emergency_plugin()
```

---

## 6. 测试与验证

### 6.1 单元测试

```cpp
// tests/unit/test_emergency_detect.cpp

#include <gtest/gtest.h>
#include "plugins/emergency_management/emergency_detect.h"

class EmergencyDetectTest : public ::testing::Test {
protected:
    framework::plugin::EmergencyDetect* plugin;
    
    void SetUp() override {
        plugin = new framework::plugin::EmergencyDetect();
        plugin->init("models/emergency/v1.0/plugin/config.yaml");
    }
    
    void TearDown() override {
        plugin->deinit();
        delete plugin;
    }
};

TEST_F(EmergencyDetectTest, InitTest) {
    EXPECT_EQ(plugin->get_plugin_name(), "emergency_detect");
    EXPECT_EQ(plugin->get_plugin_version(), "1.0.0");
}

TEST_F(EmergencyDetectTest, ExecuteTest) {
    cv::Mat test_image = cv::imread("test/images/landslide_001.jpg");
    std::vector<framework::Detection> detections;
    
    bool success = plugin->execute(&test_image, &detections);
    
    EXPECT_TRUE(success);
    EXPECT_GT(detections.size(), 0);
}
```

---

### 6.2 集成测试

```python
# tests/integration/test_emergency_integration.py

import pytest
from edge_infer import EdgeInfer

def test_edge_to_cloud():
    """测试云边协同"""
    
    # 初始化边缘推理
    edge_infer = EdgeInfer(
        plugin_name='emergency_management',
        config_path='models/emergency/v1.0/plugin/config.yaml'
    )
    
    # 初始化云端推理
    cloud_infer = CloudInfer(
        api_url='https://api.skyedge.ai'
    )
    
    # 边缘推理
    image = cv2.imread('test/images/landslide_001.jpg')
    edge_results = edge_infer.detect(image)
    
    # 如果需要深度分析，调用云端
    if len(edge_results) > 0:
        # 上传图像
        image_url = upload_to_cloud(image)
        
        # 云端RCMT变化检测
        cloud_results = cloud_infer.change_detection(
            image_url,
            reference_image_url
        )
        
        # 合并结果
        final_results = merge_results(edge_results, cloud_results)
        
        assert len(final_results) > 0
```

---

## 7. 常见问题与解决方案

### 7.1 模型转换问题

**问题1：ONNX转换失败**

```bash
错误：Exporting model to ONNX format failed

解决：
1. 检查PyTorch版本（推荐2.0+）
2. 检查ultralytics版本（推荐8.0.0+）
3. 使用--simplify参数
4. 检查模型是否有不支持的操作
```

**问题2：TensorRT转换失败**

```bash
错误：[TensorRT] ERROR: UNSUPPORTED_NODE

解决：
1. 检查ONNX opset版本（推荐12+）
2. 使用onnx-simplifier简化模型
3. 检查TensorRT版本（推荐8.6+）
4. 查看详细日志：--verbose
```

---

### 7.2 性能问题

**问题：推理速度慢（>100ms）**

```bash
解决方案：
1. 使用FP16精度
2. 减小输入尺寸（640 → 416）
3. 使用INT8量化（需要校准）
4. 优化后处理代码（使用CUDA）
5. 使用batch推理
```

---

### 7.3 集成问题

**问题：插件加载失败**

```bash
错误：dlopen failed: undefined symbol

解决：
1. 检查依赖库是否安装
2. 检查LD_LIBRARY_PATH
3. 重新编译插件（clean build）
4. 检查ABI兼容性
```

---

## 8. 总结

### 8.1 软件工程师工作清单

```markdown
Day 1 (0.5天):
- [ ] 验收模型包
- [ ] PT → ONNX转换
- [ ] ONNX → TensorRT转换
- [ ] 性能测试

Day 2-3 (2天):
- [ ] 编写插件代码（C++）
- [ ] 编写配置文件
- [ ] 编译插件
- [ ] 单元测试

Day 4 (0.5天):
- [ ] 集成测试
- [ ] 端到端测试
- [ ] 打包发布
```

**总计**: 3天/每个部门

---

**维护者**: 空中智能体团队
**最后更新**: 2026-03-09
**版本**: V1.0
**文档位置**: docs/v2_reorganized/05_business/SOFTWARE_ENGINEER_WORKFLOW.md
