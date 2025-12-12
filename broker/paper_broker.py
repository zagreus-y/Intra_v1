"""
PaperBroker

A realistic paper-trading broker designed for intraday algos.

Features:
- Market + Limit orders
- Tick-based execution
- Slippage support
- Cash & position tracking
- Order lifecycle: pending → filled / rejected / cancelled
"""

import uuid
import time
from typing import Dict, Any, Optional
from .base_broker import BaseBroker


class PaperBroker(BaseBroker):

    def __init__(self, starting_cash: float = 100000.0, slippage: float = 0.0):
        self.cash = starting_cash
        self.slippage = slippage

        self.positions: Dict[str, int] = {}  # {symbol: qty}
        self.orders: Dict[str, Dict[str, Any]] = {}  # order_id -> order dict
        self.trades = []  # list of executed trades

    # ----------------------------------------------------------
    # Required API implementations
    # ----------------------------------------------------------

    def place_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = "market",
        price: Optional[float] = None
    ) -> Dict[str, Any]:

        order_id = str(uuid.uuid4())

        order = {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "side": side,            # 'buy' or 'sell'
            "type": order_type,      # 'market' or 'limit'
            "limit_price": price,
            "status": "pending",
            "created": time.time(),
        }

        self.orders[order_id] = order
        return order

    def cancel_order(self, order_id: str) -> bool:
        order = self.orders.get(order_id)
        if not order:
            return False

        if order["status"] in ("filled", "cancelled"):
            return False

        order["status"] = "cancelled"
        return True

    def get_positions(self) -> Dict[str, Any]:
        return dict(self.positions)

    def get_orders(self) -> Dict[str, Any]:
        return dict(self.orders)

    def get_cash(self) -> float:
        return self.cash

    # ----------------------------------------------------------
    # Tick-based execution engine
    # ----------------------------------------------------------

    def on_market_tick(self, symbol: str, ltp: float):
        """
        Called by live runner every time a new tick arrives.
        Executes pending market/limit orders.
        """

        for order in list(self.orders.values()):
            if order["symbol"] != symbol:
                continue

            if order["status"] != "pending":
                continue

            if order["type"] == "market":
                self._execute_market(order, ltp)

            elif order["type"] == "limit":
                if order["side"] == "buy" and ltp <= order["limit_price"]:
                    self._execute_market(order, order["limit_price"])

                elif order["side"] == "sell" and ltp >= order["limit_price"]:
                    self._execute_market(order, order["limit_price"])

    # ----------------------------------------------------------
    # Internal execution helpers
    # ----------------------------------------------------------

    def _execute_market(self, order: Dict[str, Any], price: float):
        """
        Executes the order at market. Applies slippage.
        Checks cash / position limits.
        """

        # apply slippage
        if order["side"] == "buy":
            fill_price = price * (1 + self.slippage)
        else:
            fill_price = price * (1 - self.slippage)

        qty = order["qty"]
        value = fill_price * qty

        # BUY
        if order["side"] == "buy":
            if value > self.cash:
                order["status"] = "rejected"
                order["reason"] = "insufficient_cash"
                return

            self.cash -= value
            self.positions[order["symbol"]] = self.positions.get(order["symbol"], 0) + qty

        # SELL
        else:
            pos = self.positions.get(order["symbol"], 0)
            if pos < qty:
                order["status"] = "rejected"
                order["reason"] = "insufficient_position"
                return

            self.cash += value
            self.positions[order["symbol"]] = pos - qty

        # Mark fill
        order["status"] = "filled"
        order["filled_price"] = fill_price
        order["filled_time"] = time.time()

        # Record trade
        self.trades.append({
            "symbol": order["symbol"],
            "side": order["side"],
            "qty": qty,
            "price": fill_price,
            "timestamp": order["filled_time"],
        })
