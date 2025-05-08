@echo off
echo ===== Starting LinkedIn Easy Apply Bot =====

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if config file exists
if exist config.yaml goto skipwarning
echo [WARNING] Config file (config.yaml) not found.
echo The GUI will be launched to create a config file.
:skipwarning

echo Launching GUI...
python gui_tkinter.py

REM If you want to run the bot directly (without GUI), uncomment the line below
REM python main.py

echo ===== Program exited =====
pause