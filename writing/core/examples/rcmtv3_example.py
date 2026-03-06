# -*- coding: utf-8 -*-
"""
RCMT-V3论文生成示例
RCMT-V3 Paper Generation Example

演示如何使用教授级论文写作智能体框架生成RCMT-V3论文。

使用场景：
1. 快速生成论文草稿
2. 质量检查和改进
3. 多格式输出
4. 迭代优化

作者: OpenClaw Writing System
日期: 2026-03-05
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from rcmtv3_paper_agent import RCMTV3PaperAgent
from professor_writing_strategies import ProfessorWritingStrategies


def main():
    """主函数"""
    print("=" * 80)
    print("RCMT-V3 Paper Generation Example")
    print("=" * 80)
    print()
    
    # 1. 创建写作智能体
    print("[Step 1: Create Writing Agent]")
    print("-" * 80)
    
    experiment_data_path = r"D:\github\edge_infer_cloud\projects\rcmt_v3\paper_writing\experiments\rcmt_v3_optimized_results.json"
    
    # 检查文件是否存在
    if not Path(experiment_data_path).exists():
        print(f"[ERROR] Experiment data file not found: {experiment_data_path}")
        print("Please ensure experiments have been run and results saved to the specified path.")
        return
    
    agent = RCMTV3PaperAgent(experiment_data_path=experiment_data_path)
    print(f"✅ 写作智能体已创建")
    print(f"   方法: {agent.data.model}")
    print(f"   数据集: {agent.data.dataset}")
    print(f"   F1: {agent.data.f1:.2f}%, Params: {agent.data.params_M}M")
    print()
    
    # 2. 生成摘要
    print("=" * 80)
    print("📝 步骤 2: 生成摘要（BIT风格）")
    print("-" * 80)
    
    abstract = agent.generate_abstract(style="bit")
    print(abstract)
    print()
    
    # 3. 质量检查
    print("=" * 80)
    print("🔍 步骤 3: 质量检查")
    print("-" * 80)
    
    quality = agent.check_quality(abstract)
    print(f"质量评分: {quality['quality_score']}/100")
    print(f"AI痕迹检测: {'发现' if quality['ai_patterns_detected'] else '未发现'}")
    
    if quality['ai_patterns_detected']:
        print("\n检测到的问题:")
        for i, issue in enumerate(quality['issues'], 1):
            print(f"  {i}. {issue['type']}")
            print(f"     发现: '{issue['found']}'")
            print(f"     建议: {issue['suggestion']}")
    
    if quality['recommendations']:
        print("\n改进建议:")
        for rec in quality['recommendations']:
            print(f"  - {rec}")
    
    print()
    
    # 4. 生成完整论文
    print("=" * 80)
    print("📝 步骤 4: 生成完整论文")
    print("-" * 80)
    
    # 生成LaTeX格式
    latex_paper = agent.generate_full_paper(output_format="latex")
    print(f"✅ LaTeX论文已生成")
    print(f"   字数: {len(latex_paper.split())} words")
    print(f"   字符数: {len(latex_paper)} chars")
    print()
    
    # 生成Markdown格式
    markdown_paper = agent.generate_full_paper(output_format="markdown")
    print(f"✅ Markdown论文已生成")
    print(f"   字数: {len(markdown_paper.split())} words")
    print()
    
    # 5. 保存论文
    print("=" * 80)
    print("💾 步骤 5: 保存论文")
    print("-" * 80)
    
    # 创建输出目录
    output_dir = Path(r"D:\github\edge_infer_cloud\projects\rcmt_v3\paper_writing\drafts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存LaTeX
    latex_path = output_dir / "rcmtv3_paper.tex"
    agent.save_paper(str(latex_path), format="latex")
    
    # 保存Markdown
    markdown_path = output_dir / "rcmtv3_paper.md"
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(markdown_paper)
    print(f"✅ Markdown论文已保存到: {markdown_path}")
    
    # 保存纯文本
    text_path = output_dir / "rcmtv3_paper.txt"
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(agent.generate_full_paper(output_format="text"))
    print(f"✅ 纯文本论文已保存到: {text_path}")
    print()
    
    # 6. 生成各章节预览
    print("=" * 80)
    print("📖 步骤 6: 论文预览")
    print("-" * 80)
    
    print("\n【引言预览】（前500字符）")
    print(agent.generate_introduction()[:500] + "...")
    
    print("\n【方法论预览】（前500字符）")
    print(agent.generate_methodology()[:500] + "...")
    
    print("\n【实验部分预览】（前500字符）")
    print(agent.generate_experiments()[:500] + "...")
    
    print("\n【结论预览】（前500字符）")
    print(agent.generate_conclusion()[:500] + "...")
    
    print()
    
    # 7. 完成总结
    print("=" * 80)
    print("✅ 论文生成完成！")
    print("-" * 80)
    print(f"输出目录: {output_dir}")
    print(f"文件列表:")
    print(f"  - rcmtv3_paper.tex (LaTeX格式)")
    print(f"  - rcmtv3_paper.md (Markdown格式)")
    print(f"  - rcmtv3_paper.txt (纯文本格式)")
    print()
    print("下一步操作:")
    print("  1. 阅读生成的论文草稿")
    print("  2. 根据质量检查建议进行修改")
    print("  3. 添加相关的相关工作部分")
    print("  4. 补充图表和引用")
    print("  5. 提交到目标期刊（IEEE TGRS）")
    print()


def demo_strategies():
    """演示写作策略库的使用"""
    print("=" * 80)
    print("[Writing Strategy Demo]")
    print("=" * 80)
    print()
    
    strategies = ProfessorWritingStrategies()
    
    # 1. AI痕迹检测
    print("【AI痕迹检测】")
    print("-" * 80)
    
    bad_text = "Our method achieves excellent results and plays a critical role in urban monitoring."
    result = strategies.check_ai_patterns(bad_text)
    
    print(f"原文: {bad_text}")
    print(f"质量评分: {result['score']}/100")
    
    if result['issues']:
        print("\n检测到的问题:")
        for issue in result['issues']:
            print(f"  - {issue['type']}: '{issue['found']}'")
            print(f"    建议: {issue['suggestion']}")
    
    print()
    
    # 改进后的文本
    good_text = "Our method achieves 90.16% F1 on LEVIR-CD, which is critical for urban monitoring (Chen et al., 2021)."
    result_good = strategies.check_ai_patterns(good_text)
    print(f"改进后: {good_text}")
    print(f"质量评分: {result_good['score']}/100")
    print()
    
    # 2. 量化对比生成
    print("【量化对比生成】")
    print("-" * 80)
    
    comparisons = [
        ("vs BIT", 90.16, 90.87, "BIT", 11.8, 27.8),
        ("vs ChangeFormer", 90.16, 91.45, "ChangeFormer", 11.8, 24.5),
        ("vs TinyCD", 90.16, 89.50, "TinyCD", 11.8, 5.8)
    ]
    
    for name, our_val, base_val, base_name, our_params, base_params in comparisons:
        comp = strategies.generate_quantitative_comparison(
            our_value=our_val,
            baseline_value=base_val,
            metric="F1",
            baseline_name=base_name,
            params_ours=our_params,
            params_baseline=base_params
        )
        print(f"{name}: {comp}")
    
    print()
    
    # 3. 首次创新陈述
    print("【首次创新陈述】")
    print("-" * 80)
    
    innovations = [
        ("introduce self-attention mechanisms", "semantic change detection"),
        ("systematically study optimization strategies", "change detection"),
        ("propose bidirectional temporal fusion", "bi-temporal feature modeling")
    ]
    
    for action, field in innovations:
        statement = strategies.generate_first_innovation_statement(action, field)
        print(f"- {statement}")
    
    print()


def demo_templates():
    """演示模板库的使用"""
    print("=" * 80)
    print("[Template Library Demo]")
    print("=" * 80)
    print()
    
    from paper_template_library import AbstractTemplates, IntroductionTemplates
    
    # 1. 不同风格的摘要
    print("【摘要模板演示】")
    print("-" * 80)
    
    project_info = {
        'method_name': 'RCMT-V3',
        'architecture': 'CNN-Transformer hybrid',
        'components': ['Optimization Strategy', 'BTF', 'Hybrid Design'],
        'main_result': '90.16% F1',
        'comparison': 'outperforming BIT by 0.93 percentage points',
        'efficiency': '58% fewer parameters',
        'first_innovation': 'systematically study optimization strategies',
        'application1': 'urban monitoring',
        'application2': 'disaster assessment',
        'application3': 'environmental analysis',
        'existing_method': 'CNN-based architectures',
        'limitation': 'limited receptive fields',
        'benefit': 'overcomes CNN limitations',
        'technique1': 'depthwise separable convolutions',
        'technique2': 'bidirectional attention',
        'goal1': 'reduce parameters',
        'goal2': 'capture long-range dependencies',
        'dataset1': 'LEVIR-CD',
        'dataset2': 'SYSU-CD',
        'dataset3': 'WHU-CD',
        'params': 11.8
    }
    
    print("BIT风格（约180词）:")
    bit_abstract = AbstractTemplates.bit_style(project_info)
    print(f"{bit_abstract}\n")
    
    print("ChangeFormer风格（约190词）:")
    changeformer_abstract = AbstractTemplates.changeformer_style(project_info)
    print(f"{changeformer_abstract}\n")
    
    print("TinyCD风格（约130词）:")
    tinycd_abstract = AbstractTemplates.tinycd_style(project_info)
    print(f"{tinycd_abstract}\n")
    
    # 2. 引言模板
    print("【引言模板演示】")
    print("-" * 80)
    
    print("背景和动机:")
    print(f"{IntroductionTemplates.background_and_motivation()}\n")
    
    print("CNN方法:")
    print(f"{IntroductionTemplates.cnn_methods()[:300]}...\n")
    
    print("局限性分析:")
    print(f"{IntroductionTemplates.limitations_analysis()[:300]}...\n")
    
    print("我们的方法:")
    print(f"{IntroductionTemplates.our_approach(['Optimization Strategy', 'BTF', 'Hybrid Design'])[:300]}...\n")
    
    print("贡献:")
    contributions = [
        {'title': 'Systematic Optimization', 'details': '+1.52% F1 improvement'},
        {'title': 'Dual Architecture', 'details': 'Hybrid (11.8M) and Swin (58.7M)'},
        {'title': 'Bidirectional Temporal Fusion', 'details': '+0.71% F1 contribution'}
    ]
    print(f"{IntroductionTemplates.contributions(contributions)[:300]}...\n")


if __name__ == '__main__':
    # 演示选项
    import argparse
    
    parser = argparse.ArgumentParser(description='RCMT-V3论文生成示例')
    parser.add_argument('--demo', type=str, choices=['strategies', 'templates', 'all'],
                       default='paper', help='演示内容（strategies/templates/all）')
    
    args = parser.parse_args()
    
    if args.demo == 'strategies':
        demo_strategies()
    elif args.demo == 'templates':
        demo_templates()
    elif args.demo == 'all':
        demo_strategies()
        print("\n\n")
        demo_templates()
        print("\n\n")
        main()
    else:  # 默认生成论文
        main()
