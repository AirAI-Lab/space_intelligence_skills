# SkyEdge AI RCMT 训练框架重构方案 V2.0

> **项目**: RCMT (Recurrent Cross-Memory Transformer)  
> **目标**: 实现完整的训练过程和推理预测，性能超越ChangeFormer  
> **日期**: 2026-02-16  
> **版本**: Final  
> **部署环境**: `rcmt_training_persistent_protected_20260216`

---

## 📋 目录

1. [重构背景与目标](#1-重构背景与目标)
2. [ChangeFormer数据集分析](#2-changeformer数据集分析)
3. [端到端框架设计](#3-端到端框架设计)
4. [多主干架构设计](#4-多主干架构设计)
5. [时序建模设计](#5-时序建模设计)
6. [多任务损失设计](#6-多任务损失设计)
7. [训练流程设计](#7-训练流程设计)
8. [推理评估设计](#8-推理评估设计)
9. [性能优化策略](#9-性能优化策略)

---

## 1. 重构背景与目标

### 1.1 当前问题分析

**现有问题**：
- ❌ 多个训练脚本分散，没有统一入口
- ❌ 没有正常的CI伪标签生成流程
- ❌ 没有完整的端到端训练流程
- ❌ 没有规范的推理评估流程
- ❌ 没有性能监控和优化机制

**根本原因**：
1. **架构不统一**: 多个脚本各自为政，没有统一的框架
2. **流程不完整**: 缺少CI伪标签、数据增强、模型优化等关键环节
3. **评估不标准**: 没有标准化的评估指标和评估流程
4. **优化不系统**: 缺少系统性的性能优化策略

### 1.2 重构目标

**核心目标**：
1. **完整的端到端框架**: 从数据集准备到模型部署的完整流程
2. **CI伪标签生成**: 自动生成伪标签，提升训练效率
3. **多主干架构**: 支持SAM2、DINOv2、CLIP等多种主干
4. **时序建模**: 实现时序一致性学习
5. **多任务损失**: 检测+分割+属性识别的多任务损失
6. **OAT性能**: mIoU>80%, F1>85%, 推理速度<50ms

---

## 2. ChangeFormer数据集分析

### 2.1 主流OTA数据集格式

**ChangeFormer数据集格式**：
```
datasets/
├── LEVIR-MCD/              # LEVIR-MCD数据集
│   ├── train/
│   │   ├── 00001/
│   │   │   ├── 00001_00001.png
│   │   │   ├── 00001_00002.png
│   │   │   └── ...
│   │   └── ...
│   ├── val/
│   └── test/
├── xBD/                      # xBD数据集
└── ...
```

**数据集特点**：
1. **时序对图像**: 同一地点在不同时间拍摄的图像对
2. **二元变化掩码**: 手工标注的二元变化掩码（0=无变化，1=有变化）
3. **多场景**: 城市、农村、季节变化、建设工地等

### 2.2 RCMT数据集格式设计

**RCMT数据集格式**：
```
datasets/
├── LEVIR-MCD/              # LEVIR-MCD数据集（标准）
│   ├── images/               # 原始图像
│   │   ├── 00001_00001.png
│   │   ├── 00001_00002.png
│   │   └── ...
│   ├── masks/                # 变化掩码（二元）
│   │   ├── 00001_00001.png
│   │   ├── 00001_00002.png
│   │   └── ...
│   ├── meta.json              # 元数据（包含时间戳、GPS、天气等）
│   └── splits.json            # 数据集划分（训练/验证/测试）
├── xBD/                      # xBD数据集（标准）
└── ...
```

**元数据格式 (meta.json)**：
```json
{
  "dataset_name": "LEVIR-MCD",
  "description": "LEVIR-MCD dataset for change detection",
  "version": "2.0",
  "date_range": ["2006-06-01", "2012-12-31"],
  "spatial_resolution": "0.1m/pixel",
  "image_format": "png",
  "mask_format": "png",
  "num_pairs": 637,
  "num_classes": 2,
  "labels": ["no-change", "change"]
}
```

**数据集划分 (splits.json)**：
```json
{
  "train": ["00001", "00002", ..., "00500"],
  "val": ["00501", "00502", ..., "00550"],
  "test": ["00551", "00552", ..., "00637"]
}
```

### 2.3 数据集准备流程

**流程图**：
```
原始数据集下载
    ↓
图像对齐（特征点匹配）
    ↓
时序对构建（时间戳匹配）
    ↓
伪标签生成（SAM2+CLIP）
    ↓
数据集划分（训练/验证/测试）
    ↓
RCMT数据集
```

**详细步骤**：
1. **原始数据集下载**: 从官方源下载原始数据集
2. **图像对齐**: 使用特征点匹配（SIFT、ORB、SuperPoint）对齐时序对图像
3. **时序对构建**: 基于时间戳匹配构建时序对（T1, T2）
4. **伪标签生成**: 使用SAM2+CLIP生成伪标签（变化掩码）
5. **数据集划分**: 随机划分训练/验证/测试集（70%/20%/10%）

---

## 3. 端到端框架设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│              RCMT端到端训练框架 V2.0                   │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │              数据层（Data Layer）             │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ 原始图像  │  │ 变化掩码  │  │ 伪标签    │      │  │
│  │  │ (Images) │  │ (Masks)   │  │ (Pseudo)   │      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              预处理层（Preprocessing）        │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ 图像对齐  │  │ 时序对构建│  │ 数据增强   │      │  │
│  │  │ (Alignment)│  │ (Temporal) │  │ (Augment)  │      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              模型层（Model Layer）          │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ 多主干架构  │  │ 时序编码器│  │ 时序解码器│      │  │
│  │  │ (Multi-Backbone)│  │ (TemporalEncoder)│  │ (TemporalDecoder)│      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              损失层（Loss Layer）            │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ 检测损失  │  │ 分割损失  │  │ 属性损失   │      │  │
│  │  │ (Detection)│  │ (Segmentation)│  │ (Attribute)│      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              优化层（Optimization）          │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ 优化器    │  │ 学习率调度│  │ 早停策略   │      │  │
│  │  │ (Optimizer)│  │ (LR Scheduler)│  │ (Early Stop)│      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              评估层（Evaluation）            │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ mIoU评估  │  │ F1评估    │  │ 推理速度评估│      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 3.2 核心组件

#### 3.2.1 数据集管理器 (DatasetManager)

**职责**：
1. 数据集下载和管理
2. 图像对齐和时序对构建
3. 伪标签生成（CI伪标签生成）
4. 数据集划分（训练/验证/测试）

**接口设计**：
```python
class DatasetManager:
    def download_dataset(self, dataset_name: str, save_dir: str):
        """下载原始数据集"""
        pass
    
    def align_images(self, image_t1: str, image_t2: str) -> np.ndarray:
        """对齐图像对（基于特征点匹配）"""
        pass
    
    def build_temporal_pair(self, image_t1: str, image_t2: str, 
                           meta_t1: dict, meta_t2: dict) -> dict:
        """构建时序对（T1, T2）"""
        pass
    
    def generate_pseudo_labels(self, image_t1: str, image_t2: str) -> np.ndarray:
        """生成伪标签（使用SAM2+CLIP）"""
        pass
    
    def split_dataset(self, dataset_dir: str, 
                      train_ratio=0.7, val_ratio=0.2, test_ratio=0.1,
                      seed=42) -> dict:
        """划分数据集（训练/验证/测试）"""
        pass
```

#### 3.2.2 训练管理器 (TrainingManager)

**职责**：
1. 训练流程管理
2. 模型保存和加载
3. 学习率调度和早停
4. 性能监控和日志

**接口设计**：
```python
class TrainingManager:
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.optimizer = None
        self.scheduler = None
        self.early_stop = None
    
    def train(self, model, train_loader, val_loader):
        """训练模型"""
        pass
    
    def save_checkpoint(self, model, optimizer, epoch, metrics):
        """保存检查点"""
        pass
    
    def load_checkpoint(self, checkpoint_path):
        """加载检查点"""
        pass
    
    def configure_optimizer(self, model):
        """配置优化器"""
        pass
    
    def configure_scheduler(self, optimizer):
        """配置学习率调度器"""
        pass
    
    def configure_early_stop(self, patience=10):
        """配置早停策略"""
        pass
```

#### 3.2.3 评估管理器 (EvaluationManager)

**职责**：
1. 模型评估（mIoU, F1, 推理速度）
2. 结果统计和报告生成
3. 性能分析和优化建议

**接口设计**：
```python
class EvaluationManager:
    def __init__(self, config: EvaluationConfig):
        self.config = config
        self.metrics = {}
    
    def evaluate(self, model, test_loader):
        """评估模型"""
        pass
    
    def calculate_miou(self, pred_mask, gt_mask) -> float:
        """计算mIoU"""
        pass
    
    def calculate_f1(self, pred_mask, gt_mask) -> float:
        """计算F1分数"""
        pass
    
    def calculate_inference_time(self, model, image) -> float:
        """计算推理时间"""
        pass
    
    def generate_report(self, metrics) -> dict:
        """生成评估报告"""
        pass
```

---

## 4. 多主干架构设计

### 4.1 多主干架构

**核心思想**：支持多种主干网络（SAM2, DINOv2, CLIP），用户可以自由选择和组合。

**架构图**：
```
┌─────────────────────────────────────────────────────────┐
│              多主干架构（Multi-Backbone）             │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │              主干选择器（Backbone Selector）   │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ SAM2     │  │ DINOv2    │  │ CLIP      │      │  │
│  │  │ (ViT-H)  │  │ (ViT-B)  │  │ (ViT-B)  │      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              特征融合（Feature Fusion）        │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ 特征拼接 │  │ 特征加法  │  │ 特征注意力 │      │  │
│  │  │ (Concat) │  │ (Add)    │  │ (Attention)│      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              时序编码器（Temporal Encoder）   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 4.2 SAM2集成

**SAM2架构**：
- **编码器**: ViT-H (视觉Transformer)
- **解码器**: 掩码解码器（Transformer解码器）
- **提示机制**: 提示驱动的分割

**集成方式**：
```python
class SAM2Backbone(nn.Module):
    def __init__(self, sam2_checkpoint_path: str):
        super().__init__()
        # 加载SAM2预训练模型
        self.model = sam2_model_registry['sam2_vit_h'](checkpoint_path)
        self.image_encoder = self.model.image_encoder
        self.mask_decoder = self.model.mask_decoder
        self.prompt_encoder = self.model.prompt_encoder
    
    def forward(self, image, prompt=None):
        # 图像编码
        image_embeddings = self.image_encoder(image)
        
        # 提示编码
        prompt_embeddings = self.prompt_encoder(prompt) if prompt else None
        
        # 掩码解码
        masks = self.mask_decoder(image_embeddings, prompt_embeddings)
        
        return masks
```

### 4.3 DINOv2集成

**DINOv2架构**：
- **编码器**: ViT-B (视觉Transformer)
- **自监督训练**: DINO自监督训练
- **特征表示**: 全局特征表示

**集成方式**：
```python
class DINOv2Backbone(nn.Module):
    def __init__(self, dinov2_checkpoint_path: str):
        super().__init__()
        # 加载DINOv2预训练模型
        self.model = hub.load('facebook/dinov2_vitb14', checkpoint_path=checkpoint_path)
    
    def forward(self, x):
        # DINOv2前向传播
        features = self.model(x)
        
        return features
```

### 4.4 CLIP集成

**CLIP架构**：
- **图像编码器**: ViT-B (视觉Transformer)
- **文本编码器**: Transformer (文本编码器)
- **多模态对齐**: 图像-文本多模态对齐

**集成方式**：
```python
class CLIPBackbone(nn.Module):
    def __init__(self, clip_checkpoint_path: str):
        super().__init__()
        # 加载CLIP预训练模型
        self.model, _ = clip.load(clip_checkpoint_path)
        self.image_encoder = self.model.visual
        self.text_encoder = self.model.transformer
    
    def forward(self, image, text=None):
        # 图像编码
        image_features = self.image_encoder(image)
        
        # 文本编码
        if text:
            text_features = self.text_encoder(text)
            return image_features, text_features
        
        return image_features
```

### 4.5 多主干融合

**融合策略**：
1. **特征拼接**: 将多个主干的特征拼接
2. **特征加法**: 将多个主干的特征相加
3. **特征注意力**: 使用注意力机制融合多个主干的特征

**实现方式**：
```python
class MultiBackboneFusion(nn.Module):
    def __init__(self, backbone_list, fusion_type='concat'):
        super().__init__()
        self.backbone_list = backbone_list
        self.fusion_type = fusion_type
        
        if fusion_type == 'concat':
            self.fusion = nn.Concatenate()
        elif fusion_type == 'add':
            self.fusion = nn.Add()
        elif fusion_type == 'attention':
            self.fusion = MultiHeadAttention(embed_dim=768)
    
    def forward(self, x):
        # 多主干前向传播
        backbone_features = []
        for backbone in self.backbone_list:
            features = backbone(x)
            backbone_features.append(features)
        
        # 特征融合
        if self.fusion_type == 'concat':
            fused_features = self.fusion(backbone_features)
        elif self.fusion_type == 'add':
            fused_features = self.fusion(backbone_features)
        elif self.fusion_type == 'attention':
            fused_features = self.fusion(backbone_features)
        
        return fused_features
```

---

## 5. 时序建模设计

### 5.1 时序建模架构

**核心思想**：建模时序依赖关系，理解时序变化。

**架构图**：
```
┌─────────────────────────────────────────────────────────┐
│              时序建模（Temporal Modeling）            │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │              时序编码器（Temporal Encoder）   │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ LSTM     │  │ GRU      │  │ Transformer│      │  │
│  │  │ (LSTM)   │  │ (GRU)    │  │ (Trans)   │      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              时序记忆（Temporal Memory）       │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ 短期记忆  │  │ 长期记忆  │  │ 空间记忆   │      │  │
│  │  │ (Short)   │  │ (Long)    │  │ (Spatial)  │      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              时序解码器（Temporal Decoder）   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 5.2 时序编码器（Temporal Encoder）

**核心思想**：编码时序信息（T1, T2），理解时序变化。

**实现方式**：
```python
class TemporalEncoder(nn.Module):
    def __init__(self, feature_dim=768, hidden_dim=512):
        super().__init__()
        self.lstm = nn.LSTM(feature_dim, hidden_dim, batch_first=True)
        self.gru = nn.GRU(feature_dim, hidden_dim, batch_first=True)
        self.transformer = nn.Transformer(d_model=feature_dim, nhead=8, num_encoder_layers=4)
        self.short_term_memory = nn.Parameter(torch.zeros(1, 1, hidden_dim))
        self.long_term_memory = nn.Parameter(torch.zeros(1, 1, feature_dim))
        self.spatial_memory = nn.Parameter(torch.zeros(1, 1, feature_dim))
    
    def forward(self, features_t1, features_t2):
        # 拼接时序特征
        temporal_features = torch.cat([features_t1, features_t2], dim=1)
        
        # LSTM编码
        lstm_out, _ = self.lstm(temporal_features)
        
        # GRU编码
        gru_out, _ = self.gru(temporal_features)
        
        # Transformer编码
        transformer_out = self.transformer(temporal_features)
        
        # 时序记忆
        self.short_term_memory = lstm_out.mean(dim=1, keepdim=True)
        self.long_term_memory = transformer_out.mean(dim=1, keepdim=True)
        self.spatial_memory = features_t2.mean(dim=1, keepdim=True)
        
        return lstm_out, gru_out, transformer_out
```

### 5.3 时序记忆（Temporal Memory）

**核心思想**：短期记忆、长期记忆、空间记忆。

**实现方式**：
```python
class TemporalMemory(nn.Module):
    def __init__(self, feature_dim=768, hidden_dim=512):
        super().__init__()
        self.short_term_memory = nn.LSTM(feature_dim, hidden_dim, batch_first=True)
        self.long_term_memory = nn.LSTM(feature_dim, hidden_dim, batch_first=True)
        self.spatial_memory = nn.Linear(feature_dim, feature_dim)
    
    def forward(self, features):
        # 短期记忆
        short_term_out, _ = self.short_term_memory(features)
        
        # 长期记忆
        long_term_out, _ = self.long_term_memory(features)
        
        # 空间记忆
        spatial_out = self.spatial_memory(features)
        
        return short_term_out, long_term_out, spatial_out
```

### 5.4 时序解码器（Temporal Decoder）

**核心思想**：解码时序信息，预测变化掩码。

**实现方式**：
```python
class TemporalDecoder(nn.Module):
    def __init__(self, feature_dim=512, mask_dim=256):
        super().__init__()
        self.decoder = nn.Transformer(d_model=feature_dim, nhead=8, num_decoder_layers=4)
        self.mask_head = nn.Linear(feature_dim, mask_dim)
    
    def forward(self, encoded_features):
        # 解码
        decoded_features = self.decoder(encoded_features)
        
        # 变化掩码预测
        change_mask = self.mask_head(decoded_features)
        
        return change_mask
```

---

## 6. 多任务损失设计

### 6.1 多任务损失架构

**核心思想**：同时优化检测、分割、属性识别多个任务。

**架构图**：
```
┌─────────────────────────────────────────────────────────┐
│              多任务损失（Multi-Task Loss）            │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │              检测头（Detection Head）          │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ 边界框回归│  │ 目标分类  │  │ 置信度回归│      │  │
│  │  │ (BBox)    │  │ (Class)   │  │ (Conf)    │      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              分割头（Segmentation Head）        │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ 二元分割  │  │ 多类分割  │  │ 属性分割  │      │  │
│  │  │ (Binary)  │  │ (Multi)   │  │ (Attribute)│      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              损失函数（Loss Functions）        │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ 检测损失  │  │ 分割损失  │  │ 属性损失   │      │  │
│  │  │ (Detection)│  │ (Segmentation)│  │ (Attribute)│      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 6.2 检测损失（Detection Loss）

**检测损失**：边界框回归损失 + 目标分类损失 + 置信度损失

**实现方式**：
```python
class DetectionLoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.bbox_loss = nn.L1Loss()
        self.cls_loss = nn.CrossEntropyLoss()
        self.conf_loss = nn.BCELoss()
    
    def forward(self, bbox_pred, bbox_gt, cls_pred, cls_gt, conf_pred, conf_gt):
        # 边界框损失
        bbox_loss = self.bbox_loss(bbox_pred, bbox_gt)
        
        # 目标分类损失
        cls_loss = self.cls_loss(cls_pred, cls_gt)
        
        # 置信度损失
        conf_loss = self.conf_loss(conf_pred, conf_gt)
        
        return bbox_loss + cls_loss + conf_loss
```

### 6.3 分割损失（Segmentation Loss）

**分割损失**：二元分割损失 + 多类分割损失 + 属性分割损失

**实现方式**：
```python
class SegmentationLoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.binary_seg_loss = nn.BCEWithLogitsLoss()
        self.multi_seg_loss = nn.CrossEntropyLoss()
        self.attr_seg_loss = nn.CrossEntropyLoss()
    
    def forward(self, seg_pred, seg_gt):
        # 二元分割损失
        binary_loss = self.binary_seg_loss(seg_pred, seg_gt)
        
        # 多类分割损失
        multi_loss = self.multi_seg_loss(seg_pred, seg_gt)
        
        # 属性分割损失
        attr_loss = self.attr_seg_loss(seg_pred, seg_gt)
        
        return binary_loss + multi_loss + attr_loss
```

### 6.4 属性损失（Attribute Loss）

**属性损失**：时序一致性损失 + 空间一致性损失 + 语义一致性损失

**实现方式**：
```python
class AttributeLoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.temporal_consistency_loss = nn.L1Loss()
        self.spatial_consistency_loss = nn.L1Loss()
        self.semantic_consistency_loss = nn.KLDivLoss()
    
    def forward(self, attr_pred, attr_gt):
        # 时序一致性损失
        temporal_loss = self.temporal_consistency_loss(attr_pred, attr_gt)
        
        # 空间一致性损失
        spatial_loss = self.spatial_consistency_loss(attr_pred, attr_gt)
        
        # 语义一致性损失
        semantic_loss = self.semantic_consistency_loss(attr_pred, attr_gt)
        
        return temporal_loss + spatial_loss + semantic_loss
```

---

## 7. 训练流程设计

### 7.1 完整训练流程

**流程图**：
```
1. 数据集准备
   ├── 1.1 原始数据集下载
   ├── 1.2 图像对齐（特征点匹配）
   ├── 1.3 时序对构建（时间戳匹配）
   ├── 1.4 伪标签生成（SAM2+CLIP）
   └── 1.5 数据集划分（训练/验证/测试）

2. 模型初始化
   ├── 2.1 多主干初始化（SAM2+DINOv2+CLIP）
   ├── 2.2 时序编码器初始化（LSTM+GRU+Transformer）
   └── 2.3 损失函数初始化（检测+分割+属性）

3. 训练
   ├── 3.1 前向传播
   ├── 3.2 损失计算
   ├── 3.3 反向传播
   └── 3.4 参数更新

4. 验证
   ├── 4.1 模型评估（mIoU, F1, 推理速度）
   └── 4.2 性能分析

5. 保存
   ├── 5.1 模型保存（PyTorch）
   ├── 5.2 模型导出（ONNX）
   └── 5.3 模型发布（HuggingFace）

6. 部署
   ├── 6.1 模型量化（FP16/INT8）
   ├── 6.2 模型优化（TensorRT）
   └── 6.3 模型部署（边缘部署）
```

### 7.2 训练脚本设计

**训练脚本**：`train_rcmt.py`

**核心功能**：
1. 数据加载（多线程）
2. 模型训练（支持混合精度）
3. 验证和测试
4. 模型保存和导出
5. 性能监控和日志

**接口设计**：
```python
def train_rcmt(config):
    # 数据加载
    train_loader = DataLoader(...)
    val_loader = DataLoader(...)
    test_loader = DataLoader(...)
    
    # 模型初始化
    model = RCMTModel(config)
    
    # 训练
    for epoch in range(config.num_epochs):
        train_loss = train_one_epoch(model, train_loader, config)
        val_loss = validate(model, val_loader, config)
        
        # 保存检查点
        if epoch % config.save_interval == 0:
            save_checkpoint(model, optimizer, epoch, train_loss)
    
    # 测试
    test_metrics = test(model, test_loader, config)
    
    # 模型导出
    export_model(model, config.export_path)

def train_one_epoch(model, dataloader, config):
    model.train()
    total_loss = 0
    for batch_idx, (images_t1, images_t2, masks, attrs) in enumerate(dataloader):
        # 前向传播
        pred_masks, pred_attrs = model(images_t1, images_t2)
        
        # 损失计算
        detection_loss = model.detection_loss(pred_attrs, attrs)
        segmentation_loss = model.segmentation_loss(pred_masks, masks)
        attribute_loss = model.attribute_loss(pred_attrs, attrs)
        total_loss = detection_loss + segmentation_loss + attribute_loss
        
        # 反向传播
        total_loss.backward()
        optimizer.step()
        optimizer.zero_grad()
    
    return total_loss

def validate(model, dataloader, config):
    model.eval()
    total_miou = 0
    total_f1 = 0
    with torch.no_grad():
        for batch_idx, (images_t1, images_t2, masks, attrs) in enumerate(dataloader):
            # 前向传播
            pred_masks, pred_attrs = model(images_t1, images_t2)
            
            # mIoU计算
            miou = calculate_miou(pred_masks, masks)
            total_miou += miou
            
            # F1计算
            f1 = calculate_f1(pred_masks, masks)
            total_f1 += f1
    
    avg_miou = total_miou / len(dataloader)
    avg_f1 = total_f1 / len(dataloader)
    
    return avg_miou, avg_f1

def test(model, dataloader, config):
    model.eval()
    total_miou = 0
    total_f1 = 0
    total_inference_time = 0
    with torch.no_grad():
        for batch_idx, (images_t1, images_t2, masks, attrs) in enumerate(dataloader):
            # 推理时间测量
            start_time = time.time()
            pred_masks, pred_attrs = model(images_t1, images_t2)
            end_time = time.time()
            total_inference_time += (end_time - start_time)
            
            # mIoU计算
            miou = calculate_miou(pred_masks, masks)
            total_miou += miou
            
            # F1计算
            f1 = calculate_f1(pred_masks, masks)
            total_f1 += f1
    
    avg_miou = total_miou / len(dataloader)
    avg_f1 = total_f1 / len(dataloader)
    avg_inference_time = total_inference_time / len(dataloader)
    
    return avg_miou, avg_f1, avg_inference_time
```

---

## 8. 推理评估设计

### 8.1 推理评估流程

**流程图**：
```
1. 模型加载
   ├── 1.1 PyTorch模型加载
   ├── 1.2 ONNX模型加载
   └── 1.3 TensorRT模型加载

2. 推理
   ├── 2.1 前向传播
   ├── 2.2 后处理
   └── 2.3 结果输出

3. 评估
   ├── 3.1 mIoU计算
   ├── 3.2 F1计算
   ├── 3.3 推理速度计算
   └── 3.4 资源占用计算

4. 报告
   ├── 4.1 评估报告
   ├── 4.2 性能报告
   └── 4.3 优化建议
```

### 8.2 推理脚本设计

**推理脚本**：`inference_rcmt.py`

**核心功能**：
1. 模型加载（PyTorch/ONNX/TensorRT）
2. 推理执行（支持批推理）
3. 结果后处理（NMS、阈值化）
4. 结果可视化（可视化工具）

**接口设计**：
```python
def inference_rcmt(config):
    # 模型加载
    model = load_model(config.model_path, config.model_type)
    
    # 推理
    results = []
    with torch.no_grad():
        for image_t1, image_t2 in config.image_pairs:
            # 前向传播
            start_time = time.time()
            pred_masks, pred_attrs = model(image_t1, image_t2)
            end_time = time.time()
            
            # 后处理
            pred_masks = postprocess(pred_masks)
            
            # 结果输出
            results.append({
                'image_t1': image_t1,
                'image_t2': image_t2,
                'pred_mask': pred_masks,
                'pred_attrs': pred_attrs,
                'inference_time': end_time - start_time
            })
    
    # 评估
    metrics = evaluate(results, config.gt_masks)
    
    # 报告
    report = generate_report(results, metrics)
    
    return results, metrics, report

def load_model(model_path, model_type='pytorch'):
    if model_type == 'pytorch':
        model = torch.load(model_path)
        model.eval()
    elif model_type == 'onnx':
        import onnxruntime as ort
        session = ort.InferenceSession(model_path)
        return session
    elif model_type == 'tensorrt':
        import tensorrt as tr
        runtime = tr.Runtime(TRT_LOGGER)
        engine = runtime.load_cuda_engine(model_path)
        return engine
    else:
        raise ValueError(f"Unsupported model type: {model_type}")

def postprocess(pred_masks):
    # NMS
    pred_masks = nms(pred_masks)
    
    # 阈值化
    pred_masks = (pred_masks > 0.5).float()
    
    return pred_masks

def evaluate(results, gt_masks):
    # mIoU计算
    total_miou = 0
    for result, gt_mask in zip(results, gt_masks):
        miou = calculate_miou(result['pred_mask'], gt_mask)
        total_miou += miou
    
    # F1计算
    total_f1 = 0
    for result, gt_mask in zip(results, gt_masks):
        f1 = calculate_f1(result['pred_mask'], gt_mask)
        total_f1 += f1
    
    # 推理速度计算
    total_inference_time = sum([result['inference_time'] for result in results])
    avg_inference_time = total_inference_time / len(results)
    
    return {
        'miou': total_miou / len(results),
        'f1': total_f1 / len(results),
        'avg_inference_time': avg_inference_time
    }

def generate_report(results, metrics):
    # 评估报告
    report = {
        'num_images': len(results),
        'miou': metrics['miou'],
        'f1': metrics['f1'],
        'avg_inference_time': metrics['avg_inference_time'],
        'timestamp': datetime.now().isoformat()
    }
    
    return report
```

---

## 9. 性能优化策略

### 9.1 优化策略

**优化目标**：
1. **mIoU>80%**: 超越ChangeFormer
2. **F1>85%**: 超越ChangeFormer
3. **推理速度<50ms**: 满足实时需求

**优化策略**：
1. **混合精度训练**: FP16混合精度训练，降低显存占用
2. **梯度累积**: 梯度累积降低显存占用
3. **数据并行**: 数据并行加速训练
4. **分布式训练**: 多卡分布式训练
5. **模型压缩**: 量化、剪枝、蒸馏

### 9.2 混合精度训练

**实现方式**：
```python
# 混合精度训练
model = RCMTModel(config).cuda()
model.half()  # 转为FP16

optimizer = torch.optim.AdamW(model.parameters(), lr=config.lr)
scaler = torch.cuda.amp.GradScaler(enabled=True)

for epoch in range(config.num_epochs):
    for batch_idx, (images_t1, images_t2, masks, attrs) in enumerate(train_loader):
        images_t1 = images_t1.cuda().half()
        images_t2 = images_t2.cuda().half()
        masks = masks.cuda()
        attrs = attrs.cuda()
        
        # 自动混合精度训练
        with torch.cuda.amp.autocast():
            pred_masks, pred_attrs = model(images_t1, images_t2)
            
            detection_loss = model.detection_loss(pred_attrs, attrs)
            segmentation_loss = model.segmentation_loss(pred_masks, masks)
            attribute_loss = model.attribute_loss(pred_attrs, attrs)
            
            total_loss = detection_loss + segmentation_loss + attribute_loss
        
        scaler.scale(total_loss.backward())
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad()
```

### 9.3 模型量化（FP16/INT8）

**实现方式**：
```python
# 模型量化
import torch.quantization as quant

model = RCMTModel(config)
model.eval()

# 量化配置
quantized_model = quant.quantize_dynamic(
    model,
    {torch.nn.Linear, torch.nn.Conv2d},  # 量化Linear和Conv2d
     dtype=torch.qint8  # 量化为INT8
)
```

### 9.4 TensorRT优化

**实现方式**：
```python
# TensorRT优化
import tensorrt as tr

TRT_LOGGER = tr.Logger(tr.Logger.INFO)

model = RCMTModel(config)
model.eval()

# TensorRT引擎构建
builder = tr.Builder(TRT_LOGGER)
network = builder.create_network(1, 1)
with tr.Builder(TRT_LOGGER).create_network(1, 1) as network, builder:
    with builder.create_network(1, 1) as network, builder:
        builder.add_input('image_t1', dtype=tr.float32)
        builder.add_input('image_t2', dtype=tr.float32)
        builder.add_output('pred_mask', dtype=tr.float32)
        builder.add_output('pred_attrs', dtype=tr.float32)
        
        # 添加自定义层
        network.add_plugin(tr.Plugin('RCMTPlugin'))

# 构建和序列化
engine = builder.build_cuda_engine('rcmt.engine', builder.create_network(1, 1).get_network(0))
engine.serialize('rcmt.trt')
```

---

**文档状态**: Final  
**最后更新**: 2026-02-16  
**作者**: SkyEdge AI Team
