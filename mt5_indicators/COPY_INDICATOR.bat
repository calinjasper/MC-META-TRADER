@echo off
REM Batch script to copy indicator file to MT5
echo ========================================
echo MT5 Indicator File Copy Script
echo ========================================
echo.

REM Get current directory
set "SOURCE_FILE=%~dp0PythonIndicators.mq5"

if not exist "%SOURCE_FILE%" (
    echo ERROR: PythonIndicators.mq5 not found in current directory!
    echo Please run this script from the mt5_indicators folder.
    pause
    exit /b 1
)

echo Source file: %SOURCE_FILE%
echo.

REM Try common MT5 installation paths
set "TARGET1=C:\Program Files\MetaTrader 5\MQL5\Indicators\PythonIndicators.mq5"
set "TARGET2=C:\Program Files (x86)\MetaTrader 5\MQL5\Indicators\PythonIndicators.mq5"

if exist "C:\Program Files\MetaTrader 5\MQL5\Indicators\" (
    echo Found MT5 at: C:\Program Files\MetaTrader 5\
    echo Copying to: %TARGET1%
    copy "%SOURCE_FILE%" "%TARGET1%" >nul
    if %errorlevel% equ 0 (
        echo [OK] File copied successfully!
        echo.
        echo Next steps:
        echo 1. Open MetaEditor (F4 in MT5)
        echo 2. Open PythonIndicators.mq5
        echo 3. Press F7 to compile
        echo 4. Verify: 0 error(s), 0 warning(s)
    ) else (
        echo [ERROR] Failed to copy file. Try running as Administrator.
    )
) else if exist "C:\Program Files (x86)\MetaTrader 5\MQL5\Indicators\" (
    echo Found MT5 at: C:\Program Files (x86)\MetaTrader 5\
    echo Copying to: %TARGET2%
    copy "%SOURCE_FILE%" "%TARGET2%" >nul
    if %errorlevel% equ 0 (
        echo [OK] File copied successfully!
        echo.
        echo Next steps:
        echo 1. Open MetaEditor (F4 in MT5)
        echo 2. Open PythonIndicators.mq5
        echo 3. Press F7 to compile
        echo 4. Verify: 0 error(s), 0 warning(s)
    ) else (
        echo [ERROR] Failed to copy file. Try running as Administrator.
    )
) else (
    echo [WARNING] MT5 not found in standard locations.
    echo.
    echo Please manually copy:
    echo   FROM: %SOURCE_FILE%
    echo   TO:   {Your MT5 Path}\MQL5\Indicators\PythonIndicators.mq5
    echo.
    echo To find your MT5 path:
    echo   1. Open MT5
    echo   2. File -^> Open Data Folder
    echo   3. Navigate up to find installation folder
)

echo.
pause

