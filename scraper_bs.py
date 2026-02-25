import requests
from bs4 import BeautifulSoup

URL = "http://127.0.0.1:5500/example_www/index.html"

def get_workpiece_number():
    try:
        response = requests.get(URL, timeout=5, verify=False)
        response.raise_for_status()
        
        with open("response_dump.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.find("span", class_="value workpieceNumber")

        if element and element.text.strip():
            return element.text.strip()
        else:
            return None

    except requests.exceptions.Timeout:
        print("Błąd: Timeout połączenia")
    except requests.exceptions.ConnectionError:
        print("Błąd: Brak połączenia z serwerem")
    except requests.exceptions.HTTPError as e:
        print(f"Błąd HTTP: {e}")
    except Exception as e:
        print(f"Inny błąd: {e}")

    return None


if __name__ == "__main__":
    value = get_workpiece_number()
    print("WORKPIECE NUMBER:", value)