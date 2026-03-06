# 论文精读汇总

**生成时间**: 2026-03-04
**论文数量**: 10

---

## 📚 已精读论文列表

1. [BIT](BIT_analysis.md)
2. [ChangeCLIP](ChangeCLIP_analysis.md)
3. [ChangeFormer](ChangeFormer_analysis.md)
4. [CMNet](CMNet_analysis.md)
5. [FC-Siam_Daudt2018](FC-Siam_Daudt2018_analysis.md)
6. [GSTM-SCD](GSTM-SCD_analysis.md)
7. [Open-CD](Open-CD_analysis.md)
8. [PeftCD](PeftCD_analysis.md)
9. [SAM2-CD](SAM2-CD_analysis.md)
10. [Tiny_CD](Tiny_CD_analysis.md)


---

## 📊 待提取的关键信息

### 1. LEVIR-CD 数据汇总表

| 论文 | F1 (%) | IoU (%) | Params (M) | FPS |
|------|--------|---------|------------|-----|
| BIT | 90.87 | 83.45 | 27.8 | ~28 |
| ChangeFormer | 91.45 | ? | 24.5 | ~35 |
| SNUNet-CD | 89.83 | ? | 31.6 | ? |
| FC-Siam | ~87 | ? | ~2 | ? |
| TinyCD | 89.50 | ? | 5.8 | ~55 |
| **RCMT-V3-Hybrid** | **90.16** | **82.08** | **11.8** | **45** |
| **RCMT-V3-Swin** | **?** | **?** | **58.7** | **?** |

### 2. 关键技术创新

**Transformers**:
- BIT: 双边感知模块 (Bilateral Awareness)
- ChangeFormer: 层次化 Transformer + MLP 解码器
- SAM2-CD: Foundation Model (SAM2) 适配

**CNNs**:
- SNUNet-CD: 密集连接嵌套 UNet
- FC-Siam: 早期融合/差分/拼接

**Hybrid**:
- CMNet: CNN + Mamba
- RCMT-V3: CNN + Transformer (Hybrid/Swin)

### 3. 写作风格要点

**Abstract**:
- ✅ "Change Detection (CD) aims to..." (简洁定义)
- ✅ "Different from..." (强调创新)
- ✅ "the first..." (首次/新颖)
- ✅ 量化对比: "outperforms X by Y%"

**Introduction**:
- ✅ 具体应用场景
- ✅ 实际部署约束
- ✅ 有引用支持的挑战

**Related Work**:
- ✅ 每个方法有评价
- ✅ 优缺点分析

---

## 🚀 下一步行动

1. [ ] 手动补充每篇论文的完整信息
2. [ ] 提取 LEVIR-CD 完整实验数据
3. [ ] 整理写作风格要点
4. [ ] 更新写作工具
5. [ ] 生成 RCMT-V3 论文

---

**状态**: ⏳ 批量提取完成，待手动精读补充
