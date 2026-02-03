#!/usr/bin/env python3
"""
更新 Plastic_in_River 数据集的类别名称
从数字 ['0', '1', '2', '3'] 更新为有意义的名称
"""

from pathlib import Path

YAML_FILE = Path("D:/github/edge_infer_cloud/data/datasets/Plastic_in_River/data.yaml")

NEW_NAMES = ['Plastic_bag', 'Plastic_bottle', 'Other_plastic_waste', 'Non_plastic_trash']

content = f"""train: ../train/images
val: ../valid/images
test: ../test/images

nc: 4
names: {NEW_NAMES}

roboflow:
  workspace: uni-gbehq
  project: plastic_in_river
  version: 2
  license: CC BY 4.0
  url: https://universe.roboflow.com/uni-gbehq/plastic_in_river/dataset/2
"""

YAML_FILE.write_text(content, encoding='utf-8')
print(f"已更新 {YAML_FILE}")
print(f"\n新类别名称:")
for i, name in enumerate(NEW_NAMES):
    print(f"  {i}: {name}")
