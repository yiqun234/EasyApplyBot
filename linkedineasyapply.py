import time, random, csv, pyautogui, traceback, os, re, json, requests, logging
import sys
import io

# Force stdout to be UTF-8, to prevent `UnicodeEncodeError` on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

from urllib.parse import urlparse, parse_qs

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from datetime import date, datetime
from itertools import product

# 添加CloudAIResponseGenerator类
class CloudAIResponseGenerator:
    """基于AWS Lambda的AI响应生成器，将请求发送到AWS API Gateway处理"""
    
    def __init__(self, api_key=None, personal_info=None, experience=None, languages=None, resume_path=None, text_resume_path=None,customQuestions={}, debug=False, job_fit_prompt='', eeo=None):
        """
        初始化云端AI响应生成器
        
        参数与AIResponseGenerator保持一致，以确保无缝切换
        api_key参数将传递给云函数，如果提供的话
        """
        self.personal_info = personal_info
        self.experience = experience
        self.languages = languages
        self.pdf_resume_path = resume_path
        self.text_resume_path = text_resume_path
        self._resume_content = None
        self.debug = debug
        self.openai_api_key = api_key  # 保存用户提供的OpenAI API密钥
        self.job_fit_prompt = job_fit_prompt  # 添加自定义提示词参数
        self.eeo = eeo or {}  # 添加EEO信息参数

        self.customQuestions = customQuestions
        
        # API配置
        self.api_url = "https://api.nuomi.ai/api"
        self.api_key = None
        self.user_id = None
        
        # 优先从本地auth.json读取userId和apiKey
        self._load_auth_data()
        # 如果外部传入api_key参数，优先覆盖api_key
        
        import logging
        printger = logging.getLogger('CloudAIResponseGenerator')

    def _load_auth_data(self):
        """从本地auth.json读取userId和apiKey"""
        import os, json
        auth_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth.json')
        if os.path.exists(auth_path):
            try:
                with open(auth_path, 'r', encoding='utf-8') as f:
                    auth_data = json.load(f)
                    self.user_id = auth_data.get('userId')
                    if not self.api_key:
                        self.api_key = auth_data.get('apiKey')
            except Exception as e:
                print(f"读取auth.json失败: {e}")
                self.user_id = None
                if not self.api_key:
                    self.api_key = None
        else:
            self.user_id = None
            if not self.api_key:
                self.api_key = None

    def extract_text_via_aws(self, pdf_filename, base64_pdf_data):
        """
        使用OpenAI API通过AWS提取PDF文档中的文本内容

        Args:
            pdf_filename: PDF文件名，用于日志记录
            base64_pdf_data: Base64编码的PDF文件内容

        Returns:
            提取的文本内容，如果提取失败则返回None
        """
        try:
            # 准备发送到AWS API的数据
            request_data = {
                "pdf_filename": pdf_filename,
                "pdf_base64": base64_pdf_data,
                "openai_api_key": self.openai_api_key
            }

            # 打印基本信息
            print(f"正在使用AWS API提取PDF文件 '{pdf_filename}' 的文本内容...")

            # 调用云端API的extract-pdf-text端点
            response_data = self._call_cloud_api("extract-pdf-text", request_data)

            # 检查响应数据
            if not response_data:
                print(f"从AWS API获取响应失败")
                return None

            # 适配新的API响应格式
            if 'success' in response_data and not response_data.get('success'):
                print(f"PDF提取失败: {response_data.get('error', '未知错误')}")
                return None

            # 检查响应中是否包含提取的文本
            if "extracted_text" not in response_data:
                print(f"AWS API响应中不包含'extracted_text'字段")
                print(f"返回的数据: {response_data}")
                return None

            extracted_text = response_data["extracted_text"]

            # 记录成功提取
            print(f"成功从PDF文件中提取了 {len(extracted_text)} 字符")

            return extracted_text

        except Exception as e:
            print(f"PDF文本提取过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    @property
    def resume_content(self):
        if self._resume_content is None:
            # First try to read from text resume if available
            if self.text_resume_path:
                try:
                    with open(self.text_resume_path, 'r', encoding='utf-8') as f:
                        self._resume_content = f.read()
                        print("Successfully loaded text resume")
                        return self._resume_content
                except Exception as e:
                    print(f"Could not read text resume: {str(e)}")
        return self._resume_content

    def _build_context(self):
        # 格式化自定义问答字典
        custom_answers = "\n".join(f"- {q} => {a}" for q, a in self.customQuestions.items()) if self.customQuestions else ""
        custom_block = f"\nCustom Application Answers:\n{custom_answers}\n" if custom_answers else ""

        # 格式化EEO信息
        eeo_info = ""
        if hasattr(self, 'eeo') and self.eeo:
            eeo_items = []
            for key, value in self.eeo.items():
                if value:  # 只包含非空的EEO信息
                    eeo_items.append(f"- {key.title()}: {value}")
            if eeo_items:
                eeo_info = f"\nEqual Employment Opportunity (EEO) Information:\n{chr(10).join(eeo_items)}\n"

        return f"""
        Personal Information:
        - Name: {self.personal_info['First Name']} {self.personal_info['Last Name']}
        - Current Role: {self.experience.get('currentRole', '')}
        - Skills: {', '.join(self.experience.keys())}
        - Languages: {', '.join(f'{lang}: {level}' for lang, level in self.languages.items())}
        - Professional Summary: {self.personal_info.get('MessageToManager', '')}
        {eeo_info}{custom_block}
        Resume Content (Give the greatest weight to this information, if specified) (If you have similar questions to the Personal Information above, please refer to the following resume content):
        {self.resume_content}
        """

    def _call_cloud_api(self, endpoint, data):
        """调用云API处理AI请求"""
        try:
            import requests
            headers = {
                "Content-Type": "application/json"
            }
            # 必须加x-api-key和x-user-id
            if self.api_key:
                headers["x-api-key"] = self.api_key
            if self.user_id:
                headers["x-user-id"] = self.user_id
            else:
                print("警告：未检测到x-user-id，API请求可能会被拒绝。请先登录。")

            # 将用户的OpenAI API密钥添加到请求数据中(如果有)
            if self.openai_api_key:
                data["openai_api_key"] = self.openai_api_key

            # 构建完整的API URL
            full_url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"

            response = requests.post(
                full_url,
                headers=headers,
                json=data,
                timeout=60  # 设置超时时间为60秒
            )

            if response.status_code == 200:
                api_response = response.json()

                # 新的API响应格式处理
                if 'success' in api_response:
                    # 新的响应格式
                    if api_response.get('success') is False:
                        print(f"API请求失败: {api_response.get('error', '未知错误')}")
                        return None
                    return api_response
                elif api_response.get('statusCode') == 200:
                    # 旧的响应格式 - 保留兼容性
                    if 'body' in api_response and isinstance(api_response['body'], str):
                        try:
                            return json.loads(api_response['body'])
                        except:
                            print("无法解析响应中的body字段")
                            return None
                    else:
                        return api_response
                else:
                    print(f"API请求失败: {api_response.get('error', '未知错误')}")
                    return None
            else:
                print(f"API请求失败: HTTP {response.status_code}")
                print(f"错误详情: {response.text}")
                return None

        except requests.exceptions.Timeout:
            print("API请求超时")
            return None

        except requests.exceptions.RequestException as e:
            print(f"API请求异常: {str(e)}")
            return None

        except Exception as e:
            print(f"处理API请求时出错: {str(e)}")
            return None

    def generate_response(self, question_text, response_type="text", options=None, max_tokens=3000):
        """
        通过云端API生成回答

        Args:
            question_text: 应用中的问题
            response_type: "text", "numeric", 或 "choice"
            options: 对于"choice"类型，包含可能答案的(索引,文本)元组列表
            max_tokens: 回答的最大长度

        Returns:
            - 文本类型: 生成的文本回答或None
            - 数字类型: 整数值或None
            - 选择类型: 选择选项的整数索引或None
        """
        try:
            context = self._build_context()

            # 准备发送到云端API的数据
            request_data = {
                "context": context,
                "question": question_text,
                "response_type": response_type,
                "max_tokens": max_tokens,
                "debug": self.debug
            }

            if response_type == "choice" and options:
                request_data["options"] = options

            # 调用云端API
            response_data = self._call_cloud_api("generate-response", request_data)

            # 检查响应数据
            if not response_data:
                return None

            # 适配新的API响应格式
            if 'success' in response_data and not response_data.get('success'):
                print(f"API请求失败: {response_data.get('error', '未知错误')}")
                return None

            # 获取结果 - 兼容新旧格式
            if "result" not in response_data:
                print("API响应中没有'result'字段")
                return None

            answer = response_data["result"]
            print(f"AI response {response_type}: {answer}")

            if response_type == "numeric":
                # 如果返回的不是数字，尝试从回答中提取数字
                import re
                if not isinstance(answer, (int, float)):
                    numbers = re.findall(r'\d+', str(answer))
                    if numbers:
                        return int(numbers[0])
                    return 0
                return answer
            elif response_type == "choice":
                # 确保返回的索引在有效范围内
                if isinstance(answer, int) and options and 0 <= answer < len(options):
                    return answer
                return None

            return answer

        except Exception as e:
            print(f"生成回答时出错: {str(e)}")
            return None

    def evaluate_job_fit(self, job_title, job_description):
        """
        评估基于候选人经验和职位要求，这个职位是否值得申请

        Args:
            job_title: 职位标题
            job_description: 完整的职位描述文本

        Returns:
            bool: True表示应该申请，False表示应该跳过
        """
        try:
            context = self._build_context()

            # 准备发送到云端API的数据
            request_data = {
                "context": context,
                "job_title": job_title,
                "job_description": job_description,
                "debug": self.debug
            }

            # 添加自定义提示词
            if self.job_fit_prompt:
                request_data["system_prompt"] = self.job_fit_prompt

            # 调用云端API
            response_data = self._call_cloud_api("evaluate-job-fit", request_data)
            print(response_data)

            # 检查响应数据
            if not response_data:
                return True

            # 适配新的API响应格式
            if 'success' in response_data and not response_data.get('success'):
                print(f"API请求失败: {response_data.get('error', '未知错误')}")
                return True

            # 获取结果 - 兼容新旧格式
            if "result" not in response_data:
                print("API响应中没有'result'字段")
                return True

            # 提取决策结果和可能的解释
            decision = response_data["result"]
            explanation = response_data.get("explanation", "")

            if explanation and self.debug:
                print(f"AI Evaluation Explained: {explanation}")

            # 决策应该是布尔值，但也接受字符串"APPLY"/"SKIP"
            if isinstance(decision, bool):
                return decision
            elif isinstance(decision, str):
                return decision.upper().startswith('A')  # True代表APPLY，False代表SKIP

            return True  # 默认继续申请

        except Exception as e:
            print(f"评估职位匹配度时出错: {str(e)}")
            return True  # 出错时继续申请

class LinkedinEasyApply:
    def __init__(self, parameters, driver):
        self.browser = driver
        self.email = parameters['email']
        self.password = parameters['password']
        self.openai_api_key = parameters.get('openaiApiKey', '')  # Get API key with empty default
        self.disable_lock = parameters['disableAntiLock']
        self.company_blacklist = parameters.get('companyBlacklist', []) or []
        self.title_blacklist = parameters.get('titleBlacklist', []) or []
        self.poster_blacklist = parameters.get('posterBlacklist', []) or []

        # Duplicate application prevention configuration
        self.avoid_duplicate_applications = parameters.get('avoidDuplicateApplications', True)
        self.reapply_days = parameters.get('reapplyDays', 30)  # 多少天后可以重新投递
        self.applied_jobs_file = parameters.get('appliedJobsFile', 'applied_jobs.json')
        self.applied_jobs = {}  # Store applied job records with dates

        # Start from specific page configuration
        self.start_from_page = max(1, int(parameters.get('startFromPage', 1)))  # Minimum page 1

        # Email verification configuration
        self.verify_email = parameters.get('verifyEmail', True)  # Enable email verification by default

        # 少于X名申请者的筛选选项
        self.lessApplicantsEnabled = parameters.get('lessApplicantsEnabled', False)
        self.lessApplicantsCount = parameters.get('lessApplicantsCount', 100)

        # New: Configurations for positions with application counts
        self.positions_with_count = parameters.get('positionsWithCount', []) or []
        self.applied_counts = {} # Tracks the number of applications for each position name

        # Existing position and location configurations
        self.positions = parameters.get('positions', [])
        self.locations = parameters.get('locations', [])

        self.residency = parameters.get('residentStatus', [])
        self.base_search_url = self.get_base_search_url(parameters)
        self.seen_jobs = []
        self.file_name = "output"
        self.unprepared_questions_file_name = "unprepared_questions"
        self.output_file_directory = parameters['outputFileDirectory']
        self.resume_dir = parameters['uploads']['resume']
        self.text_resume = parameters.get('textResume', '')
        if 'coverLetter' in parameters['uploads']:
            self.cover_letter_dir = parameters['uploads']['coverLetter']
        else:
            self.cover_letter_dir = ''

        self.photo_dir = parameters['uploads']['photo']
        if 'photo' in parameters['uploads']:
            self.photo_dir = parameters['uploads']['photo']
        else:
            self.photo_dir = ''

        self.checkboxes = parameters.get('checkboxes', [])
        self.university_gpa = parameters['universityGpa']
        self.salary_minimum = parameters['salaryMinimum']
        self.notice_period = int(parameters['noticePeriod'])
        self.languages = parameters.get('languages', [])
        self.experience = parameters.get('experience', [])
        self.personal_info = parameters.get('personalInfo', [])
        self.eeo = parameters.get('eeo', [])
        self.experience_default = int(self.experience['default'])
        self.debug = parameters.get('debug', False)
        self.evaluate_job_fit = parameters.get('evaluateJobFit', False)
        self.customQuestions = parameters.get('customQuestions', {})
        self.jobFitPrompt = parameters.get('jobFitPrompt', '')  # 添加自定义提示词参数

        self.workExperiences = parameters.get('workExperiences', [])
        self.education = parameters.get('educations', [])

        self.speed_mode = parameters.get('speed_mode', 'slow') # slow/fast
        self.FastMode = True if self.speed_mode == 'fast' else False

        print("Using cloud AI services")
        self.ai_response_generator = CloudAIResponseGenerator(
            api_key=self.openai_api_key,  # 保持参数一致性
            personal_info=self.personal_info,
            experience=self.experience,
            languages=self.languages,
            resume_path=self.resume_dir,
            text_resume_path=self.text_resume,
            customQuestions=self.customQuestions,
            job_fit_prompt=self.jobFitPrompt,  # 传递自定义提示词
            eeo=self.eeo,  # 传递EEO信息
            debug=self.debug
        )

        # Load applied job records
        if self.avoid_duplicate_applications:
            self.load_applied_jobs()
            print(f"Duplicate application prevention enabled, currently tracking {len(self.applied_jobs)} applied jobs")
        else:
            print("Duplicate application prevention disabled")

        # Display start page configuration
        if self.start_from_page > 1:
            print(f"Configured to start from page {self.start_from_page}")
        else:
            print("Starting from page 1 (default)")

    def load_applied_jobs(self):
        """Load applied job records"""
        try:
            if os.path.exists(self.applied_jobs_file):
                with open(self.applied_jobs_file, 'r', encoding='utf-8') as f:
                    applied_data = json.load(f)
                
                # old to new
                if applied_data and isinstance(applied_data[0], str):
                    from datetime import datetime
                    current_time = datetime.now().isoformat()
                    self.applied_jobs = {url: current_time for url in applied_data}
                    self.save_applied_jobs()
                else:
                    self.applied_jobs = {item['url']: item['applied_date'] for item in applied_data}
                
                print(f"Successfully loaded {len(self.applied_jobs)} applied job records")
            else:
                print("Applied jobs record file not found, creating new record")
                self.applied_jobs = {}
        except Exception as e:
            print(f"Failed to load applied job records: {e}")
            self.applied_jobs = {}

    def save_applied_jobs(self):
        """Save applied job records"""
        try:
            # 转换为新格式：包含URL和日期的对象列表
            applied_list = [
                {"url": url, "applied_date": date} 
                for url, date in self.applied_jobs.items()
            ]
            with open(self.applied_jobs_file, 'w', encoding='utf-8') as f:
                json.dump(applied_list, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(self.applied_jobs)} applied job records")
        except Exception as e:
            print(f"Failed to save applied job records: {e}")

    def is_job_already_applied(self, job_link):
        """Check if job has already been applied to"""
        if not self.avoid_duplicate_applications:
            return False

        # Clean link, remove query parameters, keep only base link
        clean_link = job_link.split('?')[0] if job_link else ""
        
        if clean_link not in self.applied_jobs:
            return False
        
        try:
            from datetime import datetime, timedelta
            applied_date_str = self.applied_jobs[clean_link]
            applied_date = datetime.fromisoformat(applied_date_str.replace('Z', '+00:00'))
            current_date = datetime.now()
            
            days_passed = (current_date - applied_date).days
            if days_passed >= self.reapply_days:
                print(f"Job {clean_link} was applied {days_passed} days ago, allowing reapplication (threshold: {self.reapply_days} days)")
                return False
            else:
                print(f"Job {clean_link} was applied {days_passed} days ago, skipping (threshold: {self.reapply_days} days)")
                return True
        except Exception as e:
            print(f"Error checking application date for {clean_link}: {e}")
            return True

    def add_applied_job(self, job_link):
        """Add applied job to records"""
        if not self.avoid_duplicate_applications or not job_link:
            return

        # Clean link, remove query parameters, keep only base link
        clean_link = job_link.split('?')[0]
        from datetime import datetime
        current_time = datetime.now().isoformat()
        self.applied_jobs[clean_link] = current_time
        self.save_applied_jobs()

    def logout(self):
        """Logs out from the current LinkedIn session."""
        try:
            print("Attempting to log out...")

            # 1. Click the profile dropdown trigger
            # Using a stable attribute instead of the random 'id'
            profile_dropdown_trigger = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test-profile-dropdown-trigger]"))
            )
            profile_dropdown_trigger.click()
            print("Profile dropdown clicked.")
            time.sleep(random.uniform(1, 2))

            # 2. Find and click the "Sign Out" button
            # The footer contains multiple links. We need to be specific.
            # The logout link's href specifically contains '/uas/logout'.
            sign_out_button = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-test-profile-dropdown-footer-link][href*='/logout']"))
            )
            print("Found 'Sign Out' button using a more specific CSS selector.")
            sign_out_button.click()

            # 3. Wait for the logout to complete and redirect to a logged-out page
            WebDriverWait(self.browser, 15).until(
                EC.url_contains("linkedin.com/home")
            )
            print("Successfully logged out.")
            return True

        except Exception as e:
            print(f"An error occurred during logout: {e}")
            # If something fails, take a screenshot for debugging and print page source
            try:
                self.browser.save_screenshot("logout_error_screenshot.png")
                with open("logout_error_page_source.html", "w", encoding="utf-8") as f:
                    f.write(self.browser.page_source)
                print("Saved screenshot and page source for debugging logout error.")
            except:
                pass
            return False

    def verify_logged_in_email(self):
        """
        验证当前登录的邮箱是否与配置文件中的邮箱匹配

        Returns:
            bool: True if emails match or verification is skipped, False otherwise
        """
        if not self.verify_email:
            print("Email verification is disabled, skipping.")
            return True

        try:
            print("Verifying logged-in email address...")

            # Navigate to LinkedIn preferences page
            self.browser.get("https://www.linkedin.com/mypreferences/d/categories/sign-in-and-security")

            # Wait for the email sneak peek element to be present
            email_element = WebDriverWait(self.browser, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-category-item-sneakpeek]"))
            )

            logged_in_email = email_element.text.strip().lower()
            expected_email = self.email.lower()

            print(f"Current logged-in email: {logged_in_email}")
            print(f"Expected email from config: {expected_email}")

            if logged_in_email == expected_email:
                print("✓ Email verification successful - correct account is logged in.")
                return True
            else:
                print(f"✗ Email mismatch detected! Attempting to log out and log back in.")

                # Logout from the incorrect account
                if self.logout():
                    # If logout is successful, proceed to log in with the correct account
                    print("Proceeding to log in with the correct account...")
                    self.load_login_page_and_login()
                    # After successful login, re-verify the email to be sure
                    return self.verify_logged_in_email_after_relogin()
                else:
                    print("Logout failed. Cannot proceed with login. Please check the account manually.")
                    return False

        except Exception as e:
            print(f"Error during email verification: {e}")
            print("Warning: Email verification failed, continuing with current session as a fallback.")
            return True

    def verify_logged_in_email_after_relogin(self):
        """A simplified verification check after a re-login attempt."""
        try:
            print("Re-verifying email after login...")
            self.browser.get("https://www.linkedin.com/mypreferences/d/categories/sign-in-and-security")
            email_element = WebDriverWait(self.browser, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-category-item-sneakpeek]"))
            )
            logged_in_email = email_element.text.strip().lower()
            if logged_in_email == self.email.lower():
                print("✓ Email re-verification successful.")
                return True
            else:
                print("✗ Email mismatch persists even after re-login. Aborting.")
                return False
        except Exception as e:
            print(f"Error during email re-verification: {e}")
            return False

    def login(self):
        try:
            # Check if the "chrome_bot" directory exists
            print("Attempting to restore previous session...")
            if os.path.exists("chrome_bot"):
                self.browser.get("https://www.linkedin.com/feed/")
                time.sleep(random.uniform(1, 2))

                # Check if the current URL is the feed page
                if "linkedin.com/feed/" not in self.browser.current_url:
                    print("Feed page not loaded, proceeding to login.")
                    self.load_login_page_and_login()
                    # Verify email after fresh login if enabled
                    if self.verify_email:
                        self.verify_logged_in_email()
                else:
                    print("Session restored successfully.")
                    # Verify email for existing session if enabled
                    if self.verify_email:
                        print("Verifying email for existing session...")
                        if not self.verify_logged_in_email():
                            # If verification fails and results in a logout/login flow,
                            # the session is now corrected. We can proceed.
                            print("Email verification flow completed. Continuing application process.")
            else:
                print("No session found, proceeding to login.")
                self.load_login_page_and_login()
                # Verify email after fresh login if enabled
                if self.verify_email:
                    self.verify_logged_in_email()

        except TimeoutException:
            print("Timeout occurred, checking for security challenges...")
            self.security_check()
            # raise Exception("Could not login!")

    def security_check(self):
        current_url = self.browser.current_url
        page_source = self.browser.page_source

        if '/checkpoint/challenge/' in current_url or 'security check' in page_source or 'quick verification' in page_source:
            input("Please complete the security check and press enter on this console when it is done.")
            time.sleep(random.uniform(5.5, 10.5))

    def load_login_page_and_login(self):
        self.browser.get("https://www.linkedin.com/checkpoint/lg/sign-in-another-account")

        # Wait for the username field to be present
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        print("Login page loaded.")

        self.browser.find_element(By.ID, "username").send_keys(self.email)
        self.browser.find_element(By.ID, "password").send_keys(self.password)
        self.browser.find_element(By.CSS_SELECTOR, ".btn__primary--large").click()

        # Wait for the feed page to load after login
        WebDriverWait(self.browser, 15).until(
            EC.url_contains("linkedin.com/feed/")
        )
        print("Successfully logged in.")
        
    def start_applying(self):
        # New logic: Prioritize positions_with_count if available
        if self.positions_with_count:
            print("Detected 'positionsWithCount' configuration. Engaging new application logic...")
            page_sleep = 0
            minimum_time = 60 * 2  # Minimum time bot should run before taking a break
            minimum_page_time = time.time() + minimum_time

            for position_config in self.positions_with_count:
                position_name = position_config['name']
                max_applications = position_config['count']
                
                current_applied_for_this_pos = self.applied_counts.get(position_name, 0)
                if current_applied_for_this_pos >= max_applications:
                    print(f"Position '{position_name}' has reached its application limit ({current_applied_for_this_pos}/{max_applications}). Skipping.")
                    continue

                print(f"Processing position: '{position_name}' (Applied: {current_applied_for_this_pos}, Limit: {max_applications})")

                if not self.locations:
                    print(f"Warning: Global locations list is empty. Cannot search for position '{position_name}'.")
                    continue
                
                shuffled_locations = random.sample(self.locations, len(self.locations))
                for location in shuffled_locations:
                    current_applied_for_this_pos = self.applied_counts.get(position_name, 0) # Re-check count before processing a new location
                    if current_applied_for_this_pos >= max_applications:
                        print(f"Position '{position_name}' reached limit before processing location '{location}'. Stopping search for this position.")
                        break  # Break from location loop, move to next position_config

                    location_url = "&location=" + location + "&geoId=" + self.click_location_url(location)
                    job_page_number = self.start_from_page - 2  # Will be incremented to start_from_page - 2 in loop
                    print(f"Searching for position '{position_name}' in '{location}' starting from page {self.start_from_page}.")

                    try:
                        while True:
                            current_applied_for_this_pos = self.applied_counts.get(position_name, 0) # Re-check count before fetching new page
                            if current_applied_for_this_pos >= max_applications:
                                print(f"Position '{position_name}' reached limit ({current_applied_for_this_pos}/{max_applications}) before fetching new page in '{location}'. Stopping.")
                                break # Break from while loop (pages) for current location

                            page_sleep += 1
                            job_page_number += 1
                            print(f"Position '{position_name}' @ '{location}': Going to job page {job_page_number}")
                            self.next_job_page(position_name, location_url, job_page_number)
                            time.sleep(random.uniform(1, 2)) if not self.FastMode else time.sleep(random.uniform(0.5, 1))
                            print("Starting the application process for this page...")
                            # Pass current_position_config to apply_jobs for targeted application and counting
                            self.apply_jobs(location, current_position_config=position_config) 
                            print("Job applications on this page have been processed.")

                            # Time control logic (similar to existing logic)
                            time_left = minimum_page_time - time.time()
                            if time_left > 0:
                                print(f"Sleeping for {time_left:.2f} seconds.")
                                time.sleep(time_left)
                                minimum_page_time = time.time() + minimum_time
                            if page_sleep % 5 == 0:
                                sleep_time = random.randint(5, 10)
                                print(f"Taking a short break for {sleep_time} seconds.")
                                time.sleep(sleep_time)
                                page_sleep +=1 # To avoid immediate re-trigger if loop is very fast
                    except Exception as e:
                        # These are expected exceptions that indicate we should move to next location
                        expected_exceptions = [
                            "No more jobs on this page.",
                            "Nothing to do here, moving forward...",
                            "Job list UI elements not found, cannot proceed with this page."
                        ]
                        
                        if not any(expected_msg in str(e) for expected_msg in expected_exceptions):
                            print(f"Error processing position '{position_name}' in '{location}': {e}")
                            traceback.print_exc()
                        else: # Expected exceptions for end of job list or similar
                             print(f"Position '{position_name}' @ '{location}': {str(e)}. Ending search for this location.")
                        # Any exception (including no more jobs) breaks the while True loop for the current location
                    
                    # After a location is fully processed (or an error occurred), check count again.
                    if self.applied_counts.get(position_name, 0) >= max_applications:
                        print(f"Position '{position_name}' reached application limit after processing location '{location}'.")
                        break # Break from location loop for this position_name
            
            print("All 'positionsWithCount' configurations have been processed.")
            return # New logic finished, return to prevent old logic execution

        # --- Existing logic starts below --- 
        # This part will only execute if self.positions_with_count is empty.
        print("'positionsWithCount' is not configured or is empty. Engaging original application logic...")
        searches = list(product(self.positions, self.locations))
        random.shuffle(searches)

        page_sleep = 0
        minimum_time = 60 * 2  # minimum time bot should run before taking a break
        minimum_page_time = time.time() + minimum_time

        for (position, location) in searches:
            location_url = "&location=" + location + "&geoId=" + self.click_location_url(location)
            job_page_number = self.start_from_page - 2  # Will be incremented to start_from_page - 1 in loop

            print(f"Starting the search for {position} in {location} from page {self.start_from_page}.")

            try:
                while True:
                    page_sleep += 1
                    job_page_number += 1
                    print("Going to job page " + str(job_page_number))
                    self.next_job_page(position, location_url, job_page_number)
                    time.sleep(random.uniform(1, 2)) if not self.FastMode else time.sleep(random.uniform(0.5, 1))
                    print("Starting the application process for this page...")
                    self.apply_jobs(location)
                    print("Job applications on this page have been successfully completed.")

                    time_left = minimum_page_time - time.time()
                    if time_left > 0:
                        print("Sleeping for " + str(time_left) + " seconds.")
                        time.sleep(time_left)
                        minimum_page_time = time.time() + minimum_time
                    if page_sleep % 5 == 0:
                        sleep_time = random.randint(5, 10)  # Changed from 500, 900 {seconds}
                        print(f"Sleeping for {sleep_time} seconds.")
                        time.sleep(sleep_time)
                        page_sleep += 1
            except Exception as e:
                # These are expected exceptions that indicate we should move to next search
                expected_exceptions = [
                    "No more jobs on this page.",
                    "Nothing to do here, moving forward...", 
                    "Job list UI elements not found, cannot proceed with this page."
                ]
                
                if not any(expected_msg in str(e) for expected_msg in expected_exceptions):
                    print(f"Error processing {position} in {location}: {e}")
                    traceback.print_exc()
                else:
                    print(f"{position} @ {location}: {str(e)}. Moving to next search.")
                pass

            time_left = minimum_page_time - time.time()
            if time_left > 0:
                print("Sleeping for " + str(time_left) + " seconds.")
                time.sleep(time_left)
                minimum_page_time = time.time() + minimum_time
            if page_sleep % 5 == 0:
                sleep_time = random.randint(5, 10)  # Changed from 500, 900 {seconds}
                print(f"Sleeping for {sleep_time} seconds.")
                time.sleep(sleep_time)
                page_sleep += 1

    def apply_jobs(self, location, current_position_config=None):
        # 添加统计变量
        jobs_processed = 0
        jobs_applied = 0
        jobs_skipped = 0
        start_seen_count = len(self.seen_jobs)
        
        no_jobs_text = ""
        try:
            no_jobs_element = self.browser.find_element(By.CLASS_NAME,
                                                        'jobs-search-two-pane__no-results-banner--expand')
            no_jobs_text = no_jobs_element.text
        except:
            pass
        if 'No matching jobs found' in no_jobs_text:
            raise Exception("No more jobs on this page.")

        if 'unfortunately, things are' in self.browser.page_source.lower():
            raise Exception("No more jobs on this page.")

        job_results_header = ""
        maybe_jobs_crap = ""
        job_results_header = self.browser.find_element(By.CLASS_NAME, "jobs-search-results-list__text")
        maybe_jobs_crap = job_results_header.text

        if 'Jobs you may be interested in' in maybe_jobs_crap:
            raise Exception("Nothing to do here, moving forward...")

        try:
            # TODO: Can we simply use class name scaffold-layout__list for the scroll (necessary to show all li in the dom?)? Does it need to be the ul within the scaffold list?
            #      Then we can simply get all the li scaffold-layout__list-item elements within it for the jobs

            # Define the XPaths for potentially different regions
            xpath_region1 = "/html/body/div[6]/div[3]/div[4]/div/div/main/div/div[2]/div[1]/div"
            xpath_region2 = "/html/body/div[5]/div[3]/div[4]/div/div/main/div/div[2]/div[1]/div"
            job_list = []

            # Attempt to locate the element using XPaths
            try:
                job_results = self.browser.find_element(By.XPATH, xpath_region1)
                ul_xpath = "/html/body/div[6]/div[3]/div[4]/div/div/main/div/div[2]/div[1]/div/ul"
                ul_element = self.browser.find_element(By.XPATH, ul_xpath)
                ul_element_class = ul_element.get_attribute("class").split()[0]
                print(f"Found using xpath_region1 and detected ul_element as {ul_element_class} based on {ul_xpath}")

            except NoSuchElementException:
                job_results = self.browser.find_element(By.XPATH, xpath_region2)
                ul_xpath = "/html/body/div[5]/div[3]/div[4]/div/div/main/div/div[2]/div[1]/div/ul"
                ul_element = self.browser.find_element(By.XPATH, ul_xpath)
                ul_element_class = ul_element.get_attribute("class").split()[0]
                print(f"Found using xpath_region2 and detected ul_element as {ul_element_class} based on {ul_xpath}")

            # Extract the random class name dynamically
            random_class = job_results.get_attribute("class").split()[0]
            print(f"Random class detected: {random_class}")

            # Use the detected class name to find the element
            job_results_by_class = self.browser.find_element(By.CSS_SELECTOR, f".{random_class}")
            print(f"job_results: {job_results_by_class}")
            print("Successfully located the element using the random class name.")

            # Find job list elements
            job_list = self.browser.find_elements(By.CLASS_NAME, ul_element_class)[0].find_elements(By.CLASS_NAME, 'scaffold-layout__list-item')
            print(f"Found {len(job_list)} jobs on this page")

            if len(job_list) == 0:
                raise Exception("No more jobs on this page.")  # TODO: Seemed to encounter an error where we ran out of jobs and didn't go to next page, perhaps because I didn't have scrolling on?
            else:
                job_list[0].find_element(By.TAG_NAME, 'a').click()
                time.sleep(random.uniform(2, 3))
                # Scroll logic (currently disabled for testing)
                self.scroll_slow(job_results_by_class, step=600, )  # Scroll down
                self.scroll_slow(job_results_by_class, step=900, reverse=True)  # Scroll up

        except NoSuchElementException:
            print("No job results found using the specified XPaths or class.")
            # To prevent loop, ensure an exception is raised if job list can't be found, 
            # which will be caught by start_applying to move to next location/position.
            raise Exception("Job list UI elements not found, cannot proceed with this page.") 
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise Exception(f"Unexpected error fetching job list: {e}")

        for i in range(len(job_list)):
            # === START: New logic for position counting and matching ===
            if current_position_config:
                target_position_name = current_position_config['name']
                max_allowed_applications = current_position_config['count']
                current_applied_count = self.applied_counts.get(target_position_name, 0)

                if current_applied_count >= max_allowed_applications:
                    print(f"Target for '{target_position_name}' ({max_allowed_applications}) reached. Stopping further applications for this position on this page.")
                    break # Stop processing jobs on this page for this position_config
            # === END: New logic for position counting and matching ===
            
            # jobs_processed - 只有真正开始处理的职位才计入
            jobs_processed += 1

            job_title, company, poster, job_location, apply_method, link = "", "", "", "", "", ""
            job_tile = self.browser.find_elements(By.CLASS_NAME, ul_element_class)[0].find_elements(By.CLASS_NAME, 'scaffold-layout__list-item')[i]
            try:
                job_title_element = job_tile.find_element(By.TAG_NAME, 'a')
                job_title = job_title_element.find_element(By.TAG_NAME, 'strong').text
                # link = job_title_element.get_attribute('href').split('?')[0]
                link = job_title_element.get_attribute('href')
            except:
                pass
            try:
                # company = job_tile.find_element(By.CLASS_NAME, 'job-card-container__primary-description').text # original code
                company = job_tile.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle').text
            except:
                pass
            try:
                # get the name of the person who posted for the position, if any is listed
                hiring_line = job_tile.find_element(By.XPATH, '//span[contains(.,\' is hiring for this\')]')
                hiring_line_text = hiring_line.text
                name_terminating_index = hiring_line_text.find(' is hiring for this')
                if name_terminating_index != -1:
                    poster = hiring_line_text[:name_terminating_index]
            except:
                pass
            try:
                job_location = job_tile.find_element(By.CLASS_NAME, 'job-card-container__metadata-item').text
            except:
                pass
            try:
                apply_method = job_tile.find_element(By.CLASS_NAME, 'job-card-container__apply-method').text
            except:
                pass

            contains_blacklisted_keywords = False


            for word in self.title_blacklist:
                if word.lower() in job_title.lower():
                    contains_blacklisted_keywords = True
                    break

            if company.lower() not in [word.lower() for word in self.company_blacklist] and \
                    poster.lower() not in [word.lower() for word in self.poster_blacklist] and \
                    contains_blacklisted_keywords is False and link not in self.seen_jobs and \
                    not self.is_job_already_applied(link):
                try:
                    # Click the job to load description
                    max_retries = 3
                    retries = 0
                    while retries < max_retries:
                        try:
                            # TODO: This is throwing an exception when running out of jobs on a page
                            job_el = job_tile.find_element(By.TAG_NAME, 'a')
                            job_el.click()
                            break
                        except StaleElementReferenceException:
                            retries += 1
                            continue

                    time.sleep(random.uniform(3, 5)) if not self.FastMode else time.sleep(random.uniform(1, 2))

                    # 检查申请人数是否超过设定的阈值
                    if self.lessApplicantsEnabled:
                        try:
                            # 尝试找到显示申请人数的元素
                            desc_container = self.browser.find_element(By.CLASS_NAME, 'job-details-jobs-unified-top-card__tertiary-description-container')
                            description_text = desc_container.text
                            
                            # 提取申请人数（支持多种格式）
                            # 英文格式: "2 applicants"
                            # 中文格式: "2 位申请者", "超过 100 位申请者", "超过 100 位会员点击过"申请""
                            applicants_count = None
                            
                            # 匹配各种格式的正则表达式
                            patterns = [
                                r'(\d+)\s+applicants?',  # 英文: "2 applicants"
                                r'(\d+)\s*位申请者',      # 中文: "2 位申请者"
                                r'超过\s*(\d+)\s*位申请者',  # 中文: "超过 100 位申请者"
                                r'over\s*(\d+)\s*applicants',  # 英文: "over 100 applicants"
                                r'超过\s*(\d+)\s*位会员点击过"?申请"?',  # 中文: "超过 100 位会员点击过"申请""
                                r'over\s*(\d+)\s*people clicked apply'  # 英文: "Over 100 people clicked apply"
                            ]
                            
                            # 尝试所有模式
                            for pattern in patterns:
                                match = re.search(pattern, description_text)
                                if match:
                                    # 提取数字
                                    applicants_count = int(match.group(1))
                                    break
                            
                            # 如果成功提取到申请人数
                            if applicants_count is not None:
                                print(f"Detected applicants count: {applicants_count}")
                                
                                # 如果申请人数超过设定的阈值，跳过此职位
                                if applicants_count > self.lessApplicantsCount:
                                    print(f"Applicants count ({applicants_count}) exceeds threshold ({self.lessApplicantsCount}), skipping job")
                                    jobs_skipped += 1  # jobs_skipped
                                    if link and link not in self.seen_jobs: 
                                        self.seen_jobs.append(link)
                                    continue
                        except Exception as e:
                            print(f"检查申请人数时出错: {e}")

                    # TODO: Check if the job is already applied or the application has been reached
                    # "You've reached the Easy Apply application limit for today. Save this job and come back tomorrow to continue applying."
                    # Do this before evaluating job fit to save on API calls

                    if self.evaluate_job_fit:
                        try:
                            # Get job description
                            job_description = self.browser.find_element(
                                By.ID, 'job-details'
                            ).text  

                            # Evaluate if we should apply
                            if not self.ai_response_generator.evaluate_job_fit(job_title, job_description):
                                print("Skipping application: Job requirements not aligned with candidate profile per AI evaluation.")
                                jobs_skipped += 1  # jobs_skipped
                                if link and link not in self.seen_jobs: self.seen_jobs.append(link) # Mark as seen
                                continue
                        except Exception as e:
                            print(f"Could not load job description for AI evaluation: {e}")
                            # Decide if you want to proceed without AI evaluation or skip
                            # if link and link not in self.seen_jobs: self.seen_jobs.append(link)
                            # continue 

                    try:
                        done_applying = self.apply_to_job()
                        if done_applying:
                            print(f"Application sent to {company} for the position of {job_title}.")
                            # Add to applied records
                            self.add_applied_job(link)
                            # jobs_applied
                            jobs_applied += 1
                            # === START: New logic for incrementing count ===
                            if current_position_config:
                                target_position_name_for_count = current_position_config['name']
                                self.applied_counts[target_position_name_for_count] = self.applied_counts.get(target_position_name_for_count, 0) + 1
                                print(f"Applied count for '{target_position_name_for_count}' is now: {self.applied_counts[target_position_name_for_count]}/{current_position_config['count']}")
                            # === END: New logic for incrementing count ===
                        else:
                            print(f"An application for '{job_title}' at {company} has been submitted earlier or was not EasyApply.")
                    except Exception as e_apply:
                        # Check if it's a daily limit error
                        if "Daily Easy Apply limit reached" in str(e_apply):
                            print("🛑 Daily limit reached - stopping application process")
                            raise Exception("Daily limit reached - stopping application process")
                        
                        temp = self.file_name
                        self.file_name = "failed"
                        print(f"Failed to apply to job: '{job_title}'. Link: {link}. Error: {e_apply}")
                        traceback.print_exc()
                        try:
                            self.write_to_file(company, job_title, link, job_location, location)
                        except:
                            pass
                        self.file_name = temp
                        # print(f'updated {temp}.') # Original comment

                    try:
                        # Write to file only if successfully applied, or based on your preference
                        if done_applying: # Condition this write based on success if preferred
                             self.write_to_file(company, job_title, link, job_location, location)
                    except Exception as e_write:
                        print(
                            f"Unable to save the job information in the file for '{job_title}'. Error: {e_write}")
                        # traceback.print_exc() # Already printed by the application failure usually
                except Exception as e_outer_job_loop:
                    # Check if it's a daily limit error that should stop the entire process
                    if "Daily limit reached - stopping application process" in str(e_outer_job_loop):
                        print("🔄 The program stopped gracefully: The LinkedIn daily application limit has been reached")
                        print(f"Page processing complete - Processed: {jobs_processed}, Applied: {jobs_applied}, Skipped: {jobs_skipped}, Newly seen: {newly_seen}")

                        return jobs_processed, jobs_applied, jobs_skipped
                    
                    print(f"Outer loop error for job '{job_title}': {e_outer_job_loop}")
                    traceback.print_exc()
                    # pass # Original was pass, consider if seen_jobs needs update here
            else:
                # This 'else' corresponds to the blacklist/seen_jobs check
                skip_reason = []
                if company.lower() in [word.lower() for word in self.company_blacklist]:
                    skip_reason.append("company blacklisted")
                if poster.lower() in [word.lower() for word in self.poster_blacklist]:
                    skip_reason.append("poster blacklisted")
                if contains_blacklisted_keywords:
                    skip_reason.append("title contains blacklisted keywords")
                if link in self.seen_jobs:
                    skip_reason.append("already seen in this session")
                if self.is_job_already_applied(link):
                    skip_reason.append("already applied previously")
                
                reason_text = ", ".join(skip_reason) if skip_reason else "unknown reason"
                
                try:
                    print(f"Skipping job - {company} {job_title} (Reason: {reason_text})")
                except UnicodeEncodeError:
                    print(f"Skipping job - {company.encode('gbk', 'replace').decode('gbk')} {job_title.encode('gbk', 'replace').decode('gbk')} (Reason: {reason_text})")
                
                jobs_skipped += 1
                
                if link not in self.seen_jobs and link:
                    self.seen_jobs.append(link)

        end_seen_count = len(self.seen_jobs)
        newly_seen = end_seen_count - start_seen_count
        print(f"Page processing complete - Processed: {jobs_processed}, Applied: {jobs_applied}, Skipped: {jobs_skipped}, Newly seen: {newly_seen}")

    def apply_to_job(self):
        easy_apply_button = None

        try:
            easy_apply_button = self.browser.find_element(By.CLASS_NAME, 'jobs-apply-button')
            if not ('easy apply' in easy_apply_button.text.lower()) and not ('快速申请' in easy_apply_button.text.lower()):
                print(f"Easy apply button not found: {easy_apply_button.text}")
                return False
        except:
            return False
        # Scroll to the job description
        try:
            job_description_area = self.browser.find_element(By.ID, "job-details")
            print(f"{job_description_area}")
            # self.scroll_slow(job_description_area, end=1600)
            # self.scroll_slow(job_description_area, end=1600, step=400, reverse=True)
        except:
            pass

        print("Starting the job application...")
        easy_apply_button.click()
        
        # Check for daily application limit after clicking
        time.sleep(random.uniform(2, 3)) if not self.FastMode else time.sleep(random.uniform(1, 2))
        
        # Check if we've reached the daily Easy Apply limit
        daily_limit_messages = [
            "you've reached today's easy apply limit",
            "reached today's easy apply limit",
            "easy apply limit for today",
            "continue applying tomorrow",
            "daily submissions to help ensure",
            "您已达到今天的快速申请限额",
            "今日快速申请限额",
            "明天继续申请"
        ]
        
        if any(msg in self.browser.page_source.lower() for msg in daily_limit_messages):
            print("❌ you've reached today's easy apply limit")
            # Try to close any modal dialogs
            try:
                self.browser.find_element(By.CLASS_NAME, 'artdeco-modal__dismiss').click()
                time.sleep(1)
            except:
                pass

            raise Exception("Daily Easy Apply limit reached")

        button_text = ""
        submit_application_text = 'submit application'

        while submit_application_text not in button_text.lower() and '提交' not in button_text:
            try:
                self.fill_up()
                next_button = self.browser.find_element(By.CLASS_NAME, "artdeco-button--primary")
                button_text = next_button.text.lower()
                print(button_text)
                if submit_application_text in button_text or '提交' in button_text:
                    try:
                        # Try to unfollow company
                        self.unfollow()
                    except:
                        print("Failed to unfollow company.")
                time.sleep(random.uniform(1.5, 2.5)) if not self.FastMode else time.sleep(random.uniform(1, 2))
                next_button.click()
                time.sleep(random.uniform(3.0, 5.0)) if not self.FastMode else time.sleep(random.uniform(2.0, 3.0))

                # Newer error handling
                error_messages = [
                    'enter a valid',
                    'enter a decimal',
                    'Enter a whole number'
                    'Enter a whole number between 0 and 99',
                    'file is required',
                    'whole number',
                    'make a selection',
                    'select checkbox to proceed',
                    'saisissez un numéro',
                    '请输入whole编号',
                    '请输入decimal编号',
                    '长度超过 0.0',
                    'Numéro de téléphone',
                    'Introduce un número de whole entre',
                    'Inserisci un numero whole compreso',
                    'Preguntas adicionales',
                    'Insira um um número',
                    'Cuántos años'
                    'use the format',
                    'A file is required',
                    '请选择',
                    '请 选 择',
                    '請選擇',
                    '請 選 擇',
                    '請輸入有效',
                    'Inserisci',
                    'wholenummer',
                    'Wpisz liczb',
                    'zakresu od',
                    'tussen'
                ]

                if any(error in self.browser.page_source.lower() for error in error_messages):
                    raise Exception("Failed answering required questions or uploading required files.")
            except:
                traceback.print_exc()
                self.browser.find_element(By.CLASS_NAME, 'artdeco-modal__dismiss').click()
                time.sleep(random.uniform(2, 3)) if not self.FastMode else time.sleep(random.uniform(1, 2))
                self.browser.find_elements(By.CLASS_NAME, 'artdeco-modal__confirm-dialog-btn')[0].click()
                time.sleep(random.uniform(2, 3)) if not self.FastMode else time.sleep(random.uniform(1, 2))
                raise Exception("Failed to apply to job!")

        closed_notification = False
        time.sleep(random.uniform(2, 3)) if not self.FastMode else time.sleep(random.uniform(1, 2))
        try:
            self.browser.find_element(By.CLASS_NAME, 'artdeco-modal__dismiss').click()
            closed_notification = True
        except:
            pass
        try:
            self.browser.find_element(By.CLASS_NAME, 'artdeco-toast-item__dismiss').click()
            closed_notification = True
        except:
            pass
        try:
            self.browser.find_element(By.CSS_SELECTOR, 'button[data-control-name="save_application_btn"]').click()
            closed_notification = True
        except:
            pass

        time.sleep(random.uniform(3, 5)) if not self.FastMode else time.sleep(random.uniform(2, 3))

        if closed_notification is False:
            raise Exception("Could not close the applied confirmation window!")

        return True

    def home_address(self, form):
        print("Trying to fill up home address fields")
        try:
            groups = form.find_elements(By.CLASS_NAME, 'jobs-easy-apply-form-section__grouping')
            if len(groups) > 0:
                for group in groups:
                    lb = group.find_element(By.TAG_NAME, 'label').text.lower()
                    input_field = group.find_element(By.TAG_NAME, 'input')
                    if 'street' in lb:
                        self.enter_text(input_field, self.personal_info['Street address'])
                    elif 'city' in lb or 'GEO-LOCATION' in input_field.get_attribute('id'):
                        print("Trying to fill up city field")
                        print(self.personal_info['City'])
                        self.enter_text(input_field, self.personal_info['City'])
                        time.sleep(1.5)
                        input_field.send_keys(Keys.DOWN)
                        input_field.send_keys(Keys.RETURN)
                    elif 'zip' in lb or 'zip / postal code' in lb or 'postal' in lb:
                        self.enter_text(input_field, self.personal_info['Zip'])
                    elif 'state' in lb or 'province' in lb:
                        self.enter_text(input_field, self.personal_info['State'])
                    else:
                        pass
            else:
                groups = form.find_elements(By.TAG_NAME, 'label')
                for group in groups:
                    lb = group.text.lower()
                    input_id = group.get_attribute('for')
                    if input_id:
                        input_field = form.find_element(By.ID, input_id)
                        print(f"Label: {lb}")
                        if 'street' in lb:
                            self.enter_text(input_field, self.personal_info['Street address'])
                        elif 'city' in lb or 'GEO-LOCATION' in input_field.get_attribute('id'):
                            print("Trying to fill up city field")
                            print(self.personal_info['City'])
                            self.enter_text(input_field, self.personal_info['City'])
                            time.sleep(1.5)
                            input_field.send_keys(Keys.DOWN)
                            input_field.send_keys(Keys.RETURN)
                        elif 'zip' in lb or 'zip / postal code' in lb or 'postal' in lb:
                            self.enter_text(input_field, self.personal_info['Zip'])
                        elif 'state' in lb or 'province' in lb:
                            self.enter_text(input_field, self.personal_info['State'])
                        else:
                            pass
        except:
            pass

    def get_answer(self, question):
        if self.checkboxes[question]:
            return 'yes'
        else:
            return 'no'

    # 主要代码
    def additional_questions(self, form):
        questions = form.find_elements(By.CLASS_NAME, 'fb-dash-form-element')
        for question in questions:
            try:
                # Radio check
                try:
                    radio_fieldset = question.find_element(By.TAG_NAME, 'fieldset')
                    question_span = radio_fieldset.find_element(By.CLASS_NAME, 'fb-dash-form-element__label').find_elements(By.TAG_NAME, 'span')[0]
                    radio_text = question_span.text.lower()
                    print(f"Radio question text: {radio_text}")

                    # First check whether it matches the custom question
                    custom_answer = None
                    if hasattr(self, 'customQuestions'):
                        for custom_question, answer in self.customQuestions.items():
                            print('custom_question:', custom_question.lower())
                            if custom_question.lower() in radio_text:
                                custom_answer = answer
                                print(f"Found matches for custom radio questions: '{radio_text}' -> '{custom_answer}'")
                                break

                    radio_labels = radio_fieldset.find_elements(By.TAG_NAME, 'label')
                    radio_options = [(i, text.text.lower()) for i, text in enumerate(radio_labels)]
                    print(f"radio options: {[opt[1] for opt in radio_options]}")

                    if len(radio_options) == 0:
                        raise Exception("No radio options found in question")

                    # If there is a custom answer, use it first
                    if custom_answer:
                        selected = False
                        for i, (_, option_text) in enumerate(radio_options):
                            if custom_answer.lower() in option_text:
                                radio_labels[i].click()
                                print(f"Custom answer single option selected: '{radio_text}' -> '{option_text}'")
                                selected = True
                                break
                        
                        if selected:
                            continue

                    # If there is no matching custom answer, use the original logic
                    answer = None

                    # Try to determine answer using existing logic
                    if 'driver\'s licence' in radio_text or 'driver\'s license' in radio_text:
                        answer = self.get_answer('driversLicence')
                    elif any(keyword in radio_text.lower() for keyword in
                            [
                                'Aboriginal', 'native', 'indigenous', 'tribe', 'first nations',
                                'native american', 'native hawaiian', 'inuit', 'metis', 'maori',
                                'aborigine', 'ancestral', 'native peoples', 'original people',
                                'first people', 'gender', 'race', 'disability', 'latino', 'torres',
                                'do you identify'
                            ]):
                        
                        print(f"EEO-related radio question detected: {radio_text}")
                        
                        # 构建EEO上下文信息
                        eeo_context = ""
                        if hasattr(self, 'eeo') and self.eeo:
                            eeo_info = []
                            for key, value in self.eeo.items():
                                if value:
                                    eeo_info.append(f"{key}: {value}")
                            if eeo_info:
                                eeo_context = f" My EEO information: {', '.join(eeo_info)}."
                        
                        # 添加EEO上下文到问题中
                        enhanced_question = radio_text + eeo_context
                        
                        # 使用AI来智能选择最佳EEO选项
                        ai_response = self.ai_response_generator.generate_response(
                            enhanced_question,
                            response_type="choice",
                            options=radio_options
                        )
                        
                        if ai_response is not None:
                            print(f"AI selected EEO radio option: {radio_options[ai_response]} for question: '{radio_text}'")
                            to_select = radio_labels[ai_response]
                            to_select.click()
                            continue
                        
                        # AI失败时的后备逻辑 - 使用原有的关键词匹配
                        print("AI response failed for EEO radio question, using fallback keyword matching")
                        answer = None
                        if 'gender' in radio_text.lower() and 'gender' in self.eeo:
                            eeo_value = self.eeo['gender']
                            if 'male' in eeo_value.lower():
                                answer = next((option for option in radio_options if 'male' in option[1].lower() and 'female' not in option[1].lower()), None)
                            elif 'female' in eeo_value.lower():
                                answer = next((option for option in radio_options if 'female' in option[1].lower()), None)
                            else:
                                negative_keywords = ['prefer', 'decline', 'don\'t', 'specified', 'none', 'wish']
                                answer = next((option for option in radio_options if
                                            any(neg_keyword in option[1].lower() for neg_keyword in negative_keywords)), None)
                        
                        elif 'race' in radio_text.lower() and 'race' in self.eeo:
                            eeo_value = self.eeo['race']
                            if 'asian' in eeo_value.lower():
                                answer = next((option for option in radio_options if 'asian' in option[1].lower()), None)
                            elif 'white' in eeo_value.lower():
                                answer = next((option for option in radio_options if 'white' in option[1].lower()), None)
                            elif 'black' in eeo_value.lower() or 'african' in eeo_value.lower():
                                answer = next((option for option in radio_options if 'black' in option[1].lower() or 'african' in option[1].lower()), None)
                            elif 'hispanic' in eeo_value.lower() or 'latino' in eeo_value.lower():
                                answer = next((option for option in radio_options if 'hispanic' in option[1].lower() or 'latino' in option[1].lower()), None)
                            elif 'american indian' in eeo_value.lower() or 'alaska native' in eeo_value.lower():
                                answer = next((option for option in radio_options if 'american indian' in option[1].lower() or 'alaska' in option[1].lower()), None)
                            elif 'hawaiian' in eeo_value.lower() or 'pacific' in eeo_value.lower():
                                answer = next((option for option in radio_options if 'hawaiian' in option[1].lower() or 'pacific' in option[1].lower()), None)
                            elif 'two or more' in eeo_value.lower():
                                answer = next((option for option in radio_options if 'two' in option[1].lower() and 'more' in option[1].lower()), None)
                            else:
                                negative_keywords = ['prefer', 'decline', 'don\'t', 'specified', 'none', 'wish']
                                answer = next((option for option in radio_options if
                                            any(neg_keyword in option[1].lower() for neg_keyword in negative_keywords)), None)
                        
                        elif 'disability' in radio_text.lower() and 'disability' in self.eeo:
                            eeo_value = self.eeo['disability']
                            if 'yes' in eeo_value.lower():
                                answer = next((option for option in radio_options if 'yes' in option[1].lower()), None)
                            elif 'no' in eeo_value.lower():
                                answer = next((option for option in radio_options if 'no' in option[1].lower()), None)
                            else:
                                negative_keywords = ['prefer', 'decline', 'don\'t', 'specified', 'none', 'wish', 'choose']
                                answer = next((option for option in radio_options if
                                            any(neg_keyword in option[1].lower() for neg_keyword in negative_keywords)), None)
                        
                        else:
                            # 默认选择拒绝回答的选项
                            negative_keywords = ['prefer', 'decline', 'don\'t', 'specified', 'none', 'wish', 'choose']
                            answer = next((option for option in radio_options if
                                        any(neg_keyword in option[1].lower() for neg_keyword in negative_keywords)), None)

                    elif 'assessment' in radio_text:
                        answer = self.get_answer("assessment")

                    elif 'clearance' in radio_text:
                        answer = self.get_answer("securityClearance")

                    elif 'north korea' in radio_text:
                        answer = 'no'

                    elif 'previously employ' in radio_text or 'previous employ' in radio_text:
                        answer = 'no'

                    elif 'authorized' in radio_text or 'authorised' in radio_text or 'legally' in radio_text:
                        answer = self.get_answer('legallyAuthorized')

                    elif any(keyword in radio_text.lower() for keyword in
                            ['certified', 'certificate', 'cpa', 'chartered accountant', 'qualification']):
                        answer = self.get_answer('certifiedProfessional')

                    elif 'urgent' in radio_text:
                        answer = self.get_answer('urgentFill')

                    elif 'commut' in radio_text or 'on-site' in radio_text or 'hybrid' in radio_text or 'onsite' in radio_text:
                        answer = self.get_answer('commute')

                    elif 'remote' in radio_text:
                        answer = self.get_answer('remote')

                    elif 'background check' in radio_text:
                        answer = self.get_answer('backgroundCheck')

                    elif 'drug test' in radio_text:
                        answer = self.get_answer('drugTest')

                    elif 'currently living' in radio_text or 'currently reside' in radio_text or 'right to live' in radio_text:
                        answer = self.get_answer('residency')

                    elif 'level of education' in radio_text:
                        for degree in self.checkboxes['degreeCompleted']:
                            if degree.lower() in radio_text:
                                answer = "yes"
                                break

                    elif 'experience' in radio_text:
                        if self.experience_default > 0:
                            answer = 'yes'
                        else:
                            for experience in self.experience:
                                if experience.lower() in radio_text:
                                    answer = "yes"
                                    break

                    elif 'data retention' in radio_text:
                        answer = 'no'

                    elif 'sponsor' in radio_text:
                        answer = self.get_answer('requireVisa')
                    
                    elif 'veteran' in radio_text.lower() and 'veteran' in self.eeo:
                        eeo_value = self.eeo['veteran']
                        if 'protected veteran' in eeo_value.lower():
                            answer = next((option for option in radio_options if 'protected' in option[1].lower() and 'veteran' in option[1].lower()), None)
                        elif 'not a protected veteran' in eeo_value.lower():
                            answer = next((option for option in radio_options if 'not' in option[1].lower() and 'protected' in option[1].lower()), None)
                        elif 'veteran but not' in eeo_value.lower():
                            answer = next((option for option in radio_options if 'veteran' in option[1].lower() and 'not' in option[1].lower() and 'protected' in option[1].lower()), None)
                        else:
                            negative_keywords = ['prefer', 'decline', 'don\'t', 'specified', 'none', 'wish', 'choose']
                            answer = next((option for option in radio_options if
                                        any(neg_keyword in option[1].lower() for neg_keyword in negative_keywords)), None)
                    
                    to_select = None
                    if answer is not None:
                        print(f"Choosing answer: {answer}")
                        i = 0
                        for radio in radio_labels:
                            if answer in radio.text.lower():
                                to_select = radio_labels[i]
                                break
                            i += 1
                        if to_select is None:
                            print("Answer not found in radio options")

                    if to_select is None:
                        print("No answer determined")
                        self.record_unprepared_question("radio", radio_text)
                        question_text = question.find_element(By.TAG_NAME, 'label').text.lower()

                        # Since no response can be determined, we use AI to identify the best responseif available, falling back to the final option if the AI response is not available
                        ai_response = self.ai_response_generator.generate_response(
                            question_text,
                            response_type="choice",
                            options=radio_options
                        )
                        if ai_response is not None:
                            to_select = radio_labels[ai_response]
                        else:
                            to_select = radio_labels[len(radio_labels) - 1]
                    to_select.click()

                    if radio_labels:
                        continue
                except Exception as e:
                    print(f"No custom radio option was matched")

                # Questions check
                try:
                    question_text = question.find_element(By.TAG_NAME, 'label').text.lower()
                    print(question_text)

                    # First check whether it matches the custom question
                    custom_answer = None
                    if hasattr(self, 'customQuestions'):
                        for custom_question, answer in self.customQuestions.items():
                            if custom_question.lower() in question_text:
                                custom_answer = answer
                                print(f"Find custom text question matches: '{question_text}' -> '{custom_answer}'")
                                break
                    
                    txt_field_visible = False
                    try:
                        txt_field = question.find_element(By.TAG_NAME, 'input')
                        txt_field_visible = True
                    except:
                        try:
                            txt_field = question.find_element(By.TAG_NAME, 'textarea')
                            txt_field_visible = True
                        except:
                            raise Exception("Could not find textarea or input tag for question")

                    if 'numeric' in txt_field.get_attribute('id').lower():
                        # For decimal and integer response fields, the id contains 'numeric' while the type remains 'text' 
                        text_field_type = 'numeric'
                    elif 'text' in txt_field.get_attribute('type').lower():
                        text_field_type = 'text'
                    else:
                        raise Exception("Could not determine input type of input field!")

                    # If there is a custom answer, use it first
                    if custom_answer:
                        self.enter_text(txt_field, custom_answer)
                        print(f"Custom text answer filled in: '{question_text}' -> '{custom_answer}'")
                        continue

                    # If there is no matching custom answer, use the original logic
                    to_enter = ''
                    if ('experience' in question_text and 'salary' not in question_text) or 'how many years in' in question_text:
                        no_of_years = None
                        for experience in self.experience:
                            if experience.lower() in question_text:
                                no_of_years = int(self.experience[experience])
                                break
                        if no_of_years is None:
                            self.record_unprepared_question(text_field_type, question_text)
                            no_of_years = int(self.experience_default)
                        to_enter = no_of_years

                    elif 'grade point average' in question_text:
                        to_enter = self.university_gpa

                    elif 'first name' in question_text:
                        to_enter = self.personal_info['First Name']

                    elif 'last name' in question_text:
                        to_enter = self.personal_info['Last Name']

                    elif 'name' in question_text:
                        to_enter = self.personal_info['First Name'] + " " + self.personal_info['Last Name']

                    elif 'pronouns' in question_text:
                        to_enter = self.personal_info['Pronouns']

                    elif 'phone' in question_text:
                        to_enter = self.personal_info['Mobile Phone Number']
                    elif '联系电话' in question_text:
                        to_enter = self.personal_info['Mobile Phone Number']

                    elif 'linkedin' in question_text:
                        to_enter = self.personal_info['Linkedin']

                    elif 'message to hiring' in question_text or 'cover letter' in question_text:
                        to_enter = self.personal_info['MessageToManager']

                    elif 'website' in question_text or 'github' in question_text or 'portfolio' in question_text:
                        to_enter = self.personal_info['Website']

                    elif 'notice' in question_text or 'weeks' in question_text:
                        if text_field_type == 'numeric':
                            to_enter = int(self.notice_period)
                        else:
                            to_enter = str(self.notice_period)

                    elif 'salary' in question_text or 'expectation' in question_text or 'compensation' in question_text or 'CTC' in question_text:
                        if text_field_type == 'numeric':
                            to_enter = int(self.salary_minimum)
                        else:
                            to_enter = float(self.salary_minimum)
                        self.record_unprepared_question(text_field_type, question_text)

                    # Since no response can be determined, we use AI to generate a response if available, falling back to 0 or empty string if the AI response is not available
                    if text_field_type == 'numeric':
                        if not isinstance(to_enter, (int, float)):
                            ai_response = self.ai_response_generator.generate_response(
                                question_text,
                                response_type="numeric"
                            )
                            to_enter = ai_response if ai_response is not None else 0
                    elif to_enter == '':
                        ai_response = self.ai_response_generator.generate_response(
                            question_text,
                            response_type="text"
                        )
                        to_enter = ai_response if ai_response is not None else " ‏‏‎ "

                    self.enter_text(txt_field, to_enter)
                    continue
                except Exception as e:
                    print(f"An exception occurred while filling up text field")

                # Date Check
                try:
                    date_picker = question.find_element(By.CLASS_NAME, 'artdeco-datepicker__input ')
                    date_picker.clear()
                    date_picker.send_keys(date.today().strftime("%m/%d/%y"))
                    time.sleep(1.5)
                    date_picker.send_keys(Keys.RETURN)
                    time.sleep(0.5)
                    continue
                except Exception as e:
                    print(f"An exception occurred while filling up date picker field")

                # Dropdown check
                try:
                    question_text = question.find_element(By.TAG_NAME, 'label').text.lower()
                    print(f"Dropdown question text: {question_text}")
                    
                    # First check whether it matches the custom question
                    custom_answer = None
                    if hasattr(self, 'customQuestions'):
                        for custom_question, answer in self.customQuestions.items():
                            if custom_question.lower() in question_text:
                                custom_answer = answer
                                print(f"Found custom dropdown menu question matching: '{question_text}' -> '{custom_answer}'")
                                break
                                
                    dropdown_field = question.find_element(By.TAG_NAME, 'select')
                    select = Select(dropdown_field)
                    options = [option.text for option in select.options]
                    print(f"Dropdown options: {options}")
                    
                    # If there is a custom answer, use it first
                    if custom_answer:
                        selected = False
                        for option in options:
                            if custom_answer.lower() in option.lower():
                                self.select_dropdown(dropdown_field, option)
                                print(f"Custom drop-down menu option selected: '{question_text}' -> '{option}'")
                                selected = True
                                break
                        
                        if selected:
                            continue

                    # 如果没有匹配的自定义答案，使用原逻辑
                    if 'proficiency' in question_text:
                        proficiency = "None"
                        for language in self.languages:
                            if language.lower() in question_text:
                                proficiency = self.languages[language]
                                break
                        self.select_dropdown(dropdown_field, proficiency)

                    elif 'clearance' in question_text:
                        answer = self.get_answer('securityClearance')

                        choice = ""
                        for option in options:
                            if answer == 'yes':
                                choice = option
                            else:
                                if 'no' in option.lower():
                                    choice = option
                        if choice == "":
                            self.record_unprepared_question("dropdown", question_text)
                        self.select_dropdown(dropdown_field, choice)

                    elif 'assessment' in question_text:
                        answer = self.get_answer('assessment')
                        choice = ""
                        for option in options:
                            if answer == 'yes':
                                choice = option
                            else:
                                if 'no' in option.lower():
                                    choice = option
                        # if choice == "":
                        #    choice = options[len(options) - 1]
                        self.select_dropdown(dropdown_field, choice)

                    elif 'commut' in question_text or 'on-site' in question_text or 'hybrid' in question_text or 'onsite' in question_text:
                        answer = self.get_answer('commute')

                        choice = ""
                        for option in options:
                            if answer == 'yes':
                                choice = option
                            else:
                                if 'no' in option.lower():
                                    choice = option
                        # if choice == "":
                        #    choice = options[len(options) - 1]
                        self.select_dropdown(dropdown_field, choice)

                    elif 'country code' in question_text:
                        self.select_dropdown(dropdown_field, self.personal_info['Phone Country Code'])

                    elif 'north korea' in question_text:
                        choice = ""
                        for option in options:
                            if 'no' in option.lower():
                                choice = option
                        if choice == "":
                            choice = options[len(options) - 1]
                        self.select_dropdown(dropdown_field, choice)

                    elif 'previously employed' in question_text or 'previous employment' in question_text:
                        choice = ""
                        for option in options:
                            if 'no' in option.lower():
                                choice = option
                        if choice == "":
                            choice = options[len(options) - 1]
                        self.select_dropdown(dropdown_field, choice)

                    elif 'sponsor' in question_text:
                        answer = self.get_answer('requireVisa')
                        choice = ""
                        for option in options:
                            if answer == 'yes':
                                choice = option
                            else:
                                if 'no' in option.lower():
                                    choice = option
                        if choice == "":
                            choice = options[len(options) - 1]
                        self.select_dropdown(dropdown_field, choice)

                    elif 'above 18' in question_text.lower():  # Check for "above 18" in the question text
                        choice = ""
                        for option in options:
                            if 'yes' in option.lower():  # Select 'yes' option
                                choice = option
                        if choice == "":
                            choice = options[0]  # Default to the first option if 'yes' is not found
                        self.select_dropdown(dropdown_field, choice)

                    elif 'currently living' in question_text or 'currently reside' in question_text:
                        answer = self.get_answer('residency')
                        choice = ""
                        for option in options:
                            if answer == 'yes':
                                choice = option
                            else:
                                if 'no' in option.lower():
                                    choice = option
                        if choice == "":
                            choice = options[len(options) - 1]
                        self.select_dropdown(dropdown_field, choice)

                    elif 'authorized' in question_text or 'authorised' in question_text:
                        answer = self.get_answer('legallyAuthorized')
                        choice = ""
                        for option in options:
                            if answer == 'yes':
                                # find some common words
                                choice = option
                            else:
                                if 'no' in option.lower():
                                    choice = option
                        if choice == "":
                            choice = options[len(options) - 1]
                        self.select_dropdown(dropdown_field, choice)

                    elif any(keyword in question_text.lower() for keyword in
                             [
                                 'aboriginal', 'native', 'indigenous', 'tribe', 'first nations',
                                 'native american', 'native hawaiian', 'inuit', 'metis', 'maori',
                                 'aborigine', 'ancestral', 'native peoples', 'original people',
                                 'first people', 'gender', 'race', 'disability', 'latino', 'veteran'
                             ]):

                        print(f"EEO-related dropdown question detected: {question_text}")

                        # 使用AI来智能选择最佳EEO选项
                        choice = options[len(options) - 1]  # 默认选择最后一个选项
                        choices = [(i, option) for i, option in enumerate(options)]

                        # 构建EEO上下文信息
                        eeo_context = ""
                        if hasattr(self, 'eeo') and self.eeo:
                            eeo_info = []
                            for key, value in self.eeo.items():
                                if value:
                                    eeo_info.append(f"{key}: {value}")
                            if eeo_info:
                                eeo_context = f" My EEO information: {', '.join(eeo_info)}."

                        # 添加EEO上下文到问题中
                        enhanced_question = question_text + eeo_context

                        ai_response = self.ai_response_generator.generate_response(
                            enhanced_question,
                            response_type="choice",
                            options=choices
                        )

                        if ai_response is not None:
                            choice = options[ai_response]
                            print(f"AI selected EEO option: '{choice}' for question: '{question_text}'")
                        else:
                            # AI失败时的后备逻辑 - 使用配置的EEO信息进行基本匹配
                            print("AI response failed, using fallback EEO matching logic")

                            # 尝试使用EEO配置
                            if 'gender' in question_text.lower() and 'gender' in self.eeo:
                                eeo_value = self.eeo['gender']
                                if 'male' in eeo_value.lower():
                                    choice = next((option for option in options if
                                                   'male' in option.lower() and 'female' not in option.lower()), "")
                                elif 'female' in eeo_value.lower():
                                    choice = next((option for option in options if 'female' in option.lower()), "")

                            elif 'race' in question_text.lower() and 'race' in self.eeo:
                                eeo_value = self.eeo['race']
                                race_mapping = {
                                    'asian': 'asian',
                                    'white': 'white',
                                    'black': ['black', 'african'],
                                    'hispanic': ['hispanic', 'latino'],
                                    'american indian': ['american indian', 'alaska'],
                                    'hawaiian': ['hawaiian', 'pacific'],
                                    'two or more': ['two', 'more']
                                }

                                for race_key, search_terms in race_mapping.items():
                                    if race_key in eeo_value.lower():
                                        if isinstance(search_terms, list):
                                            choice = next((option for option in options if
                                                           any(term in option.lower() for term in search_terms)), "")
                                        else:
                                            choice = next(
                                                (option for option in options if search_terms in option.lower()), "")
                                        break

                            elif 'disability' in question_text.lower() and 'disability' in self.eeo:
                                eeo_value = self.eeo['disability']
                                if 'yes' in eeo_value.lower():
                                    choice = next((option for option in options if 'yes' in option.lower()), "")
                                elif 'no' in eeo_value.lower():
                                    choice = next((option for option in options if 'no' in option.lower()), "")

                            elif 'veteran' in question_text.lower() and 'veteran' in self.eeo:
                                eeo_value = self.eeo['veteran']
                                if 'protected veteran' in eeo_value.lower():
                                    choice = next((option for option in options if
                                                   'protected' in option.lower() and 'veteran' in option.lower() and 'not' not in option.lower()),
                                                  "")
                                elif 'not a protected veteran' in eeo_value.lower():
                                    choice = next((option for option in options if
                                                   'not' in option.lower() and 'protected' in option.lower()), "")
                                elif 'veteran but not' in eeo_value.lower():
                                    choice = next((option for option in options if
                                                   'veteran' in option.lower() and 'not' in option.lower() and 'protected' in option.lower()),
                                                  "")

                            # 如果仍然没有找到匹配项，使用默认的拒绝回答选项
                            if not choice:
                                negative_keywords = ['prefer', 'decline', 'don\'t', 'specified', 'none', 'wish',
                                                     'choose']
                                for option in options:
                                    if any(neg_keyword in option.lower() for neg_keyword in negative_keywords):
                                        choice = option
                                        break

                        if not choice and options:
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)

                    elif 'citizenship' in question_text:
                        answer = self.get_answer('legallyAuthorized')
                        choice = ""
                        for option in options:
                            if answer == 'yes':
                                if 'no' in option.lower():
                                    choice = option
                        if choice == "":
                            choice = options[len(options) - 1]
                        self.select_dropdown(dropdown_field, choice)

                    elif 'clearance' in question_text:
                        answer = self.get_answer('clearance')
                        choice = ""
                        for option in options:
                            if answer == 'yes':
                                choice = option
                            else:
                                if 'no' in option.lower():
                                    choice = option
                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)
                    elif 'notifications' in question_text and options:
                        choice = ""
                        for option in options:
                            if 'yes' in option.lower():
                                choice = option

                        if choice == "":
                            choice = options[len(options) - 1]

                        self.select_dropdown(dropdown_field, choice)

                    elif 'email' in question_text:
                        continue  # assume email address is filled in properly by default

                    elif 'experience' in question_text or 'understanding' in question_text or 'familiar' in question_text or 'comfortable' in question_text or 'able to' in question_text:
                        answer = 'no'
                        if self.experience_default > 0:
                            answer = 'yes'
                        else:
                            for experience in self.experience:
                                if experience.lower() in question_text and self.experience[experience] > 0:
                                    answer = 'yes'
                                    break
                        if answer == 'no':
                            # record unlisted experience as unprepared questions
                            self.record_unprepared_question("dropdown", question_text)

                        choice = ""
                        for option in options:
                            if answer in option.lower():
                                choice = option
                        if choice == "":
                            choice = options[len(options) - 1]
                        self.select_dropdown(dropdown_field, choice)

                    else:
                        print(f"Unhandled dropdown question: {question_text}")
                        self.record_unprepared_question("dropdown", question_text)

                        # Since no response can be determined, we use AI to identify the best responseif available, falling back "yes" or the final response if the AI response is not available
                        choice = options[len(options) - 1]
                        choices = [(i, option) for i, option in enumerate(options)]
                        ai_response = self.ai_response_generator.generate_response(
                            question_text,
                            response_type="choice",
                            options=choices
                        )
                        if ai_response is not None:
                            choice = options[ai_response]
                        else:
                            choice = ""
                            for option in options:
                                if 'yes' in option.lower():
                                    choice = option

                        print(f"Selected option: {choice}")
                        self.select_dropdown(dropdown_field, choice)
                    continue
                except Exception as e:
                    print(f"An exception occurred while filling up dropdown field")

                # Checkbox check for agreeing to terms and service
                try:
                    clickable_checkbox = question.find_element(By.TAG_NAME, 'label')
                    clickable_checkbox.click()
                except Exception as e:
                    print(f"An exception occurred while filling up checkbox field")
            except Exception as e:
                print(f"An exception occurred while processing the problem")
                
    def fill_up(self):
        try:
            easy_apply_modal_content = self.browser.find_element(By.CLASS_NAME, "jobs-easy-apply-modal__content")
            form = easy_apply_modal_content.find_element(By.TAG_NAME, 'form')
            try:
                label = form.find_element(By.TAG_NAME, 'h3').text.lower()
                # Try to fill in the basic information, if you don't have it AI will help you
                if 'home address' in label:
                    self.home_address(form)
                elif 'contact info' in label:
                    self.contact_info(form)
                elif 'resume' in label:
                    self.send_resume()
                elif 'work experience' in label and len(self.workExperiences) > 0:
                    self.work_experience(form)
                elif 'education' in label and len(self.education) > 0:
                    self.education_fun(form)
                else:
                    self.additional_questions(form)
            except Exception as e:
                print("An exception occurred while filling up the form: no label, pass")
        except:
            print("An exception occurred while searching for form in modal")

    def write_to_file(self, company, job_title, link, location, search_location):
        to_write = [company, job_title, link, location, search_location, datetime.now()]
        file_path = self.file_name + ".csv"
        print(f'updated {file_path}.')

        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(to_write)

    def record_unprepared_question(self, answer_type, question_text):
        to_write = [answer_type, question_text]
        file_path = self.unprepared_questions_file_name + ".csv"

        try:
            with open(file_path, 'a') as f:
                writer = csv.writer(f)
                writer.writerow(to_write)
                print(f'Updated {file_path} with {to_write}.')
        except:
            print(
                "Special characters in questions are not allowed. Failed to update unprepared questions log.")
            print(question_text)

    def scroll_slow(self, scrollable_element, start=0, end=3600, step=100, reverse=False):
        if reverse:
            start, end = end, start
            step = -step

        for i in range(start, end, step):
            self.browser.execute_script("arguments[0].scrollTo(0, {})".format(i), scrollable_element)
            time.sleep(random.uniform(0.5, .6))

    def avoid_lock(self):
        if self.disable_lock:
            return

        pyautogui.keyDown('ctrl')
        pyautogui.press('esc')
        pyautogui.keyUp('ctrl')
        time.sleep(1.0)
        pyautogui.press('esc')

    def get_base_search_url(self, parameters):
        remote_url = ""
        lessthanTenApplicants_url = ""
        newestPostingsFirst_url = ""

        if parameters.get('remote'):
            remote_url = "&f_WT=2"
        else:
            remote_url = ""
            # TO DO: Others &f_WT= options { WT=1 onsite, WT=2 remote, WT=3 hybrid, f_WT=1%2C2%2C3 }

        if parameters['lessthanTenApplicants']:
            lessthanTenApplicants_url = "&f_EA=true"
            
        # 注意：我们现在在页面内容中直接检查申请人数，不再使用URL参数

        if parameters['newestPostingsFirst']:
            newestPostingsFirst_url += "&sortBy=DD"

        level = 1
        experience_level = parameters.get('experienceLevel', [])
        experience_url = "f_E="
        for key in experience_level.keys():
            if experience_level[key]:
                experience_url += "%2C" + str(level)
            level += 1

        distance_url = "?distance=" + str(parameters['distance'])

        job_types_url = "f_JT="
        job_types = parameters.get('jobTypes', [])
        # job_types = parameters.get('experienceLevel', [])
        for key in job_types:
            if job_types[key]:
                job_types_url += "%2C" + key[0].upper()

        date_url = ""
        dates = {"all time": "", "month": "&f_TPR=r2592000", "week": "&f_TPR=r604800", "24 hours": "&f_TPR=r86400"}
        date_table = parameters.get('date', [])
        
        # 处理自定义小时数
        custom_hours_selected = False
        custom_hours_value = 24  # 默认24小时
        
        # 检查是否有自定义小时数
        if date_table and 'custom_hours' in date_table and date_table['custom_hours']:
            custom_hours_selected = True
            # 获取自定义小时数
            if 'customHours' in parameters:
                try:
                    custom_hours_value = int(parameters['customHours'])
                    if custom_hours_value <= 0:  # 确保是正数
                        custom_hours_value = 24  # 如果无效则使用默认值
                except (ValueError, TypeError):
                    pass  # 使用默认值
        
        # 设置日期URL
        if custom_hours_selected:
            # 计算秒数：小时数 * 3600 秒/小时
            seconds = custom_hours_value * 3600
            date_url = f"&f_TPR=r{seconds}"
        else:
            # 处理标准日期选项
            for key in date_table.keys():
                if date_table[key] and key in dates:
                    date_url = dates[key]
                    break

        easy_apply_url = "&f_AL=true"

        extra_search_terms = [distance_url, remote_url, lessthanTenApplicants_url, newestPostingsFirst_url, job_types_url, experience_url]
        extra_search_terms_str = '&'.join(
            term for term in extra_search_terms if len(term) > 0) + easy_apply_url + date_url

        return extra_search_terms_str

    def next_job_page(self, position, location, job_page):
        self.browser.get("https://www.linkedin.com/jobs/search/" + self.base_search_url +
                         "&keywords=" + position + location + "&start=" + str(job_page * 25))

        self.avoid_lock()

    def click_location_url(self, keyword):
        try:
            self.browser.get("https://www.linkedin.com/jobs/search/")
            # 使用xpath获取id前缀为jobs-search-box-location-id-xxx的元素
            location_input = self.browser.find_element(By.XPATH, '//input[starts-with(@id,"jobs-search-box-location-id-")]')
            self.enter_text(location_input, keyword)
            time.sleep(2)

            location_seach_button = self.browser.find_element(By.XPATH, '//*[@id="global-nav-search"]/div/div[2]/button[1]')
            location_seach_button.click()
            time.sleep(5)
            # 获取当前地址的链接,提取参数geoId
            url = self.browser.current_url
            geoId = self.parse_geoId_from_url(url)
            return geoId
        except:
            print("An exception occurred while searching for location")
            return ''

    def parse_geoId_from_url(self, url):
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        geoId = query_params.get('geoId', [None])[0]
        return geoId

    def unfollow(self):
        try:
            follow_checkbox = self.browser.find_element(By.XPATH,
                                                        "//label[contains(.,'to stay up to date with their page.') or contains(.,'随时了解公司动态')]").click()
            follow_checkbox.click()
        except:
            pass

    def send_resume(self):
        print("Trying to send resume")
        try:
            file_upload_elements = (By.CSS_SELECTOR, "input[name='file']")
            if len(self.browser.find_elements(file_upload_elements[0], file_upload_elements[1])) > 0:
                input_buttons = self.browser.find_elements(file_upload_elements[0], file_upload_elements[1])
                if len(input_buttons) == 0:
                    raise Exception("No input elements found in element")
                for upload_button in input_buttons:
                    # upload_type = upload_button.find_element(By.XPATH, "..").find_element(By.XPATH, "preceding-sibling::*")
                    input_id = upload_button.get_attribute("id")
                    upload_type = self.browser.find_element(By.CSS_SELECTOR, f"label[for='{input_id}']")
                    if 'resume' in upload_type.text.lower():
                        upload_button.send_keys(self.resume_dir)
                    elif 'cover' in upload_type.text.lower():
                        if self.cover_letter_dir != '':
                            upload_button.send_keys(self.cover_letter_dir)
                        elif 'required' in upload_type.text.lower():
                            upload_button.send_keys(self.resume_dir)
                    elif  'upload' == upload_type.text.lower(): # photo is Upload
                        if self.photo_dir != '':
                            upload_button.send_keys(self.photo_dir)
                        elif 'required' in upload_type.text.lower():
                            upload_button.send_keys(self.resume_dir)
        except:
            print("Failed to upload resume or cover letter!")
            pass

    def enter_text(self, element, text):
        element.clear()
        element.send_keys(text)

    def select_dropdown(self, element, text):
        select = Select(element)
        select.select_by_visible_text(text)

    # Radio Select
    def radio_select(self, element, label_text, clickLast=False):
        label = element.find_element(By.TAG_NAME, 'label')
        if label_text in label.text.lower() or clickLast == True:
            label.click()

    # Contact info fill-up
    def contact_info(self, form):
        print("Trying to fill up contact info fields")
        frm_el = form.find_elements(By.TAG_NAME, 'label')
        if len(frm_el) > 0:
            for el in frm_el:
                text = el.text.lower()
                input_id = el.get_attribute('for')
                input_field = None
                if input_id:
                    input_field = form.find_element(By.ID, input_id)
                if 'email address' in text:
                    continue
                elif 'phone number' in text:
                    try:
                        country_code_picker = el.find_element(By.XPATH,
                                                              '//select[contains(@id,"phoneNumber")][contains(@id,"country")]')
                        self.select_dropdown(country_code_picker, self.personal_info['Phone Country Code'])
                    except Exception as e:
                        print("Country code " + self.personal_info[
                            'Phone Country Code'] + " not found. Please make sure it is same as in LinkedIn.")
                        print(e)
                    try:
                        phone_number_field = el.find_element(By.XPATH,
                                                             '//input[contains(@id,"phoneNumber")][contains(@id,"nationalNumber")]')
                        self.enter_text(phone_number_field, self.personal_info['Mobile Phone Number'])
                    except Exception as e:
                        print("Could not enter phone number:")
                        print(e)

                elif 'city' in text or (input_field and 'GEO-LOCATION' in input_field.get_attribute('id')):
                    print("Trying to fill up city field")
                    print(self.personal_info['City'])
                    self.enter_text(input_field, self.personal_info['City'])
                    time.sleep(1.5)
                    input_field.send_keys(Keys.DOWN)
                    input_field.send_keys(Keys.RETURN)

            self.send_resume()

    def handle_current_checkbox(self, question, form, item, form_type):
        """
        Handle "current" status checkboxes for both work experience and education
        
        Args:
            question: Current question element
            form: Form element
            item: Current item being processed (work experience or education)
            form_type: Form type, either 'work' or 'education'
        
        Returns:
            bool: True if checkbox was successfully handled, False otherwise
        """
        # Define keywords based on form type
        keywords = {
            'work': ['present', 'current'],
            'education': ['currently attend', 'current student']
        }
        # Define log messages based on form type
        log_messages = {
            'work': 'Current position',
            'education': 'Currently attending'
        }
        
        try:
            # Get question text
            checkbox_text = question.find_element(By.TAG_NAME, 'label').text.lower()
            # Check if it contains relevant keywords
            if any(keyword in checkbox_text for keyword in keywords.get(form_type, [])):
                is_current = item.get('current', False)
                print(f"{log_messages.get(form_type, 'Current')}: {is_current}")
                if is_current:
                    print('Attempting to click')
                    try:
                        # Try to get input_id and click the corresponding label
                        input_id = question.find_element(By.TAG_NAME, 'label').get_attribute('for')
                        if input_id:
                            label = form.find_element(By.XPATH, f"//label[@for='{input_id}']")
                            label.click()
                        else:
                            # If input_id not found, click the label directly
                            question.find_element(By.TAG_NAME, 'label').click()
                    except Exception as inner_e:
                        print(f"Could not click on '{log_messages.get(form_type, 'current')}' checkbox: {inner_e}")
                return True
        except Exception as e:
            print(f"Error handling current checkbox: {e}")
        return False

    def fill_repeatable_form(self, form, form_type):
        """
        Fill repeatable form sections like work experience or education
        
        Args:
            form: The form element to fill
            form_type: Type of form, either 'work' or 'education'
        """
        # Determine which data source and field mapping to use
        if form_type == 'work':
            items = self.workExperiences
            item_name = "work experience"
            field_mapping = {
                'title': ['title', 'position'],
                'company': ['company', 'employer'],
                'city': ['city', 'location'],
                'description': ['description']
            }
        else:  # form_type == 'education'
            items = self.education
            item_name = "education"
            field_mapping = {
                'school': ['school'],
                'degree': ['degree'],
                'major': ['field', 'major'],
                'city': ['city', 'location'],
            }
        
        if len(items) == 0:
            return
        
        print(f"Filling {item_name} fields")
        
        # Check for existing entries and remove them
        try:
            # Find cards in the form
            cards = form.find_elements(By.CLASS_NAME, 'artdeco-card')
            
            # If cards found and there's more than 0, we have old data
            if cards and len(cards) > 0:
                print(f"Found {len(cards)} existing {item_name} entries, removing them")

                for card in cards:
                    try:
                        # Find delete button (at same level as card, not inside it)
                        # Get parent element of the card
                        parent_element = card.find_element(By.XPATH, "./..")
                        
                        # Find delete buttons in parent element (at same level as card)
                        remove_buttons = parent_element.find_elements(By.XPATH, 
                            ".//button[contains(@aria-label, 'Remove') or contains(@aria-label, '删除') or contains(@aria-label, 'Delete')]")
                        
                        if not remove_buttons:
                            # Try other ways to find delete buttons
                            remove_buttons = form.find_elements(By.XPATH, 
                                "//button[contains(@aria-label, 'Remove') or contains(@aria-label, '删除') or contains(@aria-label, 'Delete')]")
                        
                        if remove_buttons:
                            print("Found delete button, clicking to remove")
                            remove_buttons[0].click()
                            time.sleep(0.5)
                            
                            # Click confirm delete button
                            confirm_buttons = self.browser.find_elements(By.CLASS_NAME, 'artdeco-modal__confirm-dialog-btn')
                            if confirm_buttons:
                                confirm_buttons[-1].click()
                                print(f"Removed an existing {item_name} entry")
                                time.sleep(1)
                            else:
                                print("Confirm delete button not found")
                        else:
                            print("Delete button not found")
                    except Exception as e:
                        print(f"Error deleting existing {item_name} entry: {e}")

                # Click 'Add more' button to add new form
                try:
                    print("Clicking 'Add more' button to add new form")
                    add_buttons = self.browser.find_elements(By.CLASS_NAME, 'jobs-easy-apply-repeatable-groupings__add-button')
                    if add_buttons:
                        add_buttons[0].click()
                        print("Add button clicked")
                        time.sleep(0.5)
                    else:
                        print(f"Add button not found, cannot add more {item_name} entries")
                except Exception as e:
                    print(f"Error clicking add button: {e}")

            else:
                print(f"No existing {item_name} data found, filling new data directly")
        except Exception as e:
            print(f"Error checking for existing {item_name} data: {e}")
        
        # Loop through all items
        for index, item in enumerate(items):
            print(f"Filling {item_name} entry #{index+1}")
            if index > 0:
                try:
                    print("Clicking 'Add more' button to add new form")
                    add_buttons = self.browser.find_elements(By.CLASS_NAME, 'jobs-easy-apply-repeatable-groupings__add-button')
                    if add_buttons:
                        add_buttons[0].click()
                        print("Add button clicked")
                        time.sleep(0.5)
                    else:
                        print(f"Add button not found, cannot add more {item_name} entries")
                        break
                except Exception as e:
                    print(f"Error clicking add button: {e}")
                    break
            
            # Search for elements in the form
            questions = form.find_elements(By.CLASS_NAME, 'fb-dash-form-element')
            
            for question in questions:
                try:
                    # Handle date range fields
                    try:
                        # Find date range component
                        date_range_component = question.find_element(By.XPATH, "./div[@data-test-date-range-form-component]")
                        if date_range_component:
                            print("Found date range component")
                            
                            # Handle start date (From)
                            from_fieldset = date_range_component.find_element(By.XPATH, ".//fieldset[@data-test-date-dropdown='start']")
                            if from_fieldset:
                                # Find month selector
                                month_select = from_fieldset.find_element(By.XPATH, ".//select[@data-test-month-select]")
                                select = Select(month_select)
                                # Get month from data
                                month_to_select = item.get('from_month', "January")
                                try:
                                    select.select_by_visible_text(month_to_select)
                                except:
                                    # Select first non-empty option
                                    options = select.options
                                    for option in options:
                                        option_text = option.text
                                        if option_text == month_to_select:
                                            option.click()
                                            break
                                            
                                # Find year selector
                                year_select = from_fieldset.find_element(By.XPATH, ".//select[@data-test-year-select]")
                                select = Select(year_select)
                                # Get year from data
                                default_year = "2020" if form_type == 'work' else "2015"
                                year_to_select = str(item.get('from_year', default_year))
                                try:
                                    select.select_by_visible_text(year_to_select)
                                except:
                                    # Select a reasonable year
                                    options = select.options
                                    for option in options:
                                        option_text = option.text
                                        if option_text.isdigit() and len(option_text) == 4 and int(option_text) == int(year_to_select):
                                            option.click()
                                            break
                            
                            # Handle end date (To)
                            to_fieldset = date_range_component.find_element(By.XPATH, ".//fieldset[@data-test-date-dropdown='end']")
                            if to_fieldset:
                                # Find month selector
                                month_select = to_fieldset.find_element(By.XPATH, ".//select[@data-test-month-select]")
                                select = Select(month_select)
                                # Get month from data
                                month_to_select = item.get('to_month', "January")
                                try:
                                    select.select_by_visible_text(month_to_select)
                                except:
                                    # Select first non-empty option
                                    options = select.options
                                    for option in options:
                                        option_text = option.text
                                        if option_text == month_to_select:
                                            option.click()
                                            break

                                # Find year selector
                                year_select = to_fieldset.find_element(By.XPATH, ".//select[@data-test-year-select]")
                                select = Select(year_select)
                                # Get year from data
                                default_year = "2020" if form_type == 'work' else "2019"
                                year_to_select = str(item.get('to_year', default_year))
                                try:
                                    select.select_by_visible_text(year_to_select)
                                except:
                                    # Select a reasonable year
                                    options = select.options
                                    for option in options:
                                        option_text = option.text
                                        if option_text.isdigit() and len(option_text) == 4 and int(option_text) == int(year_to_select):
                                            option.click()
                                            break
                            
                            continue  # Date handling complete, continue to next element
                    except Exception as e:
                        pass
                    
                    # Handle "current" status checkbox for work experience or education
                    if self.handle_current_checkbox(question, form, item, form_type):
                        continue
                    
                    # Handle regular input fields
                    try:
                        question_text = question.find_element(By.TAG_NAME, 'label').text.lower()
                        print(f"Input field: {question_text}")
                        
                        txt_field = None
                        try:
                            txt_field = question.find_element(By.TAG_NAME, 'input')
                        except:
                            try:
                                txt_field = question.find_element(By.TAG_NAME, 'textarea')
                            except:
                                pass
                        
                        if txt_field:
                            # Fill fields based on field mapping
                            field_filled = False
                            for field, keywords in field_mapping.items():
                                if any(keyword in question_text for keyword in keywords):
                                    value = item.get(field, "")
                                    self.enter_text(txt_field, value)
                                    
                                    # Special handling for city field
                                    if field == 'city' and value:
                                        time.sleep(1.5)
                                        try:
                                            txt_field.send_keys(Keys.DOWN)
                                            txt_field.send_keys(Keys.RETURN)
                                        except:
                                            pass
                                    
                                    field_filled = True
                                    break
                            
                            if field_filled:
                                continue
                    except Exception as e:
                        pass
                    
                except Exception as e:
                    print(f"Error processing form element: {e}")
        
            # Save all entries
            try:
                # First look for buttons with explicit "Save" or "保存" text
                save_buttons = form.find_elements(By.XPATH, "//button[contains(., 'Save') or contains(., '保存')]")
                if save_buttons:
                    save_buttons[0].click()
                    time.sleep(1)
                    print(f"{item_name.capitalize()} form saved")
            except Exception as e:
                print(f"Error clicking save button: {e}")
        
        print(f"{item_name.capitalize()} filling complete, filled {len(items)} entries")

    def work_experience(self, form):
        """Process and fill work experience fields in application forms"""
        self.fill_repeatable_form(form, 'work')

    def education_fun(self, form):
        """Process and fill education history fields in application forms"""
        self.fill_repeatable_form(form, 'education')