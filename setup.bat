@echo off
echo ===== LinkedIn Easy Apply Bot - Setup =====
echo Creating virtual environment...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not detected. Please install Python 3.8 or higher.
    echo Please visit https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Create virtual environment
if not exist venv\ (
    python -m venv venv
    echo Virtual environment created.
) else (
    echo Existing virtual environment detected.
)

REM Activate virtual environment and install dependencies
echo Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo ===== Installation complete! =====
echo You can now run start.bat to launch LinkedIn Easy Apply Bot.
pause