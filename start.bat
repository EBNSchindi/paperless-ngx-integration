@echo off
REM Windows Starter für Paperless NGX Integration

echo ============================================
echo     Paperless NGX Integration System
echo ============================================
echo.

REM Check if venv exists
if exist "venv\Scripts\activate.bat" (
    echo Aktiviere Virtual Environment...
    call venv\Scripts\activate.bat
) else (
    echo Virtual Environment nicht gefunden!
    echo Erstelle venv mit: python -m venv venv
    pause
    exit /b 1
)

REM Run the universal Python starter
python start.py %*

REM Keep window open if double-clicked
if %errorlevel% neq 0 pause