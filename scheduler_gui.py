import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import subprocess
import os
import glob
import time
import json
from datetime import datetime, timedelta
from enum import Enum

class TaskStatus(Enum):
    IDLE = "空闲"
    QUEUED = "队列中"
    RUNNING = "运行中"
    SUCCESS = "成功"
    FAILED = "失败"
    DISABLED = "已禁用"

class ScheduleType(Enum):
    INTERVAL = "间隔执行"
    DAILY = "每日定时"
    MANUAL = "仅手动"

class UserTask:
    def __init__(self, user_id, config_path):
        self.user_id = user_id
        self.config_path = config_path
        self.status = TaskStatus.IDLE
        self.last_run = None
        self.next_run = None
        self.process = None
        self.enabled = True
        self.selected = True  # 是否被选中执行
        
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'config_path': self.config_path,
            'status': self.status.value,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'enabled': self.enabled,
            'selected': self.selected
        }

class SchedulerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LinkedIn Bot 任务调度器 v2.0")
        self.root.geometry("1400x900")
        
        self.CONFIG_DIR = "configs"
        self.DEFAULT_CONFIG = "config.yaml"
        self.MAIN_SCRIPT = "main.py"
        
        self.user_tasks = {}
        self.task_queue = queue.Queue()
        self.current_running_task = None
        self.running = False
        self.scheduler_thread = None
        self.worker_thread = None
        
        # 调度配置
        self.schedule_type = ScheduleType.INTERVAL
        self.schedule_interval = 2  # hours
        self.daily_time = "08:00"
        
        self.setup_ui()
        self.load_user_configs()
        self.update_ui_timer()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="LinkedIn Bot 串行任务调度器", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Left panel - Configuration
        config_frame = ttk.LabelFrame(main_frame, text="调度配置", padding="10")
        config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Schedule type selection
        ttk.Label(config_frame, text="调度方式:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.schedule_type_var = tk.StringVar(value=self.schedule_type.value)
        schedule_types = [stype.value for stype in ScheduleType]
        schedule_combo = ttk.Combobox(config_frame, textvariable=self.schedule_type_var, 
                                    values=schedule_types, state="readonly", width=15)
        schedule_combo.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        schedule_combo.bind('<<ComboboxSelected>>', self.on_schedule_type_change)
        
        # Interval configuration
        self.interval_frame = ttk.LabelFrame(config_frame, text="间隔配置", padding="5")
        self.interval_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(self.interval_frame, text="间隔(小时):").grid(row=0, column=0, sticky=tk.W)
        self.interval_var = tk.StringVar(value=str(self.schedule_interval))
        interval_entry = ttk.Entry(self.interval_frame, textvariable=self.interval_var, width=10)
        interval_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        # Daily time configuration
        self.daily_frame = ttk.LabelFrame(config_frame, text="每日定时", padding="5")
        self.daily_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(self.daily_frame, text="执行时间:").grid(row=0, column=0, sticky=tk.W)
        self.daily_time_var = tk.StringVar(value=self.daily_time)
        daily_time_entry = ttk.Entry(self.daily_frame, textvariable=self.daily_time_var, width=10)
        daily_time_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        ttk.Label(self.daily_frame, text="(格式: HH:MM)").grid(row=1, column=0, columnspan=2, sticky=tk.W)
        
        # Queue configuration
        queue_config_frame = ttk.LabelFrame(config_frame, text="队列配置", padding="5")
        queue_config_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(queue_config_frame, text="任务间延迟(秒):").grid(row=0, column=0, sticky=tk.W)
        self.task_delay_var = tk.StringVar(value="30")
        delay_entry = ttk.Entry(queue_config_frame, textvariable=self.task_delay_var, width=10)
        delay_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        # Control buttons
        control_buttons_frame = ttk.LabelFrame(config_frame, text="控制操作", padding="5")
        control_buttons_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_button = ttk.Button(control_buttons_frame, text="启动调度器", 
                                     command=self.start_scheduler)
        self.start_button.grid(row=0, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        
        self.stop_button = ttk.Button(control_buttons_frame, text="停止调度器", 
                                    command=self.stop_scheduler, state=tk.DISABLED)
        self.stop_button.grid(row=1, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        
        refresh_button = ttk.Button(control_buttons_frame, text="刷新任务列表", 
                                  command=self.refresh_users)
        refresh_button.grid(row=2, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        
        run_queue_button = ttk.Button(control_buttons_frame, text="立即执行队列", 
                                    command=self.run_queue_now)
        run_queue_button.grid(row=3, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        
        # Configure column weight
        control_buttons_frame.columnconfigure(0, weight=1)
        
        # Status
        self.status_var = tk.StringVar(value="调度器已停止")
        status_label = ttk.Label(config_frame, textvariable=self.status_var, 
                                font=("Arial", 10, "bold"), foreground="red")
        status_label.grid(row=6, column=0, pady=(20, 0), sticky=tk.W)
        
        # Right panel - Task management
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)
        
        # Task selection frame
        task_selection_frame = ttk.LabelFrame(right_panel, text="任务选择与状态", padding="10")
        task_selection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        task_selection_frame.columnconfigure(0, weight=1)
        task_selection_frame.rowconfigure(0, weight=1)
        
        # Tasks treeview with checkboxes
        columns = ("选择", "用户ID", "状态", "上次运行", "下次运行")
        self.tasks_tree = ttk.Treeview(task_selection_frame, columns=columns, show="headings", height=8)
        
        # Configure columns
        self.tasks_tree.heading("选择", text="选择")
        self.tasks_tree.column("选择", width=50)
        self.tasks_tree.heading("用户ID", text="用户ID")
        self.tasks_tree.column("用户ID", width=100)
        self.tasks_tree.heading("状态", text="状态")
        self.tasks_tree.column("状态", width=80)
        self.tasks_tree.heading("上次运行", text="上次运行")
        self.tasks_tree.column("上次运行", width=120)
        self.tasks_tree.heading("下次运行", text="下次运行")
        self.tasks_tree.column("下次运行", width=120)
        
        # Bind double-click to toggle selection
        self.tasks_tree.bind('<Double-1>', self.toggle_task_selection)
        
        # Scrollbar for treeview
        tasks_scrollbar = ttk.Scrollbar(task_selection_frame, orient=tk.VERTICAL, 
                                       command=self.tasks_tree.yview)
        self.tasks_tree.configure(yscrollcommand=tasks_scrollbar.set)
        
        self.tasks_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tasks_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Task control buttons
        task_control_frame = ttk.Frame(task_selection_frame)
        task_control_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky=tk.W)
        
        ttk.Button(task_control_frame, text="全选", 
                  command=self.select_all_tasks).grid(row=0, column=0)
        ttk.Button(task_control_frame, text="全不选", 
                  command=self.deselect_all_tasks).grid(row=0, column=1, padx=(10, 0))
        ttk.Button(task_control_frame, text="运行选中", 
                  command=self.run_selected_task).grid(row=0, column=2, padx=(10, 0))
        ttk.Button(task_control_frame, text="停止当前", 
                  command=self.stop_current_task).grid(row=0, column=3, padx=(10, 0))
        
        # Queue status frame
        queue_frame = ttk.LabelFrame(right_panel, text="队列状态", padding="10")
        queue_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)
        
        # Queue display
        self.queue_text = scrolledtext.ScrolledText(queue_frame, height=6, width=60)
        self.queue_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="10")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, width=120)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Log control
        log_control_frame = ttk.Frame(log_frame)
        log_control_frame.grid(row=1, column=0, pady=(10, 0), sticky=tk.W)
        
        ttk.Button(log_control_frame, text="清除日志", 
                  command=self.clear_log).grid(row=0, column=0)
        ttk.Button(log_control_frame, text="保存日志", 
                  command=self.save_log).grid(row=0, column=1, padx=(10, 0))
        
        # Initialize UI state
        self.on_schedule_type_change(None)
    
    def on_schedule_type_change(self, event):
        """Handle schedule type change"""
        selected_type = self.schedule_type_var.get()
        
        if selected_type == ScheduleType.INTERVAL.value:
            self.interval_frame.grid()
            self.daily_frame.grid_remove()
        elif selected_type == ScheduleType.DAILY.value:
            self.interval_frame.grid_remove()
            self.daily_frame.grid()
        else:  # MANUAL
            self.interval_frame.grid_remove()
            self.daily_frame.grid_remove()
    
    def load_user_configs(self):
        """Load all available user configurations"""
        config_files = []
        
        # Add default config if exists
        if os.path.exists(self.DEFAULT_CONFIG):
            config_files.append(self.DEFAULT_CONFIG)
        
        # Add user configs from configs directory
        if os.path.exists(self.CONFIG_DIR):
            user_configs = glob.glob(os.path.join(self.CONFIG_DIR, "*.yaml"))
            config_files.extend(user_configs)
        
        # Create or update user tasks
        for config_path in config_files:
            user_id = self.get_user_id_from_config(config_path)
            if user_id not in self.user_tasks:
                task = UserTask(user_id, config_path)
                self.user_tasks[user_id] = task
                self.log(f"已添加用户: {user_id} ({config_path})")
        
        # Remove tasks for configs that no longer exist
        to_remove = []
        for user_id, task in self.user_tasks.items():
            if not os.path.exists(task.config_path):
                to_remove.append(user_id)
        
        for user_id in to_remove:
            del self.user_tasks[user_id]
            self.log(f"已移除用户: {user_id} (配置文件不存在)")
        
        self.update_tasks_display()
        self.update_queue_display()
    
    def get_user_id_from_config(self, config_path):
        """Extract user ID from config file path"""
        if config_path == self.DEFAULT_CONFIG:
            return "default"
        filename = os.path.basename(config_path)
        return filename.replace('.yaml', '')
    
    def refresh_users(self):
        """Refresh user list"""
        self.load_user_configs()
        self.log("任务列表已刷新")
    
    def toggle_task_selection(self, event):
        """Toggle task selection on double-click"""
        selection = self.tasks_tree.selection()
        if not selection:
            return
        
        item = self.tasks_tree.item(selection[0])
        user_id = item['values'][1]  # User ID is in column 1
        task = self.user_tasks.get(user_id)
        
        if task:
            task.selected = not task.selected
            self.log(f"任务 {user_id} {'已选中' if task.selected else '已取消选中'}")
            self.update_tasks_display()
    
    def select_all_tasks(self):
        """Select all tasks"""
        for task in self.user_tasks.values():
            task.selected = True
        self.log("已选中所有任务")
        self.update_tasks_display()
    
    def deselect_all_tasks(self):
        """Deselect all tasks"""
        for task in self.user_tasks.values():
            task.selected = False
        self.log("已取消选中所有任务")
        self.update_tasks_display()
    
    def start_scheduler(self):
        """Start the task scheduler"""
        # Validate configuration
        try:
            schedule_type = self.schedule_type_var.get()
            
            if schedule_type == ScheduleType.INTERVAL.value:
                self.schedule_interval = float(self.interval_var.get())
                if self.schedule_interval <= 0:
                    raise ValueError("间隔必须大于0")
                    
            elif schedule_type == ScheduleType.DAILY.value:
                time_str = self.daily_time_var.get()
                # Validate time format
                try:
                    datetime.strptime(time_str, "%H:%M")
                    self.daily_time = time_str
                except ValueError:
                    raise ValueError("时间格式错误，请使用 HH:MM 格式")
                    
        except ValueError as e:
            messagebox.showerror("错误", f"配置错误: {e}")
            return
        
        self.schedule_type = ScheduleType(schedule_type)
        self.running = True
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker_thread.start()
        
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set(f"调度器运行中 ({schedule_type})")
        
        # Set next run times based on schedule type
        self.calculate_next_run_times()
        
        self.log(f"调度器已启动 - {schedule_type}")
    
    def calculate_next_run_times(self):
        """Calculate next run times based on schedule type"""
        now = datetime.now()
        
        if self.schedule_type == ScheduleType.INTERVAL:
            next_run_time = now + timedelta(hours=self.schedule_interval)
            for task in self.user_tasks.values():
                if task.selected:
                    task.next_run = next_run_time
                    
        elif self.schedule_type == ScheduleType.DAILY:
            # Calculate next daily run time
            today = now.date()
            time_parts = self.daily_time.split(':')
            target_time = datetime.combine(today, datetime.strptime(self.daily_time, "%H:%M").time())
            
            if target_time <= now:
                target_time += timedelta(days=1)
                
            for task in self.user_tasks.values():
                if task.selected:
                    task.next_run = target_time
    
    def stop_scheduler(self):
        """Stop the task scheduler"""
        self.running = False
        
        # Stop current running task
        if self.current_running_task and self.current_running_task.process:
            try:
                self.current_running_task.process.terminate()
                self.current_running_task.status = TaskStatus.IDLE
                self.current_running_task = None
            except:
                pass
        
        # Clear queue
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except:
                break
        
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("调度器已停止")
        
        self.log("调度器已停止")
        self.update_queue_display()
    
    def scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            if self.schedule_type == ScheduleType.MANUAL:
                time.sleep(60)  # Just sleep if manual mode
                continue
                
            current_time = datetime.now()
            
            # Check if it's time to run
            should_run = False
            
            if self.schedule_type == ScheduleType.INTERVAL:
                # Check if any task is due
                for task in self.user_tasks.values():
                    if (task.selected and task.next_run and current_time >= task.next_run 
                        and task.status not in [TaskStatus.RUNNING, TaskStatus.QUEUED]):
                        should_run = True
                        break
                        
            elif self.schedule_type == ScheduleType.DAILY:
                # Check if it's the daily run time
                for task in self.user_tasks.values():
                    if (task.selected and task.next_run and current_time >= task.next_run
                        and task.status not in [TaskStatus.RUNNING, TaskStatus.QUEUED]):
                        should_run = True
                        break
            
            if should_run:
                self.queue_selected_tasks()
                self.calculate_next_run_times()  # Set next run times
            
            time.sleep(30)  # Check every 30 seconds
    
    def worker_loop(self):
        """Worker loop to process task queue"""
        while self.running:
            try:
                # Get next task from queue (with timeout)
                task = self.task_queue.get(timeout=1)
                
                if not self.running:
                    break
                    
                self.current_running_task = task
                self.run_single_task(task)
                
                # Delay between tasks
                if self.running:
                    delay = float(self.task_delay_var.get())
                    self.log(f"任务间延迟 {delay} 秒...")
                    time.sleep(delay)
                
                self.current_running_task = None
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.log(f"工作线程错误: {e}")
                self.current_running_task = None
    
    def queue_selected_tasks(self):
        """Add selected tasks to queue"""
        selected_tasks = [task for task in self.user_tasks.values() 
                         if task.selected and task.status == TaskStatus.IDLE]
        
        if not selected_tasks:
            self.log("没有可执行的任务")
            return
        
        for task in selected_tasks:
            task.status = TaskStatus.QUEUED
            self.task_queue.put(task)
        
        self.log(f"已将 {len(selected_tasks)} 个任务加入队列")
        self.update_queue_display()
    
    def run_queue_now(self):
        """Run queue immediately"""
        self.queue_selected_tasks()
    
    def run_selected_task(self):
        """Run selected task immediately"""
        selection = self.tasks_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择一个任务")
            return
        
        item = self.tasks_tree.item(selection[0])
        user_id = item['values'][1]
        task = self.user_tasks.get(user_id)
        
        if task:
            if task.status == TaskStatus.RUNNING:
                messagebox.showinfo("信息", f"任务 {user_id} 正在运行中")
            elif task.status == TaskStatus.QUEUED:
                messagebox.showinfo("信息", f"任务 {user_id} 已在队列中")
            else:
                task.status = TaskStatus.QUEUED
                self.task_queue.put(task)
                self.log(f"已将任务 {user_id} 加入队列")
                self.update_queue_display()
    
    def stop_current_task(self):
        """Stop current running task"""
        if self.current_running_task and self.current_running_task.process:
            try:
                self.current_running_task.process.terminate()
                self.current_running_task.status = TaskStatus.IDLE
                self.log(f"已停止任务: {self.current_running_task.user_id}")
                self.current_running_task = None
            except Exception as e:
                self.log(f"停止任务失败: {e}")
        else:
            messagebox.showinfo("信息", "当前没有正在运行的任务")
    
    def run_single_task(self, task):
        """Run a single task"""
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        self.log(f"开始运行任务: {task.user_id}")
        
        try:
            command = ["python", "-u", self.MAIN_SCRIPT, "--config", task.config_path]
            task.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # Read output
            while True:
                if not self.running:
                    task.process.terminate()
                    break
                    
                output = task.process.stdout.readline()
                if output == '' and task.process.poll() is not None:
                    break
                if output:
                    self.log(f"[{task.user_id}] {output.strip()}")
            
            return_code = task.process.poll()
            if return_code == 0:
                task.status = TaskStatus.SUCCESS
                self.log(f"任务 {task.user_id} 成功完成")
            else:
                task.status = TaskStatus.FAILED
                self.log(f"任务 {task.user_id} 失败，返回码: {return_code}")
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            self.log(f"任务 {task.user_id} 执行异常: {e}")
        finally:
            task.process = None
            self.update_queue_display()
    
    def update_tasks_display(self):
        """Update the tasks display"""
        # Save current selection
        selected_items = self.tasks_tree.selection()
        selected_user_ids = []
        for item in selected_items:
            item_values = self.tasks_tree.item(item)['values']
            if len(item_values) > 1:
                selected_user_ids.append(item_values[1])  # User ID is in column 1
        
        # Clear existing items
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)
        
        # Add current tasks
        items_to_reselect = []
        for task in self.user_tasks.values():
            selected = "✓" if task.selected else "○"
            last_run = task.last_run.strftime("%m-%d %H:%M") if task.last_run else "从未运行"
            next_run = task.next_run.strftime("%m-%d %H:%M") if task.next_run else "未计划"
            
            # Set text color based on status
            tags = []
            if task.status == TaskStatus.RUNNING:
                tags = ['running']
            elif task.status == TaskStatus.SUCCESS:
                tags = ['success']
            elif task.status == TaskStatus.FAILED:
                tags = ['failed']
            elif task.status == TaskStatus.QUEUED:
                tags = ['queued']
            
            item = self.tasks_tree.insert('', 'end', values=(
                selected,
                task.user_id,
                task.status.value,
                last_run,
                next_run
            ), tags=tags)
            
            # Mark for reselection if it was previously selected
            if task.user_id in selected_user_ids:
                items_to_reselect.append(item)
        
        # Configure tags
        self.tasks_tree.tag_configure('running', background='lightblue')
        self.tasks_tree.tag_configure('success', background='lightgreen')
        self.tasks_tree.tag_configure('failed', background='lightcoral')
        self.tasks_tree.tag_configure('queued', background='lightyellow')
        
        # Restore selection
        for item in items_to_reselect:
            self.tasks_tree.selection_add(item)
    
    def update_queue_display(self):
        """Update queue status display"""
        self.queue_text.delete(1.0, tk.END)
        
        queue_info = []
        
        # Current running task
        if self.current_running_task:
            queue_info.append(f"🔄 正在运行: {self.current_running_task.user_id}")
        
        # Queued tasks
        queue_size = self.task_queue.qsize()
        if queue_size > 0:
            queue_info.append(f"⏳ 队列中任务数: {queue_size}")
            
        # Selected tasks summary
        selected_count = sum(1 for task in self.user_tasks.values() if task.selected)
        total_count = len(self.user_tasks)
        queue_info.append(f"📋 已选择任务: {selected_count}/{total_count}")
        
        # Task status summary
        status_counts = {}
        for task in self.user_tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        queue_info.append("\n📊 任务状态统计:")
        for status, count in status_counts.items():
            queue_info.append(f"  {status}: {count}")
        
        self.queue_text.insert(tk.END, "\n".join(queue_info))
    
    def update_ui_timer(self):
        """Update UI periodically"""
        self.update_tasks_display()
        self.update_queue_display()
        self.root.after(3000, self.update_ui_timer)  # Update every 3 seconds
    
    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
    
    def clear_log(self):
        """Clear the log"""
        self.log_text.delete(1.0, tk.END)
        self.log("日志已清除")
    
    def save_log(self):
        """Save log to file"""
        try:
            log_content = self.log_text.get(1.0, tk.END)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scheduler_log_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            self.log(f"日志已保存到: {filename}")
            messagebox.showinfo("成功", f"日志已保存到: {filename}")
        except Exception as e:
            self.log(f"保存日志失败: {e}")
            messagebox.showerror("错误", f"保存日志失败: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SchedulerGUI(root)
    root.mainloop() 