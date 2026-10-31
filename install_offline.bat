@echo off
chcp 65001 >nul
echo ========================================================
echo   SanadBan (MaskanYar) - Offline Environment Installer
echo ========================================================
echo.

if not exist ".venv" (
    echo [*] Creating virtual environment (.venv)...
    python -m venv .venv
) else (
    echo [*] Virtual environment (.venv) already exists.
)

echo [*] Activating virtual environment...
call .\.venv\Scripts\activate.bat

echo [*] Installing dependencies from offline wheels directory...
python -m pip install --no-index --find-links=.\wheels -r requirements.txt

echo.
echo [*] Applying database migrations...
python manage.py migrate

echo.
echo [*] Setting up 29 users and 3 system administrators...
python scripts/setup_server_users.py

echo.
echo [*] Collecting static files...
python manage.py collectstatic --noinput

echo.
echo ========================================================
echo   Installation completed successfully!
echo   You can now start the server using run_waitress.bat
echo ========================================================
pause
