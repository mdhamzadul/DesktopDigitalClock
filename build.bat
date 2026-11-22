@echo off
title Desktop Digital Clock - Build Tool
echo ========================================================
echo  Desktop Digital Clock - Automated PyInstaller Builder
echo  Developed by AsR
echo ========================================================
echo.

REM Verify Python & PyInstaller
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in system PATH!
    pause
    exit /b 1
)

echo [1/4] Installing / Updating dependencies...
python -m pip install --upgrade pip
python -m pip install pystray pillow pyinstaller

echo.
echo [2/4] Building Portable Clock (DesktopDigitalClock_AsR.exe)...
pyinstaller --clean --onefile --noconsole --icon clock.ico --add-data "clock.ico;." --name DesktopDigitalClock_AsR desktop_clock.py

if not exist "dist\DesktopDigitalClock_AsR.exe" (
    echo [ERROR] Failed to build DesktopDigitalClock_AsR.exe!
    pause
    exit /b 1
)

copy /y "dist\DesktopDigitalClock_AsR.exe" "DesktopDigitalClock_AsR.exe" >nul
echo [OK] Portable executable built successfully: DesktopDigitalClock_AsR.exe

echo.
echo [3/4] Building Setup Wizard (Setup_DesktopDigitalClock_AsR.exe)...
pyinstaller --clean --onefile --noconsole --icon clock.ico --add-data "DesktopDigitalClock_AsR.exe;." --add-data "clock.ico;." --name Setup_DesktopDigitalClock_AsR installer.py

if not exist "dist\Setup_DesktopDigitalClock_AsR.exe" (
    echo [ERROR] Failed to build Setup_DesktopDigitalClock_AsR.exe!
    pause
    exit /b 1
)

copy /y "dist\Setup_DesktopDigitalClock_AsR.exe" "Setup_DesktopDigitalClock_AsR.exe" >nul
echo [OK] Setup Wizard built successfully: Setup_DesktopDigitalClock_AsR.exe

echo.
echo [4/4] Cleaning temporary build folders...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "DesktopDigitalClock_AsR.spec" del /f /q "DesktopDigitalClock_AsR.spec"
if exist "Setup_DesktopDigitalClock_AsR.spec" del /f /q "Setup_DesktopDigitalClock_AsR.spec"

echo.
echo ========================================================
echo  BUILD COMPLETE!
echo   - DesktopDigitalClock_AsR.exe (Portable)
echo   - Setup_DesktopDigitalClock_AsR.exe (Installer)
echo ========================================================
pause
