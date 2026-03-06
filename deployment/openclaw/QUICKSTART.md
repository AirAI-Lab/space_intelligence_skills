# OpenClaw 快速使用指南

## 当前状态
- OpenClaw 版本: 2026.2.3-1
- Gateway 运行中: http://localhost:18789
- 模型: glm-4.7 (智谱 AI)
- 工作区: d:/github/edge_infer_cloud

## 启动和停止

### 方式一：使用脚本（推荐）

双击运行以下脚本：
- **启动**: `deployment/openclaw/start-gateway.bat`
- **停止**: `deployment/openclaw/stop-gateway.bat`

### 方式二：命令行

```bash
# Windows 启动
cd d:/github/edge_infer_cloud
openclaw gateway --port 18789 --token edge-infer-claw-2026

# 访问 Control UI
start http://localhost:18789
```

### 停止 Gateway
```bash
# 双击 stop-gateway.bat 或
# 按 Ctrl+C
```

## 两种使用模式

### 1. 聊天机器人模式

#### WhatsApp 配置

**方式一：使用脚本（推荐）**
```
双击 deployment/openclaw/login-whatsapp.bat
```

**方式二：命令行**
```bash
# 登录 WhatsApp
openclaw channels login

# 扫描二维码后即可使用
```

#### WebChat 界面
访问 http://localhost:18789，使用内置的 WebChat 界面。

### 2. 自动编程模式

#### CLI 命令
```bash
# 发送消息给 AI
openclaw agent --message "帮我查看 Git 状态"

# 执行编程任务
openclaw agent --message "在 backend 添加一个新的 REST API 端点"
```

#### WebChat 编程
在 http://localhost:18789 中直接输入编程任务：

```
重启 Docker 后端服务
创建一个新的用户管理功能
查看当前项目结构
```

## 常用命令

### 会话管理
```bash
# 查看所有会话
openclaw sessions list

# 查看会话历史
openclaw sessions history

# 创建新会话
openclaw sessions create
```

### Channel 管理
```bash
# WhatsApp 登录
openclaw channels login whatsapp

# WhatsApp 登出
openclaw channels logout whatsapp

# 查看配对状态
openclaw pairing list
```

### 配置管理
```bash
# 查看配置
openclaw config get agents.defaults.model.primary

# 设置模型
openclaw config set agents.defaults.model.primary glm-4

# 诊断问题
openclaw doctor
```

## 自动编程示例

### Docker 管理
```
用户: 重启后端服务
AI: [执行] cd deployment/docker && docker-compose restart backend
服务已重启
```

### Git 操作
```
用户: 创建新分支 feature-auth
AI: [执行] git checkout -b feature-auth
分支已创建并切换
```

### 代码开发
```
用户: 添加用户认证 API
AI: 我将帮你创建用户认证 API...
1. 创建 AuthController.java
2. 创建 AuthService.java
3. 添加 JWT 配置
4. 更新路由
```

## 故障排除

### Gateway 无法启动
```bash
# 检查配置
openclaw doctor

# 重置配置
rm ~/.openclaw/openclaw.json
openclaw configure
```

### WhatsApp 连接问题
```bash
# 重新登录
openclaw channels logout whatsapp
openclaw channels login whatsapp
```

### 模型调用失败
- 检查 API Key: `~/.openclaw/credentials/anthropic.json`
- 确认网络可以访问 open.bigmodel.cn
- 查看 Gateway 日志

## 下一步

1. **配置 WhatsApp**: 使用 `openclaw channels login whatsapp` 扫码登录
2. **测试聊天**: 通过 WhatsApp 或 WebChat 发送测试消息
3. **开始编程**: 尝试让 AI 执行简单的开发任务
4. **自定义技能**: 在 `~/.openclaw/workspace/skills/` 添加项目特定技能

## 相关链接

- [OpenClaw Control UI](http://localhost:18789)
- [项目文档](./README.md)
- [OpenClaw 官方文档](https://docs.openclaw.ai)
