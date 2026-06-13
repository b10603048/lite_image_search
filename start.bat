@echo off
chcp 65001 >nul 2>&1
title Lite Image Search

set "APPDIR=%~dp0"
set "RUNTIME=%APPDIR%runtime"
set "PYTHON=%RUNTIME%\python\python.exe"

REM ── Custom port via command line: start.bat 8080 ──
set "PORT_ARG="
if not "%~1"=="" set "PORT_ARG=--port %~1"

REM ── Check if setup is needed ──
REM Track requirements.txt hash to detect when new packages are added
set "NEED_SETUP=0"
if not exist "%PYTHON%" set "NEED_SETUP=1"

REM Compare current requirements.txt hash with the one from last install
set "REQ_HASH_FILE=%RUNTIME%\req_hash.txt"
set "CURRENT_HASH="
if exist "%APPDIR%requirements.txt" (
    for /f "delims=" %%h in ('certutil -hashfile "%APPDIR%requirements.txt" MD5 2^>nul ^| findstr /v ":" ^| findstr /r "."') do set "CURRENT_HASH=%%h"
)
set "SAVED_HASH="
if exist "%REQ_HASH_FILE%" (
    set /p SAVED_HASH=<"%REQ_HASH_FILE%"
)
if not "%CURRENT_HASH%"=="%SAVED_HASH%" set "NEED_SETUP=1"

REM ── Already set up and requirements unchanged? Just launch ──
if "%NEED_SETUP%"=="0" goto :launch

echo.
echo ============================================
echo   Lite Image Search - Setup
echo ============================================
echo.

REM ── Step 1: Download portable Python ──

if not exist "%PYTHON%" (
    echo [1/3] Downloading Python...
    if not exist "%RUNTIME%" mkdir "%RUNTIME%"

    powershell -ExecutionPolicy Bypass -Command ^
        "$url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip';" ^
        "$out = '%RUNTIME%\python.zip';" ^
        "Write-Host '  Downloading...';" ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
        "Invoke-WebRequest -Uri $url -OutFile $out;" ^
        "Write-Host '  Extracting...';" ^
        "Expand-Archive -Path $out -DestinationPath '%RUNTIME%\python' -Force;" ^
        "Remove-Item $out;" ^
        "Write-Host '  Done.'"

    if not exist "%PYTHON%" (
        echo [ERROR] Failed to download Python. Check internet connection.
        pause
        exit /b 1
    )

    REM Enable site-packages: uncomment "import site" in _pth file
    powershell -ExecutionPolicy Bypass -Command ^
        "$f = '%RUNTIME%\python\python311._pth';" ^
        "$c = Get-Content $f;" ^
        "$c = $c -replace '^#?\s*import site', 'import site';" ^
        "Set-Content $f $c"
)

echo [OK] Python ready

REM ── Step 2: Install pip ──

if not exist "%RUNTIME%\python\Scripts\pip.exe" (
    echo [2/3] Installing pip...
    powershell -ExecutionPolicy Bypass -Command ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
        "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%RUNTIME%\get-pip.py';"
    "%PYTHON%" "%RUNTIME%\get-pip.py" --no-warn-script-location
    del "%RUNTIME%\get-pip.py" 2>nul
)

echo [OK] pip ready

REM ── Step 3: Install packages ──

echo [3/3] Installing packages... please wait.
echo.

"%PYTHON%" -m pip install -r "%APPDIR%requirements.txt"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Package installation failed. Check internet connection.
    pause
    exit /b 1
)

echo [OK] All packages installed

REM Save current requirements hash
echo %CURRENT_HASH%> "%REQ_HASH_FILE%"

echo.
echo [OK] Setup complete!

REM ── Launch ──

:launch
echo.
echo ============================================
echo   Lite Image Search
if defined PORT_ARG (
echo   http://localhost:%~1
) else (
echo   http://localhost:6626
)
echo   Press Ctrl+C to stop
echo ============================================
echo.

"%PYTHON%" "%APPDIR%start.py" %PORT_ARG%
pause
