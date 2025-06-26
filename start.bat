@echo off
echo ===== LinkedIn Easy Apply Bot - Setup & Start =====

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not detected. Please install Python 3.8 or higher.
    echo Please visit https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
echo Creating/Verifying virtual environment...
if not exist venv\ (
    python -m venv venv
    echo Virtual environment created.
    REM If venv is newly created, force requirements installation by deleting any old flag
    if exist venv\.requirements_installed del venv\.requirements_installed
) else (
    echo Existing virtual environment detected.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies if not already installed
echo Checking and installing dependencies...
if exist venv\.requirements_installed (
    echo Dependencies appear to be installed. Skipping installation.
) else (
    echo Installing dependencies...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if %errorlevel% equ 0 (
        echo Dependencies installed successfully.
        REM Create a flag file to indicate successful installation
        echo.> venv\.requirements_installed
    ) else (
        echo [ERROR] Failed to install dependencies. Please check requirements.txt and your internet connection.
        pause
        exit /b 1
    )
)

REM Check if config file exists
if exist config.yaml goto skipwarning
echo [WARNING] Config file (config.yaml) not found.
echo The GUI will be launched to create a config file.
:skipwarning

echo Launching GUI...
python gui_web_tkinter.py

REM If you want to run the bot directly (without GUI), uncomment the line below
REM python main.py

echo ===== Program exited =====
pause