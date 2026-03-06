# Tiny_CD 论文精读笔记

**生成时间**: 2026-03-04
**页数**: 19

---

## 📋 基本信息

- **文件名**: Tiny_CD.pdf
- **页数**: 19

---

## 📄 前3页文本（自动提取）

```
TINYCD: A(NOT SO ) DEEPLEARNING MODEL FOR CHANGE
DETECTION
Andrea Codegoni
Dipartimento di Matematica "F. Casorati"
University of Pavia
andrea.codegoni01@ateneopv.itGabriele Lombardi, Alessandro Ferrari
ARGO Vision
Milano
{gabriele.lombardi,alessandro.ferrari}@argo.vision
ABSTRACT
In this paper, we present a lightweight and effective change detection model, called TinyCD. This
model has been designed to be faster and smaller than current state-of-the-art change detection
models due to industrial needs. Despite being from 13 to 140 times smaller than the compared
change detection models, and exposing at least a quarter of the computational complexity, our model
outperforms the current state-of-the-art models by at least 1%on both F1 score and IoU on the
LEVIR-CD dataset, and more than 8%on the WHU-CD dataset. To reach these results, TinyCD uses
a Siamese U-Net architecture exploiting low-level features in a globally temporal and locally spatial
way. In addition, it adopts a new strategy to mix features in the space-time domain both to merge the
embeddings obtained from the Siamese backbones, and, coupled with an MLP block, it forms a novel
space-semantic attention mechanism, the Mix and Attention Mask Block (MAMB). Source code,
models and results are available here: https://github.com/AndreaCodegoni/Tiny_model_4_
CD
Keywords Change Detection (CD) Remote Sensing (RS) Convolutional Neural Network (CNN)
1 Introduction
In the Remote Sensing community, Change Detection (from now denoted with CD) is one of the main research topics.
The main purpose of CD is to identify changes occurred in a scene between two different times. To this aim, a CD
model compares two co-registered images I1andI2acquired at times t1andt2[1–3]. Once the relevant changes have
been identiﬁed, such as urban expansion, deforestation, or post disaster damage assessment [4 –10], the challenge is
to let the CD model ignore other irrelevant changes. Examples of irrelevant changes are, but not limited to
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
