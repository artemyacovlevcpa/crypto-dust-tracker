import requests
import hmac
import hashlib
import time
from urllib.parse import urlencode
import os

class BinanceDustTracker:
    BASE_URL = "https://api.binance.com"

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    def _sign_payload(self, payload: dict):
        query_string = urlencode(payload)
        signature = hmac.new(self.api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        return query_string + f"&signature={signature}"

    def _request(self, method: str, path: str, payload: dict = None):
        url = self.BASE_URL + path
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        payload = payload or {}
        payload['timestamp'] = int(time.time() * 1000)
        signed_payload = self._sign_payload(payload)

        if method == "GET":
            return requests.get(url + "?" + signed_payload, headers=headers).json()
        elif method == "POST":
            return requests.post(url + "?" + signed_payload, headers=headers).json()

    def get_balances(self):
        data = self._request("GET", "/api/v3/account")
        return [b for b in data['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]

    def get_dust_assets(self):
        balances = self.get_balances()
        dust = []
        for b in balances:
            total = float(b['free']) + float(b['locked'])
            if total < 0.001:
                dust.append(b)
        return dust

    def get_convertible_dust_assets(self):
        path = "/sapi/v1/asset/dust-btc"
        return self._request("GET", path)

    def notify_telegram(self, message: str):
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            print("Telegram not configured.")
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": message}
        requests.post(url, data=data)

    def run(self):
        dust = self.get_dust_assets()
        dust_names = [d['asset'] for d in dust]
        message = f"🧹 Обнаружена криптопыль: {', '.join(dust_names)}"

        try:
            convertible = self.get_convertible_dust_assets()
            conv_names = [i['asset'] for i in convertible.get('details', [])]
            if conv_names:
                message += f"\n🔁 Можно сконвертировать: {', '.join(conv_names)}"
        except:
            message += "\n⚠️ Не удалось получить список конвертируемых токенов."

        self.notify_telegram(message)
