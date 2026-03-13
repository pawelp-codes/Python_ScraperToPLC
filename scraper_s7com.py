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
CSS_SELECTOR1 = ".value.currentProcessWorkpiece"
XPATH_SELECTOR2 = "//*[@id='app']/div/div/main/div/div[2]/div[2]/div[1]/div/table[1]/tbody/tr/td[2]"

READ_INTERVAL_SEC = 1
PLC_RECONNECT_SEC = 5
SELENIUM_RESTART_SEC = 5

PLC_IP = "192.168.0.1"
PLC_RACK = 0
PLC_SLOT = 1
PLC_DB_NUMBER = 69
PLC_DB_OFFSET1 = 0
PLC_DB_OFFSET2 = 2

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
        EC.presence_of_element_located((By.CSS_SELECTOR, CSS_SELECTOR1))
    )
    wait.until(
        EC.presence_of_element_located((By.XPATH, XPATH_SELECTOR2))
    )

    return driver

# =========================
# ===== PLC ===============
# =========================

def connect_plc():
    plc = Client()
    plc.connect(PLC_IP, PLC_RACK, PLC_SLOT)
    return plc

def write_int(plc, value, PLC_DB_OFFSET):
    data = bytearray(2)
    set_int(data, 0, value)
    plc.db_write(PLC_DB_NUMBER, PLC_DB_OFFSET, data)

def parse_value1(raw):
    try:
        v = int(raw)
        if v < 0 or v > 999:
            return 0
        return v
    except:
        return 0

def parse_value2(raw):
    try:
        v = str(raw)
        if v != "disabled":
            return 1
        else:
             return 0
    except:
        return 0

# =========================
# ===== MAIN ==============
# =========================

def main():

    plc = None
    driver = None
    last_value1 = None
    last_value2 = None

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
            element1 = driver.find_element(By.CSS_SELECTOR, CSS_SELECTOR1)
            raw1 = element1.text.strip()
            
            element2 = driver.find_element(By.XPATH, XPATH_SELECTOR2)
            raw2 = element2.text.strip()

            # ==========================
            # ===== Zapis HTML ========
            # ==========================
            try:
                with open("last_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            except Exception as e:
                print("Nie udało się zapisać HTML:", e)
            # ==========================
        
            value1 = parse_value1(raw1)
            value2 = parse_value2(raw2)

            # Zawsze 3 cyfry
            value1_str = f"{value1:03d}"
            value2_str = f"{value2:03d}"

            if value1 != last_value1:
                print("Wysyłam /workpiece/:", value1_str)
                write_int(plc, value1, PLC_DB_OFFSET1)
                last_value1 = value1

            if value2 != last_value2:
                print("Wysyłam /tightening group state/:", value2_str)
                write_int(plc, value2, PLC_DB_OFFSET2)
                last_value2 = value2

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