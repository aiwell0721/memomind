@echo off
title MemoMind DEV - 开发模式
chcp 65001 >nul

echo ============================================
echo   MemoMind - 开发模式  v3.0.0
echo ============================================
echo.

:: 切换到项目目录
cd /d "%~dp0"

:: 数据库：项目目录（dev）
set "MEMOMIND_DB_PATH=%~dp0memomind.db"

:: 启动开发服务器
echo [1/2] 启动开发服务器 (DB: %MEMOMIND_DB_PATH%)...
start "MemoMind-Dev" cmd /c "python -m uvicorn core.api_server:create_app --factory --host 127.0.0.1 --port 8000"

:: 等待服务就绪
echo [2/2] 等待服务就绪...
:wait_loop
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if %errorlevel% neq 0 goto wait_loop

:: 打开浏览器
start http://127.0.0.1:8000

echo.
echo ============================================
echo   MemoMind DEV 已启动！
echo.
echo   模式:      开发模式 (dev)
echo   本地地址:  http://127.0.0.1:8000
echo   API 文档:  http://127.0.0.1:8000/api/docs
echo   数据库:    %MEMOMIND_DB_PATH%
echo.
echo   停止服务：关闭 "MemoMind-Dev" 命令行窗口
echo ============================================
echo.
pause >nul
