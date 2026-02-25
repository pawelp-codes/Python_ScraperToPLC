# Python Scraper to PLC

Projekt umożliwia odczyt numeru detalu z lokalnego serwera HTTP (np. interfejsu webowego maszyny) i zapis wartości do PLC S7-1500. System automatycznie restartuje przeglądarkę w przypadku błędów (watchdog Selenium) i ponawia połączenie z PLC w razie utraty komunikacji.

Funkcjonalności:
- Odczyt wartości z elementu strony za pomocą Selenium (`CSS_SELECTOR`)
- Zapis wartości do PLC S7-1500 jako INT (zawsze 3-cyfrowy, brak/błąd = 000)
- Watchdog Selenium – automatyczny restart przeglądarki przy błędzie
- Autoreconnect PLC – próby ponownego połączenia w razie rozłączenia
- Zapis ostatniej strony HTML do `last_page.html` (debug/log)

Konfiguracja znajduje się w pliku `scraper_selenium.py` i należy ją dostosować do swojego środowiska:

```python
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

Wymagania:

Python 3.10 lub nowszy

Biblioteki Python: selenium, snap7

Chrome + Chromedriver zgodne z wersją przeglądarki

Instalacja:

Sklonuj repozytorium lub skopiuj pliki na swój komputer.

Zainstaluj wymagane pakiety:

pip install selenium snap7

Upewnij się, że chromedriver.exe i folder chrome-win64 znajdują się w katalogu projektu lub zmień ścieżki w konfiguracji.

Uruchomienie:

python scraper_s7com.py

Skrypt uruchomi Selenium w trybie headless i rozpocznie odczyt z serwera oraz zapis do PLC. Watchdog automatycznie restartuje przeglądarkę przy błędach, a PLC reconnect próbuje ponownie połączyć się w razie utraty komunikacji.

scraper_selenium.py - do testowania dzialania samego scrappera (pobiera zmienna danej klasy i wyswietla w konsoli)


Struktura katalogów:

.
├── scraper_selenium.py
├── scraper_s7com.py
├── autostartPyScraperToPLC.bat
├── chromedriver.exe
├── chrome-win64/
└── example_www/