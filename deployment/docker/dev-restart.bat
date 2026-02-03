@echo off
REM 开发模式快速重启脚本 (Windows)
REM 用于快速重新构建并重启后端服务

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%\..\..\..

echo ==========================================
echo   云边协同平台 - 开发模式快速重启
echo ==========================================
echo.

REM 检查参数
if "%1"=="" goto :usage
if /i "%1"=="backend" goto :backend
if /i "%1"=="b" goto :backend
if /i "%1"=="training" goto :training
if /i "%1"=="t" goto :training
if /i "%1"=="frontend" goto :frontend
if /i "%1"=="f" goto :frontend
if /i "%1"=="all" goto :all
goto :usage

:backend
echo 🔧 重新构建并重启后端服务...
cd /d "%PROJECT_ROOT%\deployment\docker"
docker-compose build backend
docker-compose up -d backend
echo ✅ 后端服务已重启
echo.
echo 📊 查看后端日志: docker-compose logs -f backend
goto :end

:training
echo 🔧 重新构建并重启训练服务...
cd /d "%PROJECT_ROOT%\deployment\docker"
docker-compose --profile gpu build training
docker-compose --profile gpu up -d training
echo ✅ 训练服务已重启
echo.
echo 📊 查看训练日志: docker-compose logs -f training
goto :end

:frontend
echo 🔧 重新构建并重启前端服务...
cd /d "%PROJECT_ROOT%\deployment\docker"
docker-compose build frontend
docker-compose up -d frontend
echo ✅ 前端服务已重启
goto :end

:all
echo 🔧 重新构建并重启所有服务...
cd /d "%PROJECT_ROOT%\deployment\docker"
docker-compose build
docker-compose up -d
echo ✅ 所有服务已重启
goto :end

:usage
echo 用法: %~nx0 [backend^|training^|frontend^|all]
echo.
echo 选项:
echo   backend, b    - 仅重启后端服务
echo   training, t   - 仅重启训练服务 (需要 GPU)
echo   frontend, f  - 仅重启前端服务
echo   all, a       - 重启所有服务
echo.
echo 示例:
echo   %~nx0 backend     # 修改 Java 代码后使用
echo   %~nx0 training    # 修改 Python 代码后使用
echo   %~nx0 frontend    # 修改 Vue 代码后使用
echo   %~nx0 all         # 修改多个服务后使用
goto :end

:end
