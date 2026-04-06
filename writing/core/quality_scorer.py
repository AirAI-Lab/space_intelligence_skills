# -*- coding: utf-8 -*-
"""
Multi-Dimensional Quality Scorer
多维度质量评分器

对学术论文进行多维度质量评分：
- 学术严谨性
- 写作质量
- 技术准确性
- 引用质量
- 创新清晰度

特点：
- ✅ 5个维度评分
- ✅ 量化指标评估
- ✅ A/B/C/D/F等级评定
- ✅ 改进优先级
- ✅ 基准对比

作者: OpenClaw Writing System
日期: 2026-03-24
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


# ==================== 数据结构 ====================

@dataclass
class DimensionScore:
    """维度分数"""
    name: str
    score: float  # 0-100
    weight: float
    metrics: Dict[str, float]
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    """质量报告"""
    overall_score: float  # 0-100
    grade: str  # A, B, C, D, F

    # 维度分数
    dimension_scores: Dict[str, DimensionScore] = field(default_factory=dict)

    # 统计
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0

    # 建议
    improvement_priorities: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)


# ==================== 质量评分器 ====================

class QualityScorer:
    """
    多维度质量评分器

    维度：
    1. Academic Rigor (学术严谨性) - 权重 0.25
    2. Writing Quality (写作质量) - 权重 0.20
    3. Technical Accuracy (技术准确性) - 权重 0.25
    4. Citation Quality (引用质量) - 权重 0.15
    5. Innovation Clarity (创新清晰度) - 权重 0.15
    """

    # 维度定义
    DIMENSIONS = {
        "academic_rigor": {
            "weight": 0.25,
            "metrics": ["quantitative_support", "citation_coverage", "methodological_soundness", "evidence_quality"],
            "threshold": 80
        },
        "writing_quality": {
            "weight": 0.20,
            "metrics": ["clarity", "coherence", "grammar", "style_consistency"],
            "threshold": 75
        },
        "technical_accuracy": {
            "weight": 0.25,
            "metrics": ["notation_correctness", "formula_accuracy", "terminology_precision", "technical_depth"],
            "threshold": 80
        },
        "citation_quality": {
            "weight": 0.15,
            "metrics": ["source_reliability", "citation_relevance", "reference_completeness", "format_consistency"],
            "threshold": 85
        },
        "innovation_clarity": {
            "weight": 0.15,
            "metrics": ["novelty_expression", "contribution_specificity", "differentiation", "impact_quantification"],
            "threshold": 75
        }
    }

    def __init__(self):
        """初始化评分器"""
        self.benchmarks = {
            "sota": {"overall": 85, "academic_rigor": 85, "writing_quality": 80, "technical_accuracy": 85, "citation_quality": 90, "innovation_clarity": 80},
            "accepted": {"overall": 75, "academic_rigor": 75, "writing_quality": 70, "technical_accuracy": 75, "citation_quality": 80, "innovation_clarity": 70},
            "submission": {"overall": 60, "academic_rigor": 60, "writing_quality": 55, "technical_accuracy": 60, "citation_quality": 65, "innovation_clarity": 55}
        }

    # ==================== 主评分方法 ====================

    def calculate_quality(self, paper: str, additional_data: Optional[Dict] = None) -> QualityReport:
        """
        计算综合质量分数

        参数:
            paper: 论文文本
            additional_data: 额外数据（实验结果、引用等）

        返回:
            QualityReport: 质量报告
        """
        if additional_data is None:
            additional_data = {}

        # 计算各维度分数
        dimension_scores = {}

        dimension_scores["academic_rigor"] = self._score_academic_rigor(paper, additional_data)
        dimension_scores["writing_quality"] = self._score_writing_quality(paper)
        dimension_scores["technical_accuracy"] = self._score_technical_accuracy(paper, additional_data)
        dimension_scores["citation_quality"] = self._score_citation_quality(paper, additional_data)
        dimension_scores["innovation_clarity"] = self._score_innovation_clarity(paper, additional_data)

        # 计算总分
        overall_score = sum(
            dim_score.score * self.DIMENSIONS[dim_name]["weight"]
            for dim_name, dim_score in dimension_scores.items()
        )

        # 确定等级
        grade = self._determine_grade(overall_score)

        # 统计问题
        total_issues = sum(len(dim.issues) for dim in dimension_scores.values())
        critical_issues = sum(1 for dim in dimension_scores.values() for issue in dim.issues if "critical" in issue.lower())

        # 生成建议
        improvement_priorities = self._generate_improvement_priorities(dimension_scores)
        strengths = self._identify_strengths(dimension_scores)

        return QualityReport(
            overall_score=round(overall_score, 2),
            grade=grade,
            dimension_scores=dimension_scores,
            total_issues=total_issues,
            critical_issues=critical_issues,
            high_issues=0,  # 简化
            medium_issues=0,  # 简化
            low_issues=0,  # 简化
            improvement_priorities=improvement_priorities,
            strengths=strengths
        )

    # ==================== 维度评分方法 ====================

    def _score_academic_rigor(self, paper: str, data: Dict) -> DimensionScore:
        """评分学术严谨性"""
        score = 100.0
        metrics = {}
        issues = []
        suggestions = []

        # 1. 量化支持检查
        quantitative_matches = len(re.findall(r'\b\d+\.?\d*%\b', paper))
        if quantitative_matches > 10:
            metrics["quantitative_support"] = 100.0
        else:
            metrics["quantitative_support"] = quantitative_matches * 10
            score -= (10 - quantitative_matches) * 3
            issues.append(f"Only {quantitative_matches} quantitative metrics found")
            suggestions.append("Add specific numerical results: F1, IoU, parameter counts")

        # 2. 引用覆盖检查
        citation_matches = len(re.findall(r'\\cite\{[^}]+\}', paper))
        if citation_matches > 15:
            metrics["citation_coverage"] = 100.0
        else:
            metrics["citation_coverage"] = citation_matches * 6
            score -= (15 - citation_matches) * 2
            suggestions.append("Add more citations to support key claims")

        # 3. 方法学严谨性
        has_methodology = bool(re.search(r'section.*method|methodology', paper, re.IGNORECASE))
        has_experiments = bool(re.search(r'section.*exper|experiment', paper, re.IGNORECASE))
        has_ablation = bool(re.search(r'ablation', paper, re.IGNORECASE))

        method_score = (50 if has_methodology else 0) + (30 if has_experiments else 0) + (20 if has_ablation else 0)
        metrics["methodological_soundness"] = method_score
        score += (method_score - 100) * 0.3

        return DimensionScore(
            name="Academic Rigor",
            score=max(0, min(100, score)),
            weight=self.DIMENSIONS["academic_rigor"]["weight"],
            metrics=metrics,
            issues=issues,
            suggestions=suggestions
        )

    def _score_writing_quality(self, paper: str) -> DimensionScore:
        """评分写作质量"""
        score = 100.0
        metrics = {}
        issues = []
        suggestions = []

        # 1. 清晰度检查
        avg_sentence_length = self._calculate_avg_sentence_length(paper)
        if 15 <= avg_sentence_length <= 25:
            metrics["clarity"] = 100.0
        else:
            deviation = min(abs(avg_sentence_length - 20), 10)
            metrics["clarity"] = 100 - deviation * 5
            score -= deviation * 3
            suggestions.append("Vary sentence length for better readability")

        # 2. AI模式检测（简化）
        ai_patterns = [
            r'plays a (?:critical|crucial|important) role',
            r'(?:significantly|dramatically) (?:improves|outperforms)',
            r'excellent performance',
            r'novel method (?:achieves|demonstrates)'
        ]
        ai_pattern_count = sum(len(re.findall(pattern, paper, re.IGNORECASE)) for pattern in ai_patterns)
        metrics["coherence"] = max(0, 100 - ai_pattern_count * 15)
        score -= ai_pattern_count * 10

        if ai_pattern_count > 0:
            issues.append(f"{ai_pattern_count} AI writing patterns detected")
            suggestions.append("Replace AI patterns with specific, quantitative statements")

        # 3. 风格一致性
        metrics["style_consistency"] = 100.0  # 简化

        return DimensionScore(
            name="Writing Quality",
            score=max(0, min(100, score)),
            weight=self.DIMENSIONS["writing_quality"]["weight"],
            metrics=metrics,
            issues=issues,
            suggestions=suggestions
        )

    def _score_technical_accuracy(self, paper: str, data: Dict) -> DimensionScore:
        """评分技术准确性"""
        score = 100.0
        metrics = {}
        suggestions = []

        # 1. 符号正确性
        has_equations = bool(re.search(r'\\begin\{equation\}', paper))
        metrics["notation_correctness"] = 100.0 if has_equations else 70.0
        if not has_equations:
            score -= 10
            suggestions.append("Add mathematical formulations using equation environments")

        # 2. 术语精确性
        technical_terms = ['architecture', 'module', 'mechanism', 'framework', 'network']
        term_count = sum(len(re.findall(rf'\b{term}\b', paper, re.IGNORECASE)) for term in technical_terms)
        metrics["terminology_precision"] = min(100, term_count * 5)
        score += (term_count * 5 - 100) * 0.2

        # 3. 技术深度
        has_implementation = bool(re.search(r'implementation|details|setup', paper, re.IGNORECASE))
        metrics["technical_depth"] = 80.0 if has_implementation else 60.0

        return DimensionScore(
            name="Technical Accuracy",
            score=max(0, min(100, score)),
            weight=self.DIMENSIONS["technical_accuracy"]["weight"],
            metrics=metrics,
            suggestions=suggestions
        )

    def _score_citation_quality(self, paper: str, data: Dict) -> DimensionScore:
        """评分引用质量"""
        score = 100.0
        metrics = {}
        issues = []
        suggestions = []

        # 1. 引用数量
        citations = len(re.findall(r'\\cite\{[^}]+\}', paper))
        if citations >= 20:
            metrics["reference_completeness"] = 100.0
        else:
            metrics["reference_completeness"] = citations * 5
            score -= (20 - citations) * 2
            suggestions.append("Add more references (aim for 20+ citations)")

        # 2. 格式一致性
        has_multiple_formats = bool(re.search(r'\\cite', paper)) and bool(re.search(r'\[\d+\]', paper))
        metrics["format_consistency"] = 100.0 if not has_multiple_formats else 50.0
        if has_multiple_formats:
            score -= 20
            issues.append("Multiple citation formats detected")
            suggestions.append("Use consistent citation format throughout")

        # 3. 相关性（简化）
        metrics["citation_relevance"] = 100.0
        metrics["source_reliability"] = 100.0

        return DimensionScore(
            name="Citation Quality",
            score=max(0, min(100, score)),
            weight=self.DIMENSIONS["citation_quality"]["weight"],
            metrics=metrics,
            issues=issues,
            suggestions=suggestions
        )

    def _score_innovation_clarity(self, paper: str, data: Dict) -> DimensionScore:
        """评分创新清晰度"""
        score = 100.0
        metrics = {}
        suggestions = []

        # 1. 新颖性表达
        innovation_keywords = ['first', 'novel', 'new', 'innovative', 'pioneering']
        innovation_count = sum(len(re.findall(rf'\b{keyword}\b', paper, re.IGNORECASE)) for keyword in innovation_keywords)
        metrics["novelty_expression"] = min(100, innovation_count * 20)

        # 2. 贡献具体性
        has_contributions = bool(re.search(r'contribut|contribution', paper, re.IGNORECASE))
        metrics["contribution_specificity"] = 100.0 if has_contributions else 50.0
        if not has_contributions:
            score -= 30
            suggestions.append("Clearly state your contributions in a numbered list")

        # 3. 区分度
        differentiation = len(re.findall(r'unlike|different|compared to|outperforms', paper, re.IGNORECASE))
        metrics["differentiation"] = min(100, differentiation * 10)

        # 4. 影响力量化
        quantitative_impact = len(re.findall(r'\b\d+\.?\d*%\s*(?:improvement|gain|reduction)', paper, re.IGNORECASE))
        metrics["impact_quantification"] = min(100, quantitative_impact * 25)

        return DimensionScore(
            name="Innovation Clarity",
            score=max(0, min(100, score)),
            weight=self.DIMENSIONS["innovation_clarity"]["weight"],
            metrics=metrics,
            suggestions=suggestions
        )

    # ==================== 辅助方法 ====================

    def _calculate_avg_sentence_length(self, text: str) -> float:
        """计算平均句子长度"""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0

        lengths = [len(s.split()) for s in sentences]
        return sum(lengths) / len(lengths)

    def _determine_grade(self, score: float) -> str:
        """确定等级"""
        if score >= 90:
            return "A+"
        elif score >= 85:
            return "A"
        elif score >= 80:
            return "A-"
        elif score >= 75:
            return "B+"
        elif score >= 70:
            return "B"
        elif score >= 65:
            return "B-"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"

    def _generate_improvement_priorities(self, dimension_scores: Dict[str, DimensionScore]) -> List[str]:
        """生成改进优先级"""
        priorities = []

        # 找出最低的维度
        sorted_dims = sorted(dimension_scores.items(), key=lambda x: x[1].score)

        for dim_name, dim_score in sorted_dims[:3]:  # 最低的3个维度
            if dim_score.score < 75:
                priorities.append(f"Improve {dim_score.name}: {', '.join(dim_score.suggestions[:2])}")

        return priorities

    def _identify_strengths(self, dimension_scores: Dict[str, DimensionScore]) -> List[str]:
        """识别优势"""
        strengths = []

        for dim_name, dim_score in dimension_scores.items():
            if dim_score.score >= 90:
                strengths.append(f"Excellent {dim_score.name}: {dim_score.score}/100")

        return strengths

    def compare_to_benchmark(self, paper_score: float, benchmark: str = "sota") -> Dict[str, Any]:
        """
        对比基准

        参数:
            paper_score: 论文分数
            benchmark: 基准名称

        返回:
            对比结果
        """
        if benchmark not in self.benchmarks:
            benchmark = "sota"

        benchmark_score = self.benchmarks[benchmark]["overall"]
        difference = paper_score - benchmark_score

        return {
            "benchmark": benchmark,
            "benchmark_score": benchmark_score,
            "paper_score": paper_score,
            "difference": difference,
            "meets_benchmark": difference >= 0,
            "assessment": f"Your paper scores {difference:+.1f} points compared to {benchmark} standard"
        }

    def generate_quality_feedback(self, report: QualityReport) -> str:
        """
        生成质量反馈

        参数:
            report: 质量报告

        返回:
            反馈文本
        """
        feedback = []

        feedback.append(f"=== Quality Assessment ===")
        feedback.append(f"Overall Score: {report.overall_score}/100 (Grade: {report.grade})")

        feedback.append(f"\n=== Dimension Scores ===")
        for dim_name, dim_score in report.dimension_scores.items():
            status = "✓" if dim_score.score >= 80 else "⚠" if dim_score.score >= 60 else "✗"
            feedback.append(f"{status} {dim_score.name}: {dim_score.score:.1f}/100")

        if report.strengths:
            feedback.append(f"\n=== Strengths ===")
            for strength in report.strengths:
                feedback.append(f"• {strength}")

        if report.improvement_priorities:
            feedback.append(f"\n=== Priority Improvements ===")
            for i, priority in enumerate(report.improvement_priorities, 1):
                feedback.append(f"{i}. {priority}")

        return "\n".join(feedback)


# ==================== 便捷函数 ====================

def score_paper_quality(paper: str, additional_data: Optional[Dict] = None) -> QualityReport:
    """
    便捷函数：评分论文质量

    参数:
        paper: 论文文本
        additional_data: 额外数据

    返回:
        QualityReport: 质量报告
    """
    scorer = QualityScorer()
    return scorer.calculate_quality(paper, additional_data)


if __name__ == "__main__":
    # 示例使用
    sample_paper = """
    Change detection plays an important role in remote sensing applications.
    We propose a novel method that achieves excellent results on various datasets.
    Our method significantly outperforms existing approaches.
    The method uses 90.5% F1 score on LEVIR-CD dataset.
    We conducted extensive experiments to validate our approach.
    The contributions of this work include: first, we propose a new architecture;
    second, we achieve 90.5% F1; third, we use only 11.8M parameters.
    """

    print("=== Paper Quality Scoring ===")
    report = score_paper_quality(sample_paper, {"f1": 90.5})

    print(f"Overall Score: {report.overall_score}/100")
    print(f"Grade: {report.grade}")

    print("\n=== Detailed Scores ===")
    for dim_name, dim_score in report.dimension_scores.items():
        print(f"{dim_name}: {dim_score.score:.1f}/100")
        if dim_score.suggestions:
            print(f"  Suggestions: {', '.join(dim_score.suggestions[:2])}")

    print("\n=== Feedback ===")
    scorer = QualityScorer()
    print(scorer.generate_quality_feedback(report))
