"""
DreamingService 惰性导入测试

验证 `sentence_transformers` 不在模块导入时加载，
避免 ARM64 Windows 上 import torch 拖慢服务启动（约 2 分钟）。
"""
import subprocess
import sys
from pathlib import Path


def test_import_dreaming_service_does_not_load_sentence_transformers():
    """导入 dreaming_service 不应触发 sentence_transformers 加载。

    用子进程隔离验证：因为一旦 sentence_transformers 被加载进当前
    sys.modules，就无法再卸载，必须用干净进程断言导入副作用。
    """
    project_root = Path(__file__).resolve().parent.parent
    code = (
        "import sys\n"
        "from core import dreaming_service\n"
        "print('LOADED' if 'sentence_transformers' in sys.modules else 'NOT_LOADED')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(project_root),
        timeout=60,
    )
    assert result.returncode == 0, f"子进程导入失败: {result.stderr}"
    assert result.stdout.strip() == "NOT_LOADED", (
        "sentence_transformers 在模块导入时被加载，惰性导入失效"
    )
