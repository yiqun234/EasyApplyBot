import yaml, os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from validate_email import validate_email
from linkedineasyapply import LinkedinEasyApply
import shutil
import sys
import platform # For more detailed platform info like machine architecture
import requests # For downloading
import zipfile # For unzipping
import stat # For chmod
import json # For loading/saving local versions.json

# --- Definition for setup_bundled_chrome ---
def setup_bundled_chrome(project_root, force_download=False):
    """
    Downloads and extracts the latest stable Chrome for Testing and corresponding ChromeDriver
    into the project's 'vendor/chrome_for_testing/' directory.
    Tries to use a local cache of version information first.
    """
    print("Setting up bundled Chrome and ChromeDriver...")
    vendor_dir = os.path.join(project_root, "vendor", "chrome_for_testing")
    os.makedirs(vendor_dir, exist_ok=True)

    local_versions_json_path = os.path.join(project_root, "vendor", "cft-versions.json")

    platform_system = sys.platform
    platform_machine = platform.machine()

    json_platform_key_chrome, json_platform_key_driver = None, None
    chrome_dir_name, chromedriver_dir_name, chrome_exe_name, chromedriver_exe_name = "", "", "", ""
    mac_arch_suffix = "arm64"

    if platform_system.startswith("win"):
        json_platform_key_chrome, json_platform_key_driver = "win64", "win64"
        chrome_dir_name, chromedriver_dir_name = "chrome-win64", "chromedriver-win64"
        chrome_exe_name, chromedriver_exe_name = "chrome.exe", "chromedriver.exe"
    elif platform_system.startswith("linux"):
        if platform_machine == "x86_64":
            json_platform_key_chrome, json_platform_key_driver = "linux64", "linux64"
            chrome_dir_name, chromedriver_dir_name = "chrome-linux64", "chromedriver-linux64"
            chrome_exe_name, chromedriver_exe_name = "chrome", "chromedriver"
    elif platform_system.startswith("darwin"):
        if platform_machine == "arm64": mac_arch_suffix = "arm64"
        elif platform_machine == "x86_64": mac_arch_suffix = "x64"
        else: print(f"Unsupported macOS architecture: {platform_machine}"); return False
        json_platform_key_chrome = f"mac-{mac_arch_suffix}"
        json_platform_key_driver = f"mac-{mac_arch_suffix}"
        chrome_dir_name, chromedriver_dir_name = f"chrome-mac-{mac_arch_suffix}", f"chromedriver-mac-{mac_arch_suffix}"
        chrome_exe_name = os.path.join("Google Chrome for Testing.app", "Contents", "MacOS", "Google Chrome for Testing")
        chromedriver_exe_name = "chromedriver"

    if not (json_platform_key_chrome and chrome_dir_name and chrome_exe_name):
        print(f"Unsupported platform/arch for auto-download: system='{platform_system}', machine='{platform_machine}'")
        return False

    target_chrome_exe_path = os.path.join(vendor_dir, chrome_dir_name, chrome_exe_name)
    target_chromedriver_exe_path = os.path.join(vendor_dir, chromedriver_dir_name, chromedriver_exe_name)

    if not force_download and os.path.exists(target_chrome_exe_path) and os.path.exists(target_chromedriver_exe_path):
        print("Bundled Chrome and ChromeDriver already exist.")
        if platform_system.startswith("linux") or platform_system.startswith("darwin"):
            if os.path.exists(target_chromedriver_exe_path):
                try:
                    current_mode = os.stat(target_chromedriver_exe_path).st_mode
                    if not (current_mode & stat.S_IXUSR):
                         os.chmod(target_chromedriver_exe_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                         print(f"Ensured execute permission for existing ChromeDriver: {target_chromedriver_exe_path}")
                except Exception as e: print(f"Warning: Could not set execute permission for existing ChromeDriver: {e}")
        return True

    if force_download:
        chrome_full_dir_path = os.path.join(vendor_dir, chrome_dir_name)
        driver_full_dir_path = os.path.join(vendor_dir, chromedriver_dir_name)
        if os.path.exists(chrome_full_dir_path): shutil.rmtree(chrome_full_dir_path)
        if os.path.exists(driver_full_dir_path): shutil.rmtree(driver_full_dir_path)
        os.makedirs(vendor_dir, exist_ok=True)

    # Attempt to load version data from local JSON first
    versions_data = None
    if os.path.exists(local_versions_json_path):
        print(f"Attempting to load version info from local cache: {local_versions_json_path}")
        try:
            with open(local_versions_json_path, 'r', encoding='utf-8') as f:
                versions_data = json.load(f)
            print("Successfully loaded version info from local cache.")
        except Exception as e:
            print(f"Error loading local version info JSON: {e}. Will attempt to fetch from URL.")
            versions_data = None # Ensure it's None to trigger fetch

    if versions_data is None: # If local load failed or file didn't exist
        try:
            versions_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
            print(f"Fetching latest stable versions from: {versions_url}")
            response = requests.get(versions_url, timeout=20)
            response.raise_for_status()
            versions_data = response.json()
            # Save the fetched data to local cache for next time
            try:
                with open(local_versions_json_path, 'w', encoding='utf-8') as f:
                    json.dump(versions_data, f, indent=4)
                print(f"Saved fetched version info to local cache: {local_versions_json_path}")
            except Exception as e:
                print(f"Warning: Could not save fetched version info to local cache: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching version information from URL: {e}")
            return False # Critical if we can't get version info

    if not versions_data:
        print("Failed to obtain version information from any source.")
        return False

    stable_channel_data = versions_data.get("channels", {}).get("Stable", {})
    if not stable_channel_data:
        print("Could not find 'Stable' channel data in the version information.")
        return False

    chrome_download_url, chromedriver_download_url = None, None
    for item in stable_channel_data.get("downloads", {}).get("chrome", []):
        if item.get("platform") == json_platform_key_chrome: chrome_download_url = item.get("url"); break
    for item in stable_channel_data.get("downloads", {}).get("chromedriver", []):
        if item.get("platform") == json_platform_key_driver: chromedriver_download_url = item.get("url"); break

    if not chrome_download_url: print(f"Could not find Chrome download URL for {json_platform_key_chrome}"); return False
    if not chromedriver_download_url: print(f"Could not find ChromeDriver URL for {json_platform_key_driver}"); return False

    def _download_and_extract_zip(url, file_name_prefix, base_extract_dir):
        temp_zip_filename = f"{file_name_prefix}-{json_platform_key_chrome}-temp.zip"
        zip_download_path = os.path.join(vendor_dir, temp_zip_filename)
        print(f"Downloading {file_name_prefix} from {url} to {zip_download_path}...")
        try:
            with requests.get(url, stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(zip_download_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192 * 10): f.write(chunk)
            print(f"Extracting {zip_download_path} to {base_extract_dir}...")
            with zipfile.ZipFile(zip_download_path, 'r') as zip_ref:
                zip_ref.extractall(base_extract_dir)
            print(f"Successfully downloaded and extracted {file_name_prefix}.")
            return True
        except Exception as e: print(f"Error during download/extraction for {file_name_prefix}: {e}"); return False
        finally: 
            if os.path.exists(zip_download_path): os.remove(zip_download_path)

    print("-" * 20); print("Processing Chrome...")
    if not _download_and_extract_zip(chrome_download_url, "chrome", vendor_dir): return False
    print("-" * 20); print("Processing ChromeDriver...")
    if not _download_and_extract_zip(chromedriver_download_url, "chromedriver", vendor_dir): return False
    print("-" * 20)

    if platform_system.startswith("linux") or platform_system.startswith("darwin"):
        if os.path.exists(target_chromedriver_exe_path):
            print(f"Setting execute permission for: {target_chromedriver_exe_path}")
            try:
                current_mode = os.stat(target_chromedriver_exe_path).st_mode
                os.chmod(target_chromedriver_exe_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception as e: print(f"Warning: Could not set execute permission for ChromeDriver: {e}")
        else: print(f"Error: Expected ChromeDriver not found after extraction: {target_chromedriver_exe_path}"); return False
            
    print("Bundled Chrome and ChromeDriver setup complete.")
    return True
# --- End of setup_bundled_chrome definition ---

_WINREG_AVAILABLE = False
if os.name == 'nt':
    try:
        import winreg
        _WINREG_AVAILABLE = True
    except ImportError:
        print("Module 'winreg' could not be imported. Registry lookup will be unavailable.")

def _get_hive_name_for_logging(hive_constant):
    if not _WINREG_AVAILABLE: return str(hive_constant)
    if hive_constant == winreg.HKEY_LOCAL_MACHINE: return "HKEY_LOCAL_MACHINE"
    if hive_constant == winreg.HKEY_CURRENT_USER: return "HKEY_CURRENT_USER"
    return str(hive_constant)

def find_chrome_executable_on_windows():
    if not os.name == 'nt': return None
    chrome_path = None
    if _WINREG_AVAILABLE:
        registry_keys_to_check = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
        ]
        for hive, subkey_path in registry_keys_to_check:
            try:
                with winreg.OpenKey(hive, subkey_path) as reg_key:
                    path_from_registry, _ = winreg.QueryValueEx(reg_key, None)
                    if path_from_registry and os.path.exists(path_from_registry):
                        print(f"Found system Chrome via registry: ({_get_hive_name_for_logging(hive)}\\{subkey_path}): {path_from_registry}")
                        chrome_path = path_from_registry
                        break
            except FileNotFoundError: continue
            except Exception as e: print(f"Error reading registry key {_get_hive_name_for_logging(hive)}\\{subkey_path}: {e}"); continue
        if chrome_path: return chrome_path
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
    local_app_data = os.environ.get("LOCALAPPDATA")
    potential_default_paths = [
        os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
    ]
    if local_app_data: potential_default_paths.append(os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"))
    for path in potential_default_paths:
        if os.path.exists(path): print(f"Found system Chrome in common default location: {path}"); chrome_path = path; break
    if chrome_path: return chrome_path
    try:
        path_from_which = shutil.which("chrome.exe")
        if path_from_which and os.path.exists(path_from_which): print(f"Found system Chrome via shutil.which (checking PATH): {path_from_which}"); return path_from_which
    except Exception as e: print(f"Error or system Chrome not found in PATH using shutil.which: {e}")
    return None

def init_browser():
    project_root = os.path.dirname(os.path.abspath(__file__))
    setup_successful = setup_bundled_chrome(project_root, force_download=False) 
    if not setup_successful:
        print("Automated setup of bundled Chrome FAILED. Please check errors above. Proceeding with fallback methods if possible.")

    browser_options = Options()
    options = [
        '--disable-blink-features', '--no-sandbox', '--start-maximized',
        '--disable-extensions', '--ignore-certificate-errors',
        '--disable-blink-features=AutomationControlled', '--remote-debugging-port=9222'
    ]
    user_data_dir = os.path.join(os.getcwd(), "chrome_bot")
    browser_options.add_argument(f"user-data-dir={user_data_dir}")
    for option in options: browser_options.add_argument(option)

    platform_system = sys.platform 
    platform_machine = platform.machine()

    chrome_dir_name, chromedriver_dir_name, chrome_exe_name, chromedriver_exe_name = "", "", "", ""
    mac_arch_suffix = "arm64" 

    if platform_system.startswith("win"):
        chrome_dir_name, chromedriver_dir_name, chrome_exe_name, chromedriver_exe_name = "chrome-win64", "chromedriver-win64", "chrome.exe", "chromedriver.exe"
    elif platform_system.startswith("linux"):
        if platform_machine == "x86_64":
            chrome_dir_name, chromedriver_dir_name, chrome_exe_name, chromedriver_exe_name = "chrome-linux64", "chromedriver-linux64", "chrome", "chromedriver"
    elif platform_system.startswith("darwin"):
        if platform_machine == "x86_64": mac_arch_suffix = "x64"
        chrome_dir_name = f"chrome-mac-{mac_arch_suffix}"
        chromedriver_dir_name = f"chromedriver-mac-{mac_arch_suffix}"
        chrome_exe_name = os.path.join("Google Chrome for Testing.app", "Contents", "MacOS", "Google Chrome for Testing")
        chromedriver_exe_name = "chromedriver"

    bundled_chrome_binary_path = ""
    if chrome_dir_name and chrome_exe_name:
        bundled_chrome_binary_path = os.path.join(project_root, "vendor", "chrome_for_testing", chrome_dir_name, chrome_exe_name)

    bundled_chromedriver_path = ""
    if chromedriver_dir_name and chromedriver_exe_name:
        bundled_chromedriver_path = os.path.join(project_root, "vendor", "chrome_for_testing", chromedriver_dir_name, chromedriver_exe_name)
    
    service = None
    final_chrome_binary_path_to_use = None 

    if bundled_chrome_binary_path and bundled_chromedriver_path and \
       os.path.exists(bundled_chrome_binary_path) and os.path.exists(bundled_chromedriver_path):
        print(f"Attempting to use (potentially just downloaded/verified) bundled Chrome from: {bundled_chrome_binary_path}")
        print(f"Attempting to use (potentially just downloaded/verified) bundled ChromeDriver from: {bundled_chromedriver_path}")
        browser_options.binary_location = bundled_chrome_binary_path
        final_chrome_binary_path_to_use = bundled_chrome_binary_path
        try:
            service = ChromeService(executable_path=bundled_chromedriver_path)
            print("Service initialized with bundled ChromeDriver.")
        except Exception as e:
            print(f"Error initializing service with bundled ChromeDriver (even if files exist): {e}. Falling back...")
            service = None 
            final_chrome_binary_path_to_use = None 
            browser_options.binary_location = None 
    else:
        print("Bundled Chrome/ChromeDriver executables not found at expected paths. Will try system/fallback.")
        browser_options.binary_location = None

    if service is None: 
        print("Attempting fallback: System Chrome / ChromeDriver via Manager.")
        browser_options.binary_location = None 
        final_chrome_binary_path_to_use = None

        if os.name == 'nt': 
            system_chrome_path = find_chrome_executable_on_windows()
            if system_chrome_path:
                print(f"Found system Chrome (Windows): {system_chrome_path}")
                browser_options.binary_location = system_chrome_path
                final_chrome_binary_path_to_use = system_chrome_path
            else:
                print("System Chrome not found on Windows via specific search. WebDriver will try PATH.")
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            print("Attempting to use ChromeDriver via webdriver-manager...")
            service = ChromeService(ChromeDriverManager().install())
            if final_chrome_binary_path_to_use is None and browser_options.binary_location:
                 final_chrome_binary_path_to_use = browser_options.binary_location
            
            if final_chrome_binary_path_to_use:
                 print(f"webdriver-manager is expected to find a driver for Chrome at: {final_chrome_binary_path_to_use}")
            else:
                 print(f"webdriver-manager is expected to find a driver for the default system Chrome (from PATH).")

        except ImportError:
            print("webdriver-manager not installed. Critical if bundled setup also failed.")
            raise Exception("ChromeDriver setup failed: webdriver-manager not available AND bundled driver not used/found.")
        except Exception as e:
            print(f"Error setting up ChromeDriver with webdriver-manager: {e}")
            raise Exception(f"ChromeDriver setup failed during fallback: {e}")

    driver = None
    try:
        if service:
            effective_binary_location = final_chrome_binary_path_to_use if final_chrome_binary_path_to_use else "Default (from PATH or WebDriver choice)"
            print(f"Initializing WebDriver with Chrome binary effectively at: {effective_binary_location}")
            if final_chrome_binary_path_to_use : 
                 browser_options.binary_location = final_chrome_binary_path_to_use
            
            driver = webdriver.Chrome(service=service, options=browser_options)
            print("WebDriver initialized successfully!")
            driver.implicitly_wait(1)
            driver.set_window_position(0, 0)
            driver.maximize_window()
        else:
            raise Exception("ChromeService could not be configured.")
    except Exception as e:
        print(f"WebDriver final initialization failed: {e}")
        is_windows_edge_error = (os.name == 'nt' and
                                 final_chrome_binary_path_to_use is None and
                                 (browser_options.binary_location is None) and 
                                 "Edg/" in str(e))
        if is_windows_edge_error:
            print("Error suggests WebDriver might be incorrectly using Microsoft Edge. No specific Chrome binary was successfully configured or found in PATH.")
        raise
        
    return driver

def validate_yaml():
    with open("config.yaml", 'r', encoding='utf-8') as stream:
        try:
            parameters = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise exc

    mandatory_params = ['email',
                        'password',
                        'disableAntiLock',
                        'remote',
                        'lessthanTenApplicants',
                        'newestPostingsFirst',
                        'experienceLevel',
                        'jobTypes',
                        'date',
                        'positions',
                        'locations',
                        'residentStatus',
                        'distance',
                        'outputFileDirectory',
                        'checkboxes',
                        'universityGpa',
                        'languages',
                        'experience',
                        'personalInfo',
                        'eeo',
                        'uploads']

    for mandatory_param in mandatory_params:
        if mandatory_param not in parameters:
            raise Exception(mandatory_param + ' is not defined in the config.yaml file!')

    assert validate_email(parameters['email'])
    assert len(str(parameters['password'])) > 0
    assert isinstance(parameters['disableAntiLock'], bool)
    assert isinstance(parameters['remote'], bool)
    assert isinstance(parameters['lessthanTenApplicants'], bool)
    assert isinstance(parameters['newestPostingsFirst'], bool)
    assert isinstance(parameters['residentStatus'], bool)
    assert len(parameters['experienceLevel']) > 0
    experience_level = parameters.get('experienceLevel', [])
    at_least_one_experience = False

    for key in experience_level.keys():
        if experience_level[key]:
            at_least_one_experience = True
    assert at_least_one_experience

    assert len(parameters['jobTypes']) > 0
    job_types = parameters.get('jobTypes', [])
    at_least_one_job_type = False
    for key in job_types.keys():
        if job_types[key]:
            at_least_one_job_type = True

    assert at_least_one_job_type
    assert len(parameters['date']) > 0
    date = parameters.get('date', [])
    at_least_one_date = False

    for key in date.keys():
        if date[key]:
            at_least_one_date = True
    assert at_least_one_date

    approved_distances = {0, 5, 10, 25, 50, 100}
    assert parameters['distance'] in approved_distances
    assert len(parameters['positions']) > 0
    assert len(parameters['locations']) > 0
    assert len(parameters['uploads']) >= 1 and 'resume' in parameters['uploads']
    assert len(parameters['checkboxes']) > 0

    checkboxes = parameters.get('checkboxes', [])
    assert isinstance(checkboxes['driversLicence'], bool)
    assert isinstance(checkboxes['requireVisa'], bool)
    assert isinstance(checkboxes['legallyAuthorized'], bool)
    assert isinstance(checkboxes['certifiedProfessional'], bool)
    assert isinstance(checkboxes['urgentFill'], bool)
    assert isinstance(checkboxes['commute'], bool)
    assert isinstance(checkboxes['backgroundCheck'], bool)
    assert isinstance(checkboxes['securityClearance'], bool)
    assert 'degreeCompleted' in checkboxes
    assert isinstance(parameters['universityGpa'], (int, float))

    languages = parameters.get('languages', [])
    language_types = {'none', 'conversational', 'professional', 'native or bilingual'}
    for language in languages:
        assert languages[language].lower() in language_types

    experience = parameters.get('experience', [])
    for tech in experience:
        assert isinstance(experience[tech], int)
    assert 'default' in experience

    assert len(parameters['personalInfo'])
    personal_info = parameters.get('personalInfo', [])
    for info in personal_info:
        assert personal_info[info] != ''

    assert len(parameters['eeo'])
    eeo = parameters.get('eeo', [])
    for survey_question in eeo:
        assert eeo[survey_question] != ''

    if parameters.get('openaiApiKey') == 'sk-proj-your-openai-api-key':
        parameters['openaiApiKey'] = None

    return parameters


if __name__ == '__main__':
    parameters = validate_yaml()
    browser = None
    try:
        browser = init_browser()
    except Exception as e:
        print(f"Critical error during browser initialization: {e}")

    if browser is None:
        print("Script cannot continue due to browser initialization failure. Please check the error messages above.")
    else:
        bot = LinkedinEasyApply(parameters, browser)
        bot.login()
        bot.security_check()
        bot.start_applying()
