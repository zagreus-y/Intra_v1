"""
BaseStrategy

Every strategy must extend this class.
Your live_runner & backtester will rely on these hooks:

- on_start()     → called once before data flow
- on_tick(tick)  → called for every tick
- on_bar(bar)    → called for every completed bar
- on_stop()      → called once when shutting down

All strategy-generated signals must be dicts like:
    { "action": "buy" or "sell", "price": float }
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseStrategy(ABC):

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def on_start(self):
        pass

    @abstractmethod
    def on_tick(self, tick: Dict[str, Any]):
        """
        tick = {
            "symbol": str,
            "ltp": float,
            "volume": int,
            "timestamp": datetime
        }
        """
        pass

    @abstractmethod
    def on_bar(self, bar: Dict[str, Any]):
        """
        bar = {
            "timestamp": datetime,
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": int
        }
        """
        pass

    @abstractmethod
    def on_stop(self):
        pass
