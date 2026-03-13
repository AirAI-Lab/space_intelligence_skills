# Token超限自动解决方案

## 问题分析

**当前问题**：
1. 上下文超过205k tokens → `model_context_window_exceeded`
2. 必须手动在电脑重启gateway
3. 手机端无法自动恢复

## 解决方案

### 方案1: 配置自动上下文管理（推荐）

#### 1.1 启用Compaction（自动压缩历史）
```bash
openclaw config set agents.defaults.compaction.mode "safeguard"
openclaw config set agents.defaults.compaction.reserveTokens 20000
openclaw config set agents.defaults.compaction.keepRecentTokens 30000
openclaw config set agents.defaults.compaction.maxHistoryShare 0.7
```

**效果**：
- ✅ 当token接近上限时自动压缩历史
- ✅ 保留最近30k tokens的对话
- ✅ 预留20k tokens用于回复
- ✅ 历史最多占70%上下文

#### 1.2 配置Context Pruning（自动清理）
```bash
openclaw config set agents.defaults.contextPruning.mode "auto"
openclaw config set agents.defaults.contextPruning.softTrimRatio 0.8
openclaw config set agents.defaults.contextPruning.hardClearRatio 0.9
openclaw config set agents.defaults.contextPruning.keepLastAssistants 5
```

**效果**：
- ✅ 80%时开始软清理（压缩tool输出）
- ✅ 90%时硬清理（删除早期历史）
- ✅ 保留最近5条助手回复

### 方案2: Heartbeat增强（自动检测和修复）

在HEARTBEAT.md中添加token监控：

```markdown
## Token监控 (每30分钟)
- 检查当前session token使用情况
- 超过180k自动清空历史
- 发送飞书通知
```

让我创建一个自动监控脚本：

```python
# 在heartbeat中执行
import subprocess
import json

def check_tokens():
    # 获取当前session状态
    result = subprocess.run(
        ['openclaw', 'status', '--json'],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)
    tokens = data['sessions'][0]['tokens']

    # 如果超过180k，自动清空
    if tokens > 180000:
        # 方案A: 重启session
        subprocess.run(['openclaw', 'session', 'restart'])

        # 方案B: 清空历史（需要API支持）
        # subprocess.run(['openclaw', 'session', 'clear-history'])

        # 发送通知
        send_alert("Token超限，已自动清空历史")
```

### 方案3: 自动重启脚本（独立运行）

创建一个独立监控脚本，不需要手动启动：

```bash
# 创建监控脚本
cat > ~/.openclaw/scripts/token_monitor.sh << 'EOF'
#!/bin/bash
while true; do
  # 获取token使用
  TOKENS=$(openclaw status --json 2>/dev/null | jq -r '.sessions[0].tokens' 2>/dev/null)

  if [ ! -z "$TOKENS" ] && [ "$TOKENS" -gt 180000 ]; then
    echo "[$(date)] Token超限 ($TOKENS)，自动重启session"
    openclaw session restart

    # 发送飞书通知
    # curl -X POST "your-webhook-url" -d "Token超限已自动恢复"
  fi

  sleep 600  # 每10分钟检查一次
done
EOF

chmod +x ~/.openclaw/scripts/token_monitor.sh

# 添加到系统服务（开机自启）
# Linux: systemd service
# macOS: launchd plist
# Windows: Task Scheduler
```

### 方案4: 飞书命令远程重启（最简单）

**配置飞书命令**（如果支持）：
```
用户发送: /restart
系统执行: 重启gateway
```

或者在飞书中发送特定消息触发重启：
```
用户: 重启gateway
AI: 收到，正在重启...
```

## 推荐配置（综合方案）

### 立即配置（自动上下文管理）
```bash
# 1. Compaction配置
openclaw config set agents.defaults.compaction.mode "safeguard"
openclaw config set agents.defaults.compaction.reserveTokens 20000
openclaw config set agents.defaults.compaction.keepRecentTokens 30000
openclaw config set agents.defaults.compaction.maxHistoryShare 0.7

# 2. Context Pruning配置
openclaw config set agents.defaults.contextPruning.mode "auto"
openclaw config set agents.defaults.contextPruning.softTrimRatio 0.8
openclaw config set agents.defaults.contextPruning.hardClearRatio 0.9

# 3. 重启gateway生效
openclaw gateway restart
```

### 效果
- ✅ **自动压缩**：接近上限时自动压缩历史
- ✅ **自动清理**：超限时自动清理早期内容
- ✅ **保留最近**：保留最近的对话上下文
- ✅ **无需手动**：系统自动管理，无需人工干预

### 如果还是超限（最后手段）

在HEARTBEAT.md中添加：
```markdown
## Token紧急清理
如果遇到model_context_window_exceeded：
1. 自动重启session
2. 发送飞书通知
3. 记录到日志
```

## 验证配置

```bash
# 查看当前配置
openclaw config get agents.defaults.compaction
openclaw config get agents.defaults.contextPruning

# 查看session状态
openclaw status
```

## 总结

**最佳方案**：方案1（自动上下文管理）
- 配置简单
- 自动生效
- 保留最近对话
- 无需手动干预

**备用方案**：Heartbeat增强
- 定期检查
- 超限自动清理
- 发送通知

**最终方案**：飞书远程命令
- 手机端直接发命令
- 无需到电脑前

建议先配置方案1，如果还有问题再增加方案2和3。
