# =========================
# ===== KONFIGURACJA =====
# =========================

URL = "https://127.0.0.1:8181/doc/index.html#/process/workplace1"
CSS_SELECTOR = ".value.currentProcessWorkpiece"
READ_INTERVAL_SEC = 1
PAGE_LOAD_TIMEOUT = 5
ELEMENT_TIMEOUT = 5
HTML_LOG_FILE = "last_page.html"  # plik do zapisu ostatniego HTML

CHROMEDRIVER_PATH = "./chromedriver.exe"
CHROME_BINARY_PATH = "./chrome-win64/chrome.exe"

# =========================
# =====   IMPORTY    =====
# =========================

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# =========================
# =====  FUNKCJE     =====
# =========================

def format_to_3_digits(value: str):
    """Konwertuje tekst na 3-cyfrowy string, brak -> None"""
    if not value or value == "---":
        return None

    try:
        number = int(value)
        return f"{number:03d}"   # dopełnienie zerami
    except ValueError:
        return None

def save_html(driver):
    """Zapisuje aktualny HTML do pliku"""
    try:
        with open(HTML_LOG_FILE, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    except Exception as e:
        print("Nie udało się zapisać HTML:", e)

# =========================
# =====  MAIN LOOP  ======
# =========================

def main():

    options = Options()
    options.binary_location = CHROME_BINARY_PATH
    # options.add_argument("--headless=new")  # odkomentuj jeśli chcesz w tle
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = None
    last_value = None

    print("Start systemu testowego...")

    while True:
        if driver is None:
            try:
                service = Service(CHROMEDRIVER_PATH)
                driver = webdriver.Chrome(service=service, options=options)
                driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
                driver.get(URL)

                wait = WebDriverWait(driver, ELEMENT_TIMEOUT)
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, CSS_SELECTOR))
                )

                print("Selenium OK, rozpoczęto odczyt...")

            except Exception as e:
                print("Błąd startu Selenium:", e)
                if driver:
                    try: driver.quit()
                    except: pass
                driver = None
                time.sleep(5)
                continue

        try:
            element = driver.find_element(By.CSS_SELECTOR, CSS_SELECTOR)
            raw_value = element.text.strip()
            formatted_value = format_to_3_digits(raw_value)

            # zapis HTML dla debug
            save_html(driver)

            if formatted_value != last_value:
                print("WORKPIECE NUMBER:", formatted_value)
                last_value = formatted_value

            time.sleep(READ_INTERVAL_SEC)

        except Exception as e:
            print("Watchdog Selenium, błąd odczytu:", e)
            try:
                driver.quit()
            except: pass
            driver = None
            time.sleep(5)

# =========================
# ===== ENTRY POINT ======
# =========================

if __name__ == "__main__":
    main()