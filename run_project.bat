@echo off
title HealthAI Project Launcher
color 0A

echo ========================================================
echo        HealthAI - Automated Startup Launcher
echo ========================================================
echo.

cd /d "C:\Users\ujjwa\OneDrive\Desktop\ai health assistant"

echo [1/3] Starting MongoDB Server in Background...
start "HealthAI - MongoDB Database" cmd /k ""C:\Program Files\MongoDB\Server\8.3\bin\mongod.exe" --dbpath "C:\Program Files\MongoDB\Server\8.3\data""

timeout /t 3 /nobreak >nul

echo [2/3] Starting FastAPI Backend on Port 8000...
start "HealthAI - Python Backend API" cmd /k "cd /d "C:\Users\ujjwa\OneDrive\Desktop\ai health assistant" && python -m uvicorn app.main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

echo [3/3] Starting Vite React Frontend on Port 5173...
start "HealthAI - React Frontend" cmd /k "cd /d "C:\Users\ujjwa\OneDrive\Desktop\ai health assistant\app\frontend" && npm run dev"

timeout /t 4 /nobreak >nul

echo.
echo ========================================================
echo  All systems running! Opening browser in 3 seconds...
echo ========================================================
start http://localhost:5173/

echo.
echo Keep the 3 black terminal windows running in the background.
echo To stop the project later, simply close those terminal windows.
pause
