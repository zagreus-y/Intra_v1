"""
StopLossManager

Tracks:
- fixed stoploss
- trailing stoploss
- per-symbol SL states

Usage:
    slm = StopLossManager()
    slm.set_fixed("TATASTEEL", entry=120, stop=118)

    slm.on_tick("TATASTEEL", price=117.9) → returns "hit"
"""

from typing import Dict, Any, Optional


class StopLossManager:

    def __init__(self):
        # symbol → SL dictionary
        self.sl: Dict[str, Dict[str, Any]] = {}

    # ----------------------------------------------------
    # Create Stoploss
    # ----------------------------------------------------

    def set_fixed(self, symbol: str, entry_price: float, stop_price: float):
        self.sl[symbol] = {
            "type": "fixed",
            "entry": entry_price,
            "stop": stop_price
        }

    def set_trailing(self, symbol: str, entry_price: float, trail_points: float):
        """
        trail_points = absolute distance

        Example:
            entry = 120
            trail = 1
            initial SL = 119
        """
        self.sl[symbol] = {
            "type": "trailing",
            "entry": entry_price,
            "trail": trail_points,
            "stop": entry_price - trail_points
        }

    # ----------------------------------------------------
    # On Tick Check
    # ----------------------------------------------------

    def on_tick(self, symbol: str, price: float) -> Optional[str]:
        """
        Check if SL is hit.
        Return:
            'hit' → stoploss triggered
            None → still alive
        """
        if symbol not in self.sl:
            return None

        data = self.sl[symbol]

        # Fixed stoploss
        if data["type"] == "fixed":
            if price <= data["stop"]:
                return "hit"

        # Trailing stoploss
        elif data["type"] == "trailing":
            # move stop upward as price increases
            new_stop = max(data["stop"], price - data["trail"])
            data["stop"] = new_stop

            if price <= data["stop"]:
                return "hit"

        return None

    # ----------------------------------------------------
    # Clear SL after exit
    # ----------------------------------------------------

    def clear(self, symbol: str):
        if symbol in self.sl:
            del self.sl[symbol]
