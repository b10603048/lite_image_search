#!/usr/bin/env bash
# ──────────────────────────────────────────────
# Lite Image Search — Linux / Mac Launcher
# Usage: ./start.sh [port]
# ──────────────────────────────────────────────

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/venv"

# ── Check Python3 ──
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "錯誤：找不到 Python3。請先安裝 Python 3.10+"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv"
    echo "  macOS (Homebrew): brew install python3"
    exit 1
fi

# Verify Python version >= 3.10
PY_VER=$($PYTHON -c "import sys; print(sys.version_info[:2])")
PY_MAJOR=$(echo "$PY_VER" | sed 's/(//;s/,.*//')
PY_MINOR=$(echo "$PY_VER" | sed 's/.*,//;s/).*//')
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo "錯誤：Python 版本過舊 (需要 3.10+，目前 $PY_MAJOR.$PY_MINOR)"
    exit 1
fi

# ── Create venv if needed ──
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/2] 建立虛擬環境..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# ── Install requirements if needed ──
VENV_PYTHON="$VENV_DIR/bin/python"
MARKER="$VENV_DIR/installed.flag"
if [ ! -f "$MARKER" ]; then
    echo "[2/2] 安裝套件（首次執行，請稍候）..."
    "$VENV_PYTHON" -m pip install --upgrade pip -q
    "$VENV_PYTHON" -m pip install -r "$APP_DIR/requirements.txt"
    touch "$MARKER"
    echo "[OK] 套件安裝完成"
else
    echo "[OK] 虛擬環境已就緒"
fi

# ── Port argument ──
PORT_ARG=""
if [ $# -ge 1 ]; then
    PORT_ARG="--port $1"
fi

# ── Launch ──
echo ""
echo "============================================"
echo "  Lite Image Search"
if [ -n "$PORT_ARG" ]; then
    echo "  http://localhost:$1"
else
    echo "  http://localhost:6626"
fi
echo "  按 Ctrl+C 停止"
echo "============================================"
echo ""

cd "$APP_DIR"
exec "$VENV_PYTHON" "$APP_DIR/start.py" $PORT_ARG
