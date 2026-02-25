# scraper_selenium.py
# -------------------
# Odczyt danych z lokalnego serwera HTTP (np. http://<IP>:<PORT>)
# Watchdog Selenium restartuje przeglądarkę przy błędzie
# Autoreconnect PLC S7-1500
# INT zawsze 3-cyfrowy, brak/blad = 000

# =========================
# ===== KONFIGURACJA =====
# =========================

URL = "https://127.0.0.1:8181/doc/index.html#/process/workplace1"
CSS_SELECTOR = ".value.currentProcessWorkpiece"

READ_INTERVAL_SEC = 1
PLC_RECONNECT_SEC = 5
SELENIUM_RESTART_SEC = 5

PLC_IP = "192.168.0.1"
PLC_RACK = 0
PLC_SLOT = 1
PLC_DB_NUMBER = 69
PLC_DB_OFFSET = 0

CHROMEDRIVER_PATH = "./chromedriver.exe"
CHROME_BINARY_PATH = "./chrome-win64/chrome.exe"

# =========================
# ===== IMPORTY ===========
# =========================

import time
import os
import snap7
from snap7.util import set_int
from snap7.client import Client
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =========================
# ===== SELENIUM ==========
# =========================

def start_driver():
    options = Options()
    options.binary_location = CHROME_BINARY_PATH
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)  # <-- poprawione

    driver.set_page_load_timeout(5)
    driver.get(URL)

    wait = WebDriverWait(driver, 5)
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, CSS_SELECTOR))
    )

    return driver

# =========================
# ===== PLC ===============
# =========================

def connect_plc():
    plc = Client()
    plc.connect(PLC_IP, PLC_RACK, PLC_SLOT)
    return plc

def write_int(plc, value):
    data = bytearray(2)
    set_int(data, 0, value)
    plc.db_write(PLC_DB_NUMBER, PLC_DB_OFFSET, data)

# =========================
# ===== MAIN ==============
# =========================

def main():

    plc = None
    driver = None
    last_value = None

    print("Start systemu")

    while True:

        # --- PLC reconnect ---
        if plc is None or not plc.get_connected():
            try:
                print("Łączenie PLC...")
                plc = connect_plc()
                print("PLC OK")
            except Exception as e:
                print("PLC offline:", e)
                time.sleep(PLC_RECONNECT_SEC)
                continue

        # --- Selenium restart ---
        if driver is None:
            try:
                print("Start przeglądarki...")
                driver = start_driver()
                print("Selenium OK")
            except Exception as e:
                print("Błąd startu Selenium:", e)
                time.sleep(SELENIUM_RESTART_SEC)
                continue

        try:
            element = driver.find_element(By.CSS_SELECTOR, CSS_SELECTOR)
            raw = element.text.strip()

            # ==========================
            # ===== Zapis HTML ========
            # ==========================
            try:
                with open("last_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            except Exception as e:
                print("Nie udało się zapisać HTML:", e)
            # ==========================
        
            try:
                value = int(raw)
                if value < 0 or value > 999:
                    value = 0
            except:
                value = 0

            # Zawsze 3 cyfry
            value_str = f"{value:03d}"

            if value != last_value:
                print("Wysyłam:", value_str)
                write_int(plc, value)
                last_value = value

            time.sleep(READ_INTERVAL_SEC)

        except Exception as e:
            print("Watchdog Selenium:", e)

            try:
                driver.quit()
            except:
                pass

            driver = None
            time.sleep(SELENIUM_RESTART_SEC)


if __name__ == "__main__":
    main()