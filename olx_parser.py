import requests
from bs4 import BeautifulSoup
import json
import datetime
import os

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

def load_existing_data(filename="olx_ads.json"):
    """Загружает существующие данные из файла, если он есть, иначе возвращает пустой список."""
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {"updated": str(datetime.datetime.now()), "ads": []}

def save_data(filename="olx_ads.json", data=None):
    """Сохраняет данные в JSON файл."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def update_ads():
    new_ads = get_olx_ads()
    if new_ads:
        # Загружаем существующие данные
        existing_data = load_existing_data()

        # Добавляем новые объявления
        existing_ads = existing_data.get("ads", [])
        existing_ads_set = {ad["link"] for ad in existing_ads}  # Множество для проверки уникальности
        new_ads_filtered = [ad for ad in new_ads if ad["link"] not in existing_ads_set]

        if new_ads_filtered:
            existing_data["ads"].extend(new_ads_filtered)  # Добавляем только новые объявления
            existing_data["updated"] = str(datetime.datetime.now())  # Обновляем дату

            # Сохраняем обновленные данные
            save_data(data=existing_data)

            print(f"✅ Найдено {len(new_ads_filtered)} новых объявлений. Данные обновлены в olx_ads.json.")
        else:
            print("❌ Нет новых объявлений.")
    else:
        print("❌ Объявления не найдены.")

if __name__ == "__main__":
    update_ads()  # Запуск обновления данных сразу
