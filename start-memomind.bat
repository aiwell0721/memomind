@echo off
title MemoMind - 生产模式
chcp 65001 >nul

echo ============================================
echo   MemoMind - 生产模式  v3.0.0
echo ============================================
echo.

cd /d "%~dp0"

:: ── 选择 Python 解释器 ──
:: 优先级：项目 .venv > PATH 中的 python
set "PYTHON_EXE="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
)
if "%PYTHON_EXE%"=="" (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    ) else (
        echo [错误] 未找到 Python，请先安装:
        echo   https://www.python.org/downloads/
        pause >nul
        exit /b 1
    )
)
echo [OK] Python: %PYTHON_EXE%

:: ── Prod 模式：不设 MEMOMIND_DB_PATH，默认 ~/.memomind/memomind.db ──
echo [1/2] 启动生产服务...
start "MemoMind-Prod" cmd /k "%PYTHON_EXE% -m uvicorn core.api_server:create_app --factory --host 127.0.0.1 --port 8000"

echo [2/2] 等待服务就绪...
set /a WAIT_COUNT=0
:wait_loop
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if not errorlevel 1 goto ready
set /a WAIT_COUNT+=1
if %WAIT_COUNT% lss 30 goto wait_loop
echo [失败] 服务 60 秒内未就绪，请检查 MemoMind-Prod 窗口输出
pause >nul
exit /b 1
:ready

start http://127.0.0.1:8000

echo.
echo ============================================
echo   MemoMind PROD 已启动！
echo.
echo   模式:      生产模式 (prod)
echo   本地地址:  http://127.0.0.1:8000
echo   数据库:    %USERPROFILE%\.memomind\memomind.db
echo.
echo   停止服务：关闭 "MemoMind-Prod" 命令行窗口
echo ============================================
echo.
pause >nul
