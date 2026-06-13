"""
Lite Image Search — Configuration
"""

import os
import sys

# ── Server ──
HOST = "0.0.0.0"
PORT = int(os.environ.get("LIS_PORT", "6626"))

# ── Gemini API ──
GEMINI_MODEL = "gemini-embedding-2"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
EMBEDDING_DIMENSION = 768  # output_dimensionality (Matryoshka truncation)

# ── Paths ──
# When running as PyInstaller bundle, use the exe's directory, not the temp extraction dir
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    _MEIPASS = sys._MEIPASS  # PyInstaller temp extraction dir (contains bundled static/)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _MEIPASS = BASE_DIR
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "lite_image_search.db")
ORIGINAL_DIR = os.path.join(DATA_DIR, "original")
CONVERTED_DIR = os.path.join(DATA_DIR, "converted")
THUMBNAIL_DIR = os.path.join(DATA_DIR, "thumbnails")

# ── Static files (frontend) ──
# PyInstaller bundles static/ into _MEIPASS; non-frozen uses BASE_DIR
STATIC_DIR = os.path.join(_MEIPASS, "static")

# ── Thumbnail ──
THUMBNAIL_MAX_SIZE = 800  # max width/height in pixels

# ── API Key persistence (plain text file, separate from DB) ──
API_KEY_PATH = os.path.join(DATA_DIR, "api_key.txt")


def get_api_key() -> str:
    """Load API key from file or environment variable."""
    if os.path.exists(API_KEY_PATH):
        with open(API_KEY_PATH, "r", encoding="utf-8") as f:
            key = f.read().strip()
            if key:
                return key
    return os.environ.get("GEMINI_API_KEY", "")


def set_api_key(key: str) -> None:
    """Save API key to a plain text file."""
    os.makedirs(os.path.dirname(API_KEY_PATH), exist_ok=True)
    with open(API_KEY_PATH, "w", encoding="utf-8") as f:
        f.write(key.strip())


def norm_path(path: str) -> str:
    """Normalize path to forward slashes for cross-platform DB storage.
    Both Windows and Linux handle '/' correctly in os.path.join."""
    if not path:
        return path
    return path.replace("\\", "/")


def ensure_dirs():
    """Create data directories if they don't exist."""
    for d in [DATA_DIR, ORIGINAL_DIR, CONVERTED_DIR, THUMBNAIL_DIR]:
        os.makedirs(d, exist_ok=True)
