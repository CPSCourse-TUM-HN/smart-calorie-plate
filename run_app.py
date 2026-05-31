"""Smart Plate 桌面应用启动器。

一个自包含的桌面 app：
  1. 在后台线程启动 FastAPI（uvicorn），它同时托管：
       - REST API（/foods、/meal/*、/api/*）
       - 前端静态站点（smart-plate-ui/out，由 `npm run build` 生成）
  2. 等后端 /api/health 就绪后，再打开 PyWebView 窗口指向同一个本地端口。

这样前端与后端同源，彻底避免"打包后用 file:// 打开导致 JS 不加载、页面无法跳转"的问题。

首次使用请先构建前端：
    cd smart-plate-ui && npm install && npm run build
然后：
    python run_app.py
"""

import sys
import threading
import time
import urllib.request
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "src" / "calorie_plate"
FRONTEND_OUT = ROOT / "smart-plate-ui" / "out"


def _start_backend() -> None:
    """在当前进程内启动 uvicorn（不另起子进程，便于一键打包）。"""
    # main.py 用的是 `from database import ...` 这种平铺 import，
    # 因此要把后端目录加入 sys.path 并以它为基准。
    sys.path.insert(0, str(BACKEND_DIR))
    import uvicorn

    from main import app  # noqa: E402  （path 注入后才能 import）

    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def _wait_until_ready(timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def main() -> None:
    if not FRONTEND_OUT.is_dir():
        print(
            "⚠️  未找到前端静态文件：smart-plate-ui/out\n"
            "    请先构建前端：cd smart-plate-ui && npm install && npm run build\n"
            "    （窗口仍会打开，但只能访问 API 文档 /docs）"
        )

    backend = threading.Thread(target=_start_backend, daemon=True)
    backend.start()

    if not _wait_until_ready():
        print("❌ 后端启动超时，请检查依赖是否安装完整（fastapi/uvicorn/ultralytics 等）。")
        return

    import webview

    webview.create_window(
        title="Smart Plate",
        url=BASE_URL,
        width=1280,
        height=800,
        background_color="#09090b",
    )
    # debug=True 开启 Web Inspector（右键→检查元素），方便排查前端问题。
    webview.start(debug=True)


if __name__ == "__main__":
    main()
