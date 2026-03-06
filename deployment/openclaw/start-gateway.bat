@echo off
REM OpenClaw Gateway Startup Script
REM Auto-detects and uses current model configuration

setlocal enabledelayedexpansion

REM Set Zhipu AI environment variables
set OPENCLAW_ANTHROPIC_API_KEY=c0218f870d074d909251eccbf6b552e6.MjpUXG6TaNwTN1t3
set OPENCLAW_ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic

REM Also set standard Anthropic variables for compatibility
set ANTHROPIC_API_KEY=c0218f870d074d909251eccbf6b552e6.MjpUXG6TaNwTN1t3
set ANTHROPIC_AUTH_TOKEN=c0218f870d074d909251eccbf6b552e6.MjpUXG6TaNwTN1t3
set ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic

REM Set console code page to UTF-8
chcp 65001 >nul 2>&1

echo ========================================
echo   OpenClaw Gateway Startup
echo ========================================
echo.

REM Clean old lock files first
echo [*] Cleaning old lock files...
if exist "C:\Users\wennu\.openclaw\agents\main\sessions\*.lock" (
    del /F /Q "C:\Users\wennu\.openclaw\agents\main\sessions\*.lock" 2>nul
    echo [OK] Lock files cleaned
) else (
    echo [*] No lock files found
)

echo.
echo [*] Environment configured:
echo     API Endpoint: https://open.bigmodel.cn/api/anthropic
echo.

REM Check if openclaw is installed
where openclaw >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] ERROR: openclaw command not found!
    echo [!] Please install OpenClaw first:
    echo [!]     npm install -g openclaw
    echo.
    pause
    exit /b 1
)

REM Check if Gateway is already running
echo [*] Checking if Gateway is already running...
netstat -ano | findstr ":18789" | findstr "LISTENING" >nul 2>&1
if %errorlevel% == 0 (
    echo [!] Gateway is already running on port 18789
    echo.
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":18789" ^| findstr "LISTENING"') do (
        echo     Process ID: %%a
        echo     To stop it, run: stop-gateway.bat
    )
    echo.
    echo [*] Access: http://localhost:18789?token=edge-infer-claw-2026
    echo.
    pause
    exit /b 0
)

echo [*] Starting Gateway...
echo.

REM Change to project directory
cd /d d:\github\edge_infer_cloud

echo ========================================
echo   Gateway Configuration
echo ========================================
echo   Port:    18789
echo   Token:   edge-infer-claw-2026
echo   Model:   GLM-5 (with GLM-4.7 fallback)
echo   Press Ctrl+C to stop
echo ========================================
echo.

openclaw gateway

REM Cleanup on exit
set EXIT_CODE=%errorlevel%
echo.
echo [*] Gateway stopped (exit code: %EXIT_CODE%)
echo.
pause
