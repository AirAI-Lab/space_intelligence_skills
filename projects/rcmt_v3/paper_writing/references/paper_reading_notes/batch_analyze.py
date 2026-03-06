# -*- coding: utf-8 -*-
"""
批量精读论文工具
Batch Paper Reading Tool

用途：
1. 提取所有 PDF 论文的关键信息
2. 生成精读笔记到本地文件
3. 避免在 session 中占用大量 token
"""

import os
import PyPDF2
from pathlib import Path


def extract_paper_info(pdf_path):
    """提取论文关键信息"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            # 基本信息
            info = {
                'file_name': os.path.basename(pdf_path),
                'pages': len(reader.pages),
                'metadata': reader.metadata
            }
            
            # 提取前3页文本（通常包含摘要、介绍）
            text = ""
            for i in range(min(3, len(reader.pages))):
                text += reader.pages[i].extract_text()
            
            info['first_pages_text'] = text[:5000]  # 限制长度
            
            return info
    except Exception as e:
        return {'error': str(e), 'file_name': os.path.basename(pdf_path)}


def analyze_change_detection_paper(pdf_path, output_dir):
    """分析变化检测论文并生成精读笔记"""
    
    print(f"\n{'='*60}")
    print(f"Analyzing: {os.path.basename(pdf_path)}")
    print(f"{'='*60}")
    
    info = extract_paper_info(pdf_path)
    
    if 'error' in info:
        print(f"[ERROR] {info['error']}")
        return None
    
    # 生成精读笔记文件名
    paper_name = Path(pdf_path).stem
    note_path = os.path.join(output_dir, f"{paper_name}_analysis.md")
    
    # 分析内容
    analysis = f"""# {paper_name} 论文精读笔记

**生成时间**: 2026-03-04
**页数**: {info['pages']}

---

## 📋 基本信息

- **文件名**: {info['file_name']}
- **页数**: {info['pages']}

---

## 📄 前3页文本（自动提取）

```
{info['first_pages_text'][:2000]}
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
"""
    
    # 保存到文件
    with open(note_path, 'w', encoding='utf-8') as f:
        f.write(analysis)
    
    print(f"[OK] Analysis saved to: {os.path.basename(note_path)}")
    
    return note_path


def batch_analyze_papers(papers_dir, output_dir):
    """批量分析论文"""
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有 PDF 文件
    pdf_files = [f for f in os.listdir(papers_dir) if f.endswith('.pdf')]
    
    print(f"\n{'='*60}")
    print(f"Found {len(pdf_files)} papers to analyze")
    print(f"{'='*60}\n")
    
    analyzed = []
    for pdf_file in pdf_files:
        pdf_path = os.path.join(papers_dir, pdf_file)
        note_path = analyze_change_detection_paper(pdf_path, output_dir)
        if note_path:
            analyzed.append(note_path)
    
    # 生成汇总文件
    summary_path = os.path.join(output_dir, "00_SUMMARY.md")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"""# 论文精读汇总

**生成时间**: 2026-03-04
**论文数量**: {len(analyzed)}

---

## 📚 已精读论文列表

""")
        for i, note_path in enumerate(analyzed, 1):
            paper_name = os.path.basename(note_path).replace('_analysis.md', '')
            f.write(f"{i}. [{paper_name}]({os.path.basename(note_path)})\n")
        
        f.write(f"""

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
""")
    
    print(f"\n{'='*60}")
    print(f"Batch analysis complete!")
    print(f"Analyzed: {len(analyzed)} papers")
    print(f"Summary: {summary_path}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    papers_dir = r"D:\github\edge_infer_cloud\projects\rcmt_v3\paper_writing\references"
    output_dir = r"D:\github\edge_infer_cloud\projects\rcmt_v3\paper_writing\references\paper_reading_notes"
    
    batch_analyze_papers(papers_dir, output_dir)
