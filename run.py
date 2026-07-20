"""
MemoMind Windows 启动入口
用于 PyInstaller 打包为一键部署包
"""

import os
import sys
import webbrowser
import threading
import time
from pathlib import Path

# 确保项目根在 sys.path 中
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _open_browser(host: str, port: int, delay: float = 2.0):
    """延迟打开浏览器"""
    time.sleep(delay)
    url = f"http://{host}:{port}"
    print(f"Opening browser: {url}")
    webbrowser.open(url)


def main():
    import uvicorn
    from core.api_server import create_app

    # 配置
    host = os.environ.get("MEMOMIND_HOST", "127.0.0.1")
    port = int(os.environ.get("MEMOMIND_PORT", "8000"))
    
    # ========== 数据库路径决议 ==========
    # 优先级：
    #   1) 环境变量 MEMOMIND_DB_PATH 显式指定
    #   2) 按运行模式走默认路径（dev vs prod）
    #   3) 旧路径自动迁移
    
    _frozen = getattr(sys, 'frozen', False)
    
    env_db = os.environ.get("MEMOMIND_DB_PATH")
    if env_db:
        db_path = env_db
    elif _frozen:
        # ── Prod 模式（.exe）→ ~/.memomind/memomind.db ──
        _exe_dir = os.path.dirname(sys.executable)
        _target_path = str(Path.home() / ".memomind" / "memomind.db")
        _target_dir = str(Path.home() / ".memomind")

        if os.path.isfile(_target_path):
            db_path = _target_path
            print(f"[MemoMind] Using database: {_target_path}")
        else:
            # 旧路径迁移（按优先级搜索）：
            #   1) exe 同级 data/memomind.db
            #   2) exe 同级 memomind.db
            #   3) ~/memomind.db（v3.0 旧默认位置，统一前）
            _old_data_db = os.path.join(_exe_dir, "data", "memomind.db")
            _old_root_db = os.path.join(_exe_dir, "memomind.db")
            _old_home_db = str(Path.home() / "memomind.db")
            _src = None
            _src_label = None
            if os.path.isfile(_old_data_db):
                _src = _old_data_db
                _src_label = "data/memomind.db"
            elif os.path.isfile(_old_root_db):
                _src = _old_root_db
                _src_label = "memomind.db (exe 同级)"
            elif os.path.isfile(_old_home_db):
                _src = _old_home_db
                _src_label = "~/memomind.db (v3.0 旧默认)"

            if _src:
                import shutil
                os.makedirs(_target_dir, exist_ok=True)
                shutil.copy2(_src, _target_path)
                # 也迁移 AI 配置文件
                _old_ai_json = os.path.join(os.path.dirname(_src), "memomind.json")
                _new_ai_json = os.path.join(_target_dir, "memomind.json")
                if os.path.isfile(_old_ai_json) and not os.path.isfile(_new_ai_json):
                    shutil.copy2(_old_ai_json, _new_ai_json)
                db_path = _target_path
                print(f"[MemoMind] Migrated {_src_label} -> {_target_path}")
            else:
                db_path = _target_path
                print(f"[MemoMind] Creating new database: {_target_path}")
    else:
        # ── Dev 模式（python run.py）→ data/memomind.db ──
        _data_dir = os.path.join(_project_root, "data")
        _standard = os.path.join(_data_dir, "memomind.db")

        if os.path.isfile(_standard):
            db_path = _standard
            print(f"[MemoMind] Using database: {_standard}")
        else:
            # 可选：从项目根旧库迁移
            _legacy = os.path.join(_project_root, "memomind.db")
            if os.path.isfile(_legacy):
                import shutil
                os.makedirs(_data_dir, exist_ok=True)
                shutil.copy2(_legacy, _standard)
                db_path = _standard
                print(f"[MemoMind] Migrated memomind.db (项目根) -> {_standard}")
            else:
                db_path = _standard
                print(f"[MemoMind] Creating new database: {_standard}")

    # 确保目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print(f"[MemoMind] v3.0.0")
    print(f"{'='*40}")
    print(f"  Data:     {db_path}")
    print(f"  Address:  http://{host}:{port}")
    print(f"  API docs: http://{host}:{port}/api/docs")
    print(f"{'='*40}")
    print()

    # 自动打开浏览器（后台线程）
    threading.Thread(target=_open_browser, args=(host, port), daemon=True).start()

    # 启动服务器
    app = create_app(db_path=db_path)
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
