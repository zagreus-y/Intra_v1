"""
SmartAPI Broker (Angel One)

Real broker implementation for live trading.
Implements the BaseBroker interface.
"""

import uuid
import time
from typing import Dict, Any, Optional, List
from .base_broker import BaseBroker


class SmartAPIBroker(BaseBroker):
    """
    Angel One SmartAPI real broker implementation.
    """

    def __init__(
        self,
        smartapi_obj,  # SmartConnect object
        client_code: str,
        jwt_token: str,
        initial_capital: float = 100000
    ):
        self.smartapi_obj = smartapi_obj
        self.client_code = client_code
        self.jwt_token = jwt_token
        self.initial_capital = initial_capital
        
        self.positions: Dict[str, Dict] = {}
        self.orders: Dict[str, Dict] = {}
        self.trades: List[Dict] = []
        
        self._fetch_initial_state()
    
    def _fetch_initial_state(self):
        """Fetch initial positions and cash from broker."""
        # Get holdings
        try:
            holdings = self.smartapi_obj.getHolding({})
            if holdings.get("status"):
                for holding in holdings.get("data", []):
                    symbol = holding["tradingsymbol"]
                    qty = int(holding["quantity"])
                    
                    if qty > 0:
                        self.positions[symbol] = {
                            "qty": qty,
                            "avg_price": float(holding["pricebasis"]),
                            "symbol": symbol
                        }
        except Exception as e:
            print(f"Warning: Could not fetch holdings: {e}")
    
    # ============ ORDER PLACEMENT ============
    def place_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = "market",
        price: Optional[float] = None,
        variety: str = "NORMAL",
        product_type: str = "INTRADAY"
    ) -> Dict[str, Any]:
        """
        Place order via SmartAPI.
        """
        
        try:
            # Get token
            from data.instrument_mapper import AngelInstrumentMapper
            mapper = AngelInstrumentMapper()
            token = mapper.get_tokens([symbol])[symbol]
            
            params = {
                "variety": variety,
                "tradingsymbol": symbol,
                "symboltoken": token,
                "transactiontype": "BUY" if side == "buy" else "SELL",
                "exchange": "NSE",
                "ordertype": "MARKET" if order_type == "market" else "LIMIT",
                "producttype": product_type,
                "duration": "DAY",
                "quantity": qty,
            }
            
            if order_type == "limit" and price:
                params["price"] = price
            
            response = self.smartapi_obj.placeOrder(params)
            
            if not response.get("status"):
                return {
                    "order_id": None,
                    "status": "rejected",
                    "error": response.get("message", "Unknown error")
                }
            
            order_id = response["data"]["orderid"]
            
            order = {
                "order_id": order_id,
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "type": order_type,
                "price": price,
                "status": "pending",
                "placed_at": time.time()
            }
            
            self.orders[order_id] = order
            
            return {
                "order_id": order_id,
                "status": "pending",
                "symbol": symbol,
                "qty": qty,
                "side": side
            }
        
        except Exception as e:
            print(f"Error placing order: {e}")
            return {
                "order_id": None,
                "status": "error",
                "error": str(e)
            }
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        
        try:
            response = self.smartapi_obj.cancelOrder(
                order_id,
                "NORMAL"
            )
            
            if response.get("status"):
                self.orders[order_id]["status"] = "cancelled"
                return True
            return False
        
        except Exception as e:
            print(f"Error cancelling order: {e}")
            return False
    
    def modify_order(
        self,
        order_id: str,
        qty: Optional[int] = None,
        price: Optional[float] = None
    ) -> bool:
        """Modify an order."""
        
        try:
            params = {"orderid": order_id}
            
            if qty:
                params["quantity"] = qty
            if price:
                params["price"] = price
            
            response = self.smartapi_obj.modifyOrder(params)
            return response.get("status", False)
        
        except Exception as e:
            print(f"Error modifying order: {e}")
            return False
    
    # ============ POSITION & CASH TRACKING ============
    def get_positions(self) -> Dict[str, Any]:
        """Get current positions."""
        # Refresh from broker periodically
        try:
            holdings = self.smartapi_obj.getHolding({})
            if holdings.get("status"):
                self.positions = {}
                for holding in holdings.get("data", []):
                    symbol = holding["tradingsymbol"]
                    qty = int(holding["quantity"])
                    
                    if qty > 0:
                        self.positions[symbol] = {
                            "qty": qty,
                            "avg_price": float(holding["pricebasis"]),
                            "symbol": symbol
                        }
        except Exception as e:
            print(f"Warning: Could not refresh holdings: {e}")
        
        return dict(self.positions)
    
    def get_orders(self) -> Dict[str, Any]:
        """Get all orders."""
        return dict(self.orders)
    
    def get_cash(self) -> float:
        """Get available cash."""
        try:
            profile = self.smartapi_obj.getProfile({})
            if profile.get("status"):
                return float(profile["data"].get("cash", self.initial_capital))
        except Exception as e:
            print(f"Warning: Could not fetch cash: {e}")
        
        return self.initial_capital