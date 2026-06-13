# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Lite Image Search — builds a single .exe
Usage:  python -m PyInstaller lite_image_search.spec --noconfirm

Bundle strategy for native dependencies:
  - cairosvg → cairocffi ships libcairo-2.dll on Windows pip install
  - pillow-heif → ships libheif.dll + libde265.dll on Windows pip install
  - psd-tools → pure Python, just needs hiddenimports
  - PyMuPDF (fitz) → ships .dll/.so, collected automatically
  - pdf2image → EXCLUDED (needs external poppler binaries, PyMuPDF handles PDF)
"""

import os
import glob

block_cipher = None

# ── Project root (where this spec file lives) ──
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))

# ── Collect native DLLs from packages that ship them ──
# PyInstaller.utils.hooks.collect_dynamic_libs finds .dll/.so/.dylib
# inside the package directory and adds them to the bundle.
try:
    from PyInstaller.utils.hooks import collect_dynamic_libs
    _cairocffi_libs = collect_dynamic_libs('cairocffi')   # libcairo-2.dll for cairosvg
except Exception:
    _cairocffi_libs = []

try:
    from PyInstaller.utils.hooks import collect_dynamic_libs
    _heif_libs = collect_dynamic_libs('pillow_heif')      # libheif.dll, libde265.dll
except Exception:
    _heif_libs = []

try:
    from PyInstaller.utils.hooks import collect_dynamic_libs
    _fitz_libs = collect_dynamic_libs('fitz')              # PyMuPDF native libs
except Exception:
    _fitz_libs = []

_extra_binaries = _cairocffi_libs + _heif_libs + _fitz_libs

# ── Collect all .py files in the project as hidden imports ──
py_files = glob.glob(os.path.join(SPEC_DIR, "*.py"))
hidden_imports = [
    os.path.splitext(os.path.basename(f))[0]
    for f in py_files
    if os.path.basename(f) != "__init__.py"
]

# Core hidden imports that PyInstaller can't auto-detect
extra_hidden = [
    "PIL",             # Pillow
    "fitz",            # PyMuPDF
    "fastapi",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "pywebview",
    "pywebview._defaults",
    "anyio",
    "anyio._backends",
    "anyio._backends._asyncio",
    "httpcore",
    "httpcore._async",
    "httpcore._sync",
    "sniffio",
    "starlette",
    "starlette.routing",
    "starlette.middleware",
    "starlette.responses",
    "starlette.requests",
    "starlette.staticfiles",
    "pydantic",
    "pydantic.deprecated",
    "pydantic.deprecated.decorator",
    "email_validator",
    "multipart",
    "sqlite3",
    # ── Format converters ──
    "svglib",          # SVG → PNG (pure Python, primary SVG converter)
    "svglib.svglib",
    "reportlab",       # SVG rendering backend for svglib
    "reportlab.graphics",
    "reportlab.graphics.renderPM",
    "cairosvg",        # SVG → PNG fallback (needs cairocffi DLLs)
    "cairocffi",       # Cairo bindings for cairosvg
    "psd_tools",       # PSD → PNG (pure Python)
    "packbits",        # psd_tools dependency
    "pillow_heif",     # HEIC/HEIF → PNG (needs libheif DLLs)
]
hidden_imports.extend(extra_hidden)

# ── Data files: static/ folder ──
datas = [
    (os.path.join(SPEC_DIR, "static"), "static"),
]

# ── Analysis ──
a = Analysis(
    [os.path.join(SPEC_DIR, "app.py")],
    pathex=[SPEC_DIR],
    binaries=_extra_binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Only exclude pdf2image — it needs external poppler, PyMuPDF handles PDF
    excludes=["pdf2image"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ── PYZ (Python zip archive) ──
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE ──
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="LiteImageSearch",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,           # Placeholder — set path to .ico when available
)
