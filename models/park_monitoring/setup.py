#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水利巡检智能检测系统 - 安装脚本
"""

from setuptools import setup, find_packages

setup(
    name="water_inspection",
    version="1.0.0",
    description="水利巡检智能检测系统 - 统一、规范、可部署",
    author="空中智能体团队",
    author_email="team@skyagent.com",
    url="https://github.com/your-org/water-inspection",
    license="Internal",
    
    # 包
    packages=find_packages(exclude=["tests", "docs"]),
    
    # 依赖
    install_requires=[
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "numpy>=1.24.0",
        "pillow>=9.5.0",
        "opencv-python>=4.8.0",
        "ultralytics>=8.0.180",
        "pyyaml>=6.0",
        "albumentations>=1.3.0",
        "tqdm>=4.65.0",
    ],
    
    # 额外依赖
    extras_require={
        "api": [
            "fastapi>=0.100.0",
            "uvicorn>=0.22.0",
            "python-multipart>=0.0.6",
        ],
        "dev": [
            "pytest>=7.4.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
        ],
        "jetson": [
            "torch2trt>=0.4.0",
        ],
    },
    
    # Python版本
    python_requires=">=3.8",
    
    # 分类器
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    
    # 入口点
    entry_points={
        "console_scripts": [
            "water-inspect=water_inspection.cli:main",
        ],
    },
)
