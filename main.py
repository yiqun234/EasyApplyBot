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
import subprocess # Added for get_chrome_version
import re # Added for get_chrome_version

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
        else: print(f"Unsupported macOS architecture: {platform_machine}"); return False, None, None, None
        json_platform_key_chrome = f"mac-{mac_arch_suffix}"
        json_platform_key_driver = f"mac-{mac_arch_suffix}"
        chrome_dir_name, chromedriver_dir_name = f"chrome-mac-{mac_arch_suffix}", f"chromedriver-mac-{mac_arch_suffix}"
        chrome_exe_name = os.path.join("Google Chrome for Testing.app", "Contents", "MacOS", "Google Chrome for Testing")
        chromedriver_exe_name = "chromedriver"

    if not (json_platform_key_chrome and chrome_dir_name and chrome_exe_name):
        print(f"Unsupported platform/arch for auto-download: system='{platform_system}', machine='{platform_machine}'")
        return False, None, None, None

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
        return True, target_chrome_exe_path, target_chromedriver_exe_path, None

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
            return False, None, None, None

    if not versions_data:
        print("Failed to obtain version information from any source.")
        return False, None, None, None

    stable_channel_data = versions_data.get("channels", {}).get("Stable", {})
    if not stable_channel_data:
        print("Could not find 'Stable' channel data in the version information.")
        return False, None, None, None

    chrome_version_from_json = stable_channel_data.get("version")
    if not chrome_version_from_json:
        print("Could not find 'version' in Stable channel data.")
        return False, None, None, None

    chrome_download_url, chromedriver_download_url = None, None
    for item in stable_channel_data.get("downloads", {}).get("chrome", []):
        if item.get("platform") == json_platform_key_chrome: chrome_download_url = item.get("url"); break
    for item in stable_channel_data.get("downloads", {}).get("chromedriver", []):
        if item.get("platform") == json_platform_key_driver: chromedriver_download_url = item.get("url"); break

    if not chrome_download_url: print(f"Could not find Chrome download URL for {json_platform_key_chrome}"); return False, None, None, None
    if not chromedriver_download_url: print(f"Could not find ChromeDriver URL for {json_platform_key_driver}"); return False, None, None, None

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
    if not _download_and_extract_zip(chrome_download_url, "chrome", vendor_dir): return False, None, None, None
    print("-" * 20); print("Processing ChromeDriver...")
    if not _download_and_extract_zip(chromedriver_download_url, "chromedriver", vendor_dir): return False, None, None, None
    print("-" * 20)

    if platform_system.startswith("linux") or platform_system.startswith("darwin"):
        if os.path.exists(target_chromedriver_exe_path):
            print(f"Setting execute permission for: {target_chromedriver_exe_path}")
            try:
                current_mode = os.stat(target_chromedriver_exe_path).st_mode
                os.chmod(target_chromedriver_exe_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception as e: print(f"Warning: Could not set execute permission for ChromeDriver: {e}")
        else:
            print(f"Error: Expected ChromeDriver not found after extraction: {target_chromedriver_exe_path}")
            return False, None, None, None

    print(f"Bundled Chrome and ChromeDriver setup complete. Chrome version from JSON: {chrome_version_from_json}")
    return True, target_chrome_exe_path, target_chromedriver_exe_path, chrome_version_from_json
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

# Function to get Chrome version from Windows Registry (HKEY_CURRENT_USER)
def _get_chrome_version_from_registry_windows():
    if not _WINREG_AVAILABLE:
        return None
    try:
        key_path = r"Software\\Google\\Chrome\\BLBeacon"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            version_string_raw, _ = winreg.QueryValueEx(key, "version")
            if version_string_raw:
                version_string = str(version_string_raw).strip() # Ensure string and strip
                print(f"Registry: Found Chrome version string (raw: '{version_string_raw}', stripped: '{version_string}')")

                # Try full match for X.Y.Z.W
                match_full_strict = re.fullmatch(r"(\d+\.\d+\.\d+\.\d+)", version_string)
                if match_full_strict:
                    print(f"Registry: Matched full version (X.Y.Z.W) using re.fullmatch: {match_full_strict.group(1)}")
                    return match_full_strict.group(1)

                # Try full match for X.Y.Z
                match_short_strict = re.fullmatch(r"(\d+\.\d+\.\d+)", version_string)
                if match_short_strict:
                    print(f"Registry: Matched short version (X.Y.Z) using re.fullmatch: {match_short_strict.group(1)}")
                    return match_short_strict.group(1)
                
                print(f"Registry: re.fullmatch failed for '{version_string}'. Trying re.search...")

                # Fallback to re.search for X.Y.Z.W
                match_full_search = re.search(r"(\d+\.\d+\.\d+\.\d+)", version_string)
                if match_full_search:
                    print(f"Registry: Matched full version (X.Y.Z.W) using re.search: {match_full_search.group(1)}")
                    return match_full_search.group(1)

                # Fallback to re.search for X.Y.Z
                match_short_search = re.search(r"(\d+\.\d+\.\d+)", version_string)
                if match_short_search:
                    print(f"Registry: Matched short version (X.Y.Z) using re.search: {match_short_search.group(1)}")
                    return match_short_search.group(1)
                
                print(f"Registry: Could not parse version from string '{version_string}' using any known regex patterns.")
        return None
    except FileNotFoundError:
        print(f"Chrome version key (HKEY_CURRENT_USER\\\\{key_path}\\\\version) not found in registry. Will try other methods.")
        return None
    except Exception as e:
        print(f"Warning: Error reading Chrome version from registry (HKEY_CURRENT_USER\\\\{key_path}\\\\version): {e}. Will try other methods.")
        return None

def get_chrome_version(chrome_exe_path):
    """Gets the version of Chrome from Windows registry (preferred) or its executable."""
    if os.name == 'nt': # Check if on Windows
        print("Attempting to get Chrome version from Windows registry...")
        reg_version = _get_chrome_version_from_registry_windows()
        if reg_version:
            print(f"Successfully retrieved Chrome version from registry: {reg_version}")
            return reg_version
        else:
            print("Failed to get Chrome version from registry or version format not fully recognized, falling back to command line '--version'.")

    # Existing logic for --version
    if not chrome_exe_path or not os.path.exists(chrome_exe_path):
        print(f"Chrome executable not found at path: {chrome_exe_path} (for version check)")
        return None
    try:
        command = [chrome_exe_path, "--version"]
        print(f"CMD: Attempting to get Chrome version with command: {' '.join(command)}")

        # Fetch raw bytes to handle encoding issues better, especially on Windows.
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_bytes, stderr_bytes = process.communicate(timeout=15)

        output = ""
        decoded_from = ""

        if stdout_bytes:
            print(f"CMD: Raw stdout: {stdout_bytes}")
            try:
                output = stdout_bytes.decode('utf-8').strip()
                decoded_from = "stdout, utf-8"
            except UnicodeDecodeError:
                try:
                    import locale
                    console_encoding = locale.getpreferredencoding(False)
                    print(f"CMD: UTF-8 decode failed for stdout. Trying console encoding: {console_encoding}")
                    output = stdout_bytes.decode(console_encoding).strip()
                    decoded_from = f"stdout, {console_encoding}"
                except Exception: # Broad exception for other decode errors or if locale fails
                    try:
                        print(f"CMD: Console encoding ({console_encoding}) failed for stdout. Trying cp1252.")
                        output = stdout_bytes.decode('cp1252').strip()
                        decoded_from = "stdout, cp1252"
                    except UnicodeDecodeError:
                        print(f"CMD: cp1252 decode failed for stdout. Using utf-8 with replace.")
                        output = stdout_bytes.decode('utf-8', errors='replace').strip()
                        decoded_from = "stdout, utf-8 with replace"
        
        if not output and stderr_bytes: # If no output from stdout, try stderr
            print(f"CMD: Raw stderr: {stderr_bytes}")
            try:
                output = stderr_bytes.decode('utf-8').strip()
                decoded_from = "stderr, utf-8"
            except UnicodeDecodeError:
                try:
                    import locale
                    console_encoding = locale.getpreferredencoding(False)
                    print(f"CMD: UTF-8 decode failed for stderr. Trying console encoding: {console_encoding}")
                    output = stderr_bytes.decode(console_encoding).strip()
                    decoded_from = f"stderr, {console_encoding}"
                except Exception:
                    try:
                        print(f"CMD: Console encoding ({console_encoding}) failed for stderr. Trying cp1252.")
                        output = stderr_bytes.decode('cp1252').strip()
                        decoded_from = "stderr, cp1252"
                    except UnicodeDecodeError:
                        print(f"CMD: cp1252 decode failed for stderr. Using utf-8 with replace.")
                        output = stderr_bytes.decode('utf-8', errors='replace').strip()
                        decoded_from = "stderr, utf-8 with replace"
        
        if output:
            print(f"CMD: Decoded output ('{decoded_from}'): '{output}'")
        else:
            print(f"CMD: No version output after attempting decodes.")

        if process.returncode != 0 and not output:
             print(f"Command '{' '.join(command)}' failed with return code {process.returncode} and no version output.")
             return None

        # print(f"Raw version output from '{' '.join(command)}': '{output}'") # Optional: for debugging
        # Expected: "Google Chrome 123.0.1234.56" or "Chromium 123.0.1234.56 ..." or just "123.0.1234.56"
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)", output) # Full version X.Y.Z.W
        if match:
            version = match.group(1)
            # print(f"Detected Chrome version (full): {version}") # Optional: for debugging
            return version
        else:
            # Try matching X.Y.Z if full version not found (e.g. some builds/outputs)
            match_short = re.search(r"(\d+\.\d+\.\d+)", output)
            if match_short:
                version = match_short.group(1)
                # print(f"Detected Chrome version (short): {version}") # Optional: for debugging
                return version
            print(f"Could not parse version from output: '{output}' using command '{' '.join(command)}'")
            return None
    except FileNotFoundError:
        print(f"Error: Chrome executable not found at {chrome_exe_path} when trying to run --version.")
        return None
    except subprocess.TimeoutExpired:
        print(f"Timeout while trying to get Chrome version from {chrome_exe_path} using --version.")
        return None
    except Exception as e:
        print(f"Error getting Chrome version from {chrome_exe_path} using --version: {e}")
        return None

def find_chrome_executable_on_windows():
    if not os.name == 'nt': return None
    chrome_path = None
    if _WINREG_AVAILABLE:
        registry_keys_to_check = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chrome.exe"),
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chrome.exe"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chrome.exe"),
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
    program_files = os.environ.get("ProgramFiles", "C:\\\\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\\\Program Files (x86)")
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
    browser_options = Options()
    project_root = os.getcwd() # For setup_bundled_chrome path context



    # --- Chrome Options ---
    # --remote-debugging-port=9222 is INCLUDED to allow reusing an existing browser session
    # if launched with the same user-data-dir. This helps avoid re-logins during development/testing.
    options_to_add = [
        '--disable-blink-features', # Generic, often combined with AutomationControlled
        '--no-sandbox', # Essential for some Linux environments / Docker
        '--start-maximized', # Starts browser maximized
        '--disable-extensions', # Disables extensions, good for automation
        '--ignore-certificate-errors', # Ignores certificate errors
        '--disable-blink-features=AutomationControlled', # Helps avoid bot detection
        '--remote-debugging-port=9270', # INCLUDED to enable session reuse
    ]

    user_data_dir = os.path.join(os.getcwd(), "chrome_bot")
    print(f"Chrome User Data Directory: {user_data_dir}")
    browser_options.add_argument(f"user-data-dir={user_data_dir}")

    for option in options_to_add:
        browser_options.add_argument(option)

    service = None
    final_chrome_binary_path = None # Store the decided Chrome binary path for logging


    # The force_download parameter for setup_bundled_chrome could be True during initial setup
    # or if specified by user, e.g., via a config parameter like parameters.get("force_download_bundled_chrome", False)
    print("\nStep 1: Attempting to use System Chrome with version-matched ChromeDriver...")
    system_chrome_exe_path = None
    if os.name == 'nt':
        system_chrome_exe_path = find_chrome_executable_on_windows()  # This function already prints findings
    else:  # Linux/macOS
        common_names = ["google-chrome", "google-chrome-stable", "chrome", "chromium-browser", "chromium"]
        for name in common_names:
            found_path = shutil.which(name)
            if found_path:
                system_chrome_exe_path = found_path
                print(f"Found system Chrome via shutil.which: {system_chrome_exe_path}")
                break
        if not system_chrome_exe_path and platform.system() == "Darwin":  # macOS specific check
            macos_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(macos_path):
                system_chrome_exe_path = macos_path
                print(f"Found system Chrome in default macOS location: {system_chrome_exe_path}")

    if system_chrome_exe_path and os.path.exists(system_chrome_exe_path):
        browser_options.binary_location = system_chrome_exe_path
        final_chrome_binary_path = system_chrome_exe_path
        print(f"Using System Chrome binary: {final_chrome_binary_path}")

        detected_sys_chrome_version = get_chrome_version(system_chrome_exe_path)
        if detected_sys_chrome_version:
            print(
                f"Detected System Chrome version: {detected_sys_chrome_version}. Attempting to get matching ChromeDriver via webdriver-manager.")
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                driver_install_path = ChromeDriverManager(driver_version=detected_sys_chrome_version).install()
                service = ChromeService(executable_path=driver_install_path)
                print(
                    f"webdriver-manager: ChromeDriver for version {detected_sys_chrome_version} installed at: {driver_install_path}")
            except ImportError:
                print("webdriver-manager not installed. Cannot download version-specific driver for system Chrome.")
            except Exception as e_wdm_ver:
                print(
                    f"webdriver-manager: Error installing ChromeDriver for version {detected_sys_chrome_version}: {e_wdm_ver}")
                print("Will attempt generic ChromeDriver download as a further fallback.")
        else:
            print("Could not detect version of System Chrome. Will attempt generic ChromeDriver download.")
    else:
        print("System Chrome executable not found. WebDriver will try PATH for Chrome.")
        final_chrome_binary_path = None  # Let webdriver find Chrome
        browser_options.binary_location = None  # Ensure it's not set from a failed previous attempt


    # --- Attempt 2: System Chrome with Version-Matched ChromeDriver ---
    if service is None:
        # --- Attempt 2: Bundled Chrome for Testing ---
        # This assumes setup_bundled_chrome is robust and handles downloads/updates.
        # A flag in config.yaml could control whether to attempt using bundled chrome.
        # For now, we'll always attempt it if this logic is active.
        print("Step 2: Attempting to use Bundled Chrome for Testing...")
        setup_success, bundled_c_path, bundled_cd_path, bundled_c_ver = setup_bundled_chrome(project_root,
                                                                                             force_download=False)

        if setup_success and bundled_c_path and bundled_cd_path and os.path.exists(bundled_c_path) and os.path.exists(
                bundled_cd_path):
            print(f"Successfully prepared Bundled Chrome: {bundled_c_path} (Version from JSON: {bundled_c_ver})")
            print(f"Using Bundled ChromeDriver: {bundled_cd_path}")
            browser_options.binary_location = bundled_c_path
            final_chrome_binary_path = bundled_c_path
            try:
                service = ChromeService(executable_path=bundled_cd_path)
                print("Service configured with Bundled ChromeDriver.")
            except Exception as e_bundle_service:
                print(f"Error setting up service with Bundled ChromeDriver ({bundled_cd_path}): {e_bundle_service}")
                print("Will proceed to System Chrome fallback.")
                service = None  # Ensure fallback
                final_chrome_binary_path = None
                browser_options.binary_location = None  # Reset
        else:
            print("Bundled Chrome setup failed or paths invalid. Proceeding to System Chrome fallback.")

    # --- Attempt 3: Generic ChromeDriver (if specific attempts failed) ---
    if service is None:
        print("\nStep 3: Attempting generic ChromeDriver download via webdriver-manager...")
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            if final_chrome_binary_path:
                print(f"webdriver-manager will attempt to find driver for Chrome at: {final_chrome_binary_path}")
            elif browser_options.binary_location : # Should be same as final_chrome_binary_path if set
                print(f"webdriver-manager will attempt to find driver for Chrome at: {browser_options.binary_location}")
            else:
                print("webdriver-manager will attempt to find driver for Chrome in system PATH.")

            driver_install_path = ChromeDriverManager().install()
            service = ChromeService(executable_path=driver_install_path)
            print(f"webdriver-manager: Generic ChromeDriver installed at: {driver_install_path}")
        except ImportError:
            print("CRITICAL: webdriver-manager not installed, and no other ChromeDriver setup succeeded.")
            raise Exception("ChromeDriver setup failed: webdriver-manager not available AND other methods failed.")
        except Exception as e_wdm_generic:
            print(f"CRITICAL: webdriver-manager: Error setting up generic ChromeDriver: {e_wdm_generic}")
            raise Exception(f"ChromeDriver setup failed during generic fallback: {e_wdm_generic}")

    # --- WebDriver Initialization ---
    if not service:
        print("CRITICAL: ChromeService could not be configured after all attempts.")
        raise Exception("Failed to initialize ChromeService. Cannot start browser.")

    driver = None
    try:
        effective_binary_msg = browser_options.binary_location if browser_options.binary_location else "Default (from PATH or WebDriver choice)"
        print(f"\nFinalizing WebDriver Initialization...")
        print(f"  Effective Chrome Binary: {effective_binary_msg}")
        print(f"  Using ChromeDriver: {service.path}")

        driver = webdriver.Chrome(service=service, options=browser_options)
        print("WebDriver initialized successfully!")
        driver.implicitly_wait(1) # As per original user script
        # driver.set_window_position(0, 0) # --start-maximized should handle this
        # driver.maximize_window() # --start-maximized option is used
    except Exception as e_wd_init:
        print(f"WebDriver final initialization failed: {e_wd_init}")
        is_windows_edge_error = (os.name == 'nt' and
                                 (browser_options.binary_location is None) and
                                 "Edg/" in str(e_wd_init))
        if is_windows_edge_error:
            print("Error suggests WebDriver might be incorrectly using Microsoft Edge. Ensure Chrome is in PATH or a binary is specified.")
        if "user data directory is already in use" in str(e_wd_init):
             print(f"ERROR: 'user data directory is already in use' ({user_data_dir}). This should be unique due to timestamping. \nPossible issues: Lingering Chrome processes, permissions, or system limitations.")
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

    browser = init_browser()

    if browser is None:
        print("Script cannot continue due to browser initialization failure. Please check the error messages above.")
    else:
        bot = LinkedinEasyApply(parameters, browser)
        bot.login()
        bot.security_check()
        bot.start_applying()
