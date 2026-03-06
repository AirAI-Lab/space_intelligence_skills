# BIT 论文精读笔记

**生成时间**: 2026-03-04
**页数**: 14

---

## 📋 基本信息

- **文件名**: BIT.pdf
- **页数**: 14

---

## 📄 前3页文本（自动提取）

```
1
Remote Sensing Image Change Detection with
Transformers
Hao Chen, Zipeng Qi and Zhenwei Shi?,Member, IEEE
Abstract —Modern change detection (CD) has achieved re-
markable success by the powerful discriminative ability of
deep convolutions. However, high-resolution remote sensing CD
remains challenging due to the complexity of objects in the
scene. Objects with the same semantic concept may show distinct
spectral characteristics at different times and spatial locations.
Most recent CD pipelines using pure convolutions are still
struggling to relate long-range concepts in space-time. Non-
local self-attention approaches show promising performance via
modeling dense relations among pixels, yet are computationally
inefﬁcient. Here, we propose a bitemporal image transformer
(BIT) to efﬁciently and effectively model contexts within the
spatial-temporal domain. Our intuition is that the high-level
concepts of the change of interest can be represented by a
few visual words, i.e., semantic tokens. To achieve this, we
express the bitemporal image into a few tokens, and use a
transformer encoder to model contexts in the compact token-
based space-time. The learned context-rich tokens are then
feedback to the pixel-space for reﬁning the original features via
a transformer decoder. We incorporate BIT in a deep feature
differencing-based CD framework. Extensive experiments on
three CD datasets demonstrate the effectiveness and efﬁciency of
the proposed method. Notably, our BIT-based model signiﬁcantly
outperforms the purely convolutional baseline using only 3 times
lower computational costs and model parameters. Based on
a naive backbone (ResNet18) without sophisticated structures
(e.g., FPN, UNet), our model surpasses several state-of-the-art
CD methods, including better than four recent attention-based
methods in terms of efﬁciency and accuracy. Our code is available
at https://github.com/justchenhao/BIT CD.
Index Terms —Change detection (CD), high-resolution optical
remote s
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
