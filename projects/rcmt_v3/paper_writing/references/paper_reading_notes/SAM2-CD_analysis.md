# SAM2-CD 论文精读笔记

**生成时间**: 2026-03-04
**页数**: 13

---

## 📋 基本信息

- **文件名**: SAM2-CD.pdf
- **页数**: 13

---

## 📄 前3页文本（自动提取）

```
IEEE JOURNAL OF SELECTED TOPICS IN APPLIED EARTH OBSERVATIONS AND REMOTE SENSING, VOL. 18, 2025 24575
SAM2-CD: Remote Sensing Image Change
Detection With SAM2
Yuan Qin , Chaoting Wang, Yuanyuan Fan, and Chanling Pan
Abstract —Change detection in high-resolution remote sensing
imagery remains challenging due to the difﬁculty in distinguish-ing task-relevant semantic changes from irrelevant variations andcapturing subtle local differences. While segment anything model2 (SAM2) exhibits strong generalization in natural image segmen-tation, its direct application to remote sensing change detection ishindered by single-image segmentation bias and contextual granu-larity mismatches. To address these limitations, we propose SAM2-CD, a lightweight architecture that adapts SAM2 for bitemporalchange detection through two novel modules: An activation selec-tion gate) that dynamically suppresses task-irrelevant variationsby learning channel-wise activation maps from cross-temporal fea-tures, and A global–local contextual attention module that hierar-chically integrates adaptive pooling and spatial attention to amplifyboth scene-level semantics and pixel-level details. By leveragingSAM2’s multiscale pyramid encoder and our optimized multiscalefeature fusion module, SAM2-CD achieves state-of-the-art per-formance across three benchmarks (LEVIR-CD, WHU-CD, andLEVIR+-CD), with IoU scores of 85.51%, 88.97%, and 69.31%,respectively. Notably, cross-dataset experiments demonstrate su-perior generalization, outperforming baselines by 35.29% in F1under zero-shot settings, demonstrating superior accuracy and
robustness in complex scenarios.
Index Terms —Change detection, dynamic feature selection,
global–local attention, multitemporal analysis, remote sensing (RS)semantics, segment anything model 2 (SAM2).
I. I NTRODUCTION
CHANGE detection is one of the core tasks in remote
sensing (RS), aimed at automatically identifying environ-
mental changes by comparing RS images of the same location
a
```

---

## 🔍 关键信息提取（需手动补充）

### 1. 标题
[待手动提取]

### 2. 作者
[待手动提取]

### 3. 会议/期刊
[待手动提取]

### 4. 核心贡献
[待手动提取]

### 5. LEVIR-CD 实验结果
- F1: [待提取]
- IoU: [待提取]
- Params: [待提取]

### 6. 关键技术
[待手动提取]

### 7. 写作风格亮点
[待手动提取]

### 8. 可借鉴的表达
[待手动提取]

---

## 💡 与 RCMT-V3 的关系

[待手动分析]

---

**精读状态**: ⏳ 待手动精读补充
