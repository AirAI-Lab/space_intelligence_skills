# -*- coding: utf-8 -*-
"""
AI Writing Pattern Deep Detector
AI写作模式深度检测器

基于2025年最新研究，实现15+种AI写作模式检测，覆盖5个维度：
1. Sentence Structure Patterns - 句式结构模式
2. Lexical Patterns - 词汇模式
3. Syntactic Patterns - 语法模式
4. Semantic Patterns - 语义模式
5. Stylistic Patterns - 风格模式

特点：
- ✅ 15+ AI模式检测规则
- ✅ 多维度分析（句式、词汇、语法、语义、风格）
- ✅ 严重程度分类
- ✅ 替换建议生成
- ✅ 人类化改写建议

作者: OpenClaw Writing System
日期: 2026-03-24
参考: 2025年AI检测研究、GPTZero、Grammarly AI检测指南
"""

import re
import string
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import Counter
import statistics


# ==================== 数据结构 ====================

@dataclass
class PatternMatch:
    """模式匹配结果"""
    pattern_name: str
    category: str
    severity: str  # critical, high, medium, low
    found_text: str
    position: Tuple[int, int]  # (start, end)
    suggestion: str
    confidence: float = 1.0


@dataclass
class SentenceAnalysis:
    """句子分析结果"""
    total_sentences: int
    avg_length: float
    length_std: float
    length_variance: float
    opening_words: Counter
    opening_diversity: float  # 0-1, 1 is most diverse
    sentence_types: Dict[str, int]  # simple, compound, complex, compound-complex


@dataclass
class LexicalAnalysis:
    """词汇分析结果"""
    total_words: int
    unique_words: int
    ttr: float  # Type-Token Ratio
    overused_adjectives: List[PatternMatch]
    vague_phrases: List[PatternMatch]
    generic_openings: List[PatternMatch]


@dataclass
class SyntacticAnalysis:
    """语法分析结果"""
    passive_voice_count: int
    passive_voice_ratio: float
    noun_strings: List[PatternMatch]
    weak_verbs: List[PatternMatch]
    complex_sentences_ratio: float


@dataclass
class SemanticAnalysis:
    """语义分析结果"""
    vague_statements: List[PatternMatch]
    lacking_specificity: List[PatternMatch]
    missing_quantifiers: List[PatternMatch]
    generic_claims: List[PatternMatch]


@dataclass
class StylisticAnalysis:
    """风格分析结果"""
    formulaic_transitions: List[PatternMatch]
    predictable_conclusions: List[PatternMatch]
    template_phrasing: List[PatternMatch]
    mechanical_citations: List[PatternMatch]


@dataclass
class PatternDetectionResult:
    """综合检测结果"""
    overall_score: float  # 0-100, higher is better
    category_scores: Dict[str, float]
    all_patterns: List[PatternMatch]
    sentence_analysis: SentenceAnalysis
    lexical_analysis: LexicalAnalysis
    syntactic_analysis: SyntacticAnalysis
    semantic_analysis: SemanticAnalysis
    stylistic_analysis: StylisticAnalysis

    def get_patterns_by_severity(self, severity: str) -> List[PatternMatch]:
        """按严重程度获取模式"""
        return [p for p in self.all_patterns if p.severity == severity]

    def get_improvement_priority(self) -> List[PatternMatch]:
        """获取改进优先级列表"""
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(self.all_patterns, key=lambda p: (severity_order[p.severity], -p.confidence))


# ==================== AI模式检测器 ====================

class AIPatternDetector:
    """
    AI写作模式深度检测器

    检测15+种AI写作模式：
    1. 重复句式开头
    2. 统一句子长度
    3. 可预测过渡词
    4. 公式化段落结构
    5. 过度形容词
    6. 通用开场短语
    7. 模糊比较词
    8. 冗余修饰语
    9. 被动语态滥用
    10. 名词串过多
    11. 弱动词使用
    12. 缺乏具体性
    13. 缺少量化数据
    14. 缺少具体例子
    15. 公式化结论
    """

    # ==================== 句式结构模式 ====================

    SENTENCE_PATTERNS = {
        "repetitive_openings": {
            "pattern": r"^(In addition|Furthermore|Moreover|Additionally|Therefore|However|Thus|Hence|Consequently)[,\s]",
            "severity": "medium",
            "suggestion": "Vary sentence openings. Try: quantitative leads, technical context, or direct statements."
        },
        "uniform_length_check": {
            "description": "Sentences have similar lengths (low std)",
            "severity": "medium",
            "threshold": 6.0,  # std threshold in words
            "suggestion": "Mix short (8-12), medium (15-25), and long (30-40) word sentences."
        },
        "predictable_transitions": {
            "pattern": r"\b(In conclusion?(?: to conclude)?|To summarize|Overall|In summary?(?: to sum up)?)\b,?\s+\w+",
            "severity": "high",
            "suggestion": "Replace with more substantive conclusions that recap key findings."
        }
    }

    # ==================== 词汇模式 ====================

    LEXICAL_PATTERNS = {
        "overused_adjectives": {
            "excellent": r"\b(excellent|outstanding|remarkable|impressive|exceptional)\s+(performance|results?|accuracy|outcome)",
            "novel": r"\b(novel|innovative|groundbreaking|revolutionary|state-of-the-art)\s+(approach|method|framework|architecture)",
            "effective": r"\b(highly\s+)?effective|efficient\s+(way|manner|method|approach)",
            "severity": "high",
            "suggestion": "Replace with specific metrics: 'achieves 91.5% F1', 'uses 11.8M parameters'"
        },
        "generic_openings": {
            "pattern": r"\b(plays?\s+a?\s+(?:critical|crucial|important|vital|significant|essential)\s+role|(?:is|remains|becomes)\s+a?\s+(?:critical|crucial|important)\s+(?:task|challenge|problem))",
            "severity": "high",
            "suggestion": "Replace with specific applications and quantitative impact."
        },
        "vague_comparatives": {
            "pattern": r"\b(significantly|dramatically|substantially|considerably|notably|markedly)\s+(improves?|outperforms?|surpasses?|exceeds?|enhances?|betters?)",
            "severity": "critical",
            "suggestion": "Replace with quantitative comparison: 'improves F1 by 1.2 percentage points'"
        },
        "redundant_modifiers": {
            "pattern": r"\b(very|really|quite|rather|extremely|highly|particularly|especially)\s+(good|bad|important|significant|interesting|useful|effective|clear|obvious|apparent)",
            "severity": "medium",
            "suggestion": "Remove redundant modifiers or replace with precise terms."
        }
    }

    # ==================== 语法模式 ====================

    SYNTACTIC_PATTERNS = {
        "passive_overuse": {
            "pattern": r"\b(was|were|is|are|been|being)\s+\w+ed\b",
            "threshold": 0.3,  # max 30% passive
            "severity": "medium",
            "suggestion": "Use active voice: 'We propose' instead of 'is proposed'"
        },
        "noun_strings": {
            "pattern": r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){3,}\b",  # 4+ consecutive capitalized words
            "severity": "medium",
            "suggestion": "Break up noun strings with prepositions or restructure."
        },
        "weak_verbs": {
            "pattern": r"\b(is|are|was|were|has|have|had)\s+(a|an|the)?\s*(?:lot\s+of|few|many|much|some|several|various|different|numerous|multiple)\b",
            "severity": "low",
            "suggestion": "Replace with specific quantifiers: '3 methods', '5 datasets', '12 experiments'"
        }
    }

    # ==================== 语义模式 ====================

    SEMANTIC_PATTERNS = {
        "lacking_specificity": {
            "pattern": r"\b(?:achieves|demonstrates?|shows?|exhibits?)\s+(?:excellent|outstanding|impressive|superior|exceptional)\s+(?:performance|results?|accuracy)",
            "severity": "critical",
            "suggestion": "Replace with specific metrics: 'achieves 91.5% F1 on LEVIR-CD'"
        },
        "missing_quantifiers": {
            "pattern": r"\b(?:many|multiple|various|numerous|several|different)\s+(?:methods?|approaches?|techniques?|strategies?|experiments?|studies?)",
            "severity": "high",
            "suggestion": "Specify exact numbers: '3 methods', '4 experiments', '5 strategies'"
        },
        "vague_statements": {
            "pattern": r"\b(?:is\s+(?:very\s+)?important|plays?\s+a?\s+(?:very\s+)?important\s+role|is\s+(?:very\s+)?useful)\b",
            "severity": "high",
            "suggestion": "Replace with specific applications and quantitative impact."
        },
        "generic_claims": {
            "pattern": r"\b(?:state-of-the-art|SOTA|cutting-edge|leading|advanced)\s+(?:performance|results?|methods?|techniques?)(?:\s+without\s+(?:specific|exact|precise)\s+(?:numbers?|metrics?|data))?",
            "severity": "high",
            "suggestion": "Always provide specific metrics when claiming SOTA performance."
        }
    }

    # ==================== 风格模式 ====================

    STYLISTIC_PATTERNS = {
        "formulaic_transitions": {
            "first_second_third": r"(?:First(?:ly)?,?\s*[^.]+\.?)?(?:\s*Second(?:ly)?,?\s*[^.]+\.?)?(?:\s*Third(?:ly)?,?\s*[^.]+\.?)?(?:\s*Finally,?\s*[^.]+\.?)?",
            "on_the_other_hand": r"\bon\s+the\s+other\s+hand\b",
            "severity": "medium",
            "suggestion": "Use varied transitions and integrate them naturally into sentences."
        },
        "predictable_conclusions": {
            "pattern": r"\b(?:In\s+conclusion|To\s+conclude|To\s+summarize|In\s+summary)(?:,?\s+we\s+have\s+(?:presented|demonstrated|shown))",
            "severity": "medium",
            "suggestion": "Write conclusions that recap key findings and their implications."
        },
        "template_phrasing": {
            "extensive_experiments": r"\b(?:Extensive|Comprehensive|Thorough)\s+(?:experiments?|studies?|analyses?)\s+(?:show|demonstrate|indicate|reveal|suggest)\b",
            "promising_results": r"\b(?:promising|encouraging|satisfying)\s+results?\b",
            "severity": "high",
            "suggestion": "Replace with specific experimental details and quantitative findings."
        },
        "mechanical_citations": {
            "pattern": r"\[[\d,]+\](?:\s*\[[\d,]+\]){2,}",  # Multiple citations in sequence
            "severity": "low",
            "suggestion": "Integrate citations more naturally with context."
        }
    }

    def __init__(self, strict_mode: bool = False):
        """
        初始化检测器

        参数:
            strict_mode: 严格模式，降低检测阈值
        """
        self.strict_mode = strict_mode
        self.all_patterns = {
            "sentence": self.SENTENCE_PATTERNS,
            "lexical": self.LEXICAL_PATTERNS,
            "syntactic": self.SYNTACTIC_PATTERNS,
            "semantic": self.SEMANTIC_PATTERNS,
            "stylistic": self.STYLISTIC_PATTERNS
        }

    # ==================== 主检测方法 ====================

    def detect_patterns(self, text: str) -> PatternDetectionResult:
        """
        执行完整的AI模式检测

        参数:
            text: 要检测的文本

        返回:
            PatternDetectionResult: 综合检测结果
        """
        all_matches = []

        # 1. 句式结构分析
        sentence_analysis = self.analyze_sentence_structure(text)
        all_matches.extend(self._check_sentence_patterns(text, sentence_analysis))

        # 2. 词汇分析
        lexical_analysis = self.detect_lexical_patterns(text)
        all_matches.extend(lexical_analysis.overused_adjectives)
        all_matches.extend(lexical_analysis.vague_phrases)
        all_matches.extend(lexical_analysis.generic_openings)

        # 3. 语法分析
        syntactic_analysis = self.check_syntactic_variety(text)
        all_matches.extend(syntactic_analysis.noun_strings)
        all_matches.extend(syntactic_analysis.weak_verbs)

        # 4. 语义分析
        semantic_analysis = self.check_semantic_patterns(text)
        all_matches.extend(semantic_analysis.vague_statements)
        all_matches.extend(semantic_analysis.lacking_specificity)
        all_matches.extend(semantic_analysis.missing_quantifiers)
        all_matches.extend(semantic_analysis.generic_claims)

        # 5. 风格分析
        stylistic_analysis = self.check_stylistic_patterns(text)
        all_matches.extend(stylistic_analysis.formulaic_transitions)
        all_matches.extend(stylistic_analysis.predictable_conclusions)
        all_matches.extend(stylistic_analysis.template_phrasing)
        all_matches.extend(stylistic_analysis.mechanical_citations)

        # 计算分数
        category_scores = self._calculate_category_scores(all_matches)
        overall_score = self._calculate_overall_score(category_scores)

        return PatternDetectionResult(
            overall_score=overall_score,
            category_scores=category_scores,
            all_patterns=all_matches,
            sentence_analysis=sentence_analysis,
            lexical_analysis=lexical_analysis,
            syntactic_analysis=syntactic_analysis,
            semantic_analysis=semantic_analysis,
            stylistic_analysis=stylistic_analysis
        )

    # ==================== 句式结构分析 ====================

    def analyze_sentence_structure(self, text: str) -> SentenceAnalysis:
        """
        分析句子结构

        参数:
            text: 要分析的文本

        返回:
            SentenceAnalysis: 句子分析结果
        """
        # 分割句子
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return SentenceAnalysis(0, 0, 0, 0, Counter(), 0.0, {})

        # 计算句子长度
        lengths = [len(s.split()) for s in sentences]

        # 分析开头词
        opening_words = []
        for sent in sentences:
            words = sent.split()
            if words:
                # 获取第一个有意义的词（跳过标点）
                first_word = words[0].strip(string.punctuation).lower()
                if len(first_word) > 2:  # 忽略太短的词
                    opening_words.append(first_word)

        opening_counter = Counter(opening_words)
        opening_diversity = len(opening_counter) / len(opening_words) if opening_words else 0

        # 分析句子类型
        sentence_types = self._classify_sentence_types(sentences)

        return SentenceAnalysis(
            total_sentences=len(sentences),
            avg_length=statistics.mean(lengths) if lengths else 0,
            length_std=statistics.stdev(lengths) if len(lengths) > 1 else 0,
            length_variance=statistics.variance(lengths) if len(lengths) > 1 else 0,
            opening_words=opening_counter,
            opening_diversity=opening_diversity,
            sentence_types=sentence_types
        )

    def _classify_sentence_types(self, sentences: List[str]) -> Dict[str, int]:
        """
        分类句子类型
        """
        types = {"simple": 0, "compound": 0, "complex": 0, "compound-complex": 0}

        for sent in sentences:
            # 简单的启发式分类
            clause_count = sent.count(',') + sent.count(' and ') + sent.count(' but ') + sent.count(' or ') + 1

            # 检测从句
            has_subordinate = any(word in sent.lower() for word in
                                ['although', 'because', 'since', 'while', 'if', 'when', 'that', 'which', 'who'])

            if clause_count == 1:
                types["simple"] += 1
            elif clause_count == 2:
                if has_subordinate:
                    types["complex"] += 1
                else:
                    types["compound"] += 1
            else:
                if has_subordinate:
                    types["compound-complex"] += 1
                else:
                    types["compound"] += 1

        return types

    def _check_sentence_patterns(self, text: str, analysis: SentenceAnalysis) -> List[PatternMatch]:
        """检查句式结构模式"""
        matches = []

        # 检查统一句长
        if analysis.length_std < self.SENTENCE_PATTERNS["uniform_length_check"]["threshold"]:
            matches.append(PatternMatch(
                pattern_name="uniform_length_check",
                category="sentence_structure",
                severity=self.SENTENCE_PATTERNS["uniform_length_check"]["severity"],
                found_text=f"Length std: {analysis.length_std:.2f}",
                position=(0, 0),
                suggestion=self.SENTENCE_PATTERNS["uniform_length_check"]["suggestion"]
            ))

        # 检查开头多样性
        if analysis.opening_diversity < 0.5:
            matches.append(PatternMatch(
                pattern_name="repetitive_openings",
                category="sentence_structure",
                severity="medium",
                found_text=f"Opening diversity: {analysis.opening_diversity:.2f}",
                position=(0, 0),
                suggestion="Increase sentence opening diversity. Use varied starting words and structures."
            ))

        # 检查可预测过渡词
        for match in re.finditer(self.SENTENCE_PATTERNS["predictable_transitions"]["pattern"], text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="predictable_transitions",
                category="sentence_structure",
                severity=self.SENTENCE_PATTERNS["predictable_transitions"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.SENTENCE_PATTERNS["predictable_transitions"]["suggestion"]
            ))

        return matches

    # ==================== 词汇模式检测 ====================

    def detect_lexical_patterns(self, text: str) -> LexicalAnalysis:
        """
        检测词汇模式
        """
        all_matches = []

        # 计算TTR (Type-Token Ratio)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        unique_words = set(words)
        ttr = len(unique_words) / len(words) if words else 0

        # 检测过度形容词
        overused_adj = self._detect_overused_adjectives(text)
        all_matches.extend(overused_adj)

        # 检测通用开场
        generic_openings = self._detect_generic_openings(text)
        all_matches.extend(generic_openings)

        # 检测模糊比较
        vague_comparatives = self._detect_vague_comparatives(text)
        all_matches.extend(vague_comparatives)

        # 检测冗余修饰语
        redundant_mods = self._detect_redundant_modifiers(text)
        all_matches.extend(redundant_mods)

        return LexicalAnalysis(
            total_words=len(words),
            unique_words=len(unique_words),
            ttr=ttr,
            overused_adjectives=overused_adj,
            vague_phrases=vague_comparatives,
            generic_openings=generic_openings
        )

    def _detect_overused_adjectives(self, text: str) -> List[PatternMatch]:
        """检测过度使用的形容词"""
        matches = []

        patterns = self.LEXICAL_PATTERNS["overused_adjectives"]

        for adj_type, pattern in patterns.items():
            if isinstance(pattern, str):
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    matches.append(PatternMatch(
                        pattern_name=f"overused_adjective_{adj_type}",
                        category="lexical",
                        severity=patterns["severity"],
                        found_text=match.group(),
                        position=match.span(),
                        suggestion=patterns["suggestion"]
                    ))

        return matches

    def _detect_generic_openings(self, text: str) -> List[PatternMatch]:
        """检测通用开场短语"""
        matches = []

        pattern = self.LEXICAL_PATTERNS["generic_openings"]["pattern"]
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="generic_opening",
                category="lexical",
                severity=self.LEXICAL_PATTERNS["generic_openings"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.LEXICAL_PATTERNS["generic_openings"]["suggestion"]
            ))

        return matches

    def _detect_vague_comparatives(self, text: str) -> List[PatternMatch]:
        """检测模糊比较词"""
        matches = []

        pattern = self.LEXICAL_PATTERNS["vague_comparatives"]["pattern"]
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="vague_comparative",
                category="lexical",
                severity=self.LEXICAL_PATTERNS["vague_comparatives"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.LEXICAL_PATTERNS["vague_comparatives"]["suggestion"]
            ))

        return matches

    def _detect_redundant_modifiers(self, text: str) -> List[PatternMatch]:
        """检测冗余修饰语"""
        matches = []

        pattern = self.LEXICAL_PATTERNS["redundant_modifiers"]["pattern"]
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="redundant_modifier",
                category="lexical",
                severity=self.LEXICAL_PATTERNS["redundant_modifiers"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.LEXICAL_PATTERNS["redundant_modifiers"]["suggestion"]
            ))

        return matches

    # ==================== 语法模式检测 ====================

    def check_syntactic_variety(self, text: str) -> SyntacticAnalysis:
        """
        检查语法多样性
        """
        # 检测被动语态
        passive_matches = list(re.finditer(self.SYNTACTIC_PATTERNS["passive_overuse"]["pattern"], text, re.IGNORECASE))
        passive_count = len(passive_matches)

        # 估算句子数
        sentences = len(re.split(r'[.!?]+', text))
        passive_ratio = passive_count / sentences if sentences > 0 else 0

        # 检测名词串
        noun_strings = self._detect_noun_strings(text)

        # 检测弱动词
        weak_verbs = self._detect_weak_verbs(text)

        return SyntacticAnalysis(
            passive_voice_count=passive_count,
            passive_voice_ratio=passive_ratio,
            noun_strings=noun_strings,
            weak_verbs=weak_verbs,
            complex_sentences_ratio=0.5  # 简化，实际应计算
        )

    def _detect_noun_strings(self, text: str) -> List[PatternMatch]:
        """检测名词串"""
        matches = []

        pattern = self.SYNTACTIC_PATTERNS["noun_strings"]["pattern"]
        for match in re.finditer(pattern, text):
            matches.append(PatternMatch(
                pattern_name="noun_string",
                category="syntactic",
                severity=self.SYNTACTIC_PATTERNS["noun_strings"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.SYNTACTIC_PATTERNS["noun_strings"]["suggestion"]
            ))

        return matches

    def _detect_weak_verbs(self, text: str) -> List[PatternMatch]:
        """检测弱动词"""
        matches = []

        pattern = self.SYNTACTIC_PATTERNS["weak_verbs"]["pattern"]
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="weak_verb",
                category="syntactic",
                severity=self.SYNTACTIC_PATTERNS["weak_verbs"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.SYNTACTIC_PATTERNS["weak_verbs"]["suggestion"]
            ))

        return matches

    # ==================== 语义模式检测 ====================

    def check_semantic_patterns(self, text: str) -> SemanticAnalysis:
        """
        检查语义模式
        """
        vague_statements = self._detect_vague_statements(text)
        lacking_specificity = self._detect_lacking_specificity(text)
        missing_quantifiers = self._detect_missing_quantifiers(text)
        generic_claims = self._detect_generic_claims(text)

        return SemanticAnalysis(
            vague_statements=vague_statements,
            lacking_specificity=lacking_specificity,
            missing_quantifiers=missing_quantifiers,
            generic_claims=generic_claims
        )

    def _detect_vague_statements(self, text: str) -> List[PatternMatch]:
        """检测模糊陈述"""
        matches = []

        pattern = self.SEMANTIC_PATTERNS["vague_statements"]["pattern"]
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="vague_statement",
                category="semantic",
                severity=self.SEMANTIC_PATTERNS["vague_statements"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.SEMANTIC_PATTERNS["vague_statements"]["suggestion"]
            ))

        return matches

    def _detect_lacking_specificity(self, text: str) -> List[PatternMatch]:
        """检测缺乏具体性"""
        matches = []

        pattern = self.SEMANTIC_PATTERNS["lacking_specificity"]["pattern"]
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="lacking_specificity",
                category="semantic",
                severity=self.SEMANTIC_PATTERNS["lacking_specificity"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.SEMANTIC_PATTERNS["lacking_specificity"]["suggestion"]
            ))

        return matches

    def _detect_missing_quantifiers(self, text: str) -> List[PatternMatch]:
        """检测缺少量词"""
        matches = []

        pattern = self.SEMANTIC_PATTERNS["missing_quantifiers"]["pattern"]
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="missing_quantifier",
                category="semantic",
                severity=self.SEMANTIC_PATTERNS["missing_quantifiers"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.SEMANTIC_PATTERNS["missing_quantifiers"]["suggestion"]
            ))

        return matches

    def _detect_generic_claims(self, text: str) -> List[PatternMatch]:
        """检测通用声明"""
        matches = []

        pattern = self.SEMANTIC_PATTERNS["generic_claims"]["pattern"]
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="generic_claim",
                category="semantic",
                severity=self.SEMANTIC_PATTERNS["generic_claims"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.SEMANTIC_PATTERNS["generic_claims"]["suggestion"]
            ))

        return matches

    # ==================== 风格模式检测 ====================

    def check_stylistic_patterns(self, text: str) -> StylisticAnalysis:
        """
        检查风格模式
        """
        formulaic_transitions = self._detect_formulaic_transitions(text)
        predictable_conclusions = self._detect_predictable_conclusions(text)
        template_phrasing = self._detect_template_phrasing(text)
        mechanical_citations = self._detect_mechanical_citations(text)

        return StylisticAnalysis(
            formulaic_transitions=formulaic_transitions,
            predictable_conclusions=predictable_conclusions,
            template_phrasing=template_phrasing,
            mechanical_citations=mechanical_citations
        )

    def _detect_formulaic_transitions(self, text: str) -> List[PatternMatch]:
        """检测公式化过渡"""
        matches = []

        # 检测First, Second, Third模式
        pattern = self.STYLISTIC_PATTERNS["formulaic_transitions"]["first_second_third"]
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="formulaic_transition",
                category="stylistic",
                severity=self.STYLISTIC_PATTERNS["formulaic_transitions"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.STYLISTIC_PATTERNS["formulaic_transitions"]["suggestion"]
            ))

        return matches

    def _detect_predictable_conclusions(self, text: str) -> List[PatternMatch]:
        """检测可预测结论"""
        matches = []

        pattern = self.STYLISTIC_PATTERNS["predictable_conclusions"]["pattern"]
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="predictable_conclusion",
                category="stylistic",
                severity=self.STYLISTIC_PATTERNS["predictable_conclusions"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.STYLISTIC_PATTERNS["predictable_conclusions"]["suggestion"]
            ))

        return matches

    def _detect_template_phrasing(self, text: str) -> List[PatternMatch]:
        """检测模板短语"""
        matches = []

        # 检测extensive experiments
        pattern1 = self.STYLISTIC_PATTERNS["template_phrasing"]["extensive_experiments"]
        for match in re.finditer(pattern1, text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="template_phrasing_extensive",
                category="stylistic",
                severity=self.STYLISTIC_PATTERNS["template_phrasing"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.STYLISTIC_PATTERNS["template_phrasing"]["suggestion"]
            ))

        # 检测promising results
        pattern2 = self.STYLISTIC_PATTERNS["template_phrasing"]["promising_results"]
        for match in re.finditer(pattern2, text, re.IGNORECASE):
            matches.append(PatternMatch(
                pattern_name="template_phrasing_promising",
                category="stylistic",
                severity=self.STYLISTIC_PATTERNS["template_phrasing"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.STYLISTIC_PATTERNS["template_phrasing"]["suggestion"]
            ))

        return matches

    def _detect_mechanical_citations(self, text: str) -> List[PatternMatch]:
        """检测机械式引用"""
        matches = []

        pattern = self.STYLISTIC_PATTERNS["mechanical_citations"]["pattern"]
        for match in re.finditer(pattern, text):
            matches.append(PatternMatch(
                pattern_name="mechanical_citation",
                category="stylistic",
                severity=self.STYLISTIC_PATTERNS["mechanical_citations"]["severity"],
                found_text=match.group(),
                position=match.span(),
                suggestion=self.STYLISTIC_PATTERNS["mechanical_citations"]["suggestion"]
            ))

        return matches

    # ==================== 分数计算 ====================

    def _calculate_category_scores(self, all_matches: List[PatternMatch]) -> Dict[str, float]:
        """计算各维度分数"""
        category_scores = {
            "sentence_structure": 100.0,
            "lexical": 100.0,
            "syntactic": 100.0,
            "semantic": 100.0,
            "stylistic": 100.0
        }

        # 根据严重程度扣分
        severity_penalty = {"critical": 20, "high": 10, "medium": 5, "low": 2}

        for match in all_matches:
            category = match.category
            penalty = severity_penalty.get(match.severity, 5)
            category_scores[category] = max(0, category_scores[category] - penalty)

        return category_scores

    def _calculate_overall_score(self, category_scores: Dict[str, float]) -> float:
        """计算总体分数"""
        # 加权平均
        weights = {
            "sentence_structure": 0.15,
            "lexical": 0.25,
            "syntactic": 0.15,
            "semantic": 0.25,
            "stylistic": 0.20
        }

        total = sum(category_scores[cat] * weights[cat] for cat in category_scores)
        return round(total, 2)

    # ==================== 人类化建议 ====================

    def generate_humanization_suggestions(self, result: PatternDetectionResult) -> List[str]:
        """
        生成人类化建议

        参数:
            result: 检测结果

        返回:
            建议列表
        """
        suggestions = []

        # 基于分数生成建议
        if result.overall_score < 70:
            suggestions.append("Overall: Paper needs significant humanization. Focus on adding specific data and varying sentence structure.")

        # 句式结构建议
        if result.category_scores["sentence_structure"] < 80:
            suggestions.append("Sentence Structure: Vary sentence openings and lengths. Mix short (8-12 words), medium (15-25 words), and long (30-40 words) sentences.")

        # 词汇建议
        if result.category_scores["lexical"] < 80:
            suggestions.append("Lexical: Replace vague adjectives with specific metrics. Use quantified comparisons instead of 'significantly improves'.")

        # 语义建议
        if result.category_scores["semantic"] < 80:
            suggestions.append("Semantic: Add quantitative data to support all claims. Replace generic statements with specific numbers and citations.")

        # 风格建议
        if result.category_scores["stylistic"] < 80:
            suggestions.append("Style: Avoid template phrases. Write naturally with authorial voice and varied transitions.")

        return suggestions


# ==================== 便捷函数 ====================

def detect_ai_patterns(text: str, strict_mode: bool = False) -> PatternDetectionResult:
    """
    便捷函数：检测AI写作模式

    参数:
        text: 要检测的文本
        strict_mode: 严格模式

    返回:
        PatternDetectionResult: 检测结果
    """
    detector = AIPatternDetector(strict_mode=strict_mode)
    return detector.detect_patterns(text)


if __name__ == "__main__":
    # 示例使用
    sample_text = """
    Change detection plays a critical role in remote sensing applications.
    Our novel method achieves excellent performance on various datasets.
    Significantly, we outperform existing approaches by using multiple techniques.
    In conclusion, we have presented a promising approach for change detection.
    Extensive experiments show that our method works well.
    """

    result = detect_ai_patterns(sample_text)

    print("=== AI Pattern Detection Results ===")
    print(f"Overall Score: {result.overall_score}/100")
    print(f"\nCategory Scores:")
    for category, score in result.category_scores.items():
        print(f"  {category}: {score}/100")

    print(f"\nPatterns Detected: {len(result.all_patterns)}")
    for pattern in result.all_patterns[:10]:  # 只显示前10个
        print(f"  - [{pattern.severity}] {pattern.pattern_name}: '{pattern.found_text[:50]}...'")

    print("\n=== Humanization Suggestions ===")
    suggestions = AIPatternDetector().generate_humanization_suggestions(result)
    for suggestion in suggestions:
        print(f"  - {suggestion}")
