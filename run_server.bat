@echo off
chcp 65001 > nul
title SanadBan (MaskanYar) Web Server
echo ========================================================
echo       Starting SanadBan (MaskanYar) Web Application
echo ========================================================
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo Using Virtual Environment: .venv\Scripts\python.exe
    ".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
) else (
    echo Virtual environment not found, falling back to system python...
    python manage.py runserver 127.0.0.1:8000
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Server exited with code %ERRORLEVEL%.
)
pause
