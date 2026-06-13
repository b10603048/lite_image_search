"""
Lite Image Search — Start script
Double-click this file or run: python start.py [--port PORT]
"""

import sys
import os
import webbrowser
import threading
import argparse

# Ensure the app directory is in sys.path (embeddable Python / PyInstaller)
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
os.chdir(APP_DIR)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lite Image Search")
    parser.add_argument("--port", type=int, default=None, help="Server port (default: 6626)")
    args = parser.parse_args()

    import config
    if args.port is not None:
        config.PORT = args.port
    port = config.PORT

    def open_browser():
        """Open browser after a short delay to let server start."""
        import time
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")

    print(f"Lite Image Search — starting on http://localhost:{port}")
    print("Press Ctrl+C to stop.\n")

    # Open browser in background
    threading.Thread(target=open_browser, daemon=True).start()

    # Start uvicorn
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=port, log_level="info")
