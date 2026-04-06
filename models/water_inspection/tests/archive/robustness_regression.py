#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小范围稳健性回归：阈值 + prompt 子集扰动
输出最稳参数（按均值与方差折中），避免单次最优过拟合。
"""

import argparse
import copy
import json
import random
import statistics
import subprocess
from pathlib import Path

import yaml


def perturb_prompt(prompt_cfg, keep_ratio, seed):
    rnd = random.Random(seed)
    out = copy.deepcopy(prompt_cfg)
    scen = out.get("water_anomaly_urban_river", {})
    for _, cfg in scen.items():
        if not isinstance(cfg, dict):
            continue
        for key in ["prompts", "background"]:
            arr = cfg.get(key, [])
            if not isinstance(arr, list) or len(arr) <= 1:
                continue
            k = max(1, int(round(len(arr) * keep_ratio)))
            idx = list(range(len(arr)))
            rnd.shuffle(idx)
            idx = sorted(idx[:k])
            cfg[key] = [arr[i] for i in idx]
    return out


def run_eval(root: Path, threshold: float, out_json: Path):
    cmd = [
        "python3",
        "tests/evaluate_manual_gt_detection.py",
        "--input-dir",
        str(root / "data" / "test_results"),
        "--meta-dir",
        str(root / "data" / "evaluation" / "manual_gt" / "meta"),
        "--output",
        str(out_json),
        "--threshold",
        str(threshold),
        "--device",
        "cuda",
        "--radio-code-dir",
        "/app/models/NVlabs_RADIO",
        "--siglip2-dir",
        "/app/models/siglip2-giant-opt-patch16-384",
        "--checkpoint",
        "/app/models/C-RADIOv4-H/c-radio_v4-h_half.pth.tar",
    ]
    subprocess.run(cmd, check=True, cwd=str(root))
    return json.loads(out_json.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=str, default="/app/water_inspection")
    ap.add_argument("--thresholds", type=str, default="0.25,0.30,0.35")
    ap.add_argument("--prompt-keep", type=str, default="0.6,0.8,1.0")
    ap.add_argument("--seeds", type=str, default="11,23")
    ap.add_argument("--out", type=str, default="/app/water_inspection/data/evaluation/robustness_regression_report.json")
    args = ap.parse_args()

    root = Path(args.project_root)
    cfg_path = root / "configs" / "water_inspection.yaml"
    prompt_path = root / "configs" / "prompt.yml"

    base_cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    base_prompt = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))

    thresholds = [float(x) for x in args.thresholds.split(",") if x.strip()]
    prompt_keep = [float(x) for x in args.prompt_keep.split(",") if x.strip()]
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]

    work = root / "work" / "robustness"
    work.mkdir(parents=True, exist_ok=True)

    rows = []

    try:
        for th in thresholds:
            for keep in prompt_keep:
                f1_vals = []
                fp_vals = []
                for sd in seeds:
                    run_cfg = copy.deepcopy(base_cfg)
                    run_cfg["cloud"]["radio"]["inference"]["threshold"] = th
                    cfg_path.write_text(yaml.safe_dump(run_cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

                    run_prompt = perturb_prompt(base_prompt, keep, sd)
                    prompt_path.write_text(yaml.safe_dump(run_prompt, allow_unicode=True, sort_keys=False), encoding="utf-8")

                    out_json = work / f"eval_t{th}_k{keep}_s{sd}.json"
                    rep = run_eval(root, th, out_json)
                    f1_vals.append(float(rep["image_level"]["f1"]))
                    fp_vals.append(float(rep["normal_images"]["false_positive_rate"]))

                mean_f1 = statistics.mean(f1_vals)
                std_f1 = statistics.pstdev(f1_vals)
                mean_fp = statistics.mean(fp_vals)
                robust_score = mean_f1 - 0.7 * std_f1 - 0.3 * mean_fp
                rows.append(
                    {
                        "threshold": th,
                        "prompt_keep_ratio": keep,
                        "mean_f1": mean_f1,
                        "std_f1": std_f1,
                        "mean_fp_rate": mean_fp,
                        "robust_score": robust_score,
                        "runs": len(seeds),
                    }
                )
    finally:
        cfg_path.write_text(yaml.safe_dump(base_cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
        prompt_path.write_text(yaml.safe_dump(base_prompt, allow_unicode=True, sort_keys=False), encoding="utf-8")

    rows.sort(key=lambda x: x["robust_score"], reverse=True)
    result = {
        "metric": "robust_score = mean_f1 - 0.7*std_f1 - 0.3*mean_fp_rate",
        "grid": rows,
        "best": rows[0] if rows else None,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"best": result["best"], "out": str(out)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
