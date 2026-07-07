"""Smart Plate desktop application launcher.

A self-contained desktop app:
  1. Starts FastAPI (uvicorn) on a background thread. The server hosts both:
       - the REST API (/foods, /meal/*, /api/*)
       - the static frontend site (smart-plate-ui/out, produced by `npm run build`)
  2. Waits until /api/health responds, then opens a PyWebView window pointed
     at the same local port.

Serving the frontend and backend from the same origin avoids the classic
packaged-app failure mode where pages opened via file:// cannot load JS or
navigate between routes.

Before the first run, build the frontend:
    cd smart-plate-ui && npm install && npm run build
Then:
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
    """Run uvicorn inside the current process (no subprocess, easier to package)."""
    # main.py uses flat imports such as `from database import ...`, so the
    # backend directory must be on sys.path before importing it.
    sys.path.insert(0, str(BACKEND_DIR))
    import uvicorn

    from main import app  # noqa: E402  (importable only after the path insert)

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
            "Warning: frontend static files not found at smart-plate-ui/out\n"
            "    Build the frontend first: cd smart-plate-ui && npm install && npm run build\n"
            "    (The window will still open, but only the API docs at /docs will be available.)"
        )

    backend = threading.Thread(target=_start_backend, daemon=True)
    backend.start()

    if not _wait_until_ready():
        print(
            "Error: backend startup timed out. "
            "Check that all dependencies are installed (fastapi/uvicorn/ultralytics, etc.)."
        )
        return

    import webview

    webview.create_window(
        title="Smart Plate",
        url=BASE_URL,
        width=1280,
        height=800,
        background_color="#09090b",
    )
    # debug=True enables the Web Inspector (right click -> Inspect Element)
    # for troubleshooting frontend issues inside the WebView.
    webview.start(debug=True)


if __name__ == "__main__":
    main()
