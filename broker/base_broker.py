"""
Abstract broker interface with a clean, predictable API.

Every real or paper broker in your system must implement these methods.
Your strategy + live runner will talk ONLY to this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseBroker(ABC):

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        qty: int,
        side: str,              # 'buy' or 'sell'
        order_type: str = "market",   # 'market' or 'limit'
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Places an order into the broker.
        Must return a dict with at least:
        {
            'order_id': str,
            'status': 'pending' | 'filled' | 'rejected'
        }
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Attempts to cancel an order.
        """
        pass

    @abstractmethod
    def get_positions(self) -> Dict[str, Any]:
        """
        Returns:
            { symbol: qty }
        """
        pass

    @abstractmethod
    def get_orders(self) -> Dict[str, Any]:
        """
        Returns:
            { order_id: order_state_dict }
        """
        pass

    @abstractmethod
    def get_cash(self) -> float:
        """
        Returns current cash balance.
        """
        pass
