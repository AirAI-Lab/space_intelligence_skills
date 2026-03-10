# V4 vs V6 配置对比分析

## 问题3答案：为什么batch_size=16会OOM？

### 配置对比

| 配置项 | V4 (train_rcmt_v4_final.py) | V6 (train_rcmt_swin.py) | 差异 |
|--------|----------------------------|------------------------|------|
| **模型** | build_rcmt_v3_hybrid | RCMT_V3_Swin_Temporal | 不同！ |
| **depths** | [2, 2, 2, 2] (默认) | [2, 2, 18, 2] | **V6的Stage3有18层！** |
| **embed_dim** | 64 (第一个stage) | 128 | **V6的维度翻倍！** |
| **num_heads** | 8 (统一) | [4, 8, 16, 32] | V6逐级增加 |
| **参数量** | ~11.77M | ~147.6M | **V6是V4的12.5倍！** |
| **batch_size** | 16 ✅ | 16 ❌ OOM | 相同但显存需求差异巨大 |

### OOM根本原因

**V6配置是Swin-Base级别**：
- Stage 3有18个Transformer blocks
- embed_dim=128（是V4的2倍）
- 参数量147.6M（V4的12.5倍）
- 显存需求：21.21GB > 16GB可用

**V4配置是Swin-Tiny级别**：
- 所有Stage只有2个blocks
- embed_dim=64
- 参数量11.77M
- 显存需求：<4GB

### 问题4答案：depths是否正确？

**V4实际使用**：`depths=[2, 2, 2, 2]` (Swin-Tiny)  
**V6配置使用**：`depths=[2, 2, 18, 2]` (Swin-Base)

❌ **不正确！V6配置远大于V4**

---

## 解决方案

### 方案1：使用V4相同配置（推荐）

```python
# 使用V4的Swin-Tiny配置
self.model = build_rcmt_v3_hybrid(
    drop_path=args.drop_path,
    encoder_depths=[2, 2, 2, 2],  # Swin-Tiny
    encoder_dims=[64, 128, 256, 512],
    num_heads=8,
    use_btf=True,
    use_msa=True
)
```

**优点**：
- ✅ 参数量11.77M（与V4相同）
- ✅ batch_size=16不会OOM
- ✅ 已验证有效（V4达到0.9201 F1）

**缺点**：
- ❓ build_rcmt_v3_hybrid是混合架构还是纯Swin？需要确认

---

### 方案2：使用Swin-Small配置（折中）

```python
# Swin-Small配置
depths=[2, 2, 18, 2]  # 与当前V6相同
embed_dim=96  # 降低维度（128→96）
num_heads=[3, 6, 12, 24]
```

**参数量**：~60M（介于V4和V6之间）  
**batch_size**：可能需要降到8

---

### 方案3：使用Swin-Tiny（最保守）

```python
# 纯Swin-Tiny
depths=[2, 2, 2, 2]
embed_dim=96
num_heads=[3, 6, 12, 24]
window_size=7
```

**参数量**：~28M  
**batch_size**：16 ✅

---

## 建议采用的方案

**推荐方案1（V4配置）**，理由：
1. ✅ 已验证有效（F1=0.9201 > 0.92）
2. ✅ batch_size=16不会OOM
3. ✅ 训练速度快
4. ✅ 参数效率高

**关键修改**：
```python
# train_rcmt_swin.py
# 使用V4的build_rcmt_v3_hybrid配置
from models.model import build_rcmt_v3_hybrid

self.model = build_rcmt_v3_hybrid(
    drop_path=args.drop_path,
    use_btf=True,
    use_msa=True,
    use_deep_supervision=True
).to(self.device)
```

**或者直接使用Swin-Tiny配置的RCMT_V3_Swin_Temporal**：
```python
# 使用Swin-Tiny配置
self.model = RCMT_V3_Swin_Temporal(
    embed_dim=96,  # 降低
    depths=[2, 2, 2, 2],  # Tiny配置
    num_heads=[3, 6, 12, 24],
    window_size=7,
    drop_path_rate=0.3,
    use_temporal_fusion=True
)
```

---

## 总结

**问题根源**：V6使用Swin-Base配置（147.6M参数），V4使用Swin-Tiny配置（11.77M参数）

**解决方案**：使用V4相同或相近的Swin-Tiny配置，确保batch_size=16不会OOM
