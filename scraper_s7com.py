import time
import os
import sys
import subprocess
import socket
import ssl
import urllib.request

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
# KONFIGURACJA
# =========================

URL = "https://127.0.0.1:8181/doc/index.html#/process/workplace1"
CSS_SELECTOR1 = ".value.currentProcessWorkpiece"
XPATH_SELECTOR2 = "//*[@id='app']/div/div/main/div/div[2]/div[2]/div[1]/div/table[1]/tbody/tr/td[2]"

READ_INTERVAL_SEC = 1
PLC_RECONNECT_SEC = 5
SELENIUM_RESTART_SEC = 5
RESTART_COOLDOWN = 30

PLC_IP = "192.168.0.1"
PLC_RACK = 0
PLC_SLOT = 1

PLC_DB_NUMBER = 69
PLC_DB_OFFSET1 = 0
PLC_DB_OFFSET2 = 2

CHROMEDRIVER_PATH = "./chromedriver.exe"
CHROME_BINARY_PATH = "./chrome-win64/chrome.exe"

SERVICE_NAME = "prosqobe"

# =========================
# PRINT Z TIMESTAMP
# =========================

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

# =========================
# SERVICE RESTART
# =========================

def restart_service():
    try:
        log(f"Restart usługi: {SERVICE_NAME}")
        subprocess.run(["sc", "stop", SERVICE_NAME], check=False)
        for _ in range(10):
            status = subprocess.run(["sc", "query", SERVICE_NAME], capture_output=True, text=True)
            if "STOP_PENDING" not in status.stdout:
                break
            time.sleep(1)
        subprocess.run(["sc", "start", SERVICE_NAME], check=False)
        log("Usługa zrestartowana")
        time.sleep(5)
    except:
        log("Nie udało się zrestartować usługi")

# =========================
# WAIT FOR HTTP SERVER
# =========================

def is_port_open(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect((host, port))
        s.close()
        return True
    except:
        return False

def wait_for_server(timeout=20):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    log("Czekam na działający serwer HTTP...")
    start = time.time()
    while True:
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                if response.status == 200:
                    log("Serwer HTTP działa poprawnie")
                    return True
        except:
            pass
        if time.time() - start > timeout:
            log("Timeout serwera – restart usługi")
            restart_service()
            start = time.time()
        time.sleep(2)

# =========================
# SELENIUM
# =========================

def start_driver():
    wait_for_server()
    options = Options()
    options.binary_location = CHROME_BINARY_PATH
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--ignore-certificate-errors")
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(5)
    driver.get(URL)
    wait = WebDriverWait(driver, 5)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, CSS_SELECTOR1)))
    wait.until(EC.presence_of_element_located((By.XPATH, XPATH_SELECTOR2)))
    return driver

# =========================
# PLC
# =========================

def connect_plc():
    plc = Client()
    plc.connect(PLC_IP, PLC_RACK, PLC_SLOT)
    log(f"Połączono z PLC {PLC_IP}")
    return plc

def write_int(plc, value, offset, retries=3):
    data = bytearray(2)
    set_int(data, 0, value)
    for _ in range(retries):
        try:
            plc.db_write(PLC_DB_NUMBER, offset, data)
            return True
        except:
            time.sleep(1)
    return False

def parse_value1(raw):
    try:
        v = int(raw)
        return v if 0 <= v <= 999 else 0
    except:
        return 0

def parse_value2(raw):
    try:
        return 0 if str(raw) == "disabled" else 1
    except:
        return 0

# =========================
# SYSTEM RESTART
# =========================

def restart_system(driver):
    log("Stan DISABLED -> restart systemu")
    try:
        driver.quit()
    except:
        pass
    restart_service()
    log("Restart skryptu")
    os.execv(sys.executable, [sys.executable] + sys.argv)

# =========================
# MAIN
# =========================

def main():
    plc = None
    driver = None
    last_value1 = None
    last_value2 = None
    last_restart = 0

    log("Start systemu")

    while True:
        if plc is None or not plc.get_connected():
            try:
                log("Łączenie PLC...")
                plc = connect_plc()
            except:
                time.sleep(PLC_RECONNECT_SEC)
                continue

        if driver is None:
            wait_for_server()
            try:
                log("Start przeglądarki...")
                driver = start_driver()
            except:
                log("Błąd startu Selenium, ponawiam próbę po chwili")
                time.sleep(SELENIUM_RESTART_SEC)
                continue

        try:
            element1 = driver.find_element(By.CSS_SELECTOR, CSS_SELECTOR1)
            raw1 = element1.text.strip()
            element2 = driver.find_element(By.XPATH, XPATH_SELECTOR2)
            raw2 = element2.text.strip()

            if raw2 == "disabled" and time.time() - last_restart > RESTART_COOLDOWN:
                last_restart = time.time()
                restart_system(driver)

            value1 = parse_value1(raw1)
            value2 = parse_value2(raw2)

            if value1 != last_value1:
                log(f"Wysyłam /workpiece/: {value1:03d}")
                write_int(plc, value1, PLC_DB_OFFSET1)
                last_value1 = value1

            if value2 != last_value2:
                log(f"Wysyłam /tightening group state/: {value2:03d}")
                write_int(plc, value2, PLC_DB_OFFSET2)
                last_value2 = value2

            time.sleep(READ_INTERVAL_SEC)

        except:
            try:
                driver.quit()
            except:
                pass
            driver = None
            time.sleep(SELENIUM_RESTART_SEC)

if __name__ == "__main__":
    main()