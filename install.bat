@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo  Lite Image Search - Reinstall Packages
echo ============================================
echo.
pause

set "APPDIR=%~dp0"
set "RUNTIME=%APPDIR%runtime"
set "PYTHON=%RUNTIME%\python\python.exe"

if not exist "%PYTHON%" (
    echo [ERROR] Python not found. Run start.bat first.
    pause
    exit /b 1
)

echo Reinstalling packages...
"%PYTHON%" -m pip install -r "%APPDIR%requirements.txt" --force-reinstall
del "%RUNTIME%\installed.flag" 2>nul
echo. > "%RUNTIME%\installed.flag"
echo.
echo Done! Run start.bat to launch the app.
pause
