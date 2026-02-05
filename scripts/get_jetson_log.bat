@echo off
setlocal enabledelayedexpansion

set JETSON_IP=192.168.0.104
set USERNAME=nvidia

set COMMANDS=cd ~/edge_infer ^&^& echo "=== 检查日志文件 ===" ^&^& ls -la logs/ ^&^& echo "=== 最近的日志 ===" ^&^& tail -100 logs/edge_framework.log 2^>^/dev/null ^|^| tail -100 logs/*.log 2^>^/dev/null ^|^| echo "日志文件未找到"

"C:\Windows\System32\OpenSSH\ssh.exe" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null %USERNAME%@%JETSON_IP% "%COMMANDS%"

pause
