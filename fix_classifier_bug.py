#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复重构代码bug的补丁

问题1: classifier.py - compute_similarity 空文本列表
问题2: segmentor.py - max() 空序列

作者: 空中智能体团队
日期: 2026-04-05
"""

import os

def fix_classifier_py():
    """修复 classifier.py 的空文本检查"""
    classifier_path = "/app/water_inspection/models/open_vocab/core/classifier.py"

    with open(classifier_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 在 texts = pos_texts + neg_texts 之后添加检查
    old_code = "        texts = pos_texts + neg_texts\n\n        # 使用 backbone 的 SigLIP2 adaptor"

    new_code = """        texts = pos_texts + neg_texts

        # 检查空文本列表
        if not texts:
            logger.warning("没有有效的提示词文本，返回默认分类")
            return {cls_name: 1.0/len(classes_config) for cls_name in classes_config.keys()}

        # 使用 backbone 的 SigLIP2 adaptor"""

    content = content.replace(old_code, new_code)

    with open(classifier_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ classifier.py 修复完成")


def fix_segmentor_py():
    """修复 segmentor.py 的空序列检查"""
    segmentor_path = "/app/water_inspection/models/open_vocab/core/segmentor.py"

    with open(segmentor_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复第1处: requested_classes 空列表检查
    old_code1 = """        requested_classes = [
            k for k, v in classes_config.items()
            if not v.get("is_background", False)
        ]

        # ━━━ 第 1 步: 图像级分类 ━━━"""

    new_code1 = """        requested_classes = [
            k for k, v in classes_config.items()
            if not v.get("is_background", False)
        ]

        # 检查空类别列表
        if not requested_classes:
            logger.warning("没有配置检测类别，返回空结果")
            return {}

        # ━━━ 第 1 步: 图像级分类 ━━━"""

    content = content.replace(old_code1, new_code1)

    # 修复第2处: max() 空序列检查
    old_code2 = "        img_anomaly_prob = max(class_probs.get(c, 0.0) for c in requested_classes)"

    new_code2 = "        img_anomaly_prob = max([class_probs.get(c, 0.0) for c in requested_classes] or [0.0])"

    content = content.replace(old_code2, new_code2)

    with open(segmentor_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ segmentor.py 修复完成")


def fix_compute_patch_similarity():
    """修复 compute_patch_similarity 的空文本检查"""
    classifier_path = "/app/water_inspection/models/open_vocab/core/classifier.py"

    with open(classifier_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 在 compute_patch_similarity 的 texts 构建后添加检查
    old_code = "        texts = pos_texts + neg_texts\n\n        # 使用 backbone 的 SigLIP2 adaptor"

    # 这个已经在 fix_classifier_py 中修复了，这里检查是否还有其他地方
    if "# 检查空文本列表" not in content:
        # 如果还没修复，使用相同的逻辑
        new_code = """        texts = pos_texts + neg_texts

        # 检查空文本列表
        if not texts:
            logger.warning("compute_patch_similarity: 没有有效的提示词文本")
            return {cls_name: np.zeros((orig_h, orig_w)) for cls_name in classes_config.keys()}

        # 使用 backbone 的 SigLIP2 adaptor"""
        content = content.replace(old_code, new_code)

        with open(classifier_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("✅ compute_patch_similarity 修复完成")
    else:
        print("✅ compute_patch_similarity 已在 classifier.py 中修复")


if __name__ == '__main__':
    print("开始修复重构代码的bug...")
    print("="*80)

    try:
        fix_classifier_py()
        fix_segmentor_py()
        fix_compute_patch_similarity()

        print("="*80)
        print("✅ 所有bug修复完成！")
        print("现在可以重新运行评估脚本")
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
