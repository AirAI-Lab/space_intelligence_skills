# SigLIP2 + RADIO 零样本评估报告 v2

## 总览
- 样本数: 109
- 总体准确率: 17.43%
- 异常类 Macro-F1: 17.08%
- 正常水误检率: 72.00%
- 颜色软融合 alpha: 0.200
- 预测分布: {'normal_water': 34, 'turbid_water': 7, 'black_water': 28, 'green_water': 3, 'milky_foam_water': 15, 'red_water': 16, 'dam_seepage': 6}

## 类别阈值
- black_water: 0.250
- turbid_water: 0.100
- red_water: 0.200
- green_water: 0.100
- milky_foam_water: 0.400
- dam_seepage: 0.150

## 异常类别指标
- black_water: P=17.86%, R=31.25%, F1=22.73%, mIoU=0.0017, TP/FP/FN=5/23/11
- turbid_water: P=14.29%, R=4.17%, F1=6.45%, mIoU=0.0000, TP/FP/FN=1/6/23
- red_water: P=6.25%, R=11.11%, F1=8.00%, mIoU=0.0132, TP/FP/FN=1/15/8
- green_water: P=33.33%, R=7.69%, F1=12.50%, mIoU=0.0000, TP/FP/FN=1/2/12
- milky_foam_water: P=6.67%, R=6.67%, F1=6.67%, mIoU=0.0028, TP/FP/FN=1/14/14
- dam_seepage: P=50.00%, R=42.86%, F1=46.15%, mIoU=0.0043, TP/FP/FN=3/3/4

## 失败样本诊断
- GT=normal_water
  - image=69.jpeg, pred=milky_foam_water, score=0.815, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=069_69_gt-normal_water_pred-milky_foam_water.jpg
  - image=3.jpeg, pred=black_water, score=0.798, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=003_3_gt-normal_water_pred-black_water.jpg
  - image=87.png, pred=milky_foam_water, score=0.796, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=087_87_gt-normal_water_pred-milky_foam_water.jpg
  - image=98.png, pred=black_water, score=0.792, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=098_98_gt-normal_water_pred-black_water.jpg
  - image=11.jpeg, pred=black_water, score=0.787, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=011_11_gt-normal_water_pred-black_water.jpg
- GT=turbid_water
  - image=6.jpeg, pred=black_water, score=0.848, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=006_6_gt-turbid_water_pred-black_water.jpg
  - image=22.jpeg, pred=black_water, score=0.785, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=022_22_gt-turbid_water_pred-black_water.jpg
  - image=36.jpg, pred=milky_foam_water, score=0.782, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=036_36_gt-turbid_water_pred-milky_foam_water.jpg
  - image=5.jpeg, pred=normal_water, score=0.000, iou=0.000, reason=文本对齐偏弱（分类分数低）, vis=005_5_gt-turbid_water_pred-normal_water.jpg
  - image=12.jpg, pred=normal_water, score=0.000, iou=0.000, reason=文本对齐偏弱（分类分数低）, vis=012_12_gt-turbid_water_pred-normal_water.jpg
- GT=green_water
  - image=105.jpg, pred=red_water, score=0.850, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=105_105_gt-green_water_pred-red_water.jpg
  - image=19.jpeg, pred=turbid_water, score=0.707, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=019_19_gt-green_water_pred-turbid_water.jpg
  - image=55.jpg, pred=turbid_water, score=0.687, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=055_55_gt-green_water_pred-turbid_water.jpg
  - image=7.jpeg, pred=turbid_water, score=0.680, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=007_7_gt-green_water_pred-turbid_water.jpg
  - image=82.jpg, pred=dam_seepage, score=0.674, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=082_82_gt-green_water_pred-dam_seepage.jpg
- GT=black_water
  - image=15.png, pred=normal_water, score=0.000, iou=0.000, reason=文本对齐偏弱（分类分数低）, vis=015_15_gt-black_water_pred-normal_water.jpg
  - image=38.jpeg, pred=normal_water, score=0.000, iou=0.000, reason=文本对齐偏弱（分类分数低）, vis=038_38_gt-black_water_pred-normal_water.jpg
  - image=44.png, pred=normal_water, score=0.000, iou=0.000, reason=文本对齐偏弱（分类分数低）, vis=044_44_gt-black_water_pred-normal_water.jpg
  - image=84.png, pred=normal_water, score=0.000, iou=0.000, reason=文本对齐偏弱（分类分数低）, vis=084_84_gt-black_water_pred-normal_water.jpg
  - image=90.jpeg, pred=normal_water, score=0.000, iou=0.000, reason=文本对齐偏弱（分类分数低）, vis=090_90_gt-black_water_pred-normal_water.jpg
- GT=milky_foam_water
  - image=60.jpeg, pred=black_water, score=0.865, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=060_60_gt-milky_foam_water_pred-black_water.jpg
  - image=34.jpeg, pred=black_water, score=0.852, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=034_34_gt-milky_foam_water_pred-black_water.jpg
  - image=57.jpg, pred=black_water, score=0.849, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=057_57_gt-milky_foam_water_pred-black_water.jpg
  - image=16.jpeg, pred=black_water, score=0.790, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=016_16_gt-milky_foam_water_pred-black_water.jpg
  - image=70.jpeg, pred=red_water, score=0.737, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=070_70_gt-milky_foam_water_pred-red_water.jpg
- GT=dam_seepage
  - image=30.jpeg, pred=black_water, score=0.774, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=030_30_gt-dam_seepage_pred-black_water.jpg
  - image=23.jpeg, pred=green_water, score=0.658, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=023_23_gt-dam_seepage_pred-green_water.jpg
  - image=21.jpeg, pred=milky_foam_water, score=0.895, iou=0.001, reason=类别混淆（提示词可分性不足）, vis=021_21_gt-dam_seepage_pred-milky_foam_water.jpg
  - image=47.jpeg, pred=black_water, score=0.764, iou=0.018, reason=类别混淆（提示词可分性不足）, vis=047_47_gt-dam_seepage_pred-black_water.jpg
- GT=red_water
  - image=26.jpg, pred=normal_water, score=0.000, iou=0.000, reason=文本对齐偏弱（分类分数低）, vis=026_26_gt-red_water_pred-normal_water.jpg
  - image=61.jpg, pred=normal_water, score=0.000, iou=0.000, reason=文本对齐偏弱（分类分数低）, vis=061_61_gt-red_water_pred-normal_water.jpg
  - image=63.jpg, pred=normal_water, score=0.000, iou=0.000, reason=文本对齐偏弱（分类分数低）, vis=063_63_gt-red_water_pred-normal_water.jpg
  - image=109.jpg, pred=normal_water, score=0.000, iou=0.000, reason=文本对齐偏弱（分类分数低）, vis=109_109_gt-red_water_pred-normal_water.jpg
  - image=62.jpg, pred=black_water, score=0.729, iou=0.000, reason=类别混淆（提示词可分性不足）, vis=062_62_gt-red_water_pred-black_water.jpg
