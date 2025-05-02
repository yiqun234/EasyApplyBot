@echo off
echo ===== 启动 LinkedIn Easy Apply Bot =====

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 检查配置文件是否存在
if not exist config.yaml (
    echo [警告] 未找到配置文件(config.yaml)
    echo 将启动GUI以创建配置文件
)

echo 正在启动图形界面...
python gui_tkinter.py

REM 如果想直接运行机器人(无GUI)，可以取消下面这行的注释
REM python main.py

echo ===== 程序已退出 =====
pause