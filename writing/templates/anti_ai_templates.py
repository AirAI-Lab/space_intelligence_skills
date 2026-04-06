# -*- coding: utf-8 -*-
"""
Anti-AI Writing Templates and Strategies
反AI写作模板和策略

基于2025年最新研究，提供人类化写作模板和策略：
- 句式多样化策略
- 人类化技术
- 去AI味表达替换
- 教授级写作增强

特点：
- ✅ 10+种句式开头模式
- ✅ 多样化句长策略
- ✅ 元评论和不确定性表达
- ✅ 量化数据驱动模板
- ✅ 个人声音和作者视角

作者: OpenClaw Writing System
日期: 2026-03-24
参考: 2025年AI检测研究、GPTZero、Grammarly AI检测指南
"""

import re
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# ==================== 数据结构 ====================

@dataclass
class SentenceVariation:
    """句式变体"""
    original: str
    variations: List[str]
    category: str  # opening, length, structure


@dataclass
class HumanizationSuggestion:
    """人类化建议"""
    original_text: str
    issue_type: str
    suggested_replacement: str
    explanation: str


# ==================== 反AI写作模板 ====================

class AntiAIWritingTemplates:
    """
    反AI写作模板库

    提供：
    1. 句式开头多样性
    2. 句长多样性
    3. 结构多样性
    4. 人类化表达
    5. 量化数据驱动
    """

    # ==================== 句式开头模式 ====================

    OPENING_PATTERNS = {
        "quantitative_lead": [
            "{value}% {metric} on {dataset} demonstrates the effectiveness of our approach.",
            "With {value}% {metric}, our method achieves state-of-the-art performance on {dataset}.",
            "The {value}% {metric} score on {dataset} represents a significant improvement.",
            "Achieving {value}% {metric} on {dataset}, our method outperforms previous approaches."
        ],
        "technical_lead": [
            "The {Architecture} architecture enables our method to capture long-range dependencies.",
            "By incorporating {Technique}, we address the limitation of existing methods.",
            "Our approach leverages {Mechanism} to improve {aspect} of change detection.",
            "The {Module} module is designed to capture {property} in bi-temporal features."
        ],
        "contextual_lead": [
            "In remote sensing change detection, {Challenge} remains a significant obstacle.",
            "For applications such as {Application}, accurate change detection is critical.",
            "The {Dataset} dataset presents unique challenges due to {characteristic}.",
            "Change detection in {Domain} requires both {Requirement1} and {Requirement2}."
        ],
        "comparative_lead": [
            "Unlike {Baseline}, which struggles with {Limitation}, our method addresses this through {Innovation}.",
            "While {Method} achieves {Value}% {metric}, it requires {Resource}, limiting its practical application.",
            "Compared to existing approaches that {Approach}, our method {Differentiation}.",
            "Previous work has focused on {Focus}, but we argue that {Alternative} is equally important."
        ],
        "temporal_lead": [
            "Recent advances in {Field} have enabled new approaches to {Task}.",
            "Over the past few years, {Technology} has revolutionized {Domain}.",
            "Building on recent progress in {Area}, we propose {Innovation}.",
            "The emergence of {Technology} has created opportunities for {Application}."
        ],
        "question_lead": [
            "How can we achieve {Goal} while maintaining {Constraint}?",
            "What enables {Method} to outperform {Baseline} in {Scenario}?",
            "Why do existing methods struggle with {Challenge}, and how can we address this?",
            "Can we achieve {Goal} without sacrificing {Aspect}?"
        ],
        "finding_lead": [
            "We find that {Finding}, which contradicts the common assumption that {Assumption}.",
            "Our experiments reveal that {Finding}, suggesting that {Implication}.",
            "Analysis of {Data} shows that {Finding}, highlighting the importance of {Factor}.",
            "We observe that {Observation}, which has important implications for {Application}."
        ]
    }

    # ==================== 句长多样性 ====================

    SENTENCE_LENGTH_PATTERNS = {
        "short": {  # 8-12 words
            "templates": [
                "{Method} achieves {value}% {metric}.",
                "We employ {Technique} for {Task}.",
                "This approach improves {Aspect}.",
                "Experiments confirm this finding.",
                "The results demonstrate effectiveness."
            ]
        },
        "medium": {  # 15-25 words
            "templates": [
                "Our method achieves {value}% {metric} on {dataset}, outperforming {baseline} by {improvement}%.",
                "We incorporate {Technique} to capture {property}, which is critical for {application}.",
                "The {Module} module processes bi-temporal features using {mechanism} to extract changes.",
                "Experiments on {dataset} demonstrate that our approach achieves competitive results."
            ]
        },
        "long": {  # 30-40 words
            "templates": [
                "By combining {Technique1} with {Technique2}, our method achieves {value}% {metric} on {dataset}, representing a {improvement}% improvement over {baseline} while using {reduction}% fewer parameters.",
                "The key innovation of our approach is the use of {mechanism} to capture {property}, which addresses the limitation of existing methods that struggle with {challenge}.",
                "We design a {architecture} that balances {aspect1} and {aspect2}, achieving {value}% {metric} with only {params}M parameters, making it suitable for {application}."
            ]
        }
    }

    # ==================== 句式结构多样性 ====================

    SENTENCE_STRUCTURE_PATTERNS = {
        "simple_declarative": [
            "{Subject} {verb} {object}.",
            "The {noun} {verb} {object}.",
            "We {verb} {object} using {method}."
        ],
        "compound_with_contrast": [
            "{Method} achieves {result}, but it requires {resource}.",
            "{Approach} addresses {challenge}, yet it introduces {limitation}.",
            "We employ {Technique}, which improves {aspect1} but may affect {aspect2}."
        ],
        "complex_with_subordination": [
            "Although {Method} achieves {result}, it struggles with {challenge}.",
            "Because {Technique} captures {property}, it improves {aspect}.",
            "When {condition} occurs, our method {response}.",
            "While {baseline} achieves {value1}, our method achieves {value2}."
        ],
        "inverted_structure": [
            "Critical to our approach is {Component}, which {function}.",
            "Even more important is {Aspect}, which determines {outcome}.",
            "Of particular note is {Finding}, which suggests {implication}."
        ],
        "participial_opening": [
            "Building on {approach}, we propose {innovation}.",
            "Combining {Technique1} with {Technique2}, our method achieves {result}.",
            "Motivated by {factor}, we designed {Component} to {goal}.",
            "Addressing {challenge}, we introduce {Method} for {task}."
        ]
    }

    # ==================== 人类化表达 ====================

    HUMANIZATION_PATTERNS = {
        "meta_commentary": [
            "Interestingly, we find that {finding}.",
            "Surprisingly, the results show that {observation}.",
            "It is worth noting that {observation}.",
            "Our analysis reveals an important insight: {finding}.",
            "We observed that {finding}, which suggests {implication}."
        ],
        "uncertainty_acknowledgment": [
            "While our method achieves strong results, it may struggle with {scenario}.",
            "There are limitations to our approach, particularly in {context}.",
            "We acknowledge that {aspect} could be further improved.",
            "The performance in {scenario} suggests room for improvement.",
            "This approach is not without limitations, notably {limitation}."
        ],
        "authorial_voice": [
            "We believe that {claim}.",
            "Our analysis suggests that {finding}.",
            "We argue that {position}.",
            "In our view, {perspective}.",
            "Based on our experiments, we conclude that {finding}."
        ],
        "concrete_specificity": [
            "Specifically, on {dataset}, we achieve {value}% {metric}.",
            "For example, in {scenario}, our method improves {aspect} by {X}%.",
            "To illustrate, Figure {N} shows that {observation}.",
            "Consider the case of {example}, where {finding}."
        ]
    }

    # ==================== 量化数据驱动表达 ====================

    QUANTITATIVE_PATTERNS = {
        "performance_claim": [
            "Our method achieves {value}% {metric} on {dataset} (Table {N}), outperforming {baseline} by {improvement} percentage points.",
            "Experiments on {dataset} show {value}% {metric} (Figure {N}), which represents a {improvement}% improvement over {baseline}.",
            "We report {value}% {metric} on {dataset} with {params}M parameters, achieving state-of-the-art performance."
        ],
        "efficiency_claim": [
            "Despite using {reduction}% fewer parameters than {baseline}, our method achieves {value}% {metric}.",
            "Our method achieves {value}% {metric} with only {params}M parameters, making it suitable for edge deployment.",
            "We reduce parameter count by {reduction}% while maintaining {value}% of {baseline}'s performance."
        ],
        "comparison_claim": [
            "Compared to {baseline} ({baseline_value}% {metric}), our method achieves {our_value}% {metric} (Δ={improvement}%).",
            "While {baseline} achieves {baseline_value}% {metric}, our approach improves this to {our_value}% ({improvement}% gain).",
            "Our method outperforms {baseline} by {improvement} percentage points on {dataset}."
        ]
    }

    # ==================== 替换AI模式 ====================

    AI_PATTERN_REPLACEMENTS = {
        "plays_critical_role": [
            "{Domain} is essential for {specific_application}, where it enables {specific_benefit}.",
            "In {application}, {domain} enables {specific_benefit}, which is critical for {outcome}.",
            "{Domain} has become indispensable for {application} due to its ability to {benefit}."
        ],
        "significantly_improves": [
            "improves {metric} by {X}%, from {baseline}% to {ours}%",
            "achieves a {X}% improvement in {metric}, reaching {value}%",
            "increases {metric} by {X} percentage points to {value}%"
        ],
        "excellent_performance": [
            "achieves {value}% {metric} on {dataset}",
            "obtains competitive results with {value}% {metric}",
            "demonstrates strong performance with {value}% {metric}"
        ],
        "extensive_experiments": [
            "Ablation studies (Section {N}) reveal that {finding}.",
            "Experiments on {N} datasets demonstrate that {finding}.",
            "We conducted {N} experiments to assess {aspect}. Results show that {finding}."
        ],
        "novel_method": [
            "{Method} introduces {innovation}, which addresses {challenge}.",
            "Our approach, {Method}, employs {technique} to achieve {goal}.",
            "We present {Method}, which differs from previous approaches by {differentiation}."
        ]
    }

    # ==================== 方法 ====================

    @staticmethod
    def vary_sentence_opening(text: str, context: Optional[Dict] = None) -> str:
        """
        变化句子开头

        参数:
            text: 输入文本
            context: 上下文信息（数据集、指标等）

        返回:
            变化后的文本
        """
        if not context:
            context = {}

        # 简化的实现：选择一个开头模式
        pattern_type = random.choice(list(AntiAIWritingTemplates.OPENING_PATTERNS.keys()))
        patterns = AntiAIWritingTemplates.OPENING_PATTERNS[pattern_type]

        if patterns:
            # 选择一个模板并填充
            template = random.choice(patterns)

            # 用上下文填充模板
            try:
                variation = template.format(**context)
            except KeyError:
                variation = template

            return variation

        return text

    @staticmethod
    def add_sentence_length_variety(text: str) -> str:
        """
        添加句长多样性

        参数:
            text: 输入文本

        返回:
            变化后的文本
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)

        varied_sentences = []
        for sent in sentences:
            word_count = len(sent.split())

            # 根据当前长度决定是否需要变化
            if word_count < 10:
                # 短句，可能需要扩展
                category = "medium"
            elif word_count > 25:
                # 长句，可能需要简化
                category = "short"
            else:
                # 中等长度，保持
                category = "medium"

            varied_sentences.append(sent)

        return " ".join(varied_sentences)

    @staticmethod
    def add_human_touch(text: str, data: Optional[Dict] = None) -> str:
        """
        添加人类化元素

        参数:
            text: 输入文本
            data: 实验数据

        返回:
            人类化后的文本
        """
        # 添加元评论
        # 添加不确定性陈述
        # 添加具体数据

        if data and "f1" in data:
            # 替换模糊陈述为具体数据
            text = re.sub(
                r'(achieves|demonstrates|shows)\s+(excellent|strong|good)\s+performance',
                r'achieves {f1}% F1'.format(**data),
                text,
                flags=re.IGNORECASE
            )

        return text

    @staticmethod
    def replace_ai_patterns(text: str, replacements: Optional[Dict] = None) -> str:
        """
        替换AI模式

        参数:
            text: 输入文本
            replacements: 替换数据

        返回:
            替换后的文本
        """
        if not replacements:
            replacements = {}

        for ai_pattern, replacements_list in AntiAIWritingTemplates.AI_PATTERN_REPLACEMENTS.items():
            # 选择一个替换
            replacement = random.choice(replacements_list)

            try:
                replacement = replacement.format(**replacements)
            except KeyError:
                pass

            # 简化的模式匹配
            if "critical_role" in ai_pattern:
                text = re.sub(
                    r'plays\s+a\s+(?:critical|crucial|important)\s+role',
                    replacement,
                    text,
                    flags=re.IGNORECASE
                )
            elif "significantly" in ai_pattern:
                text = re.sub(
                    r'significantly\s+(?:improves|outperforms)',
                    replacement,
                    text,
                    flags=re.IGNORECASE
                )

        return text

    @staticmethod
    def enhance_specificity(text: str, data: Dict) -> str:
        """
        增强具体性

        参数:
            text: 输入文本
            data: 具体数据

        返回:
            增强后的文本
        """
        # 替换通用词为具体数据
        if "f1" in data:
            text = re.sub(
                r'\{method\}\s+achieves\s+excellent\s+results',
                'Our method achieves {f1}% F1'.format(**data),
                text,
                flags=re.IGNORECASE
            )

        if "dataset" in data:
            text = re.sub(
                r'on\s+various\s+datasets',
                'on {dataset}'.format(**data),
                text,
                flags=re.IGNORECASE
            )

        return text

    @staticmethod
    def generate_humanized_paragraph(content: str, data: Optional[Dict] = None) -> str:
        """
        生成人类化段落

        参数:
            content: 原始内容
            data: 数据

        返回:
            人类化的段落
        """
        if not data:
            data = {}

        # 1. 变化句子开头
        text = AntiAIWritingTemplates.vary_sentence_opening(content, data)

        # 2. 添加句长多样性
        text = AntiAIWritingTemplates.add_sentence_length_variety(text)

        # 3. 增强具体性
        text = AntiAIWritingTemplates.enhance_specificity(text, data)

        # 4. 替换AI模式
        text = AntiAIWritingTemplates.replace_ai_patterns(text, data)

        return text


# ==================== 便捷函数 ====================

def humanize_text(text: str, data: Optional[Dict] = None) -> str:
    """
    便捷函数：人类化文本

    参数:
        text: 输入文本
        data: 实验数据

    返回:
        人类化后的文本
    """
    return AntiAIWritingTemplates.generate_humanized_paragraph(text, data)


def replace_ai_patterns(text: str, replacements: Optional[Dict] = None) -> str:
    """
    便捷函数：替换AI模式

    参数:
        text: 输入文本
        replacements: 替换数据

    返回:
        替换后的文本
    """
    return AntiAIWritingTemplates.replace_ai_patterns(text, replacements)


if __name__ == "__main__":
    # 示例使用
    ai_text = "Our method achieves excellent performance on various datasets. Change detection plays a critical role in many applications. Our novel approach significantly improves results."

    print("=== Original AI-Text ===")
    print(ai_text)

    print("\n=== Humanized Text ===")
    humanized = humanize_text(ai_text, {"f1": 91.5, "dataset": "LEVIR-CD"})
    print(humanized)

    print("\n=== AI Pattern Replacement ===")
    replaced = replace_ai_patterns(ai_text, {"f1": 91.5})
    print(replaced)
