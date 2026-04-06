# -*- coding: utf-8 -*-
"""
Iterative Improver
自动迭代改进引擎

基于质量报告自动改进论文：
- 分析问题
- 生成改进
- 验证改进
- 迭代直到达标

特点：
- ✅ 基于AI模式检测改进
- ✅ 引用修复
- ✅ 风格一致性改进
- ✅ 自动迭代优化
- ✅ 改进验证

作者: OpenClaw Writing System
日期: 2026-03-24
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# 导入其他组件
from ai_pattern_detector import AIPatternDetector, PatternDetectionResult
from citation_verifier import CitationVerifier, VerificationResult
from style_consistency_checker import StyleConsistencyChecker, StyleReport
from quality_scorer import QualityScorer, QualityReport
from templates.anti_ai_templates import AntiAIWritingTemplates


# ==================== 数据结构 ====================

@dataclass
class ImprovementAction:
    """改进动作"""
    action_type: str  # replace, insert, delete
    location: Tuple[int, int]
    original_text: str
    improved_text: str
    reason: str
    confidence: float


@dataclass
class IterationResult:
    """迭代结果"""
    original_paper: str
    improved_paper: str
    iterations_used: int
    quality_progression: List[float]
    actions_taken: List[ImprovementAction]
    final_quality_score: float
    target_met: bool


# ==================== 迭代改进器 ====================

class IterativeImprover:
    """
    自动迭代改进器

    功能：
    1. 分析质量问题
    2. 生成改进建议
    3. 应用改进
    4. 验证效果
    5. 迭代优化
    """

    def __init__(self, quality_threshold: float = 80.0, max_iterations: int = 5):
        """
        初始化改进器

        参数:
            quality_threshold: 目标质量分数
            max_iterations: 最大迭代次数
        """
        self.quality_threshold = quality_threshold
        self.max_iterations = max_iterations

        # 初始化检测器
        self.ai_detector = AIPatternDetector()
        self.citation_verifier = CitationVerifier()
        self.style_checker = StyleConsistencyChecker()
        self.quality_scorer = QualityScorer()
        self.anti_ai_templates = AntiAIWritingTemplates()

    # ==================== 主改进方法 ====================

    def improve_paper(self, paper: str, quality_report: QualityReport) -> str:
        """
        改进论文

        参数:
            paper: 论文文本
            quality_report: 质量报告

        返回:
            改进后的论文
        """
        improved_paper = paper
        actions = []

        # 1. 修复AI模式
        if quality_report.dimension_scores.get("writing_quality", type(None)).score if quality_report.dimension_scores.get("writing_quality") else 0 < 75:
            improved_paper, ai_actions = self._fix_ai_patterns(improved_paper)
            actions.extend(ai_actions)

        # 2. 增强引用
        if quality_report.dimension_scores.get("citation_quality", type(None)).score if quality_report.dimension_scores.get("citation_quality") else 0 < 80:
            improved_paper, citation_actions = self._enhance_citations(improved_paper)
            actions.extend(citation_actions)

        # 3. 改进风格
        style_report = self.style_checker.check_consistency(improved_paper)
        if style_report.overall_score < 80:
            improved_paper, style_actions = self._improve_style(improved_paper, style_report)
            actions.extend(style_actions)

        return improved_paper

    def iterate_to_quality(self, paper: str, target_score: Optional[float] = None,
                          additional_data: Optional[Dict] = None) -> IterationResult:
        """
        迭代直到达到目标质量

        参数:
            paper: 原始论文
            target_score: 目标分数（默认使用初始化的阈值）
            additional_data: 额外数据

        返回:
            IterationResult: 迭代结果
        """
        if target_score is None:
            target_score = self.quality_threshold

        if additional_data is None:
            additional_data = {}

        current_paper = paper
        quality_scores = []
        all_actions = []

        for iteration in range(self.max_iterations):
            # 评估当前质量
            quality_report = self.quality_scorer.calculate_quality(current_paper, additional_data)
            quality_scores.append(quality_report.overall_score)

            # 检查是否达标
            if quality_report.overall_score >= target_score:
                return IterationResult(
                    original_paper=paper,
                    improved_paper=current_paper,
                    iterations_used=iteration + 1,
                    quality_progression=quality_scores,
                    actions_taken=all_actions,
                    final_quality_score=quality_report.overall_score,
                    target_met=True
                )

            # 应用改进
            current_paper = self.improve_paper(current_paper, quality_report)

            # 记录动作（简化）
            all_actions.append(ImprovementAction(
                action_type="improvement",
                location=(0, 0),
                original_text="",
                improved_text="",
                reason=f"Iteration {iteration + 1} improvements applied",
                confidence=0.8
            ))

        # 最终评估
        final_quality = self.quality_scorer.calculate_quality(current_paper, additional_data)
        quality_scores.append(final_quality.overall_score)

        return IterationResult(
            original_paper=paper,
            improved_paper=current_paper,
            iterations_used=self.max_iterations,
            quality_progression=quality_scores,
            actions_taken=all_actions,
            final_quality_score=final_quality.overall_score,
            target_met=final_quality.overall_score >= target_score
        )

    # ==================== 改进方法 ====================

    def _fix_ai_patterns(self, text: str) -> Tuple[str, List[ImprovementAction]]:
        """修复AI模式"""
        actions = []

        # 检测AI模式
        detection_result = self.ai_detector.detect_patterns(text)

        # 应用反AI模板
        improved_text = self.anti_ai_templates.replace_ai_patterns(text, {})

        # 记录动作
        if detection_result.all_patterns:
            actions.append(ImprovementAction(
                action_type="replace",
                location=(0, 0),
                original_text="AI patterns detected",
                improved_text="Humanized",
                reason=f"Fixed {len(detection_result.all_patterns)} AI patterns",
                confidence=0.8
            ))

        return improved_text, actions

    def _enhance_citations(self, text: str) -> Tuple[str, List[ImprovementAction]]:
        """增强引用"""
        actions = []

        # 检测引用问题
        citation_issues = self.citation_verifier.verify_text_citations(text)

        # 简化处理：如果有问题，建议检查引用
        if citation_issues:
            actions.append(ImprovementAction(
                action_type="review",
                location=(0, 0),
                original_text="",
                improved_text="",
                reason=f"Review {len(citation_issues)} citation issues",
                confidence=0.7
            ))

        return text, actions

    def _improve_style(self, text: str, style_report: StyleReport) -> Tuple[str, List[ImprovementAction]]:
        """改进风格"""
        actions = []
        improved_text = text

        # 修复术语不一致
        for issue in style_report.terminology_issues:
            if issue.suggested_standard:
                improved_text = improved_text.replace(issue.found_variants[0], issue.suggested_standard)
                actions.append(ImprovementAction(
                    action_type="replace",
                    location=issue.location,
                    original_text=issue.found_variants[0],
                    improved_text=issue.suggested_standard,
                    reason=issue.explanation,
                    confidence=0.9
                ))

        return improved_text, actions

    def _validate_improvement(self, original: str, improved: str) -> bool:
        """
        验证改进是否有效

        参数:
            original: 原始文本
            improved: 改进后文本

        返回:
            是否有效
        """
        original_score = self.quality_scorer.calculate_quality(original).overall_score
        improved_score = self.quality_scorer.calculate_quality(improved).overall_score

        return improved_score > original_score


# ==================== 便捷函数 ====================

def improve_paper_iteratively(paper: str, target_score: float = 80.0,
                             additional_data: Optional[Dict] = None) -> IterationResult:
    """
    便捷函数：迭代改进论文

    参数:
        paper: 论文文本
        target_score: 目标分数
        additional_data: 额外数据

    返回:
        IterationResult: 迭代结果
    """
    improver = IterativeImprover(quality_threshold=target_score)
    return improver.iterate_to_quality(paper, target_score, additional_data)


if __name__ == "__main__":
    # 示例使用
    ai_paper = """
    Change detection plays a critical role in many applications.
    Our novel method achieves excellent results on various datasets.
    Significantly, we outperform existing approaches.
    Extensive experiments show the effectiveness of our approach.
    """

    print("=== Iterative Improvement ===")
    result = improve_paper_iteratively(ai_paper, target_score=75.0)

    print(f"Original quality: {result.quality_progression[0]:.1f}/100")
    print(f"Final quality: {result.final_quality_score:.1f}/100")
    print(f"Iterations: {result.iterations_used}")
    print(f"Target met: {result.target_met}")

    print(f"\n=== Improved Paper ===")
    print(result.improved_paper[:500])
