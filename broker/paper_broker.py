"""
Enhanced Paper Broker V2

Features:
- Realistic tick-based execution
- Limit & market orders
- Order lifecycle management
- Slippage & realistic latency
- Position & cash tracking
- Trade history
"""

import uuid
import time
from typing import Dict, Any, Optional, List
from enum import Enum
from .base_broker import BaseBroker

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stoploss"
    BRACKET = "bracket"


class PaperBroker(BaseBroker):
    """
    Realistic paper trading broker with tick-based execution.
    """

    def __init__(
        self,
        starting_cash: float = 100000,
        slippage: float = 0.0005,
        latency_ms: float = 100
    ):
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.slippage = slippage
        self.latency_ms = latency_ms
        
        self.positions: Dict[str, Dict] = {}  # symbol -> {qty, avg_price}
        self.orders: Dict[str, Dict] = {}  # order_id -> order
        self.trades: List[Dict] = []  # executed trades
        self.order_counter = 0
        
    # ============ ORDER PLACEMENT ============
    def place_order(
        self,
        symbol: str,
        qty: int,
        side: str,  # "buy" or "sell"
        order_type: str = "market",
        price: Optional[float] = None,
        stop_loss: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place an order.
        
        Returns:
            {
                "order_id": str,
                "status": OrderStatus,
                "symbol": str,
                "qty": int,
                "side": str,
                "price": float,
                "timestamp": float (unix)
            }
        """
        
        order_id = f"ORDER_{self.order_counter}_{uuid.uuid4().hex[:8]}"
        self.order_counter += 1
        
        order = {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": order_type,
            "price": price,
            "stop_loss": stop_loss,
            "status": OrderStatus.PENDING.value,
            "filled_qty": 0,
            "avg_price": None,
            "timestamp": time.time(),
            "fill_time": None
        }
        
        self.orders[order_id] = order
        return {k: v for k, v in order.items() if k != "timestamp"}
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order if possible."""
        
        order = self.orders.get(order_id)
        if not order:
            return False
        
        if order["status"] in (OrderStatus.FILLED.value, OrderStatus.CANCELLED.value):
            return False
        
        order["status"] = OrderStatus.CANCELLED.value
        return True
    
    # ============ TICK-BASED EXECUTION ============
    def on_tick(self, symbol: str, price: float, volume: int) -> None:
        """
        Process a market tick.
        Executes pending orders for this symbol.
        """
        
        for order_id, order in list(self.orders.items()):
            
            if order["symbol"] != symbol:
                continue
            
            if order["status"] == OrderStatus.PENDING.value:
                
                if order["type"] == OrderType.MARKET.value:
                    self._execute_market_order(order, price)
                
                elif order["type"] == OrderType.LIMIT.value:
                    if order["side"] == "buy" and price <= order["price"]:
                        self._execute_market_order(order, price)
                    elif order["side"] == "sell" and price >= order["price"]:
                        self._execute_market_order(order, price)
    
    def _execute_market_order(self, order: Dict, execution_price: float) -> None:
        """Execute a market/limit order."""
        
        # Apply slippage
        if order["side"] == "buy":
            exec_price = execution_price * (1 + self.slippage)
        else:
            exec_price = execution_price * (1 - self.slippage)
        
        qty = order["qty"]
        symbol = order["symbol"]
        
        # Validate cash for buys
        if order["side"] == "buy":
            cost = exec_price * qty
            if cost > self.cash:
                order["status"] = OrderStatus.REJECTED.value
                return
        
        # Validate position for sells
        if order["side"] == "sell":
            if symbol not in self.positions or self.positions[symbol]["qty"] < qty:
                order["status"] = OrderStatus.REJECTED.value
                return
        
        # Execute
        if order["side"] == "buy":
            self._execute_buy(symbol, qty, exec_price)
        else:
            self._execute_sell(symbol, qty, exec_price)
        
        order["status"] = OrderStatus.FILLED.value
        order["avg_price"] = exec_price
        order["filled_qty"] = qty
        order["fill_time"] = time.time()
    
    def _execute_buy(self, symbol: str, qty: int, price: float) -> None:
        """Internal: execute a buy and update positions."""
        
        cost = price * qty
        self.cash -= cost
        
        if symbol not in self.positions:
            self.positions[symbol] = {
                "qty": qty,
                "avg_price": price
            }
        else:
            pos = self.positions[symbol]
            old_val = pos["avg_price"] * pos["qty"]
            new_val = price * qty
            pos["avg_price"] = (old_val + new_val) / (pos["qty"] + qty)
            pos["qty"] += qty
        
        self.trades.append({
            "symbol": symbol,
            "side": "BUY",
            "qty": qty,
            "price": price,
            "timestamp": time.time()
        })
    
    def _execute_sell(self, symbol: str, qty: int, price: float) -> None:
        """Internal: execute a sell and update positions."""
        
        proceeds = price * qty
        self.cash += proceeds
        
        pos = self.positions[symbol]
        pnl = (price - pos["avg_price"]) * qty
        
        self.positions[symbol]["qty"] -= qty
        
        if self.positions[symbol]["qty"] == 0:
            del self.positions[symbol]
        
        self.trades.append({
            "symbol": symbol,
            "side": "SELL",
            "qty": qty,
            "price": price,
            "pnl": pnl,
            "timestamp": time.time()
        })
    
    # ============ STATE QUERIES ============
    def get_positions(self) -> Dict[str, Dict]:
        """Get all open positions."""
        return {k: dict(v) for k, v in self.positions.items()}
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a specific symbol."""
        return dict(self.positions[symbol]) if symbol in self.positions else None
    
    def get_orders(self, symbol: Optional[str] = None) -> Dict[str, Dict]:
        """Get all orders, optionally filtered by symbol."""
        if symbol is None:
            return {k: dict(v) for k, v in self.orders.items()}
        else:
            return {k: dict(v) for k, v in self.orders.items() if v["symbol"] == symbol}
    
    def get_cash(self) -> float:
        """Get available cash."""
        return self.cash
    
    def get_equity(self) -> float:
        """Get total equity (cash + positions marked to market)."""
        return self.cash + sum(
            pos["qty"] * (pos.get("current_price", pos["avg_price"]))
            for pos in self.positions.values()
        )
    
    def get_trades(self) -> List[Dict]:
        """Get trade history."""
        return list(self.trades)