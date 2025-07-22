import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import subprocess
import os
import glob
import time
import json
import sys
from datetime import datetime, timedelta
from enum import Enum
import traceback

# 语言配置
LANGUAGES = {
    'zh': {
        'title': 'EasyApply 多用户调度器',
        'schedule_config': '调度配置',
        'schedule_type': '调度类型：',
        'interval_minutes': '间隔(分钟)：',
        'daily_time': '每日时间(HH:MM)：',
        'task_delay': '任务间延迟(秒)：',
        'control_ops': '控制操作',
        'start_scheduler': '启动调度器',
        'stop_scheduler': '停止调度器',
        'refresh_tasks': '刷新任务列表',
        'run_queue_now': '立即执行队列',
        'reset_status': '重置任务状态',
        'force_stop_all': '🛑 强制停止所有任务',
        'task_selection': '任务选择与状态',
        'selected': '选择',
        'user_id': '用户ID',
        'status': '状态',
        'last_run': '上次运行',
        'next_run': '下次运行',
        'queue_status': '队列状态',
        'log_output': '日志输出',
        'language': '语言：',
        'scheduler_stopped': '调度器已停止',
        'scheduler_running': '调度器运行中',
        'no_executable_tasks': '没有可执行的任务',
        'tasks_in_queue': '个选中的任务正在运行或队列中',
        'no_selected_tasks': '没有选中的任务或所有选中任务都在运行中',
        'added_to_queue': '已将',
        'tasks_to_queue': '个任务加入队列',
        'reset_completed_tasks': '已重置',
        'completed_tasks_to_idle': '个已完成任务的状态为空闲',
        'no_reset_needed': '没有需要重置的已完成任务',
        'force_stopping_all': '🛑 强制停止所有任务...',
        'force_terminate_current': '强制终止当前任务：',
        'force_stop_complete': '✅ 强制停止完成：',
        'stopped_running_tasks': '停止了',
        'running_tasks': '个正在运行的任务',
        'cleared_queue_tasks': '清空了队列中的',
        'queue_tasks': '个任务',
        'reset_task_count': '重置了',
        'tasks_status': '个任务状态',
        'stop_complete_title': '停止完成',
        'stop_complete_msg': '已强制停止所有任务!',
        'stopped': '停止：',
        'cleared': '清空队列：',
        'reset': '重置：',
        'task_status': {
            'idle': '空闲',
            'queued': '队列中', 
            'running': '运行中',
            'success': '成功',
            'failed': '失败',
            'disabled': '已禁用'
        },
        'schedule_types': {
            'interval': '间隔执行',
            'daily': '每日定时', 
            'manual': '仅手动'
        }
    },
    'en': {
        'title': 'EasyApply Multi-User Scheduler',
        'schedule_config': 'Schedule Configuration',
        'schedule_type': 'Schedule Type:',
        'interval_minutes': 'Interval (minutes):',
        'daily_time': 'Daily Time (HH:MM):',
        'task_delay': 'Task Delay (seconds):',
        'control_ops': 'Control Operations',
        'start_scheduler': 'Start Scheduler',
        'stop_scheduler': 'Stop Scheduler',
        'refresh_tasks': 'Refresh Task List',
        'run_queue_now': 'Run Queue Now',
        'reset_status': 'Reset Task Status',
        'force_stop_all': '🛑 Force Stop All Tasks',
        'task_selection': 'Task Selection & Status',
        'selected': 'Selected',
        'user_id': 'User ID',
        'status': 'Status',
        'last_run': 'Last Run',
        'next_run': 'Next Run',
        'queue_status': 'Queue Status',
        'log_output': 'Log Output',
        'language': 'Language:',
        'scheduler_stopped': 'Scheduler Stopped',
        'scheduler_running': 'Scheduler Running',
        'no_executable_tasks': 'No executable tasks',
        'tasks_in_queue': 'selected tasks are running or queued',
        'no_selected_tasks': 'No selected tasks or all selected tasks are running',
        'added_to_queue': 'Added',
        'tasks_to_queue': 'tasks to queue',
        'reset_completed_tasks': 'Reset',
        'completed_tasks_to_idle': 'completed tasks status to idle',
        'no_reset_needed': 'No completed tasks need to be reset',
        'force_stopping_all': '🛑 Force stopping all tasks...',
        'force_terminate_current': 'Force terminate current task:',
        'force_stop_complete': '✅ Force stop complete:',
        'stopped_running_tasks': 'Stopped',
        'running_tasks': 'running tasks',
        'cleared_queue_tasks': 'Cleared',
        'queue_tasks': 'queued tasks',
        'reset_task_count': 'Reset',
        'tasks_status': 'task status',
        'stop_complete_title': 'Stop Complete',
        'stop_complete_msg': 'All tasks force stopped!',
        'stopped': 'Stopped:',
        'cleared': 'Cleared:',
        'reset': 'Reset:',
        'task_status': {
            'idle': 'Idle',
            'queued': 'Queued',
            'running': 'Running', 
            'success': 'Success',
            'failed': 'Failed',
            'disabled': 'Disabled'
        },
        'schedule_types': {
            'interval': 'Interval Execution',
            'daily': 'Daily Schedule',
            'manual': 'Manual Only'
        }
    }
}

class TaskStatus(Enum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DISABLED = "disabled"

class ScheduleType(Enum):
    INTERVAL = "interval"
    DAILY = "daily"
    MANUAL = "manual"

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
        
        # 语言配置
        self.language_settings_file = 'scheduler_language.json'
        self.current_language = self.load_language_setting()  # 加载保存的语言设置
        self.texts = LANGUAGES[self.current_language]
        
        self.root.title(self.texts['title'])
        self.root.geometry("1400x900")
        
        self.CONFIG_DIR = "configs"
        self.DEFAULT_CONFIG = "config.yaml"
        self.MAIN_SCRIPT = "main.py"
        
        self.user_tasks = {}
        self.task_queue = queue.Queue()
        self.log_queue = queue.Queue()
        self.current_running_task = None
        self.running = False
        self.scheduler_thread = None
        self.worker_thread = None
        self.last_task_finish_time = None
        
        # 调度配置
        self.schedule_type = ScheduleType.INTERVAL
        self.schedule_interval = 2  # hours
        self.daily_time = "08:00"
        
        self.setup_ui()
        self.load_user_configs()
        self.update_ui_timer()
        self.process_log_queue()  # Start the log processing loop
    
    def process_log_queue(self):
        """Process the log queue to update the GUI safely from other threads."""
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                timestamp = datetime.now().strftime("[%H:%M:%S]")
                log_message = f"{timestamp} {message}\n"
                self.log_text.insert(tk.END, log_message)
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_log_queue)
            
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(1, weight=1)
        
        # Language selector (top right)
        lang_frame = ttk.Frame(main_frame)
        lang_frame.grid(row=0, column=2, sticky=tk.E, pady=(0, 10))
        
        ttk.Label(lang_frame, text=self.texts['language']).grid(row=0, column=0, padx=(0, 5))
        # Set initial language display based on loaded setting
        initial_display = '中文' if self.current_language == 'zh' else 'English'
        self.language_var = tk.StringVar(value=initial_display)
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.language_var, 
                                values=['中文', 'English'], state="readonly", width=8)
        lang_combo.grid(row=0, column=1)
        lang_combo.bind('<<ComboboxSelected>>', self.on_language_change)
        
        # Title
        self.title_label = ttk.Label(main_frame, text=self.texts['title'], 
                               font=("Arial", 16, "bold"))
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Left panel - Configuration
        self.config_frame = ttk.LabelFrame(main_frame, text=self.texts['schedule_config'], padding="10")
        self.config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Schedule type selection
        self.schedule_type_label = ttk.Label(self.config_frame, text=self.texts['schedule_type'], font=("Arial", 10, "bold"))
        self.schedule_type_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.schedule_type_var = tk.StringVar(value=self.texts['schedule_types'][self.schedule_type.value])
        self.schedule_combo = ttk.Combobox(self.config_frame, textvariable=self.schedule_type_var, 
                                    values=list(self.texts['schedule_types'].values()), state="readonly", width=15)
        self.schedule_combo.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        self.schedule_combo.bind('<<ComboboxSelected>>', self.on_schedule_type_change)
        
        # Interval configuration
        self.interval_frame = ttk.LabelFrame(self.config_frame, text=self.texts['interval_minutes'], padding="5")
        self.interval_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.interval_label = ttk.Label(self.interval_frame, text=self.texts['interval_minutes'])
        self.interval_label.grid(row=0, column=0, sticky=tk.W)
        self.interval_var = tk.StringVar(value=str(self.schedule_interval))
        interval_entry = ttk.Entry(self.interval_frame, textvariable=self.interval_var, width=10)
        interval_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        # Daily time configuration
        self.daily_frame = ttk.LabelFrame(self.config_frame, text=self.texts['daily_time'], padding="5")
        self.daily_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.daily_label = ttk.Label(self.daily_frame, text=self.texts['daily_time'])
        self.daily_label.grid(row=0, column=0, sticky=tk.W)
        self.daily_time_var = tk.StringVar(value=self.daily_time)
        daily_time_entry = ttk.Entry(self.daily_frame, textvariable=self.daily_time_var, width=10)
        daily_time_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        self.daily_format_label = ttk.Label(self.daily_frame, text="(HH:MM)")
        self.daily_format_label.grid(row=1, column=0, columnspan=2, sticky=tk.W)
        
        # Queue configuration
        self.queue_config_frame = ttk.LabelFrame(self.config_frame, text=self.texts['task_delay'], padding="5")
        self.queue_config_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.delay_label = ttk.Label(self.queue_config_frame, text=self.texts['task_delay'])
        self.delay_label.grid(row=0, column=0, sticky=tk.W)
        self.task_delay_var = tk.StringVar(value="30")
        delay_entry = ttk.Entry(self.queue_config_frame, textvariable=self.task_delay_var, width=10)
        delay_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        # Control buttons
        self.control_buttons_frame = ttk.LabelFrame(self.config_frame, text=self.texts['control_ops'], padding="5")
        self.control_buttons_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_button = ttk.Button(self.control_buttons_frame, text=self.texts['start_scheduler'], 
                                     command=self.start_scheduler)
        self.start_button.grid(row=0, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        
        self.stop_button = ttk.Button(self.control_buttons_frame, text=self.texts['stop_scheduler'], 
                                    command=self.stop_scheduler, state=tk.DISABLED)
        self.stop_button.grid(row=1, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        
        self.refresh_button = ttk.Button(self.control_buttons_frame, text=self.texts['refresh_tasks'], 
                                  command=self.refresh_users)
        self.refresh_button.grid(row=2, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        
        self.run_queue_button = ttk.Button(self.control_buttons_frame, text=self.texts['run_queue_now'], 
                                    command=self.run_queue_now)
        self.run_queue_button.grid(row=3, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        
        self.reset_button = ttk.Button(self.control_buttons_frame, text=self.texts['reset_status'], 
                                command=self.reset_task_status)
        self.reset_button.grid(row=4, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        
        self.stop_all_button = ttk.Button(self.control_buttons_frame, text=self.texts['force_stop_all'], 
                                   command=self.force_stop_all_tasks)
        self.stop_all_button.grid(row=5, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        # self.stop_all_button.config(style="Danger.TButton")  # 使用醒目的样式
        
        # Configure column weight
        self.control_buttons_frame.columnconfigure(0, weight=1)
        
        # Status
        self.status_var = tk.StringVar(value=self.texts['scheduler_stopped'])
        self.status_label = ttk.Label(self.config_frame, textvariable=self.status_var, 
                                font=("Arial", 10, "bold"), foreground="red")
        self.status_label.grid(row=6, column=0, pady=(20, 0), sticky=tk.W)
        
        # Right panel - Task management
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)
        
        # Task selection frame
        self.task_selection_frame = ttk.LabelFrame(right_panel, text=self.texts['task_selection'], padding="10")
        self.task_selection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        self.task_selection_frame.columnconfigure(0, weight=1)
        self.task_selection_frame.rowconfigure(0, weight=1)
        
        # Tasks treeview with checkboxes
        self.column_keys = ["selected", "user_id", "status", "last_run", "next_run"]
        columns = (self.texts['selected'], self.texts['user_id'], self.texts['status'], self.texts['last_run'], self.texts['next_run'])
        self.tasks_tree = ttk.Treeview(self.task_selection_frame, columns=columns, show="headings", height=8)
        
        # Configure columns
        self.tasks_tree.heading(self.texts['selected'], text=self.texts['selected'])
        self.tasks_tree.column(self.texts['selected'], width=60)
        self.tasks_tree.heading(self.texts['user_id'], text=self.texts['user_id'])
        self.tasks_tree.column(self.texts['user_id'], width=150)
        self.tasks_tree.heading(self.texts['status'], text=self.texts['status'])
        self.tasks_tree.column(self.texts['status'], width=100)
        self.tasks_tree.heading(self.texts['last_run'], text=self.texts['last_run'])
        self.tasks_tree.column(self.texts['last_run'], width=140)
        self.tasks_tree.heading(self.texts['next_run'], text=self.texts['next_run'])
        self.tasks_tree.column(self.texts['next_run'], width=140)
        
        # Bind double-click to toggle selection
        self.tasks_tree.bind('<Double-1>', self.toggle_task_selection)
        
        # Scrollbar for treeview
        tasks_scrollbar = ttk.Scrollbar(self.task_selection_frame, orient=tk.VERTICAL, 
                                       command=self.tasks_tree.yview)
        self.tasks_tree.configure(yscrollcommand=tasks_scrollbar.set)
        
        self.tasks_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tasks_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Task control buttons
        task_control_frame = ttk.Frame(self.task_selection_frame)
        task_control_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky=tk.W)
        
        select_all_text = "Select All" if self.current_language == 'en' else "全选"
        deselect_all_text = "Deselect All" if self.current_language == 'en' else "全不选"
        run_selected_text = "Run Selected" if self.current_language == 'en' else "运行选中"
        stop_current_text = "Stop Current" if self.current_language == 'en' else "停止当前"
        
        self.select_all_btn = ttk.Button(task_control_frame, text=select_all_text, 
                  command=self.select_all_tasks)
        self.select_all_btn.grid(row=0, column=0)
        self.deselect_all_btn = ttk.Button(task_control_frame, text=deselect_all_text, 
                  command=self.deselect_all_tasks)
        self.deselect_all_btn.grid(row=0, column=1, padx=(10, 0))
        self.run_selected_btn = ttk.Button(task_control_frame, text=run_selected_text, 
                  command=self.run_selected_task)
        self.run_selected_btn.grid(row=0, column=2, padx=(10, 0))
        self.stop_current_btn = ttk.Button(task_control_frame, text=stop_current_text, 
                  command=self.stop_current_task)
        self.stop_current_btn.grid(row=0, column=3, padx=(10, 0))
        
        # Queue status frame
        self.queue_frame = ttk.LabelFrame(right_panel, text=self.texts['queue_status'], padding="10")
        self.queue_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.queue_frame.columnconfigure(0, weight=1)
        self.queue_frame.rowconfigure(0, weight=1)
        
        # Queue display
        self.queue_text = scrolledtext.ScrolledText(self.queue_frame, height=6, width=60)
        self.queue_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Log frame
        self.log_frame = ttk.LabelFrame(main_frame, text=self.texts['log_output'], padding="10")
        self.log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=12, width=120)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Log control
        log_control_frame = ttk.Frame(self.log_frame)
        log_control_frame.grid(row=1, column=0, pady=(10, 0), sticky=tk.W)
        
        clear_log_text = "Clear Log" if self.current_language == 'en' else "清除日志"
        save_log_text = "Save Log" if self.current_language == 'en' else "保存日志"
        
        self.clear_log_btn = ttk.Button(log_control_frame, text=clear_log_text, 
                  command=self.clear_log)
        self.clear_log_btn.grid(row=0, column=0)
        self.save_log_btn = ttk.Button(log_control_frame, text=save_log_text, 
                  command=self.save_log)
        self.save_log_btn.grid(row=0, column=1, padx=(10, 0))
        
        # Initialize UI state
        self.on_schedule_type_change(None)
    
    def on_schedule_type_change(self, event):
        """Handle schedule type change"""
        selected_display_text = self.schedule_type_var.get()
        
        # Find the schedule type key based on display text
        selected_type_key = None
        for key, display_text in self.texts['schedule_types'].items():
            if display_text == selected_display_text:
                selected_type_key = key
                break
        
        # Update the actual schedule type
        if selected_type_key:
            for schedule_type in ScheduleType:
                if schedule_type.value == selected_type_key:
                    self.schedule_type = schedule_type
                    break
        
        # Show/hide appropriate frames
        if selected_type_key == 'interval':
            self.interval_frame.grid()
            self.daily_frame.grid_remove()
        elif selected_type_key == 'daily':
            self.interval_frame.grid_remove()
            self.daily_frame.grid()
        else:  # manual
            self.interval_frame.grid_remove()
            self.daily_frame.grid_remove()
    
    def load_user_configs(self):
        """Load all available user configurations"""
        config_files = []
        
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
                self.log(f"Added user: {user_id} ({config_path})")
        
        # Remove tasks for configs that no longer exist
        to_remove = []
        for user_id, task in self.user_tasks.items():
            if not os.path.exists(task.config_path):
                to_remove.append(user_id)
        
        for user_id in to_remove:
            del self.user_tasks[user_id]
            self.log(f"Removed user: {user_id} (config file not found)")
        
        self.update_tasks_display()
        self.update_queue_display()
    
    def get_user_id_from_config(self, config_path):
        """Extract user ID from config file path"""
        filename = os.path.basename(config_path)
        return filename.replace('.yaml', '')
    
    def refresh_users(self):
        """Refresh user list"""
        self.load_user_configs()
        self.log("Task list refreshed")
    
    def toggle_task_selection(self, event):
        """Toggle task selection on double-click"""
        selection = self.tasks_tree.selection()
        if not selection:
            return
        
        item = self.tasks_tree.item(selection[0])
        user_id = item['values'][1]  # User ID is in column 1 (after selected column)
        task = self.user_tasks.get(user_id)
        
        if task:
            task.selected = not task.selected
            self.log(f"Task {user_id} {'selected' if task.selected else 'deselected'}")
            # Recalculate next run time when selection changes
            if self.running:  # Only if scheduler is running
                self.calculate_next_run_time_for_task(task)
            self.update_tasks_display()
    
    def select_all_tasks(self):
        """Select all tasks"""
        for task in self.user_tasks.values():
            task.selected = True
        self.log("All tasks selected")
        # Recalculate next run times when all tasks are selected
        if self.running:  # Only if scheduler is running
            for task in self.user_tasks.values():
                self.calculate_next_run_time_for_task(task)
        self.update_tasks_display()
    
    def deselect_all_tasks(self):
        """Deselect all tasks"""
        for task in self.user_tasks.values():
            task.selected = False
        self.log("All tasks deselected")
        # Recalculate next run times when all tasks are deselected
        if self.running:  # Only if scheduler is running
            for task in self.user_tasks.values():
                self.calculate_next_run_time_for_task(task)
        self.update_tasks_display()
    
    def start_scheduler(self):
        """Start the task scheduler"""
        # Validate configuration
        try:
            schedule_display_text = self.schedule_type_var.get()
            
            # Convert display text to schedule type key
            schedule_type_key = None
            for key, display_text in self.texts['schedule_types'].items():
                if display_text == schedule_display_text:
                    schedule_type_key = key
                    break
            
            if not schedule_type_key:
                raise ValueError("Invalid schedule type selected")
            
            if schedule_type_key == 'interval':
                self.schedule_interval = float(self.interval_var.get())
                if self.schedule_interval <= 0:
                    raise ValueError("Interval must be greater than 0")
                    
            elif schedule_type_key == 'daily':
                time_str = self.daily_time_var.get()
                # Validate time format
                try:
                    datetime.strptime(time_str, "%H:%M")
                    self.daily_time = time_str
                except ValueError:
                    raise ValueError("Invalid time format, please use HH:MM format")
                    
        except ValueError as e:
            messagebox.showerror("Error", f"Configuration error: {e}")
            return
        
        # Set schedule type using the enum key
        for schedule_type in ScheduleType:
            if schedule_type.value == schedule_type_key:
                self.schedule_type = schedule_type
                break
        self.running = True
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker_thread.start()
        
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Use localized schedule type text for status display
        schedule_display_text = self.texts['schedule_types'][schedule_type_key]
        status_text = f"{self.texts['scheduler_running']} ({schedule_display_text})"
        self.status_var.set(status_text)
        
        # Set next run times based on schedule type
        self.calculate_next_run_times()
        
        self.log(f"Scheduler started - {schedule_display_text}")
    
    def calculate_next_run_times(self):
        """Calculate next run times based on schedule type"""
        now = datetime.now()
        
        if self.schedule_type == ScheduleType.INTERVAL:
            next_run_time = now + timedelta(minutes=self.schedule_interval)
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

    def calculate_next_run_time_for_task(self, task):
        """Calculate next run time for a single task after completion"""
        if not task.selected:
            # Clear next run time for unselected tasks
            task.next_run = None
            return
            
        now = datetime.now()
        
        if self.schedule_type == ScheduleType.INTERVAL:
            # Next run is current time + interval
            task.next_run = now + timedelta(minutes=self.schedule_interval)
            
        elif self.schedule_type == ScheduleType.DAILY:
            # Calculate next daily run time
            today = now.date()
            target_time = datetime.combine(today, datetime.strptime(self.daily_time, "%H:%M").time())
            
            # If today's time has passed, schedule for tomorrow
            if target_time <= now:
                target_time += timedelta(days=1)
            
            task.next_run = target_time
            
        elif self.schedule_type == ScheduleType.MANUAL:
            # Manual mode - clear next run time
            task.next_run = None
    
    def stop_scheduler(self):
        """Stop the task scheduler"""
        self.running = False
        
        # Stop current running task
        if self.current_running_task and self.current_running_task.process:
            try:
                self.current_running_task.process.terminate()
                # Wait for process to terminate
                try:
                    self.current_running_task.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.current_running_task.process.kill()
                    self.log(f"Force terminating task: {self.current_running_task.user_id}")
                
                self.current_running_task.status = TaskStatus.IDLE
                self.current_running_task = None
            except Exception as e:
                self.log(f"Failed to stop task: {e}")
        
        # Clear queue and reset all queued tasks to IDLE
        while not self.task_queue.empty():
            try:
                task = self.task_queue.get_nowait()
                if task.status == TaskStatus.QUEUED:
                    task.status = TaskStatus.IDLE
            except:
                break
        
        # Reset all running tasks to IDLE
        for task in self.user_tasks.values():
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.IDLE
        
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Scheduler stopped")
        
        self.log("Scheduler stopped, all task statuses reset")
        self.update_queue_display()
    
    def scheduler_loop(self):
        """Main scheduler loop - checks each task independently."""
        while self.running:
            if self.schedule_type == ScheduleType.MANUAL:
                self.interruptible_sleep(60)
                continue

            now = datetime.now()
            
            for task in self.user_tasks.values():
                if not task.selected or not task.next_run:
                    continue
                
                if now >= task.next_run and task.status not in [TaskStatus.RUNNING, TaskStatus.QUEUED]:
                    self.log(f"Scheduler queuing task: {task.user_id}")
                    task.status = TaskStatus.QUEUED
                    self.task_queue.put(task)
                    self.update_queue_display()

                    # Immediately calculate the next run time for this task,
                    # so it doesn't get queued again in the next loop.
                    self.calculate_next_run_time_for_task(task)

            self.interruptible_sleep(10)  # Check every 10 seconds
        
        self.log("Scheduler loop stopped")
    
    def interruptible_sleep(self, duration, step=0.1):
        """Sleep for a duration, but check for stop signal periodically."""
        slept_time = 0
        while slept_time < duration and self.running:
            time.sleep(step)
            slept_time += step

    def worker_loop(self):
        """Worker loop to process task queue."""
        self.log("Worker thread started")
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                
                if not self.running:
                    self.task_queue.task_done()
                    break

                self.current_running_task = task
                self.run_single_task(task)
                
                # Post-execution logic
                self.last_task_finish_time = datetime.now()
                self.current_running_task = None
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.log(f"Critical Worker thread error: {e}\n{traceback.format_exc()}")
                if self.current_running_task:
                    try:
                        self.task_queue.task_done()
                    except: pass
                    self.current_running_task = None
                time.sleep(1) 
        
        self.log("Worker thread stopped")
    
    def queue_selected_tasks(self):
        """Add selected tasks to queue"""
        # Get selected tasks that are not currently running or queued
        selected_tasks = []
        for task in self.user_tasks.values():
            if task.selected and task.status not in [TaskStatus.RUNNING, TaskStatus.QUEUED]:
                # Reset completed tasks to allow re-execution
                if task.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
                    task.status = TaskStatus.IDLE
                selected_tasks.append(task)
        
        if not selected_tasks:
            # Check if there are selected tasks that are running/queued
            running_or_queued = [task for task in self.user_tasks.values() 
                               if task.selected and task.status in [TaskStatus.RUNNING, TaskStatus.QUEUED]]
            if running_or_queued:
                msg = f"There are {len(running_or_queued)} {self.texts['tasks_in_queue']}" if self.current_language == 'en' else f"有 {len(running_or_queued)} {self.texts['tasks_in_queue']}"
                self.log(msg)
            else:
                self.log(self.texts['no_selected_tasks'])
            return
        
        for task in selected_tasks:
            task.status = TaskStatus.QUEUED
            self.task_queue.put(task)
        
        msg = f"{self.texts['added_to_queue']} {len(selected_tasks)} {self.texts['tasks_to_queue']}"
        self.log(msg)
        self.update_queue_display()
    
    def run_queue_now(self):
        """Run queue immediately"""
        self.queue_selected_tasks()
    
    def reset_task_status(self):
        """Reset all completed task status to IDLE"""
        reset_count = 0
        for task in self.user_tasks.values():
            if task.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
                task.status = TaskStatus.IDLE
                reset_count += 1
        
        if reset_count > 0:
            msg = f"{self.texts['reset_completed_tasks']} {reset_count} {self.texts['completed_tasks_to_idle']}"
            self.log(msg)
        else:
            self.log(self.texts['no_reset_needed'])
        
        self.update_tasks_display()
    
    def force_stop_all_tasks(self):
        """Force stop all running tasks and clear queue"""
        self.log(self.texts['force_stopping_all'])
        
        stopped_count = 0
        queue_cleared = 0
        
        # 1. Force stop current running task
        if self.current_running_task and self.current_running_task.process:
            try:
                msg = f"{self.texts['force_terminate_current']} {self.current_running_task.user_id}"
                self.log(msg)
                self.current_running_task.process.kill()  # 直接kill，不等待
                self.current_running_task.status = TaskStatus.IDLE
                # Keep task selected so it can be rescheduled by the scheduler
                # Update last finish time to ensure proper delay before next scheduling
                self.last_task_finish_time = datetime.now()
                self.current_running_task = None
                stopped_count += 1
            except Exception as e:
                self.log(f"Force stop current task failed: {e}")
        
        # 2. Clear entire queue
        while not self.task_queue.empty():
            try:
                task = self.task_queue.get_nowait()
                task.status = TaskStatus.IDLE
                # Keep queued tasks selected so they can be rescheduled
                queue_cleared += 1
            except:
                break
        
        # 3. Reset all task status to IDLE
        reset_count = 0
        for task in self.user_tasks.values():
            if task.status in [TaskStatus.RUNNING, TaskStatus.QUEUED]:
                task.status = TaskStatus.IDLE
                # Keep tasks selected so scheduler can reschedule them if still running
                reset_count += 1
                
                # If task has a process, kill it
                if hasattr(task, 'process') and task.process:
                    try:
                        task.process.kill()
                        task.process = None
                    except:
                        pass
        
        # 4. Report results
        self.log(self.texts['force_stop_complete'])
        if stopped_count > 0:
            msg = f"  - {self.texts['stopped_running_tasks']} {stopped_count} {self.texts['running_tasks']}"
            self.log(msg)
        if queue_cleared > 0:
            msg = f"  - {self.texts['cleared_queue_tasks']} {queue_cleared} {self.texts['queue_tasks']}"
            self.log(msg)
        if reset_count > 0:
            msg = f"  - {self.texts['reset_task_count']} {reset_count} {self.texts['tasks_status']}"
            self.log(msg)
        
        # 5. Update display
        self.update_queue_display()
        self.update_tasks_display()  # Update task selection status display
        
        # 6. Recalculate next run times for all selected tasks
        for task in self.user_tasks.values():
            if task.selected:
                self.calculate_next_run_time_for_task(task)
        
        dialog_msg = f"{self.texts['stop_complete_msg']}\n{self.texts['stopped']} {stopped_count}, {self.texts['cleared']} {queue_cleared}, {self.texts['reset']} {reset_count}"
        messagebox.showinfo(self.texts['stop_complete_title'], dialog_msg)
    
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
                messagebox.showinfo("Info", f"Task {user_id} is currently running")
            elif task.status == TaskStatus.QUEUED:
                messagebox.showinfo("Info", f"Task {user_id} is already in queue")
            else:
                task.status = TaskStatus.QUEUED
                self.task_queue.put(task)
                self.log(f"Added task {user_id} to queue")
                self.update_queue_display()
    
    def stop_current_task(self):
        """Stop current running task"""
        if self.current_running_task and self.current_running_task.process:
            try:
                self.current_running_task.process.terminate()
                self.current_running_task.status = TaskStatus.IDLE
                # Keep task selected so it can be rescheduled in the next cycle
                # Update last finish time to ensure proper delay before next scheduling
                self.last_task_finish_time = datetime.now()
                
                # Recalculate next run time based on manual stop time
                stopped_task = self.current_running_task
                self.current_running_task = None
                self.calculate_next_run_time_for_task(stopped_task)
                
                self.log(f"Stopped task: {stopped_task.user_id}")
                # Update the display to reflect the current state
                self.update_tasks_display()
            except Exception as e:
                self.log(f"Failed to stop task: {e}")
        else:
            messagebox.showinfo("Info", "No task currently running")
    
    def run_single_task(self, task):
        """Run a single task in a separate process and handle its I/O non-blockingly."""
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        self.log(f"Starting task: {task.user_id}")
        
        try:
            # Use sys.executable to ensure the correct Python interpreter is used
            # Set creationflags to CREATE_NO_WINDOW on Windows to hide the console
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            
            process = subprocess.Popen(
                [sys.executable, "-u", self.MAIN_SCRIPT, "--config", task.config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # Read as bytes to handle any encoding
                creationflags=creationflags
            )
            task.process = process
            
            # Start daemon threads to read stdout and stderr to prevent blocking
            stdout_thread = threading.Thread(
                target=self.read_stream_to_queue, 
                args=(process.stdout, task.user_id), 
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=self.read_stream_to_queue, 
                args=(process.stderr, task.user_id), 
                daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()

            # The worker_loop will wait for the task to finish without blocking the GUI
            # We don't call process.wait() here to keep the worker responsive
            while process.poll() is None:
                if not self.running:
                    task.process.terminate()
                    self.log(f"Terminated task {task.user_id} due to scheduler stop.")
                    break
                time.sleep(0.5)

            # Threads will exit automatically as they are daemons

            return_code = process.poll()
            if return_code == 0:
                task.status = TaskStatus.SUCCESS
                self.log(f"Task {task.user_id} completed successfully.")
            else:
                task.status = TaskStatus.FAILED
                self.log(f"Task {task.user_id} failed with return code: {return_code}")
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            self.log(f"Task {task.user_id} execution error: {e}\n{traceback.format_exc()}")
            
        finally:
            task.process = None
            # This logic must be here to ensure it runs after every task execution
            if self.running:
                self.calculate_next_run_time_for_task(task)
            self.update_tasks_display()
    
    def read_stream_to_queue(self, stream, user_id):
        """Read lines from a stream and put them into the log queue."""
        try:
            for line in iter(stream.readline, b''):
                if not self.running:
                    break
                decoded_line = f"[{user_id}] {line.decode('utf-8', errors='ignore').strip()}"
                self.log_queue.put(decoded_line)
        except Exception as e:
            self.log_queue.put(f"[SYSTEM] Error reading stream for {user_id}: {e}")
        finally:
            stream.close()

    def update_tasks_display(self):
        """Update the tasks display"""
        # Save current selection
        selected_items = self.tasks_tree.selection()
        selected_user_ids = []
        for item in selected_items:
            item_values = self.tasks_tree.item(item)['values']
            if len(item_values) > 1:
                selected_user_ids.append(item_values[1])  # User ID is in column 1 (after selected column)
        
        # Clear existing items
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)
        
        # Add current tasks
        items_to_reselect = []
        for task in self.user_tasks.values():
            selected = "✓" if task.selected else "○"
            
            # Localized text for never run and not planned
            never_run_text = "Never Run" if self.current_language == 'en' else "从未运行"
            not_planned_text = "Not Planned" if self.current_language == 'en' else "未计划"
            
            last_run = task.last_run.strftime("%m-%d %H:%M") if task.last_run else never_run_text
            next_run = task.next_run.strftime("%m-%d %H:%M") if task.next_run else not_planned_text
            
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
            
            # Use localized status text
            localized_status = self.get_localized_status(task.status)
            
            item = self.tasks_tree.insert('', 'end', values=(
                selected,
                task.user_id,
                localized_status,
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
            queue_info.append(f"🔄 Running: {self.current_running_task.user_id}")
        
        # Queued tasks
        queue_size = self.task_queue.qsize()
        if queue_size > 0:
            queue_info.append(f"⏳ Tasks in queue: {queue_size}")
            
        # Selected tasks summary
        selected_count = sum(1 for task in self.user_tasks.values() if task.selected)
        total_count = len(self.user_tasks)
        queue_info.append(f"📋 Selected tasks: {selected_count}/{total_count}")
        
        # Task status summary
        status_counts = {}
        for task in self.user_tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        queue_info.append("\n📊 Task Status Summary:")
        for status, count in status_counts.items():
            queue_info.append(f"  {status}: {count}")
        
        self.queue_text.insert(tk.END, "\n".join(queue_info))
    
    def update_ui_timer(self):
        """Update UI periodically"""
        self.update_tasks_display()
        self.update_queue_display()
        self.root.after(3000, self.update_ui_timer)  # Update every 3 seconds
    
    def log(self, message):
        """Add message to the thread-safe log queue."""
        self.log_queue.put(message)
    
    def clear_log(self):
        """Clear the log"""
        self.log_text.delete(1.0, tk.END)
        self.log("Log cleared")
    
    def save_log(self):
        """Save log to file"""
        try:
            log_content = self.log_text.get(1.0, tk.END)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scheduler_log_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            self.log(f"Log saved to: {filename}")
            messagebox.showinfo("Success", f"Log saved to: {filename}")
        except Exception as e:
            self.log(f"Failed to save log: {e}")
            messagebox.showerror("Error", f"Failed to save log: {e}")
    
    def load_language_setting(self):
        """Load saved language setting, default to English"""
        try:
            if os.path.exists(self.language_settings_file):
                with open(self.language_settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    language = settings.get('language', 'en')
                    print(f"Loaded language setting: {language}")
                    return language
        except Exception as e:
            print(f"Failed to load language setting: {e}")
        
        # Default to English
        print("Using default language: English")
        return 'en'
    
    def save_language_setting(self, language):
        """Save current language setting"""
        try:
            settings = {'language': language}
            with open(self.language_settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            print(f"Saved language setting: {language}")
        except Exception as e:
            print(f"Failed to save language setting: {e}")
    
    def on_language_change(self, event):
        """Handle language change"""
        selected_lang = self.language_var.get()
        new_lang = 'zh' if selected_lang == '中文' else 'en'
        
        if new_lang != self.current_language:
            self.current_language = new_lang
            self.texts = LANGUAGES[self.current_language]
            self.save_language_setting(new_lang)  # 保存语言设置
            self.update_ui_texts()
    
    def update_ui_texts(self):
        """Update all UI texts based on current language"""
        # Update window title
        self.root.title(self.texts['title'])
        
        # Update main title
        self.title_label.config(text=self.texts['title'])
        
        # Update config frame
        self.config_frame.config(text=self.texts['schedule_config'])
        self.schedule_type_label.config(text=self.texts['schedule_type'])
        
        # Update schedule combo values
        # Use the actual schedule_type enum value instead of display text to avoid language mismatch
        current_schedule_key = self.schedule_type.value
        
        # Update combobox values
        self.schedule_combo.config(values=list(self.texts['schedule_types'].values()))
        # Set the display value based on the current schedule type
        if current_schedule_key in self.texts['schedule_types']:
            self.schedule_type_var.set(self.texts['schedule_types'][current_schedule_key])
        
        # Update treeview column headers
        if hasattr(self, 'tasks_tree'):
            columns = [self.texts['selected'], self.texts['user_id'], self.texts['status'], self.texts['last_run'], self.texts['next_run']]
            self.tasks_tree.config(columns=columns)
            
            self.tasks_tree.heading(self.texts['selected'], text=self.texts['selected'])
            self.tasks_tree.heading(self.texts['user_id'], text=self.texts['user_id'])
            self.tasks_tree.heading(self.texts['status'], text=self.texts['status'])
            self.tasks_tree.heading(self.texts['last_run'], text=self.texts['last_run'])
            self.tasks_tree.heading(self.texts['next_run'], text=self.texts['next_run'])
        
        # Update other UI elements
        self.update_ui_elements_texts()
        
        # Update status
        if hasattr(self, 'status_var'):
            current_status = self.status_var.get()
            if "运行中" in current_status or "Running" in current_status:
                self.status_var.set(self.texts['scheduler_running'])
            else:
                self.status_var.set(self.texts['scheduler_stopped'])
        
        # Update task display
        self.update_tasks_display()
        self.update_queue_display()
    
    def update_ui_elements_texts(self):
        """Update UI element texts that need to be stored as attributes"""
        # Update button texts if they exist
        if hasattr(self, 'start_button'):
            self.start_button.config(text=self.texts['start_scheduler'])
        if hasattr(self, 'stop_button'):
            self.stop_button.config(text=self.texts['stop_scheduler'])
        if hasattr(self, 'refresh_button'):
            self.refresh_button.config(text=self.texts['refresh_tasks'])
        if hasattr(self, 'run_queue_button'):
            self.run_queue_button.config(text=self.texts['run_queue_now'])
        if hasattr(self, 'reset_button'):
            self.reset_button.config(text=self.texts['reset_status'])
        if hasattr(self, 'stop_all_button'):
            self.stop_all_button.config(text=self.texts['force_stop_all'])
        
        # Update task control buttons
        if hasattr(self, 'select_all_btn'):
            select_all_text = "Select All" if self.current_language == 'en' else "全选"
            self.select_all_btn.config(text=select_all_text)
        if hasattr(self, 'deselect_all_btn'):
            deselect_all_text = "Deselect All" if self.current_language == 'en' else "全不选"
            self.deselect_all_btn.config(text=deselect_all_text)
        if hasattr(self, 'run_selected_btn'):
            run_selected_text = "Run Selected" if self.current_language == 'en' else "运行选中"
            self.run_selected_btn.config(text=run_selected_text)
        if hasattr(self, 'stop_current_btn'):
            stop_current_text = "Stop Current" if self.current_language == 'en' else "停止当前"
            self.stop_current_btn.config(text=stop_current_text)
        
        # Update log control buttons
        if hasattr(self, 'clear_log_btn'):
            clear_log_text = "Clear Log" if self.current_language == 'en' else "清除日志"
            self.clear_log_btn.config(text=clear_log_text)
        if hasattr(self, 'save_log_btn'):
            save_log_text = "Save Log" if self.current_language == 'en' else "保存日志"
            self.save_log_btn.config(text=save_log_text)
        
        # Update frame texts
        if hasattr(self, 'control_buttons_frame'):
            self.control_buttons_frame.config(text=self.texts['control_ops'])
        if hasattr(self, 'task_selection_frame'):
            self.task_selection_frame.config(text=self.texts['task_selection'])
        if hasattr(self, 'queue_frame'):
            self.queue_frame.config(text=self.texts['queue_status'])
        if hasattr(self, 'log_frame'):
            self.log_frame.config(text=self.texts['log_output'])
        if hasattr(self, 'interval_frame'):
            self.interval_frame.config(text=self.texts['interval_minutes'])
        if hasattr(self, 'daily_frame'):
            self.daily_frame.config(text=self.texts['daily_time'])
        if hasattr(self, 'queue_config_frame'):
            self.queue_config_frame.config(text=self.texts['task_delay'])
        
        # Update labels
        if hasattr(self, 'interval_label'):
            self.interval_label.config(text=self.texts['interval_minutes'])
        if hasattr(self, 'daily_label'):
            self.daily_label.config(text=self.texts['daily_time'])
        if hasattr(self, 'delay_label'):
            self.delay_label.config(text=self.texts['task_delay'])
    
    def get_localized_status(self, status):
        """Get localized status text"""
        if isinstance(status, TaskStatus):
            return self.texts['task_status'][status.value]
        return status

if __name__ == "__main__":
    root = tk.Tk()
    app = SchedulerGUI(root)
    root.mainloop() 