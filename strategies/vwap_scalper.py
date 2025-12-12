"""
VWAP Scalper Strategy
- Computes VWAP from intraday bars
- Simple bounce/mean reversion logic
- Works with bar-driven LiveRunner
"""

from collections import deque
import numpy as np


class VWAPScalper:
    def __init__(self, params=None):
        """
        params optional:
            threshold: % deviation from VWAP to trigger reversal
        """
        if params is None:
            params = {}

        self.threshold = params.get("threshold", 0.25)  # 0.25% deviation
        self.symbol = None
        self.data_provider = None
        self.broker = None

        # store (typical_price, volume)
        self.typical_prices = deque(maxlen=400)  
        self.volumes = deque(maxlen=400)

        self.last_signal = None

    # ------------------------------
    # preload historical bars
    # ------------------------------
    def on_start(self, symbol):
        self.symbol = symbol

        try:
            df = self.data_provider.get_ohlcv(symbol, interval="1m", lookback=200)
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    tp = (row["high"] + row["low"] + row["close"]) / 3
                    self.typical_prices.append(tp)
                    self.volumes.append(row["volume"])
            print(f"[VWAP] Preloaded {len(self.typical_prices)} bars for {symbol}")
        except:
            print("[VWAP] Warning: failed to load historical bars")

    def bind(self, data_provider, broker):
        self.data_provider = data_provider
        self.broker = broker

    # ------------------------------
    # VWAP calculation
    # ------------------------------
    def _get_vwap(self):
        tp = np.array(self.typical_prices)
        vol = np.array(self.volumes)

        if tp.size == 0 or vol.size == 0:
            return None

        return np.sum(tp * vol) / np.sum(vol)

    # ------------------------------
    # Called every new bar
    # ------------------------------
    def on_bar(self, symbol, bar):
        close = float(bar["close"])
        high = float(bar["high"])
        low = float(bar["low"])
        vol = int(bar["volume"])

        tp = (high + low + close) / 3

        self.typical_prices.append(tp)
        self.volumes.append(vol)

        vwap = self._get_vwap()
        if vwap is None:
            return None

        deviation = (close - vwap) / vwap * 100  # in %

        pos = self.broker.get_positions().get(symbol, 0)

        # BUY when price dips sufficiently below VWAP
        if deviation <= -self.threshold and self.last_signal != "buy" and pos == 0:
            self.last_signal = "buy"
            return {
                "action": "buy",
                "price": close,
                "qty": None
            }

        # SELL when price goes sufficiently above VWAP (take profit)
        if deviation >= self.threshold and self.last_signal != "sell" and pos > 0:
            self.last_signal = "sell"
            return {
                "action": "sell",
                "price": close,
                "qty": None
            }

        return None

    def on_stop(self, symbol):
        print("[VWAP] Stopped.")
