"""
Stoploss Manager

Handles fixed and trailing stoploss mechanisms.
Monitors positions and executes exits based on stoploss levels.
"""

from typing import Dict, Optional, Callable
from enum import Enum


class StoplossType(Enum):
    FIXED = "fixed"
    TRAILING = "trailing"
    TIME_BASED = "time_based"


class StoplossManager:
    """
    Manages stoploss for open positions.
    Works with both backtesting and live trading.
    """

    def __init__(
        self,
        on_exit_callback: Callable[[str, float, str], None]
    ):
        """
        on_exit_callback: Called when stoploss is hit
                         Signature: callback(symbol, exit_price, reason)
        """
        self.on_exit_callback = on_exit_callback
        self.stoploss_levels: Dict[str, Dict] = {}  # symbol -> {sl_price, type,  ...}
    
    def set_fixed_stoploss(
        self,
        symbol: str,
        entry_price: float,
        stoploss_percent: float
    ) -> float:
        """
        Set fixed stoploss as percentage below entry.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stoploss_percent: % below entry (e.g., 2.0 for 2%)
            
        Returns:
            Stoploss level
        """
        
        sl_level = entry_price * (1 - stoploss_percent / 100)
        
        self.stoploss_levels[symbol] = {
            "type": StoplossType.FIXED.value,
            "entry_price": entry_price,
            "sl_level": sl_level,
            "percent": stoploss_percent,
            "highest_price": entry_price
        }
        
        return sl_level
    
    def set_trailing_stoploss(
        self,
        symbol: str,
        entry_price: float,
        trail_percent: float
    ) -> float:
        """
        Set trailing stoploss.
        """
        
        sl_level = entry_price * (1 - trail_percent / 100)
        
        self.stoploss_levels[symbol] = {
            "type": StoplossType.TRAILING.value,
            "entry_price": entry_price,
            "sl_level": sl_level,
            "trail_percent": trail_percent,
            "highest_price": entry_price
        }
        
        return sl_level
    
    def on_tick(self, symbol: str, price: float) -> bool:
        """
        Check stoploss on each tick.
        Returns True if stoploss hit.
        """
        
        if symbol not in self.stoploss_levels:
            return False
        
        sl = self.stoploss_levels[symbol]
        
        # Update highest price (for trailing stop)
        if price > sl["highest_price"]:
            sl["highest_price"] = price
            
            # Reset trailing stop
            if sl["type"] == StoplossType.TRAILING.value:
                sl["sl_level"] = price * (1 - sl["trail_percent"] / 100)
        
        # Check if stoploss hit
        if price <= sl["sl_level"]:
            self.on_exit_callback(symbol, price, "stoploss")
            del self.stoploss_levels[symbol]
            return True
        
        return False
    
    def on_bar(self, symbol: str, bar: Dict) -> bool:
        """
        Check stoploss on bar close.
        """
        return self.on_tick(symbol, bar["close"])
    
    def clear(self, symbol: str) -> None:
        """Clear stoploss for a symbol."""
        if symbol in self.stoploss_levels:
            del self.stoploss_levels[symbol]
    
    def get_level(self, symbol: str) -> Optional[float]:
        """Get current stoploss level."""
        if symbol in self.stoploss_levels:
            return self.stoploss_levels[symbol]["sl_level"]
        return None