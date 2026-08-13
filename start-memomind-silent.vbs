' MemoMind 静默启动 v3.1.0
' 后台启动 REST API (8000) - 开机自启用
' 修正：设置工作目录 + 依赖完整性检测

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strProjectDir = "C:\prj_claude\projects\memomind"

' 选择 Python：优先 .venv（完整依赖），回退全局
strPython = ""
If fso.FileExists(strProjectDir & "\.venv\Scripts\python.exe") Then
    strPython = strProjectDir & "\.venv\Scripts\python.exe"
End If

' 回退全局 Python
If strPython = "" Then
    strPython = "python"
End If

' 设置工作目录到项目路径（关键！否则模块找不到）
WshShell.CurrentDirectory = strProjectDir

' 启动 REST API 服务器（prod 模式，~/.memomind/memomind.db）
strCmd = strPython & " -m uvicorn core.api_server:create_app --factory --host 127.0.0.1 --port 8000"
WshShell.Run "cmd /c " & strCmd, 0, False
