"""
施工安全监测系统

功能:
- 安全装备检测（4类）
- 危险区域（3类）
- 危险行为（5类）
- 机械监测（3类）
"""

from .models.unified import SafetyDetector, Detection, Alert, Compliance

__version__ = "1.0.0"
__author__ = "空中智能体团队"
