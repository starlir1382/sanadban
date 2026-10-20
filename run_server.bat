@echo off
title SanadBan Server
echo ========================================================
echo       Starting SanadBan (DeedFlow) Web Application
echo ========================================================
cd /d "E:\SK\sanadban"
python manage.py runserver 127.0.0.1:8000
pause
