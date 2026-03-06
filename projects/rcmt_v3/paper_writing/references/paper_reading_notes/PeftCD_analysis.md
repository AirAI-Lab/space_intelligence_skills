# PeftCD 论文精读笔记

**生成时间**: 2026-03-04
**页数**: 16

---

## 📋 基本信息

- **文件名**: PeftCD.pdf
- **页数**: 16

---

## 📄 前3页文本（自动提取）

```
JOURNAL OF L ATEX CLASS FILES, VOL. 18, NO. 9, SEPTEMBER 2025 1
PeftCD: Leveraging Vision Foundation Models with
Parameter-Efficient Fine-Tuning for Remote Sensing Change
Detection
Sijun Dong, Yuxuan Hu, LiBo Wang, Geng Chen, Xiaoliang Meng*
Abstract—To tackle the prevalence of pseudo changes, the
scarcity of labeled samples, and the difficulty of cross-domain
generalization in multi-temporal and multi-source remote sensing
imagery, we propose PeftCD, a change detection framework
built upon Vision Foundation Models (VFMs) with Parameter-
Efficient Fine-Tuning (PEFT). At its core, PeftCD employs a
weight-sharing Siamese encoder derived from a VFM, into which
LoRA and Adapter modules are seamlessly integrated. This
design enables highly efficient task adaptation by training only
a minimal set of additional parameters. To fully unlock the
potential of VFMs, we investigate two leading backbones: the
Segment Anything Model v2 (SAM2), renowned for its strong seg-
mentation priors, and DINOv3, a state-of-the-art self-supervised
representation learner. The framework is complemented by a de-
liberately lightweight decoder, ensuring the focus remains on the
powerful feature representations from the backbones. Extensive
experiments demonstrate that PeftCD achieves state-of-the-art
performance across multiple public datasets, including SYSU-CD
(IoU 73.81%), WHUCD (92.05%), MSRSCD (64.07%), MLCD
(76.89%), CDD (97.01%), S2Looking (52.25%) and LEVIR-CD
(85.62%), with notably precise boundary delineation and strong
suppression of pseudo-changes. In summary, PeftCD presents
an optimal balance of accuracy, efficiency, and generalization.
It offers a powerful and scalable paradigm for adapting large-
scale VFMs to real-world remote sensing change detection
applications. The code and pretrained models will be released
at https://github.com/dyzy41/PeftCD.
Index Terms—Remote Sensing Change Detection, Vision Foun-
dation Models, Parameter-Efficient Fine-Tuning
I. INTRODUCTION
Remote sensi
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
