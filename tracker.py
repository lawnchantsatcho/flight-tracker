import os
import requests
import json
import time

# 讀取保密設定
SERP_API_KEY = os.environ.get('SERP_API_KEY')
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

HISTORY_FILE = "price_history.json"

# ==================== 多組機票追蹤清單 ====================
ROUTES = [
    {
        "name": "札幌 - 10月行程",
        "departure": "HKG",
        "arrival": "CTS",
        "outbound_date": "2026-10-17",
        "return_date": "2026-10-25"
    },
    {
        "name": "大阪 (關西) - 10月假期",
        "departure": "HKG",
        "arrival": "KIX",
        "outbound_date": "2026-10-17",
        "return_date": "2026-10-25"
    }
]
# ==========================================================

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram 推播失敗: {e}")

def check_flights():
    history = load_history()
    
    for route in ROUTES:
        name = route["name"]
        dep = route["departure"]
        arr = route["arrival"]
        out_date = route["outbound_date"]
        ret_date = route["return_date"]

        print(f"\n正在查詢：{name} ({dep} -> {arr})...")

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

            current_price = best_flights[0].get('price', 99999)
            airline = best_flights[0].get('flights', [{}])[0].get('airline', '未知航空公司')
            
            # 讀取上一版的價格紀錄
            prev_data = history.get(name, {})
            prev_price = prev_data.get("price", None)
            
            # 計算價差與趨勢圖示
            if prev_price is None:
                price_diff_str = "首次紀錄（無歷史數據）"
                trend_symbol = "🆕"
            elif current_price < prev_price:
                diff = prev_price - current_price
                price_diff_str = f"降價 HKD ${diff} 📉"
                trend_symbol = "🟢"
            elif current_price > prev_price:
                diff = current_price - prev_price
                price_diff_str = f"加價 HKD ${diff} 📈"
                trend_symbol = "🔴"
            else:
                price_diff_str = "價格持平 ➖"
                trend_symbol = "⚪"

            prev_price_display = f"HKD ${prev_price}" if prev_price is not None else "無歷史數據"

            # 組合推播訊息 (不設任何門檻，每次執行必發送)
            msg = (
                f"{trend_symbol} 【機票價格日報 - {name}】\n\n"
                f"航線：{dep} ➡️ {arr}\n"
                f"日期：{out_date} 至 {ret_date}\n"
                f"航空公司：{airline}\n"
                f"─────────────────\n"
                f"今日價格：HKD ${current_price}\n"
                f"前次價格：{prev_price_display}\n"
                f"變動趨勢：{price_diff_str}"
            )
            
            send_telegram(msg)
            
            # 更新紀錄
            history[name] = {
                "price": current_price,
                "airline": airline
            }
            
        except Exception as e:
            print(f"[{name}] 查詢出錯: {e}")
        
        time.sleep(2)

    save_history(history)

if __name__ == "__main__":
    check_flights()
