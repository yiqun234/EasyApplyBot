#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LinkedIn Bot 图形界面调度器启动脚本
"""

import os
import sys

def main():
    # 确保在正确的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 检查必要文件
    if not os.path.exists('scheduler_gui.py'):
        print("错误：找不到 scheduler_gui.py 文件")
        input("按回车键退出...")
        return
    
    if not os.path.exists('main.py'):
        print("错误：找不到 main.py 文件")
        input("按回车键退出...")
        return
    
    print("正在启动 LinkedIn Bot 图形界面调度器...")
    print("提示：")
    print("- 确保已在 configs 目录下放置用户配置文件")
    print("- 配置文件格式：用户ID.yaml")
    print("- 首次使用请先测试单个任务是否正常运行")
    print("-" * 50)
    
    try:
        # 导入并运行调度器
        from scheduler_gui import *
        
        root = tk.Tk()
        app = SchedulerGUI(root)
        root.mainloop()
        
    except ImportError as e:
        print(f"导入错误：{e}")
        print("请确保已安装所需的Python包：tkinter")
        input("按回车键退出...")
    except Exception as e:
        print(f"启动错误：{e}")
        input("按回车键退出...")

if __name__ == "__main__":
    main() 