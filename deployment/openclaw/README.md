# OpenClaw + edge_infer_cloud 集成指南

本项目集成 OpenClaw AI 助手，支持自动编程和飞书聊天机器人两大功能。

## 最新更新 (2026-02-08)

### ✅ 已修复问题
- **Session 文件锁**: 清理了锁文件，解决多实例冲突
- **API Key 更新**: 使用新的智谱 AI API Key
- **模型配置优化**: 移除无效的 anthropic/glm-4.7 fallback
- **飞书集成**: 添加飞书频道支持

### 📋 当前配置
- **API Key**: `c0218f870d074d909251eccbf6b552e6.MjpUXG6TaNwTN1t3`
- **主模型**: `zai/glm-4.7` (智谱 AI GLM-4.7)
- **备用模型**: `anthropic/claude-3-5-sonnet-20241022`, `zai/glm-4.7-flash`
- **飞书应用**: App ID `cli_a90c7b3390789cbd`

## 功能概览

### 1. 自动编程功能
- AI 辅助代码编写和审查
- 自动执行开发任务
- Docker 服务管理
- Git 操作自动化

### 2. 聊天机器人功能
- WhatsApp 交互（电脑端 + 手机端）
- WebChat 界面
- 多模型支持（glm-4.7）

## 快速开始

### 安装状态
- OpenClaw 版本: 2026.2.3-1
- 配置文件: `~/.openclaw/openclaw.json`
- 工作区: `d:/github/edge_infer_cloud`

### 启动 Gateway

```bash
# 启动 OpenClaw Gateway (Windows)
cd d:/github/edge_infer_cloud
openclaw gateway --port 18789 --token edge-infer-claw-2026

# 访问 Control UI
start http://localhost:18789
```

### WhatsApp 配置

#### 方法一：使用登录脚本（推荐）

```bash
# 双击运行登录脚本
deployment/openclaw/login-whatsapp.bat

# 扫描二维码后，服务将自动运行
```

#### 方法二：命令行登录

```bash
# 登录 WhatsApp
openclaw channels login

# 扫描二维码后，服务将自动运行
```

#### 方法三：WhatsApp Web 电脑端

1. 打开浏览器访问 https://web.whatsapp.com
2. 用手机 WhatsApp 扫码登录
3. 同时运行 OpenClaw Gateway

## 使用方式

### WhatsApp 交互

发送消息到 WhatsApp（与 AI 配对的号码）：

```
# 聊天功能
你好，帮我写一个 Python 脚本

# 自动编程任务
在 edge_infer_cloud 项目中添加一个新的 API 端点

# Docker 管理
重启后端服务

# Git 操作
创建一个新的功能分支
```

### WebChat 界面

访问 http://localhost:18789 打开 WebChat 界面。

### CLI 命令

```bash
# 发送消息给 AI
openclaw agent --message "帮我查看当前 Git 状态"

# 发送到 WhatsApp
openclaw message send --to +1234567890 --message "Hello from OpenClaw"

# 查看会话状态
openclaw sessions list
```

## 智能编程助手

OpenClaw 已配置以下技能：

1. **edge-infer 技能**
   - 项目结构理解
   - Docker 服务管理
   - API 开发辅助
   - Git 操作自动化

2. **可用工具**
   - `bash`: 执行 shell 命令
   - `read`: 读取文件
   - `write`: 写入文件
   - `edit`: 编辑文件
   - `browser`: Web 浏览
   - `sessions_*`: 会话管理

## 配置详情

### 模型配置
- **Provider**: 智谱 AI (BigModel)
- **模型**: glm-4.7 (glm-4-plus)
- **Base URL**: https://open.bigmodel.cn/api/paas/v4
- **上下文**: 128K tokens

### 渠道配置
- **WhatsApp**: 启用，开放 DM 策略
- **WebChat**: 启用，允许所有来源

### 工具配置
- 工作目录: `d:/github/edge_infer_cloud`
- 允许工具: bash, read, write, edit, browser, sessions

## 常用命令

### Gateway 管理
```bash
# 启动
openclaw gateway --port 18789

# 停止
openclaw gateway stop

# 重启
openclaw gateway restart

# 查看状态
openclaw doctor
```

### 会话管理
```bash
# 列出所有会话
openclaw sessions list

# 查看会话历史
openclaw sessions history <session_id>

# 发送消息到会话
openclaw sessions send <session_id> "消息内容"
```

### Channel 管理
```bash
# 登录 WhatsApp
openclaw channels login

# 登出
openclaw channels logout

# 查看配对状态
openclaw pairing list
```

## 自动编程示例

### 示例 1：添加新 API
```
用户: 在后端添加一个用户管理 API

AI: 我将帮你创建用户管理 API...
1. 创建 UserController.java
2. 创建 UserService.java
3. 创建 UserRepository.java
4. 添加路由配置
```

### 示例 2：Docker 管理
```
用户: 重启后端服务

AI: 执行命令: cd deployment/docker && docker-compose restart backend
服务已重启
```

### 示例 3：Git 操作
```
用户: 创建功能分支 feature-ai-assistant

AI: 执行命令: git checkout -b feature-ai-assistant
分支已创建
```

## 故障排除

### Gateway 无法启动
```bash
# 检查配置
openclaw doctor

# 查看日志
openclaw gateway --verbose
```

### WhatsApp 连接问题
```bash
# 重新登录
openclaw channels logout
openclaw channels login
```

### 模型调用失败
- 检查 API Key 是否有效
- 确认网络可以访问 open.bigmodel.cn
- 查看日志中的错误信息

## 下一步

- [ ] 配置 HTTPS（生产环境）
- [ ] 设置用户权限管理
- [ ] 添加更多自定义技能
- [ ] 集成 CI/CD 流程

## 相关资源

- [OpenClaw 官方文档](https://docs.openclaw.ai)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [智谱 AI 文档](https://open.bigmodel.cn/dev/api)
