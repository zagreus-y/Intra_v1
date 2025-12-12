"""
SMAIntraday Strategy
Fast/Slow SMA crossover
Compatible with LiveRunner (bar-driven)
"""

from collections import deque
import numpy as np


class SMAIntraday:
    def __init__(self, params):
        """
        params = {"fast": int, "slow": int}
        """
        self.fast = params.get("fast", 5)
        self.slow = params.get("slow", 20)

        self.closes = deque(maxlen=self.slow + 5)
        self.symbol = None
        self.data_provider = None
        self.broker = None

        self.last_signal = None  # "buy", "sell", or None

    # ------------------------------
    # Called once at start
    # ------------------------------
    def on_start(self, symbol):
        self.symbol = symbol

        # preload historical 1m data so SMAs work immediately
        try:
            df = self.data_provider.get_ohlcv(symbol, interval="1m", lookback=200)
            if df is not None and not df.empty:
                for c in df["close"].tolist():
                    self.closes.append(float(c))
            print(f"[SMA] Preloaded {len(self.closes)} bars for {symbol}")
        except:
            print("[SMA] Warning: failed to load historical bars")

    # ------------------------------
    # LiveRunner will call this to inject references
    # (Optional but recommended)
    # ------------------------------
    def bind(self, data_provider, broker):
        self.data_provider = data_provider
        self.broker = broker

    # ------------------------------
    # Called every new bar
    # ------------------------------
    def on_bar(self, symbol, bar):
        close = float(bar["close"])
        self.closes.append(close)

        if len(self.closes) < self.slow:
            return None  # not enough data

        fast_sma = np.mean(list(self.closes)[-self.fast:])
        slow_sma = np.mean(list(self.closes)[-self.slow:])

        # Current position
        pos = self.broker.get_positions().get(symbol, 0)

        # BUY condition
        if fast_sma > slow_sma and self.last_signal != "buy" and pos == 0:
            self.last_signal = "buy"
            return {
                "action": "buy",
                "price": close,
                "qty": None
            }

        # SELL condition
        if fast_sma < slow_sma and self.last_signal != "sell" and pos > 0:
            self.last_signal = "sell"
            return {
                "action": "sell",
                "price": close,
                "qty": None
            }

        return None

    # ------------------------------
    def on_stop(self, symbol):
        print("[SMA] Stopped.")
