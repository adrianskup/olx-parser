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
        price_text = item.select_one("p[data-testid='ad-price']").text.strip() if item.select_one("p[data-testid='ad-price']") else "Цена не указана"
        link = item.find("a", href=True)["href"] if item.find("a", href=True) else "#"
        location = item.select_one("small[data-testid='ad-location']").text.strip() if item.select_one("small[data-testid='ad-location']") else ""

        # Преобразуем цену в число (если это возможно)
        try:
            price = float(price_text.replace("zł", "").replace(" ", "").replace(",", "."))
        except ValueError:
            price = None  # Если цена невалидная, пропускаем это объявление

        # Фильтрация по цене и городу (Варшава)
        if price is not None and price <= 10000 and "Warszawa" in location:
            ads.append({
                "title": title,
                "price": price,
                "location": location,
                "link": f"https://www.olx.pl{link}" if link.startswith("/") else link
            })

    return ads

def update_ads():
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

if __name__ == "__main__":
    update_ads()  # Запуск обновления данных сразу
