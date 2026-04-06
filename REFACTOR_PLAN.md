# 水质检测模型代码重构计划

## 任务概述
重构 `/app/water_inspection/models/open_vocab/` 目录，合并多个segmentor版本，建立清晰的代码架构。

## 当前问题
1. **代码混乱**: 5个不同的segmentor实现
   - radio_segmentor.py
   - two_stage_segmentor.py  
   - radio_segmentor_v4_method.py
   - hybrid_segmentor.py
   - radseg_segmentor.py

2. **类别定义不一致**: 代码中使用9类，需要改为7类
   - 移除: brown_water, yellow_water
   - 新增: turbid_water
   - 合并: milky_water + foam_water → milky_foam_water

3. **提示词分散**: 两个prompts文件需要合并

## 目标架构

```
models/open_vocab/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── backbone.py          # RADIO backbone封装
│   ├── segmentor.py         # 主分割器（统一版本）
│   └── classifier.py        # SigLIP2文本对齐分类器
├── prompts/
│   └── water_quality.yaml   # 合并后的提示词文件
└── utils/
    ├── __init__.py
    ├── visualization.py     # 可视化工具
    └── evaluation.py        # 评估工具
```

## 核心需求

### 1. 类别定义 (7类)
```python
CLASS_COLORS = {
    "black_water": (0, 0, 180),           # 深蓝色
    "turbid_water": (42, 100, 170),       # 茶色
    "red_water": (0, 0, 255),             # 红色
    "green_water": (0, 200, 0),           # 绿色
    "milky_foam_water": (200, 200, 200),  # 浅灰色
    "dam_seepage": (100, 100, 100),       # 深灰色
    "normal_water": (200, 200, 100),      # 淡黄色(背景)
}

DETECTION_CLASSES = [
    "black_water", "turbid_water", "red_water", 
    "green_water", "milky_foam_water", "dam_seepage"
]
```

### 2. 零样本分割流程
1. **RADIO分割**: 精准分割水区域和坝体区域
2. **SigLIP2分类**: 使用提示词对分割区域分类
3. **输出**: 6类异常水质检测结果

### 3. 评估要求
- 使用109张样本 + GT masks
- 评估RADIO分割IoU
- 评估分类准确率
- 统计颜色分布

**重要**: 样本用于修正提示词和验证，**不是训练**！

## RADIO模块验证要点
- 确认patch、sam3、dinov3等模块正确加载
- 验证分割能力（使用GT评估）
- 参考segRADIO实现

## 数据集信息
- 位置: `/app/water_inspection/data/datasets/`
- 图片: 109张
- GT masks: 127个
- 元数据: JSON格式（包含类别、bbox等）

## 执行步骤
1. 分析现有代码，选择最佳实现
2. 设计新架构
3. 创建统一的segmentor
4. 整合提示词文件
5. 编写评估脚本
6. 验证RADIO模块
7. 测试并生成报告
