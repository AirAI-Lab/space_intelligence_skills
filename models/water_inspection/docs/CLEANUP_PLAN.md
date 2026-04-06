# 水利巡检核心代码整理方案

## 一、保留的核心文件（移动到 models/water_inspection）

### 1.1 核心脚本（scripts/）
- train_lightweight_classifier.py - 训练分类器
- generate_visualization_fixed.py - 生成可视化（中文修复版）
- run_sam3_eval_simplified.py - SAM3评估脚本

### 1.2 文档（docs/）
- 从 memory/ 移动相关报告和分析文档

## 二、删除的临时文件

### 2.1 调试脚本
- check_classes.py
- debug_prompts.py
- debug_similarity.py

### 2.2 临时修复脚本
- correct_integration.py
- fix_*.py (所有fix_开头的文件)

### 2.3 临时评估脚本
- evaluate_correct.py
- evaluate_radio_segmentation.py
- evaluate_refactored_model.py
- evaluate_sam3_comparison.py
- evaluate_unified_segmentor.py
- evaluate_with_sam3.py

### 2.4 临时测试脚本
- test_sam3_support.py
- enhance_color_classifier.py
- implement_color_classifier.py
- integrate_lightweight_classifier.py
- optimize_segmentor_v3.py

### 2.5 临时日志文件
- evaluation_6class.txt
- evaluation_final.txt
- eval_log.txt
- final_eval_log.txt
- radio_segmentation_eval.txt

### 2.6 临时运行脚本
- run_docker_eval.py
- run_sam3_eval_in_container.sh
- run_sam3_eval_local.py

### 2.7 临时数据文件
- temp_datasets_meta.json
- evaluate_lightweight_full.py
