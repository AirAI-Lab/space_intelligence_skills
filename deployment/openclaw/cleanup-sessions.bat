@echo off
REM OpenClaw Session Cleanup Script
REM Cleans session files older than 7 days

setlocal

chcp 65001 >nul 2>&1

echo ========================================
echo   OpenClaw Session Cleanup
echo ========================================
echo.

set SESSIONS_DIR=C:\Users\wennu\.openclaw\agents\main\sessions
set BACKUP_DIR=%SESSIONS_DIR%\backup
set DAYS_TO_KEEP=7

echo [*] Sessions Directory: %SESSIONS_DIR%
echo [*] Keeping sessions newer than: %DAYS_TO_KEEP% days
echo.

REM Create backup directory if not exists
if not exist "%BACKUP_DIR%" (
    mkdir "%BACKUP_DIR%"
    echo [OK] Created backup directory
)

REM Backup current sessions.json
if exist "%SESSIONS_DIR%\sessions.json" (
    copy /Y "%SESSIONS_DIR%\sessions.json" "%BACKUP_DIR%\sessions.json.%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%.json" >nul
    echo [OK] Backed up sessions.json
)

REM Count total files
set TOTAL_COUNT=0
for /f %%a in ('dir /b "%SESSIONS_DIR%\*.jsonl" 2^>nul ^| find /c /v ""') do set TOTAL_COUNT=%%a

echo [*] Found %TOTAL_COUNT% session files

REM Delete old session files
set DELETED_COUNT=0
for /f "delims=" %%f in ('dir /b /od "%SESSIONS_DIR%\*.jsonl" 2^>nul') do (
    forfiles /P "%SESSIONS_DIR%" /M "%%f" /D -%DAYS_TO_KEEP% 2>nul
    if not errorlevel 1 (
        del /F /Q "%SESSIONS_DIR%\%%f" 2>nul
        if exist "%SESSIONS_DIR%\%%f" (
            echo [SKIP] Failed to delete: %%f
        ) else (
            echo [DELETE] %%f
            set /a DELETED_COUNT+=1
        )
    )
)

echo.
echo [*] Deleted %DELETED_COUNT% old session files
echo [*] Remaining session files: set /a REMAINING=%TOTAL_COUNT%-%DELETED_COUNT%
echo.
echo [*] Cleanup complete
echo.
pause
