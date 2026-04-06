#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送飞书通知 - 使用 OpenClaw API
"""

import json
import sys
from pathlib import Path

# 读取通知内容
notification_file = Path(__file__).parent / "latest_notification.txt"
if not notification_file.exists():
    print("没有待发送的通知")
    sys.exit(0)

with open(notification_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 构建飞书卡片
card = {
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "🎯 ACTA+ViT-Large 训练更新"
            },
            "template": "blue"
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": content.replace("[!]", "**🎉**").replace(":", ":**").replace("\n", "**\n")
                }
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "OpenClaw 训练监控 | 2026-03-27"
                    }
                ]
            }
        ]
    }
}

# 输出 JSON
output_file = Path(__file__).parent / "feishu_card.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(card, f, ensure_ascii=False, indent=2)

print(f"飞书卡片已生成: {output_file}")
print("\n卡片内容:")
print(json.dumps(card, ensure_ascii=False, indent=2))
