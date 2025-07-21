import schedule
import time
import subprocess
import os
import logging
from datetime import datetime

# --- Configuration ---
# Add all user configuration file paths here
USER_CONFIGS = [
    "config.yaml",
    # "config_user2.yaml",  # Example: uncomment this line to add a second user
    # "config_user3.yaml",
]

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
        return

    logging.info(f"--- Starting job for user (config: {config_file}) ---")
    
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
                logging.info(output.strip())
        
        # Check the return code
        return_code = process.poll()
        if return_code == 0:
            logging.info(f"Successfully completed job for user (config: {config_file}).")
        else:
            logging.error(f"Job for user (config: {config_file}) failed with return code: {return_code}")

    except Exception as e:
        logging.error(f"An unexpected error occurred while running the job for user (config: {config_file}): {e}")
        
    finally:
        logging.info(f"--- Finished job for user (config: {config_file}) ---")
        time.sleep(10) # Add a short delay between users

def job():
    """
    The main function for the scheduled job, which will execute tasks for all users sequentially.
    """
    logging.info(f"====== Starting a new round of scheduled jobs ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ======")
    if not USER_CONFIGS:
        logging.warning("User config list is empty. No jobs to run in this round.")
        return

    for config in USER_CONFIGS:
        run_bot_for_user(config)

    logging.info(f"====== All jobs for this round have been executed. Next run at: {schedule.next_run} ======")

if __name__ == "__main__":
    logging.info("Scheduler script started.")
    logging.info(f"User configs to be executed: {USER_CONFIGS}")
    
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