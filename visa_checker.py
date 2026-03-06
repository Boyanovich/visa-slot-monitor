import time
import os
import requests
import whisper
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN_HERE"
SUBSCRIBERS_FILE = "subscribers.txt"

# IMPORTANT: This link is dynamic and bound to a user session. 
# For a real run, you must authorize on the website and insert the actual URL with the token (?t=...)
URL_TO_CHECK = "https://italyvms.com/autoform/?action=reschedule"
DRIVER_PATH = "C:\\webdriver\\chromedriver.exe" 
CHROME_PROFILE_PATH = "C:/chrome_profile_for_bot"

class BlockException(Exception):
    def __init__(self, message, delay, error_type):
        super().__init__(message)
        self.delay = delay
        self.error_type = error_type

def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            subscribers = [line.strip() for line in f if line.strip().isdigit()]
        if not subscribers: 
            raise ValueError("File is empty.")
        return subscribers
    except Exception as e:
        print(f"Error loading subscribers: {e}. Using default ID.")
        return ["606388605"]

def send_telegram_message(message, screenshot_path=None):
    CHAT_IDS = load_subscribers()
    bot_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    photo_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    photo_data = None
    
    if screenshot_path and os.path.exists(screenshot_path):
        try:
            with open(screenshot_path, 'rb') as photo_file: 
                photo_data = photo_file.read()
        except Exception as e:
            print(f"Error reading screenshot: {e}")
    
    for chat_id in CHAT_IDS:
        try:
            requests.post(bot_url, params={"chat_id": chat_id, "text": message}, timeout=30)
            if photo_data:
                requests.post(photo_url, files={'photo': ('screenshot.png', photo_data)}, data={'chat_id': chat_id}, timeout=30)
        except Exception as e:
            print(f"Error sending message to user {chat_id}: {e}")

def check_for_block(driver, error_type_to_check, in_iframe=False):
    time.sleep(1)
    if not in_iframe:
        try: driver.switch_to.default_content()
        except: pass
        
    page_source = driver.page_source.lower()
    is_blocked = False
    delay = 1500 # Base delay of 25 minutes

    # Target website outputs strings in Russian, keeping the triggers as they are
    if error_type_to_check == "too_many" and "слишком много запросов" in page_source:
        is_blocked = True
    elif error_type_to_check == "auto_requests" and any(p in page_source for p in ["повторите попытку позже", "автоматически отправляют запросы"]):
        is_blocked = True

    if is_blocked:
        print(f"Block detected: {error_type_to_check}. Pausing for {delay//60} minutes.")
        raise BlockException(f"Block detected: {error_type_to_check}", delay=delay, error_type=error_type_to_check)

def solve_single_audio_captcha(driver, wait, whisper_model):
    print("Switching to captcha iframe...")
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[contains(@src, 'recaptcha/api2/bframe')]")))
    
    try:
        short_wait = WebDriverWait(driver, 3)
        audio_src = short_wait.until(EC.presence_of_element_located((By.ID, "audio-source"))).get_attribute('src')
    except TimeoutException:
        wait.until(EC.element_to_be_clickable((By.ID, "recaptcha-audio-button"))).click()
        check_for_block(driver, "auto_requests", in_iframe=True)
        audio_src = wait.until(EC.presence_of_element_located((By.ID, "audio-source"))).get_attribute('src')

    print("Downloading and transcribing audio challenge...")
    doc = requests.get(audio_src, stream=True)
    with open("captcha.mp3", "wb") as f: 
        f.write(doc.content)
    
    result = whisper_model.transcribe("captcha.mp3", fp16=False)
    recognized_text = result["text"].strip().lower()
    
    if not recognized_text:
        raise Exception("Recognized text is empty.")

    wait.until(EC.element_to_be_clickable((By.ID, "audio-response"))).send_keys(recognized_text)
    wait.until(EC.element_to_be_clickable((By.ID, "recaptcha-verify-button"))).click()
    
    driver.switch_to.default_content()
    print("Captcha successfully solved.")
    return True

if __name__ == "__main__":
    try:
        print("Loading Whisper model...")
        whisper_model = whisper.load_model("base")
    except Exception as e:
        print(f"Critical error loading Whisper model: {e}")
        exit()

    driver = None
    send_telegram_message("🤖 Visa slot monitoring bot has started.")
    
    try:
        while True:
            current_run_error = False
            delay = random.randint(180, 360)
            
            try:
                print("\n--- Starting a new check cycle ---")
                options = uc.ChromeOptions()
                options.add_argument("profile-directory=Default")
                options.add_argument("--lang=en-US")
                driver = uc.Chrome(options=options, user_data_dir=CHROME_PROFILE_PATH, driver_executable_path=DRIVER_PATH)
                
                driver.get(URL_TO_CHECK)
                wait = WebDriverWait(driver, 30)

                check_for_block(driver, "too_many")
                check_for_block(driver, "auto_requests")

                print("Clicking 'I am not a robot' checkbox...")
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[contains(@src, 'recaptcha/api2/anchor')]")))
                wait.until(EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))).click()
                driver.switch_to.default_content()
                
                time.sleep(5) 
                # Target website outputs strings in Russian
                if "пожалуйста, введите капчу" in driver.page_source.lower():
                    solve_single_audio_captcha(driver, wait, whisper_model)

                print("Analyzing page for available slots...")
                time.sleep(5)
                page_text = driver.page_source.lower()
                screenshot_path = "screenshot.png"
                driver.save_screenshot(screenshot_path)

                # Target website outputs strings in Russian
                if any(p in page_text for p in ["на ближайшие 2 недели записи нет", "нет подходящих временных интервалов"]):
                    print("No slots available. Waiting for the next cycle.")
                else:
                    print("!!! CHANGES DETECTED !!!")
                    send_telegram_message("🚨 ATTENTION! SLOTS MIGHT BE AVAILABLE!", screenshot_path)

            except BlockException as e:
                current_run_error = True
                delay = e.delay
            except Exception as e:
                print(f"Error during execution cycle: {e}")
                current_run_error = True
                delay = 300
            finally:
                if driver:
                    try: driver.quit()
                    except: pass
            
            print(f"Next check in {delay / 60:.1f} minutes.")
            time.sleep(delay)

    except KeyboardInterrupt:
        print("\nProcess manually stopped by user.")
    finally:
        if driver:
            try: driver.quit()
            except: pass