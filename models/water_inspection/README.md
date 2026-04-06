# 水利巡检模块 (Water Inspection)

## 目录结构

```
models/water_inspection/
├── scripts/              # 核心脚本
│   ├── train_lightweight_classifier.py      # 训练轻量级分类器
│   ├── generate_visualization_fixed.py      # 生成可视化（中文支持）
│   ├── generate_visualization.py            # 生成可视化
│   └── run_sam3_eval_simplified.py          # SAM3评估脚本
├── docs/                 # 文档
│   ├── 2026-04-05-work-summary.md          # 工作总结
│   ├── 2026-04-06-optimization-analysis.md # 优化分析
│   ├── 2026-04-06-SAM3-optimization-final-report.md # SAM3最终报告
│   └── v4.1_evaluation_report.md           # v4.1评估报告
├── outputs/              # 输出文件
│   └── (评估结果、报告等)
└── README.md            # 本文件
```

## 核心代码位置

### 分割器
- `models/open_vocab/core/segmentor.py` - 主分割器
- `models/open_vocab/core/backbone.py` - RADIO backbone

### 分类器
- `models/classifier/lightweight_classifier.pkl` - 训练好的SVM分类器
- `models/classifier/scaler.pkl` - 特征标准化器

### 配置
- `config/prompts.yaml` - 提示词配置
- `config/water_inspection.yaml` - 水利巡检配置

## 使用方法

### 1. 训练分类器
```bash
cd models/water_inspection/scripts
python train_lightweight_classifier.py
```

### 2. 生成可视化
```bash
python generate_visualization_fixed.py
```

### 3. 运行评估
```bash
python run_sam3_eval_simplified.py
```

## 性能指标

### 当前性能（v4.1）
- **分割**: IoU 48.8%, F1 63.8%
- **分类**: 准确率 85.3% (109张完整数据集)

### 优化目标
- **短期**: 后处理调优 (+3-5% IoU)
- **中期**: DINOv3融合 (+5-10% IoU)
- **长期**: SAM3精细化 (+10-15% IoU)

## 相关文档

- [优化分析报告](docs/2026-04-06-optimization-analysis.md)
- [SAM3最终报告](docs/2026-04-06-SAM3-optimization-final-report.md)
- [工作总结](docs/2026-04-05-work-summary.md)

## 更新历史

- 2026-04-06: 整理代码结构，移动核心文件到 `models/water_inspection`
- 2026-04-05: 完成v4.1 P0优化，达到85.3%准确率
- 2026-04-04: 完成代码架构重构，统一为7类
