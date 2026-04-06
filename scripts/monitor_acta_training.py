#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACTA+ViT-Large 训练监控脚本
监听训练状态，在达到最佳结果时输出通知内容
"""

import json
import subprocess
import re
from datetime import datetime
from pathlib import Path

# 配置
CONTAINER_NAME = "rcmt-training"
CONTAINER_LOG_PATH = "/workspace/peftcd_repro/peftcd_repro/artifacts/logs/acta_train.log"
STATE_FILE = Path(__file__).parent / "acta_vit_monitor_state.json"


def load_state():
    """加载状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    return {
        "last_check": None,
        "best_iou": 0,
        "best_f1": 0,
        "last_epoch": 0,
        "best_epoch": 0,
        "notifications_sent": []
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
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='ignore'
        )
        if result.returncode == 0:
            return result.stdout
    except Exception as e:
        print(f"读取日志失败: {e}")
    return None


def parse_log_content(content):
    """解析日志内容"""
    metrics = {
        "current_epoch": 0,
        "total_epochs": 0,
        "val_iou": 0,
        "val_f1": 0,
        "val_p": 0,
        "val_r": 0,
        "train_loss": 0,
        "val_loss": 0,
        "best_metric": "",
        "best_value": 0,
        "has_new_best": False,
        "is_running": False,
        "is_completed": False,
        "error_message": ""
    }
    
    if not content:
        return metrics
    
    # 提取 epoch
    epoch_match = re.findall(r"Epoch\s+(\d+)/(\d+)\s+\|", content)
    if epoch_match:
        # 取最后一个 epoch
        last_epoch = epoch_match[-1]
        metrics["current_epoch"] = int(last_epoch[0])
        metrics["total_epochs"] = int(last_epoch[1])
        metrics["is_running"] = True
    
    # 提取指标 - 取最后一个 epoch 的值
    all_iou = re.findall(r"val_iou=([\d.]+)", content)
    if all_iou:
        metrics["val_iou"] = float(all_iou[-1])
    
    all_f1 = re.findall(r"val_f1=([\d.]+)", content)
    if all_f1:
        metrics["val_f1"] = float(all_f1[-1])
    
    all_p = re.findall(r"val_p=([\d.]+)", content)
    if all_p:
        metrics["val_p"] = float(all_p[-1])
    
    all_r = re.findall(r"val_r=([\d.]+)", content)
    if all_r:
        metrics["val_r"] = float(all_r[-1])
    
    all_train_loss = re.findall(r"train_loss=([\d.]+)", content)
    if all_train_loss:
        metrics["train_loss"] = float(all_train_loss[-1])
    
    all_val_loss = re.findall(r"val_loss=([\d.]+)", content)
    if all_val_loss:
        metrics["val_loss"] = float(all_val_loss[-1])
    
    # 检查最佳结果 - 检查当前 epoch 是否有新最佳
    best_match = re.findall(r"New best (IoU|F1) at epoch (\d+):\s*([\d.]+)", content)
    if best_match:
        # 取最后一个最佳结果
        last_best = best_match[-1]
        metrics["best_metric"] = last_best[0]
        metrics["best_value"] = float(last_best[2])
        # 检查是否是当前 epoch
        if int(last_best[1]) == metrics["current_epoch"]:
            metrics["has_new_best"] = True
    
    # 检查完成/错误
    if re.search(r"Training completed|训练完成", content):
        metrics["is_completed"] = True
        metrics["is_running"] = False
    
    if re.search(r"Error:|Exception:|RuntimeError", content):
        metrics["is_running"] = False
        metrics["error_message"] = "训练出错"
    
    return metrics


def generate_notification(metrics, previous_best):
    """生成通知消息"""
    lines = [
        "[!] 新的最佳 IoU 结果！",
        "",
        f"Epoch: {metrics['current_epoch']}/{metrics['total_epochs']}",
        f"最佳 IoU: {metrics['val_iou']:.4f}",
        f"F1 Score: {metrics['val_f1']:.4f}",
        f"Precision: {metrics['val_p']:.4f}",
        f"Recall: {metrics['val_r']:.4f}",
        f"Train Loss: {metrics['train_loss']:.4f}",
        f"Val Loss: {metrics['val_loss']:.4f}"
    ]
    
    if previous_best > 0:
        improvement = (metrics['val_iou'] - previous_best) * 100
        lines.append(f"\n提升: +{improvement:.2f}%")
    
    return "\n".join(lines)


def main():
    """主监控函数"""
    state = load_state()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 50)
    print("ACTA+ViT-Large 训练监控")
    print(f"时间: {timestamp}")
    print("=" * 50)
    
    # 读取日志
    log_content = get_container_log()
    if not log_content:
        print("[!] 无法读取训练日志")
        return
    
    # 解析
    metrics = parse_log_content(log_content)
    
    # 显示状态
    print("\n[*] 训练状态:")
    if metrics["current_epoch"] > 0:
        progress = metrics["current_epoch"] / metrics["total_epochs"] * 100
        print(f"  Epoch: {metrics['current_epoch']}/{metrics['total_epochs']} ({progress:.2f}%)")
    
    print(f"  Val IoU: {metrics['val_iou']:.4f}")
    print(f"  Val F1: {metrics['val_f1']:.4f}")
    print(f"  Val Precision: {metrics['val_p']:.4f}")
    print(f"  Val Recall: {metrics['val_r']:.4f}")
    print(f"  Train Loss: {metrics['train_loss']:.4f}")
    print(f"  Val Loss: {metrics['val_loss']:.4f}")
    
    if metrics["best_metric"]:
        print(f"\n  [*] 当前最佳 {metrics['best_metric']}: {metrics['best_value']:.4f}")
    
    if metrics["is_completed"]:
        print("\n  [OK] 训练完成")
    elif metrics["is_running"]:
        print("\n  [.] 训练进行中...")
    elif metrics["error_message"]:
        print(f"\n  [X] {metrics['error_message']}")
    
    # 检查新的最佳结果
    notification = None
    if (metrics["has_new_best"] and
        metrics["best_metric"] == "IoU" and
        metrics["val_iou"] > state["best_iou"]):
        
        print(f"\n[!] 检测到新的最佳 IoU: {metrics['val_iou']:.4f} (之前: {state['best_iou']:.4f})")
        
        # 生成通知
        notification = generate_notification(metrics, state["best_iou"])
        
        # 更新状态
        state["best_iou"] = metrics["val_iou"]
        state["best_f1"] = metrics["val_f1"]
        state["best_epoch"] = metrics["current_epoch"]
        
        print("\n[*] 通知内容:")
        print(notification)
        
        # 保存通知到文件
        notification_file = Path(__file__).parent / "latest_notification.txt"
        with open(notification_file, 'w', encoding='utf-8') as f:
            f.write(notification)
        print(f"\n[OK] 通知已保存到: {notification_file}")
    
    # 更新状态
    state["last_check"] = timestamp
    state["last_epoch"] = metrics["current_epoch"]
    save_state(state)
    
    print("\n[OK] 监控检查完成")
    
    return notification


if __name__ == "__main__":
    import sys
    
    # 如果带参数 --daemon，则循环运行
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        import time
        interval = 300  # 5 分钟
        print(f"启动守护进程模式，检查间隔: {interval} 秒")
        print("按 Ctrl+C 退出\n")
        
        while True:
            try:
                notification = main()
                if notification:
                    # 保存到 JSON 供外部读取
                    notification_json = Path(__file__).parent / "pending_notification.json"
                    with open(notification_json, 'w', encoding='utf-8') as f:
                        json.dump({
                            "timestamp": datetime.now().isoformat(),
                            "message": notification
                        }, f, ensure_ascii=False, indent=2)
                    print(f"\n📩 通知已保存到: {notification_json}")
                
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\n\n监控已停止")
                break
    else:
        main()
