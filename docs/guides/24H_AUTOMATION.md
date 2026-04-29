# 空中智能体 - 24小时自动化工作方案

> **目的**: 实现OpenClaw 24小时运行，支持远程控制和自动化任务
> **日期**: 2026-03-06

---

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    24小时自动化架构                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │   飞书/微信  │    │  Telegram   │    │  Discord    │    │
│  │   (手机)     │    │   (手机)     │    │   (电脑)    │    │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            ▼                               │
│                  ┌─────────────────┐                       │
│                  │  OpenClaw       │                       │
│                  │  Gateway        │◄── 7x24 运行          │
│                  │  (本地/服务器)   │                       │
│                  └────────┬────────┘                       │
│                           │                                │
│         ┌─────────────────┼─────────────────┐             │
│         ▼                 ▼                 ▼             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │  Heartbeat  │   │    Cron     │   │   子代理    │     │
│  │  定期检查    │   │  定时任务    │   │  任务执行   │     │
│  └─────────────┘   └─────────────┘   └─────────────┘     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 2. 方案一：飞书通道 (推荐)

### 2.1 优势
- ✅ 已配置，当前正在使用
- ✅ 手机App支持，随时随地发指令
- ✅ 消息推送及时
- ✅ 支持富文本、卡片消息

### 2.2 使用方式

**发送指令**:
```
@delegate 检查训练状态
@delegate 软件开发代理: 修复xxx问题
@delegate 算法开发代理: 分析模型性能
```

**查看结果**:
- 子代理完成后自动推送结果到飞书
- 支持长文本、代码块、表格

### 2.3 保持运行

**方式1: 本地PC运行Gateway**
```powershell
# 启动gateway服务
openclaw gateway start

# 查看状态
openclaw gateway status
```

**方式2: 云服务器部署** (推荐周末使用)
- 部署到24小时运行的服务器
- 配置开机自启动
- 通过飞书远程控制

---

## 3. 方案二：Heartbeat自动检查

### 3.1 配置HEARTBEAT.md

编辑 `D:\github\edge_infer_cloud\HEARTBEAT.md`:

```markdown
# Heartbeat 任务清单

## 每次心跳检查 (约30分钟一次)

### 1. 训练状态检查
- 检查RCMT训练进度
- 如果训练完成，发送通知

### 2. 设备状态检查
- 检查边缘设备在线状态
- 如果有设备离线，发送告警

### 3. 代码变更检查
- 检查是否有未提交的代码
- 检查是否有新的PR或Issue
```

### 3.2 自动执行逻辑

OpenClaw会定期读取HEARTBEAT.md，执行里面的任务。

---

## 4. 方案三：Cron定时任务

### 4.1 配置示例

创建 `scripts/cron_tasks.ps1`:

```powershell
# 每小时检查训练状态
$trainLog = "D:\github\edge_infer\rcmt_v3\logs_swin_final_v2\train.log"
$lastLines = Get-Content $trainLog -Tail 5

# 如果训练完成，发送飞书通知
if ($lastLines -match "训练完成") {
    # 调用飞书API发送通知
}

# 检查设备状态
# ...
```

### 4.2 Windows任务计划

```powershell
# 创建定时任务
$action = New-ScheduledTaskAction -Execute "powershell" -Argument "-File D:\github\edge_infer_cloud\scripts\cron_tasks.ps1"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "SkyEdge-Agent-Cron" -Action $action -Trigger $trigger
```

---

## 5. 方案四：远程服务器部署

### 5.1 服务器要求
- Windows/Linux服务器
- Node.js 18+
- 稳定网络连接

### 5.2 部署步骤

```bash
# 1. 安装OpenClaw
npm install -g openclaw

# 2. 克隆代码
git clone https://github.com/xxx/edge_infer_cloud.git

# 3. 配置飞书通道
openclaw config set channel feishu
openclaw config set feishu.app_id xxx
openclaw config set feishu.app_secret xxx

# 4. 启动gateway
openclaw gateway start

# 5. 配置开机自启动
# Linux: systemd
# Windows: 任务计划程序
```

---

## 6. 周末自动化建议

### 6.1 必须配置

1. **Gateway服务**: 保持24小时运行
2. **飞书通道**: 随时接收指令
3. **HEARTBEAT.md**: 配置自动检查任务

### 6.2 推荐配置

1. **自动检查训练状态**:
```markdown
# HEARTBEAT.md
- 每小时检查训练日志
- 如果F1 > 0.92，发送通知
- 如果训练报错，发送告警
```

2. **自动提交代码**:
```
@delegate 每天晚上10点自动提交今天的代码变更
```

3. **自动生成日报**:
```
@delegate 每天18:00生成本日工作总结并发送到飞书
```

---

## 7. 远程控制指令速查

### 7.1 常用指令

```
# 项目状态
@delegate 汇报项目当前状态

# 训练相关
@delegate 算法开发代理: 检查训练进度
@delegate 算法开发代理: 如果训练完成，发送通知

# 代码相关
@delegate 软件开发代理: 提交今天的代码变更

# 文档相关
@delegate 更新MEMORY.md

# 日报
@delegate 生成今天的工作总结
```

### 7.2 紧急情况

```
@delegate 停止所有正在运行的任务
@delegate 发送告警到飞书
```

---

## 8. 实施步骤

### 8.1 立即执行 (今天)

1. **配置HEARTBEAT.md**
```bash
# 编辑心跳配置
code D:\github\edge_infer_cloud\HEARTBEAT.md
```

2. **测试飞书控制**
```
通过手机飞书发送: @delegate 汇报当前状态
```

### 8.2 周末前配置 (周五)

1. **确保Gateway运行**
```powershell
openclaw gateway start
```

2. **配置自动任务**
- 训练状态监控
- 代码自动提交
- 日报生成

### 8.3 长期优化

1. 部署到云服务器
2. 配置更复杂的自动化流程
3. 集成更多通知渠道

---

## 9. 成本考虑

| 方案 | 成本 | 可靠性 |
|------|------|--------|
| 本地PC运行 | 免费 | ⚠️ 需要保持开机 |
| 云服务器 | ¥50-200/月 | ✅ 7x24稳定 |
| 混合方案 | 免费 | ✅ 工作日本地，周末云端 |

---

**维护者**: SkyEdge AI Team
**创建日期**: 2026-03-06
