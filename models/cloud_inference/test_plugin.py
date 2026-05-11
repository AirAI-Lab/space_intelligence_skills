#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
插件化重构验证脚本

验证 ScenarioPlugin 能正确读取所有场景 YAML 的告警规则，
并与旧硬编码 alert_map 输出一致。

用法:
  python models/cloud_inference/test_plugin.py
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent.parent
if not (PROJECT_ROOT / "models").exists():
    PROJECT_ROOT = _HERE.parent
sys.path.insert(0, str(_HERE))

from plugin_base import ScenarioPlugin

# 旧硬编码 alert_map (来自 radio_infer_server.py 原始代码)
OLD_ALERT_MAP = {
    # 水利巡检
    "black_water": ("critical", "黑水污染"),
    "brown_water": ("critical", "褐色水体"),
    "yellow_water": ("warning", "黄色水体"),
    "green_water": ("warning", "藻类爆发"),
    "red_water": ("critical", "化学污染"),
    "milky_water": ("warning", "水体浑浊"),
    "foam_water": ("warning", "水面泡沫"),
    "dam_seepage": ("critical", "坝体渗水"),
    # 施工安全
    "bare_soil_uncovered": ("warning", "裸土未覆盖"),
    "dust_pollution": ("critical", "扬尘污染"),
    "pit_water_accumulation": ("warning", "坑内积水"),
    "material_near_pit": ("warning", "基坑边材料堆放"),
    # 变换检测
    "blue_canopy": ("warning", "蓝色雨棚违建"),
    "green_shack": ("warning", "绿色棚屋违建"),
    "illegal_extension": ("warning", "违章搭建"),
    "vehicle": ("info", "机动车辆"),
    "construction_vehicle": ("info", "工程车辆"),
    "debris_dump": ("warning", "垃圾违规堆放"),
    "material_stock": ("info", "建材堆放"),
    "enclosure_fence": ("info", "围挡围栏"),
    "scaffolding": ("info", "脚手架"),
    "bare_ground": ("info", "裸土"),
}


def test_config(config_path: str, scenario_name: str):
    """测试单个场景配置"""
    print(f"\n{'='*60}")
    print(f"测试场景: {scenario_name}")
    print(f"配置文件: {config_path}")
    print('='*60)

    try:
        plugin = ScenarioPlugin(config_path)
    except FileNotFoundError:
        print(f"  ⚠ 配置文件不存在, 跳过")
        return True

    # 1. 检查类别加载
    classes = plugin.get_classes_config()
    print(f"  类别数: {len(classes)}")
    print(f"  类别列表: {list(classes.keys())}")

    # 2. 检查阈值
    threshold, min_area = plugin.get_thresholds()
    print(f"  阈值: threshold={threshold}, min_area={min_area}")

    # 3. 检查告警规则
    alert_rules = plugin.get_alert_rules()
    print(f"  告警规则数: {len(alert_rules)}")
    for cls, rule in alert_rules.items():
        print(f"    {cls}: level={rule['level']}, desc={rule['description']}")

    # 4. 生成模拟告警，对比旧硬编码
    print(f"\n  --- 对比旧硬编码 alert_map ---")
    test_segments = {}
    for cls_name in classes:
        test_segments[cls_name] = {
            "area": 0.1,
            "score": 0.8,
            "class_name_cn": classes[cls_name].get("zh", cls_name),
        }

    new_alerts = plugin.generate_alerts(test_segments, min_area=0.01)
    new_alert_map = {a["class_name"]: a["level"] for a in new_alerts}

    match = 0
    mismatch = 0
    missing = 0
    extra = 0

    for cls_name in classes:
        old_entry = OLD_ALERT_MAP.get(cls_name)
        new_level = new_alert_map.get(cls_name)

        if old_entry is None:
            # YAML 中有但旧 alert_map 没有的类别
            if new_level is not None:
                extra += 1
                print(f"    [新增] {cls_name}: level={new_level} (旧代码无此类别)")
            continue

        old_level = old_entry[0]
        if new_level is None:
            missing += 1
            print(f"    [缺失] {cls_name}: 旧={old_level}, 新=无告警规则")
        elif new_level == old_level:
            match += 1
        else:
            mismatch += 1
            print(f"    [不一致] {cls_name}: 旧={old_level}, 新={new_level}")

    print(f"\n  结果: 匹配={match}, 不一致={mismatch}, 缺失={missing}, 新增={extra}")

    if mismatch > 0 or missing > 0:
        print(f"  ❌ {scenario_name} 验证失败")
        return False
    else:
        print(f"  ✅ {scenario_name} 验证通过")
        return True


def main():
    configs = [
        ("models/water_inspection/configs/water_inspection.yaml", "水利巡检"),
        ("models/construction_safety/configs/construction_safety.yaml", "施工安全"),
        ("models/change_detection/configs/change_detection.yaml", "变换检测"),
        ("models/park_monitoring/configs/park_monitoring.yaml", "园区监控"),
    ]

    all_pass = True
    for config_path, name in configs:
        full_path = str(PROJECT_ROOT / config_path)
        if not test_config(full_path, name):
            all_pass = False

    print(f"\n{'='*60}")
    if all_pass:
        print("✅ 全部场景验证通过!")
    else:
        print("❌ 存在验证失败的场景，请检查上面的输出")
    print('='*60)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
