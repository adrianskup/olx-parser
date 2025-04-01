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

    print(f"Найдено {len(ads)} объявлений.")  # Отладочный вывод
    return ads

# Путь к файлу JSON
json_filename = "olx_ads.json"

# Проверка, существует ли файл
if os.path.exists(json_filename):
    # Если файл существует, загружаем данные
    with open(json_filename, "r", encoding="utf-8") as f:
        existing_data = json.load(f)
else:
    # Если файла нет, создаем новый файл с пустыми данными
    existing_data = {"updated": str(datetime.datetime.now()), "ads": []}

# Получаем новые объявления
new_ads = get_olx_ads()

# Если объявления найдены
if new_ads:
    # Добавляем новые объявления
    existing_ads_set = {ad["link"] for ad in existing_data["ads"]}  # Множество для проверки уникальности
    new_ads_filtered = [ad for ad in new_ads if ad["link"] not in existing_ads_set]

    if new_ads_filtered:
        existing_data["ads"].extend(new_ads_filtered)  # Добавляем только новые объявления
        existing_data["updated"] = str(datetime.datetime.now())  # Обновляем дату

        # Сохраняем обновленные данные в файл
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)

        print(f"✅ Найдено {len(new_ads_filtered)} новых объявлений. Данные обновлены в {json_filename}.")
    else:
        print("❌ Нет новых объявлений.")
else:
    print("❌ Объявления не найдены.")
