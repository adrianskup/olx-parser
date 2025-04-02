import requests
import json
import datetime
from bs4 import BeautifulSoup
import re

# Словарь для преобразования названий месяцев с польского
MONTHS_PL = {
    "stycznia": "January", "lutego": "February", "marca": "March", "kwietnia": "April",
    "maja": "May", "czerwca": "June", "lipca": "July", "sierpnia": "August",
    "września": "September", "października": "October", "listopada": "November", "grudnia": "December"
}

OLX_URL = "https://www.olx.pl/motoryzacja/samochody/warszawa/?search%5Bdist%5D=100&search%5Border%5D=created_at:desc&search%5Bfilter_float_price:to%5D=10000"

# Функция для парсинга местоположения и даты
def parse_location_date(location_date):
    today_pattern = r'(Odświeżono )?Dzisiaj o (\d{1,2}:\d{2})'
    date_pattern = r'(Odświeżono )?(\d{1,2}) ([a-z]+) (\d{4})'

    match_today = re.search(today_pattern, location_date)
    if match_today:
        location = location_date.split(" - ")[0]
        date = datetime.datetime.now().strftime("%d %B %Y") + " o " + match_today.group(2)
        return location, date

    match_date = re.search(date_pattern, location_date)
    if match_date:
        location = location_date.split(" - ")[0]
        day, month_pl, year = match_date.groups()[1:]
        month_en = MONTHS_PL.get(month_pl, month_pl)
        date = f"{day} {month_en} {year}"
        return location, date

    return location_date, ""

# Функция для получения деталей автомобиля
def get_car_details(link):
    if "otomoto.pl" in link:
        return {}

    try:
        response = requests.get(link)
        if response.status_code != 200:
            return {}
        
        soup = BeautifulSoup(response.text, "html.parser")
        description = soup.select_one("div.css-19duwlz")
        description = description.text.strip() if description else "Описание не указано"
        
        details = {}
        details_section = soup.select("div.css-ae1s7g div.css-1msmb8o p.css-z0m36u")
        for item in details_section:
            text = item.text.strip()
            parts = text.split(": ", 1)
            if len(parts) == 2:
                key, value = parts
                details[key] = value
        
        return {"description": description, "details": details}

    except Exception:
        return {}

# Функция для получения всех объявлений с OLX
def get_olx_ads():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(OLX_URL, headers=headers)

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    ads = []

    ad_items = soup.select("div[data-cy='l-card']")
    for item in ad_items:
        try:
            title = item.select_one("a > h4").text.strip()
            price_text = item.select_one("p[data-testid='ad-price']").text.strip()
            link = f"https://www.olx.pl{item.find('a', href=True)['href']}"
            location_date = item.select_one("p.css-vbz67q").text.strip()

            location, date = parse_location_date(location_date)  # Функция для парсинга локации и даты
            car_details = get_car_details(link)  # Функция для получения дополнительных деталей

            ads.append({
                "title": title,
                "price": price_text,
                "link": link,
                "location": location,
                "date": date,
                "description": car_details.get("description", "Нет описания"),
                "details": car_details.get("details", {})
            })

        except Exception:
            continue

    return ads

# Функция для загрузки существующих данных из JSON
def load_existing_data():
    try:
        with open("olx_ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("ads", [])
    except FileNotFoundError:
        return []

# Функция для сохранения обновленных данных в JSON
def save_data_to_json(ads):
    data = {"updated": str(datetime.datetime.now()), "ads": ads}
    with open("olx_ads.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Функция для корректного преобразования строки даты в объект datetime
def convert_date_to_datetime(date_str):
    try:
        for pl, en in MONTHS_PL.items():
            date_str = date_str.replace(pl, en)
        if " o " in date_str:
            date_obj = datetime.datetime.strptime(date_str, "%d %B %Y o %H:%M")
        else:
            date_obj = datetime.datetime.strptime(date_str, "%d %B %Y")
        return date_obj
    except ValueError:
        return None

# Функция для обновления данных
def update_ads():
    # Загружаем старые данные из JSON
    existing_ads = load_existing_data()

    # Получаем новые объявления
    new_ads = get_olx_ads()

    # Добавляем новые объявления, которых еще нет в существующих данных
    all_ads = existing_ads
    for ad in new_ads:
        # Проверяем, если ссылка на это объявление уже есть в существующих данных
        if not any(existing_ad["link"] == ad["link"] for existing_ad in existing_ads):
            all_ads.append(ad)

    # Убираем дубли (если объявления с одинаковыми ссылками)
    unique_ads = {ad["link"]: ad for ad in all_ads}
    all_ads = list(unique_ads.values())

    # Проверяем, чтобы у каждого объявления была дата, если нет, то присваиваем "01 January 1970"
    for ad in all_ads:
        if not ad.get("date"):
            ad["date"] = "01 January 1970"

    # Сортируем по дате (новые вверху)
    all_ads.sort(key=lambda x: convert_date_to_datetime(x["date"]) or datetime.datetime.min, reverse=True)

    # Сохраняем обновленные данные в JSON
    save_data_to_json(all_ads)

# Запуск обновления
update_ads()
