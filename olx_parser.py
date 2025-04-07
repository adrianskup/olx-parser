import os
import requests
import json
import datetime
from bs4 import BeautifulSoup
import re
import time
import random 
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    negotiable = "do negocjacji" in price_text
    price_text = re.sub(r'\s*do negocjacji', '', price_text).strip()
    return price_text, negotiable

def get_car_details(link, is_otomoto=False):
    try:
        response = requests.get(link, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        result = {"description": "Описание не указано", "details": {}, "image_url": None}

        if is_otomoto:
            try:
                desc = soup.select_one("div.ooa-unlmzs.e1s9vvdy4")
                if desc:
                    result["description"] = desc.get_text(separator="\n").strip()
            except: pass

            try:
                details = {}
                params_container = soup.find("div", {"data-testid": "ad-top-attributes"})
                if params_container:
                    params = params_container.find_all("p")
                    for i in range(0, len(params), 2):
                        if i + 1 < len(params):
                            details[params[i].text.strip().rstrip(":")] = params[i + 1].text.strip()
                tech_params = soup.find("div", {"data-testid": "ad-params"})
                if tech_params:
                    for section in tech_params.find_all("div", recursive=False):
                        try:
                            key = section.find("p", class_="ekwurce8 ooa-1vfan6r").text.strip()
                            value = section.find("p", class_="ekwurce9 ooa-10u0vtk").text.strip()
                            details[key] = value
                        except: continue
                if not details:
                    for item in soup.select("div.ooa-17g1q1x.ekwurce6"):
                        try:
                            key = item.find("p", class_="ekwurce8 ooa-1vfan6r").text.strip()
                            value = item.find("p", class_="ekwurce9 ooa-10u0vtk").text.strip()
                            details[key] = value
                        except: continue
                result["details"] = details
            except: pass

            try:
                img = soup.select_one('div.css-gl6djm img') or \
                      soup.select_one('img[data-testid="bigImage"]') or \
                      soup.select_one('img[src*="apollo.olxcdn.com"]')
                if img:
                    image_url = img.get('src') or img.get('data-src')
                    if image_url and ';s=' in image_url:
                        image_url = image_url.split(';s=')[0]
                    result["image_url"] = image_url
            except: pass

        else:
            try:
                desc = soup.select_one("div.css-19duwlz")
                if desc:
                    result["description"] = desc.get_text(separator="\n").strip()
            except: pass

            try:
                details = {}
                for item in soup.select("div.css-ae1s7g div.css-1msmb8o p.css-z0m36u"):
                    text = item.get_text(strip=True)
                    if ':' in text:
                        key, value = text.split(':', 1)
                        details[key.strip()] = value.strip()
                result["details"] = details
            except: pass

            try:
                img = soup.select_one('div.swiper-zoom-container img') or \
                      soup.select_one('img[data-testid="swiper-image"]')
                if img:
                    result["image_url"] = img.get('src') or img.get('data-src')
            except: pass

        return result

    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса для {link}: {e}")
    except Exception as e:
        print(f"Ошибка при обработке {link}: {e}")

    return {"description": "Ошибка при получении данных", "details": {}, "image_url": None}

def fetch_details_for_ad(ad):
    is_otomoto = "otomoto.pl" in ad["link"]
    details = get_car_details(ad["link"], is_otomoto)
    ad.update({
        "description": details.get("description", "Нет описания"),
        "details": details.get("details", {}),
        "image_url": details.get("image_url")
    })
    return ad

def get_olx_ads():
    response = requests.get(OLX_URL, headers=HEADERS)
    if response.status_code != 200:
        return []
    
    # Задержка между запросами от 1 до 4 секунд
    time.sleep(random.uniform(1, 4))  # Задержка от 1 до 4 секунд

    soup = BeautifulSoup(response.text, "html.parser")
    ad_items = soup.select("div[data-cy='l-card']")
    ads = []

    for item in ad_items:
        try:
            link = item.find("a", href=True)["href"]
            title = item.select_one("a > h4").text.strip()
            price_text = item.select_one("p[data-testid='ad-price']").text.strip()
            price, negotiable = clean_price(price_text)
            is_otomoto = "otomoto.pl" in link
            link = link if is_otomoto else f"https://www.olx.pl{link}"
            location_date = item.select_one("p.css-vbz67q").text.strip()
            location, date = parse_location_date(location_date)
            date = date if date else "01 January 2000"
            ad_date = convert_date_to_datetime(date)
            if ad_date < datetime.datetime.now() - datetime.timedelta(days=1):
                continue
            ads.append({
                "title": title, "price": price, "negotiable": negotiable,
                "link": link, "location": location, "date": date
            })
        except Exception:
            continue

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_details_for_ad, ad) for ad in ads]
        ads = [future.result() for future in as_completed(futures)]

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
    existing_links = {ad["link"] for ad in existing_ads}

    ads_dict = {ad["link"]: ad for ad in existing_ads}
    for ad in new_ads:
        if ad["link"] not in existing_links:
            ads_dict[ad["link"]] = ad

    now = datetime.datetime.now()
    filtered_ads = [ad for ad in ads_dict.values()
                    if convert_date_to_datetime(ad["date"]) >= now - datetime.timedelta(days=1)]

    filtered_ads.sort(key=lambda x: convert_date_to_datetime(x["date"]), reverse=True)
    save_data_to_json(filtered_ads)

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
