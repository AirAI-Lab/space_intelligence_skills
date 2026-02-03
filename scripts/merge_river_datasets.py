#!/usr/bin/env python3
"""
合并两个河道检测数据集为统一的 7 类数据集
- Drowning Detection (3类) 保持索引 0-2
- Plastic_in_River (4类) 重新映射到索引 3-6
"""

import os
import shutil
from pathlib import Path
from collections import defaultdict

# 数据集路径
DROWNING_PATH = Path("D:/github/edge_infer_cloud/data/datasets/Drowning Detection")
PLASTIC_PATH = Path("D:/github/edge_infer_cloud/data/datasets/Plastic_in_River")
OUTPUT_PATH = Path("D:/github/edge_infer_cloud/data/datasets/River_Detection_7Class")

# 类别映射
DROWNING_CLASSES = {
    0: "Drowning",
    1: "Person_out_of_water",
    2: "Swimming"
}

PLASTIC_CLASSES = {
    0: 3,  # Plastic_bag
    1: 4,  # Plastic_bottle
    2: 5,  # Other_plastic_waste
    3: 6   # Non_plastic_trash
}

ALL_CLASSES = [
    'Drowning', 'Person_out_of_water', 'Swimming',
    'Plastic_bag', 'Plastic_bottle', 'Other_plastic_waste', 'Non_plastic_trash'
]

def create_directory_structure():
    """创建合并数据集的目录结构"""
    for split in ['train', 'valid', 'test']:
        (OUTPUT_PATH / split / 'images').mkdir(parents=True, exist_ok=True)
        (OUTPUT_PATH / split / 'labels').mkdir(parents=True, exist_ok=True)

def copy_drowning_dataset(split):
    """复制 Drowning Detection 数据集（保持类别索引）"""
    src_images = DROWNING_PATH / split / 'images'
    src_labels = DROWNING_PATH / split / 'labels'

    if not src_images.exists():
        print(f"    警告: {src_images} 不存在，跳过")
        return 0

    count = 0
    for img_file in src_images.glob('*.jpg'):
        # 复制图片
        shutil.copy2(img_file, OUTPUT_PATH / split / 'images' / img_file.name)

        # 复制标签（类别索引保持不变）
        label_file = img_file.stem + '.txt'
        src_label = src_labels / label_file
        if src_label.exists():
            shutil.copy2(src_label, OUTPUT_PATH / split / 'labels' / label_file)

        count += 1
    return count

def copy_and_remap_plastic_dataset(split):
    """复制 Plastic_in_River 数据集并重新映射类别索引"""
    src_images = PLASTIC_PATH / split / 'images'
    src_labels = PLASTIC_PATH / split / 'labels'

    if not src_images.exists():
        print(f"    警告: {src_images} 不存在，跳过")
        return 0

    count = 0
    label_stats = defaultdict(int)

    for img_file in src_images.glob('*.jpg'):
        # 复制图片
        shutil.copy2(img_file, OUTPUT_PATH / split / 'images' / img_file.name)

        # 处理标签文件（重新映射类别索引）
        label_file = img_file.stem + '.txt'
        src_label = src_labels / label_file
        dst_label = OUTPUT_PATH / split / 'labels' / label_file

        if src_label.exists():
            with open(src_label, 'r') as f_in, open(dst_label, 'w') as f_out:
                for line in f_in:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_id = int(parts[0])
                        if class_id in PLASTIC_CLASSES:
                            new_class_id = PLASTIC_CLASSES[class_id]
                            # 重新映射类别索引
                            parts[0] = str(new_class_id)
                            f_out.write(' '.join(parts) + '\n')
                            label_stats[class_id] += 1

        count += 1
    return count

def generate_data_yaml():
    """生成合并后的 data.yaml"""
    content = f"""train: train/images
val: valid/images
test: test/images

nc: {len(ALL_CLASSES)}
names: {ALL_CLASSES}

roboflow:
  workspace: merged
  project: river_detection_7class
  version: 1
  license: CC BY 4.0
"""
    with open(OUTPUT_PATH / 'data.yaml', 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    print("=" * 60)
    print("河道检测数据集合并工具")
    print("=" * 60)

    # 创建目录结构
    print("\n1. 创建目录结构...")
    create_directory_structure()
    print(f"   输出目录: {OUTPUT_PATH}")

    # 合并数据集
    stats = defaultdict(int)
    for split in ['train', 'valid', 'test']:
        print(f"\n2. 处理 {split} 数据集...")

        # 复制 Drowning Detection
        d_count = copy_drowning_dataset(split)
        print(f"   Drowning Detection: {d_count} 张图片")

        # 复制并重新映射 Plastic_in_River
        p_count = copy_and_remap_plastic_dataset(split)
        print(f"   Plastic_in_River: {p_count} 张图片 (类别索引已重新映射 0-3 → 3-6)")

        stats[split] = d_count + p_count

    # 生成 data.yaml
    print("\n3. 生成 data.yaml...")
    generate_data_yaml()
    print("   data.yaml 已生成")

    # 统计信息
    print("\n" + "=" * 60)
    print("合并完成！")
    print("=" * 60)
    print(f"\n输出目录: {OUTPUT_PATH}")
    print(f"\n数据统计:")
    print(f"  训练集: {stats['train']} 张")
    print(f"  验证集: {stats['valid']} 张")
    print(f"  测试集: {stats['test']} 张")
    print(f"  总计: {sum(stats.values())} 张")
    print(f"\n7 类类别定义:")
    for i, cls in enumerate(ALL_CLASSES):
        original = " (Drowning)" if i <= 2 else f" (Plastic {i-3})"
        print(f"  {i}: {cls}{original}")
    print("\n现在可以在管理平台中选择 'River_Detection_7Class' 数据集进行训练！")
    print("\n下一步:")
    print("  1. 访问 http://localhost:3000")
    print("  2. 进入数据集管理")
    print("  3. 选择'本地路径'方式")
    print("  4. 输入路径: River_Detection_7Class")
    print("  5. 等待验证完成后创建训练任务")

if __name__ == '__main__':
    main()
