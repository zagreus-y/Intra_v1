"""
BaseStrategy

All strategies must inherit this class.

Engine lifecycle:

- on_start() → called once before backtest/live session
- on_bar(bar) → called for each completed candle
- on_stop() → called once after session ends

Strategy must return signals in this format:

{
    "action": "buy" or "sell",
    "price": float (optional, defaults to close),
    "qty": int
}
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseStrategy(ABC):

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbol: str = config.get("symbol", "UNKNOWN")

    # -------------------------
    @abstractmethod
    def on_start(self) -> None:
        pass

    # -------------------------
    @abstractmethod
    def on_bar(self, bar: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        bar = {
            "timestamp": datetime,
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": float
        }
        """
        pass

    # -------------------------
    @abstractmethod
    def on_stop(self) -> None:
        pass