import os
import requests
import json
import time
from datetime import datetime, timedelta

SERP_API_KEY = os.environ.get('SERP_API_KEY')
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

HISTORY_FILE = "price_history.json"
MODE_FILE = "tracking_mode.json"

# 設定降價門檻：降價大於或等於此金額才觸發高頻追蹤
DROP_THRESHOLD = 100 

ROUTES = [
    {
        "name": "福岡 - 10月行程",
        "departure": "HKG",
        "arrival": "FUK",
        "outbound_date": "2026-10-17",
        "return_date": "2026-10-25"
    },
    {
        "name": "大阪 (關西) - 聖誕假期",
        "departure": "HKG",
        "arrival": "KIX",
        "outbound_date": "2026-10-17",
        "return_date": "2026-10-25"
    },
    {
        "name": "仙台 - 10月假期",
        "departure": "HKG",
        "arrival": "SDJ",
        "outbound_date": "2026-10-18",
        "return_date": "2026-10-25"
    }
]

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram 推播失敗: {e}")

def should_run(mode_data):
    """判定本次 Cron 觸發是否需要真正執行 SerpApi 查詢"""
    last_run_str = mode_data.get("last_run")
    high_freq_until_str = mode_data.get("high_freq_until")
    now = datetime.now()

    # 如果處於高頻追蹤模式且未過期，每次排程（每3小時）都執行
    if high_freq_until_str:
        high_freq_until = datetime.fromisoformat(high_freq_until_str)
        if now < high_freq_until:
            print(f"🔥 處於高頻追蹤模式中（有效至：{high_freq_until_str}），執行檢查。")
            return True

    # 常態模式：距離上次執行小於 20 小時則跳過
    if last_run_str:
        last_run = datetime.fromisoformat(last_run_str)
        if now - last_run < timedelta(hours=20):
            print("💤 常態模式下距上次執行未滿 20 小時，跳過本次檢查以節省 API 額度。")
            return False

    return True

def check_flights():
    history = load_json(HISTORY_FILE)
    mode_data = load_json(MODE_FILE)

    # 檢查是否手動觸發 (workflow_dispatch) 或符合時間間隔
    is_manual = os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
    if not is_manual and not should_run(mode_data):
        return

    now = datetime.now()
    trigger_high_freq = False

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
            f"&currency=HKD&hl=zh-tw&api_key={SERP_API_KEY}"
        )

        try:
            response = requests.get(url).json()
            best_flights = response.get('best_flights', [])
            flight_url = response.get('search_metadata', {}).get('google_flights_url', 'https://www.google.com/travel/flights')

            price_insights = response.get('price_insights', {})
            price_level = price_insights.get('price_level', 'UNKNOWN')
            
            if price_level == 'LOW':
                eval_str = "🔥 價格偏低 (非常划算！)"
            elif price_level == 'TYPICAL':
                eval_str = "⚖️ 屬於正常價格範圍"
            elif price_level == 'HIGH':
                eval_str = "⚠️ 價格偏高"
            else:
                eval_str = "ℹ️ 暫無歷史評價數據"

            if not best_flights:
                print(f"[{name}] 未查到相關航班資訊")
                continue

            current_price = best_flights[0].get('price', 99999)
            airline = best_flights[0].get('flights', [{}])[0].get('airline', '未知航空公司')

            prev_data = history.get(name, {})
            prev_price = prev_data.get("price", None)

            price_dropped_enough = False

            if prev_price is None:
                price_diff_str = "首次紀錄（無歷史數據）"
                trend_symbol = "🆕"
            elif current_price < prev_price:
                diff = prev_price - current_price
                price_diff_str = f"降價 HKD ${diff} 📉"
                trend_symbol = "🟢"
                
                # 判斷降價是否達到門檻 (>= 100 蚊)
                if diff >= DROP_THRESHOLD:
                    price_dropped_enough = True
                    trigger_high_freq = True  # 觸發開啟高頻追蹤
            elif current_price > prev_price:
                diff = current_price - prev_price
                price_diff_str = f"加價 HKD ${diff} 📈"
                trend_symbol = "🔴"
            else:
                price_diff_str = "價格持平 ➖"
                trend_symbol = "⚪"

            prev_price_display = f"HKD ${prev_price}" if prev_price is not None else "無歷史數據"

            # 若降價滿 $100，在 Telegram 訊息加入醒目標示
            high_freq_notice = f"\n🚨 *顯著降價 (≥ HKD ${DROP_THRESHOLD})！已觸發高頻追蹤模式（未來 48 小時內每 3 小時檢查一次）*" if price_dropped_enough else ""

            msg = (
                f"{trend_symbol} 【機票價格日報 - {name}】\n\n"
                f"✈️ 航線：{dep} ➡️ {arr}\n"
                f"📅 日期：{out_date} 至 {ret_date}\n"
                f"🏢 航空公司：{airline}\n"
                f"─────────────────\n"
                f"💰 今日價格：HKD ${current_price}\n"
                f"📊 前次價格：{prev_price_display} ({price_diff_str})\n"
                f"💡 Google 評價：{eval_str}"
                f"{high_freq_notice}\n\n"
                f"🔗 查看購票平台與預訂：\n{flight_url}"
            )

            send_telegram(msg)

            history[name] = {
                "price": current_price,
                "airline": airline
            }

        except Exception as e:
            print(f"[{name}] 查詢出錯: {e}")

        time.sleep(2)

    # 儲存歷史價格
    save_json(HISTORY_FILE, history)

    # 更新模式與最後執行時間
    mode_data["last_run"] = now.isoformat()
    if trigger_high_freq:
        # 降價超過 $100 時，開啟/延長高頻模式持續 48 小時
        high_freq_until = now + timedelta(hours=48)
        mode_data["high_freq_until"] = high_freq_until.isoformat()
        print(f"🚨 偵測到降價超過 HKD ${DROP_THRESHOLD}！開啟高頻追蹤模式至 {high_freq_until.isoformat()}")

    save_json(MODE_FILE, mode_data)

if __name__ == "__main__":
    check_flights()
