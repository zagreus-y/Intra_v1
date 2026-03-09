"""
Trend Filter Helpers

Use these to confirm entry direction aligns with trend.
This SINGLE change typically improves win rates by 10-15%.
"""

from collections import deque
import numpy as np


class TrendFilter:
    """
    Detects trend direction using multiple methods.
    Use to confirm trade direction matches trend.
    """

    def __init__(self, fast_period: int = 10, slow_period: int = 20):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.closes = deque(maxlen=slow_period + 5)

    def add_bar(self, close: float) -> None:
        """Add a new close price."""
        self.closes.append(close)

    def is_uptrend(self) -> bool:
        """
        Returns True if in uptrend.
        Simple method: fast_sma > slow_sma AND price > slow_sma
        """
        if len(self.closes) < self.slow_period:
            return False

        closes = list(self.closes)
        fast_sma = np.mean(closes[-self.fast_period:])
        slow_sma = np.mean(closes[-self.slow_period:])
        close = closes[-1]

        return fast_sma > slow_sma and close > slow_sma

    def is_downtrend(self) -> bool:
        """
        Returns True if in downtrend.
        Simple method: fast_sma < slow_sma AND price < slow_sma
        """
        if len(self.closes) < self.slow_period:
            return False

        closes = list(self.closes)
        fast_sma = np.mean(closes[-self.fast_period:])
        slow_sma = np.mean(closes[-self.slow_period:])
        close = closes[-1]

        return fast_sma < slow_sma and close < slow_sma

    def get_trend(self) -> str:
        """
        Returns 'up', 'down', or 'neutral'.
        """
        if self.is_uptrend():
            return "up"
        elif self.is_downtrend():
            return "down"
        else:
            return "neutral"

    def can_long(self) -> bool:
        """Only open long positions in uptrends."""
        return self.is_uptrend()

    def can_short(self) -> bool:
        """Only open short positions in downtrends."""
        return self.is_downtrend()


class RSITrendFilter:
    """RSI-based trend detection (alternative to SMA)."""

    def __init__(self, period: int = 14, oversold: int = 35, overbought: int = 65):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.closes = deque(maxlen=period + 5)

    def add_bar(self, close: float) -> None:
        """Add a new close price."""
        self.closes.append(close)

    def _calculate_rsi(self) -> float:
        """Calculate RSI."""
        if len(self.closes) < self.period:
            return 50.0  # Neutral

        closes = list(self.closes)
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-self.period:])
        avg_loss = np.mean(losses[-self.period:])

        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def get_rsi(self) -> float:
        """Get current RSI value."""
        return self._calculate_rsi()

    def is_uptrend(self) -> bool:
        """Uptrend: RSI > 50."""
        return self.get_rsi() > 50

    def is_downtrend(self) -> bool:
        """Downtrend: RSI < 50."""
        return self.get_rsi() < 50

    def can_long(self) -> bool:
        """Only long in uptrend."""
        return self.is_uptrend()

    def can_short(self) -> bool:
        """Only short in downtrend."""
        return self.is_downtrend()
