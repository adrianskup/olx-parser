import requests
import json
import datetime
from bs4 import BeautifulSoup
import re

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
            price_text = item.select_one("p[data-testid='ad-price']").text.strip()
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
                "details": car_details.get("details", {})
            }
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

def update_ads():
    existing_ads = load_existing_data()
    new_ads = get_olx_ads()
    all_ads = existing_ads + new_ads
    unique_ads = {ad["link"]: ad for ad in all_ads}
    all_ads = list(unique_ads.values())
    
    for ad in all_ads:
        if "date" not in ad or not ad["date"]:
            ad["date"] = "01 January 2000"
    
    all_ads.sort(key=lambda x: convert_date_to_datetime(x["date"]), reverse=True)
    save_data_to_json(all_ads)
    print("DEBUG: Итоговый список объявлений:", all_ads)

update_ads()
