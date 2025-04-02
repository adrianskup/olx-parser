import requests
import json
import datetime
from bs4 import BeautifulSoup
import re
import time
import os

MONTHS_PL = {
    "stycznia": "January", "lutego": "February", "marca": "March", "kwietnia": "April",
    "maja": "May", "czerwca": "June", "lipca": "July", "sierpnia": "August",
    "września": "September", "października": "October", "listopada": "November", "grudnia": "December"
}

OLX_URL = "https://www.olx.pl/motoryzacja/samochody/warszawa/?search%5Bdist%5D=100&search%5Border%5D=created_at:desc&search%5Bfilter_float_price:to%5D=10000"

def parse_location_date(location_date):
    today_pattern = r'(?:Odświeżono )?Dzisiaj o (\d{1,2}:\d{2})'
    refreshed_date_pattern = r'Odświeżono dnia (\d{1,2}) ([a-z]+) (\d{4})'
    standard_date_pattern = r'(\d{1,2}) ([a-z]+) (\d{4})'

    match_today = re.search(today_pattern, location_date)
    if match_today:
        time_part = match_today.group(1)
        today_date = datetime.datetime.now().strftime("%d %B %Y")
        return location_date.split(" - ")[0], f"{today_date} o {time_part}"

    match_refreshed_date = re.search(refreshed_date_pattern, location_date)
    if match_refreshed_date:
        day, month_pl, year = match_refreshed_date.groups()
        month_en = MONTHS_PL.get(month_pl, month_pl)
        return location_date.split(" - ")[0], f"{day} {month_en} {year}"

    match_standard_date = re.search(standard_date_pattern, location_date)
    if match_standard_date:
        day, month_pl, year = match_standard_date.groups()
        month_en = MONTHS_PL.get(month_pl, month_pl)
        return location_date.split(" - ")[0], f"{day} {month_en} {year}"

    return location_date, None

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
        return datetime.datetime.min

def clean_price(price_text):
    return re.sub(r'\s*do negocjacji', '', price_text).strip()

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
        
        image_element = soup.select_one("div.swiper-zoom-container img")
        image_url = image_element["src"] if image_element else None

        if not image_url:
            time.sleep(1)
            response = requests.get(link)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                image_element = soup.select_one("div.swiper-zoom-container img")
                image_url = image_element["src"] if image_element else None

        details = {}
        details_section = soup.select("div.css-ae1s7g div.css-1msmb8o p.css-z0m36u")
        for item in details_section:
            text = item.text.strip()
            parts = text.split(": ", 1)
            if len(parts) == 2:
                key, value = parts
                details[key] = value
        return {"description": description, "details": details, "image_url": image_url}
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
    for item in ad_items:
        try:
            link = item.find("a", href=True)["href"]
            if "otomoto.pl" in link:
                continue
            title = item.select_one("a > h4").text.strip()
            price_text = clean_price(item.select_one("p[data-testid='ad-price']").text.strip())
            link = f"https://www.olx.pl{link}"
            location_date = item.select_one("p.css-vbz67q").text.strip()
            location, date = parse_location_date(location_date)

            if not date:
                date = "01 January 2000"
            
            car_details = get_car_details(link)
            ad = {
                "title": title,
                "price": price_text,
                "link": link,
                "location": location,
                "date": date,
                "description": car_details.get("description", "Нет описания"),
                "details": car_details.get("details", {}),
                "image_url": car_details.get("image_url", None)
            }

            ad_date = convert_date_to_datetime(ad["date"])
            if ad_date < datetime.datetime.now() - datetime.timedelta(days=3):
                continue

            ads.append(ad)
        except Exception:
            continue
    return ads

def load_existing_data():
    try:
        with open("olx_ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("ads", [])
    except FileNotFoundError:
        return []

def save_data_to_json(ads):
    data = {"updated": str(datetime.datetime.now()), "ads": ads}
    with open("olx_ads.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def update_ads():
    existing_ads = load_existing_data()
    new_ads = get_olx_ads()
    all_ads = new_ads
    all_ads.sort(key=lambda x: convert_date_to_datetime(x["date"]), reverse=True)
    save_data_to_json(all_ads)

update_ads()

# Настройки для GitHub
GITHUB_USERNAME = "adrianskup"
REPO_NAME = "olx-parser"
BRANCH_NAME = "main"  # Или другая ветка, если используешь

def push_to_github():
    os.system("git config --global user.name 'github-actions'")
    os.system("git config --global user.email 'github-actions@github.com'")
    os.system("git add olx_ads.json")
    os.system('git commit -m "Автоматическое обновление объявлений" || echo "No changes to commit"')
    os.system("git push")

# Запускаем пуш после обновления объявлений
push_to_github()
