import os
import requests
import time

# 讀取保密設定
SERP_API_KEY = os.environ.get('SERP_API_KEY')
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

# ==================== 多組機票追蹤清單 ====================
# 你可以在大括號 { } 裡面自由新增或修改想要追蹤的航線與日期
ROUTES = [
    {
        "name": "東京 (成田) - 12月行程",
        "departure": "HKG",
        "arrival": "NRT",
        "outbound_date": "2026-12-01",
        "return_date": "2026-12-10",
        "target_price": 3000
    },
    {
        "name": "大阪 (關西) - 聖誕假期",
        "departure": "HKG",
        "arrival": "KIX",
        "outbound_date": "2026-12-23",
        "return_date": "2026-12-28",
        "target_price": 3500
    },
    {
        "name": "台北 (桃園) - 跨年快閃",
        "departure": "HKG",
        "arrival": "TPE",
        "outbound_date": "2026-12-30",
        "return_date": "2027-01-02",
        "target_price": 1800
    }
]
# ==========================================================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram 推播失敗: {e}")

def check_flights():
    for route in ROUTES:
        name = route["name"]
        dep = route["departure"]
        arr = route["arrival"]
        out_date = route["outbound_date"]
        ret_date = route["return_date"]
        target = route["target_price"]

        print(f"\n正在查詢：{name} ({dep} -> {arr}, {out_date} 至 {ret_date})...")

        url = (
            f"https://serpapi.com/search.json?engine=google_flights"
            f"&departure_id={dep}&arrival_id={arr}"
            f"&outbound_date={out_date}&return_date={ret_date}"
            f"&currency=HKD&api_key={SERP_API_KEY}"
        )
        
        try:
            response = requests.get(url).json()
            best_flights = response.get('best_flights', [])
            
            if not best_flights:
                print(f"[{name}] 未查到相關航班資訊")
                continue

            lowest_price = best_flights[0].get('price', 99999)
            airline = best_flights[0].get('flights', [{}])[0].get('airline', '未知航空公司')
            
            print(f"[{name}] 目前最低價格為：HKD ${lowest_price}")
            
            if lowest_price <= target:
                msg = (
                    f"✈️ 【平機票降價通知 - {name}】\n\n"
                    f"航線：{dep} ➡️ {arr}\n"
                    f"日期：{out_date} 至 {ret_date}\n"
                    f"航空公司：{airline}\n"
                    f"目前最低價：HKD ${lowest_price}\n"
                    f"(已低於目標價 HKD ${target}！)"
                )
                send_telegram(msg)
        except Exception as e:
            print(f"[{name}] 查詢出錯: {e}")
        
        # 每次查詢間隔 2 秒，確保 API 呼叫穩定
        time.sleep(2)

if __name__ == "__main__":
    check_flights()
