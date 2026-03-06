# -*- coding: utf-8 -*-
"""
论文写作配置
Paper Writing Configuration

管理论文写作的全局配置和参数。

作者: OpenClaw Writing System
日期: 2026-03-05
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ==================== 期刊配置 ====================

JOURNAL_CONFIGS = {
    "ieee_tgrs": {
        "name": "IEEE Transactions on Geoscience and Remote Sensing",
        "abbreviation": "IEEE TGRS",
        "impact_factor": 8.2,
        "style": "ieee",
        "format": "double_column",
        "page_limit": "12 pages",
        "math_mode": "latex",
        "citation_style": "numbered",
        "template": "IEEEtran"
    },
    "cvpr": {
        "name": "IEEE/CVF Conference on Computer Vision and Pattern Recognition",
        "abbreviation": "CVPR",
        "impact_factor": None,
        "style": "cvpr",
        "format": "single_column",
        "page_limit": "8 pages + supplement",
        "math_mode": "latex",
        "citation_style": "author_year",
        "template": "CVPR"
    },
    "iccv": {
        "name": "IEEE International Conference on Computer Vision",
        "abbreviation": "ICCV",
        "impact_factor": None,
        "style": "cvpr",
        "format": "single_column",
        "page_limit": "8 pages + supplement",
        "math_mode": "latex",
        "citation_style": "author_year",
        "template": "ICCV"
    },
    "nature": {
        "name": "Nature Communications",
        "abbreviation": "Nature",
        "impact_factor": 16.6,
        "style": "nature",
        "format": "single_column",
        "page_limit": "5-10 pages",
        "math_mode": "latex",
        "citation_style": "superscript",
        "template": "Nature"
    }
}


# ==================== 写作风格配置 ====================

WRITING_STYLE_CONFIGS = {
    "professor": {
        "name": "Professor Level",
        "description": "教授级写作，强调量化对比和引用支持",
        "require_quantitative": True,
        "require_citations": True,
        "avoid_ai_patterns": True,
        "emphasize_first_innovation": True,
        "emphasize_efficiency": True,
        "quality_threshold": 80  # A级
    },
    "sota": {
        "name": "SOTA Level",
        "description": "SOTA论文写作风格，强调创新和性能",
        "require_quantitative": True,
        "require_citations": True,
        "avoid_ai_patterns": True,
        "emphasize_first_innovation": True,
        "emphasize_efficiency": True,
        "quality_threshold": 70  # B级
    },
    "standard": {
        "name": "Standard Academic",
        "description": "标准学术写作",
        "require_quantitative": False,
        "require_citations": True,
        "avoid_ai_patterns": True,
        "emphasize_first_innovation": False,
        "emphasize_efficiency": False,
        "quality_threshold": 60  # C级
    }
}


# ==================== 论文配置数据结构 ====================

@dataclass
class PaperConfig:
    """论文配置"""
    # 基本信息
    title: str
    authors: List[str]
    affiliation: str
    
    # 期刊信息
    target_journal: str = "ieee_tgrs"
    
    # 写作风格
    writing_style: str = "professor"  # professor, sota, standard
    
    # 语言
    language: str = "en"  # en, zh
    
    # 输出格式
    output_format: str = "latex"  # latex, markdown, text
    
    # 质量要求
    require_quantitative_comparison: bool = True
    require_citation_support: bool = True
    avoid_ai_patterns: bool = True
    check_quality: bool = True
    
    # 自定义选项
    custom_abstract_style: Optional[str] = None  # bit, changeformer, tinycd
    enable_quality_feedback: bool = True
    
    # 实验数据
    experiment_data_path: Optional[str] = None
    include_ablation: bool = True
    include_visualization: bool = True


# ==================== RCMT-V3特定配置 ====================

@dataclass
class RCMTV3Config:
    """RCMT-V3特定配置"""
    # 项目信息
    project_name: str = "RCMT-V3"
    full_name: str = "A Systematic Framework for High-Performance Change Detection"
    
    # 模型变体
    variants: List[str] = field(default_factory=lambda: ["RCMT-V3-Hybrid", "RCMT-V3-Swin"])
    primary_variant: str = "RCMT-V3-Hybrid"
    
    # 关键贡献
    contributions: List[Dict] = field(default_factory=lambda: [
        {
            "id": 1,
            "title": "Systematic Optimization Strategy",
            "improvement": "+1.52% F1",
            "details": "BCEWithLogitsLoss + OneCycleLR + MixUp + Gradient Clipping",
            "architecture_agnostic": True
        },
        {
            "id": 2,
            "title": "Dual Architecture Design",
            "improvement": "Efficiency + Performance",
            "details": "Hybrid (11.8M, 90.16% F1) + Swin (58.7M, 91.5% F1)",
            "architecture_agnostic": False
        },
        {
            "id": 3,
            "title": "Bidirectional Temporal Fusion",
            "improvement": "+0.71% F1",
            "details": "T1 ↔ T2 bidirectional attention vs unidirectional",
            "architecture_agnostic": True
        }
    ])
    
    # 数据集
    primary_dataset: str = "LEVIR-CD256"
    additional_datasets: List[str] = field(default_factory=lambda: ["SYSU-CD", "WHU-CD"])
    
    # 指标
    primary_metric: str = "F1"
    metrics: List[str] = field(default_factory=lambda: ["Precision", "Recall", "F1", "IoU"])
    
    # SOTA基线
    baselines: List[str] = field(default_factory=lambda: [
        "FC-EF", "FC-Siam-Diff", "SNUNet-CD",
        "BIT", "ChangeFormer", "TinyCD", "GCD-DDPM"
    ])
    
    # 主要对比方法
    primary_baseline: str = "BIT"
    secondary_baseline: str = "ChangeFormer"
    efficiency_baseline: str = "TinyCD"


# ==================== 质量检查配置 ====================

@dataclass
class QualityCheckConfig:
    """质量检查配置"""
    # 启用检查
    enable_ai_pattern_detection: bool = True
    enable_citation_check: bool = True
    enable_grammar_check: bool = False  # 需要外部工具
    
    # AI痕迹检测
    ai_pattern_severity_threshold: str = "medium"  # low, medium, high
    
    # 质量阈值
    minimum_quality_score: int = 70  # 70分以下需要改进
    target_quality_score: int = 80  # 80分以上为A级
    
    # 反馈选项
    provide_detailed_feedback: bool = True
    suggest_improvements: bool = True
    auto_improve_simple_patterns: bool = False


# ==================== 输出配置 ====================

@dataclass
class OutputConfig:
    """输出配置"""
    # 输出目录
    output_dir: str = "D:/github/edge_infer_cloud/projects/rcmt_v3/paper_writing/drafts"
    
    # 文件名
    filename_base: str = "rcmtv3_paper"
    
    # 生成格式
    generate_latex: bool = True
    generate_markdown: bool = True
    generate_text: bool = False
    
    # PDF生成（需要pdflatex）
    generate_pdf: bool = False
    
    # 代码注释
    include_comments: bool = True
    comment_style: str = "latex"  # latex, markdown


# ==================== 全局配置 ====================

@dataclass
class GlobalConfig:
    """全局配置"""
    # 论文配置
    paper: PaperConfig = field(default_factory=PaperConfig)
    
    # RCMT-V3配置
    rcmtv3: RCMTV3Config = field(default_factory=RCMTV3Config)
    
    # 质量检查配置
    quality: QualityCheckConfig = field(default_factory=QualityCheckConfig)
    
    # 输出配置
    output: OutputConfig = field(default_factory=OutputConfig)
    
    # 模型配置
    model: str = "glm-4.7"  # 只使用glm-4.7，不使用anthropic模型
    
    # 调试选项
    debug_mode: bool = False
    verbose: bool = True


# ==================== 配置加载和保存 ====================

def load_config_from_dict(config_dict: Dict) -> GlobalConfig:
    """
    从字典加载配置
    """
    global_config = GlobalConfig()
    
    # 更新论文配置
    if 'paper' in config_dict:
        paper_dict = config_dict['paper']
        for key, value in paper_dict.items():
            if hasattr(global_config.paper, key):
                setattr(global_config.paper, key, value)
    
    # 更新RCMT-V3配置
    if 'rcmtv3' in config_dict:
        rcmtv3_dict = config_dict['rcmtv3']
        for key, value in rcmtv3_dict.items():
            if hasattr(global_config.rcmtv3, key):
                setattr(global_config.rcmtv3, key, value)
    
    # 更新质量检查配置
    if 'quality' in config_dict:
        quality_dict = config_dict['quality']
        for key, value in quality_dict.items():
            if hasattr(global_config.quality, key):
                setattr(global_config.quality, key, value)
    
    # 更新输出配置
    if 'output' in config_dict:
        output_dict = config_dict['output']
        for key, value in output_dict.items():
            if hasattr(global_config.output, key):
                setattr(global_config.output, key, value)
    
    return global_config


def save_config_to_yaml(config: GlobalConfig, filepath: str) -> None:
    """
    保存配置到YAML文件
    """
    import yaml
    
    config_dict = {
        'paper': {
            'title': config.paper.title,
            'authors': config.paper.authors,
            'affiliation': config.paper.affiliation,
            'target_journal': config.paper.target_journal,
            'writing_style': config.paper.writing_style,
            'language': config.paper.language,
            'output_format': config.paper.output_format,
            'require_quantitative_comparison': config.paper.require_quantitative_comparison,
            'require_citation_support': config.paper.require_citation_support,
            'avoid_ai_patterns': config.paper.avoid_ai_patterns,
            'check_quality': config.paper.check_quality,
            'custom_abstract_style': config.paper.custom_abstract_style,
            'enable_quality_feedback': config.paper.enable_quality_feedback,
            'experiment_data_path': config.paper.experiment_data_path,
            'include_ablation': config.paper.include_ablation,
            'include_visualization': config.paper.include_visualization
        },
        'rcmtv3': {
            'project_name': config.rcmtv3.project_name,
            'full_name': config.rcmtv3.full_name,
            'variants': config.rcmtv3.variants,
            'primary_variant': config.rcmtv3.primary_variant,
            'contributions': config.rcmtv3.contributions,
            'primary_dataset': config.rcmtv3.primary_dataset,
            'additional_datasets': config.rcmtv3.additional_datasets,
            'primary_metric': config.rcmtv3.primary_metric,
            'metrics': config.rcmtv3.metrics,
            'baselines': config.rcmtv3.baselines,
            'primary_baseline': config.rcmtv3.primary_baseline,
            'secondary_baseline': config.rcmtv3.secondary_baseline,
            'efficiency_baseline': config.rcmtv3.efficiency_baseline
        },
        'quality': {
            'enable_ai_pattern_detection': config.quality.enable_ai_pattern_detection,
            'enable_citation_check': config.quality.enable_citation_check,
            'enable_grammar_check': config.quality.enable_grammar_check,
            'ai_pattern_severity_threshold': config.quality.ai_pattern_severity_threshold,
            'minimum_quality_score': config.quality.minimum_quality_score,
            'target_quality_score': config.quality.target_quality_score,
            'provide_detailed_feedback': config.quality.provide_detailed_feedback,
            'suggest_improvements': config.quality.suggest_improvements,
            'auto_improve_simple_patterns': config.quality.auto_improve_simple_patterns
        },
        'output': {
            'output_dir': config.output.output_dir,
            'filename_base': config.output.filename_base,
            'generate_latex': config.output.generate_latex,
            'generate_markdown': config.output.generate_markdown,
            'generate_text': config.output.generate_text,
            'generate_pdf': config.output.generate_pdf,
            'include_comments': config.output.include_comments,
            'comment_style': config.output.comment_style
        },
        'model': config.model,
        'debug_mode': config.debug_mode,
        'verbose': config.verbose
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"✅ Configuration saved to {filepath}")


def load_config_from_yaml(filepath: str) -> GlobalConfig:
    """
    从YAML文件加载配置
    """
    import yaml
    
    with open(filepath, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)
    
    return load_config_from_dict(config_dict)


# ==================== 默认配置 ====================

# 创建默认的全局配置
DEFAULT_CONFIG = GlobalConfig(
    paper=PaperConfig(
        title="RCMT-V3: A Systematic Framework for High-Performance Change Detection",
        authors=["Author 1", "Author 2"],
        affiliation="Your University",
        target_journal="ieee_tgrs",
        writing_style="professor",
        language="en",
        output_format="latex",
        require_quantitative_comparison=True,
        require_citation_support=True,
        avoid_ai_patterns=True,
        check_quality=True,
        custom_abstract_style="bit",
        enable_quality_feedback=True,
        experiment_data_path=r"D:\github\edge_infer_cloud\projects\rcmt_v3\paper_writing\experiments\rcmt_v3_optimized_results.json",
        include_ablation=True,
        include_visualization=True
    ),
    output=OutputConfig(
        output_dir=r"D:/github/edge_infer_cloud/projects/rcmt_v3/paper_writing/drafts",
        filename_base="rcmtv3_paper",
        generate_latex=True,
        generate_markdown=True,
        generate_text=False,
        generate_pdf=False,
        include_comments=True,
        comment_style="latex"
    )
)


# ==================== 使用示例 ====================

if __name__ == '__main__':
    # 示例：使用默认配置
    config = DEFAULT_CONFIG
    
    print("=" * 80)
    print("默认配置")
    print("=" * 80)
    print()
    print(f"论文标题: {config.paper.title}")
    print(f"作者: {', '.join(config.paper.authors)}")
    print(f"机构: {config.paper.affiliation}")
    print(f"目标期刊: {config.paper.target_journal}")
    print(f"写作风格: {config.paper.writing_style}")
    print(f"语言: {config.paper.language}")
    print(f"输出格式: {config.paper.output_format}")
    print()
    print(f"实验数据路径: {config.paper.experiment_data_path}")
    print(f"项目名称: {config.rcmtv3.project_name}")
    print(f"主要变体: {config.rcmtv3.primary_variant}")
    print(f"主要数据集: {config.rcmtv3.primary_dataset}")
    print(f"主要基线: {config.rcmtv3.primary_baseline}")
    print()
    print(f"输出目录: {config.output.output_dir}")
    print(f"生成LaTeX: {config.output.generate_latex}")
    print(f"生成Markdown: {config.output.generate_markdown}")
    print(f"模型: {config.model}")
    print()
    
    # 示例：保存配置
    config_path = r"D:\github\edge_infer_cloud\writing\core\config.yaml"
    save_config_to_yaml(config, config_path)
    
    # 示例：加载配置
    loaded_config = load_config_from_yaml(config_path)
    print("✅ Configuration loaded successfully")
    print(f"Loaded title: {loaded_config.paper.title}")
