# -*- coding: utf-8 -*-
"""
快速启动脚本
Quick Start Script

教授级论文写作智能体框架的快速启动脚本。

使用方法：
    python quick_start.py

作者: OpenClaw Writing System
日期: 2026-03-05
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))


def quick_start():
    """快速启动RCMT-V3论文生成"""
    print("\n" + "=" * 80)
    print("Professor-Level Academic Writing Framework")
    print("Quick Start Script")
    print("=" * 80)
    print()
    
    # 导入智能体
    try:
        from rcmtv3_paper_agent import RCMTV3PaperAgent
    except ImportError as e:
        print(f"[ERROR] Failed to import RCMTV3PaperAgent: {e}")
        print("Please ensure all required files are in the current directory.")
        return
    
    # 检查实验数据文件
    experiment_data_path = r"D:\github\edge_infer_cloud\projects\rcmt_v3\paper_writing\experiments\rcmt_v3_optimized_results.json"
    
    if not Path(experiment_data_path).exists():
        print(f"[INFO] Experiment data file not found: {experiment_data_path}")
        print("Creating agent with default data...")
        print()
        agent = RCMTV3PaperAgent()
    else:
        print(f"[INFO] Loading experiment data from:")
        print(f"   {experiment_data_path}")
        print()
        agent = RCMTV3PaperAgent(experiment_data_path=experiment_data_path)
    
    # 生成摘要
    print("=" * 80)
    print("Generating Abstract (BIT Style)...")
    print("=" * 80)
    abstract = agent.generate_abstract(style="bit")
    print(abstract)
    print()
    
    # 质量检查
    print("=" * 80)
    print("Quality Check...")
    print("=" * 80)
    quality = agent.check_quality(abstract)
    print(f"Quality Score: {quality['quality_score']}/100")
    print(f"Grade: {quality['quality_score'] >= 80 and 'A (SOTA Level)' or quality['quality_score'] >= 60 and 'B (Good)' or 'C (Needs Improvement)'}")
    
    if quality['ai_patterns_detected']:
        print("\nIssues found:")
        for i, issue in enumerate(quality['issues'], 1):
            print(f"  {i}. {issue['type']}")
            print(f"     Suggestion: {issue['suggestion']}")
    
    print()
    
    # 生成完整论文
    print("=" * 80)
    print("Generating Full Paper (LaTeX)...")
    print("=" * 80)
    paper = agent.generate_full_paper(output_format="latex")
    print(f"[OK] Paper generated: {len(paper.split())} words, {len(paper)} characters")
    print()
    
    # 保存论文
    output_dir = Path(r"D:\github\edge_infer_cloud\projects\rcmt_v3\paper_writing\drafts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    latex_path = output_dir / "rcmtv3_paper.tex"
    markdown_path = output_dir / "rcmtv3_paper.md"
    
    agent.save_paper(str(latex_path), format="latex")
    
    # 保存Markdown
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(agent.generate_full_paper(output_format="markdown"))
    print(f"[OK] Markdown paper saved to: {markdown_path}")
    print()
    
    # 完成
    print("=" * 80)
    print("Generation Complete!")
    print("=" * 80)
    print(f"\nOutput directory: {output_dir}")
    print("Files generated:")
    print(f"  1. {latex_path.name} (LaTeX format)")
    print(f"  2. {markdown_path.name} (Markdown format)")
    print()
    print("Next steps:")
    print("  1. Read the generated paper drafts")
    print("  2. Review and edit based on quality feedback")
    print("  3. Add related work section")
    print("  4. Add figures and references")
    print("  5. Submit to target journal (IEEE TGRS)")
    print()
    print("For more information, see:")
    print(f"  - README.md")
    print(f"  - FRAMEWORK_SUMMARY.md")
    print(f"  - COMPLETION_REPORT.md")
    print()


if __name__ == '__main__':
    quick_start()
