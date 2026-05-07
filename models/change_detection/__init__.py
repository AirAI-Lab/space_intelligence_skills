"""
变换检测系统

基于 C-RADIOv4 零样本分割的时序变换检测:
- 违建检测 (新增/扩建建筑物)
- 堆放物检测 (垃圾倾倒、建筑废料)
- 车辆检测 (违法停车)
- 地表变化 (裸地、施工区域)
"""

from .models.unified import ChangeDetector, ChangeResult

__version__ = "1.0.0"
__author__ = "空中智能体团队"
