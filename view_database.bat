@echo off
title DUSY Healthcare Database Viewer
color 0A
echo ===================================================================
echo     DUSY HEALTHCARE PLATFORM - MONGODB LIVE DATA VIEWER
echo ===================================================================
echo.
cd /d "%~dp0"
python show_database.py
echo.
echo ===================================================================
echo Press any key to exit...
pause >nul
