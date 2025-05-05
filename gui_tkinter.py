import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import yaml
import subprocess
import sys
import os
import threading
import webbrowser
import collections.abc # Used for deep update
import traceback
import time
import json

CONFIG_FILE = "config.yaml"
# DEFAULT_CONFIG now primarily defines structure and default *values* if a key *exists* but has no value,
# or if the config file is entirely missing. It's less about forcing specific keys onto the user's config.
DEFAULT_CONFIG = {
    'email': '', 'password': '', 'openaiApiKey': '', 'disableAntiLock': False, 'remote': False,
    'lessthanTenApplicants': True, 'newestPostingsFirst': False,
    'experienceLevel': {'internship': False, 'entry': True, 'associate': True, 'mid-senior level': True, 'director': False, 'executive': False},
    'jobTypes': {'full-time': True, 'contract': True, 'part-time': False, 'temporary': True, 'internship': False, 'other': False, 'volunteer': False},
    'date': {'all time': True, 'month': False, 'week': False, '24 hours': False},
    'positions': ['sales'], 'locations': ['中国'], 'residentStatus': False, 'distance': 100,
    'outputFileDirectory': '~/Documents/EasyApplyBot/', 'companyBlacklist': [], 'titleBlacklist': [], 'posterBlacklist': [],
    'uploads': {'resume': ''},
    'checkboxes': {'driversLicence': True, 'requireVisa': False, 'legallyAuthorized': False, 'certifiedProfessional': True, 'urgentFill': True, 'commute': True, 'remote': True, 'drugTest': True, 'assessment': True, 'securityClearance': False, 'degreeCompleted': ["High School Diploma", "Bachelor's Degree"], 'backgroundCheck': True},
    'universityGpa': 4.0, 'salaryMinimum': 65000, 'languages': {'english': 'Native or bilingual'},
    'noticePeriod': 2, 'experience': {'default': 0}, 'personalInfo': {}, 'eeo': {}, 'textResume': '',
    'evaluateJobFit': False, 'debug': False,
    'customQuestions': {}  # 自定义问答配置
}

STANDARD_DEGREES = ["High School Diploma", "Associate's Degree", "Bachelor's Degree", "Master's Degree", "Master of Business Administration", "Doctor of Philosophy", "Doctor of Medicine", "Doctor of Law"]
LANGUAGE_LEVELS = ['None', 'Conversational', 'Professional', 'Native or bilingual']

# --- Configuration Handling --- (Keep robust loading/saving)
def deep_update(source, overrides):
    for key, value in overrides.items():
        if key not in source: source[key] = value
        elif isinstance(value, collections.abc.Mapping) and isinstance(source.get(key), collections.abc.Mapping): deep_update(source[key], value)
        elif isinstance(value, list) and key in source: source[key] = value # Overwrite lists
        else: source[key] = value
    return source

def load_config():
    final_config = {}
    for k, v in DEFAULT_CONFIG.items():
         if isinstance(v, (dict, list)): final_config[k] = v.copy()
         else: final_config[k] = v
    if not os.path.exists(CONFIG_FILE): print(f"配置文件 {CONFIG_FILE} 不存在..."); save_config(final_config); return final_config # Return default if file missing
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as stream:
            loaded_config = yaml.safe_load(stream)
            if not loaded_config: print(f"配置文件 {CONFIG_FILE} 为空..."); return final_config # Return default if file empty
        # IMPORTANT: Update the defaults with loaded config, preserving structure
        deep_update(final_config, loaded_config)
        # Ensure essential nested dicts/lists exist if missing in file but expected by GUI/defaults
        for key, default_val in DEFAULT_CONFIG.items():
             if key not in final_config:
                 if isinstance(default_val, (dict, list)): final_config[key] = default_val.copy()
                 else: final_config[key] = default_val
             # Ensure type consistency for critical nested structures
             elif isinstance(default_val, dict) and not isinstance(final_config[key], dict):
                 final_config[key] = default_val.copy()
             elif isinstance(default_val, list) and not isinstance(final_config[key], list):
                  final_config[key] = default_val.copy()

        # Ensure 'default' exists in experience
        if 'experience' not in final_config or not isinstance(final_config['experience'], dict):
             final_config['experience'] = {'default': 0}
        elif 'default' not in final_config['experience']:
             final_config['experience']['default'] = 0


        return final_config
    except yaml.YAMLError as exc: messagebox.showerror("配置错误", f"读取配置文件时出错: {exc}"); return final_config # Return merged defaults on error
    except Exception as e: messagebox.showerror("错误", f"加载配置时发生未知错误: {e}"); return final_config

def save_config(config):
    try:
        config_to_save = {} # Use a clean dict to ensure order from config
        for k, v in config.items():
            # Ensure nested structures are copied properly for saving
            if isinstance(v, dict): config_to_save[k] = v.copy()
            elif isinstance(v, list): config_to_save[k] = v.copy()
            else: config_to_save[k] = v
            
        with open(CONFIG_FILE, 'w', encoding='utf-8') as stream:
            yaml.dump(config_to_save, stream, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return True
    except Exception as e: messagebox.showerror("保存错误", f"无法保存配置: {e}"); return False

def safe_join_list(config_value):
    if isinstance(config_value, list): return '\n'.join(map(str, config_value))
    return ''

def parse_list_from_textarea(text_content):
    return [line.strip() for line in text_content.strip().split('\n') if line.strip()]

def save_config_to_yaml(config_data):
    """Save configuration to config.yaml"""
    with open('config.yaml', 'w', encoding='utf-8') as file:
        yaml.dump(config_data, file, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return True

# --- Helper Functions ---
def parse_list_from_textarea(text_content):
    return [line.strip() for line in text_content.strip().split('\n') if line.strip()]
# Removed parse_dict_from_textarea as it's no longer used for experience, lang, etc.


# --- GUI Class ---
class EasyApplyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LinkedIn Easy Apply Bot - 配置工具 v3 (Tkinter)") # Version bump in title
        self.geometry("900x800")

        self.config = load_config()
        
        # 特殊处理customQuestions，确保问题文本正确解析
        if 'customQuestions' in self.config and self.config['customQuestions']:
            processed_questions = {}
            for q, a in self.config['customQuestions'].items():
                # 处理可能的双引号字符串
                question = q
                answer = a
                if isinstance(question, str) and question.startswith('"') and question.endswith('"'):
                    try:
                        question = json.loads(question)
                    except:
                        print(f"无法解析问题字符串: {question}")
                if isinstance(answer, str) and answer.startswith('"') and answer.endswith('"'):
                    try:
                        answer = json.loads(answer)
                    except:
                        print(f"无法解析答案字符串: {answer}")
                processed_questions[question] = answer
            self.config['customQuestions'] = processed_questions
            
        self.bot_process = None

        # --- Variables --- (Grouped for clarity)
        self.vars = {
            # Basic
            'email': tk.StringVar(value=self.config.get('email', '')), 'password': tk.StringVar(value=self.config.get('password', '')),
            'openaiApiKey': tk.StringVar(value=self.config.get('openaiApiKey', '')),
            'resume_path': tk.StringVar(value=self.config.get('uploads', {}).get('resume', '')),
            'textResume_path': tk.StringVar(value=self.config.get('textResume', '')),
            'disableAntiLock': tk.BooleanVar(value=self.config.get('disableAntiLock', False)),
            # Job
            'positions': tk.StringVar(value=safe_join_list(self.config.get('positions', []))),
            'locations': tk.StringVar(value=safe_join_list(self.config.get('locations', []))),
            'distance': tk.IntVar(value=self.config.get('distance', 100)),
            'search_remote': tk.BooleanVar(value=self.config.get('remote', False)),
            'lessthanTenApplicants': tk.BooleanVar(value=self.config.get('lessthanTenApplicants', True)),
            'newestPostingsFirst': tk.BooleanVar(value=self.config.get('newestPostingsFirst', False)),
            'residentStatus': tk.BooleanVar(value=self.config.get('residentStatus', False)),
            # Preferences (Dynamic Checkboxes/Radio)
            'exp_level': {}, 'job_type': {}, 'date_pref': tk.StringVar(value=self._get_current_date_pref()),
            # Advanced - Simple & Blacklists
            'companyBlacklist': tk.StringVar(value=safe_join_list(self.config.get('companyBlacklist', []))),
            'titleBlacklist': tk.StringVar(value=safe_join_list(self.config.get('titleBlacklist', []))),
            'posterBlacklist': tk.StringVar(value=safe_join_list(self.config.get('posterBlacklist', []))),
            'outputFileDirectory': tk.StringVar(value=self.config.get('outputFileDirectory', '~/Documents/EasyApplyBot/')),
            'universityGpa': tk.DoubleVar(value=self.config.get('universityGpa', 4.0)),
            'salaryMinimum': tk.IntVar(value=self.config.get('salaryMinimum', 65000)),
            'noticePeriod': tk.IntVar(value=self.config.get('noticePeriod', 2)),
            'evaluateJobFit': tk.BooleanVar(value=self.config.get('evaluateJobFit', False)),
            'debug': tk.BooleanVar(value=self.config.get('debug', False)),
            # Advanced - Dynamic/Complex (Managed by dedicated widgets/logic)
            'personalInfo': {}, 'eeo': {}, 'degreeCompleted': {}, 'checkboxes': {}
        }

        # --- Dynamic Variables Init --- (More robust against missing keys in loaded config)
        exp_levels_config = self.config.get('experienceLevel', {})
        for level, default in DEFAULT_CONFIG.get('experienceLevel', {}).items():
            self.vars['exp_level'][level] = tk.BooleanVar(value=exp_levels_config.get(level, default))

        job_types_config = self.config.get('jobTypes', {})
        for jtype, default in DEFAULT_CONFIG.get('jobTypes', {}).items():
             self.vars['job_type'][jtype] = tk.BooleanVar(value=job_types_config.get(jtype, default))

        checkboxes_config = self.config.get('checkboxes', {}) # Standard Y/N questions
        for chk_key, default in DEFAULT_CONFIG.get('checkboxes', {}).items():
            if isinstance(default, bool):
                self.vars['checkboxes'][chk_key] = tk.BooleanVar(value=checkboxes_config.get(chk_key, default))

        # Personal Info & EEO StringVars (Dynamically created ONLY for keys present in config)
        for key, value in self.config.get('personalInfo', {}).items():
            self.vars['personalInfo'][key] = tk.StringVar(value=value)
        for key, value in self.config.get('eeo', {}).items():
            self.vars['eeo'][key] = tk.StringVar(value=value)

        # Degree Completed BooleanVars (Based on STANDARD_DEGREES vs config list)
        degrees_in_config = self.config.get('checkboxes', {}).get('degreeCompleted', [])
        if not isinstance(degrees_in_config, list): degrees_in_config = [] # Ensure it's a list
        for degree in STANDARD_DEGREES:
            self.vars['degreeCompleted'][degree] = tk.BooleanVar(value=(degree in degrees_in_config))

        # --- GUI Structure --- (Setup remains similar)
        self.notebook = ttk.Notebook(self); self.basic_tab = ttk.Frame(self.notebook); self.job_tab = ttk.Frame(self.notebook)
        self.preferences_tab = ttk.Frame(self.notebook); self.advanced_tab = ttk.Frame(self.notebook); self.control_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.basic_tab, text='基本设置'); self.notebook.add(self.job_tab, text='职位和位置'); self.notebook.add(self.preferences_tab, text='偏好设置')
        self.notebook.add(self.advanced_tab, text='高级设置'); self.notebook.add(self.control_tab, text='操作与状态'); self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        self._create_basic_tab(); self._create_job_tab(); self._create_preferences_tab(); self._create_advanced_tab(); self._create_control_tab()
        self.status_label = tk.Label(self, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W); self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # --- Helper and Tab Creation Methods ---
    def _get_current_date_pref(self):
        date_prefs = self.config.get('date', {}); # Default to empty dict if missing
        if isinstance(date_prefs, dict):
            for key, value in date_prefs.items():
                if value: return key
        return 'all time' # Fallback

    def _create_basic_tab(self):
        # (No significant changes needed, uses _browse_file now)
        frame = ttk.LabelFrame(self.basic_tab, text="账户和简历", padding=(10, 5)); frame.pack(expand=True, fill="both", padx=10, pady=5); frame.columnconfigure(1, weight=1); current_row=0
        ttk.Label(frame, text="邮箱:").grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(frame, textvariable=self.vars['email'], width=60).grid(row=current_row, column=1, sticky=tk.EW, padx=5, pady=3); current_row+=1
        ttk.Label(frame, text="密码:").grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(frame, textvariable=self.vars['password'], width=60).grid(row=current_row, column=1, sticky=tk.EW, padx=5, pady=3); current_row+=1
        ttk.Label(frame, text="OpenAI API密钥:").grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(frame, textvariable=self.vars['openaiApiKey'], width=60).grid(row=current_row, column=1, sticky=tk.EW, padx=5, pady=3); current_row+=1
        ttk.Label(frame, text="PDF简历文件路径:").grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3); resume_frame = ttk.Frame(frame); ttk.Entry(resume_frame, textvariable=self.vars['resume_path'], width=52).pack(side=tk.LEFT, fill=tk.X, expand=True); ttk.Button(resume_frame, text="浏览", command=lambda: self._browse_file(self.vars['resume_path'], "PDF", "*.pdf")).pack(side=tk.LEFT, padx=(5,0)); resume_frame.grid(row=current_row, column=1, sticky=tk.EW, padx=5, pady=3); current_row+=1
        ttk.Label(frame, text="文本简历文件路径:").grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3); text_resume_frame = ttk.Frame(frame); ttk.Entry(text_resume_frame, textvariable=self.vars['textResume_path'], width=52).pack(side=tk.LEFT, fill=tk.X, expand=True); ttk.Button(text_resume_frame, text="浏览", command=lambda: self._browse_file(self.vars['textResume_path'], "Text", "*.txt")).pack(side=tk.LEFT, padx=(5,0)); text_resume_frame.grid(row=current_row, column=1, sticky=tk.EW, padx=5, pady=3); current_row+=1
        ttk.Checkbutton(frame, text="禁用系统防锁定/休眠", variable=self.vars['disableAntiLock']).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10); current_row+=1

    def _browse_file(self, path_var, file_desc, file_pattern):
        filepath = filedialog.askopenfilename(title=f"选择 {file_desc} 文件", filetypes=((f"{file_desc} Files", file_pattern), ("All Files", "*.*")))
        if filepath: path_var.set(filepath)

    def _create_job_tab(self):
        # (No significant changes needed)
        frame = ttk.LabelFrame(self.job_tab, text="工作搜索条件", padding=(10, 5)); frame.pack(expand=True, fill="both", padx=10, pady=5); frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="目标职位 (每行一个):").grid(row=0, column=0, sticky=tk.NW, padx=5, pady=3)
        self.positions_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=5, width=60); self.positions_widget.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=3); self.positions_widget.insert(tk.END, self.vars['positions'].get())
        ttk.Label(frame, text="目标地点 (每行一个):").grid(row=1, column=0, sticky=tk.NW, padx=5, pady=3)
        self.locations_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=5, width=60); self.locations_widget.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=3); self.locations_widget.insert(tk.END, self.vars['locations'].get())
        dist_frame = ttk.Frame(frame); ttk.Label(dist_frame, text="搜索半径 (公里):").pack(side=tk.LEFT, padx=(0, 5)); ttk.Combobox(dist_frame, textvariable=self.vars['distance'], values=[0, 5, 10, 25, 50, 100], state="readonly", width=5).pack(side=tk.LEFT); dist_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        chk_frame = ttk.Frame(frame); chk_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        ttk.Checkbutton(chk_frame, text="只搜索远程工作", variable=self.vars['search_remote']).pack(anchor=tk.W); ttk.Checkbutton(chk_frame, text="筛选\"少于10名申请者\"的职位", variable=self.vars['lessthanTenApplicants']).pack(anchor=tk.W)
        ttk.Checkbutton(chk_frame, text="按最新发布日期排序", variable=self.vars['newestPostingsFirst']).pack(anchor=tk.W); ttk.Checkbutton(chk_frame, text="居住在工作所在国家/地区", variable=self.vars['residentStatus']).pack(anchor=tk.W)

    def _create_preferences_tab(self):
        main_frame = ttk.Frame(self.preferences_tab, padding=(10, 5))
        main_frame.pack(expand=True, fill="both", padx=10, pady=5)
        # Configure columns to have equal weight
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # --- Experience Level Frame ---
        exp_frame = ttk.LabelFrame(main_frame, text="经验等级", padding=(10, 5))
        exp_frame.grid(row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)
        exp_levels_defaults = DEFAULT_CONFIG.get('experienceLevel', {})
        # Restore the original row/col logic
        row, col = 0, 0
        for i, level in enumerate(exp_levels_defaults.keys()):
             var = self.vars['exp_level'].get(level)
             if var: # Should always exist if initialized correctly
                 label = level.replace(' level', '').replace('-',' ').title()
                 ttk.Checkbutton(exp_frame, text=label, variable=var).grid(
                     row=row, column=col, sticky=tk.W, padx=5, pady=2
                 )
                 # Original logic for 2 columns
                 col += 1
                 if col >= 2:
                     col = 0
                     row += 1


        # --- Job Type Frame ---
        job_frame = ttk.LabelFrame(main_frame, text="工作类型", padding=(10, 5))
        job_frame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.NSEW)
        job_types_defaults = DEFAULT_CONFIG.get('jobTypes', {})
        # Restore the original row/col logic
        row, col = 0, 0
        for i, jtype in enumerate(job_types_defaults.keys()):
            var = self.vars['job_type'].get(jtype)
            if var: # Should always exist
                label = jtype.replace('-',' ').title()
                ttk.Checkbutton(job_frame, text=label, variable=var).grid(
                    row=row, column=col, sticky=tk.W, padx=5, pady=2
                )
                # Original logic for 2 columns
                col += 1
                if col >= 2:
                    col = 0
                    row += 1

        # --- Date Preference Frame --- (Remains the same)
        date_frame = ttk.LabelFrame(main_frame, text="发布日期", padding=(10, 5))
        date_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        date_prefs = {'all time': '任何时间', 'month': '过去一个月', 'week': '过去一周', '24 hours': '过去24小时'}
        for i, (key, text) in enumerate(date_prefs.items()):
            ttk.Radiobutton(date_frame, text=text, variable=self.vars['date_pref'], value=key).pack(
                anchor=tk.W, padx=5, pady=1
            )


    # --- Advanced Tab Creation ---
    def _create_advanced_tab(self):
        # --- Scrollable Frame Setup ---
        self.adv_canvas = tk.Canvas(self.advanced_tab) # Store canvas reference
        scrollbar = ttk.Scrollbar(self.advanced_tab, orient="vertical", command=self.adv_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.adv_canvas) # Store frame reference
        self.scrollable_frame.bind("<Configure>", lambda e: self.adv_canvas.configure(scrollregion=self.adv_canvas.bbox("all")))
        self.adv_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.adv_canvas.configure(yscrollcommand=scrollbar.set)

        # --- Mouse Wheel Binding ---
        def _on_mousewheel(event):
            # Platform-specific scroll delta calculation
            if sys.platform == "win32":
                delta = -int(event.delta / 120)
            elif sys.platform == "darwin": # macOS
                delta = -event.delta
            else: # Linux (Button-4 and Button-5)
                 if event.num == 4: delta = -1
                 elif event.num == 5: delta = 1
                 else: delta = 0 # Should not happen
            self.adv_canvas.yview_scroll(delta, "units")

        # Bind mouse wheel events to the canvas
        self.adv_canvas.bind_all("<MouseWheel>", _on_mousewheel) # Windows & macOS?
        self.adv_canvas.bind_all("<Button-4>", _on_mousewheel)   # Linux scroll up
        self.adv_canvas.bind_all("<Button-5>", _on_mousewheel)   # Linux scroll down
        # You might need to bind to self.scrollable_frame as well sometimes, depending on focus
        self.scrollable_frame.bind_all("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind_all("<Button-4>", _on_mousewheel)
        self.scrollable_frame.bind_all("<Button-5>", _on_mousewheel)


        self.adv_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        self.scrollable_frame.columnconfigure(1, weight=1) # Configure column weight

        # --- Content ---
        current_row = 0

        # Blacklists Frame
        blacklist_frame = ttk.LabelFrame(self.scrollable_frame, text="黑名单 (每行一个)", padding=(10, 5))
        blacklist_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.EW); blacklist_frame.columnconfigure(1, weight=1); current_row += 1
        ttk.Label(blacklist_frame, text="公司:").grid(row=0, column=0, sticky=tk.NW, padx=5, pady=3); self.company_bl_widget = scrolledtext.ScrolledText(blacklist_frame, wrap=tk.WORD, height=3, width=50); self.company_bl_widget.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=3); self.company_bl_widget.insert(tk.END, self.vars['companyBlacklist'].get())
        ttk.Label(blacklist_frame, text="职位:").grid(row=1, column=0, sticky=tk.NW, padx=5, pady=3); self.title_bl_widget = scrolledtext.ScrolledText(blacklist_frame, wrap=tk.WORD, height=3, width=50); self.title_bl_widget.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=3); self.title_bl_widget.insert(tk.END, self.vars['titleBlacklist'].get())
        ttk.Label(blacklist_frame, text="发布者:").grid(row=2, column=0, sticky=tk.NW, padx=5, pady=3); self.poster_bl_widget = scrolledtext.ScrolledText(blacklist_frame, wrap=tk.WORD, height=3, width=50); self.poster_bl_widget.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=3); self.poster_bl_widget.insert(tk.END, self.vars['posterBlacklist'].get())

        # --- Languages Frame (Listbox + Buttons) ---
        lang_frame = ttk.LabelFrame(self.scrollable_frame, text="语言能力", padding=(10, 5))
        lang_frame.grid(row=current_row, column=0, padx=10, pady=5, sticky=tk.NSEW); current_row += 1 # Takes one column now
        
        # 添加滚动条容器
        lang_list_frame = ttk.Frame(lang_frame)
        lang_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))
        
        # 修改Listbox以支持多选
        self.lang_listbox = tk.Listbox(lang_list_frame, height=4, width=40, selectmode=tk.EXTENDED)
        self.lang_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加语言列表滚动条
        lang_scrollbar = ttk.Scrollbar(lang_list_frame, orient="vertical", command=self.lang_listbox.yview)
        lang_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.lang_listbox.config(yscrollcommand=lang_scrollbar.set)
        
        self._update_language_listbox() # Initial population
        lang_button_frame = ttk.Frame(lang_frame); lang_button_frame.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Button(lang_button_frame, text="添加", command=self._add_language_dialog, width=8).pack(pady=2, fill=tk.X)
        ttk.Button(lang_button_frame, text="修改", command=self._modify_language_dialog, width=8).pack(pady=2, fill=tk.X)
        ttk.Button(lang_button_frame, text="移除", command=self._remove_language, width=8).pack(pady=2, fill=tk.X)
        ttk.Button(lang_button_frame, text="批量添加", command=self._batch_add_languages, width=8).pack(pady=2, fill=tk.X)
        ttk.Button(lang_button_frame, text="批量删除", command=self._batch_remove_languages, width=8).pack(pady=2, fill=tk.X)

        # --- Experience Frame (Listbox + Buttons) ---
        exp_frame = ttk.LabelFrame(self.scrollable_frame, text="经验 (技能: 年数)", padding=(10, 5))
        exp_frame.grid(row=current_row-1, column=1, padx=10, pady=5, sticky=tk.NSEW, rowspan=1) # Place next to languages
        exp_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.EW); current_row += 1

        # 添加滚动条容器
        exp_list_frame = ttk.Frame(exp_frame)
        exp_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))
        
        # 修改Listbox以支持多选
        self.exp_listbox = tk.Listbox(exp_list_frame, height=5, width=50, selectmode=tk.EXTENDED)
        self.exp_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加经验列表滚动条
        exp_scrollbar = ttk.Scrollbar(exp_list_frame, orient="vertical", command=self.exp_listbox.yview)
        exp_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.exp_listbox.config(yscrollcommand=exp_scrollbar.set)
        
        self._update_experience_listbox() # Initial population
        exp_button_frame = ttk.Frame(exp_frame); exp_button_frame.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Button(exp_button_frame, text="添加", command=self._add_experience_dialog, width=8).pack(pady=2, fill=tk.X)
        ttk.Button(exp_button_frame, text="修改", command=self._modify_experience_dialog, width=8).pack(pady=2, fill=tk.X)
        ttk.Button(exp_button_frame, text="移除", command=self._remove_experience, width=8).pack(pady=2, fill=tk.X)
        ttk.Button(exp_button_frame, text="批量添加", command=self._batch_add_experiences, width=8).pack(pady=2, fill=tk.X)
        ttk.Button(exp_button_frame, text="批量删除", command=self._batch_remove_experiences, width=8).pack(pady=2, fill=tk.X)

        # --- 自定义问答 Frame ---
        customq_frame = ttk.LabelFrame(self.scrollable_frame, text="自定义问答", padding=(10, 5))
        customq_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.EW); current_row += 1
        
        # 添加滚动条容器
        customq_list_frame = ttk.Frame(customq_frame)
        customq_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))
        
        # 创建Listbox以支持多选
        self.customq_listbox = tk.Listbox(customq_list_frame, height=6, width=50, selectmode=tk.EXTENDED)
        self.customq_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        customq_scrollbar = ttk.Scrollbar(customq_list_frame, orient="vertical", command=self.customq_listbox.yview)
        customq_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.customq_listbox.config(yscrollcommand=customq_scrollbar.set)
        
        self._update_customquestions_listbox()  # 更新列表显示
        
        # 按钮
        customq_button_frame = ttk.Frame(customq_frame)
        customq_button_frame.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Button(customq_button_frame, text="添加", command=self._add_customquestion_dialog, width=8).pack(pady=2, fill=tk.X)
        ttk.Button(customq_button_frame, text="修改", command=self._modify_customquestion_dialog, width=8).pack(pady=2, fill=tk.X)
        ttk.Button(customq_button_frame, text="移除", command=self._remove_customquestion, width=8).pack(pady=2, fill=tk.X)
        ttk.Button(customq_button_frame, text="批量添加", command=self._batch_add_customquestions, width=8).pack(pady=2, fill=tk.X)
        ttk.Button(customq_button_frame, text="批量删除", command=self._batch_remove_customquestions, width=8).pack(pady=2, fill=tk.X)

        # --- Personal Info & EEO Frame (Dynamic Entries) ---
        dynamic_frame = ttk.LabelFrame(self.scrollable_frame, text="个人资料 & EEO (基于 config.yaml)", padding=(10, 5))
        dynamic_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.EW); current_row += 1
        dynamic_frame.columnconfigure(1, weight=1); dynamic_frame.columnconfigure(3, weight=1)
        sub_row = 0
        # Personal Info Fields (Dynamically created based on loaded config keys)
        ttk.Label(dynamic_frame, text="个人资料:", font='-weight bold').grid(row=sub_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5); sub_row += 1
        personal_keys = list(self.config.get('personalInfo', {}).keys()) # Iterate over keys present in loaded config
        for i, key in enumerate(personal_keys):
            col = (i % 2) * 2; row_offset = i // 2
            ttk.Label(dynamic_frame, text=f"{key.replace('_',' ').title()}:").grid(row=sub_row + row_offset, column=col, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(dynamic_frame, textvariable=self.vars['personalInfo'][key], width=25) # Var should exist from __init__
            entry.grid(row=sub_row + row_offset, column=col + 1, sticky=tk.EW, padx=5, pady=2)
        sub_row += (len(personal_keys) + 1) // 2

        # EEO Fields (Dynamically created based on loaded config keys)
        ttk.Label(dynamic_frame, text="EEO信息:", font='-weight bold').grid(row=sub_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5); sub_row += 1
        eeo_keys = list(self.config.get('eeo', {}).keys()) # Iterate over keys present in loaded config
        for i, key in enumerate(eeo_keys):
            col = (i % 2) * 2; row_offset = i // 2
            ttk.Label(dynamic_frame, text=f"{key.replace('_',' ').title()}:").grid(row=sub_row + row_offset, column=col, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(dynamic_frame, textvariable=self.vars['eeo'][key], width=25) # Var should exist from __init__
            entry.grid(row=sub_row + row_offset, column=col + 1, sticky=tk.EW, padx=5, pady=2)
        sub_row += (len(eeo_keys) + 1) // 2


        # --- Degree Completed Frame (Checkboxes) ---
        degree_frame = ttk.LabelFrame(self.scrollable_frame, text="已完成学位", padding=(10, 5))
        degree_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.EW); current_row += 1
        row, col = 0, 0
        for degree in STANDARD_DEGREES:
            var = self.vars['degreeCompleted'][degree]
            ttk.Checkbutton(degree_frame, text=degree, variable=var).grid(row=row, column=col, sticky=tk.W, padx=5, pady=1)
            col += 1; # Adjust layout - maybe 2 columns?
            if col >= 2: col = 0; row += 1


        # --- Other Settings Frame (GPA, Salary, etc.) ---
        other_settings_frame = ttk.LabelFrame(self.scrollable_frame, text="其他高级设置", padding=(10, 5))
        other_settings_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.EW); other_settings_frame.columnconfigure(1, weight=1); current_row += 1
        sub_row=0
        ttk.Label(other_settings_frame, text="日志输出目录:").grid(row=sub_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(other_settings_frame, textvariable=self.vars['outputFileDirectory'], width=40).grid(row=sub_row, column=1, sticky=tk.EW, padx=5, pady=3); sub_row+=1
        ttk.Label(other_settings_frame, text="大学GPA:").grid(row=sub_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(other_settings_frame, textvariable=self.vars['universityGpa'], width=15).grid(row=sub_row, column=1, sticky=tk.W, padx=5, pady=3); sub_row+=1
        ttk.Label(other_settings_frame, text="最低期望薪资:").grid(row=sub_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(other_settings_frame, textvariable=self.vars['salaryMinimum'], width=15).grid(row=sub_row, column=1, sticky=tk.W, padx=5, pady=3); sub_row+=1
        ttk.Label(other_settings_frame, text="通知周期 (周):").grid(row=sub_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(other_settings_frame, textvariable=self.vars['noticePeriod'], width=15).grid(row=sub_row, column=1, sticky=tk.W, padx=5, pady=3); sub_row+=1
        bool_flag_frame = ttk.Frame(other_settings_frame); bool_flag_frame.grid(row=sub_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5); sub_row+=1
        ttk.Checkbutton(bool_flag_frame, text="评估工作匹配度", variable=self.vars['evaluateJobFit']).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(bool_flag_frame, text="调试模式", variable=self.vars['debug']).pack(side=tk.LEFT, padx=5)


        # Checkboxes Frame (Standard Y/N Questions)
        checkbox_frame = ttk.LabelFrame(self.scrollable_frame, text="申请问题默认回答 (是/否)", padding=(10, 5))
        checkbox_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.EW); current_row += 1; row, col = 0, 0
        checkbox_labels = {'driversLicence': '有驾照?', 'requireVisa': '需签证担保?', 'legallyAuthorized': '有合法工作权?', 'certifiedProfessional': '有专业认证?', 'urgentFill': '可立即开始?', 'commute': '接受通勤?', 'remote': '接受远程?', 'drugTest': '接受药物测试?', 'assessment': '愿意完成评估?', 'securityClearance': '有安全许可?', 'backgroundCheck': '接受背景调查?'}
        # Iterate based on DEFAULT_CONFIG to ensure all standard bool checkboxes are shown
        for key, default_value in DEFAULT_CONFIG.get('checkboxes', {}).items():
             if isinstance(default_value, bool): # Only handle boolean ones here
                 label = checkbox_labels.get(key, key); var = self.vars['checkboxes'].get(key) # Get var created in __init__
                 if var: # Check if var exists
                     ttk.Checkbutton(checkbox_frame, text=label, variable=var).grid(row=row, column=col, sticky=tk.W, padx=5, pady=1); col += 1
                     if col >= 3: col = 0; row += 1

        ttk.Label(self.scrollable_frame, text="提示: 更复杂的配置请编辑 YAML 文件。", justify=tk.LEFT, foreground="grey").grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.W)

        # 给各个列表框添加鼠标滚轮事件绑定
        def _configure_listbox_scrolling():
            def _on_listbox_mousewheel(event, listbox):
                # Platform-specific scroll delta calculation
                if sys.platform == "win32":
                    delta = -int(event.delta / 120)
                elif sys.platform == "darwin":  # macOS
                    delta = -event.delta
                else:  # Linux (Button-4 and Button-5)
                    if event.num == 4:
                        delta = -1
                    elif event.num == 5:
                        delta = 1
                    else:
                        delta = 0
                listbox.yview_scroll(delta, "units")
                return "break"  # 阻止事件继续传播
            
            # 为语言列表框添加滚轮事件
            self.lang_listbox.bind("<MouseWheel>", lambda e: _on_listbox_mousewheel(e, self.lang_listbox))
            self.lang_listbox.bind("<Button-4>", lambda e: _on_listbox_mousewheel(e, self.lang_listbox))
            self.lang_listbox.bind("<Button-5>", lambda e: _on_listbox_mousewheel(e, self.lang_listbox))
            
            # 为经验列表框添加滚轮事件
            self.exp_listbox.bind("<MouseWheel>", lambda e: _on_listbox_mousewheel(e, self.exp_listbox))
            self.exp_listbox.bind("<Button-4>", lambda e: _on_listbox_mousewheel(e, self.exp_listbox))
            self.exp_listbox.bind("<Button-5>", lambda e: _on_listbox_mousewheel(e, self.exp_listbox))
            
            # 为自定义问答列表框添加滚轮事件
            self.customq_listbox.bind("<MouseWheel>", lambda e: _on_listbox_mousewheel(e, self.customq_listbox))
            self.customq_listbox.bind("<Button-4>", lambda e: _on_listbox_mousewheel(e, self.customq_listbox))
            self.customq_listbox.bind("<Button-5>", lambda e: _on_listbox_mousewheel(e, self.customq_listbox))
        
        # 在所有列表框创建完后调用配置函数
        self.after(100, _configure_listbox_scrolling)

    # --- Language Dialogs and Listbox Management ---
    def _add_language_dialog(self):
        dialog = tk.Toplevel(self); dialog.title("添加语言")
        dialog.transient(self); dialog.grab_set()
        ttk.Label(dialog, text="语言名称:").pack(pady=(10, 2)); lang_entry = ttk.Entry(dialog, width=30); lang_entry.pack(pady=2, padx=20); lang_entry.focus_set()
        ttk.Label(dialog, text="熟练度:").pack(pady=(10, 2)); level_var = tk.StringVar(value=LANGUAGE_LEVELS[1]); level_combo = ttk.Combobox(dialog, textvariable=level_var, values=LANGUAGE_LEVELS, state="readonly", width=28); level_combo.pack(pady=2, padx=20)
        def on_ok():
            lang_name = lang_entry.get().strip(); level = level_var.get()
            if not lang_name: messagebox.showwarning("输入错误", "请输入语言名称。", parent=dialog); return
            if not level: messagebox.showwarning("输入错误", "请选择熟练度。", parent=dialog); return
            if 'languages' not in self.config: self.config['languages'] = {}
            if lang_name in self.config['languages']:
                 if not messagebox.askyesno("确认覆盖", f"语言 '{lang_name}' 已存在。要覆盖吗？", parent=dialog): return
            self.config['languages'][lang_name] = level
            self._update_language_listbox(); dialog.destroy()
        button_frame = ttk.Frame(dialog); button_frame.pack(pady=15)
        ttk.Button(button_frame, text="确定", command=on_ok, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _modify_language_dialog(self):
        selection = self.lang_listbox.curselection()
        if not selection: messagebox.showwarning("未选择", "请在列表中选择要修改的语言。"); return
        selected_item = self.lang_listbox.get(selection[0])
        try: old_lang_name, old_level = map(str.strip, selected_item.split(':', 1))
        except ValueError: messagebox.showerror("错误", "无法解析选中的语言项。"); return
        dialog = tk.Toplevel(self); dialog.title("修改语言")
        dialog.transient(self); dialog.grab_set()
        ttk.Label(dialog, text="语言名称:").pack(pady=(10, 2)); lang_entry = ttk.Entry(dialog, width=30); lang_entry.pack(pady=2, padx=20); lang_entry.insert(0, old_lang_name); lang_entry.focus_set()
        ttk.Label(dialog, text="熟练度:").pack(pady=(10, 2)); level_var = tk.StringVar(value=old_level); level_combo = ttk.Combobox(dialog, textvariable=level_var, values=LANGUAGE_LEVELS, state="readonly", width=28); level_combo.pack(pady=2, padx=20)
        def on_ok():
            new_lang_name = lang_entry.get().strip(); new_level = level_var.get()
            if not new_lang_name: messagebox.showwarning("输入错误", "请输入语言名称。", parent=dialog); return
            if not new_level: messagebox.showwarning("输入错误", "请选择熟练度。", parent=dialog); return
            if 'languages' in self.config:
                 if old_lang_name != new_lang_name and old_lang_name in self.config['languages']: del self.config['languages'][old_lang_name]
                 self.config['languages'][new_lang_name] = new_level
            self._update_language_listbox(); dialog.destroy()
        button_frame = ttk.Frame(dialog); button_frame.pack(pady=15)
        ttk.Button(button_frame, text="确定", command=on_ok, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _remove_language(self):
        selection = self.lang_listbox.curselection()
        if not selection: messagebox.showwarning("未选择", "请在列表中选择要移除的语言。"); return
        selected_item = self.lang_listbox.get(selection[0])
        try:
            lang_name = selected_item.split(':', 1)[0].strip()
            if 'languages' in self.config and lang_name in self.config['languages']:
                if messagebox.askyesno("确认移除", f"确定要移除语言 '{lang_name}' 吗？"):
                     del self.config['languages'][lang_name]
                     self._update_language_listbox()
            else: messagebox.showerror("错误", f"在配置中未找到语言 '{lang_name}'。")
        except Exception as e: messagebox.showerror("错误", f"移除语言时出错: {e}")
    def _update_language_listbox(self):
        self.lang_listbox.delete(0, tk.END)
        # Sort by language name for consistency? Optional.
        # sorted_langs = sorted(self.config.get('languages', {}).items())
        # for lang, level in sorted_langs:
        for lang, level in self.config.get('languages', {}).items():
            self.lang_listbox.insert(tk.END, f"{lang}: {level}")

    # --- Experience Dialogs and Listbox Management --- Added ---
    def _update_experience_listbox(self):
        self.exp_listbox.delete(0, tk.END)
        # Ensure 'default' is always first?
        if 'default' in self.config.get('experience', {}):
             self.exp_listbox.insert(tk.END, f"default: {self.config['experience']['default']}")
        # Add others, maybe sorted
        # sorted_exp = sorted([(k,v) for k,v in self.config.get('experience', {}).items() if k != 'default'])
        # for skill, years in sorted_exp:
        for skill, years in self.config.get('experience', {}).items():
             if skill != 'default':
                 self.exp_listbox.insert(tk.END, f"{skill}: {years}")

    def _add_experience_dialog(self):
        dialog = tk.Toplevel(self); dialog.title("添加经验")
        dialog.transient(self); dialog.grab_set()
        ttk.Label(dialog, text="技能/领域名称:").pack(pady=(10, 2)); skill_entry = ttk.Entry(dialog, width=30); skill_entry.pack(pady=2, padx=20); skill_entry.focus_set()
        ttk.Label(dialog, text="年数:").pack(pady=(10, 2)); years_entry = ttk.Entry(dialog, width=10); years_entry.pack(pady=2, padx=20)
        def on_ok():
            skill_name = skill_entry.get().strip(); years_str = years_entry.get().strip()
            if not skill_name: messagebox.showwarning("输入错误", "请输入技能名称。", parent=dialog); return
            if skill_name == 'default': messagebox.showwarning("输入错误", "不能添加 'default'。", parent=dialog); return
            try: years = int(years_str)
            except ValueError: messagebox.showwarning("输入错误", "年数必须是整数。", parent=dialog); return
            if 'experience' not in self.config: self.config['experience'] = {'default': 0}
            self.config['experience'][skill_name] = years; self._update_experience_listbox(); dialog.destroy()
        button_frame = ttk.Frame(dialog); button_frame.pack(pady=15)
        ttk.Button(button_frame, text="确定", command=on_ok, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _modify_experience_dialog(self):
        selection = self.exp_listbox.curselection()
        if not selection: messagebox.showwarning("未选择", "请在列表中选择要修改的经验项。"); return
        selected_item = self.exp_listbox.get(selection[0])
        try: old_skill_name, old_years_str = map(str.strip, selected_item.split(':', 1))
        except ValueError: messagebox.showerror("错误", "无法解析选中的经验项。"); return
        is_default = (old_skill_name == 'default')
        dialog = tk.Toplevel(self); dialog.title("修改经验")
        dialog.transient(self); dialog.grab_set()
        ttk.Label(dialog, text="技能/领域名称:").pack(pady=(10, 2)); skill_entry = ttk.Entry(dialog, width=30); skill_entry.pack(pady=2, padx=20); skill_entry.insert(0, old_skill_name)
        if is_default: skill_entry.config(state='disabled')
        ttk.Label(dialog, text="年数:").pack(pady=(10, 2)); years_entry = ttk.Entry(dialog, width=10); years_entry.pack(pady=2, padx=20); years_entry.insert(0, old_years_str)
        if not is_default: skill_entry.focus_set()
        else: years_entry.focus_set()
        def on_ok():
            new_skill_name = skill_entry.get().strip(); new_years_str = years_entry.get().strip()
            if not new_skill_name: messagebox.showwarning("输入错误", "请输入技能名称。", parent=dialog); return
            try: new_years = int(new_years_str)
            except ValueError: messagebox.showwarning("输入错误", "年数必须是整数。", parent=dialog); return
            if 'experience' in self.config:
                 if old_skill_name != new_skill_name and not is_default and old_skill_name in self.config['experience']:
                      if new_skill_name != 'default' and new_skill_name in self.config['experience']:
                          if not messagebox.askyesno("确认覆盖", f"技能 '{new_skill_name}' 已存在。要覆盖吗？", parent=dialog): return
                      del self.config['experience'][old_skill_name]
                 self.config['experience'][new_skill_name] = new_years
            self._update_experience_listbox(); dialog.destroy()
        button_frame = ttk.Frame(dialog); button_frame.pack(pady=15)
        ttk.Button(button_frame, text="确定", command=on_ok, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _remove_experience(self):
        selection = self.exp_listbox.curselection()
        if not selection: messagebox.showwarning("未选择", "请在列表中选择要移除的经验项。"); return
        selected_item = self.exp_listbox.get(selection[0])
        try: skill_name = selected_item.split(':', 1)[0].strip()
        except ValueError: messagebox.showerror("错误", "无法解析选中的经验项。"); return

        if skill_name == 'default': messagebox.showerror("无法移除", "不能移除 'default' 条目。"); return

        if 'experience' in self.config and skill_name in self.config['experience']:
             if messagebox.askyesno("确认移除", f"确定要移除经验项 '{skill_name}' 吗？"):
                 del self.config['experience'][skill_name]
                 self._update_experience_listbox()
        else: messagebox.showerror("错误", f"在配置中未找到经验项 '{skill_name}'。")


    # --- Control Tab Creation --- (No changes needed)
    def _create_control_tab(self):
        frame = ttk.Frame(self.control_tab, padding=(10, 5)); frame.pack(expand=True, fill="both", padx=10, pady=5)
        ttk.Label(frame, text="运行日志:").pack(anchor=tk.W, padx=5); self.output_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=15, state='disabled'); self.output_area.pack(expand=True, fill='both', padx=5, pady=5)
        button_frame = ttk.Frame(frame); button_frame.pack(fill=tk.X, pady=5)
        self.save_button = ttk.Button(button_frame, text="保存配置", command=self._save_gui_config); self.save_button.pack(side=tk.LEFT, padx=5)
        self.start_button = ttk.Button(button_frame, text="启动机器人", command=self._start_bot); self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(button_frame, text="停止", command=self._stop_bot, state='disabled'); self.stop_button.pack(side=tk.LEFT, padx=5)
        edit_config_button = ttk.Button(button_frame, text="编辑YAML", command=self._open_config_file); edit_config_button.pack(side=tk.LEFT, padx=5)
        github_label = tk.Label(button_frame, text="GitHub项目", fg="blue", cursor="hand2"); github_label.pack(side=tk.RIGHT, padx=10); github_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/yiqun234/EasyApplyBot"))

    # --- Action Methods ---

    def _open_config_file(self):
        # (No changes needed)
        try:
            if os.path.exists(CONFIG_FILE):
                if sys.platform.startswith('win'): os.startfile(CONFIG_FILE)
                elif sys.platform.startswith('darwin'): subprocess.call(['open', CONFIG_FILE])
                else:
                    editors = ['xdg-open', 'gedit', 'kate', 'mousepad', 'nano', 'vim', 'vi']
                    opened = False
                    for editor in editors:
                        try:
                            if subprocess.call(['which', editor], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0: subprocess.Popen([editor, CONFIG_FILE]); opened = True; break
                        except FileNotFoundError: continue
                    if not opened: messagebox.showwarning("无法打开编辑器", f"未能自动打开 {CONFIG_FILE}。请手动打开。")
            else: messagebox.showinfo("文件未找到", f"{CONFIG_FILE} 不存在。")
        except Exception as e: messagebox.showerror("打开文件错误", f"无法打开配置文件: {e}")


    def _update_config_from_gui(self):
        """Updates the self.config dictionary based on GUI values. Now reads interactive elements."""
        try:
            # Basic Tab
            self.config['email'] = self.vars['email'].get(); self.config['password'] = self.vars['password'].get(); self.config['openaiApiKey'] = self.vars['openaiApiKey'].get()
            self.config['disableAntiLock'] = self.vars['disableAntiLock'].get(); self.config['uploads']['resume'] = self.vars['resume_path'].get(); self.config['textResume'] = self.vars['textResume_path'].get()
            # Job Tab
            self.config['positions'] = parse_list_from_textarea(self.positions_widget.get("1.0", tk.END)); self.config['locations'] = parse_list_from_textarea(self.locations_widget.get("1.0", tk.END))
            self.config['distance'] = self.vars['distance'].get(); self.config['remote'] = self.vars['search_remote'].get(); self.config['lessthanTenApplicants'] = self.vars['lessthanTenApplicants'].get()
            self.config['newestPostingsFirst'] = self.vars['newestPostingsFirst'].get(); self.config['residentStatus'] = self.vars['residentStatus'].get()
            # Preferences Tab
            for level, var in self.vars['exp_level'].items(): self.config['experienceLevel'][level] = var.get()
            for jtype, var in self.vars['job_type'].items(): self.config['jobTypes'][jtype] = var.get()
            selected_date = self.vars['date_pref'].get(); self.config['date'] = {key: (key == selected_date) for key in DEFAULT_CONFIG['date']}
            # --- Advanced Tab ---
            # Blacklists
            self.config['companyBlacklist'] = parse_list_from_textarea(self.company_bl_widget.get("1.0", tk.END))
            self.config['titleBlacklist'] = parse_list_from_textarea(self.title_bl_widget.get("1.0", tk.END))
            self.config['posterBlacklist'] = parse_list_from_textarea(self.poster_bl_widget.get("1.0", tk.END))
            # Other settings
            self.config['outputFileDirectory'] = self.vars['outputFileDirectory'].get()
            try: self.config['universityGpa'] = self.vars['universityGpa'].get()
            except tk.TclError: messagebox.showerror("输入错误", "大学GPA必须是数字。"); return False
            try: self.config['salaryMinimum'] = self.vars['salaryMinimum'].get()
            except tk.TclError: messagebox.showerror("输入错误", "最低期望薪资必须是整数。"); return False
            try: self.config['noticePeriod'] = self.vars['noticePeriod'].get()
            except tk.TclError: messagebox.showerror("输入错误", "通知周期必须是整数。"); return False
            # Boolean flags
            self.config['evaluateJobFit'] = self.vars['evaluateJobFit'].get(); self.config['debug'] = self.vars['debug'].get()
            # Personal Info & EEO (Read from dynamic StringVars)
            for key, var in self.vars['personalInfo'].items(): self.config['personalInfo'][key] = var.get()
            for key, var in self.vars['eeo'].items(): self.config['eeo'][key] = var.get()
            # Experience & Languages are updated directly via dialogs, no need to read here
            # --- Checkboxes (Standard Y/N & Degrees) ---
            if 'checkboxes' not in self.config: self.config['checkboxes'] = {}
            for key, var in self.vars['checkboxes'].items(): # Standard Y/N
                if isinstance(var, tk.BooleanVar): self.config['checkboxes'][key] = var.get()
            self.config['checkboxes']['degreeCompleted'] = [ # Degrees
                degree for degree, var in self.vars['degreeCompleted'].items() if var.get() ]
            
            # CustomQuestions is handled by the dialog methods, no need to read here

            return True
        except tk.TclError as e: messagebox.showerror("获取值错误", f"无法从界面获取配置值: {e}"); return False
        except Exception as e: messagebox.showerror("更新错误", f"从界面更新配置时出错: {e}"); return False


    # --- Other Methods (_save_gui_config, etc.) --- (No changes needed in these core logic methods)
    def _save_gui_config(self):
        if self._update_config_from_gui():
            if save_config(self.config): self.status_label.config(text="配置已保存！")
            else: self.status_label.config(text="保存配置时出错！")
        else: self.status_label.config(text="更新配置值时出错，未保存。")
    def _log_message(self, message):
        def append_text(): self.output_area.config(state='normal'); self.output_area.insert(tk.END, message); self.output_area.see(tk.END); self.output_area.config(state='disabled')
        if threading.current_thread() is threading.main_thread(): append_text()
        else: self.after(0, append_text)
    def _start_bot(self):
        """启动main.py并在GUI中显示输出"""
        self._save_gui_config()
        if not self.config.get('email') or not self.config.get('password'):
            messagebox.showwarning("缺少信息", "请输入LinkedIn邮箱和密码。")
            return
        pdf_resume = self.config.get('uploads', {}).get('resume', '')
        text_resume = self.config.get('textResume', '')
        if not pdf_resume and not text_resume:
            messagebox.showwarning("缺少信息", "请至少指定 PDF简历 或 文本简历 文件路径。")
            return

        self.status_label.config(text="正在启动机器人...")
        self._log_message("--- 启动 LinkedIn Easy Apply Bot ---\n")
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.save_button.config(state='disabled')

        # 确保使用正确的Python解释器
        python_executable = sys.executable
        
        try:
            # 使用更简单的方式启动，不捕获输出，不使用CREATE_NO_WINDOW标志
            if sys.platform.startswith('win'):
                # Windows: 直接启动，不使用CREATE_NO_WINDOW标志
                self.bot_process = subprocess.Popen(
                    [python_executable, "-u", "main.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    universal_newlines=True
                    # 移除 creationflags 参数
                )
            else:
                # 非Windows平台
                self.bot_process = subprocess.Popen(
                    [python_executable, "-u", "main.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    universal_newlines=True
                )
            
            self._log_message("机器人已启动，请等待...\n")
            
            # 使用线程读取输出
            self.output_thread = threading.Thread(
                target=self._read_bot_output,
                daemon=True
            )
            self.output_thread.start()
            
        except FileNotFoundError:
            self._log_message("错误: 未找到'main.py'。请确保脚本在同一目录下。\n")
            self._on_bot_finish(error=True)
        except Exception as e:
            self._log_message(f"启动机器人时出错: {e}\n")
            print(f"启动错误: {e}")  # 调试输出
            self._on_bot_finish(error=True)

    def _read_bot_output(self):
        """读取机器人输出并更新GUI（不使用select，避免WinError 10038）"""
        try:
            # 确保Bot进程和stdout存在
            if self.bot_process and self.bot_process.stdout:
                # 使用 iter 和 readline 来迭代读取行，直到遇到EOF (空字符串)
                # 这是读取管道输出的标准、非阻塞（对于行缓冲）方式
                for line in iter(self.bot_process.stdout.readline, ''):
                    if line:  # 确保行不为空
                        # 使用after在主线程中安排日志更新
                        self.after(0, self._log_message, line)
                    # (可选) 如果担心进程卡住而不是正常退出，可以加一个poll检查，
                    # 但通常 _check_bot_process 会处理进程结束
                    if self.bot_process.poll() is not None:
                        break

                # 进程正常结束 (readline返回空字符串) 或被终止后，
                # 确保最终状态检查被调度
            self.after(100, self._check_bot_process)

        except ValueError:
            # 当管道在读取操作中途被强制关闭时 (例如 terminate/kill),
            # readline 可能会抛出 ValueError: I/O operation on closed file.
            print("读取输出时检测到管道关闭 (ValueError)")
            self.after(0, self._log_message, "\n机器人进程输出管道已关闭。\n")
            self.after(100, self._check_bot_process)  # 仍然检查最终状态

        except Exception as e:
            # 捕获其他可能的读取错误
            print(f"读取输出错误: {e}")  # 调试输出
            self.after(0, self._log_message, f"\n读取机器人输出时发生未知错误: {e}\n")
            self.after(100, self._check_bot_process)  # 仍然检查最终状态
    
    def _check_bot_process(self):
        """检查机器人进程是否已结束并更新UI"""
        if hasattr(self, 'bot_process') and self.bot_process and self.bot_process.poll() is not None:
            returncode = self.bot_process.returncode
            self._on_bot_finish(returncode != 0)
    
    def _on_bot_finish(self, error=False):
        """处理机器人进程结束的情况"""
        if error:
            self.status_label.config(text="机器人运行出错或被停止。")
            self._log_message("\n--- 机器人运行出错或被停止 ---\n")
        else:
            self.status_label.config(text="机器人运行完成。")
            self._log_message("\n--- 机器人运行完成 ---\n")
            
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.save_button.config(state='normal')
        if hasattr(self, 'bot_process'):
            self.bot_process = None
    
    def _stop_bot(self):
        """停止运行中的机器人进程"""
        if hasattr(self, 'bot_process') and self.bot_process and self.bot_process.poll() is None:
            self.status_label.config(text="正在停止机器人...")
            try:
                self.bot_process.terminate()  # 尝试正常终止
                try:
                    self.bot_process.wait(timeout=2)  # 等待最多2秒
                except subprocess.TimeoutExpired:
                    self.bot_process.kill()  # 如果正常终止失败，强制关闭
                self._log_message("\n--- 用户请求停止机器人 ---\n")
            except Exception as e:
                self._log_message(f"\n停止机器人时出错: {e}\n")
            finally:
                self._on_bot_finish(error=True)
    
    def _on_closing(self):
        """直接关闭GUI，不再需要检查进程状态"""
        self.destroy()

    # 添加批量操作相关的方法
    def _batch_add_languages(self):
        """批量添加语言能力"""
        dialog = tk.Toplevel(self)
        dialog.title("批量添加语言")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="输入格式：每行一个语言，格式为 '语言名称: 熟练度'").pack(pady=(10, 5), padx=10)
        ttk.Label(dialog, text="例如：'英语: Native or bilingual'").pack(pady=(0, 10), padx=10)
        
        # 文本区域用于输入多个语言
        text_area = scrolledtext.ScrolledText(dialog, width=40, height=10)
        text_area.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        # 添加一个下拉框，显示可用的熟练度级别
        level_frame = ttk.Frame(dialog)
        level_frame.pack(pady=5, padx=10, fill=tk.X)
        ttk.Label(level_frame, text="可用熟练度:").pack(side=tk.LEFT)
        level_var = tk.StringVar()
        level_combo = ttk.Combobox(level_frame, textvariable=level_var, values=LANGUAGE_LEVELS, state="readonly", width=20)
        level_combo.pack(side=tk.LEFT, padx=(5, 0))
        level_combo.current(1)  # 默认选择第二个选项
        
        def insert_level():
            """将选中的熟练度插入到当前光标位置"""
            selected_level = level_var.get()
            if selected_level:
                text_area.insert(tk.INSERT, f": {selected_level}")
        
        ttk.Button(level_frame, text="插入熟练度", command=insert_level).pack(side=tk.LEFT, padx=(5, 0))
        
        def on_ok():
            lines = text_area.get("1.0", tk.END).strip().split('\n')
            added_count = 0
            
            for line in lines:
                if not line.strip():
                    continue
                
                try:
                    if ':' in line:
                        lang_name, level = map(str.strip, line.split(':', 1))
                    else:
                        # 如果没有指定熟练度，使用默认值
                        lang_name = line.strip()
                        level = LANGUAGE_LEVELS[1]  # 使用第二个级别作为默认值
                    
                    if not lang_name:
                        continue
                    
                    # 验证熟练度是否有效
                    if level not in LANGUAGE_LEVELS:
                        if not messagebox.askyesno("无效熟练度", 
                                                 f"语言 '{lang_name}' 的熟练度 '{level}' 不在预设列表中。是否继续并将其设为 '{LANGUAGE_LEVELS[1]}'?",
                                                 parent=dialog):
                            continue
                        level = LANGUAGE_LEVELS[1]
                    
                    if 'languages' not in self.config:
                        self.config['languages'] = {}
                    
                    # 检查是否已存在该语言
                    if lang_name in self.config['languages'] and not messagebox.askyesno("确认覆盖", 
                                                                                      f"语言 '{lang_name}' 已存在。要覆盖吗？", 
                                                                                      parent=dialog):
                        continue
                    
                    self.config['languages'][lang_name] = level
                    added_count += 1
                except Exception as e:
                    messagebox.showerror("添加错误", f"添加语言 '{line}' 时出错: {e}", parent=dialog)
            
            if added_count > 0:
                self._update_language_listbox()
                messagebox.showinfo("批量添加完成", f"成功添加了 {added_count} 个语言。", parent=dialog)
                dialog.destroy()
            else:
                messagebox.showwarning("未添加", "没有添加任何语言。请检查输入格式。", parent=dialog)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=15)
        ttk.Button(button_frame, text="确定", command=on_ok, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        
        # 居中显示对话框
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def _batch_remove_languages(self):
        """批量删除选中的语言"""
        selection = self.lang_listbox.curselection()
        if not selection:
            messagebox.showwarning("未选择", "请在列表中选择要删除的语言。")
            return
        
        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {len(selection)} 个语言吗？"):
            return
        
        # 因为每次删除一项后索引会变化，所以从后往前删除
        selected_items = [self.lang_listbox.get(i) for i in selection]
        removed_count = 0
        
        for item in selected_items:
            try:
                lang_name = item.split(':', 1)[0].strip()
                if 'languages' in self.config and lang_name in self.config['languages']:
                    del self.config['languages'][lang_name]
                    removed_count += 1
            except Exception as e:
                messagebox.showerror("删除错误", f"删除语言 '{item}' 时出错: {e}")
        
        if removed_count > 0:
            self._update_language_listbox()
            messagebox.showinfo("批量删除完成", f"成功删除了 {removed_count} 个语言。")
    
    def _batch_add_experiences(self):
        """批量添加经验"""
        dialog = tk.Toplevel(self)
        dialog.title("批量添加经验")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="输入格式：每行一个经验，格式为 '技能/领域名称: 年数'").pack(pady=(10, 5), padx=10)
        ttk.Label(dialog, text="例如：'Python: 3'").pack(pady=(0, 10), padx=10)
        
        # 文本区域用于输入多个经验
        text_area = scrolledtext.ScrolledText(dialog, width=40, height=10)
        text_area.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        def on_ok():
            lines = text_area.get("1.0", tk.END).strip().split('\n')
            added_count = 0
            
            for line in lines:
                if not line.strip():
                    continue
                
                try:
                    if ':' in line:
                        skill_name, years_str = map(str.strip, line.split(':', 1))
                    else:
                        # 如果没有指定年数，跳过
                        messagebox.showwarning("格式错误", 
                                            f"行 '{line}' 缺少年数。请使用 '技能: 年数' 格式。", 
                                            parent=dialog)
                        continue
                    
                    if not skill_name:
                        continue
                    
                    # 验证年数
                    try:
                        years = int(years_str)
                    except ValueError:
                        if not messagebox.askyesno("无效年数", 
                                                f"经验 '{skill_name}' 的年数 '{years_str}' 不是整数。是否将其设为 0?",
                                                parent=dialog):
                            continue
                        years = 0
                    
                    if skill_name == 'default':
                        if not messagebox.askyesno("默认经验", 
                                                "您正在修改默认经验年数。确定要继续吗？", 
                                                parent=dialog):
                            continue
                    
                    if 'experience' not in self.config:
                        self.config['experience'] = {'default': 0}
                    
                    # 检查是否已存在该技能
                    if skill_name in self.config['experience'] and not messagebox.askyesno("确认覆盖", 
                                                                                       f"技能 '{skill_name}' 已存在。要覆盖吗？", 
                                                                                       parent=dialog):
                        continue
                    
                    self.config['experience'][skill_name] = years
                    added_count += 1
                except Exception as e:
                    messagebox.showerror("添加错误", f"添加经验 '{line}' 时出错: {e}", parent=dialog)
            
            if added_count > 0:
                self._update_experience_listbox()
                messagebox.showinfo("批量添加完成", f"成功添加了 {added_count} 个经验。", parent=dialog)
                dialog.destroy()
            else:
                messagebox.showwarning("未添加", "没有添加任何经验。请检查输入格式。", parent=dialog)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=15)
        ttk.Button(button_frame, text="确定", command=on_ok, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        
        # 居中显示对话框
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def _batch_remove_experiences(self):
        """批量删除选中的经验"""
        selection = self.exp_listbox.curselection()
        if not selection:
            messagebox.showwarning("未选择", "请在列表中选择要删除的经验。")
            return
        
        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {len(selection)} 个经验吗？"):
            return
        
        # 因为每次删除一项后索引会变化，所以先获取所有选中项
        selected_items = [self.exp_listbox.get(i) for i in selection]
        removed_count = 0
        
        for item in selected_items:
            try:
                skill_name = item.split(':', 1)[0].strip()
                
                # 不允许删除 default
                if skill_name == 'default':
                    messagebox.showwarning("不能删除", "不能删除默认经验项。")
                    continue
                
                if 'experience' in self.config and skill_name in self.config['experience']:
                    del self.config['experience'][skill_name]
                    removed_count += 1
            except Exception as e:
                messagebox.showerror("删除错误", f"删除经验 '{item}' 时出错: {e}")
        
        if removed_count > 0:
            self._update_experience_listbox()
            messagebox.showinfo("批量删除完成", f"成功删除了 {removed_count} 个经验。")

    def _update_customquestions_listbox(self):
        """更新自定义问答列表显示"""
        self.customq_listbox.delete(0, tk.END)
        questions = self.config.get('customQuestions', {})
        for question, answer in questions.items():
            # 使用 " => " 作为问答分隔符，避免与问题中的冒号混淆
            self.customq_listbox.insert(tk.END, f"{question} => {answer}")

    def _add_customquestion_dialog(self):
        """打开添加自定义问答对话框"""
        dialog = tk.Toplevel(self)
        dialog.title("添加自定义问答")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="问题:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        question_entry = ttk.Entry(dialog, width=40)
        question_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(dialog, text="答案:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.NW)
        answer_text = scrolledtext.ScrolledText(dialog, width=40, height=5)
        answer_text.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        
        def save_question():
            question = question_entry.get().strip()
            answer = answer_text.get("1.0", tk.END).strip()
            
            if question and answer:
                if 'customQuestions' not in self.config:
                    self.config['customQuestions'] = {}
                
                # 确保问题和答案中的特殊字符被正确处理
                self.config['customQuestions'][question] = answer
                self._update_customquestions_listbox()
                # 每次添加后都保存一次配置，确保不会丢失
                self._save_gui_config()
                dialog.destroy()
            else:
                messagebox.showwarning("输入错误", "问题和答案都不能为空。", parent=dialog)
        
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="保存", command=save_question, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        
        dialog.columnconfigure(1, weight=1)
        dialog.rowconfigure(1, weight=1)
        
        # 居中显示对话框
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"+{x}+{y}")
        
        question_entry.focus_set()

    def _modify_customquestion_dialog(self):
        """打开修改自定义问答对话框"""
        selected = self.customq_listbox.curselection()
        if not selected:
            messagebox.showinfo("选择错误", "请先选择一个问题答案对。")
            return
        
        selected_item = self.customq_listbox.get(selected[0])
        try:
            # 使用 " => " 作为分隔符拆分问题和答案
            if " => " in selected_item:
                question, answer = selected_item.split(" => ", 1)
            else:
                # 兼容旧格式
                question, answer = selected_item.split(": ", 1)
        except ValueError:
            messagebox.showerror("格式错误", "所选项目格式不正确，无法修改。")
            return
        
        dialog = tk.Toplevel(self)
        dialog.title("修改自定义问答")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="问题:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        question_entry = ttk.Entry(dialog, width=40)
        question_entry.insert(0, question)
        question_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(dialog, text="答案:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.NW)
        answer_text = scrolledtext.ScrolledText(dialog, width=40, height=5)
        answer_text.insert("1.0", answer)
        answer_text.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        
        def save_modification():
            new_question = question_entry.get().strip()
            new_answer = answer_text.get("1.0", tk.END).strip()
            
            if new_question and new_answer:
                # 删除旧问答
                if question in self.config.get('customQuestions', {}):
                    del self.config['customQuestions'][question]
                
                # 添加新问答
                if 'customQuestions' not in self.config:
                    self.config['customQuestions'] = {}
                
                # 确保问题和答案中的特殊字符被正确处理
                self.config['customQuestions'][new_question] = new_answer
                self._update_customquestions_listbox()
                # 每次修改后都保存一次配置，确保不会丢失
                self._save_gui_config()
                dialog.destroy()
            else:
                messagebox.showwarning("输入错误", "问题和答案都不能为空。", parent=dialog)

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="保存", command=save_modification, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        
        dialog.columnconfigure(1, weight=1)
        dialog.rowconfigure(1, weight=1)
        
        # 居中显示对话框
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"+{x}+{y}")
        
        question_entry.focus_set()

    def _remove_customquestion(self):
        """删除选中的自定义问答"""
        selected = self.customq_listbox.curselection()
        if not selected:
            messagebox.showinfo("选择错误", "请先选择一个问题答案对。")
            return
        
        selected_items = [self.customq_listbox.get(idx) for idx in selected]
        
        if messagebox.askyesno("确认删除", f"确定要删除选中的 {len(selected_items)} 个问题答案对吗？"):
            for item in selected_items:
                try:
                    # 使用 " => " 作为分隔符拆分问题和答案
                    if " => " in item:
                        question = item.split(" => ", 1)[0]
                    else:
                        # 兼容旧格式
                        question = item.split(": ", 1)[0]
                        
                    if question in self.config.get('customQuestions', {}):
                        del self.config['customQuestions'][question]
                except ValueError:
                    continue
            
            self._update_customquestions_listbox()
            # 删除后保存配置
            self._save_gui_config()

    def _batch_add_customquestions(self):
        """批量添加自定义问答"""
        dialog = tk.Toplevel(self)
        dialog.title("批量添加自定义问答")
        dialog.geometry("500x400")  # 增加高度
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="每行一个问题答案对，格式为 '问题: 答案'").pack(pady=5)
        
        text_area = scrolledtext.ScrolledText(dialog, width=60, height=15)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        def save_batch():
            content = text_area.get("1.0", tk.END).strip()
            if not content:
                dialog.destroy()
                return
            
            lines = content.split("\n")
            added_count = 0
            
            if 'customQuestions' not in self.config:
                self.config['customQuestions'] = {}
            
            for line in lines:
                if ": " in line:
                    question, answer = line.split(": ", 1)
                    question = question.strip()
                    answer = answer.strip()
                    
                    if question and answer:
                        # 确保问题和答案中的特殊字符被正确处理
                        self.config['customQuestions'][question] = answer
                        added_count += 1
            
            if added_count > 0:
                messagebox.showinfo("批量添加完成", f"成功添加了 {added_count} 个问题答案对。", parent=dialog)
                self._update_customquestions_listbox()
                # 批量添加后保存配置
                self._save_gui_config()
                dialog.destroy()
            else:
                messagebox.showwarning("添加失败", "没有找到有效的问题答案对，请确保格式正确。", parent=dialog)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="保存", command=save_batch, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="从文件导入", command=lambda: self._import_qa_from_file(text_area), width=15).pack(side=tk.LEFT, padx=5)
        
        # 居中显示对话框
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"+{x}+{y}")
        
        text_area.focus_set()

    def _import_qa_from_file(self, text_area):
        """从文件导入问题和答案"""
        filepath = filedialog.askopenfilename(
            title="选择数据文件",
            filetypes=(
                ("文本文件", "*.txt"),
                ("CSV文件", "*.csv"),
                ("所有文件", "*.*")
            )
        )
        
        if not filepath:
            return
            
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                text_area.delete("1.0", tk.END)
                text_area.insert("1.0", content)
                messagebox.showinfo("导入成功", "文件内容已导入，请检查格式并保存。")
        except Exception as e:
            messagebox.showerror("导入错误", f"导入文件时出错：{e}")

    def _batch_remove_customquestions(self):
        """批量删除自定义问答"""
        selected = self.customq_listbox.curselection()
        if not selected:
            messagebox.showinfo("选择错误", "请先选择至少一个问题答案对。")
            return
        
        selected_items = [self.customq_listbox.get(idx) for idx in selected]
        
        if messagebox.askyesno("确认删除", f"确定要删除选中的 {len(selected_items)} 个问题答案对吗？"):
            removed_count = 0
            for item in selected_items:
                try:
                    # 使用 " => " 作为分隔符拆分问题和答案
                    if " => " in item:
                        question = item.split(" => ", 1)[0]
                    else:
                        # 兼容旧格式
                        question = item.split(": ", 1)[0]
                        
                    if question in self.config.get('customQuestions', {}):
                        del self.config['customQuestions'][question]
                        removed_count += 1
                except ValueError:
                    continue
            
            self._update_customquestions_listbox()
            # 批量删除后保存配置
            self._save_gui_config()
            messagebox.showinfo("批量删除完成", f"成功删除了 {removed_count} 个问题答案对。")

    def _save_config(self, config_to_save):
        # 确保customQuestions中的特殊字符被正确处理
        if 'customQuestions' in config_to_save and config_to_save['customQuestions']:
            processed_questions = {}
            for question, answer in config_to_save['customQuestions'].items():
                # 对问题和答案进行处理，确保特殊字符被正确处理
                # 在YAML中，冒号、引号等需要特别注意
                if isinstance(question, str) and isinstance(answer, str):
                    # 对于含有冒号的问题，确保它们被正确引用
                    question_key = question
                    if ':' in question or '\n' in question or '"' in question or "'" in question:
                        # 使用YAML风格的双引号字符串，它会正确处理所有特殊字符
                        question_key = json.dumps(question, ensure_ascii=False)
                    
                    # 同样处理答案
                    answer_value = answer
                    if ':' in answer or '\n' in answer or '"' in answer or "'" in answer:
                        answer_value = json.dumps(answer, ensure_ascii=False)
                        
                    processed_questions[question_key] = answer_value
                else:
                    processed_questions[question] = answer
                    
            config_to_save['customQuestions'] = processed_questions

        with open('config.yaml', 'w', encoding='utf-8') as stream:
            yaml.dump(config_to_save, stream, default_flow_style=False, allow_unicode=True, sort_keys=False)

if __name__ == '__main__':
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if not in_venv and not os.environ.get("SKIP_VENV_CHECK"): print("警告：建议在Python虚拟环境中运行此应用...");
    app = EasyApplyApp(); app.mainloop()