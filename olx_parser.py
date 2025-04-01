import requests
from bs4 import BeautifulSoup
import json
import datetime
from tqdm import tqdm  # Для прогресс-бара

# Обновленный URL с фильтрацией по цене до 10000 zł
OLX_URL = "https://www.olx.pl/motoryzacja/samochody/warszawa/?search%5Bdist%5D=100&search%5Border%5D=created_at:desc&search%5Bfilter_float_price:to%5D=10000"

def get_car_details(link):
    if "otomoto.pl" in link:
        return {}

    try:
        response = requests.get(link)
        if response.status_code != 200:
            return {}

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Извлекаем описание
        description = soup.select_one("div.css-19duwlz")
        description = description.text.strip() if description else "Описание не указано"
        
        # Дополнительные характеристики
        details = {}
        details_section = soup.select("div.css-ae1s7g div.css-1msmb8o p.css-z0m36u")
        
        for item in details_section:
            text = item.text.strip()
            parts = text.split(" ", 1)  # Разделяем на ключ и значение
            if len(parts) == 2:
                key, value = parts
                details[key] = value

        return {"description": description, "details": details}

    except Exception:
        return {}

def get_olx_ads():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(OLX_URL, headers=headers)

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    ads = []

    ad_items = soup.select("div[data-cy='l-card']")
    for item in tqdm(ad_items, desc="Обрабатываем объявления", unit="объявление"):
        try:
            title = item.select_one("a > h4")
            title = title.text.strip() if title else "Нет заголовка"
            
            price_text = item.select_one("p[data-testid='ad-price']")
            price_text = price_text.text.strip() if price_text else "Цена не указана"
            
            link = item.find("a", href=True)
            link = link["href"] if link else "#"
            link = f"https://www.olx.pl{link}" if link.startswith("/") else link

            car_details = get_car_details(link)

            if car_details:
                ads.append({
                    "title": title,
                    "price": price_text,
                    "link": link,
                    "description": car_details.get("description", "Нет описания"),
                    "details": car_details.get("details", {})
                })

        except Exception:
            continue

    return ads

# Основной процесс парсинга
ads = get_olx_ads()
if ads:
    data = {
        "updated": str(datetime.datetime.now()),
        "ads": ads
    }

    with open("olx_ads.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ Найдено {len(ads)} объявлений с ценой до 10000 zł. Данные сохранены в olx_ads.json")
else:
    print("❌ Объявления не найдены.")
