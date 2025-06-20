import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import yaml
import subprocess
import sys
import os
import threading
import collections.abc # Used for deep update
import traceback
import json
import datetime  # 导入datetime模块用于获取当前年份
import requests

from lang import load_language, AVAILABLE_LANGUAGES, DEFAULT_LANGUAGE  # 添加语言包支持
import auth_server  # 导入认证服务模块
import firebase_manager  # 导入 Firebase 管理模块

OCR_API = "https://ocr.nuomi.ai/api/ocr"

# 定义国家代码列表
COUNTRY_CODES = [
    "Select an option", "Canada (+1)", "United States (+1)", "Afghanistan (+93)", 
    "Aland Islands (+358)", "Albania (+355)", "Algeria (+213)", "American Samoa (+1)", 
    "Andorra (+376)", "Angola (+244)", "Anguilla (+1)", "Antarctica (+0)", 
    "Antigua and Barbuda (+1)", "Argentina (+54)", "Armenia (+374)", "Aruba (+297)", 
    "Australia (+61)", "Austria (+43)", "Azerbaijan (+994)", "Bahamas (+1)", 
    "Bahrain (+973)", "Bangladesh (+880)", "Barbados (+1)", "Belarus (+375)", 
    "Belgium (+32)", "Belize (+501)", "Benin (+229)", "Bermuda (+1)", 
    "Bhutan (+975)", "Bolivia (+591)", "Bosnia and Herzegovina (+387)", 
    "Botswana (+267)", "Bouvet Island (+0)", "Brazil (+55)", 
    "British Indian Ocean Territory (+246)", "Brunei Darussalam (+673)", 
    "Bulgaria (+359)", "Burkina Faso (+226)", "Burundi (+257)", "Cambodia (+855)", 
    "Cameroon (+237)", "Cape Verde (+238)", "Caribbean Nations (+0)", 
    "Cayman Islands (+1)", "Central African Republic (+236)", "Chad (+235)", 
    "Chile (+56)", "China (+86)", "Christmas Island (+61)", 
    "Cocos (Keeling) Islands (+61)", "Colombia (+57)", "Comoros (+269)", 
    "Congo (+242)", "Cook Islands (+682)", "Costa Rica (+506)", 
    "Cote D'Ivoire (Ivory Coast) (+225)", "Croatia (+385)", "Cuba (+53)", 
    "Cyprus (+357)", "Czech Republic (+420)", "Democratic Republic of the Congo (+243)", 
    "Denmark (+45)", "Djibouti (+253)", "Dominica (+1)", "Dominican Republic (+1)", 
    "Ecuador (+593)", "Egypt (+20)", "El Salvador (+503)", "Equatorial Guinea (+240)", 
    "Eritrea (+291)", "Estonia (+372)", "Ethiopia (+251)", 
    "Falkland Islands (Malvinas) (+500)", "Faroe Islands (+298)", 
    "Federated States of Micronesia (+691)", "Fiji (+679)", "Finland (+358)", 
    "France (+33)", "French Guiana (+594)", "French Polynesia (+689)", 
    "French Southern Territories (+0)", "Gabon (+241)", "Gambia (+220)", 
    "Georgia (+995)", "Germany (+49)", "Ghana (+233)", "Gibraltar (+350)", 
    "Greece (+30)", "Greenland (+299)", "Grenada (+1)", "Guadeloupe (+590)", 
    "Guam (+1)", "Guatemala (+502)", "Guernsey (+44)", "Guinea (+224)", 
    "Guinea-Bissau (+245)", "Guyana (+592)", "Haiti (+509)", 
    "Heard Island and McDonald Islands (+0)", "Honduras (+504)", "Hong Kong (+852)", 
    "Hungary (+36)", "Iceland (+354)", "India (+91)", "Indonesia (+62)", 
    "Iran (+98)", "Iraq (+964)", "Ireland (+353)", "Isle of Man (+44)", 
    "Israel (+972)", "Italy (+39)", "Jamaica (+1)", "Japan (+81)", 
    "Jersey (+44)", "Jordan (+962)", "Kazakhstan (+7)", "Kenya (+254)", 
    "Kiribati (+686)", "Korea (+82)", "Korea (North) (+850)", "Kosovo (+383)", 
    "Kuwait (+965)", "Kyrgyzstan (+996)", "Laos (+856)", "Latvia (+371)", 
    "Lebanon (+961)", "Lesotho (+266)", "Liberia (+231)", "Libya (+218)", 
    "Liechtenstein (+423)", "Lithuania (+370)", "Luxembourg (+352)", 
    "Macao (+853)", "Macedonia (+389)", "Madagascar (+261)", "Malawi (+265)", 
    "Malaysia (+60)", "Maldives (+960)", "Mali (+223)", "Malta (+356)", 
    "Marshall Islands (+692)", "Martinique (+596)", "Mauritania (+222)", 
    "Mauritius (+230)", "Mayotte (+262)", "Mexico (+52)", "Moldova (+373)", 
    "Monaco (+377)", "Mongolia (+976)", "Montenegro (+382)", "Montserrat (+1)", 
    "Morocco (+212)", "Mozambique (+258)", "Myanmar (+95)", "Namibia (+264)", 
    "Nauru (+674)", "Nepal (+977)", "Netherlands (+31)", 
    "Netherlands Antilles (+0)", "New Caledonia (+687)", "New Zealand (+64)", 
    "Nicaragua (+505)", "Niger (+227)", "Nigeria (+234)", "Niue (+683)", 
    "Norfolk Island (+672)", "Northern Mariana Islands (+1)", "Norway (+47)", 
    "Pakistan (+92)", "Palau (+680)", "Palestinian Territory (+970)", 
    "Panama (+507)", "Papua New Guinea (+675)", "Paraguay (+595)", "Peru (+51)", 
    "Philippines (+63)", "Pitcairn (+0)", "Poland (+48)", "Portugal (+351)", 
    "Puerto Rico (+1)", "Qatar (+974)", "Reunion (+262)", "Romania (+40)", 
    "Russian Federation (+7)", "Rwanda (+250)", 
    "S. Georgia and S. Sandwich Islands (+0)", "Saint Helena (+290)", 
    "Saint Kitts and Nevis (+1)", "Saint Lucia (+1)", 
    "Saint Pierre and Miquelon (+508)", "Saint Vincent and the Grenadines (+1)", 
    "Samoa (+685)", "San Marino (+378)", "Sao Tome and Principe (+239)", 
    "Saudi Arabia (+966)", "Senegal (+221)", "Serbia (+381)", 
    "Serbia and Montenegro (+0)", "Seychelles (+248)", "Sierra Leone (+232)", 
    "Singapore (+65)", "Slovak Republic (+421)", "Slovenia (+386)", 
    "Solomon Islands (+677)", "Somalia (+252)", "South Africa (+27)", 
    "South Sudan (+211)", "Spain (+34)", "Sri Lanka (+94)", "Sudan (+249)", 
    "Sultanate of Oman (+968)", "Suriname (+597)", "Svalbard and Jan Mayen (+47)", 
    "Swaziland (+268)", "Sweden (+46)", "Switzerland (+41)", "Syria (+963)", 
    "Taiwan (+886)", "Tajikistan (+992)", "Tanzania (+255)", "Thailand (+66)", 
    "Timor-Leste (+670)", "Togo (+228)", "Tokelau (+690)", "Tonga (+676)", 
    "Trinidad and Tobago (+1)", "Tunisia (+216)", "Turkey (+90)", 
    "Turkmenistan (+993)", "Turks and Caicos Islands (+1)", "Tuvalu (+688)", 
    "Uganda (+256)", "Ukraine (+380)", "United Arab Emirates (+971)", 
    "United Kingdom (+44)", "Uruguay (+598)", "Uzbekistan (+998)", 
    "Vanuatu (+678)", "Vatican City State (Holy See) (+39)", "Venezuela (+58)", 
    "Vietnam (+84)", "Virgin Islands (British) (+1)", "Virgin Islands (U.S.) (+1)", 
    "Wallis and Futuna (+681)", "Western Sahara (+212)", "Yemen (+967)", 
    "Zambia (+260)", "Zimbabwe (+263)"
]

# EEO选项定义 - 显示文本与标准值的映射
EEO_OPTIONS = {
    'gender': {
        'standard_values': ['I do not wish to identify', 'Male', 'Female'],
        'display_text': {
            'en': ['I do not wish to identify', 'Male', 'Female'],
            'zh': ['我不愿意透露', '男性', '女性']
        }
    },
    'race': {
        'standard_values': ['I do not wish to self identify',
                            'American Indian or Alaska Native', 'Asian',
                            'Black or African American', 'Hispanic or Latino',
                            'Native Hawaiian or Other Pacific Islander',
                            'Two or More Races', 'White'],
        'display_text': {
            'en': ['I do not wish to self identify', 'American Indian or Alaska Native', 'Asian',
                   'Black or African American', 'Hispanic or Latino',
                   'Native Hawaiian or Other Pacific Islander',
                   'Two or More Races', 'White'],
            'zh': ['我不愿意自我识别', '美洲原住民或阿拉斯加原住民', '亚裔',
                   '黑人或非裔美国人', '西班牙裔或拉丁裔',
                   '夏威夷原住民或其他太平洋岛民',
                   '两个或更多种族', '白人']
        }
    },
    'veteran': {
        'standard_values': ['I choose not to self-identify', 'I am a protected veteran',
                            'I am a veteran but not a protected veteran',
                            'I am not a protected veteran'],
        'display_text': {
            'en': ['I choose not to self-identify', 'I am a protected veteran',
                   'I am a veteran but not a protected veteran',
                   'I am not a protected veteran'],
            'zh': ['我选择不自我识别', '我是受保护的退伍军人', '我是退伍军人但不是受保护的退伍军人',
                   '我不是受保护的退伍军人']
        }
    },
    'disability': {
        'standard_values': ['I choose not to self-identify', 'Yes, I have a disability, or have had one in the past',
                            'No, I do not have a disability and have not had one in the past'],
        'display_text': {
            'en': ['I choose not to self-identify', 'Yes, I have a disability, or have had one in the past',
                   'No, I do not have a disability and have not had one in the past'],
            'zh': ['我选择不自我识别', '是的，我有残疾或曾经有过',
                   '不，我没有残疾且从未有过']
        }
    }
}


CONFIG_FILE = "config.yaml"
# DEFAULT_CONFIG now primarily defines structure and default *values* if a key *exists* but has no value,
# or if the config file is entirely missing. It's less about forcing specific keys onto the user's config.
DEFAULT_CONFIG = {
    'email': '', 'password': '', 'openaiApiKey': '', 'disableAntiLock': False, 'remote': False,
    'lessthanTenApplicants': True, 'newestPostingsFirst': False,
    'experienceLevel': {'internship': False, 'entry': True, 'associate': True, 'mid-senior level': True, 'director': False, 'executive': False},
    'jobTypes': {'full-time': True, 'contract': True, 'part-time': False, 'temporary': True, 'internship': False, 'other': False, 'volunteer': False},
    'date': {'all time': True, 'month': False, 'week': False, '24 hours': False, 'custom_hours': False},
    'positions': ['sales'], 'locations': ['united states'], 'residentStatus': False, 'distance': 100,
    'outputFileDirectory': '~/Documents/EasyApplyBot/', 'companyBlacklist': [], 'titleBlacklist': [], 'posterBlacklist': [],
    'uploads': {'resume': '', 'coverLetter': '', 'photo': ''},
    'checkboxes': {'driversLicence': True, 'requireVisa': False, 'legallyAuthorized': False, 'certifiedProfessional': True, 'urgentFill': True, 'commute': True, 'remote': True, 'drugTest': True, 'assessment': True, 'securityClearance': False, 'degreeCompleted': ["High School Diploma", "Bachelor's Degree"], 'backgroundCheck': True},
    'universityGpa': 4.0, 'salaryMinimum': 65000, 'languages': {'english': 'Native or bilingual'},
    'noticePeriod': 2, 'experience': {'default': 0}, 'personalInfo': {}, 
    'eeo': {'gender': EEO_OPTIONS["gender"]["standard_values"][0], 'race': EEO_OPTIONS["race"]["standard_values"][0],'veteran': EEO_OPTIONS["veteran"]["standard_values"][0], 'disability': EEO_OPTIONS["disability"]["standard_values"][0]}, 'textResume': '',
    'evaluateJobFit': False, 'debug': False,
    'customQuestions': {},  # 自定义问答配置
    'useCloudAI': True,  # 是否使用云服务API，默认为True
    'language': DEFAULT_LANGUAGE,  # 添加语言设置，默认为中文
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
    if not os.path.exists(CONFIG_FILE): print(f"Configuration Files {CONFIG_FILE} Does not exist..."); save_config(final_config); return final_config # Return default if file missing
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as stream:
            loaded_config = yaml.safe_load(stream)
            if not loaded_config: print(f"Configuration Files {CONFIG_FILE} Empty..."); return final_config # Return default if file empty
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
    except yaml.YAMLError as exc:
        messagebox.showerror("Configuration Error", f"Unable to parse config file: {exc}")
        return final_config # Return merged defaults on error
    except Exception as e:
        messagebox.showerror("Configuration Error", f"Error updating configuration: {e}")
        return final_config

def save_config(config):
    try:
        config_to_save = {} # Use a clean dict to ensure order from config
        for k, v in config.items():
            # Ensure nested structures are copied properly for saving
            if isinstance(v, dict): 
                config_to_save[k] = v.copy()
            elif isinstance(v, list):
                config_to_save[k] = v.copy()
            else:
                config_to_save[k] = v

        with open(CONFIG_FILE, 'w', encoding='utf-8') as stream:
            yaml.dump(config_to_save, stream, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return True
    except Exception as e: 
        import traceback
        print(f"Error saving configuration: {e}")
        traceback.print_exc()
        return False

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
        self.EEO_OPTIONS = EEO_OPTIONS
        self.config = load_config()
        self.lang_code = self.config.get('language', DEFAULT_LANGUAGE)
        self.texts = load_language(self.lang_code)

        self.title(self.texts['common']['app_title'])
        self.geometry("900x800") # Default size for main app

        # Store references to login screen widgets for language switching
        self.login_frame = None
        self.login_welcome_label = None
        self.login_please_login_label = None
        self.login_main_button = None
        self.login_exit_button = None
        self.login_progress_bar = None # Renamed from self.login_progress to avoid conflict
        self.login_status_text_label = None # Renamed from self.login_status_label
        self.login_copyright_label = None
        self.login_language_selector = None
        self.login_lang_var = None

        # Initialize other necessary attributes
        self.bot_process = None
        self.stop_event = threading.Event()
        self.job_application_thread = None
        self.pdf_extraction_thread = None
        self.pdf_extraction_stop_event = threading.Event()
        self.pdf_processing_dialog = None
        self.auth_data = None # Store authentication data (userId, apiKey)
        self.is_authenticated = False # Authentication status
        self.ocr_cancel_event = threading.Event() # Event to cancel OCR request

        # Check authentication status
        self._check_auth_status_and_init_ui()
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _check_auth_status_and_init_ui(self):
        auth_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth.json')
        if os.path.exists(auth_file_path):
            try:
                with open(auth_file_path, 'r', encoding='utf-8') as f:
                    auth_data_loaded = json.load(f)
                    if auth_data_loaded.get('userId') and auth_data_loaded.get('apiKey'):
                        self.auth_data = auth_data_loaded
                        self.is_authenticated = True
            except Exception as e:
                print(f"Error reading auth.json: {e}")
                self.auth_data = None
                self.is_authenticated = False
        
        if not self.is_authenticated:
            self._show_login_screen()
        else:
            # 已登录，正常初始化界面
            self._init_main_interface()
            print(f"User logged in, User ID: {self.auth_data.get('userId')}")

    def _show_login_screen(self):
        """显示登录欢迎界面，不显示主界面"""
        # 清空当前所有内容
        for widget in self.winfo_children():
            widget.destroy()
            
        # 设置窗口大小和标题
        self.geometry("500x450") # Increased height for language selector
        self.title(self.texts['login']['app_title'] if 'login' in self.texts else "Nuomi.ai Login")
        
        # 创建登录框架
        self.login_frame = ttk.Frame(self, padding=20)
        self.login_frame.pack(expand=True, fill=tk.BOTH)
        
        # 语言选择器
        lang_selector_frame = ttk.Frame(self.login_frame)
        lang_selector_frame.pack(pady=(0, 15), anchor='ne') # Anchor to top-right

        ttk.Label(lang_selector_frame, text=(self.texts['common']['language'] + ":" if 'common' in self.texts else "Language:")).pack(side=tk.LEFT, padx=(0,5))
        
        self.login_lang_var = tk.StringVar(value=self.lang_code)
        self.login_language_selector = ttk.Combobox(lang_selector_frame, textvariable=self.login_lang_var, state="readonly", width=18)
        self.login_language_selector['values'] = [f"{code} - {name}" for code, name in AVAILABLE_LANGUAGES.items()]
        for i, (code, _) in enumerate(AVAILABLE_LANGUAGES.items()):
            if code == self.lang_code:
                self.login_language_selector.current(i)
                break
        self.login_language_selector.pack(side=tk.LEFT)
        self.login_language_selector.bind("<<ComboboxSelected>>", self._on_login_language_changed)

        # 标题
        self.login_welcome_label = ttk.Label(self.login_frame, text=self.texts['login']['welcome'] if 'login' in self.texts else "Welcome to Nuomi.ai",
                  font=("Arial", 18, "bold"))
        self.login_welcome_label.pack(pady=(0, 20))
        
        self.login_please_login_label = ttk.Label(self.login_frame, text=self.texts['login']['please_login'] if 'login' in self.texts else "Please login to continue", 
                  font=("Arial", 12))
        self.login_please_login_label.pack(pady=(0, 30))
        
        # 登录按钮
        self.login_main_button = ttk.Button(self.login_frame, 
                                  text=self.texts['login']['login_register'] if 'login' in self.texts else "Login/Register", 
                                  command=self._handle_login)
        self.login_main_button.pack(pady=10, ipadx=20, ipady=10)
        
        # 退出按钮
        self.login_exit_button = ttk.Button(self.login_frame, 
                                 text=self.texts['login']['exit'] if 'login' in self.texts else "Exit", 
                                 command=self.destroy)
        self.login_exit_button.pack(pady=10)
        
        # 进度条和状态标签（初始隐藏）
        self.login_progress_bar = ttk.Progressbar(self.login_frame, orient="horizontal", length=300, mode="indeterminate")
        self.login_progress_bar.pack(pady=10, fill=tk.X)
        self.login_progress_bar.pack_forget()  # 初始隐藏
        
        self.login_status_text_label = ttk.Label(self.login_frame, 
                                           text=self.texts['login']['ready'] if 'login' in self.texts else "Ready to login...", 
                                           font=("Arial", 10))
        self.login_status_text_label.pack(pady=5)
        self.login_status_text_label.pack_forget()  # 初始隐藏
        
        # 隐私声明
        self.login_privacy_label = ttk.Label(self.login_frame, text=self.texts['common']['privacy_notice'] if 'common' in self.texts and 'privacy_notice' in self.texts['common'] else "We do not store your personal privacy information", font=("Arial", 8))
        self.login_privacy_label.pack(side=tk.BOTTOM, pady=(0, 5))
        
        # 版权信息
        self.login_copyright_label = ttk.Label(self.login_frame, text="© 2025 Nuomi.ai", font=("Arial", 8))
        self.login_copyright_label.pack(side=tk.BOTTOM, pady=(0, 15))
    
    def _on_login_language_changed(self, event):
        """处理登录界面语言变更事件"""
        selected_lang_display = self.login_lang_var.get()
        selected_lang_code = selected_lang_display.split(" - ")[0]

        if selected_lang_code != self.lang_code:
            self.lang_code = selected_lang_code
            self.config['language'] = self.lang_code
            self.texts = load_language(self.lang_code)
            
            # Update login screen UI elements
            self.title(self.texts['login']['app_title'] if 'login' in self.texts else "Nuomi.ai Login")
            if self.login_welcome_label:
                self.login_welcome_label.config(text=self.texts['login']['welcome'] if 'login' in self.texts else "Welcome to Nuomi.ai")
            if self.login_please_login_label:
                self.login_please_login_label.config(text=self.texts['login']['please_login'] if 'login' in self.texts else "Please login to continue")
            if self.login_main_button:
                self.login_main_button.config(text=self.texts['login']['login_register'] if 'login' in self.texts else "Login/Register")
            if self.login_exit_button:
                self.login_exit_button.config(text=self.texts['login']['exit'] if 'login' in self.texts else "Exit")
            if self.login_status_text_label and not self.login_progress_bar.winfo_ismapped(): # Only update if not in progress
                 self.login_status_text_label.config(text=self.texts['login']['ready'] if 'login' in self.texts else "Ready to login...")
            
            # 更新隐私声明
            if hasattr(self, 'login_privacy_label'):
                self.login_privacy_label.config(text=self.texts['common']['privacy_notice'] if 'common' in self.texts and 'privacy_notice' in self.texts['common'] else "We do not store your personal privacy information")

            # Also update the language selector label itself, if it exists within a frame that's part of login_frame
            # This assumes the label is the first child of the lang_selector_frame
            if self.login_language_selector:
                parent_frame = self.login_language_selector.master
                if parent_frame and parent_frame.winfo_children():
                    lang_label_widget = parent_frame.winfo_children()[0]
                    if isinstance(lang_label_widget, ttk.Label):
                         lang_label_widget.config(text=(self.texts['common']['language'] + ":" if 'common' in self.texts else "Language:"))
            
            # Save the configuration change
            save_config(self.config)


    def _handle_login(self):
        """处理登录按钮点击"""
        # 显示进度条和状态标签
        self.login_progress_bar.pack(pady=10, fill=tk.X)
        self.login_status_text_label.pack(pady=5)
        self.login_progress_bar.start(10)  # 开始动画
        
        status_text = self.texts['login']['authenticating'] if 'login' in self.texts else "Authenticating, please complete login in your browser..."
        self.login_status_text_label.config(text=status_text)
        
        # 禁用登录按钮，防止重复点击
        if self.login_frame: # Check if login_frame exists
            for widget in self.login_frame.winfo_children(): # Iterate through children of login_frame
                if isinstance(widget, ttk.Button):
                    widget.config(state="disabled")
                # Also disable the language selector if it's a direct child or in a sub-frame
                elif isinstance(widget, ttk.Frame): # Assuming lang selector is in a sub-frame
                    for sub_widget in widget.winfo_children():
                        if isinstance(sub_widget, ttk.Combobox):
                            sub_widget.config(state="disabled")
        
        # 使用线程处理认证过程
        def auth_thread_func():
            try:
                auth_result = auth_server.authenticate(lang=self.lang_code.replace('_', '-'))
                
                # 在主线程中更新UI
                self.after(100, lambda: self._process_auth_result(auth_result))
            except Exception as e:
                print(f"Login processing error: {str(e)}")
                traceback.print_exc()
                # 在主线程中显示错误
                self.after(100, lambda: self._show_auth_error(str(e)))
        
        # 启动认证线程
        auth_thread = threading.Thread(target=auth_thread_func)
        auth_thread.daemon = True
        auth_thread.start()
        
    def _process_auth_result(self, auth_result):
        """处理认证结果"""
        # 停止进度条动画
        if self.login_progress_bar: # Check if progress bar exists
            self.login_progress_bar.stop()
        
        if auth_result and auth_result.get('user_id') and auth_result.get('api_key'):
            # 认证成功
            self.auth_data = auth_result
            self.is_authenticated = True
            
            # 更新状态标签
            success_text = self.texts['login']['success'] if 'login' in self.texts else "Login successful! Loading main interface..."
            if self.login_status_text_label: # Check if status label exists
                self.login_status_text_label.config(text=success_text)
            
            # 显示成功消息
            messagebox.showinfo(
                self.texts['login']['success_title'] if 'login' in self.texts else "Login Successful",
                self.texts['login']['success_message'] if 'login' in self.texts else "Login successful! Loading main interface..."
            )
            
            # 加载主界面
            self._init_main_interface()
            return True
        else:
            # 认证失败
            warning_title = self.texts['login']['failed_title'] if 'login' in self.texts else "Login Failed"
            warning_message = self.texts['login']['failed_message'] if 'login' in self.texts else "Login was not completed. Please try again."
            
            messagebox.showwarning(warning_title, warning_message)
            
            # 恢复按钮状态
            if self.login_frame: # Check if login_frame exists
                for widget in self.login_frame.winfo_children():
                    if isinstance(widget, ttk.Button):
                        widget.config(state="normal")
                    elif isinstance(widget, ttk.Frame): # Assuming lang selector is in a sub-frame
                         for sub_widget in widget.winfo_children():
                            if isinstance(sub_widget, ttk.Combobox):
                                sub_widget.config(state="readonly") # Restore to readonly
            
            # 隐藏进度条和状态标签
            if self.login_progress_bar: self.login_progress_bar.pack_forget()
            if self.login_status_text_label: self.login_status_text_label.pack_forget()
            return False
    
    def _show_auth_error(self, error_message):
        """显示认证错误"""
        # 停止进度条动画
        if self.login_progress_bar: self.login_progress_bar.stop()
        
        # 显示错误消息
        error_title = self.texts['login']['error_title'] if 'login' in self.texts else "Login Error"
        error_prefix = self.texts['login']['error_prefix'] if 'login' in self.texts else "Login process encountered an error: "
        
        messagebox.showerror(error_title, f"{error_prefix}{error_message}")
        
        # 恢复按钮状态
        if self.login_frame: # Check if login_frame exists
            for widget in self.login_frame.winfo_children():
                if isinstance(widget, ttk.Button):
                    widget.config(state="normal")
                elif isinstance(widget, ttk.Frame): # Assuming lang selector is in a sub-frame
                     for sub_widget in widget.winfo_children():
                        if isinstance(sub_widget, ttk.Combobox):
                            sub_widget.config(state="readonly") # Restore to readonly
        
        # 隐藏进度条和状态标签
        if self.login_progress_bar: self.login_progress_bar.pack_forget()
        if self.login_status_text_label: self.login_status_text_label.pack_forget()
        return False
            
    def _init_main_interface(self):
        """初始化主界面"""
        # 清空当前所有内容
        for widget in self.winfo_children():
            widget.destroy()
            
        # 重新设置窗口大小
        self.geometry("900x800")
        self.title(self.texts['common']['app_title'])
        
        # --- 旧配置迁移到 positionsWithCount ---
        if (self.config.get('positions') and 
            isinstance(self.config.get('positions'), list) and 
            len(self.config.get('positions')) > 0 and
            (not self.config.get('positionsWithCount') or 
             (isinstance(self.config.get('positionsWithCount'), list) and len(self.config.get('positionsWithCount')) == 0))):
            
            print("Old position configuration detected, attempting to migrate...")
            migrated_positions_with_count = []
            for old_position_name in self.config['positions']:
                if isinstance(old_position_name, str) and old_position_name.strip():
                    migrated_positions_with_count.append({
                        "name": old_position_name.strip(),
                        "count": 100  # 默认投递数量
                    })
            if migrated_positions_with_count:
                self.config['positionsWithCount'] = migrated_positions_with_count
                print(f"Migrated {len(migrated_positions_with_count)} positions to new configuration format. Please review and save the configuration.")
                # Optionally, clear the old positions to avoid confusion if needed, or let backend handle it
                # self.config['positions'] = [] 

        # 初始化带数量限制的职位配置 (确保在 self.vars 初始化之前或同步进行)
        if 'positionsWithCount' not in self.config or not isinstance(self.config['positionsWithCount'], list):
            self.config['positionsWithCount'] = []
        # self.positions_with_count 成员变量将在 _create_job_tab 中直接引用 self.config['positionsWithCount']

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
                        print(f"Unable to parse the problem string: {question}")
                if isinstance(answer, str) and answer.startswith('"') and answer.endswith('"'):
                    try:
                        answer = json.loads(answer)
                    except:
                        print(f"Unable to parse answer string: {answer}")
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
            'coverletter_path': tk.StringVar(value=self.config.get('uploads', {}).get('coverLetter', '')),
            'photo_path': tk.StringVar(value=self.config.get('uploads', {}).get('photo', '')),
            # Job
            'positions': tk.StringVar(value=safe_join_list(self.config.get('positions', []))),
            'locations': tk.StringVar(value=safe_join_list(self.config.get('locations', []))),
            'distance': tk.IntVar(value=self.config.get('distance', 100)),
            'search_remote': tk.BooleanVar(value=self.config.get('remote', False)),
            'lessthanTenApplicants': tk.BooleanVar(value=self.config.get('lessthanTenApplicants', True)),
            'lessApplicantsEnabled': tk.BooleanVar(value=self.config.get('lessApplicantsEnabled', False)),
            'lessApplicantsCount': tk.StringVar(value=str(self.config.get('lessApplicantsCount', 100))),
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
            'personalInfo': {}, 'eeo': {}, 'degreeCompleted': {}, 'checkboxes': {},
            'useCloudAI': tk.BooleanVar(value=self.config.get('useCloudAI', False)),
            # AI服务器设置
            'aiServerUrl': tk.StringVar(value=self.config.get('aiServerUrl', 'https://api.nuomi.ai/api')),
            'speed_mode': tk.StringVar(value='slow'),  # 添加速度模式变量，默认为慢速模式
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

        # --- GUI Structure --- (只保留控制面板，其他配置移至 Firebase web 端)
        self.notebook = ttk.Notebook(self)
        self.control_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.control_tab, text=self.texts['tabs']['control'])
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # 只创建控制面板
        self._create_control_tab()
        
        # 初始化 Firebase 监听
        self._init_firebase_listener()
        
        # --- 添加语言选择下拉菜单 ---
        self._create_language_selector()
        
        # 隐私声明
        self.privacy_label = tk.Label(self, text=self.texts['common']['privacy_notice'] if 'common' in self.texts and 'privacy_notice' in self.texts['common'] else "We do not store your personal privacy information", font=("Arial", 8))
        self.privacy_label.pack(side=tk.BOTTOM, pady=(0, 5))
        
        self.status_label = tk.Label(self, text=self.texts['common']['ready'], bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 绑定标签页切换事件
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    # --- Helper and Tab Creation Methods ---
    def _on_tab_changed(self, event):
        """当标签页切换时调用 - 现在只有控制面板标签"""
        # 由于现在只有控制面板标签，这个方法基本不需要处理特殊逻辑
        pass

    def _get_current_date_pref(self):
        date_prefs = self.config.get('date', {}); # Default to empty dict if missing
        if isinstance(date_prefs, dict):
            # 检查custom_hours选项
            if date_prefs.get('custom_hours', False):
                return 'custom_hours'
            # 检查其他标准选项
            for key, value in date_prefs.items():
                if value and key != 'custom_hours': 
                    return key
        return 'all time' # Fallback

    def _create_basic_tab(self):
        # (No significant changes needed, uses _browse_file now)
        frame = ttk.LabelFrame(self.basic_tab, text=self.texts['basic_tab']['account_resume'], padding=(10, 5)); frame.pack(expand=True, fill="both", padx=10, pady=5); frame.columnconfigure(1, weight=1); current_row=0
        ttk.Label(frame, text=self.texts['basic_tab']['email']).grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(frame, textvariable=self.vars['email'], width=60).grid(row=current_row, column=1, sticky=tk.EW, padx=5, pady=3); current_row+=1
        ttk.Label(frame, text=self.texts['basic_tab']['password']).grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(frame, textvariable=self.vars['password'], width=60).grid(row=current_row, column=1, sticky=tk.EW, padx=5, pady=3); current_row+=1
        # ttk.Label(frame, text=self.texts['basic_tab']['openai_api_key']).grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(frame, textvariable=self.vars['openaiApiKey'], width=60).grid(row=current_row, column=1, sticky=tk.EW, padx=5, pady=3); current_row+=1
        # ttk.Label(frame, text=self.texts['basic_tab']['openai_api_key_note']).grid(row=current_row, column=1, sticky=tk.W, padx=5); current_row+=1
        
        
        # 更新简历上传提示和文件类型
        ttk.Label(frame, text=self.texts['basic_tab']['resume_path']).grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3)
        resume_frame = ttk.Frame(frame)
        ttk.Entry(resume_frame, textvariable=self.vars['resume_path'], width=42).pack(side=tk.LEFT, fill=tk.X, expand=True)  # 调整宽度为42，为新按钮留出空间
        ttk.Button(resume_frame, text=self.texts['common']['browse'], command=lambda: self._browse_file(self.vars['resume_path'], self.texts['basic_tab']['resume_path'], "*.pdf")).pack(side=tk.LEFT, padx=(5,0))
        # 添加新的按钮，用于提取PDF文本 - MODIFIED TEXT
        ttk.Button(resume_frame, text=self.texts['basic_tab']['extract_text'], command=self._trigger_aws_pdf_extraction_from_button).pack(side=tk.LEFT, padx=(5,0))
        resume_frame.grid(row=current_row, column=1, sticky=tk.EW, padx=5, pady=3)
        current_row+=1
        ttk.Label(frame, text=self.texts['basic_tab']['pdf_only']).grid(row=current_row, column=1, sticky=tk.W, padx=5)
        current_row+=1
        
        # ttk.Label(frame, text=self.texts['basic_tab']['text_resume_path']).grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3); text_resume_frame = ttk.Frame(frame); ttk.Entry(text_resume_frame, textvariable=self.vars['textResume_path'], width=52).pack(side=tk.LEFT, fill=tk.X, expand=True); ttk.Button(text_resume_frame, text=self.texts['common']['browse'], command=lambda: self._browse_text_resume_and_update_ai_tab()).pack(side=tk.LEFT, padx=(5,0)); text_resume_frame.grid(row=current_row, column=1, sticky=tk.EW, padx=5, pady=3); current_row+=1
        
        # 更新求职信上传提示和文件类型
        ttk.Label(frame, text=self.texts['basic_tab']['cover_letter_path']).grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3)
        cover_letter_frame = ttk.Frame(frame)
        ttk.Entry(cover_letter_frame, textvariable=self.vars['coverletter_path'], width=52).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(cover_letter_frame, text=self.texts['common']['browse'], command=lambda: self._browse_file(self.vars['coverletter_path'], self.texts['basic_tab']['cover_letter_path'], "*.pdf")).pack(side=tk.LEFT, padx=(5,0))
        cover_letter_frame.grid(row=current_row, column=1, sticky=tk.EW, padx=5, pady=3)
        current_row+=1
        ttk.Label(frame, text=self.texts['basic_tab']['cover_letter_note']).grid(row=current_row, column=1, sticky=tk.W, padx=5)
        current_row+=1
        
        # 更新照片上传提示和文件类型
        ttk.Label(frame, text=self.texts['basic_tab']['photo_path']).grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3)
        photo_frame = ttk.Frame(frame)
        ttk.Entry(photo_frame, textvariable=self.vars['photo_path'], width=52).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(photo_frame, text=self.texts['common']['browse'], command=lambda: self._browse_file(self.vars['photo_path'], self.texts['basic_tab']['photo_path'], "*.png *.jpg *.jpeg")).pack(side=tk.LEFT, padx=(5,0))
        photo_frame.grid(row=current_row, column=1, sticky=tk.EW, padx=5, pady=3)
        current_row+=1
        ttk.Label(frame, text=self.texts['basic_tab']['photo_note']).grid(row=current_row, column=1, sticky=tk.W, padx=5)
        current_row+=1
        
        ttk.Checkbutton(frame, text=self.texts['basic_tab']['disable_antilock'], variable=self.vars['disableAntiLock']).grid(row=current_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10); current_row+=1

    def _browse_file(self, path_var, file_desc, file_pattern):
        filepath = filedialog.askopenfilename(title=f"{self.texts['common']['select_file']} {file_desc}", filetypes=((f"{file_desc} Files", file_pattern), ("All Files", "*.*")))
        if filepath:
            # 检查文件大小
            filesize = os.path.getsize(filepath) / (1024 * 1024)  # 转换为MB
            
            # 根据文件类型检查大小限制
            if self.texts['common']['resume'] in file_desc and filesize > 2:
                messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['file_too_large'].format(file_desc, "2MB", f"{filesize:.2f}"))
                return
            elif self.texts['common']['cover_letter'] in file_desc and filesize > 0.5:
                messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['file_too_large'].format(file_desc, "512KB", f"{filesize:.2f}"))
                return
            elif self.texts['common']['photo'] in file_desc and filesize > 1:
                messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['file_too_large'].format(file_desc, "1MB", f"{filesize:.2f}"))
                return
                
            path_var.set(filepath)

    def _trigger_aws_pdf_extraction_from_button(self):
        """通过API将PDF转换为文本的按钮回调函数"""
        # 获取PDF路径
        pdf_filepath = self.vars['resume_path'].get()
        if not pdf_filepath:
            messagebox.showerror(self.texts['common']['error'], self.texts['messages']['no_pdf'])
            self._log_message(self.texts['messages']['no_pdf'])
            return

        if not pdf_filepath.lower().endswith(".pdf"):
            messagebox.showerror(self.texts['common']['error'], self.texts['messages']['not_pdf'])
            self._log_message(self.texts['messages']['not_pdf'].format(os.path.basename(pdf_filepath)))
            return

        self._log_message(self.texts['messages']['start_extract'].format(os.path.basename(pdf_filepath)))
        
        # Initialize cancel flag
        self.request_canceled = False # Ensure this is reset for each request

        try:
            pdf_filename = os.path.basename(pdf_filepath)
            
            loading_dialog = tk.Toplevel(self)
            loading_dialog.title(self.texts['messages']['pdf_processing'])
            loading_dialog.geometry("300x150") 
            loading_dialog.transient(self)
            loading_dialog.grab_set()
            loading_dialog.resizable(False, False)
            
            loading_dialog.update_idletasks()
            width = loading_dialog.winfo_width()
            height = loading_dialog.winfo_height()
            x = (loading_dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (loading_dialog.winfo_screenheight() // 2) - (height // 2)
            loading_dialog.geometry(f'{width}x{height}+{x}+{y}')
            
            ttk.Label(loading_dialog, text=self.texts['messages']['processing_file'].format(pdf_filename), 
                     font=("Helvetica", 10, "bold")).pack(pady=(20, 10))
            ttk.Label(loading_dialog, text=self.texts['messages']['please_wait']).pack(pady=5)
            
            progress = ttk.Progressbar(loading_dialog, mode="indeterminate", length=250)
            progress.pack(pady=10, padx=20)
            progress.start(10)

            def on_dialog_close(dialog_ref):
                self.request_canceled = True
                self._log_message(self.texts['messages']['ocr_canceled'])
                if dialog_ref.winfo_exists(): # Check if dialog still exists
                    dialog_ref.destroy()

            def process_request():
                try:
                    with open(pdf_filepath, 'rb') as pdf_file:
                        files = {'pdf': (pdf_filename, pdf_file, 'application/pdf')}
                        
                        # Use OCR_API defined at the top of the file
                        response = requests.post(OCR_API, files=files, timeout=180) # Increased timeout to 180s
                        
                        if self.request_canceled:
                            self._log_message("OCR request was canceled by user, skipping response processing.")
                            return

                        if response.status_code == 200:
                            data = response.json()
                            if data.get('success'):
                                extracted_text = data.get('text', '')
                                if isinstance(extracted_text, list):
                                    extracted_text = '\\\\n'.join(str(x) for x in extracted_text)
                                elif not isinstance(extracted_text, str):
                                    extracted_text = str(extracted_text)

                                output_txt_filename = os.path.splitext(pdf_filename)[0] + ".txt"
                                output_txt_path = os.path.join(os.path.dirname(pdf_filepath), output_txt_filename)

                                with open(output_txt_path, "w", encoding="utf-8") as f:
                                    f.write(extracted_text)
                                
                                self.after(0, lambda: self._log_message(self.texts['messages']['extract_success'].format(pdf_filename, output_txt_filename)))
                                
                                self.after(0, lambda: self.vars['textResume_path'].set(output_txt_path))
                                
                                current_config = self.config.copy()
                                current_config['textResume'] = output_txt_path
                                self.after(0, lambda: self._save_config(current_config))
                                
                                # NEW: Switch to AI Assistant tab and run AI
                                self.after(0, self._switch_to_ai_assistant_and_run_ai)
                            else:
                                error_msg = data.get('message', 'Unknown error')
                                self.after(0, lambda: self._log_message(f"{self.texts['messages']['extract_fail'].format(pdf_filename)}: {error_msg}"))
                                self.after(0, lambda: messagebox.showwarning(self.texts['common']['warning'], 
                                                                           f"{self.texts['messages']['extract_fail'].format(pdf_filename)}: {error_msg}"))
                        else:
                            self.after(0, lambda: self._log_message(f"{self.texts['messages']['extract_fail'].format(pdf_filename)}: {response.status_code} {response.text}"))
                            self.after(0, lambda: messagebox.showwarning(self.texts['common']['warning'], 
                                                                       f"{self.texts['messages']['extract_fail'].format(pdf_filename)}: 服务器返回状态码 {response.status_code}"))
                except requests.exceptions.Timeout:
                    if not self.request_canceled:
                        self.after(0, lambda: self._log_message(self.texts['messages']['ocr_timeout']))
                        self.after(0, lambda: messagebox.showerror(self.texts['common']['error'], self.texts['messages']['ocr_timeout']))
                except Exception as e:
                    if not self.request_canceled:
                        error_message = str(e)
                        self.after(0, lambda: self._log_message(self.texts['messages']['extract_error'].format(error_message)))
                        self.after(0, lambda: messagebox.showerror(self.texts['common']['error'], 
                                                                 self.texts['messages']['extract_error'].format(error_message)))
                finally:
                    if loading_dialog.winfo_exists():
                         self.after(0, loading_dialog.destroy)
            
            self._log_message(self.texts['messages']['sending_to_ocr'])
            thread = threading.Thread(target=process_request, daemon=True)
            thread.start()
            loading_dialog.protocol("WM_DELETE_WINDOW", lambda: on_dialog_close(loading_dialog))
            
        except Exception as e:
            self._log_message(self.texts['messages']['extract_error'].format(str(e)))
            messagebox.showerror(self.texts['common']['error'], self.texts['messages']['extract_error'].format(str(e)))

    def _switch_to_ai_assistant_and_run_ai(self):
        """Switches to the AI Assistant tab and triggers the Run AI action."""
        try:
            ai_tab_text = self.texts['tabs']['ai_assistant']
            tab_id_to_select = None
            # Iterate through tab IDs to find the AI Assistant tab by its text
            for tab_id in self.notebook.tabs():
                if self.notebook.tab(tab_id, "text") == ai_tab_text:
                    tab_id_to_select = tab_id
                    break
            
            if tab_id_to_select is not None: # Check if tab_id_to_select was found
                self.notebook.select(tab_id_to_select)
                self._log_message(f"Switched to {ai_tab_text} tab.")
                
                self.update_idletasks() # Ensure UI updates before running AI
                
                # This function should ideally read the resume text from the updated
                # self.vars['textResume_path'] or the content displayed in the AI assistant tab.
                self._run_ai_assistant()
            else:
                self._log_message(f"Error: Could not find {ai_tab_text} tab.。")
                messagebox.showerror(self.texts['common']['error'], f"Not Found {ai_tab_text} tab.")
        except Exception as e:
            # Log the full traceback for debugging
            import traceback
            tb_str = traceback.format_exc()
            self._log_message(f"Error when switching to AI Assistant and running AI: {e}\\n{tb_str}")
            messagebox.showerror(self.texts['common']['error'], f"Error when switching to AI Assistant and running AI: {e}")

    def _browse_text_resume_and_update_ai_tab(self):
        """浏览文本简历文件并更新AI助手标签页中的状态"""
        filepath = filedialog.askopenfilename(title=self.texts['common']['select_file'], filetypes=(("Text Files", "*.txt"), ("All Files", "*.*")))
        if filepath:
            self.vars['textResume_path'].set(filepath)
            # 如果AI助手标签页已创建，则调用其更新方法
            if hasattr(self, 'resume_status_label') and self.resume_status_label.winfo_exists():
                self._check_resume_file() 

    def _create_job_tab(self):
        # 主框架，包含所有内容
        main_job_frame = ttk.Frame(self.job_tab, padding=(10, 5))
        main_job_frame.pack(expand=True, fill="both", padx=10, pady=5)
        main_job_frame.columnconfigure(1, weight=1) # 允许第二列扩展

        # --- 带数量限制的职位配置部分 ---
        positions_config_frame = ttk.LabelFrame(main_job_frame, text=self.texts['job_tab']['position_config'], padding=(10, 5))
        positions_config_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        positions_config_frame.columnconfigure(0, weight=1) #让listbox部分能扩展

        listbox_container = ttk.Frame(positions_config_frame)
        listbox_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.positions_listbox = tk.Listbox(listbox_container, height=8) # 调整高度
        scrollbar = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL, command=self.positions_listbox.yview)
        self.positions_listbox.configure(yscrollcommand=scrollbar.set)
        self.positions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        position_buttons_frame = ttk.Frame(positions_config_frame)
        position_buttons_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Button(position_buttons_frame, text=self.texts['job_tab']['add_position'], command=self._add_position_with_count_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(position_buttons_frame, text=self.texts['job_tab']['modify_position'], command=self._modify_position_with_count_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(position_buttons_frame, text=self.texts['job_tab']['delete_position'], command=self._remove_position_with_count).pack(side=tk.LEFT, padx=5)
        
        # 直接引用 self.config['positionsWithCount'] 来更新列表
        self._update_positions_with_count_listbox()

        # --- 其他搜索条件框架 ---
        other_conditions_frame = ttk.LabelFrame(main_job_frame, text=self.texts['job_tab']['global_search'], padding=(10, 5))
        other_conditions_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=10, sticky=tk.EW)
        other_conditions_frame.columnconfigure(1, weight=1)

        # 目标地点 (恢复旧的地点输入方式)
        ttk.Label(other_conditions_frame, text=self.texts['job_tab']['target_location']).grid(row=0, column=0, sticky=tk.NW, padx=5, pady=3)
        self.locations_widget = scrolledtext.ScrolledText(other_conditions_frame, wrap=tk.WORD, height=5, width=60)
        self.locations_widget.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=3)
        # 从 self.vars 加载地点数据, self.vars['locations'] 在 __init__ 中初始化
        if self.vars['locations'].get(): # 确保不插入 None 或空字符串
            self.locations_widget.insert(tk.END, self.vars['locations'].get())

        # 搜索半径 (恢复)
        dist_frame = ttk.Frame(other_conditions_frame)
        ttk.Label(dist_frame, text=self.texts['job_tab']['search_radius']).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Combobox(dist_frame, textvariable=self.vars['distance'], values=[0, 5, 10, 25, 50, 100], state="readonly", width=5).pack(side=tk.LEFT)
        dist_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        # 其他复选框 (恢复)
        chk_frame = ttk.Frame(other_conditions_frame)
        chk_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        ttk.Checkbutton(chk_frame, text=self.texts['job_tab']['remote_only'], variable=self.vars['search_remote']).pack(anchor=tk.W)
        ttk.Checkbutton(chk_frame, text=self.texts['job_tab']['less_than_ten'], variable=self.vars['lessthanTenApplicants']).pack(anchor=tk.W)
        
        # 添加筛选少于X名申请者的选项(X可选择)
        less_than_frame = ttk.Frame(chk_frame)
        less_than_frame.pack(anchor=tk.W)
        
        # 创建变量，如果不存在则初始化
        if 'lessApplicantsEnabled' not in self.vars:
            self.vars['lessApplicantsEnabled'] = tk.BooleanVar(value=False)
        if 'lessApplicantsCount' not in self.vars:
            # 从配置中获取值，确保在1-100之间
            default_count = 100
            if 'lessApplicantsCount' in self.config:
                try:
                    config_value = int(self.config['lessApplicantsCount'])
                    if 1 <= config_value <= 100:
                        default_count = config_value
                except (ValueError, TypeError):
                    pass
            self.vars['lessApplicantsCount'] = tk.StringVar(value=str(default_count))
            
        # 添加复选框和数字输入框
        ttk.Checkbutton(less_than_frame, text=self.texts['job_tab']['filter_less_than'], variable=self.vars['lessApplicantsEnabled']).pack(side=tk.LEFT)
        
        # 创建一个验证函数，只允许输入1-100的整数
        def validate_number(input_value):
            # 允许空字符串以便于删除
            if input_value == "":
                return True
            # 检查是否为数字
            if not input_value.isdigit():
                return False
            # 检查范围是否为1-100
            value = int(input_value)
            return 1 <= value <= 100
            
        # 注册验证器
        validate_cmd = self.register(validate_number)
        
        # 创建带验证的整数输入框
        less_count_entry = ttk.Entry(less_than_frame, textvariable=self.vars['lessApplicantsCount'], 
                               validate="key", validatecommand=(validate_cmd, '%P'), width=5)
        less_count_entry.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(less_than_frame, text=self.texts['job_tab']['applicants_label']).pack(side=tk.LEFT)
        
        # 其他原有选项
        ttk.Checkbutton(chk_frame, text=self.texts['job_tab']['newest_first'], variable=self.vars['newestPostingsFirst']).pack(anchor=tk.W)
        ttk.Checkbutton(chk_frame, text=self.texts['job_tab']['resident_status'], variable=self.vars['residentStatus']).pack(anchor=tk.W)

    def _add_position_with_count_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title(self.texts['job_tab']['add_position'])
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding=(10, 5))
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=self.texts['job_tab']['position_name']).grid(row=0, column=0, sticky=tk.W, pady=5)
        name_entry = ttk.Entry(main_frame, width=40)
        name_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)
        name_entry.focus_set()

        ttk.Label(main_frame, text=self.texts['job_tab']['target_count']).grid(row=1, column=0, sticky=tk.W, pady=5)
        count_entry = ttk.Entry(main_frame, width=10)
        count_entry.insert(0, "100")
        count_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

        def on_ok():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror(self.texts['common']['error'], self.texts['messages']['input_error'].format(self.texts['job_tab']['position_name']), parent=dialog); return
            try:
                count = int(count_entry.get().strip())
                if count <= 0: raise ValueError(self.texts['messages']['invalid_integer'].format(self.texts['job_tab']['target_count']))
            except ValueError as e:
                messagebox.showerror(self.texts['common']['error'], f"{self.texts['messages']['invalid_integer'].format(self.texts['job_tab']['target_count'])}: {e}", parent=dialog); return
            
            self.config['positionsWithCount'].append({"name": name, "count": count})
            self._update_positions_with_count_listbox()
            dialog.destroy()

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text=self.texts["common"]["ok"], command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=self.texts["common"]["cancel"], command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        main_frame.columnconfigure(1, weight=1)

    def _modify_position_with_count_dialog(self):
        selection = self.positions_listbox.curselection()
        if not selection: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['no_selection'].format(self.texts['common']['modify'], self.texts['job_tab']['position_name'])); return
        index = selection[0]
        position_config_to_edit = self.config['positionsWithCount'][index]

        dialog = tk.Toplevel(self)
        dialog.title(self.texts['job_tab']['modify_position'])
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding=(10, 5))
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=self.texts["job_tab"]["position_name"]).grid(row=0, column=0, sticky=tk.W, pady=5)
        name_entry = ttk.Entry(main_frame, width=40)
        name_entry.insert(0, position_config_to_edit["name"])
        name_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)
        name_entry.focus_set()

        ttk.Label(main_frame, text=self.texts["job_tab"]["target_count"]).grid(row=1, column=0, sticky=tk.W, pady=5)
        count_entry = ttk.Entry(main_frame, width=10)
        count_entry.insert(0, str(position_config_to_edit.get("count", 100)))
        count_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

        def on_ok():
            name = name_entry.get().strip()
            if not name: messagebox.showerror(self.texts['common']['error'], self.texts['messages']['input_error'].format(self.texts['job_tab']['position_name']), parent=dialog); return
            try:
                count = int(count_entry.get().strip())
                if count <= 0: raise ValueError("The delivery quantity must be a positive integer")
            except ValueError as e:
                messagebox.showerror(self.texts['common']['error'], f"{self.texts['messages']['invalid_integer'].format(self.texts['job_tab']['target_count'])}: {e}", parent=dialog); return

            self.config['positionsWithCount'][index]["name"] = name
            self.config['positionsWithCount'][index]["count"] = count
            self._update_positions_with_count_listbox()
            dialog.destroy()

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text=self.texts["common"]["ok"], command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=self.texts["common"]["cancel"], command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        main_frame.columnconfigure(1, weight=1)

    def _remove_position_with_count(self):
        selection = self.positions_listbox.curselection()
        if not selection: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['no_selection'].format(self.texts['common']['delete'], self.texts['job_tab']['position_name'])); return
        if messagebox.askyesno(self.texts['common']['confirm'], self.texts['messages']['confirm_delete'].format(1, self.texts['job_tab']['position_name'])):
            indices = list(selection)
            indices.sort(reverse=True)
            for index in indices:
                del self.config['positionsWithCount'][index]
            self._update_positions_with_count_listbox()

    def _update_positions_with_count_listbox(self):
        self.positions_listbox.delete(0, tk.END)
        if self.config.get('positionsWithCount'): #直接使用 self.config 中的列表
            for config_item in self.config['positionsWithCount']:
                if isinstance(config_item, dict) and 'name' in config_item:
                    display_text = f"{config_item['name']} ({self.texts['job_tab']['target_count_display']}: {config_item.get('count', 100)})"
                    self.positions_listbox.insert(tk.END, display_text)
                else:
                    self.positions_listbox.insert(tk.END, f"{self.texts['common']['invalid_entry']}: {str(config_item)}")

    def _create_preferences_tab(self):
        main_frame = ttk.Frame(self.preferences_tab, padding=(10, 5))
        main_frame.pack(expand=True, fill="both", padx=10, pady=5)
        # Configure columns to have equal weight
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # --- Experience Level Frame ---
        exp_frame = ttk.LabelFrame(main_frame, text=self.texts['preferences_labels']['experience_level_frame'], padding=(10, 5))
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
        job_frame = ttk.LabelFrame(main_frame, text=self.texts['preferences_labels']['job_type_frame'], padding=(10, 5))
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
        date_frame = ttk.LabelFrame(main_frame, text=self.texts['preferences_labels']['date_posted_frame'], padding=(10, 5))
        date_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        date_prefs = {'all time': self.texts['preferences_tab']['all_time'], 'month': self.texts['preferences_tab']['month'], 'week': self.texts['preferences_tab']['week'], '24 hours': self.texts['preferences_tab']['24_hours']}
        for i, (key, text) in enumerate(date_prefs.items()):
            ttk.Radiobutton(date_frame, text=text, variable=self.vars['date_pref'], value=key).pack(
                anchor=tk.W, padx=5, pady=1
            )
            
        # 添加自定义小时数选项
        custom_hours_frame = ttk.Frame(date_frame)
        custom_hours_frame.pack(anchor=tk.W, padx=5, pady=1)
        
        # 确保自定义小时数变量存在
        if 'custom_hours' not in self.vars:
            # 自定义小时数默认为1小时
            default_hours = 1
            if 'customHours' in self.config:
                try:
                    config_hours = int(self.config['customHours'])
                    if config_hours > 0:  # 确保是正数
                        default_hours = config_hours
                except (ValueError, TypeError):
                    pass  # 使用默认值
            self.vars['custom_hours'] = tk.StringVar(value=str(default_hours))
        
        # 创建验证函数，只允许输入正整数
        def validate_hours(input_value):
            # 允许空字符串以便于删除
            if input_value == "":
                return True
            # 检查是否为数字
            if not input_value.isdigit():
                return False
            # 检查是否为正数
            value = int(input_value)
            return value > 0
        
        # 注册验证器
        validate_cmd = self.register(validate_hours)
        
        # 创建单选按钮和输入框组合
        ttk.Radiobutton(custom_hours_frame, text=self.texts['preferences_tab']['past'], 
                      variable=self.vars['date_pref'], value='custom_hours').pack(side=tk.LEFT, padx=0, pady=0)
        
        # 创建带验证的小时数输入框
        hours_entry = ttk.Entry(custom_hours_frame, textvariable=self.vars['custom_hours'], 
                             validate="key", validatecommand=(validate_cmd, '%P'), width=5)
        hours_entry.pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Label(custom_hours_frame, text=self.texts['preferences_tab']['hours']).pack(side=tk.LEFT)


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
                 
            # 检查下拉框是否激活 - 如果激活则不滚动
            if hasattr(self, 'dropdown_active') and self.dropdown_active:
                return "break"  # 阻止事件传播
                
            self.adv_canvas.yview_scroll(delta, "units")

        # 保存函数引用以供后续使用
        self._on_mousewheel_func = _on_mousewheel
        
        # 初始化下拉框状态标志
        self.dropdown_active = False

        # 直接使用全局绑定，因为我们会在标签切换时管理这些绑定
        self.bind_all("<MouseWheel>", _on_mousewheel) 
        self.bind_all("<Button-4>", _on_mousewheel)   
        self.bind_all("<Button-5>", _on_mousewheel)


        self.adv_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        self.scrollable_frame.columnconfigure(1, weight=1) # Configure column weight

        # --- Content ---
        current_row = 0

        # Blacklists Frame
        blacklist_frame = ttk.LabelFrame(self.scrollable_frame, text=self.texts['advanced_labels']['blacklist_frame'], padding=(10, 5))
        blacklist_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.EW); blacklist_frame.columnconfigure(1, weight=1); current_row += 1
        ttk.Label(blacklist_frame, text=self.texts['blacklist_fields']['company']).grid(row=0, column=0, sticky=tk.NW, padx=5, pady=3); self.company_bl_widget = scrolledtext.ScrolledText(blacklist_frame, wrap=tk.WORD, height=3, width=50); self.company_bl_widget.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=3); self.company_bl_widget.insert(tk.END, self.vars['companyBlacklist'].get())
        ttk.Label(blacklist_frame, text=self.texts['blacklist_fields']['title']).grid(row=1, column=0, sticky=tk.NW, padx=5, pady=3); self.title_bl_widget = scrolledtext.ScrolledText(blacklist_frame, wrap=tk.WORD, height=3, width=50); self.title_bl_widget.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=3); self.title_bl_widget.insert(tk.END, self.vars['titleBlacklist'].get())
        ttk.Label(blacklist_frame, text=self.texts['blacklist_fields']['poster']).grid(row=2, column=0, sticky=tk.NW, padx=5, pady=3); self.poster_bl_widget = scrolledtext.ScrolledText(blacklist_frame, wrap=tk.WORD, height=3, width=50); self.poster_bl_widget.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=3); self.poster_bl_widget.insert(tk.END, self.vars['posterBlacklist'].get())

        # --- Languages Frame (Listbox + Buttons) ---
        lang_frame = ttk.LabelFrame(self.scrollable_frame, text=self.texts['advanced_labels']['language_frame'], padding=(10, 5))
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
        ttk.Button(lang_button_frame, text=self.texts['common']['add'], command=self._add_language_dialog, width=12).pack(pady=2, fill=tk.X)
        ttk.Button(lang_button_frame, text=self.texts['common']['modify'], command=self._modify_language_dialog, width=12).pack(pady=2, fill=tk.X)
        ttk.Button(lang_button_frame, text=self.texts['common']['remove'], command=self._remove_language, width=12).pack(pady=2, fill=tk.X)
        ttk.Button(lang_button_frame, text=self.texts['advanced_tab']['batch_add'], command=self._batch_add_languages, width=12).pack(pady=2, fill=tk.X)
        ttk.Button(lang_button_frame, text=self.texts['advanced_tab']['batch_delete'], command=self._batch_remove_languages, width=12).pack(pady=2, fill=tk.X)

        # --- Experience Frame (Listbox + Buttons) ---
        exp_frame = ttk.LabelFrame(self.scrollable_frame, text=self.texts['advanced_labels']['experience_frame'], padding=(10, 5))
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
        ttk.Button(exp_button_frame, text=self.texts['common']['add'], command=self._add_experience_dialog, width=12).pack(pady=2, fill=tk.X)
        ttk.Button(exp_button_frame, text=self.texts['common']['modify'], command=self._modify_experience_dialog, width=12).pack(pady=2, fill=tk.X)
        ttk.Button(exp_button_frame, text=self.texts['common']['remove'], command=self._remove_experience, width=12).pack(pady=2, fill=tk.X)
        ttk.Button(exp_button_frame, text=self.texts['advanced_tab']['batch_add'], command=self._batch_add_experiences, width=12).pack(pady=2, fill=tk.X)
        ttk.Button(exp_button_frame, text=self.texts['advanced_tab']['batch_delete'], command=self._batch_remove_experiences, width=12).pack(pady=2, fill=tk.X)

        # --- 自定义问答 Frame ---
        customq_frame = ttk.LabelFrame(self.scrollable_frame, text=self.texts['advanced_labels']['custom_qa_frame'], padding=(10, 5))
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
        ttk.Button(customq_button_frame, text=self.texts['advanced_tab']['add_qa'], command=self._add_customquestion_dialog, width=12).pack(pady=2, fill=tk.X)
        ttk.Button(customq_button_frame, text=self.texts['advanced_tab']['modify_qa'], command=self._modify_customquestion_dialog, width=12).pack(pady=2, fill=tk.X)
        ttk.Button(customq_button_frame, text=self.texts['advanced_tab']['remove_qa'], command=self._remove_customquestion, width=12).pack(pady=2, fill=tk.X)
        ttk.Button(customq_button_frame, text=self.texts['advanced_tab']['batch_add_qa'], command=self._batch_add_customquestions, width=12).pack(pady=2, fill=tk.X)
        ttk.Button(customq_button_frame, text=self.texts['advanced_tab']['batch_delete_qa'], command=self._batch_remove_customquestions, width=12).pack(pady=2, fill=tk.X)

        # --- Degree Completed Frame (Checkboxes) --- (已移动到经历管理标签页)
        # degree_frame = ttk.LabelFrame(self.scrollable_frame, text=self.texts['advanced_labels']['degree_frame'], padding=(10, 5))
        # degree_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.EW); current_row += 1
        # row, col = 0, 0
        # for degree in STANDARD_DEGREES:
        #     var = self.vars['degreeCompleted'][degree]
        #     ttk.Checkbutton(degree_frame, text=degree, variable=var).grid(row=row, column=col, sticky=tk.W, padx=5, pady=1)
        #     col += 1; # Adjust layout - maybe 2 columns?
        #     if col >= 2: col = 0; row += 1


        # --- Other Settings Frame (GPA, Salary, etc.) ---
        other_settings_frame = ttk.LabelFrame(self.scrollable_frame, text=self.texts['advanced_labels']['other_settings_frame'], padding=(10, 5))
        other_settings_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.EW); other_settings_frame.columnconfigure(1, weight=1); current_row += 1
        sub_row=0
        ttk.Label(other_settings_frame, text=self.texts['advanced_fields']['output_dir']).grid(row=sub_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(other_settings_frame, textvariable=self.vars['outputFileDirectory'], width=40).grid(row=sub_row, column=1, sticky=tk.EW, padx=5, pady=3); sub_row+=1
        # 以下设置已移动到经历管理标签页
        # ttk.Label(other_settings_frame, text=self.texts['advanced_fields']['university_gpa']).grid(row=sub_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(other_settings_frame, textvariable=self.vars['universityGpa'], width=15).grid(row=sub_row, column=1, sticky=tk.W, padx=5, pady=3); sub_row+=1
        # ttk.Label(other_settings_frame, text=self.texts['advanced_fields']['min_salary']).grid(row=sub_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(other_settings_frame, textvariable=self.vars['salaryMinimum'], width=15).grid(row=sub_row, column=1, sticky=tk.W, padx=5, pady=3); sub_row+=1
        # ttk.Label(other_settings_frame, text=self.texts['advanced_fields']['notice_period']).grid(row=sub_row, column=0, sticky=tk.W, padx=5, pady=3); ttk.Entry(other_settings_frame, textvariable=self.vars['noticePeriod'], width=15).grid(row=sub_row, column=1, sticky=tk.W, padx=5, pady=3); sub_row+=1
        bool_flag_frame = ttk.Frame(other_settings_frame); bool_flag_frame.grid(row=sub_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5); sub_row+=1
        
        # 创建带"自定义提示词"按钮的评估工作匹配度选项
        job_fit_frame = ttk.Frame(bool_flag_frame)
        job_fit_frame.pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(job_fit_frame, text=self.texts['advanced_fields']['evaluate_job_fit'], variable=self.vars['evaluateJobFit']).pack(side=tk.LEFT)
        ttk.Button(job_fit_frame, text=self.texts['advanced_fields']['customize_prompt'], command=self._customize_job_fit_prompt, width=20).pack(side=tk.LEFT, padx=5)
        
        # Debug Mode单独一行
        debug_frame = ttk.Frame(other_settings_frame)
        debug_frame.grid(row=sub_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        sub_row += 1
        ttk.Checkbutton(debug_frame, text=self.texts['advanced_fields']['debug_mode'], variable=self.vars['debug']).pack(side=tk.LEFT, padx=5)

        # 添加AI速度模式选择
        speed_frame = ttk.Frame(other_settings_frame)
        speed_frame.grid(row=sub_row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        sub_row += 1
        ttk.Label(speed_frame, text=self.texts['advanced_fields']['speed_mode']).pack(side=tk.LEFT, padx=5)

        # 创建单选按钮
        ttk.Radiobutton(speed_frame, text=self.texts['advanced_fields']['speed_slow'], 
                      variable=self.vars['speed_mode'], value='slow').pack(side=tk.LEFT, padx=(10, 20))
        ttk.Radiobutton(speed_frame, text=self.texts['advanced_fields']['speed_fast'], 
                      variable=self.vars['speed_mode'], value='fast').pack(side=tk.LEFT, padx=(0, 10))

        # Checkboxes Frame (Standard Y/N Questions)
        checkbox_frame = ttk.LabelFrame(self.scrollable_frame, text=self.texts['advanced_labels']['qa_default_frame'], padding=(10, 5))
        checkbox_frame.grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.EW); current_row += 1; row, col = 0, 0
        checkbox_labels = {'driversLicence': self.texts['advanced_tab']['drivers_licence'], 'requireVisa': self.texts['advanced_tab']['require_visa'], 'legallyAuthorized': self.texts['advanced_tab']['legally_authorized'], 'certifiedProfessional': self.texts['advanced_tab']['certified_professional'], 'urgentFill': self.texts['advanced_tab']['urgent_fill'], 'commute': self.texts['advanced_tab']['commute'], 'remote': self.texts['advanced_tab']['remote'], 'drugTest': self.texts['advanced_tab']['drug_test'], 'assessment': self.texts['advanced_tab']['assessment'], 'securityClearance': self.texts['advanced_tab']['security_clearance'], 'backgroundCheck': self.texts['advanced_tab']['background_check']}
        # Iterate based on DEFAULT_CONFIG to ensure all standard bool checkboxes are shown
        for key, default_value in DEFAULT_CONFIG.get('checkboxes', {}).items():
             if isinstance(default_value, bool): # Only handle boolean ones here
                 label = checkbox_labels.get(key, key); var = self.vars['checkboxes'].get(key) # Get var created in __init__
                 if var: # Check if var exists
                     ttk.Checkbutton(checkbox_frame, text=label, variable=var).grid(row=row, column=col, sticky=tk.W, padx=5, pady=1); col += 1
                     if col >= 3: col = 0; row += 1

        ttk.Label(self.scrollable_frame, text=self.texts['advanced_tab']['edit_yaml_note'], justify=tk.LEFT, foreground="grey").grid(row=current_row, column=0, columnspan=2, padx=10, pady=5, sticky=tk.W)

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
        dialog = tk.Toplevel(self); dialog.title(self.texts['dialogs']['add_lang_title'])
        dialog.transient(self); dialog.grab_set()
        ttk.Label(dialog, text=self.texts['dialogs']['lang_name']).pack(pady=(10, 2)); lang_entry = ttk.Entry(dialog, width=30); lang_entry.pack(pady=2, padx=20); lang_entry.focus_set()
        ttk.Label(dialog, text=self.texts['dialogs']['proficiency']).pack(pady=(10, 2)); level_var = tk.StringVar(value=LANGUAGE_LEVELS[1]); level_combo = ttk.Combobox(dialog, textvariable=level_var, values=LANGUAGE_LEVELS, state="readonly", width=28); level_combo.pack(pady=2, padx=20)
        def on_ok():
            lang_name = lang_entry.get().strip(); level = level_var.get()
            if not lang_name: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['input_error'].format(self.texts['dialogs']['lang_name']), parent=dialog); return
            if not level: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['input_error'].format(self.texts['dialogs']['proficiency']), parent=dialog); return
            if 'languages' not in self.config: self.config['languages'] = {}
            if lang_name in self.config['languages']:
                 if not messagebox.askyesno(self.texts['common']['confirm'], self.texts['messages']['item_exists'].format(self.texts['dialogs']['lang_name'], lang_name), parent=dialog): return
            self.config['languages'][lang_name] = level
            self._update_language_listbox(); dialog.destroy()
        button_frame = ttk.Frame(dialog); button_frame.pack(pady=15)
        ttk.Button(button_frame, text=self.texts['common']['ok'], command=on_ok, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        ttk.Button(button_frame, text=self.texts['common']['cancel'], command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _modify_language_dialog(self):
        selection = self.lang_listbox.curselection()
        if not selection: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['no_selection'].format(self.texts['common']['modify'], self.texts['dialogs']['lang_name'])); return
        selected_item = self.lang_listbox.get(selection[0])
        try: old_lang_name, old_level = map(str.strip, selected_item.split(':', 1))
        except ValueError: messagebox.showerror(self.texts['common']['error'], self.texts['messages']['parse_error'].format(self.texts['dialogs']['lang_name'])); return
        dialog = tk.Toplevel(self); dialog.title(self.texts['dialogs']['modify_lang_title'])
        dialog.transient(self); dialog.grab_set()
        ttk.Label(dialog, text=self.texts['dialogs']['lang_name']).pack(pady=(10, 2)); lang_entry = ttk.Entry(dialog, width=30); lang_entry.pack(pady=2, padx=20); lang_entry.insert(0, old_lang_name); lang_entry.focus_set()
        ttk.Label(dialog, text=self.texts['dialogs']['proficiency']).pack(pady=(10, 2)); level_var = tk.StringVar(value=old_level); level_combo = ttk.Combobox(dialog, textvariable=level_var, values=LANGUAGE_LEVELS, state="readonly", width=28); level_combo.pack(pady=2, padx=20)
        def on_ok():
            new_lang_name = lang_entry.get().strip(); new_level = level_var.get()
            if not new_lang_name: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['input_error'].format(self.texts['dialogs']['lang_name']), parent=dialog); return
            if not new_level: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['input_error'].format(self.texts['dialogs']['proficiency']), parent=dialog); return
            if 'languages' in self.config:
                 if old_lang_name != new_lang_name and old_lang_name in self.config['languages']: del self.config['languages'][old_lang_name]
                 self.config['languages'][new_lang_name] = new_level
            self._update_language_listbox(); dialog.destroy()
        button_frame = ttk.Frame(dialog); button_frame.pack(pady=15)
        ttk.Button(button_frame, text=self.texts['common']['ok'], command=on_ok, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        ttk.Button(button_frame, text=self.texts['common']['cancel'], command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _remove_language(self):
        selection = self.lang_listbox.curselection()
        if not selection: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['no_selection'].format(self.texts['common']['remove'], self.texts['dialogs']['lang_name'])); return
        selected_item = self.lang_listbox.get(selection[0])
        try:
            lang_name = selected_item.split(':', 1)[0].strip()
            if 'languages' in self.config and lang_name in self.config['languages']:
                if messagebox.askyesno(self.texts['common']['confirm'], f"{self.texts['messages']['confirm_delete'].format(1, self.texts['dialogs']['lang_name'])} ('{lang_name}')"):
                     del self.config['languages'][lang_name]
                     self._update_language_listbox()
            else: messagebox.showerror(self.texts['common']['error'], self.texts['messages']['item_not_found'].format(self.texts['dialogs']['lang_name'], lang_name))
        except Exception as e: messagebox.showerror(self.texts['common']['error'], f"{self.texts['common']['error']}: {e}")
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
        dialog = tk.Toplevel(self); dialog.title(self.texts['dialogs']['add_exp_title'])
        dialog.transient(self); dialog.grab_set()
        ttk.Label(dialog, text=f"{self.texts['dialogs']['skill_name']}:").pack(pady=(10, 2)); skill_entry = ttk.Entry(dialog, width=30); skill_entry.pack(pady=2, padx=20); skill_entry.focus_set()
        ttk.Label(dialog, text=f"{self.texts['dialogs']['years']}").pack(pady=(10, 2)); years_entry = ttk.Entry(dialog, width=10); years_entry.pack(pady=2, padx=20)
        def on_ok():
            skill_name = skill_entry.get().strip(); years_str = years_entry.get().strip()
            if not skill_name: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['input_error'].format(self.texts['dialogs']['skill_name']), parent=dialog); return
            if skill_name == 'default': messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['cannot_modify'], parent=dialog); return
            try: years = int(years_str)
            except ValueError: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['invalid_years'], parent=dialog); return
            if 'experience' not in self.config: self.config['experience'] = {'default': 0}
            self.config['experience'][skill_name] = years; self._update_experience_listbox(); dialog.destroy()
        button_frame = ttk.Frame(dialog); button_frame.pack(pady=15)
        ttk.Button(button_frame, text=self.texts['common']['ok'], command=on_ok, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        ttk.Button(button_frame, text=self.texts['common']['cancel'], command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _modify_experience_dialog(self):
        selection = self.exp_listbox.curselection()
        if not selection: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['no_selection'].format(self.texts['common']['modify'], self.texts['dialogs']['skill_name'])); return
        selected_item = self.exp_listbox.get(selection[0])
        try: old_skill_name, old_years_str = map(str.strip, selected_item.split(':', 1))
        except ValueError: messagebox.showerror(self.texts['common']['error'], self.texts['messages']['parse_error'].format(self.texts['dialogs']['skill_name'])); return
        is_default = (old_skill_name == 'default')
        dialog = tk.Toplevel(self); dialog.title(self.texts['dialogs']['modify_exp_title'])
        dialog.transient(self); dialog.grab_set()
        ttk.Label(dialog, text=f"{self.texts['dialogs']['skill_name']}:").pack(pady=(10, 2)); skill_entry = ttk.Entry(dialog, width=30); skill_entry.pack(pady=2, padx=20); skill_entry.insert(0, old_skill_name)
        if is_default: skill_entry.config(state='disabled')
        ttk.Label(dialog, text=f"{self.texts['dialogs']['years']}").pack(pady=(10, 2)); years_entry = ttk.Entry(dialog, width=10); years_entry.pack(pady=2, padx=20); years_entry.insert(0, old_years_str)
        if not is_default: skill_entry.focus_set()
        else: years_entry.focus_set()
        def on_ok():
            new_skill_name = skill_entry.get().strip(); new_years_str = years_entry.get().strip()
            if not new_skill_name: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['input_error'].format(self.texts['dialogs']['skill_name']), parent=dialog); return
            try: new_years = int(new_years_str)
            except ValueError: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['invalid_years'], parent=dialog); return
            if 'experience' in self.config:
                 if old_skill_name != new_skill_name and not is_default and old_skill_name in self.config['experience']:
                      if new_skill_name != 'default' and new_skill_name in self.config['experience']:
                          if not messagebox.askyesno(self.texts['common']['confirm'], self.texts['messages']['confirm_overwrite'].format(self.texts['dialogs']['skill_name'], new_skill_name), parent=dialog): return
                      del self.config['experience'][old_skill_name]
                 self.config['experience'][new_skill_name] = new_years
            self._update_experience_listbox(); dialog.destroy()
        button_frame = ttk.Frame(dialog); button_frame.pack(pady=15)
        ttk.Button(button_frame, text=self.texts['common']['ok'], command=on_ok, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        ttk.Button(button_frame, text=self.texts['common']['cancel'], command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _remove_experience(self):
        selection = self.exp_listbox.curselection()
        if not selection: messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['no_selection'].format(self.texts['common']['remove'], self.texts['dialogs']['skill_name'])); return
        selected_item = self.exp_listbox.get(selection[0])
        try: skill_name = selected_item.split(':', 1)[0].strip()
        except ValueError: messagebox.showerror(self.texts['common']['error'], self.texts['messages']['parse_error'].format(self.texts['dialogs']['skill_name'])); return

        if skill_name == 'default': messagebox.showerror(self.texts['common']['error'], self.texts['messages']['cannot_delete_default']); return

        if 'experience' in self.config and skill_name in self.config['experience']:
             if messagebox.askyesno(self.texts['common']['confirm'], self.texts['messages']['confirm_delete'].format(1, self.texts['dialogs']['skill_name'])):
                 del self.config['experience'][skill_name]
                 self._update_experience_listbox()
        else: messagebox.showerror(self.texts['common']['error'], self.texts['messages']['item_not_found'].format(self.texts['dialogs']['skill_name'], skill_name))


    # --- Control Tab Creation --- (No changes needed)
    def _create_control_tab(self):
        frame = ttk.Frame(self.control_tab, padding=(10, 5)); frame.pack(expand=True, fill="both", padx=10, pady=5)
        ttk.Label(frame, text=self.texts['control_tab']['operation_log']).pack(anchor=tk.W, padx=5)
        # 添加清除日志按钮
        clear_log_btn = ttk.Button(frame, text=self.texts['control_tab']['clear_log'], command=self._clear_log)
        clear_log_btn.pack(anchor=tk.E, padx=5, pady=(0, 3))
        self.output_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=15, state='disabled'); self.output_area.pack(expand=True, fill='both', padx=5, pady=5)
        button_frame = ttk.Frame(frame); button_frame.pack(fill=tk.X, pady=5)
        self.save_button = ttk.Button(button_frame, text=self.texts['control_tab']['save_config'], command=self._save_gui_config); self.save_button.pack(side=tk.LEFT, padx=5)
        self.start_button = ttk.Button(button_frame, text=self.texts['control_tab']['start_bot'], command=self._start_bot); self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(button_frame, text=self.texts['control_tab']['stop_bot'], command=self._stop_bot, state='disabled'); self.stop_button.pack(side=tk.LEFT, padx=5)
        edit_config_button = ttk.Button(button_frame, text=self.texts['control_tab']['edit_yaml'], command=self._open_config_file); edit_config_button.pack(side=tk.LEFT, padx=5)

    def _clear_log(self):
        self.output_area.config(state='normal')
        self.output_area.delete('1.0', tk.END)
        self.output_area.config(state='disabled')

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
                            if subprocess.call(['which', editor], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                                subprocess.Popen([editor, CONFIG_FILE])
                                opened = True
                                break
                        except FileNotFoundError:
                            continue
                    if not opened:
                        messagebox.showwarning(self.texts['common']['warning'], f"{self.texts['messages']['file_open_error']} {CONFIG_FILE}")
        except Exception as e: messagebox.showerror(self.texts['common']['error'], f"{self.texts['messages']['file_open_error']}: {e}")


    def _update_config_from_gui(self):
        """Update 'config' data structure from current GUI state"""
        try:
            # Basic Tab
            self.config['email'] = self.vars['email'].get(); self.config['password'] = self.vars['password'].get(); self.config['openaiApiKey'] = self.vars['openaiApiKey'].get()
            self.config['disableAntiLock'] = self.vars['disableAntiLock'].get(); self.config['uploads']['resume'] = self.vars['resume_path'].get(); self.config['textResume'] = self.vars['textResume_path'].get()
            self.config['uploads']['coverLetter'] = self.vars['coverletter_path'].get(); self.config['uploads']['photo'] = self.vars['photo_path'].get()
            
            # Job Tab - Update for new structure
            # positionsWithCount is already updated directly in self.config by dialogs
            # Ensure it exists, even if empty, for saving
            if 'positionsWithCount' not in self.config or not isinstance(self.config['positionsWithCount'], list):
                 self.config['positionsWithCount'] = []
            
            # Save global locations and other job search criteria
            self.config['locations'] = parse_list_from_textarea(self.locations_widget.get("1.0", tk.END))
            self.config['distance'] = self.vars['distance'].get()
            self.config['remote'] = self.vars['search_remote'].get()
            self.config['lessthanTenApplicants'] = self.vars['lessthanTenApplicants'].get()
            self.config['lessApplicantsEnabled'] = self.vars['lessApplicantsEnabled'].get()
            
            # 安全地转换申请者计数为整数，确保在1-100范围
            try:
                count_value = self.vars['lessApplicantsCount'].get()
                count_int = int(count_value) if count_value else 100
                # 确保在范围内
                if count_int < 1:
                    count_int = 1
                elif count_int > 100:
                    count_int = 100
                self.config['lessApplicantsCount'] = count_int
            except ValueError:
                # 转换失败时使用默认值100
                self.config['lessApplicantsCount'] = 100
                
            self.config['newestPostingsFirst'] = self.vars['newestPostingsFirst'].get()
            self.config['residentStatus'] = self.vars['residentStatus'].get()
            
            # Old 'positions' key can be removed or left (backend handles it)
            # If you want to explicitly remove it from config when new one is used:
            # if self.config.get('positionsWithCount') and 'positions' in self.config:
            #     del self.config['positions']

            # Preferences Tab - dynamically created checkboxes need manual update
            for level, var in self.vars['exp_level'].items(): self.config['experienceLevel'][level] = var.get()
            for jtype, var in self.vars['job_type'].items(): self.config['jobTypes'][jtype] = var.get()
            # 处理日期选项，包括自定义小时数
            date_pref = self.vars['date_pref'].get()
            # 先将所有日期选项设为False
            for date_key in self.config['date']: 
                self.config['date'][date_key] = False
                
            # 根据选择的选项设置对应值为True
            if date_pref == 'custom_hours':
                # 确保custom_hours键存在
                if 'custom_hours' not in self.config['date']:
                    self.config['date']['custom_hours'] = True
                else:
                    self.config['date']['custom_hours'] = True
                
                # 保存自定义小时数
                try:
                    hours_value = self.vars['custom_hours'].get()
                    hours_int = int(hours_value) if hours_value else 24
                    # 确保是正整数
                    if hours_int <= 0:
                        hours_int = 24
                    self.config['customHours'] = hours_int
                except ValueError:
                    self.config['customHours'] = 24
            else:
                # 设置选中的标准选项为True
                self.config['date'][date_pref] = True
            # Advanced Tab
            self.config['companyBlacklist'] = parse_list_from_textarea(self.company_bl_widget.get('1.0', tk.END))
            self.config['titleBlacklist'] = parse_list_from_textarea(self.title_bl_widget.get('1.0', tk.END))
            self.config['posterBlacklist'] = parse_list_from_textarea(self.poster_bl_widget.get('1.0', tk.END))
            self.config['outputFileDirectory'] = self.vars['outputFileDirectory'].get()
            self.config['universityGpa'] = self.vars['universityGpa'].get()
            self.config['salaryMinimum'] = self.vars['salaryMinimum'].get()
            self.config['noticePeriod'] = self.vars['noticePeriod'].get()
            self.config['evaluateJobFit'] = self.vars['evaluateJobFit'].get()
            self.config['debug'] = self.vars['debug'].get()
            self.config['speed_mode'] = self.vars['speed_mode'].get()
            
            # 确保自定义工作匹配度评估提示词被保存
            if 'jobFitPrompt' not in self.config:
                self.config['jobFitPrompt'] = self.texts['advanced_fields']['default_prompt']
                
            # Completed degrees (use checked boolean vars to create list format from config)
            self.config['checkboxes']['degreeCompleted'] = [
                degree for degree, var in self.vars['degreeCompleted'].items() if var.get()
            ]
            # Simple Yes/No checkbox questions (just update with bool)
            for chk_key, var in self.vars['checkboxes'].items():
                if isinstance(var, tk.BooleanVar):  # Skip over degreeCompleted in the checkboxes dict
                    self.config['checkboxes'][chk_key] = var.get()
            # We dont need to do anything with customQuestions as those are already managed via the dialog methods
            
            # 个人资料和EEO信息
            # 确保personalInfo和eeo字段存在
            if 'personalInfo' not in self.config:
                self.config['personalInfo'] = {}
            if 'eeo' not in self.config:
                self.config['eeo'] = {}
                
            # 更新个人信息
            for key in self.vars['personalInfo']:
                self.config['personalInfo'][key] = self.vars['personalInfo'][key].get()
                
            # 更新EEO信息
            for key in self.vars['eeo']:
                self.config['eeo'][key] = self.vars['eeo'][key].get()
                
            # 保存当前语言设置
            self.config['language'] = self.lang_code

            return True
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(self.texts['common']['error'], f"{self.texts['messages']['update_error']}:\n{str(e)}")
            return False


    # --- Other Methods (_save_gui_config, etc.) --- (No changes needed in these core logic methods)
    def _save_gui_config(self):
        try:
            # 先确保所有设置已从GUI更新到配置对象中
            if self._update_config_from_gui():
                if save_config(self.config):
                    self._log_message(self.texts['messages']['save_success'] + "\n")
                    return True
                else:
                    messagebox.showerror(self.texts['common']['error'], self.texts['messages']['save_error'])
                    return False
            else:
                return False
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror(self.texts['common']['error'], f"{self.texts['messages']['save_error']}: {e}")
            return False
    def _log_message(self, message):
        # 结尾不是\n结尾，则添加换行符
        if not message.endswith('\n'):
            message += '\n'
        def append_text():
            self.output_area.config(state='normal')
            self.output_area.insert(tk.END, message)
            self.output_area.see(tk.END)
            self.output_area.config(state='disabled')
        
        if threading.current_thread() is threading.main_thread():
            append_text()
        else:
            self.after(0, append_text)
    def _start_bot(self):
        if not self.config.get('email') or not self.config.get('password'):
            messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['missing_credentials'])
            return
        
        pdf_resume = self.config.get('uploads', {}).get('resume', '')
        text_resume_path = self.config.get('textResume', '')

        # 检查PDF简历是否存在，因为文本简历依赖它
        if not pdf_resume:
            messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['missing_pdf_resume_for_text'])
            return

        # 检查文本简历是否存在且有效
        if not text_resume_path or not os.path.exists(text_resume_path):
            messagebox.showwarning(
                self.texts['common']['warning'], 
                self.texts['messages'].get('missing_text_resume_hint', 
                    "Text resume is missing or invalid. Please select a PDF resume and click the \"AI Extract Text\" button (on the Basic Settings tab) to generate it first.")
            )
            return

        self.status_label.config(text=self.texts['messages']['starting_bot'])
        self._log_message(self.texts['messages']['bot_started'])
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.save_button.config(state='disabled')

        # 确保使用正确的Python解释器
        python_executable = sys.executable
        
        try:
            # 使用更简单的方式启动，不捕获输出，不使用CREATE_NO_WINDOW标志
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
            
            self._log_message(self.texts['messages']['bot_waiting'])
            
            # 使用线程读取输出
            self.output_thread = threading.Thread(
                target=self._read_bot_output,
                daemon=True
            )
            self.output_thread.start()
            
        except FileNotFoundError:
            self._log_message(self.texts['messages']['bot_error'])
            self._on_bot_finish(error=True)
        except Exception as e:
            self._log_message(f"{self.texts['messages']['bot_start_error']}: {e}\n")
            print(f"{self.texts['messages']['bot_start_error']}: {e}")  # 调试输出
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
            print(self.texts['messages']['pipe_closed'])
            self.after(0, self._log_message, f"\n{self.texts['messages']['bot_pipe_closed']}\n")
            self.after(100, self._check_bot_process)  # 仍然检查最终状态

        except Exception as e:
            # 捕获其他可能的读取错误
            print(f"读取输出错误: {e}")  # 调试输出
            self.after(0, self._log_message, f"\n{self.texts['messages']['bot_error_stopped']}: {e}\n")
            self.after(100, self._check_bot_process)  # 仍然检查最终状态
    
    def _check_bot_process(self):
        """检查机器人进程是否已结束并更新UI"""
        if hasattr(self, 'bot_process') and self.bot_process and self.bot_process.poll() is not None:
            returncode = self.bot_process.returncode
            self._on_bot_finish(returncode != 0)
    
    def _on_bot_finish(self, error=False):
        """处理机器人进程结束的情况"""
        if error:
            self.status_label.config(text=self.texts['messages']['bot_error_stopped'])
            self._log_message(self.texts['messages']['bot_error_stopped'])
        else:
            self.status_label.config(text=self.texts['messages']['bot_finished'])
            self._log_message(self.texts['messages']['bot_finished'])
            
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.save_button.config(state='normal')
        if hasattr(self, 'bot_process'):
            self.bot_process = None
    
    def _stop_bot(self):
        """停止运行中的机器人进程"""
        if hasattr(self, 'bot_process') and self.bot_process and self.bot_process.poll() is None:
            self.status_label.config(text=self.texts['messages']['bot_stopping'])
            try:
                self.bot_process.terminate()  # 尝试正常终止
                try:
                    self.bot_process.wait(timeout=2)  # 等待最多2秒
                except subprocess.TimeoutExpired:
                    self.bot_process.kill()  # 如果正常终止失败，强制关闭
                self._log_message(self.texts['messages']['bot_stopped'])
            except Exception as e:
                self._log_message(f"{self.texts['messages']['bot_stop_error']}: {e}")
            finally:
                self._on_bot_finish(error=True)
    
    def _create_language_selector(self):
        """创建语言选择器"""
        # 创建一个框架用于放置语言选择器
        lang_frame = ttk.Frame(self)
        lang_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 添加语言选择标签
        ttk.Label(lang_frame, text=self.texts['common']['language'] + ":").pack(side=tk.LEFT, padx=5)
        
        # 添加语言选择下拉菜单
        self.lang_var = tk.StringVar(value=self.lang_code)
        lang_menu = ttk.Combobox(lang_frame, textvariable=self.lang_var, state="readonly", width=15)
        lang_menu['values'] = [f"{code} - {name}" for code, name in AVAILABLE_LANGUAGES.items()]
        # 设置当前语言
        for i, (code, _) in enumerate(AVAILABLE_LANGUAGES.items()):
            if code == self.lang_code:
                lang_menu.current(i)
                break
        lang_menu.pack(side=tk.LEFT, padx=5)
        
        # 绑定语言切换事件
        lang_menu.bind("<<ComboboxSelected>>", self._on_language_changed)
        
    def _on_language_changed(self, event):
        """语言变更事件处理函数"""
        # 获取语言代码（格式: "zh_CN - 简体中文"）
        selected = self.lang_var.get().split(" - ")[0]
        
        if selected != self.lang_code:
            # 询问是否切换语言（需要重启应用）
            if messagebox.askyesno(
                self.texts['common']['confirm'], 
                self.texts['messages']['switch_language']
            ):
                # 保存当前配置
                self._update_config_from_gui()
                self.config['language'] = selected
                self._save_config(self.config)
                
                # 更新EEO下拉框的语言（在重启前）
                old_lang_code = self.lang_code
                self.lang_code = selected
                self._update_eeo_language()
                self.lang_code = old_lang_code
                
                # 重启应用
                python = sys.executable
                os.execl(python, python, *sys.argv)
            else:
                # 恢复之前的选择
                self.lang_var.set(f"{self.lang_code} - {AVAILABLE_LANGUAGES[self.lang_code]}")
                
            # 更新隐私声明
            if hasattr(self, 'privacy_label'):
                self.privacy_label.config(text=self.texts['common']['privacy_notice'] if 'common' in self.texts and 'privacy_notice' in self.texts['common'] else "We do not store your personal privacy information")
    
    def _update_eeo_language(self):
        """Update EEO dropdown options when language changes"""
        if not hasattr(self, 'eeo_combos'):
            return
            
        lang_key = 'zh' if self.lang_code.startswith('zh') else 'en'
        
        for field_key, combo_info in self.eeo_combos.items():
            combo = combo_info['combo']
            current_standard_value = combo_info['var'].get()
            
            # 获取新语言的显示选项
            new_display_options = self.EEO_OPTIONS.get(field_key, {}).get('display_text', {}).get(lang_key, ['Select an option'])
            standard_values = combo_info['standard_values']
            
            # 更新combo的选项
            combo['values'] = new_display_options
            combo_info['display_options'] = new_display_options
            
            # 根据当前标准值设置显示文本
            if current_standard_value and current_standard_value in standard_values:
                index = standard_values.index(current_standard_value)
                combo.set(new_display_options[index])
            else:
                combo.set(new_display_options[0])

    def _map_ai_value_to_standard_eeo(self, field_key, ai_value):
        """将AI提取的值映射到标准EEO选项"""
        # 获取该字段的标准值列表
        standard_values = self.EEO_OPTIONS.get(field_key, {}).get('standard_values', [])
        
        # 如果AI值为空或无效，返回默认的"不愿透露"选项（第一个选项）
        if not ai_value or not isinstance(ai_value, str) or not ai_value.strip():
            return standard_values[0] if standard_values else ''
        
        ai_value_lower = ai_value.lower().strip()
        
        # 性别映射
        if field_key == 'gender':
            if ai_value_lower in ['male', 'man', 'm', '男', '男性']:
                return 'Male'
            elif ai_value_lower in ['female', 'woman', 'f', '女', '女性']:
                return 'Female'
            elif ai_value_lower in ['prefer not to say', 'not specified', 'other', 'non-binary', 'prefer not to answer']:
                return 'I do not wish to identify'
        
        # 种族映射
        elif field_key == 'race':
            if any(keyword in ai_value_lower for keyword in ['american indian', 'alaska native', 'native american']):
                return 'American Indian or Alaska Native'
            elif any(keyword in ai_value_lower for keyword in ['white', 'caucasian']):
                return 'White'
            elif any(keyword in ai_value_lower for keyword in ['asian', 'chinese', 'japanese', 'korean']) and 'indian' not in ai_value_lower:
                return 'Asian'
            elif any(keyword in ai_value_lower for keyword in ['black', 'african american', 'african']):
                return 'Black or African American'
            elif any(keyword in ai_value_lower for keyword in ['hispanic', 'latino', 'latina']):
                return 'Hispanic or Latino'
            elif any(keyword in ai_value_lower for keyword in ['hawaiian', 'pacific islander']):
                return 'Native Hawaiian or Other Pacific Islander'
            elif any(keyword in ai_value_lower for keyword in ['two or more', 'multiple', 'mixed']):
                return 'Two or More Races'
            elif any(keyword in ai_value_lower for keyword in ['prefer not', 'not specified', 'decline']):
                return 'I do not wish to self identify'
        
        # 退伍军人映射
        elif field_key == 'veteran':
            if any(keyword in ai_value_lower for keyword in ['protected veteran', 'disabled veteran']) and 'not' not in ai_value_lower:
                return 'I am a protected veteran'
            elif 'veteran' in ai_value_lower and any(keyword in ai_value_lower for keyword in ['not protected', 'not a protected'])  and 'but' in ai_value_lower:
                return 'I am a veteran but not a protected veteran'
            elif 'not' in ai_value_lower and 'veteran' in ai_value_lower:
                return 'I am not a protected veteran'
            elif any(keyword in ai_value_lower for keyword in ['yes', 'true', 'veteran']) and 'not' not in ai_value_lower:
                return 'I am a veteran but not a protected veteran'  # 默认为非保护退伍军人
            elif any(keyword in ai_value_lower for keyword in ['prefer not', 'decline', 'not specified']):
                return 'I choose not to self-identify'
        
        # 残疾映射
        elif field_key == 'disability':
            if any(keyword in ai_value_lower for keyword in ['prefer not', 'decline', 'not specified']):
                return 'I choose not to self-identify'
            elif any(keyword in ai_value_lower for keyword in ['no', 'false', 'no disability']) or ai_value_lower.startswith('not have'):
                return 'No, I do not have a disability and have not had one in the past'
            elif any(keyword in ai_value_lower for keyword in ['yes', 'true', 'have', 'disability', 'disabled']):
                return 'Yes, I have a disability, or have had one in the past'
        
        # 尝试直接匹配标准值
        for standard_value in standard_values:
            if standard_value and ai_value.lower() == standard_value.lower():
                return standard_value
        
        # 如果没有找到匹配，返回默认的"不愿透露"选项（第一个选项）
        return standard_values[0] if standard_values else ''
    
    def _on_closing(self):
        """直接关闭GUI，不再需要检查进程状态"""
        self.destroy()

    # 添加批量操作相关的方法
    def _batch_add_languages(self):
        """批量添加语言能力"""
        dialog = tk.Toplevel(self)
        dialog.title(self.texts['dialogs']['batch_add_lang_title'])
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text=self.texts['dialogs']['batch_add_lang_format']).pack(pady=(10, 5), padx=10)
        ttk.Label(dialog, text=self.texts['dialogs']['batch_add_lang_example']).pack(pady=(0, 10), padx=10)
        
        # 文本区域用于输入多个语言
        text_area = scrolledtext.ScrolledText(dialog, width=40, height=10)
        text_area.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        # 添加一个下拉框，显示可用的熟练度级别
        level_frame = ttk.Frame(dialog)
        level_frame.pack(pady=5, padx=10, fill=tk.X)
        ttk.Label(level_frame, text=self.texts['dialogs']['available_proficiency']).pack(side=tk.LEFT)
        level_var = tk.StringVar()
        level_combo = ttk.Combobox(level_frame, textvariable=level_var, values=LANGUAGE_LEVELS, state="readonly", width=20)
        level_combo.pack(side=tk.LEFT, padx=(5, 0))
        level_combo.current(1)  # 默认选择第二个选项
        
        def insert_level():
            """将选中的熟练度插入到当前光标位置"""
            selected_level = level_var.get()
            if selected_level:
                text_area.insert(tk.INSERT, f": {selected_level}")
        
        ttk.Button(level_frame, text=self.texts['dialogs']['insert_proficiency'], command=insert_level).pack(side=tk.LEFT, padx=(5, 0))
        
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
                        if not messagebox.askyesno(self.texts['common']['warning'], 
                                                 f"language '{lang_name}' Proficiency '{level}' is not in the preset list. Do you want to continue and set it to '{LANGUAGE_LEVELS[1]}'?",
                                                 parent=dialog):
                            continue
                        level = LANGUAGE_LEVELS[1]
                    
                    if 'languages' not in self.config:
                        self.config['languages'] = {}
                    
                    # 检查是否已存在该语言
                    if lang_name in self.config['languages'] and not messagebox.askyesno(self.texts['common']['confirm'], 
                                                                                      self.texts['messages']['item_exists'].format(self.texts['dialogs']['lang_name'], lang_name), 
                                                                                      parent=dialog):
                        continue
                    
                    self.config['languages'][lang_name] = level
                    added_count += 1
                except Exception as e:
                    messagebox.showerror(self.texts['common']['error'], f"{self.texts['common']['error']} {self.texts['dialogs']['lang_name']} '{line}': {e}", parent=dialog)
            
            if added_count > 0:
                self._update_language_listbox()
                messagebox.showinfo(self.texts['common']['success'], self.texts['messages']['batch_add_success'].format(added_count, self.texts['dialogs']['lang_name']), parent=dialog)
                dialog.destroy()
            else:
                messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['no_valid_items'].format(self.texts['dialogs']['lang_name']), parent=dialog)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=15)
        ttk.Button(button_frame, text=self.texts['common']['ok'], command=on_ok, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        ttk.Button(button_frame, text=self.texts['common']['cancel'], command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        
        # 居中显示对话框
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def _batch_remove_languages(self):
        """批量删除选中的语言"""
        selection = self.lang_listbox.curselection()
        if not selection:
            messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['no_selection'].format(self.texts['common']['delete'], self.texts['dialogs']['lang_name']))
            return

        if not messagebox.askyesno(self.texts['common']['confirm'], self.texts['messages']['confirm_bulk_delete'].format(len(selection), self.texts['dialogs']['lang_name'])):
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
                messagebox.showerror(self.texts['common']['error'], f"{self.texts['common']['error']} {self.texts['dialogs']['lang_name']} '{item}': {e}")
        
        if removed_count > 0:
            self._update_language_listbox()
            messagebox.showinfo(self.texts['common']['success'], self.texts['messages']['delete_success'].format(removed_count, self.texts['dialogs']['lang_name']))
    
    def _batch_add_experiences(self):
        """批量添加经验"""
        dialog = tk.Toplevel(self)
        dialog.title(self.texts['dialogs']['batch_add_exp_title'])
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text=self.texts['dialogs']['batch_add_exp_format']).pack(pady=(10, 5), padx=10)
        ttk.Label(dialog, text=self.texts['dialogs']['batch_add_exp_example']).pack(pady=(0, 10), padx=10)
        
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
                        messagebox.showwarning(self.texts['common']['warning'], 
                                            self.texts['messages']['invalid_format'].format(f"{line} - {self.texts['dialogs']['batch_add_exp_format']}"), 
                                            parent=dialog)
                        continue
                    
                    if not skill_name:
                        continue
                    
                    # 验证年数
                    try:
                        years = int(years_str)
                    except ValueError:
                        if not messagebox.askyesno(self.texts['common']['warning'], 
                                                f"{self.texts['messages']['invalid_years']} {self.texts['dialogs']['skill_name']} '{skill_name}': '{years_str}'。是否设为0?",
                                                parent=dialog):
                            continue
                        years = 0
                    
                    if skill_name == 'default':
                        if not messagebox.askyesno(self.texts['common']['warning'], 
                                                self.texts['messages']['cannot_modify'], 
                                                parent=dialog):
                            continue
                    
                    if 'experience' not in self.config:
                        self.config['experience'] = {'default': 0}
                    
                    # 检查是否已存在该技能
                    if skill_name in self.config['experience'] and not messagebox.askyesno(self.texts['common']['confirm'], 
                                                                                       self.texts['messages']['item_exists'].format(self.texts['dialogs']['skill_name'], skill_name), 
                                                                                       parent=dialog):
                        continue
                    
                    self.config['experience'][skill_name] = years
                    added_count += 1
                except Exception as e:
                    messagebox.showerror(self.texts['common']['error'], f"{self.texts['common']['error']} {self.texts['dialogs']['skill_name']} '{line}': {e}", parent=dialog)
            
            if added_count > 0:
                self._update_experience_listbox()
                messagebox.showinfo(self.texts['common']['success'], self.texts['messages']['batch_add_success'].format(added_count, self.texts['dialogs']['skill_name']), parent=dialog)
                dialog.destroy()
            else:
                messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['no_valid_items'].format(self.texts['dialogs']['skill_name']), parent=dialog)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=15)
        ttk.Button(button_frame, text=self.texts['common']['ok'], command=on_ok, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        ttk.Button(button_frame, text=self.texts['common']['cancel'], command=dialog.destroy, width=8).pack(side=tk.LEFT, padx=10, ipady=2)
        
        # 居中显示对话框
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def _batch_remove_experiences(self):
        """批量删除选中的经验"""
        selection = self.exp_listbox.curselection()
        if not selection:
            messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['no_selection'].format(self.texts['common']['delete'], self.texts['dialogs']['skill_name']))
            return
        
        if not messagebox.askyesno(self.texts['common']['confirm'], self.texts['messages']['confirm_bulk_delete'].format(len(selection), self.texts['dialogs']['skill_name'])):
            return
        
        # 因为每次删除一项后索引会变化，所以先获取所有选中项
        selected_items = [self.exp_listbox.get(i) for i in selection]
        removed_count = 0
        
        for item in selected_items:
            try:
                skill_name = item.split(':', 1)[0].strip()
                
                # 不允许删除 default
                if skill_name == 'default':
                    messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['cannot_delete_default'])
                    continue
                
                if 'experience' in self.config and skill_name in self.config['experience']:
                    del self.config['experience'][skill_name]
                    removed_count += 1
            except Exception as e:
                messagebox.showerror(self.texts['common']['error'], f"{self.texts['common']['error']} {self.texts['dialogs']['skill_name']} '{item}': {e}")
        
        if removed_count > 0:
            self._update_experience_listbox()
            messagebox.showinfo(self.texts['common']['success'], self.texts['messages']['delete_success'].format(removed_count, self.texts['dialogs']['skill_name']))

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
        dialog.title(self.texts['dialogs']['add_question_title'])
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text=self.texts['dialogs']['question']).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        question_entry = ttk.Entry(dialog, width=40)
        question_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(dialog, text=self.texts['dialogs']['answer']).grid(row=1, column=0, padx=5, pady=5, sticky=tk.NW)
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
                messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['missing_parameters'], parent=dialog)
        
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text=self.texts['common']['save'], command=save_question, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=self.texts['common']['cancel'], command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        
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
            messagebox.showinfo(self.texts['common']['warning'], self.texts['messages']['no_selection'].format(self.texts['common']['modify'], self.texts['dialogs']['question']))
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
            messagebox.showerror(self.texts['common']['error'], self.texts['messages']['format_error'])
            return
        
        dialog = tk.Toplevel(self)
        dialog.title(self.texts['dialogs']['modify_question_title'])
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text=self.texts['dialogs']['question']).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        question_entry = ttk.Entry(dialog, width=40)
        question_entry.insert(0, question)
        question_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(dialog, text=self.texts['dialogs']['answer']).grid(row=1, column=0, padx=5, pady=5, sticky=tk.NW)
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
                messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['missing_parameters'], parent=dialog)

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text=self.texts['common']['save'], command=save_modification, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=self.texts['common']['cancel'], command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        
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
            messagebox.showinfo(self.texts['common']['warning'], self.texts['messages']['no_selection'].format(self.texts['common']['delete'], self.texts['dialogs']['question']))
            return
        
        selected_items = [self.customq_listbox.get(idx) for idx in selected]
        
        if messagebox.askyesno(self.texts['common']['confirm'], self.texts['messages']['confirm_bulk_delete'].format(len(selected_items), self.texts['dialogs']['question'])):
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
        dialog.title(self.texts['dialogs']['batch_add_qa_title'])
        dialog.geometry("500x400")  # 增加高度
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text=self.texts['dialogs']['batch_add_qa_format']).pack(pady=5)
        
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
                messagebox.showinfo(self.texts['common']['success'], self.texts['messages']['batch_add_success'].format(added_count, self.texts['dialogs']['question']), parent=dialog)
                self._update_customquestions_listbox()
                # 批量添加后保存配置
                self._save_gui_config()
                dialog.destroy()
            else:
                messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['no_valid_items'].format(self.texts['dialogs']['question']), parent=dialog)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text=self.texts['common']['save'], command=save_batch, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=self.texts['common']['cancel'], command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=self.texts['dialogs']['import_from_file'], command=lambda: self._import_qa_from_file(text_area), width=15).pack(side=tk.LEFT, padx=5)
        
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
            title=self.texts['dialogs']['select_file'],
            filetypes=(
                ("Text Files", "*.txt"),
                ("CSV Files", "*.csv"),
                ("All Files", "*.*")
            )
        )
        
        if not filepath:
                return

        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                text_area.delete("1.0", tk.END)
                text_area.insert("1.0", content)
                messagebox.showinfo(self.texts['common']['success'], self.texts['messages']['extract_success'].format(filepath, ""))
        except Exception as e:
            messagebox.showerror(self.texts['common']['error'], f"{self.texts['messages']['file_open_error'].format(str(e))}")

    def _batch_remove_customquestions(self):
        """批量删除自定义问答"""
        selected = self.customq_listbox.curselection()
        if not selected:
            messagebox.showinfo(self.texts['common']['warning'], self.texts['messages']['no_selection'].format(self.texts['common']['delete'], self.texts['dialogs']['question']))
            return
        
        selected_items = [self.customq_listbox.get(idx) for idx in selected]
        
        if messagebox.askyesno(self.texts['common']['confirm'], self.texts['messages']['confirm_bulk_delete'].format(len(selected_items), self.texts['dialogs']['question'])):
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
            messagebox.showinfo(self.texts['common']['success'], self.texts['messages']['delete_success'].format(removed_count, self.texts['dialogs']['question']))

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

    def _create_experience_tab(self):
        # --- 添加滚动条支持 ---
        self.experience_canvas = tk.Canvas(self.experience_tab)  # 保存Canvas引用为实例变量
        scrollbar = ttk.Scrollbar(self.experience_tab, orient="vertical", command=self.experience_canvas.yview)
        self.experience_frame = ttk.Frame(self.experience_canvas)  # 保存Frame引用为实例变量
        
        self.experience_frame.bind("<Configure>", lambda e: self.experience_canvas.configure(scrollregion=self.experience_canvas.bbox("all")))
        self.experience_canvas.create_window((0, 0), window=self.experience_frame, anchor="nw")
        self.experience_canvas.configure(yscrollcommand=scrollbar.set)
        
        # --- 滚轮事件绑定 ---
        def _on_mousewheel(event):
            # 平台特定的滚动计算
            if sys.platform == "win32":
                delta = -int(event.delta / 120)
            elif sys.platform == "darwin":  # macOS
                delta = -event.delta
            else:  # Linux
                if event.num == 4:
                    delta = -1
                elif event.num == 5:
                    delta = 1
                else:
                    delta = 0
            self.experience_canvas.yview_scroll(delta, "units")
            return "break"  # 阻止事件继续传播
        
        # 直接使用bind_all，因为我们在标签切换函数中会处理解绑
        self.experience_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.experience_canvas.bind_all("<Button-4>", _on_mousewheel)
        self.experience_canvas.bind_all("<Button-5>", _on_mousewheel)
        
        # 保存事件处理函数的引用，以便在标签切换时使用
        self._experience_mousewheel_func = _on_mousewheel
        
        self.experience_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # 设置主框架（现在放入experience_frame中）
        frame = ttk.Frame(self.experience_frame, padding=(10, 5))
        frame.pack(expand=True, fill="both", padx=10, pady=5)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        
        # --- Personal Info & EEO Frame (Dynamic Entries) ---
        personal_frame = ttk.LabelFrame(frame, text=self.texts['advanced_labels']['personal_info_frame'], padding=(10, 5))
        personal_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        personal_frame.columnconfigure(1, weight=1)
        personal_frame.columnconfigure(3, weight=1)
        sub_row = 0
        
        # Personal Info Fields (Dynamically created based on loaded config keys)
        ttk.Label(personal_frame, text=self.texts['advanced_labels']['personal_info_title'], font='-weight bold').grid(row=sub_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)
        sub_row += 1
        
        personal_keys = list(self.config.get('personalInfo', {}).keys()) # Iterate over keys present in loaded config
        for i, key in enumerate(personal_keys):
            col = (i % 2) * 2
            row_offset = i // 2
            
            # 为Phone Country Code字段添加特殊处理
            if key.lower() == 'phone country code':
                # 添加标签
                ttk.Label(personal_frame, text=f"{key.replace('_',' ').title()}:").grid(row=sub_row + row_offset, column=col, sticky=tk.W, padx=5, pady=2)
                
                # 确保变量存在
                if key not in self.vars['personalInfo']:
                    self.vars['personalInfo'][key] = tk.StringVar(value=self.config.get('personalInfo', {}).get(key, 'United States (+1)'))
                
                # 使用简单的两列布局，而不是嵌套框架
                # 创建只读输入框，直接放在grid布局中
                entry_code = ttk.Entry(personal_frame, textvariable=self.vars['personalInfo'][key], state="readonly", width=17)
                entry_code.grid(row=sub_row + row_offset, column=col+1, sticky=tk.W, padx=5, pady=2)
                
                # 直接创建选择按钮，放在输入框旁边
                btn_code = ttk.Button(personal_frame, text=self.texts['advanced_tab']['select_code'], width=5)
                btn_code.grid(row=sub_row + row_offset, column=col+1, sticky=tk.E, padx=5, pady=2)
                
                # 保存当前key避免闭包问题
                saved_key = key
                
                # 定义选择函数
                def open_code_dialog():
                    # 备份当前的全局滚轮事件绑定
                    widget_dict = {}
                    widget_dict['root'] = self
                    
                    # 存储所有要恢复的绑定
                    bindings_to_restore = []
                    
                    # 解除所有绑定
                    for widget_name, widget in widget_dict.items():
                        # 滚轮事件
                        for event in ["<MouseWheel>", "<Button-4>", "<Button-5>"]:
                            # 获取所有绑定
                            curr_binding = widget.bind(event)
                            if curr_binding:
                                bindings_to_restore.append((widget, event, curr_binding))
                                widget.unbind(event)
                            
                            # 获取所有全局绑定
                            curr_all_binding = widget.bind_all(event)
                            if curr_all_binding:
                                bindings_to_restore.append((widget, f"all:{event}", curr_all_binding))
                                widget.unbind_all(event)
                    
                    # 创建简单对话框
                    dialog = tk.Toplevel(self)
                    dialog.title("Select Country Code")
                    dialog.transient(self)
                    dialog.grab_set()  # 强制模态
                    dialog.focus_set()  # 强制获取焦点
                    dialog.resizable(False, False)
                    
                    # 在对话框关闭时恢复所有绑定
                    def on_dialog_close():
                        # 恢复所有绑定
                        for widget, event, binding in bindings_to_restore:
                            if event.startswith("all:"):
                                widget.bind_all(event[4:], binding)
                            else:
                                widget.bind(event, binding)
                        dialog.destroy()
                    
                    dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
                    
                    # 创建列表框
                    list_frame = ttk.Frame(dialog, padding=10)
                    list_frame.pack(fill=tk.BOTH, expand=True)
                    
                    # 搜索框
                    search_var = tk.StringVar()
                    ttk.Label(list_frame, text=self.texts['advanced_tab']['search_prompt']).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
                    search_entry = ttk.Entry(list_frame, textvariable=search_var, width=30)
                    search_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
                    search_entry.focus_set()
                    
                    # 创建滚动条和列表框
                    scrollbar = ttk.Scrollbar(list_frame)
                    scrollbar.grid(row=1, column=2, sticky='ns', padx=(0,5), pady=5)
                    
                    country_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, width=30, height=15)
                    country_listbox.grid(row=1, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)
                    scrollbar.config(command=country_listbox.yview)
                    
                    # 加载数据
                    for code in COUNTRY_CODES:
                        country_listbox.insert(tk.END, code)
                    
                    # 当前选中的值
                    current = self.vars['personalInfo'][saved_key].get()
                    for i, code in enumerate(COUNTRY_CODES):
                        if code == current:
                            country_listbox.selection_set(i)
                            country_listbox.see(i)
                            break
                    
                    # 搜索函数
                    def filter_codes(*args):
                        search_text = search_var.get().lower()
                        country_listbox.delete(0, tk.END)
                        for code in COUNTRY_CODES:
                            if search_text in code.lower():
                                country_listbox.insert(tk.END, code)
                    
                    search_var.trace("w", filter_codes)
                    
                    # 选择函数
                    def on_select():
                        selected = country_listbox.curselection()
                        if selected:
                            value = country_listbox.get(selected[0])
                            self.vars['personalInfo'][saved_key].set(value)
                            on_dialog_close()  # 使用自定义关闭函数
                    
                    # 双击选择
                    country_listbox.bind("<Double-1>", lambda e: on_select())
                    
                    # 按钮区域
                    btn_frame = ttk.Frame(dialog, padding=(10, 0, 10, 10))
                    btn_frame.pack(fill=tk.X)
                    
                    ttk.Button(btn_frame, text=self.texts['common']['ok'], command=on_select, width=10).pack(side=tk.LEFT, padx=5)
                    ttk.Button(btn_frame, text=self.texts['common']['cancel'], command=on_dialog_close, width=10).pack(side=tk.LEFT, padx=5)
                    
                    # 调整对话框位置
                    dialog.update_idletasks()
                    width = dialog.winfo_width()
                    height = dialog.winfo_height()
                    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
                    y = (dialog.winfo_screenheight() // 2) - (height // 2)
                    dialog.geometry(f"{width}x{height}+{x}+{y}")
                    
                    # 让对话框独立处理自己的滚轮事件，实现完全隔离
                    def handle_local_scroll(event, widget):
                        # 局部滚轮事件处理
                        if sys.platform == "win32":
                            delta = -int(event.delta / 120)
                        elif sys.platform == "darwin":  # macOS
                            delta = -event.delta
                        else:  # Linux
                            if event.num == 4:
                                delta = -1
                            elif event.num == 5:
                                delta = 1
                            else:
                                delta = 0
                        widget.yview_scroll(delta, "units")
                        return "break"  # 阻止事件传播
                    
                    # 为对话框中的列表框绑定专用滚轮处理
                    country_listbox.bind("<MouseWheel>", lambda e: handle_local_scroll(e, country_listbox))
                    country_listbox.bind("<Button-4>", lambda e: handle_local_scroll(e, country_listbox))
                    country_listbox.bind("<Button-5>", lambda e: handle_local_scroll(e, country_listbox))
                    
                    # 强制等待，直到对话框关闭
                    dialog.wait_window(dialog)
                
                # 设置按钮命令
                btn_code.config(command=open_code_dialog)
            else:
                ttk.Label(personal_frame, text=f"{key.replace('_',' ').title()}:").grid(row=sub_row + row_offset, column=col, sticky=tk.W, padx=5, pady=2)
                if key not in self.vars['personalInfo']:
                    self.vars['personalInfo'][key] = tk.StringVar(value=self.config.get('personalInfo', {}).get(key, ''))
                entry = ttk.Entry(personal_frame, textvariable=self.vars['personalInfo'][key], width=25)
                entry.grid(row=sub_row + row_offset, column=col + 1, sticky=tk.EW, padx=5, pady=2)
        
        sub_row += (len(personal_keys) + 1) // 2

        # EEO Fields (Standard dropdown selections)
        ttk.Label(personal_frame, text=self.texts['advanced_labels']['eeo_info_title'], font='-weight bold').grid(row=sub_row, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)
        sub_row += 1
        
        # 确保配置中有EEO字段
        if 'eeo' not in self.config:
            self.config['eeo'] = {}
            
        # 定义标准EEO字段
        standard_eeo_fields = ['gender', 'race', 'veteran', 'disability']
        
        # 添加不存在的EEO字段到配置中
        for field in standard_eeo_fields:
            if field not in self.config['eeo']:
                self.config['eeo'][field] = ''
        
        # 创建EEO下拉选择框
        self.eeo_combos = {}  # 存储combo引用以便后续更新
        for i, key in enumerate(standard_eeo_fields):
            col = (i % 2) * 2
            row_offset = i // 2
            
            # 获取字段显示名称
            field_name = self.texts.get('eeo_fields', {}).get(key, f"{key.replace('_',' ').title()}:")
            ttk.Label(personal_frame, text=field_name).grid(row=sub_row + row_offset, column=col, sticky=tk.W, padx=5, pady=2)
            
            # 创建下拉选择框
            if key not in self.vars['eeo']:
                self.vars['eeo'][key] = tk.StringVar(value=self.config.get('eeo', {}).get(key, ''))
            
            # 获取当前语言的显示文本
            lang_key = 'zh' if self.lang_code.startswith('zh') else 'en'
            display_options = self.EEO_OPTIONS.get(key, {}).get('display_text', {}).get(lang_key, ['Select an option'])
            standard_values = self.EEO_OPTIONS.get(key, {}).get('standard_values', [''])
            
            combo = ttk.Combobox(personal_frame, values=display_options, state='readonly', width=22)
            combo.grid(row=sub_row + row_offset, column=col + 1, sticky=tk.EW, padx=5, pady=2)
            
            # 存储combo引用
            self.eeo_combos[key] = {
                'combo': combo,
                'var': self.vars['eeo'][key],
                'standard_values': standard_values,
                'display_options': display_options
            }
            
            # 设置当前值的显示
            current_standard_value = self.config.get('eeo', {}).get(key, '')
            if current_standard_value and current_standard_value in standard_values:
                # 找到对应的显示文本
                index = standard_values.index(current_standard_value)
                combo.set(display_options[index])
            else:
                # 如果值为空或不在标准值中，设置为第一个选项（"不愿透露"）
                combo.set(display_options[0])
                # 同时更新配置和变量为默认值
                default_value = standard_values[0]
                self.config['eeo'][key] = default_value
                self.vars['eeo'][key].set(default_value)
            
            # 绑定选择事件来更新标准值
            def on_eeo_select(event, field_key=key):
                combo_widget = self.eeo_combos[field_key]['combo']
                display_text = combo_widget.get()
                display_list = self.eeo_combos[field_key]['display_options']
                standard_list = self.eeo_combos[field_key]['standard_values']
                
                if display_text in display_list:
                    index = display_list.index(display_text)
                    standard_value = standard_list[index]
                    self.eeo_combos[field_key]['var'].set(standard_value)
            
            combo.bind('<<ComboboxSelected>>', on_eeo_select)
        
        # 工作经历区
        work_frame = ttk.LabelFrame(frame, text=self.texts['experience_labels']['work_frame'], padding=(10, 5))
        work_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=5, pady=5)
        self.work_listbox = tk.Listbox(work_frame, height=10, width=38)
        self.work_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        work_btn_frame = ttk.Frame(work_frame)
        work_btn_frame.pack(side=tk.TOP, fill=tk.X, pady=3)
        ttk.Button(work_btn_frame, text=self.texts['buttons']['add_work'], command=self._add_work_dialog, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(work_btn_frame, text=self.texts['buttons']['edit_work'], command=self._edit_work_dialog, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(work_btn_frame, text=self.texts['buttons']['remove_work'], command=self._remove_work, width=15).pack(side=tk.LEFT, padx=5)
        self._update_work_listbox()
        
        # 学历经历区
        edu_frame = ttk.LabelFrame(frame, text=self.texts['experience_labels']['education_frame'], padding=(10, 5))
        edu_frame.grid(row=1, column=1, sticky=tk.NSEW, padx=5, pady=5)
        self.edu_listbox = tk.Listbox(edu_frame, height=10, width=38)
        self.edu_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        edu_btn_frame = ttk.Frame(edu_frame)
        edu_btn_frame.pack(side=tk.TOP, fill=tk.X, pady=3)
        ttk.Button(edu_btn_frame, text=self.texts['buttons']['add_edu'], command=self._add_edu_dialog, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(edu_btn_frame, text=self.texts['buttons']['edit_edu'], command=self._edit_edu_dialog, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(edu_btn_frame, text=self.texts['buttons']['remove_edu'], command=self._remove_edu, width=15).pack(side=tk.LEFT, padx=5)
        self._update_edu_listbox()
        
        # --- 已完成学位和其他设置 --- 
        settings_frame = ttk.Frame(frame)
        settings_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        settings_frame.columnconfigure(0, weight=1)
        settings_frame.columnconfigure(1, weight=1)
        
        # --- 已完成学位 Frame ---
        degree_frame = ttk.LabelFrame(settings_frame, text=self.texts['advanced_labels']['degree_frame'], padding=(10, 5))
        degree_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=5, pady=5)
        row, col = 0, 0
        for degree in STANDARD_DEGREES:
            var = self.vars['degreeCompleted'][degree]
            ttk.Checkbutton(degree_frame, text=degree, variable=var).grid(row=row, column=col, sticky=tk.W, padx=5, pady=1)
            col += 1
            if col >= 2: col = 0; row += 1
            
        # --- GPA、最低期望工资、通知周期等设置 ---
        other_settings_frame = ttk.LabelFrame(settings_frame, text=self.texts['advanced_labels']['other_settings_frame'], padding=(10, 5))
        other_settings_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=5, pady=5)
        other_settings_frame.columnconfigure(1, weight=1)
        
        sub_row = 0
        ttk.Label(other_settings_frame, text=self.texts['advanced_fields']['university_gpa']).grid(row=sub_row, column=0, sticky=tk.W, padx=5, pady=3)
        ttk.Entry(other_settings_frame, textvariable=self.vars['universityGpa'], width=15).grid(row=sub_row, column=1, sticky=tk.W, padx=5, pady=3)
        sub_row += 1
        
        ttk.Label(other_settings_frame, text=self.texts['advanced_fields']['min_salary']).grid(row=sub_row, column=0, sticky=tk.W, padx=5, pady=3)
        ttk.Entry(other_settings_frame, textvariable=self.vars['salaryMinimum'], width=15).grid(row=sub_row, column=1, sticky=tk.W, padx=5, pady=3)
        sub_row += 1
        
        ttk.Label(other_settings_frame, text=self.texts['advanced_fields']['notice_period']).grid(row=sub_row, column=0, sticky=tk.W, padx=5, pady=3)
        ttk.Entry(other_settings_frame, textvariable=self.vars['noticePeriod'], width=15).grid(row=sub_row, column=1, sticky=tk.W, padx=5, pady=3)
        sub_row += 1
        
        # 为经历管理标签页的列表框和子框架单独绑定滚轮事件
        def _configure_listbox_scrolling():
            def _on_listbox_mousewheel(event, listbox):
                # 平台特定的滚动计算
                if sys.platform == "win32":
                    delta = -int(event.delta / 120)
                elif sys.platform == "darwin":  # macOS
                    delta = -event.delta
                else:  # Linux
                    if event.num == 4:
                        delta = -1
                    elif event.num == 5:
                        delta = 1
                    else:
                        delta = 0
                listbox.yview_scroll(delta, "units")
                return "break"  # 阻止事件继续传播
            
            # 为工作列表框和学历列表框添加滚轮事件
            self.work_listbox.bind("<MouseWheel>", lambda e: _on_listbox_mousewheel(e, self.work_listbox))
            self.work_listbox.bind("<Button-4>", lambda e: _on_listbox_mousewheel(e, self.work_listbox))
            self.work_listbox.bind("<Button-5>", lambda e: _on_listbox_mousewheel(e, self.work_listbox))
            
            self.edu_listbox.bind("<MouseWheel>", lambda e: _on_listbox_mousewheel(e, self.edu_listbox))
            self.edu_listbox.bind("<Button-4>", lambda e: _on_listbox_mousewheel(e, self.edu_listbox))
            self.edu_listbox.bind("<Button-5>", lambda e: _on_listbox_mousewheel(e, self.edu_listbox))
        
        # 执行列表框滚动配置
        _configure_listbox_scrolling()

    def _update_work_listbox(self):
        self.work_listbox.delete(0, tk.END)
        works = self.config.get('workExperiences', [])
        for w in works:
            title = w.get('title', '')
            company = w.get('company', '')
            city = w.get('city', '')
            
            # 调整日期显示，考虑Month/Year占位符
            from_date = f"{w.get('from_month', 'Month')}/{w.get('from_year', 'Year')}"
            if w.get('current', False):
                period = f"{from_date} - 至今"
            else:
                to_date = f"{w.get('to_month', 'Month')}/{w.get('to_year', 'Year')}"
                period = f"{from_date} - {to_date}"
            
            self.work_listbox.insert(tk.END, f"{title} @ {company} ({city}) [{period}]")

    def _update_edu_listbox(self):
        self.edu_listbox.delete(0, tk.END)
        edus = self.config.get('educations', [])
        for e in edus:
            school = e.get('school', '')
            degree = e.get('degree', '')
            major = e.get('major', '')
            city = e.get('city', '')
            
            # 调整日期显示，考虑Month/Year占位符
            from_date = f"{e.get('from_month', 'Month')}/{e.get('from_year', 'Year')}"
            if e.get('current', False):
                period = f"{from_date} - 至今"
            else:
                to_date = f"{e.get('to_month', 'Month')}/{e.get('to_year', 'Year')}"
                period = f"{from_date} - {to_date}"
            
            self.edu_listbox.insert(tk.END, f"{school} {degree} {major} ({city}) [{period}]")

    def _add_work_dialog(self):
        self._work_dialog()
    def _edit_work_dialog(self):
        idx = self.work_listbox.curselection()
        if not idx: return
        self._work_dialog(idx[0])
    def _remove_work(self):
        idx = self.work_listbox.curselection()
        if not idx: return
        works = self.config.get('workExperiences', [])
        works.pop(idx[0])
        self.config['workExperiences'] = works
        self._update_work_listbox()
        
    def _work_dialog(self, edit_idx=None):
        works = self.config.get('workExperiences', [])
        data = works[edit_idx] if edit_idx is not None else {}
        dialog = tk.Toplevel(self)
        dialog.title(self.texts['experience_tab']['edit_work'] if edit_idx is not None else self.texts['experience_tab']['add_work'])
        
        # 获取当前年份
        current_year = datetime.datetime.now().year
        
        # 定义月份和年份选项
        months = ["Month", "January", "February", "March", "April", "May", "June", 
                 "July", "August", "September", "October", "November", "December"]
        # 开始年份范围：当前年份向前推100年
        from_years = ["Year"] + [str(y) for y in range(current_year, current_year-101, -1)]
        # 结束年份范围：当前年份向后推10年再加上向前推100年
        to_years = ["Year"] + [str(y) for y in range(current_year+10, current_year-101, -1)]
        
        # 普通文本字段
        text_fields = ['title', 'company', 'city', 'description']
        text_labels = [self.texts['experience_tab']['title'], self.texts['experience_tab']['company'], 
                      self.texts['experience_tab']['city'], self.texts['experience_tab']['description']]
        
        # 创建基础变量字典
        vars = {}
        
        # 添加文本字段
        for i, (f, l) in enumerate(zip(text_fields, text_labels)):
            ttk.Label(dialog, text=l+':').grid(row=i, column=0, sticky=tk.W, padx=5, pady=3)
            v = tk.StringVar(value=data.get(f, ''))
            vars[f] = v
            ttk.Entry(dialog, textvariable=v, width=40).grid(row=i, column=1, padx=5, pady=3)
        
        # 添加日期字段 - 起始日期
        row = len(text_fields)
        ttk.Label(dialog, text=self.texts["experience_tab"]["start_date"]).grid(row=row, column=0, sticky=tk.W, padx=5, pady=3)
        date_frame = ttk.Frame(dialog)
        date_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=3)
        
        # 起始月份下拉框
        from_month_var = tk.StringVar(value=data.get('from_month', 'Month'))
        vars['from_month'] = from_month_var
        ttk.Combobox(date_frame, textvariable=from_month_var, values=months, width=12, state="readonly").pack(side=tk.LEFT, padx=(0, 5))
        
        # 起始年份下拉框
        from_year_var = tk.StringVar(value=data.get('from_year', 'Year'))
        vars['from_year'] = from_year_var
        ttk.Combobox(date_frame, textvariable=from_year_var, values=from_years, width=8, state="readonly").pack(side=tk.LEFT)
        
        # 添加日期字段 - 结束日期
        row += 1
        ttk.Label(dialog, text=self.texts["experience_tab"]["end_date"]).grid(row=row, column=0, sticky=tk.W, padx=5, pady=3)
        to_date_frame = ttk.Frame(dialog)
        to_date_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=3)
        
        # 结束月份下拉框
        to_month_var = tk.StringVar(value=data.get('to_month', 'Month'))
        vars['to_month'] = to_month_var
        to_month_combo = ttk.Combobox(to_date_frame, textvariable=to_month_var, values=months, width=12, state="readonly")
        to_month_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        # 结束年份下拉框
        to_year_var = tk.StringVar(value=data.get('to_year', 'Year'))
        vars['to_year'] = to_year_var
        to_year_combo = ttk.Combobox(to_date_frame, textvariable=to_year_var, values=to_years, width=8, state="readonly")
        to_year_combo.pack(side=tk.LEFT)
        
        # 目前在职复选框
        row += 1
        current_var = tk.BooleanVar(value=data.get('current', False))
        
        def toggle_to_fields():
            state = "disabled" if current_var.get() else "readonly"
            to_month_combo.config(state=state)
            to_year_combo.config(state=state)
            if current_var.get():
                to_month_var.set("Month")
                to_year_var.set("Year")
        
        ttk.Checkbutton(dialog, text=self.texts['experience_tab']['current_position'], variable=current_var, command=toggle_to_fields).grid(row=row, column=0, sticky=tk.W, padx=5, pady=10)
        toggle_to_fields()  # 初始化状态
        
        def on_ok():
            entry = {f: vars[f].get() for f in text_fields}
            
            # 处理日期
            from_month = vars['from_month'].get()
            from_year = vars['from_year'].get()
            to_month = vars['to_month'].get()
            to_year = vars['to_year'].get()
            
            # 验证必填字段
            if entry['title'].strip() == "" or entry['company'].strip() == "":
                messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['required_fields'].format(self.texts['experience_tab']['required_work_fields']), parent=dialog)
                return
                
            # 验证日期选择
            if from_month == "Month" or from_year == "Year":
                messagebox.showwarning(self.texts['common']['warning'], self.texts['experience_tab']['select_start_date'], parent=dialog)
                return
                
            if not current_var.get() and (to_month == "Month" or to_year == "Year"):
                messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['select_end_date'].format(self.texts['experience_tab']['current_position']), parent=dialog)
                return
            
            # 设置值
            entry['from_month'] = from_month
            entry['from_year'] = from_year
            entry['to_month'] = "Month" if current_var.get() else to_month
            entry['to_year'] = "Year" if current_var.get() else to_year
            entry['current'] = current_var.get()
            
            # 保存结果
            if edit_idx is not None:
                works[edit_idx] = entry
            else:
                works.append(entry)
            self.config['workExperiences'] = works
            self._update_work_listbox()
            dialog.destroy()
            
        # 按钮
        ttk.Button(dialog, text=self.texts['common']['ok'], command=on_ok).grid(row=row+1, column=0, padx=5, pady=10)
        ttk.Button(dialog, text=self.texts['common']['cancel'], command=dialog.destroy).grid(row=row+1, column=1, padx=5, pady=10)

    def _add_edu_dialog(self):
        self._edu_dialog()
    def _edit_edu_dialog(self):
        idx = self.edu_listbox.curselection()
        if not idx: return
        self._edu_dialog(idx[0])
    def _remove_edu(self):
        idx = self.edu_listbox.curselection()
        if not idx: return
        edus = self.config.get('educations', [])
        edus.pop(idx[0])
        self.config['educations'] = edus
        self._update_edu_listbox()
        
    def _edu_dialog(self, edit_idx=None):
        edus = self.config.get('educations', [])
        data = edus[edit_idx] if edit_idx is not None else {}
        dialog = tk.Toplevel(self)
        dialog.title(self.texts['experience_tab']['edit_edu'] if edit_idx is not None else self.texts['experience_tab']['add_edu'])
        
        # 获取当前年份
        current_year = datetime.datetime.now().year
        
        # 定义月份和年份选项
        months = ["Month", "January", "February", "March", "April", "May", "June", 
                 "July", "August", "September", "October", "November", "December"]
        # 开始年份范围：当前年份向前推100年
        from_years = ["Year"] + [str(y) for y in range(current_year, current_year-101, -1)]
        # 结束年份范围：当前年份向后推10年再加上向前推100年
        to_years = ["Year"] + [str(y) for y in range(current_year+10, current_year-101, -1)]
        
        # 普通文本字段
        text_fields = ['school', 'city', 'degree', 'major']
        text_labels = [self.texts['experience_tab']['school'], self.texts['experience_tab']['city'], 
                      self.texts['experience_tab']['degree'], self.texts['experience_tab']['major']]
        
        # 创建基础变量字典
        vars = {}
        
        # 添加文本字段
        for i, (f, l) in enumerate(zip(text_fields, text_labels)):
            ttk.Label(dialog, text=l+':').grid(row=i, column=0, sticky=tk.W, padx=5, pady=3)
            v = tk.StringVar(value=data.get(f, ''))
            vars[f] = v
            ttk.Entry(dialog, textvariable=v, width=40).grid(row=i, column=1, padx=5, pady=3)
        
        # 添加日期字段 - 起始日期
        row = len(text_fields)
        ttk.Label(dialog, text=self.texts["experience_tab"]["start_date"]).grid(row=row, column=0, sticky=tk.W, padx=5, pady=3)
        date_frame = ttk.Frame(dialog)
        date_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=3)
        
        # 起始月份下拉框
        from_month_var = tk.StringVar(value=data.get('from_month', 'Month'))
        vars['from_month'] = from_month_var
        ttk.Combobox(date_frame, textvariable=from_month_var, values=months, width=12, state="readonly").pack(side=tk.LEFT, padx=(0, 5))
        
        # 起始年份下拉框
        from_year_var = tk.StringVar(value=data.get('from_year', 'Year'))
        vars['from_year'] = from_year_var
        ttk.Combobox(date_frame, textvariable=from_year_var, values=from_years, width=8, state="readonly").pack(side=tk.LEFT)
        
        # 添加日期字段 - 结束日期
        row += 1
        ttk.Label(dialog, text=self.texts["experience_tab"]["end_date"]).grid(row=row, column=0, sticky=tk.W, padx=5, pady=3)
        to_date_frame = ttk.Frame(dialog)
        to_date_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=3)
        
        # 结束月份下拉框
        to_month_var = tk.StringVar(value=data.get('to_month', 'Month'))
        vars['to_month'] = to_month_var
        to_month_combo = ttk.Combobox(to_date_frame, textvariable=to_month_var, values=months, width=12, state="readonly")
        to_month_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        # 结束年份下拉框
        to_year_var = tk.StringVar(value=data.get('to_year', 'Year'))
        vars['to_year'] = to_year_var
        to_year_combo = ttk.Combobox(to_date_frame, textvariable=to_year_var, values=to_years, width=8, state="readonly")
        to_year_combo.pack(side=tk.LEFT)
        
        # 目前就读复选框
        row += 1
        current_var = tk.BooleanVar(value=data.get('current', False))
        
        def toggle_to_fields():
            state = "disabled" if current_var.get() else "readonly"
            to_month_combo.config(state=state)
            to_year_combo.config(state=state)
            if current_var.get():
                to_month_var.set("Month")
                to_year_var.set("Year")
        
        ttk.Checkbutton(dialog, text=self.texts['experience_tab']['current_study'], variable=current_var, command=toggle_to_fields).grid(row=row, column=0, sticky=tk.W, padx=5, pady=10)
        toggle_to_fields()  # 初始化状态
        
        def on_ok():
            entry = {f: vars[f].get() for f in text_fields}
            
            # 处理日期
            from_month = vars['from_month'].get()
            from_year = vars['from_year'].get()
            to_month = vars['to_month'].get()
            to_year = vars['to_year'].get()
            
            # 验证必填字段
            if entry['school'].strip() == "" or entry['degree'].strip() == "":
                messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['required_fields'].format(self.texts['experience_tab']['required_edu_fields']), parent=dialog)
                return
                
            # 验证日期选择
            if from_month == "Month" or from_year == "Year":
                messagebox.showwarning(self.texts['common']['warning'], self.texts['experience_tab']['select_start_date'], parent=dialog)
                return
                
            if not current_var.get() and (to_month == "Month" or to_year == "Year"):
                messagebox.showwarning(self.texts['common']['warning'], self.texts['messages']['select_end_date'].format(self.texts['experience_tab']['current_study']), parent=dialog)
                return
            
            # 设置值
            entry['from_month'] = from_month
            entry['from_year'] = from_year
            entry['to_month'] = "Month" if current_var.get() else to_month
            entry['to_year'] = "Year" if current_var.get() else to_year
            entry['current'] = current_var.get()
            
            # 保存结果
            if edit_idx is not None:
                edus[edit_idx] = entry
            else:
                edus.append(entry)
            self.config['educations'] = edus
            self._update_edu_listbox()
            dialog.destroy()
            
        # 按钮
        ttk.Button(dialog, text=self.texts['common']['ok'], command=on_ok).grid(row=row+1, column=0, padx=5, pady=10)
        ttk.Button(dialog, text=self.texts['common']['cancel'], command=dialog.destroy).grid(row=row+1, column=1, padx=5, pady=10)

    def _create_ai_assistant_tab(self):
        """创建AI助手标签页 - 使用远程服务器API从文本简历中提取内容""" 
        main_frame = ttk.Frame(self.ai_assistant_tab, padding=(10, 5))
        main_frame.pack(expand=True, fill="both", padx=10, pady=5)
        
        # 标题和说明
        ttk.Label(main_frame, text=self.texts['ai_tab']['title'], font=("Helvetica", 12, "bold")).pack(pady=(0, 5))
        ttk.Label(main_frame, text=self.texts['ai_tab']['description']).pack(anchor=tk.W, pady=(0, 10))
        
        # 简历文件提示
        resume_frame = ttk.LabelFrame(main_frame, text=self.texts['ai_tab']['resume_file'], padding=(10, 5))
        resume_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(resume_frame, text=self.texts['ai_tab']['resume_file_description']).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.resume_status_label = ttk.Label(resume_frame, text=self.texts['ai_tab']['no_resume_file'])
        self.resume_status_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Button(resume_frame, text=self.texts['ai_tab']['check_file'], command=self._check_resume_file).grid(row=1, column=1, padx=5, pady=5)
        resume_frame.columnconfigure(0, weight=1)
        
        # 创建功能选择区域
        options_frame = ttk.LabelFrame(main_frame, text=self.texts['ai_tab']['select_content'], padding=(10, 5))
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 选项变量
        self.ai_options = {
            'languages': tk.BooleanVar(value=True),
            'skills': tk.BooleanVar(value=True),
            'personal_info': tk.BooleanVar(value=True),
            'eeo': tk.BooleanVar(value=True),
            'salary': tk.BooleanVar(value=False),
            'work_experience': tk.BooleanVar(value=True),
            'education': tk.BooleanVar(value=True),
        }
        
        # 选项复选框 - 使用Grid布局以保持一致性
        options_cols = 4  # 每行显示的选项数
        for i, (option_key, option_var) in enumerate(self.ai_options.items()):
            row, col = divmod(i, options_cols)
            
            # 根据选项键显示友好名称
            option_labels = {
                'languages': self.texts['ai_tab']['option_languages'],
                'skills': self.texts['ai_tab']['option_skills'],
                'personal_info': self.texts['ai_tab']['option_personal_info'],
                'eeo': self.texts['ai_tab']['option_eeo'],
                'salary': self.texts['ai_tab']['option_salary'],
                'work_experience': self.texts['ai_tab']['option_work_experience'],
                'education': self.texts['ai_tab']['option_education'],
            }
            
            ttk.Checkbutton(options_frame, text=option_labels.get(option_key, option_key), 
                          variable=option_var).grid(row=row, column=col, sticky=tk.W, padx=10, pady=3)
        
        # 对每列进行权重设置
        for i in range(options_cols):
            options_frame.columnconfigure(i, weight=1)
        
        # 进度和执行区域
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # 进度条
        self.ai_progress = ttk.Progressbar(action_frame, orient="horizontal", length=300, mode="determinate")
        self.ai_progress.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        # 运行按钮
        self.run_ai_btn = ttk.Button(action_frame, text=self.texts['ai_tab']['run_button'], command=self._run_ai_assistant, width=15)
        self.run_ai_btn.pack(side=tk.LEFT, padx=5)
        
        # 输出区域
        output_frame = ttk.LabelFrame(main_frame, text=self.texts['ai_tab']['output_log'], padding=(10, 5))
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.ai_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=10)
        self.ai_output.pack(fill=tk.BOTH, expand=True)
        self.ai_output.config(state=tk.DISABLED)
        
        # 初始化检查简历状态
        self.after(100, self._check_resume_file)
        
        # 设置默认提示文本 - 不再显示在界面上，但后端仍然需要
        self.ai_prompt = self.texts['ai_tab']['default_prompt']
    
    def _run_ai_assistant(self):
        """Run AI assistant to analyze resume"""
        # 更新按钮状态
        self.run_ai_btn.config(state=tk.DISABLED)
        
        # 重置输出区
        self.ai_output.config(state=tk.NORMAL)
        self.ai_output.delete('1.0', tk.END)
        self.ai_output.insert(tk.END, self.texts['ai_tab']['preparing'] + "\n")
        self.ai_output.config(state=tk.DISABLED)
        
        # 获取选项
        options = []
        if self.ai_options['languages'].get():
            options.append('languages')
        if self.ai_options['skills'].get():
            options.append('skills')
        if self.ai_options['personal_info'].get():
            options.append('personal_info')
        if self.ai_options['eeo'].get():
            options.append('eeo')
        if self.ai_options['salary'].get():
            options.append('salary')
        if self.ai_options['work_experience'].get():
            options.append('work_experience')
        if self.ai_options['education'].get():
            options.append('education')
        
        if not options:
            self._update_ai_log(self.texts['ai_tab']['error_no_options'])
            self.run_ai_btn.config(state=tk.NORMAL)
            return
        
        # 检查文件
        if not self._check_resume_file():
            self.run_ai_btn.config(state=tk.NORMAL)
            return
        
        # 获取服务器URL
        server_url = self.vars['aiServerUrl'].get()
        if not server_url:
            self._update_ai_log(self.texts['ai_tab']['error_no_server_url'])
            self.run_ai_btn.config(state=tk.NORMAL)
            return
        
        # 在线程中处理以避免UI冻结
        thread = threading.Thread(target=self._process_resume, args=(server_url, options))
        thread.daemon = True
        thread.start()
    
    def _process_resume(self, server_url, options):
        """Process resume analysis in a thread"""
        try:
            # 读取简历文件内容
            resume_path = self.vars['textResume_path'].get()
            with open(resume_path, 'r', encoding='utf-8') as file:
                resume_text = file.read()
            
            # 获取数据结构
            structure = self._get_data_structure(options)
            
            # 获取元数据
            metadata = self._get_metadata()
            
            # 准备请求参数
            payload = {
                'resumeText': resume_text,
                'options': options,
                'structure': structure,
                'metadata': metadata
            }
            
            self._update_ai_log(self.texts['ai_tab']['sending_request'])
            
            # 发送请求到服务器
            extract_url = f"{server_url}/extract-from-resume"
            # 读取本地auth.json，获取x-api-key和x-user-id
            import os, json
            headers = {'Content-Type': 'application/json'}
            auth_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth.json')
            if os.path.exists(auth_path):
                try:
                    with open(auth_path, 'r', encoding='utf-8') as f:
                        auth_data = json.load(f)
                        api_key = auth_data.get('apiKey')
                        user_id = auth_data.get('userId')
                        if api_key:
                            headers['x-api-key'] = api_key
                        if user_id:
                            headers['x-user-id'] = user_id
                except Exception as e:
                    print(f"读取auth.json失败: {e}")
            else:
                print("警告：未检测到auth.json，API请求可能会被拒绝。请先登录。")

            response = requests.post(
                extract_url,
                json=payload,
                headers=headers,
                timeout=120  # 增加超时时间为2分钟
            )
            
            # 处理响应
            if response.status_code == 200:
                ai_result = response.json()
                self._update_ai_log(self.texts['ai_tab']['received_results'])
                
                # 使用服务器返回的结果与客户端元数据进行增强
                enhanced_result = self._enhance_result(ai_result, metadata)
                
                # 显示结果摘要
                result_text = json.dumps(enhanced_result, indent=2, ensure_ascii=False)
                self._update_ai_log(self.texts['ai_tab']['analysis_complete'] + "\n\n" + result_text)
                
                # 将结果应用到界面配置中
                self._update_ai_log("\n" + self.texts['ai_tab']['updating_interface'])
                self._apply_ai_data(enhanced_result)
                self._update_ai_log(self.texts['ai_tab']['update_complete'])
            else:
                error_msg = f"{self.texts['ai_tab']['server_error']}: {response.status_code} - {response.text}"
                self._update_ai_log(error_msg)
        except requests.exceptions.Timeout:
            self._update_ai_log(self.texts['ai_tab']['request_timeout'])
        except requests.exceptions.RequestException as e:
            self._update_ai_log(f"{self.texts['ai_tab']['request_error']}: {str(e)}")
        except Exception as e:
            traceback_str = traceback.format_exc()
            self._update_ai_log(f"{self.texts['ai_tab']['processing_error']}: {str(e)}\n{traceback_str}")
        finally:
            # 恢复按钮状态
            self.after(0, lambda: self.run_ai_btn.config(state=tk.NORMAL))
    
    def _enhance_result(self, result, metadata):
        """使用元数据增强结果"""
        # 这个函数可以根据需要调整元数据中的值，或者进行额外处理
        return result
    
    def _apply_ai_data(self, ai_result):
        """将AI结果应用到界面配置中"""
        try:
            update_count = 0  # 记录成功更新的项目数
            self._update_ai_log(self.texts['ai_tab']['start_applying_results'])
            
            # 更新语言能力
            if 'languages' in ai_result and isinstance(ai_result['languages'], list) and ai_result['languages']:
                lang_count = 0
                # 清空当前语言设置
                if 'languages' in self.config:
                    self.config['languages'] = {}
                
                # 遍历AI识别的语言
                for lang_item in ai_result['languages']:
                    if lang_item and 'language' in lang_item and lang_item['language'] and 'level' in lang_item and lang_item['level']:
                        lang_name = lang_item['language'].strip()
                        lang_level = lang_item['level'].strip()
                        
                        # 确保language不为空
                        if not lang_name:
                            continue
                        
                        # 确保level在允许的值中
                        if lang_level not in LANGUAGE_LEVELS:
                            # 找到最接近的值
                            lang_level = LANGUAGE_LEVELS[1]  # 默认使用第二级别
                            
                        # 更新配置
                        self.config['languages'][lang_name] = lang_level
                        lang_count += 1
                
                # 更新界面
                self._update_language_listbox()
                if lang_count > 0:
                    self._update_ai_log(self.texts['ai_tab']['updated_languages'].format(lang_count))
                    update_count += 1
            
            # 更新技能经验
            if 'skills' in ai_result and isinstance(ai_result['skills'], list) and ai_result['skills']:
                skill_count = 0
                # 清除当前经验设置，但保留default
                default_exp = self.config.get('experience', {}).get('default', 0)
                self.config['experience'] = {'default': default_exp}
                
                # 遍历AI识别的技能
                for skill_item in ai_result['skills']:
                    if skill_item and 'skill' in skill_item and skill_item['skill'] and 'years' in skill_item:
                        skill_name = skill_item['skill'].strip()
                        years = skill_item['years']
                        
                        # 确保skill不为空
                        if not skill_name:
                            continue
                            
                        # 确保years是数字
                        try:
                            years = int(float(years))
                        except:
                            years = 0
                            
                        # 更新配置
                        self.config['experience'][skill_name] = years
                        skill_count += 1
                
                # 更新界面
                self._update_experience_listbox()
                if skill_count > 0:
                    self._update_ai_log(self.texts['ai_tab']['updated_skills'].format(skill_count))
                    update_count += 1
            
            # 更新个人信息 - 严格按照现有格式
            if 'personal_info' in ai_result and isinstance(ai_result['personal_info'], dict) and ai_result['personal_info']:
                pi_data = ai_result['personal_info']
                pi_count = 0
                
                # 确保个人信息字典存在
                if 'personalInfo' not in self.config:
                    self.config['personalInfo'] = {}
                
                # 获取现有字段列表进行匹配
                existing_pi_fields = list(self.config['personalInfo'].keys())
                field_mapping = {
                    # API返回格式 -> 配置文件中的实际字段名
                    'firstName': 'First Name',
                    'lastName': 'Last Name', 
                    'email': 'Email',
                    'phone': 'Mobile Phone Number',
                    'country_code': 'Phone Country Code',
                    'address1': 'Street address',
                    'address2': 'Address Line 2',
                    'city': 'City',
                    'state': 'State',
                    'zip': 'Zip',
                    'country': 'Country'
                }
                
                # 遍历个人信息字段并更新
                for api_key, value in pi_data.items():
                    if api_key == 'confidence':  # 跳过confidence字段
                        continue
                        
                    # 如果值为空，跳过更新
                    if not value:
                        continue
                    
                    # 尝试映射到配置中的字段名
                    config_key = field_mapping.get(api_key)
                    
                    # 如果没有映射，查找匹配的现有字段
                    if not config_key:
                        # 尝试使用API键本身
                        if api_key in existing_pi_fields:
                            config_key = api_key
                        # 尝试将API键转换为标题格式并查找匹配
                        elif api_key.title() in existing_pi_fields:
                            config_key = api_key.title()
                    
                    # 如果找到匹配的字段，更新配置和界面
                    if config_key and config_key in existing_pi_fields:
                        # 处理电话国家代码特殊情况
                        if config_key == 'Phone Country Code' and value:
                            # 处理国家代码(例如: US -> United States (+1))
                            best_match = None
                            if value in ["US", "USA", "United States"]:
                                # 查找美国代码
                                for code in COUNTRY_CODES:
                                    if "(+1)" in code and "United States" in code:
                                        best_match = code
                                        break
                            else:
                                # 尝试通过代码或国家名匹配
                                for code in COUNTRY_CODES:
                                    if value in code:
                                        best_match = code
                                        break
                            
                            # 如果找到匹配，使用它
                            if best_match:
                                value = best_match
                            else:
                                # 如果找不到匹配，跳过此更新
                                continue
                        
                        # 更新配置
                        self.config['personalInfo'][config_key] = value
                        
                        # 如果GUI中有对应的变量，更新它
                        if config_key in self.vars.get('personalInfo', {}):
                            self.vars['personalInfo'][config_key].set(value)
                            pi_count += 1
                
                if pi_count > 0:
                    self._update_ai_log(f"Updated {pi_count} personal information fields")
                    update_count += 1
            
            # 更新EEO信息 - 跳过空值
            if 'eeo' in ai_result and isinstance(ai_result['eeo'], dict) and ai_result['eeo']:
                eeo_data = ai_result['eeo']
                eeo_count = 0
                
                # 确保EEO字典存在
                if 'eeo' not in self.config:
                    self.config['eeo'] = {}
                
                # 获取现有字段列表进行匹配
                existing_eeo_fields = list(self.config['eeo'].keys())
                field_mapping = {
                    # API返回格式 -> 配置文件中的实际字段名
                    'gender': 'gender',
                    'race': 'race',
                    'veteran': 'veteran',
                    'disability': 'disability',
                    'veteran_status': 'veteran',
                    'disability_status': 'disability',
                }
                
                # 遍历EEO字段并更新
                for api_key, value in eeo_data.items():
                    if api_key == 'confidence':  # 跳过confidence字段
                        continue
                        
                    # 如果值为空，跳过更新
                    if not value:
                        continue
                    
                    # 尝试映射到配置中的字段名
                    config_key = field_mapping.get(api_key)
                    
                    # 如果没有映射，查找匹配的现有字段
                    if not config_key:
                        # 尝试使用API键本身
                        if api_key in existing_eeo_fields:
                            config_key = api_key
                        # 尝试将API键转换为标题格式并查找匹配
                        elif api_key.title() in existing_eeo_fields:
                            config_key = api_key.title()
                    
                    # 如果找到匹配的字段，且字段存在于配置中，更新配置和界面
                    if config_key and config_key in existing_eeo_fields:
                        # 映射AI提取的值到标准EEO选项
                        standard_value = self._map_ai_value_to_standard_eeo(config_key, value)
                        
                        if standard_value:
                        # 更新配置
                            self.config['eeo'][config_key] = standard_value
                        
                        # 如果GUI中有对应的变量，更新它
                        if config_key in self.vars.get('eeo', {}):
                            self.vars['eeo'][config_key].set(standard_value)

                            # 如果存在EEO下拉框，更新显示值
                            if hasattr(self, 'eeo_combos') and config_key in self.eeo_combos:
                                combo_info = self.eeo_combos[config_key]
                                standard_values = combo_info['standard_values']
                                if standard_value in standard_values:
                                    index = standard_values.index(standard_value)
                                    display_options = combo_info['display_options']
                                    combo_info['combo'].set(display_options[index])
                                
                            eeo_count += 1
                
                if eeo_count > 0:
                    self._update_ai_log(f"Updated {eeo_count} EEO information fields")
                    update_count += 1
            
            # 更新薪资信息
            if 'salary' in ai_result and isinstance(ai_result['salary'], dict) and ai_result['salary'].get('amount'):
                salary_data = ai_result['salary']
                
                if 'amount' in salary_data and salary_data['amount']:
                    try:
                        amount = int(float(salary_data['amount']))
                        self.config['salaryMinimum'] = amount
                        self.vars['salaryMinimum'].set(amount)
                        self._update_ai_log(f"Updated salary: {amount}")
                        update_count += 1
                    except:
                        pass
            
            # 更新工作经历
            if 'work_experience' in ai_result and isinstance(ai_result['work_experience'], list) and ai_result['work_experience']:
                work_count = 0
                work_entries = []
                
                # 遍历工作经历并添加到列表
                for work_item in ai_result['work_experience']:
                    # 检查必要字段是否存在且非空
                    if (work_item and 'company' in work_item and work_item['company'] and 
                            'title' in work_item and work_item['title']):
                        
                        # 创建工作经历对象
                        work_entry = {
                            'company': work_item.get('company', ''),
                            'title': work_item.get('title', ''),
                            'city': work_item.get('city', ''),
                            'state': work_item.get('state', ''),
                            'country': work_item.get('country', ''),
                            'from_month': work_item.get('from_month', 'Month'),
                            'from_year': work_item.get('from_year', 'Year'),
                            'to_month': work_item.get('to_month', 'Month'),
                            'to_year': work_item.get('to_year', 'Year'),
                            'current': work_item.get('current', False),
                            'description': work_item.get('description', '')
                        }
                        
                        # 处理城市为空的情况
                        if not work_entry['city']:
                            # 如果城市为空但国家或州有值，尝试使用州或国家值作为城市占位符
                            if work_entry['state']:
                                work_entry['city'] = work_entry['state']
                            elif work_entry['country']:
                                work_entry['city'] = work_entry['country']
                            else:
                                # 无法推断，添加占位符
                                work_entry['city'] = "[City unknown]"
                        
                        # 确保日期字段是正确的格式
                        # from_month如果是数字，转换为月份名称
                        if isinstance(work_entry['from_month'], (int, float)) or work_entry['from_month'].isdigit():
                            try:
                                month_idx = int(work_entry['from_month'])
                                if 1 <= month_idx <= 12:
                                    months = ["January", "February", "March", "April", "May", "June", 
                                             "July", "August", "September", "October", "November", "December"]
                                    work_entry['from_month'] = months[month_idx-1]
                            except:
                                pass
                        
                        # to_month如果是数字，转换为月份名称
                        if isinstance(work_entry['to_month'], (int, float)) or work_entry['to_month'].isdigit():
                            try:
                                month_idx = int(work_entry['to_month'])
                                if 1 <= month_idx <= 12:
                                    months = ["January", "February", "March", "April", "May", "June", 
                                             "July", "August", "September", "October", "November", "December"]
                                    work_entry['to_month'] = months[month_idx-1]
                            except:
                                pass
                        
                        work_entries.append(work_entry)
                        work_count += 1
                
                # 更新配置
                if work_count > 0:
                    self.config['workExperiences'] = work_entries
                    self._update_work_listbox()
                    self._update_ai_log(f"Updated {work_count} Work experience")
                    update_count += 1
            
            # 更新教育背景
            if 'education' in ai_result and isinstance(ai_result['education'], list) and ai_result['education']:
                edu_count = 0
                edu_entries = []
                
                # 遍历教育经历并添加到列表
                for edu_item in ai_result['education']:
                    # 检查必要字段是否存在且非空
                    if (edu_item and 'school' in edu_item and edu_item['school'] and 
                            'degree' in edu_item and edu_item['degree']):
                        
                        # 创建教育经历对象
                        edu_entry = {
                            'school': edu_item.get('school', ''),
                            'degree': edu_item.get('degree', ''),
                            'major': edu_item.get('major', ''),
                            'city': edu_item.get('city', ''),
                            'state': edu_item.get('state', ''),
                            'country': edu_item.get('country', ''),
                            'from_month': edu_item.get('from_month', 'Month'),
                            'from_year': edu_item.get('from_year', 'Year'),
                            'to_month': edu_item.get('to_month', 'Month'),
                            'to_year': edu_item.get('to_year', 'Year'),
                            'current': edu_item.get('current', False)
                        }
                        
                        # 处理城市为空的情况
                        if not edu_entry['city']:
                            # 如果城市为空但国家或州有值，尝试使用州或国家值作为城市占位符
                            if edu_entry['state']:
                                edu_entry['city'] = edu_entry['state']
                            elif edu_entry['country']:
                                edu_entry['city'] = edu_entry['country']
                            else:
                                # 无法推断，添加占位符
                                edu_entry['city'] = "[School location unknown]"
                        
                        # 确保日期字段是正确的格式
                        # from_month如果是数字，转换为月份名称
                        if isinstance(edu_entry['from_month'], (int, float)) or str(edu_entry['from_month']).isdigit():
                            try:
                                month_idx = int(edu_entry['from_month'])
                                if 1 <= month_idx <= 12:
                                    months = ["January", "February", "March", "April", "May", "June", 
                                             "July", "August", "September", "October", "November", "December"]
                                    edu_entry['from_month'] = months[month_idx-1]
                            except:
                                pass
                        
                        # to_month如果是数字，转换为月份名称
                        if isinstance(edu_entry['to_month'], (int, float)) or str(edu_entry['to_month']).isdigit():
                            try:
                                month_idx = int(edu_entry['to_month'])
                                if 1 <= month_idx <= 12:
                                    months = ["January", "February", "March", "April", "May", "June", 
                                             "July", "August", "September", "October", "November", "December"]
                                    edu_entry['to_month'] = months[month_idx-1]
                            except:
                                pass
                        
                        edu_entries.append(edu_entry)
                        edu_count += 1
                
                # 更新配置
                if edu_count > 0:
                    self.config['educations'] = edu_entries
                    self._update_edu_listbox()
                    self._update_ai_log(f"Updated {edu_count} Educational experience")
                    update_count += 1
                
                # 更新已完成学位复选框
                if edu_count > 0:
                    if 'checkboxes' not in self.config:
                        self.config['checkboxes'] = {}
                    
                    # 提取所有学位
                    degrees = []
                    for edu_item in ai_result['education']:
                        degree = edu_item.get('degree', '')
                        # 尝试找到匹配的标准学位
                        matched_degree = None
                        for std_degree in STANDARD_DEGREES:
                            if std_degree.lower() in degree.lower():
                                matched_degree = std_degree
                                break
                        
                        # 如果找到匹配的标准学位，添加到列表
                        if matched_degree and matched_degree not in degrees:
                            degrees.append(matched_degree)
                    
                    # 只有当找到至少一个标准学位时才更新
                    if degrees:
                        # 更新已完成学位配置
                        self.config['checkboxes']['degreeCompleted'] = degrees
                        
                        # 更新界面上的复选框
                        for degree, var in self.vars['degreeCompleted'].items():
                            var.set(degree in degrees)
                        
                        self._update_ai_log(f"Updated degree completion: {', '.join(degrees)}")
            
            # 保存配置
            if update_count > 0:
                # save_config(self.config)
                self._update_ai_log(f"Successfully updated {update_count} items of data. Please check and confirm and click the \"Save Configuration\" button in \"Operation and Status\" to save the changes.")
            else:
                self._update_ai_log("没有发现可用的数据可以更新")
            
        except Exception as e:
            self._update_ai_log(f"{self.texts['ai_tab']['apply_data_error']}: {str(e)}")
            traceback_str = traceback.format_exc()
            print(f"{self.texts['messages']['gui_update_error']}: {traceback_str}")  # 调试输出
    
    def _update_test_result(self, message):
        """更新测试结果到AI输出区域"""
        self.ai_output.config(state="normal")
        self.ai_output.insert(tk.END, message + "\n")
        self.ai_output.see(tk.END)
        self.ai_output.config(state="disabled")

    def _get_data_structure(self, options):
        """根据选项生成请求的数据结构"""
        structure = {}
        
        if 'languages' in options:
            structure['languages'] = [
                {"language": "", "level": "", "confidence": 0}
            ]
            
        if 'skills' in options:
            structure['skills'] = [
                {"skill": "", "years": 0, "confidence": 0}
            ]
            
        if 'personal_info' in options:
            structure['personal_info'] = {
                "firstName": "",
                "lastName": "",
                "email": "",
                "phone": "",
                "address1": "",
                "address2": "",
                "city": "",
                "state": "",
                "zip": "",
                "country": "",
                "country_code": "",
                "confidence": 0
            }
            
        if 'eeo' in options:
            structure['eeo'] = {
                "gender": "",
                "race": "",
                "veteran": "",
                "disability": "",
                "confidence": 0
            }
            
        if 'salary' in options:
            structure['salary'] = {
                "amount": 0,
                "currency": "",
                "period": "",  # annual, monthly, hourly
                "confidence": 0
            }
            
        if 'work_experience' in options:
            structure['work_experience'] = [
                {
                    "company": "",
                    "title": "",
                    "city": "",
                    "state": "",
                    "country": "", 
                    "from_month": 1,
                    "from_year": 2020,
                    "to_month": 1,
                    "to_year": 2023,
                    "current": False,
                    "description": "",
                    "confidence": 0
                }
            ]
            
        if 'education' in options:
            structure['education'] = [
                {
                    "school": "",
                    "degree": "",
                    "major": "",
                    "city": "",
                    "state": "",
                    "country": "",
                    "from_month": 1,
                    "from_year": 2015,
                    "to_month": 1,
                    "to_year": 2019,
                    "current": False,
                    "confidence": 0
                }
            ]
            
        return structure
        
    def _get_metadata(self):
        """获取所有元数据和选项数据，以便AI能够根据预设选项进行选择"""
        metadata = {}
        
        # 添加语言熟练度选项
        metadata['languages'] = {
            'label': self.texts['ai_tab']['metadata_languages'],
            'options': LANGUAGE_LEVELS
        }
        
        # 添加个人信息的预设选项
        metadata['personal_info'] = {
            'label': self.texts['ai_tab']['metadata_personal_info'],
            'fields': {
                'country_code': {
                    'label': self.texts['ai_tab']['metadata_country_code'],
                    'options': [code.split('(')[1].replace(')', '') if '(' in code else code 
                               for code in COUNTRY_CODES if code != self.texts['common']['select_option']]
                }
            }
        }
        
        # 添加学历选项
        metadata['education'] = {
            'label': self.texts['ai_tab']['metadata_education'],
            'fields': {
                'degree': {
                    'label': self.texts['ai_tab']['metadata_degree'],
                    'options': STANDARD_DEGREES
                },
                'month': {
                    'label': '月份',
                    'options': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'],
                    'month_names': ['January', 'February', 'March', 'April', 'May', 'June', 
                                   'July', 'August', 'September', 'October', 'November', 'December'],
                    'month_abbr': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                },
                'year': {
                    'label': '年份',
                    'options': [str(year) for year in range(datetime.datetime.now().year - 50, 
                                                           datetime.datetime.now().year + 5)]
                }
            }
        }
        
        # 添加工作经验的预设选项
        metadata['work_experience'] = {
            'label': self.texts['ai_tab']['metadata_work_experience'],
            'fields': {
                'month': {
                    'label': '月份',
                    'options': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'],
                    'month_names': ['January', 'February', 'March', 'April', 'May', 'June', 
                                   'July', 'August', 'September', 'October', 'November', 'December'],
                    'month_abbr': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                },
                'year': {
                    'label': '年份',
                    'options': [str(year) for year in range(datetime.datetime.now().year - 50, 
                                                           datetime.datetime.now().year + 5)]
                }
            }
        }
        
        # 添加技能经验年限的预设选项
        experience_years = []
        for i in range(11):  # 0-10年
            experience_years.append(str(i))
        for i in range(15, 51, 5):  # 15, 20, ..., 50年
            experience_years.append(str(i))
        
        metadata['skills'] = {
            'label': self.texts['ai_tab']['metadata_skills'],
            'options': experience_years,
            'skill_list': list(self.config.get('experience', {}).keys())
        }
        
        # 添加EEO(Equal Employment Opportunity)相关选项
        metadata['eeo'] = {
            'label': self.texts['ai_tab']['metadata_eeo'],
            'fields': {
                'gender': {
                    'label': self.texts['ai_tab']['metadata_gender'],
                    'options': ['Male', 'Female', 'Non-binary', 'Prefer not to disclose']
                },
                'race': {
                    'label': self.texts['ai_tab']['metadata_race'],
                    'options': ['American Indian', 'Alaska Native', 'Asian', 'Black/African American', 
                               'Hispanic/Latino', 'Native Hawaiian', 'Pacific Islander', 'White', 
                               'Two or More Races', 'Prefer not to disclose']
                },
                'veteran': {
                    'label': self.texts['ai_tab']['metadata_veteran_status'],
                    'options': ['Protected Veteran', 'Not a Protected Veteran', 'Prefer not to disclose']
                },
                'disability': {
                    'label': self.texts['ai_tab']['metadata_disability_status'],
                    'options': ['Yes', 'No', 'Prefer not to disclose']
                }
            }
        }
        
        # 添加薪资周期选项
        metadata['salary'] = {
            'label': self.texts['ai_tab']['metadata_salary'],
            'fields': {
                'period': {
                    'label': self.texts['ai_tab']['metadata_salary_period'],
                    'options': ['hourly', 'monthly', 'yearly']
                }
            }
        }
        
        # 从配置中添加其他可能的字段和选项
        # 例如，如果有其他在YAML中定义的固定选项列表，可以在这里添加
        
        return metadata

    def _check_resume_file(self):
        """检查文本简历文件是否存在并可读"""
        resume_path = self.vars['textResume_path'].get().strip()
        if not resume_path:
            self.resume_status_label.config(text=self.texts['ai_tab']['no_resume_file'], foreground="red")
            return False
        
        if not os.path.exists(resume_path):
            self.resume_status_label.config(text=f"{self.texts['ai_tab']['file_not_found']}: {resume_path}", foreground="red")
            return False
        
        try:
            with open(resume_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    self.resume_status_label.config(text=self.texts['ai_tab']['file_empty'], foreground="red")
                    return False
                size = len(content)
                self.resume_status_label.config(text=f"{self.texts['ai_tab']['file_ok']}: {os.path.basename(resume_path)} ({size} {self.texts['ai_tab']['characters']})", foreground="green")
                return True
        except Exception as e:
            self.resume_status_label.config(text=f"{self.texts['ai_tab']['file_read_error']}: {str(e)}", foreground="red")
            return False

    def _update_ai_log(self, message):
        """在AI助手日志区域更新信息"""
        # 确保在主线程中更新UI
        if threading.current_thread() is threading.main_thread():
            self.ai_output.config(state=tk.NORMAL)
            self.ai_output.insert(tk.END, message + "\n")
            self.ai_output.see(tk.END)
            self.ai_output.config(state=tk.DISABLED)
        else:
            # 如果在子线程中，使用after方法在主线程中调度
            self.after(0, lambda: self._update_ai_log(message))

    # 添加自定义工作匹配度评估提示词对话框
    def _customize_job_fit_prompt(self):
        dialog = tk.Toplevel(self)
        dialog.title(self.texts['advanced_fields']['prompt_dialog_title'])
        dialog.transient(self)
        dialog.grab_set()
        dialog.minsize(600, 400)
        
        # 确保config中有jobFitPrompt字段
        if 'jobFitPrompt' not in self.config:
            self.config['jobFitPrompt'] = self.texts['advanced_fields']['default_prompt']
            
        # 创建说明标签
        ttk.Label(dialog, text=self.texts['advanced_fields']['prompt_description'], wraplength=550, justify=tk.LEFT).pack(pady=(10, 5), padx=20, anchor=tk.W)
        
        # 创建文本框框架
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 创建带滚动条的文本框
        prompt_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, height=15)
        prompt_text.pack(fill=tk.BOTH, expand=True)
        prompt_text.insert(tk.END, self.config.get('jobFitPrompt', self.texts['advanced_fields']['default_prompt']))
        
        # 按钮框架
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=15, padx=20)
        
        # 重置为默认按钮
        def reset_to_default():
            prompt_text.delete(1.0, tk.END)
            prompt_text.insert(tk.END, self.texts['advanced_fields']['default_prompt'])
            
        ttk.Button(button_frame, text=self.texts['advanced_fields']['reset_to_default'], command=reset_to_default).pack(side=tk.LEFT, padx=5)
        
        # 确定按钮
        def on_ok():
            prompt_content = prompt_text.get(1.0, tk.END).strip()
            if prompt_content:
                self.config['jobFitPrompt'] = prompt_content
            dialog.destroy()
            
        ttk.Button(button_frame, text=self.texts['common']['ok'], command=on_ok, width=8).pack(side=tk.RIGHT, padx=5)
        
        # 取消按钮
        ttk.Button(button_frame, text=self.texts['common']['cancel'], command=dialog.destroy, width=8).pack(side=tk.RIGHT, padx=5)
        
        # 窗口居中
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.winfo_x() + (self.winfo_width() // 2) - (width // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _init_firebase_listener(self):
        """Initialize Firebase Listener"""
        try:
            # Read user ID from auth.json
            user_id = None
            try:
                with open('auth.json', 'r', encoding='utf-8') as f:
                    auth_data = json.load(f)
                    user_id = auth_data.get('userId')
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                self._log_message("❌ Unable to read auth.json or userId not found")
                return
            
            if not user_id:
                self._log_message("❌ No valid userId in auth.json")
                return
                
            # Initialize Firebase connection
            self.firebase_manager = firebase_manager.FirebaseManager(
                user_id=user_id,
                update_callback=self._on_firebase_config_update,
                initial_sync_done_callback=self._on_firebase_sync_done
            )
            
            # Start initial sync and listening
            self.firebase_manager.initial_sync_and_listen()
            self._log_message(f"🔥 Connecting to Firebase (User: {user_id[:8]}...)...")
            
        except Exception as e:
            self._log_message(f"❌ Firebase initialization failed: {str(e)}")

    def _on_firebase_config_update(self, firebase_config):
        """Firebase config update callback (called in a background thread)"""
        # Use the after method to execute UI updates in the main thread
        self.after(0, self._update_config_from_firebase, firebase_config)

    def _on_firebase_sync_done(self):
        """Firebase initial sync completion callback"""
        self.after(0, self._log_message, "✅ Firebase initial sync complete")

    def _update_config_from_firebase(self, firebase_config):
        """Update local config from Firebase"""
        try:
            # Update in-memory config
            self.config.update(firebase_config)
            
            # Save to local config.yaml
            save_config(firebase_config)
            
            self._log_message("🔄 Configuration updated from Firebase sync")
            
        except Exception as e:
            self._log_message(f"❌ Failed to update config: {str(e)}")

if __name__ == '__main__':
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if not in_venv and not os.environ.get("SKIP_VENV_CHECK"): print("Warning: It's recommended to run this application in a Python virtual environment...");
    app = EasyApplyApp(); app.mainloop()