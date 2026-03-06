@echo off
setlocal

echo ========================================
echo   Stop OpenClaw Gateway
echo ========================================
echo.

echo [*] Checking for Gateway on port 18789...
netstat -ano | findstr ":18789" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [*] Gateway not running
    goto :end
)

echo [*] Stopping Gateway...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":18789" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    if errorlevel 0 (
        echo [OK] Stopped PID %%a
    ) else (
        echo [ERROR] Failed to stop PID %%a
    )
)

:end
echo.
echo [*] Done
echo.
pause
