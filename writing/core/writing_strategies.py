# -*- coding: utf-8 -*-
"""
教授级论文写作策略库
Professor-Level Academic Writing Strategies

基于对一区Top论文的深度分析（BIT, ChangeFormer, TinyCD等），
总结教授级写作策略、表述模板和规范。

特点：
- ✅ SOTA论文写作策略
- ✅ 量化对比生成
- ✅ 避免AI写作痕迹
- ✅ 结构化写作模板
- ✅ 一区Top论文规范

作者: OpenClaw Writing System
日期: 2026-03-05
参考论文:
    - BIT (ICCV 2021): 300+ citations
    - ChangeFormer (TGRS 2022): 200+ citations
    - TinyCD (2023): 高影响力
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import re


# ==================== 写作策略类 ====================

@dataclass
class WritingStrategy:
    """写作策略配置"""
    # 基础信息
    method_name: str
    target_journal: str = "IEEE TGRS"
    
    # 写作风格
    style: str = "professor"  # professor, sota, standard
    language: str = "en"  # en, zh
    
    # 质量要求
    require_quantitative: bool = True  # 要求量化对比
    require_citations: bool = True  # 要求引用
    avoid_ai_patterns: bool = True  # 避免AI痕迹
    
    # 强调重点
    emphasize_first_innovation: bool = True  # 强调首次性
    emphasize_efficiency: bool = True  # 强调效率
    
    # 数据精度
    decimal_places: int = 2  # 小数位数


class ProfessorWritingStrategies:
    """教授级写作策略库"""
    
    # ==================== 核心原则 ====================
    
    CORE_PRINCIPLES = {
        "claim_first_evidence_second": {
            "principle": "Claim-First, Evidence-Second",
            "description": "先提出论点，再提供数据和证据支持",
            "example_bad": "Our method achieves excellent results.",
            "example_good": "Our method achieves 90.16% F1 on LEVIR-CD, outperforming BIT by 0.93 percentage points."
        },
        "quantitative_over_qualitative": {
            "principle": "Quantitative Over Qualitative",
            "description": "使用具体数字而非模糊形容词",
            "example_bad": "The model performs significantly better.",
            "example_good": "The model improves F1 from 89.8% to 90.16% (Δ=+0.36%, p<0.01, n=1,024)."
        },
        "precise_terminology": {
            "principle": "Precise Terminology",
            "description": "使用精确的专业术语",
            "example_bad": "We use attention mechanisms to help the model focus.",
            "example_good": "We employ multi-head self-attention (Vaswani et al., 2017) with 8 attention heads to capture long-range dependencies."
        },
        "citation_support": {
            "principle": "Citation Support",
            "description": "关键陈述都要有文献支持",
            "example_bad": "This is very important for urban monitoring.",
            "example_good": "This is critical for urban monitoring (Chen et al., 2021), disaster assessment (Liu et al., 2022)."
        }
    }
    
    # ==================== AI写作痕迹检测 ====================
    
    AI_PATTERNS = {
        "generic_opening": {
            "pattern": r'plays a (critical|crucial|important|vital) role',
            "severity": "high",
            "suggestion": "Replace with specific applications and citations"
        },
        "vague_comparison": {
            "pattern": r'(significantly|dramatically|substantially) (improves|outperforms|surpasses)',
            "severity": "high",
            "suggestion": "Replace with quantitative comparison: 'improves by X%'"
        },
        "lack_specificity": {
            "pattern": r'(novel|new|proposed) method (achieves|demonstrates) (excellent|outstanding|remarkable)',
            "severity": "medium",
            "suggestion": "Replace with specific metrics and values"
        },
        "extensive_experiments": {
            "pattern": r'extensive experiments (show|demonstrate)',
            "severity": "medium",
            "suggestion": "Replace with: 'Ablation studies (Section 4.3) reveal...'"
        },
        "overused_adjectives": {
            "pattern": r'(excellent|outstanding|remarkable|impressive) performance',
            "severity": "high",
            "suggestion": "Replace with specific F1/IoU values"
        }
    }
    
    # ==================== 高影响力表达 ====================
    
    HIGH_IMPACT_EXPRESSIONS = {
        "first_innovation": {
            "templates": [
                "To our knowledge, this is the first work to {action} in {field}.",
                "We are the first to propose {innovation} for {task}.",
                "This is the first systematic study on {topic}.",
                "Unlike previous approaches, our work introduces {innovation}."
            ],
            "usage": "用于强调首次性和创新性"
        },
        "quantitative_comparison": {
            "templates": [
                "Our method achieves {value}% {metric}, outperforming {baseline} by {improvement} percentage points.",
                "Compared to {baseline}, our method improves {metric} from {baseline_value}% to {our_value}%",
                "While using {reduction}% fewer parameters, our method achieves {value}% {metric}.",
                "Our method achieves {value}% {metric} with only {params}M parameters, which is the smallest among existing methods."
            ],
            "usage": "用于量化对比"
        },
        "efficiency_emphasis": {
            "templates": [
                "Despite its high performance, our method uses only {params}M parameters.",
                "Our method achieves competitive performance with {reduction}% fewer parameters.",
                "With only {params}M parameters, our method achieves {value}% {metric}, making it suitable for edge devices.",
                "Our method runs at {fps} FPS, {improvement}% faster than {baseline}."
            ],
            "usage": "用于强调效率"
        },
        "theoretical_basis": {
            "templates": [
                "The key insight is that {insight}.",
                "To address this challenge, we propose {method}.",
                "Based on the observation that {observation}, we introduce {innovation}.",
                "Motivated by {motivation}, we design {method}."
            ],
            "usage": "用于阐述理论基础"
        }
    }
    
    # ==================== 摘要写作策略 ====================
    
    ABSTRACT_STRATEGIES = {
        "bit_style": {
            "structure": [
                "Problem Statement (1 sentence)",
                "Method Introduction (2 sentences)",
                "Specific Innovation (1 sentence)",
                "Results (2 sentences)",
                "Contribution Summary (1 sentence)"
            ],
            "length": "183 words",
            "avg_sentence": "30.5 words",
            "template": """
            <Domain> is a challenging task that requires not only [sub-task 1] but also [sub-task 2].
            We propose <Method Name>, a <Architecture> framework that incorporates <Key Innovation> to [goal].
            <Method Name> consists of <N> key components: [Component 1], [Component 2], and [Component 3].
            Experiments on <Dataset 1> and <Dataset 2> demonstrate that <Method Name> achieves <result>,
            outperforming <Previous Method> by <X%> while using <Y%> fewer parameters.
            To our knowledge, this is the first work to <key innovation> in <Field>.
            """
        },
        "changeformer_style": {
            "structure": [
                "Importance (1 sentence)",
                "Background (1 sentence)",
                "Method Introduction (2 sentences)",
                "Specific Techniques (2 sentences)",
                "Results (1 sentence)",
                "Contribution Summary (1 sentence)"
            ],
            "length": "187 words",
            "avg_sentence": "23.4 words",
            "template": """
            <Domain> plays a crucial role in [application 1], [application 2], and [application 3].
            While deep learning has achieved significant progress, most existing methods rely on <Method>, which have <limitation>.
            We present <Method Name>, a <Architecture> approach that <benefit>.
            <Method Name> consists of <N> key components: [Component 1] and [Component 2].
            The encoder uses <technique 1> to <goal 1>, while <Component 2> employs <technique 2> to <goal 2>.
            Experiments on <Dataset 1>, <Dataset 2>, and <Dataset 3> demonstrate that <Method Name> achieves <result>,
            outperforming <Baseline> by <X%> while using only <Y>M parameters.
            To our knowledge, this is the first work to <key innovation> in <Field>.
            """
        },
        "tinycd_style": {
            "structure": [
                "Context Challenge (1 sentence)",
                "Method Introduction (1 sentence)",
                "Results (1 sentence)",
                "Technical Details (1 sentence)",
                "Comparison (1 sentence)",
                "Contribution Summary (1 sentence)"
            ],
            "length": "126 words",
            "avg_sentence": "21.0 words",
            "template": """
            <Context> has limited <resource>, making it challenging to deploy <complex task>.
            We propose <Method Name>, an extremely lightweight <Architecture> with <params> parameters.
            Despite its small size, <Method> achieves <result> on <dataset>, making it suitable for <scenario>.
            Our approach uses <technique> to balance efficiency and performance.
            Compared to state-of-the-art <Baseline>, <Method> uses <X%> fewer <resource> while maintaining competitive performance.
            To our knowledge, this is the first work to achieve high performance with <X>M parameters for <Task>.
            """
        }
    }
    
    # ==================== 引言写作策略 ====================
    
    INTRODUCTION_STRATEGIES = {
        "standard_structure": {
            "sections": [
                {
                    "name": "Background and Motivation",
                    "length": "1-2 paragraphs",
                    "content": "Define the task and its applications (3+ examples)"
                },
                {
                    "name": "CNN-based Methods",
                    "length": "1 paragraph",
                    "content": "Review CNN methods with strengths and limitations"
                },
                {
                    "name": "Limitations Analysis",
                    "length": "1 paragraph",
                    "content": "List 3 specific challenges with examples"
                },
                {
                    "name": "Transformer Opportunity",
                    "length": "1 paragraph",
                    "content": "Introduce Transformer and its potential"
                },
                {
                    "name": "Our Approach",
                    "length": "1 paragraph",
                    "content": "Present method with 3 key components"
                },
                {
                    "name": "Contributions",
                    "length": "1 paragraph (numbered list)",
                    "content": "List 3-4 contributions with quantitative metrics"
                },
                {
                    "name": "Paper Organization",
                    "length": "1 paragraph",
                    "content": "Outline the paper structure"
                }
            ]
        },
        "background_template": """
        <Domain> is a critical task for [application 1], [application 2], and [application 3].
        This task involves [task definition] and is essential for [importance].
        Recent advances in <Technology> have revolutionized the field.
        """,
        
        "limitations_template": """
        Despite the success of <Existing Method>, they struggle with three key challenges:
        1. <Challenge 1> - <Specific Reason>
        2. <Challenge 2> - <Specific Reason>
        3. <Challenge 3> - <Specific Reason>
        
        For example, [Method X] achieves [result] but fails to capture [specific issue].
        """,
        
        "our_approach_template": """
        To address these challenges, we present <Method Name>, a novel framework that...
        Our framework comprises <N> key components:
        1. [Component 1]
        2. [Component 2]
        3. [Component 3]
        """,
        
        "contributions_template": """
        The main contributions of this work are:
        1. **<Contribution 1>**: We propose [technique], which improves <metric> by <X%>.
        2. **<Contribution 2>**: [Detailed description]
        3. **<Contribution 3>**: [Detailed description]
        
        To our knowledge, this is the first work to <key innovation> in <Field>.
        """
    }
    
    # ==================== 相关工作写作策略 ====================
    
    RELATED_WORK_STRATEGIES = {
        "classification": [
            "CNN-based Methods (2018-2021)",
            "Transformer-based Methods (2021-2022)",
            "Hybrid Methods (2022-2023)",
            "Weakly-Supervised Methods (if applicable)"
        ],
        
        "evaluation_format": """
        [Method Name] introduced [technique] to [goal], achieving [result].
        While this approach improves over [Previous Method], it still struggles with [limitation].
        This approach is suitable for [scenario] but fails for [scenario].
        """,
        
        "introduce_own_template": """
        However, existing methods have [limitation 1] and [limitation 2].
        To address this, we propose <Our Method> which introduces [key innovation].
        Our work differs from [Previous Method] by [specific technique] which addresses [specific challenge].
        """
    }
    
    # ==================== 方法论写作策略 ====================
    
    METHODOLOGY_STRATEGIES = {
        "structure": [
            {
                "name": "Problem Formulation",
                "content": "Formal problem definition with equations"
            },
            {
                "name": "Overall Architecture",
                "content": "Figure 1 + component description"
            },
            {
                "name": "Component 1",
                "content": "Detailed description + formula + motivation"
            },
            {
                "name": "Component 2",
                "content": "Detailed description + formula + motivation"
            },
            {
                "name": "Component 3",
                "content": "Detailed description + formula + motivation"
            }
        ],
        
        "module_introduction_template": """
        We propose [Module Name] to address <challenge>.
        [Module Name] consists of [two/three] sub-modules:
        1. [Sub-module 1], which is responsible for [task 1]
        2. [Sub-module 2], which handles [task 2]
        
        The key insight is that [theoretical reason].
        By incorporating [mechanism], we enable the model to [benefit].
        """,
        
        "formula_template": """
        [Module Name] is formulated as:
        
        <Formula>
        
        where [variables], and d is the dimensionality of the feature vectors.
        This formulation enables the model to [effect].
        """
    }
    
    # ==================== 实验写作策略 ====================
    
    EXPERIMENT_STRATEGIES = {
        "structure": [
            {
                "name": "Datasets and Metrics",
                "content": "Dataset statistics + metric definitions"
            },
            {
                "name": "Implementation Details",
                "content": "Hardware, software, hyperparameters"
            },
            {
                "name": "Main Results",
                "content": "SOTA comparison table + analysis"
            },
            {
                "name": "Ablation Studies",
                "content": "Component-wise analysis"
            },
            {
                "name": "Qualitative Analysis",
                "content": "Visual comparisons"
            },
            {
                "name": "Failure Cases",
                "content": "Limitation analysis"
            }
        ],
        
        "results_description_template": """
        Our method achieves <value>% <metric> on <dataset>, outperforming <baseline> by <X%>.
        
        Specifically:
        - Precision improves by <X%> to <value>
        - Recall increases by <X%> to <value>
        - IoU reaches <value>
        
        This demonstrates the effectiveness of [key component].
        """,
        
        "ablation_template": """
        To understand the contribution of each component, we conduct ablation studies.
        Table <N> shows that removing [Component] reduces <metric> by <X%>, confirming its importance.
        
        Specifically:
        - Full Model: <value>% <metric>
        - - [Component 1]: <value>% <metric> (Δ=<X%)
        - - [Component 2]: <value>% <metric> (Δ=<X%)
        - - Both: <value>% <metric> (Δ=<X%)
        """
    }
    
    # ==================== 数据呈现策略 ====================
    
    DATA_PRESENTATION_STRATEGIES = {
        "table_design": {
            "required_columns": [
                "Method Name",
                "Parameters (M)",
                "F1 (%)",
                "IoU (%)",
                "Precision (%)",
                "Recall (%)"
            ],
            "optional_columns": [
                "Inference Time (FPS)",
                "Training Time (hours)"
            ],
            "formatting_rules": [
                "Best results in bold",
                "Parameter count included",
                "Two decimal places for metrics",
                "Consistent precision"
            ]
        },
        
        "precision_standards": {
            "f1": "Two decimal places (e.g., 90.16%)",
            "iou": "Two decimal places (e.g., 82.08%)",
            "improvement": "Percentage points (e.g., +0.93% or +0.93 percentage points)",
            "params": "One decimal place (e.g., 11.8M)"
        },
        
        "figure_captions": {
            "architecture": """
            Figure 1: The overall architecture of <Method Name>.
            The framework consists of <N> main components: (A) [Component 1], (B) [Component 2], and (C) [Component 3].
            """,
            
            "results": """
            Figure 3: Qualitative comparison of change detection results.
            The first row shows the input bi-temporal images, the second row displays the ground truth,
            and the remaining rows present the predictions of different methods.
            """
        }
    }
    
    # ==================== 语言风格策略 ====================
    
    LANGUAGE_STYLE_STRATEGIES = {
        "transitions": {
            "strong_contrast": [
                "However,",
                "In contrast,",
                "Conversely,",
                "On the other hand,"
            ],
            "enhancement": [
                "Furthermore,",
                "Moreover,",
                "Additionally,",
                "In addition,"
            ],
            "cause_effect": [
                "Therefore,",
                "Consequently,",
                "As a result,",
                "Thus,"
            ],
            "purpose": [
                "To address this,",
                "To overcome this limitation,",
                "To achieve this goal,",
                "For this purpose,"
            ]
        },
        
        "self_reference": {
            "method_introduction": [
                "We present <Method Name>",
                "Our proposed <Method Name>",
                "The <Method Name> framework"
            ],
            "result_description": [
                "Our method achieves",
                "The proposed framework achieves",
                "Our approach demonstrates"
            ],
            "avoid": [
                "I propose",  # 单数
                "This paper"  # 过于普通
            ]
        },
        
        "absolute_terms_avoidance": {
            "avoid": [
                "always",
                "never",
                "perfectly",
                "completely",
                "obviously",
                "certainly"
            ],
            "use": [
                "often",
                "rarely",
                "significantly",
                "substantially",
                "typically"
            ]
        }
    }
    
    # ==================== 辅助方法 ====================
    
    def check_ai_patterns(self, text: str) -> Dict[str, Any]:
        """
        检测AI写作痕迹
        
        返回:
            {
                'has_ai_patterns': bool,
                'issues': List[Dict],
                'score': int  # 0-100, higher is better
            }
        """
        issues = []
        score = 100
        
        for pattern_name, pattern_info in self.AI_PATTERNS.items():
            pattern = pattern_info['pattern']
            severity = pattern_info['severity']
            suggestion = pattern_info['suggestion']
            
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            if matches:
                for match in matches:
                    issues.append({
                        'type': pattern_name,
                        'severity': severity,
                        'found': match,
                        'suggestion': suggestion
                    })
                    
                    # 根据严重程度扣分
                    if severity == 'high':
                        score -= 15
                    elif severity == 'medium':
                        score -= 10
        
        score = max(0, min(score, 100))
        
        return {
            'has_ai_patterns': len(issues) > 0,
            'issues': issues,
            'score': score
        }
    
    def generate_quantitative_comparison(self,
                                   our_value: float,
                                   baseline_value: float,
                                   metric: str,
                                   baseline_name: str,
                                   params_ours: Optional[float] = None,
                                   params_baseline: Optional[float] = None) -> str:
        """
        生成量化对比语句
        
        参数:
            our_value: 我们的指标值
            baseline_value: 基线指标值
            metric: 指标名称（F1, IoU等）
            baseline_name: 基线方法名称
            params_ours: 我们的参数量（可选）
            params_baseline: 基线参数量（可选）
        
        返回:
            对比语句字符串
        """
        improvement = our_value - baseline_value
        
        # 基础对比
        if improvement > 0:
            result = f"outperforming {baseline_name} by {improvement:.2f} percentage points"
        elif improvement < 0:
            result = f"with competitive performance to {baseline_name} (difference: {abs(improvement):.2f} percentage points)"
        else:
            result = f"with comparable performance to {baseline_name}"
        
        # 添加参数对比
        if params_ours and params_baseline:
            param_reduction = (params_baseline - params_ours) / params_baseline * 100
            if param_reduction > 0:
                result += f" while using {param_reduction:.0f}% fewer parameters"
            else:
                result += f" with {abs(param_reduction):.0f}% more parameters"
        
        return result
    
    def generate_first_innovation_statement(self,
                                      action: str,
                                      field: str = "semantic change detection") -> str:
        """
        生成首次创新陈述
        
        示例:
            "To our knowledge, this is the first work to introduce self-attention 
            mechanisms into semantic change detection."
        """
        templates = self.HIGH_IMPACT_EXPRESSIONS['first_innovation']['templates']
        template = templates[0]  # 使用最常用的模板
        return template.format(action=action, field=field)
    
    def format_metric_value(self,
                        value: float,
                        metric: str,
                        decimal_places: int = 2) -> str:
        """
        格式化指标值
        
        示例:
            format_metric_value(90.16, "F1") -> "90.16% F1"
        """
        return f"{value:.{decimal_places}f}% {metric}"
    
    def generate_contributions_list(self,
                                contributions: List[Dict[str, str]],
                                style: str = "numbered") -> str:
        """
        生成贡献列表
        
        参数:
            contributions: 贡献列表，每个元素包含 'title' 和 'details'
            style: 风格 ('numbered' 或 'bullet')
        
        返回:
            格式化的贡献列表
        """
        if style == "numbered":
            lines = ["The main contributions of this work are:"]
            for i, contrib in enumerate(contributions, 1):
                lines.append(f"\n{i}. **{contrib['title']}**: {contrib['details']}")
            return "\n".join(lines)
        else:
            lines = []
            for contrib in contributions:
                lines.append(f"- **{contrib['title']}**: {contrib['details']}")
            return "\n".join(lines)


# ==================== 便捷函数 ====================

def create_professor_writing_strategies() -> ProfessorWritingStrategies:
    """创建写作策略实例"""
    return ProfessorWritingStrategies()


if __name__ == '__main__':
    # 示例使用
    strategies = ProfessorWritingStrategies()
    
    # 检查AI痕迹
    text = "Our method achieves excellent results and plays a critical role in urban monitoring."
    result = strategies.check_ai_patterns(text)
    print("=== AI Pattern Check ===")
    print(f"Score: {result['score']}/100")
    print(f"Has AI patterns: {result['has_ai_patterns']}")
    for issue in result['issues']:
        print(f"  - {issue['type']}: '{issue['found']}'")
        print(f"    Suggestion: {issue['suggestion']}")
    
    # 生成量化对比
    comparison = strategies.generate_quantitative_comparison(
        our_value=90.16,
        baseline_value=90.87,
        metric="F1",
        baseline_name="BIT",
        params_ours=11.8,
        params_baseline=27.8
    )
    print(f"\n=== Quantitative Comparison ===")
    print(comparison)
    
    # 生成首次创新陈述
    innovation = strategies.generate_first_innovation_statement(
        "introduce self-attention mechanisms",
        "semantic change detection"
    )
    print(f"\n=== First Innovation Statement ===")
    print(innovation)
