from SmartApi import SmartConnect
import pyotp
from datetime import datetime, timedelta
from typing import List


class SmartAPIDataProvider:
    def __init__(
        self,
        api_key: str,
        client_code: str,
        password: str,
        totp_secret: str
    ):
        self.api_key = api_key
        self.client_code = client_code
        self.password = password
        self.totp_secret = totp_secret
        self.obj = None
        self._login()

    # -------------------------
    # LOGIN
    # -------------------------
    def _login(self):
        self.obj = SmartConnect(api_key=self.api_key)
        totp = pyotp.TOTP(self.totp_secret).now()
        session = self.obj.generateSession(self.client_code, self.password, totp)

        if not session["status"]:
            raise Exception("SmartAPI login failed")

        print("SmartAPI login successful")

    # -------------------------
    # INTRADAY CANDLE FETCH
    # -------------------------
    def get_intraday_candles(
        self,
        symbol_token: str,
        exchange: str = "NSE",
        interval: str = "FIVE_MINUTE",
        lookback_days: int = 5
    ) -> List[List]:
        """
        Returns candle data:
        [timestamp, open, high, low, close, volume]
        """

        to_date = datetime.now()
        from_date = to_date - timedelta(days=lookback_days)

        params = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M")
        }

        data = self.obj.getCandleData(params)

        if not data["status"]:
            raise Exception(f"Failed to fetch candles: {data}")

        return data["data"]

    # -------------------------
    # LIVE LTP
    # -------------------------
    def get_ltp(self, symbol: str, symbol_token: str, exchange: str = "NSE"):
        ltp = self.obj.ltpData(exchange, symbol, symbol_token)
        return ltp["data"]["ltp"]