"""
Position Sizing Utilities

Supports:
- percent_of_equity sizing
- fixed risk per trade sizing (recommended)
- fixed capital allocation
"""

from typing import Optional


def size_by_percent(equity: float, percent: float, price: float) -> int:
    """
    Allocates 'percent' of capital to the trade.
    Example: 5000 equity, 20% → 1000 allocation → qty = 1000 // price
    """
    if percent <= 0:
        return 0
    alloc = equity * percent
    qty = int(alloc // price)
    return max(qty, 0)


def size_by_risk(
    equity: float,
    risk_per_trade: float,
    entry_price: float,
    stop_price: float
) -> int:
    """
    Calculates position size based on maximum allowed loss.

    risk_per_trade = max loss allowed (e.g., 50 INR per trade)
    stop_price = stoploss level

    Example:
      entry = 120
      stop = 118
      risk_per_share = 2
      max risk = 50
      qty = 50 // 2 = 25 shares
    """
    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share <= 0:
        return 0

    qty = int(risk_per_trade // risk_per_share)
    return max(qty, 0)


def size_by_capital(capital: float, price: float) -> int:
    """
    Buys the maximum shares possible with given capital.
    """
    if capital <= 0:
        return 0
    return int(capital // price)
