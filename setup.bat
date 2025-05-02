@echo off
echo ===== LinkedIn Easy Apply Bot - 环境设置 =====
echo 正在创建虚拟环境...

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请安装Python 3.8或更高版本
    echo 请访问 https://www.python.org/downloads/ 下载并安装
    pause
    exit /b 1
)

REM 创建虚拟环境
if not exist venv\ (
    pip install virtualenv
    virtualenv venv
    echo 虚拟环境已创建
) else (
    echo 检测到现有虚拟环境
)

REM 激活虚拟环境并安装依赖
echo 正在安装依赖包...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo ===== 安装完成! =====
echo 现在您可以运行 start.bat 启动LinkedIn Easy Apply Bot
pause