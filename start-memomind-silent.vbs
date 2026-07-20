' MemoMind 静默启动 v3.0.0
' 后台启动 REST API (8000)
' 配合 Windows 计划任务使用，实现开机自启

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strProjectDir = fso.GetParentFolderName(WScript.ScriptFullName)
strPython = strProjectDir & "\.venv\Scripts\python.exe"

' 环境变量：Prod 模式使用 ~/.memomind/memomind.db
Set objEnv = WshShell.Environment("PROCESS")

' 启动 REST API 服务器（prod 模式，~/.memomind/memomind.db）
strCmd = "python -m uvicorn core.api_server:create_app --factory --host 127.0.0.1 --port 8000"
WshShell.Run "cmd /c " & strCmd, 0, False
