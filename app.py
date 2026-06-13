"""
Lite Image Search — pywebview desktop entry point
Run as: python app.py [--port PORT] [--server]
  --port   Server port (default: 6626)
  --server Run as localhost server only (no pywebview window)
"""

import sys
import os
import threading
import argparse
import traceback
from datetime import datetime

# Ensure the app directory is in sys.path (embeddable Python / PyInstaller)
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
os.chdir(APP_DIR)


def _log_error(msg: str):
    """Append error message to data/error.log (visible even with console=False)."""
    try:
        log_dir = os.path.join(APP_DIR, "data")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "error.log")
        with open(log_path, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {msg}\n")
    except Exception:
        pass


# Catch uncaught exceptions and log them
def _global_excepthook(exc_type, exc_value, exc_tb):
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _log_error(f"UNCAUGHT EXCEPTION:\n{msg}")
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _global_excepthook

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Lite Image Search")
    parser.add_argument("--port", type=int, default=None, help="Server port (default: 6626)")
    parser.add_argument("--server", action="store_true", help="Run as localhost server only (no pywebview window)")
    args = parser.parse_args()

    import config
    if args.port is not None:
        config.PORT = args.port
    port = config.PORT

    # ── Server-only mode (same as start.py) ──
    if args.server:
        import webbrowser
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")
        print(f"Lite Image Search — starting on http://localhost:{port}")
        print("Press Ctrl+C to stop.\n")
        threading.Thread(target=open_browser, daemon=True).start()
        uvicorn.run("main:app", host=config.HOST, port=port, log_level="info")
        return

    # ── pywebview desktop mode ──
    try:
        import webview
    except Exception as e:
        _log_error(f"webview import failed: {e}\n{traceback.format_exc()}")
        # Fallback: just start the server and open browser
        import webbrowser
        def open_browser():
            import time
            time.sleep(2)
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=open_browser, daemon=True).start()
        uvicorn.run("main:app", host="127.0.0.1", port=port, log_level="info")
        return

    # We bind to 127.0.0.1 for the pywebview scenario (no need to expose on LAN)
    server_host = "127.0.0.1"

    # Start FastAPI on a daemon thread; when the window closes the process exits.
    server_thread = threading.Thread(
        target=uvicorn.run,
        args=("main:app",),
        kwargs={"host": server_host, "port": port, "log_level": "warning"},
        daemon=True,
    )
    server_thread.start()

    # Give the server a moment to bind before opening the window
    import time
    time.sleep(1.0)

    # Verify server is running
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/stats", timeout=3)
    except Exception as e:
        _log_error(f"Server health check failed: {e}")

    url = f"http://localhost:{port}"

    # Create the pywebview window
    try:
        window = webview.create_window(
            title="Lite Image Search",
            url=url,
            width=1280,
            height=800,
            min_size=(800, 600),
        )
        # webview.start blocks until the window is closed
        webview.start()
    except Exception as e:
        _log_error(f"webview failed: {e}\n{traceback.format_exc()}")
        # Fallback: open browser
        import webbrowser
        webbrowser.open(url)
        uvicorn.run("main:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log_error(f"STARTUP FAILED:\n{traceback.format_exc()}")
        if not getattr(sys, 'frozen', False):
            raise
