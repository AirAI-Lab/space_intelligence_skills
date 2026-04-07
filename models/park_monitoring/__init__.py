"""
园区监测系统

功能:
- 周界安全（4类）
- 人员行为（5类）
- 车辆管理（3类）
- 停车位检测（1类 OBB）
"""

from .models.unified import ParkDetector, Detection, Alert

__version__ = "1.0.0"
__author__ = "空中智能体团队"
