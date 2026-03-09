"""
SMA Intraday Strategy
Fast/Slow SMA crossover
Single-symbol, bar-driven
"""

from collections import deque
import numpy as np


class SMAIntraday:
    def __init__(self, config):
        """
        config = {
            "symbol": str,
            "fast": int,
            "slow": int,
            "qty": int
        }
        """
        self.symbol = config["symbol"]
        self.fast = config.get("fast", 5)
        self.slow = config.get("slow", 20)
        self.qty = config.get("qty", 1)

        self.closes = deque(maxlen=self.slow + 5)
        self.last_signal = None

    # -------------------------
    def on_start(self):
        pass  # no preload needed for backtests

    # -------------------------
    def on_bar(self, bar):
        close = float(bar["close"])
        self.closes.append(close)

        if len(self.closes) < self.slow:
            return None

        closes = list(self.closes)
        fast_sma = np.mean(closes[-self.fast:])
        slow_sma = np.mean(closes[-self.slow:])

        # BUY
        if fast_sma > slow_sma and self.last_signal != "buy":
            self.last_signal = "buy"
            return {
                "action": "buy",
                "price": close,
                "qty": self.qty
            }

        # SELL
        if fast_sma < slow_sma and self.last_signal != "sell":
            self.last_signal = "sell"
            return {
                "action": "sell",
                "price": close,
                "qty": self.qty
            }

        return None

    # -------------------------
    def on_stop(self):
        pass