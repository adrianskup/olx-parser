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
    print(f"DEBUG: Парсим location_date = '{location_date}'")  # Отладка
    today_pattern = r'(Odświeżono )?Dzisiaj o (\d{1,2}:\d{2})'
    date_pattern = r'(Odświeżono )?(\d{1,2}) ([a-z]+) (\d{4})'
    
    match_today = re.search(today_pattern, location_date)
    if match_today:
        location = location_date.split(" - ")[0]
        date = datetime.datetime.now().strftime("%d %B %Y") + " o " + match_today.group(2)
        print(f"DEBUG: Нашли дату сегодня: {date}")
        return location, date

    match_date = re.search(date_pattern, location_date)
    if match_date:
        location = location_date.split(" - ")[0]
        day, month_pl, year = match_date.groups()[1:]
        month_en = MONTHS_PL.get(month_pl, month_pl)
        date = f"{day} {month_en} {year}"
        print(f"DEBUG: Нашли дату: {date}")
        return location, date
    
    print("DEBUG: Дата не найдена!")
    return location_date, None  # Возвращаем None, если дата не найдена

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
            
            print(f"DEBUG: Объявление '{title}' | location_date = '{location_date}' | Парсинг даты = '{date}'")
            
            if not date:
                date = "01 January 2000"
                print(f"WARNING: Дата не найдена, ставим {date}")
            
            ads.append({
                "title": title,
                "price": price_text,
                "link": link,
                "location": location,
                "date": date,
            })
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    return ads

def update_ads():
    new_ads = get_olx_ads()
    for ad in new_ads:
        if "date" not in ad or not ad["date"]:
            ad["date"] = "01 January 2000"
    print("DEBUG: Итоговый список объявлений:")
    for ad in new_ads:
        print(ad)

update_ads()
