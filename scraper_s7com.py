import time
import os
import sys
import subprocess
import socket
import ssl
import urllib.request

import snap7
from snap7.util import set_int, get_int
from snap7.util import set_bool, get_bool
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
PLC_DB_RESTART_BYTE = 4
PLC_DB_RESTART_BIT = 0

CHROMEDRIVER_PATH = "./chromedriver.exe"
CHROME_BINARY_PATH = "./chrome-win64/chrome.exe"

SERVICE_NAME = "prosqobe"

# =========================

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

# =========================
# PLC UTILS
# =========================

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

def read_int(plc, offset):
    try:
        data = plc.db_read(PLC_DB_NUMBER, offset, 2)
        return get_int(data, 0)
    except:
        return 0
    
def write_bool(plc, value, byte_offset, bit_offset, retries=3):
    for _ in range(retries):
        try:
            data = plc.db_read(PLC_DB_NUMBER, byte_offset, 1)
            buffer = bytearray(data)

            set_bool(buffer, 0, bit_offset, value)
            plc.db_write(PLC_DB_NUMBER, byte_offset, buffer)
            return True
        except:
            time.sleep(1)
    return False

def read_bool(plc, byte_offset, bit_offset):
    try:
        data = plc.db_read(PLC_DB_NUMBER, byte_offset, 1)
        return get_bool(data, 0, bit_offset)
    except:
        return False

def reset_plc_values(plc):
    log("Błąd -> zeruję PLC")
    write_int(plc, 0, PLC_DB_OFFSET1)
    write_int(plc, 0, PLC_DB_OFFSET2)

# =========================
# SERVICE
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
# HTTP CHECK
# =========================

def wait_for_server(timeout=15):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    log("Czekam na HTTP...")
    start = time.time()

    while True:
        try:
            req = urllib.request.Request(URL)
            with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
                if r.status == 200:
                    log("HTTP OK")
                    return
        except:
            pass

        if time.time() - start > timeout:
            log("Timeout HTTP -> restart usługi")
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
    log("PLC OK")
    return plc

# =========================
# PARSE
# =========================

def parse_value1(raw):
    try:
        v = int(raw)
        return v if 0 <= v <= 999 else 0
    except:
        return 0

def parse_value2(raw):
    return 0 if str(raw) == "disabled" else 1

# =========================
# RESTART SYSTEMU
# =========================

def restart_script():
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
    last_restart_flag = False

    log("Start systemu")

    while True:

        # PLC connect
        if plc is None or not plc.get_connected():
            try:
                log("Łączenie PLC...")
                plc = connect_plc()
            except:
                time.sleep(PLC_RECONNECT_SEC)
                continue

        # RESTART Z PLC
        restart_flag = read_bool(plc, PLC_DB_RESTART_BYTE, PLC_DB_RESTART_BIT)

        # wykrycie zbocza narastającego (0 -> 1)
        if restart_flag and not last_restart_flag:
            log("PLC -> restart skryptu (BOOL)")

            # zeruj flagę w PLC
            write_bool(plc, False, PLC_DB_RESTART_BYTE, PLC_DB_RESTART_BIT)

            restart_script()

        last_restart_flag = restart_flag

        # Selenium start
        if driver is None:
            try:
                log("Start Selenium...")
                driver = start_driver()
            except:
                time.sleep(SELENIUM_RESTART_SEC)
                continue

        try:
            element1 = driver.find_element(By.CSS_SELECTOR, CSS_SELECTOR1)
            element2 = driver.find_element(By.XPATH, XPATH_SELECTOR2)

            raw1 = element1.text.strip()
            raw2 = element2.text.strip()

            value1 = parse_value1(raw1)
            value2 = parse_value2(raw2)

            # DISABLED -> restart
            if raw2 == "disabled" and time.time() - last_restart > RESTART_COOLDOWN:
                last_restart = time.time()
                reset_plc_values(plc)
                restart_service()
                restart_script()

            if value1 != last_value1:
                log(f"PLC value1: {value1}")
                write_int(plc, value1, PLC_DB_OFFSET1)
                last_value1 = value1

            if value2 != last_value2:
                log(f"PLC value2: {value2}")
                write_int(plc, value2, PLC_DB_OFFSET2)
                last_value2 = value2

            time.sleep(READ_INTERVAL_SEC)

        except:
            reset_plc_values(plc)

            try:
                driver.quit()
            except:
                pass

            driver = None
            last_value1 = None
            last_value2 = None

            time.sleep(SELENIUM_RESTART_SEC)

# =========================

if __name__ == "__main__":
    main()