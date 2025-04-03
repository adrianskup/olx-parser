import os
import requests
import json
import datetime
from bs4 import BeautifulSoup
import re
import time

MONTHS_PL = {
    "stycznia": "January", "lutego": "February", "marca": "March", "kwietnia": "April",
    "maja": "May", "czerwca": "June", "lipca": "July", "sierpnia": "August",
    "września": "September", "października": "October", "listopada": "November", "grudnia": "December"
}

OLX_URL = "https://www.olx.pl/motoryzacja/samochody/warszawa/?search%5Bdist%5D=100&search%5Border%5D=created_at:desc&search%5Bfilter_float_price:to%5D=10000"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

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
    price_text = re.sub(r'\s*do negocjacji', '', price_text).strip()
    price_with_negotiation = 'do negocjacji' if 'do negocjacji' in price_text else ''
    return price_text, price_with_negotiation

def get_car_details(link, is_otomoto=False):
    try:
        response = requests.get(link, headers=HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        result = {"description": "Opis nie podano", "details": {}, "image_url": None}

        if is_otomoto:
            description_element = soup.select_one("div.ooa-unlmzs.e1s9vvdy4")
            if description_element:
                result["description"] = description_element.get_text(separator="\n").strip()

            details = {}
            params_container = soup.find("div", {"data-testid": "ad-top-attributes"})
            if params_container:
                params = params_container.find_all("p")
                for i in range(0, len(params), 2):
                    if i + 1 < len(params):
                        key = params[i].text.strip().rstrip(':')
                        value = params[i + 1].text.strip()
                        details[key] = value

            tech_params = soup.find("div", {"data-testid": "ad-params"})
            if tech_params:
                sections = tech_params.find_all("div", recursive=False)
                for section in sections:
                    try:
                        key = section.find("p", class_="ekwurce8 ooa-1vfan6r").text.strip()
                        value = section.find("p", class_="ekwurce9 ooa-10u0vtk").text.strip()
                        details[key] = value
                    except:
                        continue

            result["details"] = details
            img_container = soup.select_one('div.css-gl6djm img') or \
                            soup.select_one('img[data-testid="bigImage"]') or \
                            soup.select_one('img[src*="apollo.olxcdn.com"]')
            if img_container:
                image_url = img_container.get('src') or img_container.get('data-src')
                if image_url and ';s=' in image_url:
                    image_url = image_url.split(';s=')[0]
                result["image_url"] = image_url

        else:
            description_element = soup.select_one("div.css-19duwlz")
            if description_element:
                result["description"] = description_element.get_text(separator="\n").strip()

            details = {}
            details_items = soup.select("div.css-ae1s7g div.css-1msmb8o p.css-z0m36u")
            for item in details_items:
                text = item.get_text(strip=True)
                if ':' in text:
                    key, value = text.split(':', 1)
                    details[key.strip()] = value.strip()

            result["details"] = details
            img_element = soup.select_one('div.swiper-zoom-container img') or \
                          soup.select_one('img[data-testid="swiper-image"]')
            if img_element:
                result["image_url"] = img_element.get('src') or img_element.get('data-src')

        return result

    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса для {link}: {e}")
    except Exception as e:
        print(f"Ошибка при обработке {link}: {e}")

    return {"description": "Ошибка при получении данных", "details": {}, "image_url": None}

def get_olx_ads():
    response = requests.get(OLX_URL, headers=HEADERS)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    ads = []
    ad_items = soup.select("div[data-cy='l-card']")

    for item in ad_items:
        try:
            link = item.find("a", href=True)["href"]
            title = item.select_one("a > h4").text.strip()
            price_text = clean_price(item.select_one("p[data-testid='ad-price']").text.strip())
            
            is_otomoto = "otomoto.pl" in link
            link = link if is_otomoto else f"https://www.olx.pl{link}"

            location_date = item.select_one("p.css-vbz67q").text.strip()
            location, date = parse_location_date(location_date)
            date = date if date else "01 January 2000"

            car_details = get_car_details(link, is_otomoto)

            ad = {
                "title": title,
                "price": price_text,
                "link": link,
                "location": location,
                "date": date,
                "description": car_details.get("description", "Brak opisu"),
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

GITHUB_USERNAME = "adrianskup"
REPO_NAME = "olx-parser"
BRANCH_NAME = "main"

def push_to_github():
    os.system("git config --global user.name 'github-actions'")
    os.system("git config --global user.email 'github-actions@github.com'")
    os.system("git add olx_ads.json")
    os.system('git commit -m "Автоматическое обновление объявлений" || echo "No changes to commit"')
    os.system("git push")

push_to_github()
