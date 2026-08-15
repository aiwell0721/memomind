# MemoMind 本地服务自动拉起脚本
# 用法：powershell -ExecutionPolicy Bypass -File start-memomind.ps1
# 幂等：检查 8000 端口，已运行则跳过；未运行则拉起后端 + 健康检查

$ErrorActionPreference = 'Stop'

# 项目目录 = 脚本所在目录（自动检测，无需硬编码）
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BindAddr = '127.0.0.1'
$Port = 8000
$HealthUrl = "http://${BindAddr}:${Port}/api/health"

Write-Host "=== MemoMind 服务拉起 ===" -ForegroundColor Cyan
Write-Host "[信息] 项目目录: $ProjectDir"

# ── 1. 幂等检查：端口是否已被监听 ─────────────────────────
$listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listening) {
    Write-Host "[跳过] 端口 $Port 已有服务在运行" -ForegroundColor Yellow
    try {
        $health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 5
        Write-Host "[状态] 数据库: $($health.database.db_path)" -ForegroundColor Green
        Write-Host "[状态] 笔记数: $($health.database.note_count)" -ForegroundColor Green
        Write-Host "[状态] 访问: http://${BindAddr}:${Port}" -ForegroundColor Green
    } catch {
        Write-Host "[警告] 端口被占用但健康检查失败，可能被其他程序占用" -ForegroundColor Yellow
    }
    exit 0
}

# ── 2. 选择 Python（优先 .venv，回退全局） ────────────────
$VenvPython = Join-Path $ProjectDir '.venv\Scripts\python.exe'
$Python = if (Test-Path $VenvPython) { $VenvPython } else { 'python' }
Write-Host "[信息] Python: $Python"

# ── 3. 启动后端（后台隐藏窗口，日志写 logs/） ─────────────
$LogDir = Join-Path $ProjectDir 'logs'
$null = New-Item -ItemType Directory -Force -Path $LogDir
$OutLog = Join-Path $LogDir 'memomind.out.log'
$ErrLog = Join-Path $LogDir 'memomind.err.log'

Write-Host "[信息] 启动后端 (http://${BindAddr}:${Port})..."
$Process = Start-Process -FilePath $Python `
    -ArgumentList '-m','uvicorn','core.api_server:create_app','--factory','--host',$BindAddr,'--port',"$Port" `
    -WorkingDirectory $ProjectDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -PassThru

Write-Host "[信息] 已启动 PID $($Process.Id)"

# ── 4. 健康检查（最多 30 秒） ──────────────────────────────
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 1
    if ($Process.HasExited) {
        Write-Host "[失败] 进程启动后立即退出，查看日志:" -ForegroundColor Red
        Write-Host "  标准输出: $OutLog" -ForegroundColor Red
        Write-Host "  错误输出: $ErrLog" -ForegroundColor Red
        if (Test-Path $ErrLog) { Get-Content $ErrLog -Tail 20 }
        exit 1
    }
    try {
        $health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3
        Write-Host "[成功] 服务已就绪（耗时 ${i}s）" -ForegroundColor Green
        Write-Host "[成功] 数据库: $($health.database.db_path)" -ForegroundColor Green
        Write-Host "[成功] 笔记数: $($health.database.note_count)" -ForegroundColor Green
        Write-Host "[成功] 访问: http://${BindAddr}:${Port}" -ForegroundColor Green
        exit 0
    } catch {}
}

Write-Host "[超时] 30 秒内未就绪，查看日志 $ErrLog" -ForegroundColor Yellow
exit 1
