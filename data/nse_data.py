"""
NSEDataHybrid (Final Clean Version)
-----------------------------------
Features:
- Stable Live LTP + Volume fetch from NSE API
- Automatic cookie warm-up
- Strong browser-grade headers to avoid blocking
- Tick → 1-minute bar builder (for live market)
- Historical OHLC (EOD) using NSEPython or Yahoo
- Unified get_ohlcv() for both live + historical
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import time

# Optional libraries
try:
    from nsepython import nse_get_history
    NSEPY_AVAILABLE = True
except:
    NSEPY_AVAILABLE = False

try:
    import yfinance as yf
    YF_AVAILABLE = True
except:
    YF_AVAILABLE = False

IST = pytz.timezone("Asia/Kolkata")


# ======================================================================
# NSEDataHybrid CLEAN IMPLEMENTATION
# ======================================================================
class NSEDataHybrid:
    def __init__(self, mode="chill"):
        self.mode = mode

        # Live tick storage → bar builder
        self.bar_cache = {}
        self.last_minute = {}

        # Session + headers
        self.session = requests.Session()
        self._init_headers()
        self._warm_cookies("TATASTEEL")


    # ------------------------------------------------------------------
    # Headers strong enough to bypass NSE “lite JSON”
    # ------------------------------------------------------------------
    def _init_headers(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "identity",   # <-- IMPORTANT FIX
            "Connection": "keep-alive",
            "DNT": "1",
            "Origin": "https://www.nseindia.com",
            "Referer": "https://www.nseindia.com/get-quotes/equity",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }


    # ------------------------------------------------------------------
    # Warm cookies required for tradeInfo JSON block
    # ------------------------------------------------------------------
    def _warm_cookies(self, symbol):
        try:
            url = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"
            self.session.get(url, headers=self.headers, timeout=5)
        except:
            pass


    # ------------------------------------------------------------------
    # Market hour detector
    # ------------------------------------------------------------------
    def is_market_open(self):
        t = datetime.now(IST)
        start = t.replace(hour=9, minute=15, second=0, microsecond=0)
        end = t.replace(hour=15, minute=30, second=0, microsecond=0)
        return start <= t <= end

    # ------------------------------------------------------------------
    # Live tick from NSE API
    # ------------------------------------------------------------------
    def get_live_quote(self, symbol: str):

        # Ensure referer matches symbol
        self.headers["Referer"] = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"

        # Warm cookies properly
        self._warm_cookies(symbol)

        url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"

        try:
            resp = self.session.get(url, headers=self.headers, timeout=7)
            data = resp.json()

            # -------------------------------
            # 1. Extract LTP
            # -------------------------------
            ltp = None

            # Normal path
            try:
                ltp = data["priceInfo"]["lastPrice"]
            except:
                pass

            # Fallback: compute from order book
            if ltp is None:
                try:
                    best_bid = data["marketDeptOrderBook"]["bid"][0]["price"]
                    best_ask = data["marketDeptOrderBook"]["ask"][0]["price"]
                    ltp = (best_bid + best_ask) / 2
                except:
                    pass

            if ltp is None:
                print("No LTP found anywhere.")
                return None

            # -------------------------------
            # 2. Extract Volume
            # -------------------------------
            # -----------------------------------------
            # 2. Extract Volume (correct for this JSON)
            # -----------------------------------------
            vol = None

            # Path 1: tradeInfo (sometimes present)
            try:
                vol = data["marketDeptOrderBook"]["tradeInfo"]["totalTradedVolume"]
            except:
                pass

            # Path 2: preOpenMarket (your JSON uses this during live hours)
            if not vol:
                try:
                    vol = data["preOpenMarket"]["totalTradedVolume"]
                except:
                    pass

            # Path 3: securityWiseDP quantityTraded (backup)
            if not vol:
                try:
                    vol = data["securityWiseDP"]["quantityTraded"]
                except:
                    pass

            # Fallback
            if not vol:
                vol = 0



            return {
                "symbol": symbol,
                "ltp": float(ltp),
                "volume": int(vol),
                "timestamp": datetime.now(IST)
            }

        except Exception as e:
            print("Live quote error:", e)
            return None

    # ------------------------------------------------------------------
    # Tick → Bar Builder (used during market hours)
    # ------------------------------------------------------------------
    def _update_live_bar(self, symbol):
        tick = self.get_live_quote(symbol)
        if not tick:
            return

        ts = tick["timestamp"]
        bar_ts = ts.replace(second=0, microsecond=0)

        # First time
        if symbol not in self.last_minute:
            self.last_minute[symbol] = bar_ts
            self.bar_cache[symbol] = [{
                "timestamp": bar_ts,
                "open": tick["ltp"],
                "high": tick["ltp"],
                "low": tick["ltp"],
                "close": tick["ltp"],
                "volume": tick["volume"],
            }]
            return

        last_ts = self.last_minute[symbol]

        if bar_ts == last_ts:
            bar = self.bar_cache[symbol][-1]
            bar["high"] = max(bar["high"], tick["ltp"])
            bar["low"] = min(bar["low"], tick["ltp"])
            bar["close"] = tick["ltp"]
            bar["volume"] = max(bar["volume"], tick["volume"])
            return

        # New bar
        self.last_minute[symbol] = bar_ts
        self.bar_cache[symbol].append({
            "timestamp": bar_ts,
            "open": tick["ltp"],
            "high": tick["ltp"],
            "low": tick["ltp"],
            "close": tick["ltp"],
            "volume": tick["volume"],
        })

    # ------------------------------------------------------------------
    # Unified OHLCV fetcher (live or historical)
    # ------------------------------------------------------------------
    def get_ohlcv(self, symbol, interval="1m", lookback=30):
        # LIVE MARKET → build bars
        if self.is_market_open():
            self._update_live_bar(symbol)

            if symbol not in self.bar_cache:
                return pd.DataFrame()

            df = pd.DataFrame(self.bar_cache[symbol])
            df.set_index("timestamp", inplace=True)

            if lookback:
                cutoff = datetime.now(IST) - timedelta(minutes=lookback)
                df = df[df.index >= cutoff]

            return df

        # OUTSIDE MARKET → return historical
        return self.get_historical(symbol, interval=interval, days=1)

    # ------------------------------------------------------------------
    # Historical data for backtests
    # ------------------------------------------------------------------
    def get_historical(self, symbol, interval="1d", days=100):
        end = datetime.today().date()
        start = end - timedelta(days=days)

        # NSEPY daily
        if NSEPY_AVAILABLE and interval == "1d":
            try:
                df = nse_get_history(symbol, "EQ", start, end)
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)
                df.rename(columns=str.lower, inplace=True)
                return df[["open", "high", "low", "close", "volume"]]
            except:
                pass

        # yfinance fallback
        if YF_AVAILABLE:
            try:
                df = yf.download(
                    symbol + ".NS",
                    start=start,
                    end=end,
                    interval=interval,
                    progress=False
                )
                if df.empty:
                    return df
                df.rename(columns=str.lower, inplace=True)
                return df[["open", "high", "low", "close", "volume"]]
            except:
                return pd.DataFrame()

        return pd.DataFrame()
