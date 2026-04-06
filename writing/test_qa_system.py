# -*- coding: utf-8 -*-
"""
论文生成工具优化演示
Demonstration of Optimized Paper Generation Tool

展示新的QA系统功能：
- AI模式深度检测
- 引用验证
- 风格一致性检查
- 多维度质量评分
- 自动迭代改进

作者: OpenClaw Writing System
日期: 2026-03-24
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))

from ai_pattern_detector import AIPatternDetector
from citation_verifier import CitationVerifier
from style_consistency_checker import StyleConsistencyChecker
from quality_scorer import QualityScorer
from iterative_improver import IterativeImprover
from related_work_generator import RelatedWorkGenerator
from anti_ai_templates import AntiAIWritingTemplates


def demo_ai_pattern_detection():
    """演示AI模式检测"""
    print("=" * 60)
    print("DEMO 1: AI Pattern Detection")
    print("=" * 60)

    ai_text = """
    Change detection plays a critical role in many applications.
    Our novel method achieves excellent performance on various datasets.
    Significantly, we outperform existing approaches.
    Extensive experiments show the effectiveness of our approach.
    """

    detector = AIPatternDetector()
    result = detector.detect_patterns(ai_text)

    print(f"\nOriginal AI-Text:")
    print(ai_text)

    print(f"\nDetection Results:")
    print(f"  Overall Score: {result.overall_score:.1f}/100")
    print(f"  Patterns Detected: {len(result.all_patterns)}")
    print(f"  Sentence Analysis: {result.sentence_analysis.total_sentences} sentences, "
          f"avg length: {result.sentence_analysis.avg_length:.1f} words")
    print(f"  Opening Diversity: {result.sentence_analysis.opening_diversity:.2f}")

    # 显示前5个模式
    if result.all_patterns:
        print(f"\n  Top Patterns:")
        for pattern in result.all_patterns[:5]:
            print(f"    - [{pattern.severity}] {pattern.pattern_name}: '{pattern.found_text[:40]}...'")

    # 人类化建议
    suggestions = detector.generate_humanization_suggestions(result)
    if suggestions:
        print(f"\n  Humanization Suggestions:")
        for suggestion in suggestions[:3]:
            print(f"    - {suggestion}")

    # 人类化文本
    humanized = AntiAIWritingTemplates.generate_humanized_paragraph(
        ai_text, {"f1": 90.5, "dataset": "LEVIR-CD"}
    )
    print(f"\nHumanized Text:")
    print(humanized)


def demo_citation_verification():
    """演示引用验证"""
    print("\n" + "=" * 60)
    print("DEMO 2: Citation Verification")
    print("=" * 60)

    verifier = CitationVerifier()

    # 验证已知引用
    print("\nVerifying known citations:")
    result = verifier.verify_citation("bit", {"year": 2021, "results": {"levir_cd": {"f1": 90.87}}})
    print(f"  BIT: Valid={result.is_valid}, Confidence={result.confidence:.1f}")
    if result.verified_reference:
        print(f"    Title: {result.verified_reference.title}")
        print(f"    Authors: {result.verified_reference.authors}")

    # 检测幻觉
    print("\nDetecting citation hallucinations:")
    text_with_hallucination = "Our method outperforms BIT [cite], and also FakeMethod2024 [cite]."
    hallucination_result = verifier.detect_hallucinations(text_with_hallucination)
    print(f"  Has hallucinations: {hallucination_result.has_hallucinations}")
    for issue in hallucination_result.suspicious_citations:
        print(f"    - {issue.found_citation}: {issue.description}")

    # 建议引用
    print("\nSuggesting citations:")
    suggestions = verifier.suggest_citations("transformer change detection", "bi-temporal images")
    for suggestion in suggestions[:3]:
        print(f"  - {suggestion.reference_key} ({suggestion.relevance_score:.2f}): {suggestion.reason}")


def demo_quality_scoring():
    """演示质量评分"""
    print("\n" + "=" * 60)
    print("DEMO 3: Multi-Dimensional Quality Scoring")
    print("=" * 60)

    scorer = QualityScorer()

    sample_paper = """
    Change detection plays an important role in remote sensing applications.
    We propose a novel method that achieves 90.5% F1 score.
    The method uses a hybrid architecture with 11.8M parameters.
    Experiments on LEVIR-CD dataset demonstrate effectiveness.
    """

    report = scorer.calculate_quality(sample_paper, {"f1": 90.5, "params": 11.8})

    print(f"\nOverall Score: {report.overall_score:.1f}/100")
    print(f"Grade: {report.grade}")
    print(f"\nDimension Scores:")
    for dim_name, dim_score in report.dimension_scores.items():
        print(f"  {dim_score.name}: {dim_score.score:.1f}/100")
        if dim_score.suggestions:
            print(f"    Suggestions: {', '.join(dim_score.suggestions[:2])}")

    # 生成反馈
    feedback = scorer.generate_quality_feedback(report)
    print(f"\nQuality Feedback:")
    print(feedback)


def demo_related_work_generation():
    """演示Related Work生成"""
    print("\n" + "=" * 60)
    print("DEMO 4: Related Work Auto-Generation")
    print("=" * 60)

    generator = RelatedWorkGenerator()

    method_info = {
        "name": "RCMT-V3",
        "f1": 90.16,
        "params": 11.8,
        "dataset": "LEVIR-CD"
    }

    related_work = generator.generate_related_work(method_info, target_length=500)

    print(f"\nGenerated Related Work (first 500 chars):")
    print(related_work[:500])


def demo_iterative_improvement():
    """演示迭代改进"""
    print("\n" + "=" * 60)
    print("DEMO 5: Iterative Improvement")
    print("=" * 60)

    improver = IterativeImprover(quality_threshold=75.0, max_iterations=3)

    ai_paper = """
    Change detection plays a critical role in many applications.
    Our novel method achieves excellent results on various datasets.
    Significantly, we outperform existing approaches.
    Extensive experiments show the effectiveness of our approach.
    """

    print(f"\nOriginal Paper (first 200 chars):")
    print(ai_paper[:200])

    # 迭代改进
    result = improver.iterate_to_quality(ai_paper, target_score=75.0)

    print(f"\nImprovement Results:")
    print(f"  Original score: {result.quality_progression[0]:.1f}/100")
    print(f"  Final score: {result.final_quality_score:.1f}/100")
    print(f"  Iterations: {result.iterations_used}")
    print(f"  Target met: {result.target_met}")

    print(f"\nImproved Paper (first 200 chars):")
    print(result.improved_paper[:200])


def demo_style_consistency():
    """演示风格一致性检查"""
    print("\n" + "=" * 60)
    print("DEMO 6: Style Consistency Check")
    print("=" * 60)

    checker = StyleConsistencyChecker()

    inconsistent_text = """
    Change detection plays an important role in remote sensing.
    Change-detection is also crucial for urban planning.
    The method is proposed to address this challenge.
    Our method achieves 90% F1 on LEVIR-CD.
    Levir-CD also shows strong results.
    """

    report = checker.check_consistency(inconsistent_text)

    print(f"\nOverall Score: {report.overall_score:.1f}/100")
    print(f"Has Issues: {report.has_issues}")

    if report.terminology_issues:
        print(f"\nTerminology Issues ({len(report.terminology_issues)}):")
        for issue in report.terminology_issues:
            print(f"  - Variants: {issue.found_variants}")
            print(f"    Standard: {issue.suggested_standard}")

    if report.voice_issues:
        print(f"\nVoice Issues ({len(report.voice_issues)}):")
        for issue in report.voice_issues:
            print(f"  - Passive ratio: {issue.passive_ratio*100:.1f}%")

    print(f"\nSuggestions:")
    for suggestion in report.suggestions[:3]:
        print(f"  - {suggestion}")


def main():
    """主演示函数"""
    print("\n")
    print("*" * 60)
    print("  论文生成工具优化演示 / Paper Generation Tool Demo")
    print("  教授级写作 / Professor-Level Writing")
    print("  去除AI味 / AI Pattern Removal")
    print("  质量保证 / Quality Assurance")
    print("*" * 60)

    # 运行演示
    demo_ai_pattern_detection()
    demo_citation_verification()
    demo_quality_scoring()
    demo_style_consistency()
    demo_related_work_generation()
    demo_iterative_improvement()

    print("\n" + "=" * 60)
    print("  所有演示完成！/ All Demos Complete!")
    print("  系统已优化，可用于教授级论文写作 / System optimized for professor-level writing")
    print("=" * 60)
    print("\n")


if __name__ == "__main__":
    main()
