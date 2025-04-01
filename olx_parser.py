import requests
from bs4 import BeautifulSoup
import json
import datetime

OLX_URL = "https://www.olx.pl/motoryzacja/samochody/warszawa/"

def get_olx_ads():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(OLX_URL, headers=headers)

    if response.status_code != 200:
        print("Ошибка запроса:", response.status_code)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    ads = []

    for item in soup.select("div[data-cy='l-card']"):
        title = item.select_one("h6").text.strip() if item.select_one("h6") else "Нет заголовка"
        price = item.select_one("p[data-testid='ad-price']").text.strip() if item.select_one("p[data-testid='ad-price']") else "Цена не указана"
        link = item.find("a", href=True)["href"] if item.find("a", href=True) else "#"

        ads.append({
            "title": title,
            "price": price,
            "link": f"https://www.olx.pl{link}" if link.startswith("/") else link
        })

    return ads

ads = get_olx_ads()
if ads:
    data = {
        "updated": str(datetime.datetime.now()),
        "ads": ads
    }

    with open("olx_ads.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ Найдено {len(ads)} объявлений. Данные сохранены в olx_ads.json")
else:
    print("❌ Объявления не найдены.")
