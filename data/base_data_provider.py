"""
Abstract base class for data providers.
Allows switching between SmartAPI, free APIs, CSV files, etc.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd


class DataProvider(ABC):
    """
    All data sources (SmartAPI, NSE, CSV, etc.) must implement this interface.
    """

    @abstractmethod
    def get_candles(
        self,
        symbol: str,
        interval: str = "5m",
        lookback_days: int = 5
    ) -> pd.DataFrame:
        """
        Fetch OHLCV candles for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            interval: Candle interval ("1m", "5m", "15m", "1h", "daily")
            lookback_days: Number of days to fetch
            
        Returns:
            DataFrame with columns: [datetime, open, high, low, close, volume]
            Index should be datetime
        """
        pass

    @abstractmethod
    def get_ltp(self, symbol: str) -> float:
        """
        Get Last Traded Price for a symbol.
        """
        pass

    @abstractmethod
    def is_market_open(self) -> bool:
        """
        Check if market is currently open.
        """
        pass