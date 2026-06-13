@echo off
chcp 65001 >nul 2>&1
title Build LiteImageSearch.exe

echo.
echo ============================================
echo   Lite Image Search - Build .exe
echo ============================================
echo.

REM ── Step 0: Find Python ──
set "PYTHON="
where python >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON where py >nul 2>&1 && set "PYTHON=py"
if not defined PYTHON where python3 >nul 2>&1 && set "PYTHON=python3"

if not defined PYTHON (
    echo [ERROR] Python not found.
    echo.
    echo Please do ONE of the following:
    echo   1. Install Python 3.10+ from https://www.python.org/downloads/
    echo      IMPORTANT: Check "Add Python to PATH" during installation
    echo   2. Or open Anaconda Prompt and run: cd to this folder, then run:
    echo        pip install -r requirements.txt
    echo        pip install pyinstaller
    echo        pyinstaller lite_image_search.spec --noconfirm
    echo.
    pause
    exit /b 1
)

echo [OK] Found: %PYTHON%
%PYTHON% --version
echo.

REM ── Step 1: Install dependencies ──
echo [1/3] Installing dependencies...
%PYTHON% -m pip install -r requirements.txt
%PYTHON% -m pip install pyinstaller
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [2/3] Building LiteImageSearch.exe ...
echo   This may take a few minutes...
echo.

%PYTHON% -m PyInstaller lite_image_search.spec --noconfirm
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed. Check error messages above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build complete!
echo   Output: dist\LiteImageSearch.exe
echo ============================================
echo.

if not exist "dist\data" (
    echo [INFO] Create a 'data' folder next to the .exe for runtime storage.
    echo        The app will auto-create it on first run.
    echo.
)

pause
