@echo off
chcp 65001 > nul
title SanadBan Production WSGI Server (Waitress)
echo ========================================================
echo       Starting SanadBan Production Server via Waitress
echo ========================================================
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo [INFO] Using Virtual Environment: .venv\Scripts\python.exe
    ".venv\Scripts\python.exe" run_waitress.py
) else (
    echo [WARNING] Virtual environment not found, falling back to system python...
    python run_waitress.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Server exited with code %ERRORLEVEL%.
)
pause
