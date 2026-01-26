# 数据管理指南

本指南介绍如何使用平台的数据管理功能，包括数据上传、数据集创建、AI辅助标注等。

## 数据集目录结构（参考YOLOv8）

平台采用与YOLOv8相同的数据集目录结构：

```
datasets/
├── my_dataset/
│   ├── data.yaml           # 数据集配置文件
│   ├── images/
│   │   ├── train/         # 训练图像
│   │   └── val/           # 验证图像
│   └── labels/
│       ├── train/         # YOLO格式标注文件
│       └── val/
```

## 第一步：准备数据集

### 数据格式要求

- **图像格式**：JPG、PNG
- **标注格式**：YOLO TXT格式（每行一个目标）
- **图像尺寸**：建议统一（如640x640）

### YOLO标注格式说明

每个标注文件对应一张图像，文件名相同（扩展名不同）：

```
# class_id center_x center_y width height (归一化坐标)
0 0.5 0.5 0.3 0.4
1 0.2 0.3 0.15 0.2
```

字段说明：
- class_id：类别ID（从0开始）
- center_x, center_y：边界框中心点坐标（0-1）
- width, height：边界框宽高（0-1）

## 第二步：上传数据

### 方式一：通过Web界面上传

1. 点击"数据管理" → "上传数据"
2. 选择上传方式：
   - **文件夹上传**：保持目录结构
   - **压缩包上传**：支持ZIP格式

3. 选择本地文件或文件夹
4. 点击"开始上传"
5. 等待上传完成

### 方式二：通过命令行上传

#### 使用edge-cli工具

```bash
# 安装edge-cli
pip install edge-cli

# 上传数据集
edge-cli data upload \
    --source /path/to/dataset \
    --name my_dataset \
    --server http://localhost:8080
```

#### 使用curl上传

```bash
# 上传单个文件
curl -X POST http://localhost:8080/api/v1/data/upload \
  -F "file=@/path/to/image.jpg" \
  -F "path=my_dataset/images/train"

# 上传压缩包
curl -X POST http://localhost:8080/api/v1/data/upload \
  -F "file=@/path/to/dataset.zip" \
  -F "extract=true"
```

## 第三步：生成data.yaml配置

### 方式一：自动生成

1. 进入"数据管理" → "数据集"
2. 选择已上传的数据集
3. 点击"生成配置"
4. 填写类别信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| 数据集名称 | 显示名称 | 安全帽检测数据集 |
| 类别列表 | 类别名称 | person,car,dog |
| 训练集比例 | 训练集占比 | 0.8 |

5. 系统自动生成data.yaml

### 方式二：通过CLI生成

```bash
edge-cli data create-yaml \
    --dataset my_dataset \
    --names person car dog \
    --nc 3 \
    --train-ratio 0.8 \
    --val-ratio 0.2
```

### 方式三：手动编辑

生成的data.yaml示例：

```yaml
# 数据集配置
path: /datasets/my_dataset  # 数据集根目录
train: images/train           # 训练集相对路径
val: images/val               # 验证集相对路径

# 类别信息
names:
  0: person
  1: car
  2: dog
nc: 3  # 类别数量

# 数据增强参数（可选）
augmentation:
  hsv_h: 0.015    # 色调调整
  hsv_s: 0.7      # 饱和度调整
  hsv_v: 0.4      # 明度调整
  degrees: 0.0    # 旋转角度
  translate: 0.1  # 平移比例
  scale: 0.5      # 缩放因子
  fliplr: 0.5     # 左右翻转概率
  mosaic: 1.0     # 马赛克增强概率
  mixup: 0.0      # 混合增强概率
```

## 第四步：AI辅助标注（可选）

如果数据集没有标注或标注质量不佳，可以使用AI辅助标注功能。

### 启动AI预标注

1. 进入"数据管理" → "数据集"
2. 选择数据集，点击"AI标注"
3. 配置标注任务：

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| 推理模型 | 选择预训练模型 | yolov8n.pt |
| 目标设备 | 选择边缘设备 | EDGE_001 |
| 置信度阈值 | 检测置信度 | 0.25 |

4. 点击"开始标注"
5. 系统自动进行推理预标注

### 监控标注进度

标注任务页面显示：

- 总样本数
- 已处理数
- 当前处理文件
- 预计剩余时间
- 实时日志

### 人工修正标注

1. 标注完成后，进入"标注修正"页面
2. 显示原图和AI标注结果
3. 可以进行以下操作：
   - **添加标注**：绘制新的边界框
   - **修改标注**：调整边界框位置
   - **删除标注**：删除误检
   - **修改类别**：更改目标类别

4. 保存修正结果

### 标注质量评估

系统自动评估标注质量：

- 检测率：AI检测到的目标比例
- 准确率：标注正确的比例
- 置信度分布：各置信度区间统计

## 数据集管理

### 查看数据集统计

数据集详情页显示：

| 统计项 | 数值 |
|--------|------|
| 总样本数 | 1000 |
| 训练集 | 800 |
| 验证集 | 200 |
| 总标注数 | 3500 |
| 类别分布 | person:2000, car:1000, dog:500 |

### 数据集版本管理

每次修改都会创建新版本：

1. 点击"创建版本"
2. 填写版本说明
3. 系统保存快照

可以随时切换到历史版本。

### 导出/导入数据集

#### 导出数据集

```bash
# 导出为ZIP
edge-cli data export \
    --dataset my_dataset \
    --format zip \
    --output my_dataset.zip
```

#### 导入数据集

```bash
# 导入数据集
edge-cli data import \
    --source my_dataset.zip \
    --name imported_dataset
```

## 数据增强

平台支持多种数据增强策略：

| 增强方式 | 说明 | 参数 |
|---------|------|------|
| 色彩变换 | HSV调整 | hsv_h, hsv_s, hsv_v |
| 几何变换 | 旋转、翻转、缩放 | degrees, fliplr, scale |
| 混合增强 | Mosaic、MixUp | mosaic, mixup |

可以在data.yaml中配置增强参数。

## 常见问题

### Q1: 上传大文件失败怎么办？

- 检查网络连接
- 分批上传
- 使用压缩包格式

### Q2: 如何验证标注格式？

```bash
# 验证标注格式
edge-cli data validate \
    --dataset my_dataset \
    --format yolo
```

### Q3: AI标注不准确怎么办？

- 调整置信度阈值
- 使用更合适的预训练模型
- 人工修正后重新训练

## 下一步

- 阅读 [模型训练指南](04_training.md)
- 阅读 [模型部署指南](05_model_deploy.md)
