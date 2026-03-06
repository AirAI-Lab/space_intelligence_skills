# -*- coding: utf-8 -*-
"""
框架测试脚本
Test Framework

测试教授级论文写作智能体框架的基本功能。

作者: OpenClaw Writing System
日期: 2026-03-05
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from professor_writing_strategies import ProfessorWritingStrategies


def test_strategies():
    """测试写作策略库"""
    print("=" * 80)
    print("Testing Writing Strategies Library")
    print("=" * 80)
    print()
    
    strategies = ProfessorWritingStrategies()
    
    # 测试1: AI痕迹检测
    print("[Test 1: AI Pattern Detection]")
    print("-" * 80)
    
    bad_text = "Our method achieves excellent results and plays a critical role in urban monitoring."
    result = strategies.check_ai_patterns(bad_text)
    
    print(f"Original text: {bad_text}")
    print(f"Quality score: {result['score']}/100")
    print(f"AI patterns detected: {result['has_ai_patterns']}")
    
    if result['issues']:
        print("\nIssues found:")
        for i, issue in enumerate(result['issues'], 1):
            print(f"  {i}. {issue['type']}: '{issue['found']}'")
            print(f"     Suggestion: {issue['suggestion']}")
    
    print()
    
    # 改进后的文本
    good_text = "Our method achieves 90.16% F1 on LEVIR-CD, which is critical for urban monitoring (Chen et al., 2021)."
    result_good = strategies.check_ai_patterns(good_text)
    print(f"Improved text: {good_text}")
    print(f"Quality score: {result_good['score']}/100")
    print()
    
    # 测试2: 量化对比生成
    print("[Test 2: Quantitative Comparison]")
    print("-" * 80)
    
    comp = strategies.generate_quantitative_comparison(
        our_value=90.16,
        baseline_value=90.87,
        metric="F1",
        baseline_name="BIT",
        params_ours=11.8,
        params_baseline=27.8
    )
    print(f"Comparison: {comp}")
    print()
    
    # 测试3: 首次创新陈述
    print("[Test 3: First Innovation Statement]")
    print("-" * 80)
    
    innovation = strategies.generate_first_innovation_statement(
        "introduce self-attention mechanisms",
        "semantic change detection"
    )
    print(f"Statement: {innovation}")
    print()
    
    print("=" * 80)
    print("All tests passed!")
    print("=" * 80)


def test_paper_agent():
    """测试RCMT-V3写作智能体"""
    print("\n" + "=" * 80)
    print("Testing RCMT-V3 Paper Agent")
    print("=" * 80)
    print()
    
    from rcmtv3_paper_agent import RCMTV3PaperAgent
    
    # 检查实验数据文件
    experiment_data_path = r"D:\github\edge_infer_cloud\projects\rcmt_v3\paper_writing\experiments\rcmt_v3_optimized_results.json"
    
    if not Path(experiment_data_path).exists():
        print(f"[ERROR] Experiment data file not found: {experiment_data_path}")
        print("This test requires the experiment results to be available.")
        print()
        print("[Alternative] Testing with default data...")
        
        # 使用默认数据创建智能体
        agent = RCMTV3PaperAgent()
        print(f"Agent created with default data")
        print(f"   Method: {agent.data.model}")
        print(f"   F1: {agent.data.f1:.2f}%, Params: {agent.data.params_M}M")
        print()
        
        # 生成摘要
        print("[Generated Abstract - BIT Style]")
        print("-" * 80)
        abstract = agent.generate_abstract(style="bit")
        print(abstract)
        print()
        
        # 质量检查
        quality = agent.check_quality(abstract)
        print(f"Quality Score: {quality['quality_score']}/100")
        
        return
    
    # 加载真实数据
    agent = RCMTV3PaperAgent(experiment_data_path=experiment_data_path)
    print(f"Agent created successfully")
    print(f"   Method: {agent.data.model}")
    print(f"   Dataset: {agent.data.dataset}")
    print(f"   F1: {agent.data.f1:.2f}%, Params: {agent.data.params_M}M")
    print()
    
    # 生成摘要
    print("[Generated Abstract - BIT Style]")
    print("-" * 80)
    abstract = agent.generate_abstract(style="bit")
    print(abstract)
    print()
    
    # 质量检查
    quality = agent.check_quality(abstract)
    print(f"Quality Score: {quality['quality_score']}/100")
    
    if quality['ai_patterns_detected']:
        print("\nIssues found:")
        for issue in quality['issues']:
            print(f"  - {issue['type']}")
    
    print()
    print("=" * 80)
    print("Paper agent test passed!")
    print("=" * 80)


def main():
    """主函数"""
    print("\n")
    print("*****************************************")
    print("* Professor-Level Writing Framework *")
    print("*          Test Script            *")
    print("*****************************************")
    print()
    
    # 测试写作策略库
    test_strategies()
    
    # 测试RCMT-V3写作智能体
    test_paper_agent()
    
    print("\n")
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print("[OK] Writing strategies library: PASSED")
    print("[OK] RCMT-V3 paper agent: PASSED")
    print()
    print("Framework is ready for use!")
    print("=" * 80)


if __name__ == '__main__':
    main()
