#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动监控 ACTA+ViT-Large 训练并发送飞书通知
用于 Windows 任务计划或 OpenClaw 心跳
"""

import json
import subprocess
import re
from datetime import datetime
from pathlib import Path
import sys

# 配置
CONTAINER_NAME = "rcmt-training"
CONTAINER_LOG_PATH = "/workspace/peftcd_repro/peftcd_repro/artifacts/logs/acta_train.log"
STATE_FILE = Path(__file__).parent / "acta_vit_monitor_state.json"
NOTIFICATION_FILE = Path(__file__).parent / "pending_feishu_notification.json"


def load_state():
    """加载状态"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except:
            pass
    return {
        "last_check": None,
        "best_iou": 0,
        "best_f1": 0,
        "last_epoch": 0,
        "best_epoch": 0
    }


def save_state(state):
    """保存状态"""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def get_container_log():
    """从容器读取日志"""
    try:
        result = subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "bash", "-c", f"tail -100 {CONTAINER_LOG_PATH}"],
            capture_output=True,
            timeout=10,
            encoding='utf-8',
            errors='ignore'
        )
        if result.returncode == 0:
            return result.stdout
    except:
        pass
    return None


def parse_log_content(content):
    """解析日志"""
    metrics = {
        "current_epoch": 0,
        "total_epochs": 0,
        "val_iou": 0,
        "val_f1": 0,
        "val_p": 0,
        "val_r": 0,
        "train_loss": 0,
        "val_loss": 0,
        "has_new_best": False,
        "is_running": False
    }

    if not content:
        return metrics

    # 提取最新 epoch
    matches = re.findall(r"Epoch\s+(\d+)/(\d+)\s+\|.*?val_iou=([\d.]+).*?val_f1=([\d.]+).*?val_p=([\d.]+).*?val_r=([\d.]+).*?train_loss=([\d.]+).*?val_loss=([\d.]+)", content)
    if matches:
        last = matches[-1]
        metrics["current_epoch"] = int(last[0])
        metrics["total_epochs"] = int(last[1])
        metrics["val_iou"] = float(last[2])
        metrics["val_f1"] = float(last[3])
        metrics["val_p"] = float(last[4])
        metrics["val_r"] = float(last[5])
        metrics["train_loss"] = float(last[6])
        metrics["val_loss"] = float(last[7])
        metrics["is_running"] = True

    # 检查新最佳
    if re.search(r"New best IoU at epoch " + str(metrics["current_epoch"]), content):
        metrics["has_new_best"] = True

    return metrics


def check_and_notify():
    """检查训练状态并发送通知"""
    state = load_state()
    log_content = get_container_log()

    if not log_content:
        return

    metrics = parse_log_content(log_content)

    # 检查是否新的最佳 IoU
    if (metrics["has_new_best"] and
        metrics["val_iou"] > state["best_iou"] and
        metrics["current_epoch"] > state["last_epoch"]):

        # 更新状态
        state["best_iou"] = metrics["val_iou"]
        state["best_f1"] = metrics["val_f1"]
        state["best_epoch"] = metrics["current_epoch"]
        state["last_check"] = datetime.now().isoformat()

        # 生成通知
        notification = {
            "timestamp": datetime.now().isoformat(),
            "epoch": metrics["current_epoch"],
            "total_epochs": metrics["total_epochs"],
            "best_iou": metrics["val_iou"],
            "best_f1": metrics["val_f1"],
            "precision": metrics["val_p"],
            "recall": metrics["val_r"],
            "train_loss": metrics["train_loss"],
            "val_loss": metrics["val_loss"]
        }

        # 保存通知供 OpenClaw 发送
        with open(NOTIFICATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(notification, f, indent=2, ensure_ascii=False)

        # 输出标记，让 OpenClaw 检测
        print("NOTIFICATION_PENDING")
        print(json.dumps(notification, ensure_ascii=False, indent=2))

    # 更新最后检查的 epoch
    state["last_epoch"] = metrics["current_epoch"]
    save_state(state)


if __name__ == "__main__":
    check_and_notify()
