# -*- coding: utf-8 -*-
"""
Style Consistency Checker
风格一致性检查器

检查论文的多维度风格一致性：
- 术语一致性
- 符号/标注一致性
- 语态一致性
- 时态一致性
- 引用格式一致性

特点：
- ✅ 术语一致性检查
- ✅ 数学符号验证
- ✅ 语态一致性分析
- ✅ 时态使用检查
- ✅ 引用格式验证
- ✅ 改进建议生成

作者: OpenClaw Writing System
日期: 2026-03-24
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import Counter


# ==================== 数据结构 ====================

@dataclass
class TerminologyIssue:
    """术语问题"""
    issue_type: str  # inconsistency, variation, abbreviation
    severity: str
    location: Tuple[int, int]
    found_variants: List[str]
    suggested_standard: str
    explanation: str


@dataclass
class NotationIssue:
    """符号问题"""
    issue_type: str  # inconsistency, formatting, undefined
    severity: str
    location: Tuple[int, int]
    found_notation: str
    suggested_fix: str
    explanation: str


@dataclass
class VoiceIssue:
    """语态问题"""
    issue_type: str  # passive_overuse, inconsistency
    severity: str
    location: Tuple[int, int]
    passive_ratio: float
    suggested_fix: str


@dataclass
class TenseIssue:
    """时态问题"""
    issue_type: str  # inconsistency, incorrect_usage
    severity: str
    location: Tuple[int, int]
    found_tense: str
    expected_tense: str
    explanation: str


@dataclass
class CitationFormatIssue:
    """引用格式问题"""
    issue_type: str  # inconsistency, incorrect_format
    severity: str
    location: Tuple[int, int]
    found_format: str
    expected_format: str


@dataclass
class StyleReport:
    """风格检查报告"""
    has_issues: bool
    overall_score: float  # 0-100

    # 各维度问题
    terminology_issues: List[TerminologyIssue] = field(default_factory=list)
    notation_issues: List[NotationIssue] = field(default_factory=list)
    voice_issues: List[VoiceIssue] = field(default_factory=list)
    tense_issues: List[TenseIssue] = field(default_factory=list)
    citation_format_issues: List[CitationFormatIssue] = field(default_factory=list)

    # 统计信息
    terminology_consistency_score: float = 100.0
    notation_consistency_score: float = 100.0
    voice_consistency_score: float = 100.0
    tense_consistency_score: float = 100.0
    citation_format_score: float = 100.0

    # 建议
    suggestions: List[str] = field(default_factory=list)


# ==================== 风格一致性检查器 ====================

class StyleConsistencyChecker:
    """
    风格一致性检查器

    功能：
    1. 检查术语一致性
    2. 验证数学符号
    3. 分析语态使用
    4. 检查时态一致性
    5. 验证引用格式
    """

    # ==================== 常见术语变体 ====================

    COMMON_TERM_VARIANTS = {
        "change detection": ["change-detection", "changedetection", "Change Detection"],
        "remote sensing": ["Remote-Sensing", "remotesensing"],
        "bi-temporal": ["bitemporal", "bi temporal", "bi-temporal"],
        "deep learning": ["Deep-Learning", "deeplearning"],
        "convolutional neural network": ["CNN", "ConvNet", "Convolutional-Neural-Network"],
        "transformer": ["Transformer", "transformer-based", "Transformer-based"],
        "attention mechanism": ["attention", "Attention", "self-attention"],
        "feature extraction": ["feature-extraction", "FeatureExtraction"],
        "semantic change detection": ["SCD", "semantic-change-detection"],
        "LEVIR-CD": ["LEVIR_CD", "Levir-CD", "levir-cd"]
    }

    # ==================== 数学符号模式 ====================

    NOTATION_PATTERNS = {
        "temporal_indices": [
            r"\bT[_\s]*1\b",
            r"\bT[_\s]*2\b",
            r"\bt[_\s]*1\b",
            r"\bt[_\s]*2\b"
        ],
        "feature_notation": [
            r"\bF[_\s]*[12]\(?[xy]\)?\b",
            r"\bf[_\s]*[12]\(?[xy]\)?\b",
            r"\bFeature[_\s]*[12]\b"
        ],
        "metrics": [
            r"\bF1[_\s]?score\b",
            r"\bIoU\b",
            r"\bPrecision\b",
            r"\bRecall\b"
        ]
    }

    def __init__(self, strict_mode: bool = False):
        """
        初始化检查器

        参数:
            strict_mode: 严格模式
        """
        self.strict_mode = strict_mode

    # ==================== 主检查方法 ====================

    def check_consistency(self, text: str, domain: str = "remote_sensing") -> StyleReport:
        """
        综合风格检查

        参数:
            text: 要检查的文本
            domain: 领域（用于加载领域特定术语）

        返回:
            StyleReport: 检查报告
        """
        issues = []

        # 1. 术语一致性
        terminology_issues = self.check_terminology(text, domain)

        # 2. 符号一致性
        notation_issues = self.check_notation(text)

        # 3. 语态一致性
        voice_issues = self.check_voice(text)

        # 4. 时态一致性
        tense_issues = self.check_tense(text)

        # 5. 引用格式
        citation_issues = self.check_citation_format(text)

        # 计算分数
        term_score = max(0, 100 - len(terminology_issues) * 10)
        notation_score = max(0, 100 - len(notation_issues) * 10)
        voice_score = self._calculate_voice_score(text, voice_issues)
        tense_score = max(0, 100 - len(tense_issues) * 5)
        citation_score = max(0, 100 - len(citation_issues) * 5)

        # 计算总分
        total_issues = (len(terminology_issues) + len(notation_issues) +
                       len(voice_issues) + len(tense_issues) + len(citation_issues))

        overall_score = max(0, 100 - total_issues * 3)

        # 生成建议
        suggestions = self._generate_suggestions(
            terminology_issues, notation_issues, voice_issues, tense_issues, citation_issues
        )

        return StyleReport(
            has_issues=total_issues > 0,
            overall_score=overall_score,
            terminology_issues=terminology_issues,
            notation_issues=notation_issues,
            voice_issues=voice_issues,
            tense_issues=tense_issues,
            citation_format_issues=citation_issues,
            terminology_consistency_score=term_score,
            notation_consistency_score=notation_score,
            voice_consistency_score=voice_score,
            tense_consistency_score=tense_score,
            citation_format_score=citation_score,
            suggestions=suggestions
        )

    # ==================== 术语一致性检查 ====================

    def check_terminology(self, text: str, domain: str) -> List[TerminologyIssue]:
        """
        检查术语一致性

        参数:
            text: 输入文本
            domain: 领域

        返回:
            术语问题列表
        """
        issues = []
        text_lower = text.lower()

        # 检查常见术语变体
        for standard_term, variants in self.COMMON_TERM_VARIANTS.items():
            found_variants = []

            # 检查每个变体
            for variant in variants + [standard_term]:
                if re.search(r'\b' + re.escape(variant.lower()) + r'\b', text_lower):
                    found_variants.append(variant)

            # 如果找到多个变体，报告问题
            if len(found_variants) > 1:
                # 找到第一个出现位置
                first_variant = found_variants[0]
                match = re.search(re.escape(first_variant), text, re.IGNORECASE)
                position = match.span() if match else (0, 0)

                issues.append(TerminologyIssue(
                    issue_type="inconsistency",
                    severity="medium",
                    location=position,
                    found_variants=found_variants,
                    suggested_standard=standard_term,
                    explanation=f"Multiple variants of '{standard_term}' found: {', '.join(found_variants)}. Use consistent terminology."
                ))

        return issues

    # ==================== 符号一致性检查 ====================

    def check_notation(self, text: str) -> List[NotationIssue]:
        """
        检查符号一致性

        参数:
            text: 输入文本

        返回:
            符号问题列表
        """
        issues = []

        # 检查时间下标一致性
        temporal_usages = []
        for pattern in self.NOTATION_PATTERNS["temporal_indices"]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                temporal_usages.append((match.group(), match.span()))

        # 检查不一致的时间下标
        if len(temporal_usages) > 1:
            # 简化检查：看是否有不同格式
            formats = set()
            for usage, _ in temporal_usages:
                formats.add(re.sub(r'\d', 'N', usage))

            if len(formats) > 1:
                issues.append(NotationIssue(
                    issue_type="inconsistency",
                    severity="medium",
                    location=temporal_usages[0][1],
                    found_notation=", ".join(list(formats)),
                    suggested_fix="Use consistent format: T₁ and T₂ (or T_1 and T_2)",
                    explanation=f"Multiple temporal index formats found: {', '.join(formats)}"
                ))

        # 检查特征符号
        feature_usages = []
        for pattern in self.NOTATION_PATTERNS["feature_notation"]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                feature_usages.append((match.group(), match.span()))

        if len(feature_usages) > 1:
            formats = set()
            for usage, _ in feature_usages:
                formats.add(re.sub(r'\d', 'N', usage.lower()))

            if len(formats) > 1:
                issues.append(NotationIssue(
                    issue_type="inconsistency",
                    severity="low",
                    location=feature_usages[0][1],
                    found_notation=", ".join(list(formats)),
                    suggested_fix="Use consistent format: F₁(x) and F₂(x)",
                    explanation="Multiple feature notation formats found"
                ))

        return issues

    # ==================== 语态一致性检查 ====================

    def check_voice(self, text: str) -> List[VoiceIssue]:
        """
        检查语态一致性

        参数:
            text: 输入文本

        返回:
            语态问题列表
        """
        issues = []

        # 检测被动语态
        passive_patterns = [
            r'\b(was|were|is|are|been|being)\s+\w+ed\b',
            r'\b(was|were|is|are)\s+\w+ed\s+by\b'
        ]

        passive_count = 0
        total_sentences = len(re.split(r'[.!?]+', text))

        for pattern in passive_patterns:
            passive_count += len(re.findall(pattern, text, re.IGNORECASE))

        if total_sentences > 0:
            passive_ratio = passive_count / total_sentences

            # 如果被动语态超过30%
            if passive_ratio > 0.3:
                issues.append(VoiceIssue(
                    issue_type="passive_overuse",
                    severity="medium",
                    location=(0, 0),
                    passive_ratio=passive_ratio,
                    suggested_fix=f"Reduce passive voice from {passive_ratio*100:.1f}% to under 30%. Use active voice: 'We propose' instead of 'is proposed'."
                ))

        return issues

    def _calculate_voice_score(self, text: str, issues: List[VoiceIssue]) -> float:
        """计算语态分数"""
        if not issues:
            return 100.0

        # 根据问题严重程度扣分
        penalty = sum(20 if issue.severity == "high" else 10 for issue in issues)
        return max(0, 100 - penalty)

    # ==================== 时态一致性检查 ====================

    def check_tense(self, text: str) -> List[TenseIssue]:
        """
        检查时态一致性

        参数:
            text: 输入文本

        返回:
            时态问题列表
        """
        issues = []

        # 检查实验描述中的时态
        # 实验结果应该用过去时
        experiment_contexts = [
            r'(?:We|Our|The)\s+(?:experiment|result|study|analysis)',
            r'(?:Table|Figure)\s+\d+'
        ]

        for context_pattern in experiment_contexts:
            context_matches = re.finditer(context_pattern, text, re.IGNORECASE)

            for match in context_matches:
                # 获取上下文后的句子
                start = match.start()
                end = min(start + 200, len(text))
                context_text = text[start:end]

                # 检查是否用了现在时描述实验（应该用过去时）
                if re.search(r'\b(?:achieves|demonstrates|shows?|indicates?)\b', context_text):
                    issues.append(TenseIssue(
                        issue_type="incorrect_usage",
                        severity="low",
                        location=(start, end),
                        found_tense="present",
                        expected_tense="past",
                        explanation="Experimental results should be described in past tense: 'achieved' instead of 'achieves'"
                    ))

        return issues

    # ==================== 引用格式检查 ====================

    def check_citation_format(self, text: str) -> List[CitationFormatIssue]:
        """
        检查引用格式一致性

        参数:
            text: 输入文本

        返回:
            引用格式问题列表
        """
        issues = []

        # 提取所有引用
        citation_patterns = [
            (r'\\cite\{[^}]+\}', "latex"),
            (r'\[\d+(?:,\s*\d+)*\]', "numeric"),
            (r'\([^)]+, \d{4}\)', "author_year")
        ]

        found_formats = []
        for pattern, format_name in citation_patterns:
            if re.search(pattern, text):
                found_formats.append(format_name)

        # 如果发现多种引用格式
        if len(found_formats) > 1:
            issues.append(CitationFormatIssue(
                issue_type="inconsistency",
                severity="high",
                location=(0, 0),
                found_format=", ".join(found_formats),
                expected_format="Choose one citation format and use it consistently",
                explanation=f"Multiple citation formats detected: {', '.join(found_formats)}"
            ))

        return issues

    # ==================== 建议生成 ====================

    def _generate_suggestions(self, *issue_lists) -> List[str]:
        """生成改进建议"""
        suggestions = []
        all_issues = [issue for issues in issue_lists for issue in issues]

        if not all_issues:
            return ["No style issues detected. Your paper has excellent consistency."]

        # 基于问题类型生成建议
        issue_types = Counter(issue.issue_type for issue in all_issues)

        if "inconsistency" in issue_types:
            suggestions.append("Terminology/Notation: Establish a style guide with standard terms and notations. Use find-and-replace to standardize variants.")

        if "passive_overuse" in issue_types:
            suggestions.append("Voice: Convert passive constructions to active voice. Use 'We propose' instead of 'is proposed'.")

        if "incorrect_usage" in issue_types:
            suggestions.append("Tense: Review experimental sections. Use past tense ('achieved', 'showed') for results, present tense for facts.")

        if len(all_issues) > 10:
            suggestions.append("Overall: Multiple consistency issues detected. Consider running a systematic review of terminology and notation before final submission.")

        return suggestions


# ==================== 便捷函数 ====================

def check_style_consistency(text: str, domain: str = "remote_sensing") -> StyleReport:
    """
    便捷函数：检查风格一致性

    参数:
        text: 输入文本
        domain: 领域

    返回:
        StyleReport: 检查报告
    """
    checker = StyleConsistencyChecker()
    return checker.check_consistency(text, domain)


if __name__ == "__main__":
    # 示例使用
    sample_text = """
    Change detection plays an important role in remote sensing applications.
    Change-detection is also crucial for urban monitoring.
    The method is proposed to address this challenge.
    We achieve excellent performance on LEVIR-CD.
    Levir-CD also shows strong results.
    The network achieves 90% F1 (Table 1).
    Figure 1 shows the architecture.
    """

    print("=== Style Consistency Check ===")
    report = check_style_consistency(sample_text)

    print(f"Overall Score: {report.overall_score}/100")
    print(f"Has Issues: {report.has_issues}")

    print("\n--- Terminology Issues ---")
    for issue in report.terminology_issues:
        print(f"  - {issue.found_variants}: {issue.explanation}")

    print("\n--- Voice Issues ---")
    for issue in report.voice_issues:
        print(f"  - Passive ratio: {issue.passive_ratio*100:.1f}%: {issue.suggested_fix}")

    print("\n--- Suggestions ---")
    for suggestion in report.suggestions:
        print(f"  - {suggestion}")
