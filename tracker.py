import os
import requests

# 讀取保密設定
SERP_API_KEY = os.environ.get('SERP_API_KEY')
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

# ==================== 可自行修改的機票設定 ====================
DEPARTURE_ID = "HKG"         # 出發地機場代碼 (HKG 代表香港)
ARRIVAL_ID = "NRT"           # 目的地機場代碼 (NRT 代表東京成田)
OUTBOUND_DATE = "2026-12-01" # 去程日期 (年-月-日)
RETURN_DATE = "2026-12-10"   # 回程日期 (年-月-日)
TARGET_PRICE = 3000          # 你的目標底價 (港幣)
# ==============================================================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram 推播失敗: {e}")

def check_flights():
    url = (
        f"https://serpapi.com/search.json?engine=google_flights"
        f"&departure_id={DEPARTURE_ID}&arrival_id={ARRIVAL_ID}"
        f"&outbound_date={OUTBOUND_DATE}&return_date={RETURN_DATE}"
        f"&currency=HKD&api_key={SERP_API_KEY}"
    )
    
    response = requests.get(url).json()
    best_flights = response.get('best_flights', [])
    
    if not best_flights:
        print("未查到相關航班資訊")
        return

    lowest_price = best_flights[0].get('price', 99999)
    airline = best_flights[0].get('flights', [{}])[0].get('airline', '未知航空公司')
    
    print(f"目前搜尋到的最低價格為：HKD ${lowest_price}")
    
    if lowest_price <= TARGET_PRICE:
        msg = (
            f"✈️ 【平機票降價通知】\n\n"
            f"航線：{DEPARTURE_ID} ➡️ {ARRIVAL_ID}\n"
            f"日期：{OUTBOUND_DATE} 至 {RETURN_DATE}\n"
            f"航空公司：{airline}\n"
            f"目前最低價：HKD ${lowest_price}\n"
            f"(已低於目標價 HKD ${TARGET_PRICE}！)"
        )
        send_telegram(msg)

if __name__ == "__main__":
    check_flights()
