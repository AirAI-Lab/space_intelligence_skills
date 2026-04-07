# HEARTBEAT.md

## 📢 心跳任务

### 任务1: Token监控（自动执行）
- ✅ Windows 定时任务每 30 分钟自动检查
- 脚本: `scripts/session_monitor.ps1`
- 触发条件: 会话 > 200KB 或消息 > 30 条
- 自动清理: 保留最后 10 条消息
- 日志位置: `%USERPROFILE%\.openclaw\session_monitor.log`

---

## 使用方法

在此文件中添加需要定时检查的任务，系统会定期读取并执行。

**最后更新**: 2026-04-07 09:33 GMT+8
