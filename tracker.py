import os
import requests
import json

SERP_API_KEY = os.environ.get('SERP_API_KEY')
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

# 讀取舊數據
HISTORY_FILE = "price_history.json"
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
else:
    history = {}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    requests.post(url, json=payload)

# 監控任務清單
TARGETS = [
    {"name": "北海道", "dep": "HKG", "arr": "CTS", "out_date": "2026-10-17", "ret_date": "2026-10-25"},
]

for target in TARGETS:
    name = target["name"]
    dep = target["dep"]
    arr = target["arr"]
    out_date = target["out_date"]
    ret_date = target["ret_date"]

    url = f"https://serpapi.com/search.json?engine=google_flights&departure_id={dep}&arrival_id={arr}&outbound_date={out_date}&return_date={ret_date}&currency=HKD&hl=zh-tw&api_key={SERP_API_KEY}"

    try:
        res = requests.get(url).json()
        best_flights = res.get('best_flights', [])
        
        # 1. 抓取 Google Flights 直達網址
        flight_url = res.get('search_metadata', {}).get('google_flights_url', 'https://www.google.com/travel/flights')

        if not best_flights:
            continue

        current_price = best_flights[0].get('price', 99999)
        airline = best_flights[0].get('flights', [{}])[0].get('airline', '未知航空公司')

        prev_price = history.get(name, {}).get("price")
        
        if prev_price is None:
            trend = "🆕 首次紀錄"
        elif current_price < prev_price:
            trend = f"📉 降價 HKD ${prev_price - current_price}"
        elif current_price > prev_price:
            trend = f"📈 加價 HKD ${current_price - prev_price}"
        else:
            trend = "➖ 價格持平"

        # 2. 組合 Telegram 通知（附帶購票連結）
        msg = (
            f"【機票價格通知 - {name}】\n\n"
            f"✈️ 航空公司：{airline}\n"
            f"📅 日期：{out_date} ~ {ret_date}\n"
            f"💰 今日最低價：HKD ${current_price}\n"
            f"📊 價格趨勢：{trend}\n\n"
            f"🔗 查看購票平台與預訂：\n{flight_url}"
        )

        send_telegram(msg)

        # 更新紀錄
        history[name] = {"price": current_price}

    except Exception as e:
        print(f"Error processing {name}: {e}")

# 儲存歷史紀錄
with open(HISTORY_FILE, "w") as f:
    json.dump(history, f, indent=2)
