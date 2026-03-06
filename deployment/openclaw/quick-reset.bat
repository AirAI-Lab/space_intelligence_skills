@echo off
REM Quick Session Reset Script
REM Use this when context window exceeded error occurs

setlocal

chcp 65001 >nul 2>&1

echo ========================================
echo   Quick Session Reset
echo ========================================
echo.

set SESSIONS_DIR=C:\Users\wennu\.openclaw\agents\main\sessions

echo [*] Stopping Gateway...
taskkill /F /IM node.exe /FI "WINDOWTITLE eq openclaw*" >nul 2>&1
timeout /t 2 >nul

echo [*] Clearing current session...
for /f "delims=" %%f in ('dir /b "%SESSIONS_DIR%\*.jsonl" 2^>nul') do (
    echo [  ] Clearing: %%f
    echo [] > "%SESSIONS_DIR%\%%f"
)

echo [*] Resetting sessions.json...
echo {} > "%SESSIONS_DIR%\sessions.json"

echo [*] Clearing dedup cache...
del /F /Q "C:\Users\wennu\.openclaw\agents\main\dedup.sqlite" 2>nul

echo.
echo [OK] Session reset complete
echo [*] Starting Gateway...
start "" cmd /c "cd /d D:\github\edge_infer_cloud\deployment\openclaw && start-gateway.bat"
echo.
timeout /t 3 >nul
echo [*] Done! Please send a new message to start fresh.
echo.
pause
