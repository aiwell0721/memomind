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
    "%~dp0.venv\Scripts\python.exe" -c "import fastapi, uvicorn, pydantic_core, sentence_transformers" 2>nul
    if not errorlevel 1 set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
)
if "%PYTHON_EXE%"=="" (
    python -c "import fastapi, uvicorn, pydantic_core, sentence_transformers" 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    ) else (
        echo [错误] 未找到可用的 Python 环境，请先安装依赖:
        echo   pip install -r requirements.txt
        pause >nul
        exit /b 1
    )
)
echo [OK] Python: %PYTHON_EXE%

:: ── Prod 模式：不设 MEMOMIND_DB_PATH，默认 ~/.memomind/memomind.db ──
echo [1/2] 启动生产服务...
start "MemoMind-Prod" cmd /k "%PYTHON_EXE% -m uvicorn core.api_server:create_app --factory --host 127.0.0.1 --port 8000"

echo [2/2] 等待服务就绪...
:wait_loop
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if %errorlevel% neq 0 goto wait_loop

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
