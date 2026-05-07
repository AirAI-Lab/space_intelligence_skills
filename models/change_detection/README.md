# 变换检测系统 (Change Detection)

基于 C-RADIOv4 零样本分割的时序变换检测系统。

## 功能

- **违建检测**: 新增/扩建建筑物
- **堆放物检测**: 垃圾倾倒、建筑废料
- **车辆检测**: 违法停车、新增车辆
- **地表变化**: 裸地、施工区域、植被变化

## 架构

```
前期图像 (T1) ──→ C-RADIOv4 分割 ──→ mask_t1
                                            ├──→ 差分检测 ──→ 变化区域 ──→ 分类
后期图像 (T2) ──→ C-RADIOv4 分割 ──→ mask_t2
```

## 快速开始

```bash
python models/change_detection/models/unified.py \
    --earlier earlier.jpg \
    --later later.jpg \
    --config models/change_detection/configs/change_detection.yaml \
    --output result.jpg
```

## 批量评估

```bash
python models/change_detection/scripts/evaluate_change_detection.py \
    --config models/change_detection/configs/change_detection.yaml \
    --data_dir /path/to/data \
    --output_dir outputs/change_detection
```

## 依赖

- C-RADIOv4-H (1.68 GB)
- SigLIP2-Giant (7.5 GB)
- NVlabs_RADIO 代码

详见 `water_inspection/docs/MANUAL.md` 第10章。
