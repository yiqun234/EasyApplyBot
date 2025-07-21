import schedule
import time
import subprocess
import os
import logging
import glob
from datetime import datetime

# --- Configuration ---
CONFIG_DIR = "configs"
DEFAULT_CONFIG_FILE = "config.yaml"

def get_available_user_configs():
    """Get all available user configuration files"""
    config_files = []
    
    # Add default config if it exists
    if os.path.exists(DEFAULT_CONFIG_FILE):
        config_files.append(DEFAULT_CONFIG_FILE)
    
    # Add all user configs from configs directory
    if os.path.exists(CONFIG_DIR):
        user_configs = glob.glob(os.path.join(CONFIG_DIR, "*.yaml"))
        config_files.extend(user_configs)
    
    return config_files

def get_user_id_from_config_path(config_path):
    """Extract user ID from config file path"""
    if config_path == DEFAULT_CONFIG_FILE:
        return "default"
    
    filename = os.path.basename(config_path)
    user_id = filename.replace('.yaml', '')
    return user_id

# Get user configuration files automatically
USER_CONFIGS = get_available_user_configs()

# Log file configuration
LOG_FILE = "scheduler.log"

# Main script path
MAIN_SCRIPT_PATH = "main.py"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def run_bot_for_user(config_file: str):
    """
    Runs the LinkedIn bot for a specific user configuration file.
    """
    if not os.path.exists(config_file):
        logging.error(f"Configuration file not found: {config_file}, skipping this user.")
        return False

    user_id = get_user_id_from_config_path(config_file)
    logging.info(f"--- Starting job for user '{user_id}' (config: {config_file}) ---")
    
    try:
        command = ["python", "-u", MAIN_SCRIPT_PATH, "--config", config_file]
        
        # Use subprocess.Popen to execute the command and wait for it to complete.
        # We will capture the output, print it in real-time, and write it to the log.
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            encoding='utf-8',
            errors='replace'
        )

        # Read output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                logging.info(f"[{user_id}] {output.strip()}")
        
        # Check the return code
        return_code = process.poll()
        if return_code == 0:
            logging.info(f"Successfully completed job for user '{user_id}' (config: {config_file}).")
            return True
        else:
            logging.error(f"Job for user '{user_id}' (config: {config_file}) failed with return code: {return_code}")
            return False

    except Exception as e:
        logging.error(f"An unexpected error occurred while running the job for user '{user_id}' (config: {config_file}): {e}")
        return False
        
    finally:
        logging.info(f"--- Finished job for user '{user_id}' (config: {config_file}) ---")
        time.sleep(5) # Reduced delay between users

def job():
    """
    The main function for the scheduled job, which will execute tasks for all users sequentially.
    """
    # Refresh the config list in case new users were added
    global USER_CONFIGS
    USER_CONFIGS = get_available_user_configs()
    
    logging.info(f"====== Starting a new round of scheduled jobs ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ======")
    if not USER_CONFIGS:
        logging.warning("User config list is empty. No jobs to run in this round.")
        return

    successful_jobs = 0
    failed_jobs = 0
    
    for config in USER_CONFIGS:
        user_id = get_user_id_from_config_path(config)
        logging.info(f"Processing user '{user_id}'...")
        
        try:
            success = run_bot_for_user(config)
            if success:
                successful_jobs += 1
            else:
                failed_jobs += 1
        except Exception as e:
            logging.error(f"Critical error processing user '{user_id}': {e}")
            failed_jobs += 1
        
        # Brief pause between users to avoid system overload
        time.sleep(2)

    logging.info(f"====== Round completed. Successful: {successful_jobs}, Failed: {failed_jobs}. Next run at: {schedule.next_run} ======")

if __name__ == "__main__":
    logging.info("Multi-User LinkedIn Bot Scheduler started.")
    logging.info(f"Found {len(USER_CONFIGS)} user configurations:")
    for config in USER_CONFIGS:
        user_id = get_user_id_from_config_path(config)
        logging.info(f"  - User '{user_id}': {config}")
    
    # --- Schedule Settings ---
    # This is an example: run every 2 hours.
    # You can modify the scheduling logic here as needed.
    # For example:
    # schedule.every().day.at("08:00").do(job)  # Run every day at 8:00 AM
    # schedule.every(1).to(2).hours.do(job)     # Run every 1 to 2 hours
    
    # Default schedule is to run every 2 hours
    schedule.every(2).hours.do(job)
    
    # Run the job once immediately for testing purposes
    logging.info("Running the job once immediately for testing purposes.")
    job()

    while True:
        schedule.run_pending()
        time.sleep(1) 