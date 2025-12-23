@echo off
echo ================================================
echo  MC-META-TRADER with PocketBase Integration
echo ================================================
echo.

REM Check if PocketBase exists
if not exist "pocketbase\pocketbase.exe" (
    echo WARNING: PocketBase not found in pocketbase\pocketbase.exe
    echo Please download PocketBase from: https://github.com/pocketbase/pocketbase/releases
    echo Extract pocketbase.exe to the pocketbase\ directory
    echo.
    echo Starting trading system WITHOUT database storage...
    echo.
    timeout /t 3
    python src\main.py
    pause
    exit /b
)

REM Start PocketBase Server in new window
echo Starting PocketBase Server...
start "PocketBase Server" cmd /k "cd pocketbase && pocketbase.exe serve && pause"

REM Wait for PocketBase to start
echo Waiting for PocketBase to initialize...
timeout /t 5

REM Start Trading System
echo.
echo Starting Trading System...
echo.
python src\main.py

REM If trading system exits, keep window open
pause

