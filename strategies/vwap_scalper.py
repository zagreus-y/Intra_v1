"""
VWAP Scalper Strategy
Mean-reversion around VWAP using intraday candles
Single-symbol, bar-driven
"""

from collections import deque
import numpy as np
from strategies.base_strategy import BaseStrategy


class VWAPScalper(BaseStrategy):
    def __init__(self, config):
        """
        config = {
            "symbol": str,
            "threshold": float (% deviation),
            "qty": int,
            "window": int (rolling bars for VWAP)
        }
        """
        super().__init__(config)

        self.threshold = config.get("threshold", 0.25)  # percent deviation
        self.qty = config.get("qty", 1)
        self.window = config.get("window", 300)

        self.typical_prices = deque(maxlen=self.window)
        self.volumes = deque(maxlen=self.window)

        self.last_signal = None

    # -------------------------
    def on_start(self):
        pass

    # -------------------------
    def _vwap(self):
        tp = np.array(self.typical_prices)
        vol = np.array(self.volumes)

        if tp.size == 0 or vol.sum() == 0:
            return None

        return np.sum(tp * vol) / np.sum(vol)

    # -------------------------
    def on_bar(self, bar):
        high = float(bar["high"])
        low = float(bar["low"])
        close = float(bar["close"])
        volume = float(bar["volume"])

        typical_price = (high + low + close) / 3

        self.typical_prices.append(typical_price)
        self.volumes.append(volume)

        vwap = self._vwap()
        if vwap is None:
            return None

        deviation_pct = (close - vwap) / vwap * 100

        # BUY: price stretched below VWAP
        if deviation_pct <= -self.threshold and self.last_signal != "buy":
            self.last_signal = "buy"
            return {
                "action": "buy",
                "price": close,
                "qty": self.qty
            }

        # SELL: price stretched above VWAP
        if deviation_pct >= self.threshold and self.last_signal != "sell":
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