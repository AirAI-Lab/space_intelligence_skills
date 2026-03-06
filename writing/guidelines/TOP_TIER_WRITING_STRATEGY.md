# Top-Tier Paper Writing Strategy

**生成时间**: 2026-03-05
**基于分析**: 11篇顶级变化检测论文（BIT, ChangeFormer, TinyCD, SNUNet-CD, FC-Siam, ChangeCLIP, CMNet, GSTM-SCD, Open-CD, PeftCD, SAM2-CD）
**目标**: 帮助撰写被IEEE TGRS、CVPR、ICCV等顶级期刊/会议接收的高质量论文

---

## 🎯 一、一区Top论文共性特征

### 1. 标题规律

#### 长度规范
- **短标题**（8-12词）: "TinyCD: A Tiny and Efficient Change Detection Network"
- **中等标题**（13-20词）: "Transformer Meets Convolution: A Bilateral Awareness Network for Semantic Change Detection"
- **长标题**（21-25词）: "RCMT-V3: A Systematic Framework for High-Performance Change Detection in Remote Sensing Images"

#### 关键词选择
**必须包含**:
1. **方法名**: 首字母缩写或命名规范（BIT, ChangeFormer, RCMT-V3）
2. **架构类型**: "Transformer-based", "CNN-based", "Hybrid", "Pure Transformer"
3. **应用领域**: "Change Detection", "Semantic Change Detection", "Remote Sensing Images"
4. **核心创新**: "Bilateral Awareness", "Difference Feature Fusion", "Systematic Optimization"

**典型模式**:
```
<Method Name>: A <Adjective 1> and <Adjective 2> <Application> Network
<Method Name>: A <Architecture>-Based <Application> for <Data Type>
<Method Name>: The First <Innovation> in <Field>
```

### 2. 摘要黄金结构

#### 标准结构（4-5段，120-200词）

**第1段：问题陈述（20-30词）**
```
<Domain> is a challenging task that requires not only [sub-task 1] but also 
[sub-task 2]. This is essential for [application 1], [application 2], and 
[application 3].
```

**第2段：背景与局限（30-40词）**
```
While deep learning has achieved significant progress, most existing methods 
rely on <Method>, which have <limitation 1> and <limitation 2>.
```

**第3段：方法介绍（40-60词）**
```
We present <Method Name>, a <Architecture> approach that <benefit 1> and 
<benefit 2>. <Method Name> consists of <N> key components:
1. [Component 1]
2. [Component 2]
3. [Component 3]
```

**第4段：结果与对比（30-40词）**
```
Experiments on <Dataset 1> and <Dataset 2> demonstrate that <Method Name> 
achieves <result>, outperforming <Baseline> by <X%> while using <Y%> fewer 
parameters.
```

**第5段：贡献总结（20-30词）**
```
To our knowledge, this is the first work to <key innovation> in <Field>.
```

#### 字数分配建议
- **总词数**: 150-200词
- **问题陈述**: 15%
- **背景与局限**: 20%
- **方法介绍**: 35%
- **结果与对比**: 25%
- **贡献总结**: 5%

### 3. 引言三段式/四段式结构

#### 引言段落组成（4-5个段落）

**第1段：背景和动机**
```
<Domain> is a critical task for [application 1], [application 2], and 
[application 3]. This task involves [task definition]. Recent advances in 
<technology> have revolutionized the field.
```

**第2段：现有方法的局限**
```
The limitations of <Existing Method> include:
1. <Limitation 1> - <Explanation>
2. <Limitation 2> - <Explanation>
3. <Limitation 3> - <Explanation>

For example, <Method X> achieves <result> but fails to capture <specific issue>.
```

**第3段：我们方法的介绍**
```
To address these challenges, we present <Method Name>, a novel framework that...
Our framework comprises <N> key components:
1. [Component 1]
2. [Component 2]
3. [Component 3]
```

**第4段：贡献总结（4-5个贡献点）**
```
The main contributions of this work are:
1. **<Contribution 1>**: We propose [technique], which improves <metric> by <X%>.
2. **<Contribution 2>**: [Detailed description]
3. **<Contribution 3>**: [Detailed description]
4. **<Contribution 4>**: [Detailed description]

To our knowledge, this is the first work to <key innovation> in <Field>.
```

**第5段：论文结构（可选）**
```
The rest of this paper is organized as follows. Section 2 reviews related work. 
Section 3 presents our methodology. Section 4 describes experiments. Section 5 
concludes the paper.
```

### 4. 贡献点表述公式

#### 贡献点1：主要创新
```
**<Contribution 1>**: We propose [specific technique], which improves <metric> 
by <X%> (Table [N]).
```

**示例**:
- "We propose a systematic optimization strategy improving F1 by +1.52% (Table 2)"
- "We propose a Bidirectional Temporal Fusion mechanism contributing +0.71% F1 (Table 4)"

#### 贡献点2：架构设计
```
**<Contribution 2>**: We design a [architecture type] architecture achieving 
<result> with <params> parameters, demonstrating <benefit>.
```

**示例**:
- "We design a hybrid CNN-Transformer architecture achieving 90.16% F1 with only 11.8M parameters"

#### 贡献点3：技术方法
```
**<Contribution 3>**: We introduce [specific technique], which <benefit> for 
[task].
```

**示例**:
- "We introduce depthwise separable convolutions, which reduce parameter count by 52% while maintaining accuracy"

#### 贡献点4：系统分析
```
**<Contribution 4>**: We conduct comprehensive ablation studies showing that 
[specific finding] improves <metric> by <X%>.
```

**示例**:
- "We conduct ablation studies revealing that proper learning rate scheduling outperforms complex multi-term losses"

### 5. 图表设计原则

#### Figure 1：架构图
**要求**:
- 标注 "(A)", "(B)", "(C)" 等组件
- 说明框架由 <N> 个主要组件组成
- 使用清晰的连接线说明数据流

**模板**:
```
Figure 1: The overall architecture of <Method Name>. The framework consists of 
<N> main components: (A) [Component 1], (B) [Component 2], and (C) [Component 3].
```

#### Table 1：主实验对比
**列设计**:
```
- Method Name (必需)
- Parameters (强烈推荐)
- F1, IoU (必需)
- Precision, Recall (推荐)
- Inference Time (可选，如适用)
```

**标题**:
```
Table 1: Comparison of state-of-the-art methods on LEVIR-CD dataset. 
Best results are in bold.
```

**特点**:
- 包含历史对比（从FC-EF到当前SOTA）
- 参数量作为额外指标
- 最佳结果加粗

#### Table 2：消融实验
**格式**:
```
Table 2: Ablation study on <Method Name>. All experiments are conducted on 
<dataset>.

| Configuration | F1 | IoU | Params |
|---------------|----|-----|--------|
| Full Model | 91.45 | 84.56 | 24.5M |
| - [Component 1] | 91.12 | 84.23 | 24.5M |
| - [Component 2] | 90.89 | 83.98 | 24.5M |
| - [Component 3] | 90.12 | 83.45 | 24.5M |
| - [Component 1] + [Component 2] | 91.34 | 84.45 | 24.5M |

The results show that [analysis].
```

---

## 📚 二、高影响力表述库

### 1. 问题陈述表述

#### ✅ 强调重要性的表达
```
✅ "<Domain> is a challenging task that requires not only [sub-task 1] but also 
    [sub-task 2]."
✅ "<Domain> plays a crucial role in [application 1], [application 2], and 
    [application 3]."
✅ "<Domain> is critical for [application 1], [application 2], and 
    [application 3]."
```

#### ✅ 强调复杂性的表达
```
✅ "This task involves detecting and classifying changes between bi-temporal 
    images, which is computationally expensive."
✅ "The complexity of <Domain> stems from [challenge 1] and [challenge 2]."
```

#### ❌ 避免的表达
```
❌ "This is very important for many applications."
❌ "This is a critical problem." (太模糊)
❌ "This task is important." (缺乏细节)
```

---

### 2. 方法创新表述

#### ✅ 首次性强调
```
✅ "To our knowledge, this is the first work to introduce [innovation] into 
    <Field>."
✅ "We are the first to propose [method name] for <Task>."
✅ "This is the first work to systematically study [topic] in <Field>."
```

#### ✅ 创新性表达
```
✅ "We propose a novel <architecture> that <benefit>."
✅ "We introduce a unique <mechanism> that <benefit>."
✅ "Our approach differs from previous works by <specific difference>."
```

#### ✅ 技术描述
```
✅ "The key insight is that [theoretical reason]."
✅ "By incorporating [mechanism], we enable the model to <benefit>."
✅ "We employ <technique> to <goal>, which <benefit>."
```

#### ❌ 避免的表达
```
❌ "Our novel, groundbreaking method..." (过度形容词)
❌ "This is a revolutionary approach." (夸张)
❌ "We propose a new method that is better than all previous methods." (过于绝对)
```

---

### 3. 实验结果表述

#### ✅ 量化对比
```
✅ "Our method achieves 91.5% F1, outperforming BIT by 0.58%."
✅ "Improves F1 score from 89.8% to 91.5% (Δ=+1.7%, p<0.01)."
✅ "Uses 52% fewer parameters while maintaining 98.6% of the F1 score."
✅ "Achieves 7.64% F1 per million parameters, which is 2.3x higher than ChangeFormer."
```

#### ✅ 性能提升
```
✅ "Achieves state-of-the-art performance, surpassing the previous best by 
    X%."
✅ "Outperforms the state-of-the-art by Y percentage points."
✅ "Improves over the baseline by Z percentage points."
✅ "Maintains competitive performance while using X% fewer parameters."
```

#### ✅ 具体指标
```
✅ "On LEVIR-CD, our method achieves 91.5% F1, 84.56% IoU, 92.34% Precision, 
    and 90.59% Recall."
✅ "Achieves consistent performance across all metrics: F1: 91.5%, IoU: 84.56%, 
    Precision: 92.34%, Recall: 90.59%."
```

#### ❌ 避免的表达
```
❌ "Achieves excellent results." (模糊)
❌ "Significantly outperforms." (不说多少)
❌ "Much better than previous methods." (不具体)
❌ "Very good performance." (主观判断)
```

---

### 4. 对比优势表述

#### ✅ 优势对比
```
✅ "Compared to ChangeFormer, our method uses 52% fewer parameters while 
    maintaining 98.6% of the F1 score."
✅ "Our approach demonstrates superior efficiency, achieving X% F1 per million 
    parameters compared to Y% for previous methods."
✅ "While ChangeFormer achieves higher accuracy, RCMT-V3 is more suitable for 
    edge deployment due to its smaller footprint."
```

#### ✅ 差异分析
```
✅ "The main difference between our method and ChangeFormer is [specific aspect]."
✅ "Unlike previous methods, our approach introduces [innovation] to address 
    [challenge]."
✅ "We differ from [Previous Method] by [specific technique], which addresses 
    [specific limitation]."
```

#### ✅ 局限性对比
```
✅ "While our method achieves strong performance, it still struggles with 
    [limitation], which is an active research area."
✅ "Unlike [Previous Method], our approach has [advantage 1] and [advantage 2], 
    but lacks [disadvantage]."
```

#### ❌ 避免的表达
```
❌ "Our method is much better than all previous methods." (过于绝对)
❌ "Our method is the best in all aspects." (不可能)
❌ "Previous methods are terrible." (不客观)
❌ "Our method is superior in every way." (夸张)
```

---

### 5. 限制和未来工作表述

#### ✅ 诚实讨论局限
```
✅ "While our method demonstrates strong performance, there are still limitations: 
    <Limitation 1> and <Limitation 2>."
✅ "Our approach is less effective in [scenario], which we leave for future work."
✅ "We acknowledge that [limitation] remains a challenge, which we aim to address 
    in future versions."
```

#### ✅ 未来工作方向
```
✅ "Future work will focus on extending the framework to other remote sensing 
    tasks and exploring multi-temporal change detection."
✅ "We plan to explore zero-shot learning to improve generalization across 
    different datasets."
✅ "Future research will investigate the integration of foundation models to 
    further improve performance."
```

#### ❌ 避免的表达
```
❌ "Our method is perfect and has no limitations." (不真实)
❌ "Future work will solve all the current problems." (不现实)
❌ "Our method is the best in every way, and there is nothing to improve." (不可能)
```

---

## ✅ 三、学术写作规范

### 1. 引用格式和时机

#### ✅ 引用原则

**原则1：引用原始文献**
```
✅ "The Transformer architecture (Vaswani et al., 2017) was originally 
    proposed for machine translation."
✅ "The bilateral awareness module (Chen and Shi, 2021) enables explicit 
    modeling of inter-image interactions."
```

**原则2：引用最新工作**
```
✅ 对于变化检测:
   - BIT (Chen et al., ICCV 2021) ✓
   - ChangeFormer (Mondal et al., TGRS 2022) ✓
   - TinyCD (Codegoni et al., 2023) ✓
   - GCD-DDPM (Li et al., 2024) ✓
   
❌ 避免引用过时方法作为SOTA
```

**原则3：引用支持每个陈述**
```
✅ "BIT [cite] achieves 90.87% F1 on LEVIR-CD, which is the current 
    state-of-the-art."
✅ "While CNN-based methods excel at local feature extraction [cite], 
    they struggle with long-range dependencies [cite]."
```

**原则4：使用标准引用格式**
```bibtex
@article{changeformer2022,
  author = {Mondal, Gopal and Santra, Sanchayan and Chanda, Bhabatosh},
  title = {ChangeFormer: A Transformer-Based Method for Change Detection in 
           Remote Sensing Images},
  journal = {IEEE Transactions on Geoscience and Remote Sensing},
  year = {2022},
  volume = {60},
  pages = {1-15},
  doi = {10.1109/TGRS.2022.3216735}
}
```

#### ✅ 引用时机
1. **首次引入技术**: "The Transformer architecture [cite]..."
2. **说明局限性**: "...struggles with [limitation] [cite]..."
3. **对比方法**: "...outperforming [Method] [cite] by [X%]..."
4. **引用历史**: "...the first work to [innovation] in [Field] [cite]..."
5. **实验验证**: "...achieves [result] on [dataset] [cite]..."

### 2. 自我引用策略

#### ✅ 使用"我们的方法"vs"我们提出"

**使用"我们的方法"** (中性，描述结果)
```
✅ "Our method achieves 91.5% F1 on LEVIR-CD."
✅ "Our approach demonstrates superior efficiency, achieving 7.64% F1 per 
    million parameters."
✅ "Our experiments show that [specific finding]."
```

**使用"我们提出"** (强调创新)
```
✅ "We propose RCMT-V3, a systematic framework that..."
✅ "We introduce a novel mechanism called Bidirectional Temporal Fusion."
✅ "We conduct comprehensive ablation studies to identify optimal strategies."
```

**使用"提出的"** (正式，描述方法)
```
✅ "The proposed framework achieves..."
✅ "The proposed BTF mechanism explicitly models..."
✅ "The proposed method demonstrates..."
```

#### ✅ 自我引用模板
```
✅ 使用 "Our method achieves..."
✅ 使用 "We propose..."
✅ 使用 "The proposed framework..."
```

#### ❌ 避免的表达
```
❌ "I propose..." (不要用第一人称单数)
❌ "This paper proposes..." (不要过度使用 "This paper")
❌ "We are the first to..." (太绝对，用 "To our knowledge")
```

### 3. 数据呈现规范

#### ✅ 数值精度

**保留2位小数**
```
✅ F1: 91.45% (two decimal places)
✅ IoU: 84.56% (two decimal places)
✅ Parameters: 11.8M (one decimal place, millions)

❌ F1: 91.5% (one decimal place) - 不精确
❌ F1: 91.454% (three decimal places) - 过度精确
❌ F1: 91% (zero decimal places) - 太粗糙
```

**百分比使用说明**
```
✅ "outperforming by 0.58%" (使用小数)
✅ "improves by +1.52%" (明确正负)
✅ "using 52% fewer parameters" (明确的百分比)
✅ "achieves 7.64% F1 per million parameters" (百分比每百万参数)

❌ "improves by a lot" (模糊)
❌ "much better" (不具体)
```

#### ✅ 显著性标注

**加粗最佳结果**
```
✅ The best results are in bold.
✅ Bold indicates the highest performance.
✅ Best values are in bold.
```

**引用基准**
```
✅ "outperforming BIT by 0.58%"
✅ "maintaining 98.6% of the F1 score"
✅ "using 52% fewer parameters"
```

**使用"绝对改进"**
```
✅ "improves F1 by +1.52 percentage points"
✅ "improves IoU by +1.12 percentage points"
✅ "reduces parameters by 52%"

❌ "improves by +1.52%" (混淆百分比和百分比点)
❌ "reduces by 0.52" (缺少单位)
```

#### ✅ 表格标题

**完整标题**
```
✅ "Table 1: Comparison of state-of-the-art methods on LEVIR-CD dataset. 
     Best results are in bold."
✅ "Table 2: Ablation study on RCMT-V3-Hybrid. All experiments are conducted 
     on LEVIR-CD."
✅ "Figure 1: The overall architecture of RCMT-V3. The framework consists of 
     three main components: (A) Systematic Optimization, (B) Hybrid Architecture, 
     and (C) BTF Mechanism."
```

**关键要素**:
- 说明数据集
- 说明基准
- 指出最佳结果位置
- 描述组件

### 4. 图表标题规范

#### ✅ Figure标题
```
✅ "Figure 1: The overall architecture of <Method Name>. The framework consists 
     of <N> main components: (A) <Component 1>, (B) <Component 2>, and (C) <Component 3>."

✅ "Figure 2: The <Module Name> mechanism. (a) shows <aspect 1>, (b) illustrates 
     <aspect 2>, and (c) combines them to produce the final result."

✅ "Figure 3: Qualitative comparison of change detection results. The first row 
     shows the input bi-temporal images, the second row displays the ground truth, 
     and the remaining rows present the predictions of different methods."
```

**要求**:
- 描述组件（使用 (A), (B), (C)）
- 说明各子图
- 描述数据流或变化

#### ✅ Table标题
```
✅ "Table 1: Comparison of state-of-the-art methods on <Dataset> dataset. 
     Best results are in bold."

✅ "Table 2: Ablation study on <Method Name>. All experiments are conducted 
     on <Dataset>."

✅ "Table 3: Parameter analysis of <Method Name>. The number of parameters is 
     shown in millions (M)."
```

**要求**:
- 说明数据集
- 说明基准
- 指出最佳结果位置
- 描述分析内容

---

## 🎨 四、语言风格规范

### 1. 使用第一人称复数
```
✅ "We propose RCMT-V3..."
✅ "Our experiments show..."
✅ "We conducted comprehensive ablation studies..."
```

### 2. 使用现在时描述事实
```
✅ "Table 3 shows that our method achieves 91.5% F1."
✅ "Equation 5 defines the loss function."
✅ "The model predicts changes between bi-temporal images."
```

### 3. 使用过去时描述实验
```
✅ "We conducted experiments on LEVIR-CD."
✅ "The model achieved 91.5% F1 on the validation set."
✅ "We trained the model for 100 epochs."
```

### 4. 避免绝对化词汇
```
✅ 使用: "often", "rarely", "significantly", "substantially", "typically"
❌ 避免: "always", "never", "perfectly", "completely", "obviously"

✅ "The model often struggles with extreme illumination changes."
✅ "Significant improvements were observed on datasets with large-scale changes."
❌ "The model always fails with extreme changes."
❌ "The model perfectly handles all cases."
```

### 5. 使用精确的连接词
```
✅ 因果: "Therefore", "Consequently", "As a result"
✅ 对比: "However", "In contrast", "Conversely", "Despite"
✅ 递进: "Furthermore", "Moreover", "Additionally", "Also"
✅ 总结: "In summary", "Overall", "To conclude"
✅ 目的: "To address this", "To tackle this", "To overcome this"
✅ 转折: "On the other hand", "Conversely", "Alternatively"
```

---

## 📊 五、写作流程

### 第1步：确定论文结构（1-2小时）

**标准结构**:
```
1. Introduction (2-3页)
2. Related Work (2-3页)
3. Methodology (4-5页)
4. Experiments (5-6页)
5. Conclusion (1页)
```

**页数分配建议**:
- Introduction: 20%
- Related Work: 15%
- Methodology: 30%
- Experiments: 30%
- Conclusion: 5%

### 第2步：撰写摘要（1小时）

**模板**:
```
<Domain> is a challenging task that requires not only [sub-task 1] but also 
[sub-task 2]. While deep learning has achieved significant progress, most 
existing methods rely on <Method>, which have <limitation>. We present 
<Method Name>, a <Architecture> approach that <benefit>.

<Method Name> consists of <N> key components: [Component 1], [Component 2], 
and [Component 3]. Experiments on <Dataset 1> and <Dataset 2> demonstrate 
that <Method Name> achieves <result>, outperforming <Baseline> by <X%> while 
using <Y%> fewer parameters.

To our knowledge, this is the first work to <key innovation> in <Field>.
```

### 第3步：撰写引言（3-4小时）

**模板**:
```
## 1. Introduction

### 1.1 Background and Motivation
<Domain> is critical for [application 1], [application 2], and 
[application 3]. This task involves [task definition]. Recent advances in 
<technology> have revolutionized the field.

### 1.2 Critical Challenges
The limitations of <Existing Method> include:
1. <Limitation 1> - <Explanation>
2. <Limitation 2> - <Explanation>
3. <Limitation 3> - <Explanation>

For example, <Method X> achieves <result> but fails to capture <specific issue>.

### 1.3 Our Approach
To address these challenges, we present <Method Name>, a novel framework that...
Our framework comprises <N> key components:
1. [Component 1]
2. [Component 2]
3. [Component 3]

### 1.4 Contributions
The main contributions of this work are:
1. **<Contribution 1>**: We propose [technique], which improves <metric> by <X%>.
2. **<Contribution 2>**: [Detailed description]
3. **<Contribution 3>**: [Detailed description]

To our knowledge, this is the first work to <key innovation> in <Field>.
```

### 第4步：撰写相关工作和方法（6-8小时）

**相关工作**:
- 分类清晰
- 每个方法都要评价（优缺点）
- 引入自己工作

**方法论**:
- 问题形式化
- 架构图
- 模块描述
- 公式
- 理论依据

### 第5步：撰写实验（8-10小时）

**实验内容**:
1. 数据集和指标
2. 实验设置
3. 主实验结果
4. 消融实验
5. 定性分析
6. 局限性讨论

### 第6步：质量检查（2-3小时）

**检查清单**:
- [ ] 所有数据可验证
- [ ] 所有引用已核实
- [ ] 无自相矛盾
- [ ] 无过度承诺
- [ ] 局限性已讨论
- [ ] 无AI写作痕迹
- [ ] 术语使用一致
- [ ] 时态使用正确
- [ ] 无语法错误
- [ ] 符合期刊要求

---

## 💡 六、质量检查清单

### 内容检查
- [ ] 所有数据可验证（有实验支持）
- [ ] 所有引用已核实（准确无误）
- [ ] 无自相矛盾（数据一致）
- [ ] 无过度承诺（诚实的评估）
- [ ] 局限性已讨论（诚实分析）

### 语言检查
- [ ] 无AI写作痕迹（避免通用模式）
- [ ] 术语使用一致（不混淆术语）
- [ ] 时态使用正确（事实用现在时，实验用过去时）
- [ ] 无语法错误（仔细检查）
- [ ] 无拼写错误（使用工具检查）

### 格式检查
- [ ] 符合期刊要求（格式、引用）
- [ ] 图表清晰（可读性）
- [ ] 表格规范（标题、加粗）
- [ ] 参考文献格式正确（标准格式）
- [ ] 页数符合要求（不超也不少）

### 实验检查
- [ ] 可复现（详细设置）
- [ ] 对比公平（公平对比）
- [ ] 消融完整（所有组件）
- [ ] 可视化充分（清晰展示）

---

## 📚 七、参考资源

### 推荐阅读
1. **How to Write a Great Research Paper** - Simon Peyton Jones
2. **The Elements of Style** - Strunk & White
3. **Scientific Writing = Thinking in Words** - David Lindsay
4. **Writing for Computer Science** - Justin Zobel

### 顶级论文参考
1. **CVPR Best Papers** - 学习结构和方法
2. **IEEE TGRS High-Impact Papers** - 领域规范
3. **Nature/Science Papers** - 写作风格

### 工具推荐
- **Grammarly**: 检查语法错误
- **Overleaf**: LaTeX编辑
- **Zotero**: 参考文献管理
- **DeepL**: 翻译和润色

---

## 🎯 核心建议

### 写作的核心原则
1. **数据说话**: 每个声明都有定量支持
2. **引用支撑**: 关键陈述都有文献依据
3. **逻辑严密**: 因果关系清晰，推理完整
4. **客观中立**: 避免主观和绝对化词汇
5. **细节丰富**: 提供足够的技术细节

### 避免 AI 痕迹的关键
1. **精确性**: 使用具体数据而非模糊描述
2. **个性化**: 体现对问题的深入理解
3. **批判性**: 分析优缺点，不只是一味赞扬
4. **专业性**: 使用领域专业术语
5. **简洁性**: 避免冗余和重复

### 目标：被顶级期刊/会议接收
**成功率因素**:
1. ✅ 清晰的创新点
2. ✅ 量化的对比
3. ✅ 完整的实验
4. ✅ 诚实的评估
5. ✅ 精确的表达
6. ✅ 符合规范

---

**文档生成时间**: 2026-03-05
**状态**: ✅ 完整策略
**用途**: RCMT-V3论文写作的全面指导
**下一步**: 根据策略重构写作工具架构
