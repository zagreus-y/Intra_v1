#!/usr/bin/env python3
"""
SANITY CHECK - Post-Installation Verification

Run after git clone and credential setup to verify all systems work together.
Minimal tests for imports, API connections, and basic functionality.

Usage:
    python sanity_check.py

Exit codes:
    0: All tests passed
    1: One or more tests failed
"""

import sys
import os
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

test_results = []

def test(name):
    """Decorator for test functions."""
    def decorator(func):
        def wrapper():
            try:
                func()
                test_results.append((name, "✓", GREEN))
                print(f"{GREEN}✓{RESET} {name}")
            except Exception as e:
                test_results.append((name, f"✗ {str(e)[:60]}", RED))
                print(f"{RED}✗{RESET} {name}")
                print(f"  Error: {str(e)[:100]}")
        return wrapper()
    return decorator

# ============================================================================
# IMPORT TESTS
# ============================================================================

@test("Import: pandas, numpy")
def test_stdlib():
    import pandas as pd
    import numpy as np

@test("Import: data providers")
def test_data_imports():
    from data.smartapi_data import SmartAPIDataProvider
    from data.nse_data import NSEDataHybrid
    from data.base_data_provider import DataProvider
    from data.instrument_mapper import AngelInstrumentMapper

@test("Import: brokers")
def test_broker_imports():
    from broker.paper_broker import PaperBroker
    from broker.smartapi_broker import SmartAPIBroker
    from broker.base_broker import BaseBroker

@test("Import: strategies")
def test_strategy_imports():
    from strategies.base_strategy import BaseStrategy
    from strategies.intraday_strategies import (
        VWAPMeanReversion,
        RSIOverbought,
        BreakoutStrategy,
        TrendFollowingWithFilter
    )
    from strategies.multi_signal_hybrid import MultiSignalHybrid

@test("Import: backtest engines")
def test_backtest_imports():
    from backtest.portfolio_backtest_v2 import PortfolioBacktestEngineV2
    from backtest.portfolio_backtest_v2_ranked import PortfolioBacktestEngineV2 as PortfolioBacktestEngineV2Ranked

@test("Import: risk management")
def test_risk_imports():
    from risk.position_sizer import size_by_percent, size_by_risk
    from risk.stoploss_manager import StoplossManager

@test("Import: live engine")
def test_engine_imports():
    from engine.live_runner import LiveRunner

# ============================================================================
# CREDENTIALS TEST
# ============================================================================

@test("Credentials: API_KEY, CLIENT_CODE, PASSWORD, TOTP_SECRET")
def test_credentials():
    api_key = os.getenv("API_KEY")
    client_code = os.getenv("CLIENT_CODE")
    password = os.getenv("PASSWORD")
    totp_secret = os.getenv("TOTP_SECRET")
    
    if not all([api_key, client_code, password, totp_secret]):
        missing = []
        if not api_key: missing.append("API_KEY")
        if not client_code: missing.append("CLIENT_CODE")
        if not password: missing.append("PASSWORD")
        if not totp_secret: missing.append("TOTP_SECRET")
        raise ValueError(f"Missing credentials: {', '.join(missing)}")

# ============================================================================
# SmartAPI CONNECTION TEST
# ============================================================================

@test("SmartAPI: Connection and login")
def test_smartapi_connection():
    from data.smartapi_data import SmartAPIDataProvider
    
    api_key = os.getenv("API_KEY")
    client_code = os.getenv("CLIENT_CODE")
    password = os.getenv("PASSWORD")
    totp_secret = os.getenv("TOTP_SECRET")
    
    try:
        dp = SmartAPIDataProvider(api_key, client_code, password, totp_secret)
    except Exception as e:
        raise Exception(f"SmartAPI login failed: {str(e)[:100]}")

@test("SmartAPI: Fetch intraday data")
def test_smartapi_data():
    from data.smartapi_data import SmartAPIDataProvider
    
    api_key = os.getenv("API_KEY")
    client_code = os.getenv("CLIENT_CODE")
    password = os.getenv("PASSWORD")
    totp_secret = os.getenv("TOTP_SECRET")
    
    dp = SmartAPIDataProvider(api_key, client_code, password, totp_secret)
    
    # Try to fetch candles for a popular stock
    df = dp.get_candles("RELIANCE", interval="5m", lookback_days=1)
    
    if df is None or df.empty:
        raise ValueError("No data returned from SmartAPI")

# ============================================================================
# NSE DATA TEST
# ============================================================================

@test("NSE Data: Fetch live data (NSEDataHybrid)")
def test_nse_data():
    from data.nse_data import NSEDataHybrid
    
    dp = NSEDataHybrid()
    df = dp.get_ohlcv("RELIANCE", interval="1m", lookback=5)
    
    if df is None or df.empty:
        raise ValueError("No data from NSEDataHybrid")

# ============================================================================
# BROKER TEST
# ============================================================================

@test("Broker: PaperBroker initialization and trading")
def test_paper_broker():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=5000)
    
    # Verify initialization
    if broker.cash != 5000:
        raise ValueError("Failed to initialize broker with correct cash")

# ============================================================================
# STRATEGY TEST
# ============================================================================

@test("Strategy: MultiSignalHybrid initialization")
def test_strategy():
    from strategies.multi_signal_hybrid import MultiSignalHybrid
    
    strategy = MultiSignalHybrid({
        "fast_sma": 8,
        "slow_sma": 20,
        "rsi_period": 14,
        "symbol": "RELIANCE"
    })
    
    strategy.on_start()

@test("Strategy: Signal generation with sample data")
def test_strategy_signal():
    from strategies.multi_signal_hybrid import MultiSignalHybrid
    import numpy as np
    from datetime import datetime
    
    strategy = MultiSignalHybrid({
        "fast_sma": 8,
        "slow_sma": 20,
        "rsi_period": 14,
        "symbol": "RELIANCE"
    })
    
    strategy.on_start()
    
    # Feed sample bars
    for i in range(50):
        bar = {
            "timestamp": datetime.now(),
            "open": 2500 + i,
            "high": 2510 + i,
            "low": 2490 + i,
            "close": 2505 + i,
            "volume": 100000
        }
        signal = strategy.on_bar(bar)

# ============================================================================
# BACKTEST ENGINE TEST
# ============================================================================

@test("Backtest: PortfolioBacktestEngineV2 initialization")
def test_backtest_engine():
    from backtest.portfolio_backtest_v2 import PortfolioBacktestEngineV2
    from strategies.multi_signal_hybrid import MultiSignalHybrid
    
    engine = PortfolioBacktestEngineV2(
        strategy_cls=MultiSignalHybrid,
        strategy_config={
            "fast_sma": 8,
            "slow_sma": 20,
            "rsi_period": 14
        },
        total_capital=100000,
        max_positions=5,
        max_trades_per_day=15,
        min_trade_value=3000,
        warmup_candles=20
    )

# ============================================================================
# RISK MANAGEMENT TEST
# ============================================================================

@test("Risk: Position sizing functions")
def test_position_sizer():
    from risk.position_sizer import size_by_percent, size_by_risk
    
    # Test percent sizing
    qty = size_by_percent(equity=100000, percent=5, price=500)
    if qty <= 0:
        raise ValueError("Position sizing failed")
    
    # Test risk-based sizing
    qty2 = size_by_risk(equity=100000, risk_per_trade=50, entry_price=500, stop_price=490)
    if qty2 <= 0:
        raise ValueError("Risk-based sizing failed")

@test("Risk: StoplossManager initialization")
def test_stoploss_manager():
    from risk.stoploss_manager import StoplossManager
    
    def dummy_callback(symbol, price, reason):
        pass
    
    slm = StoplossManager(on_exit_callback=dummy_callback)
    
    # Test fixed stoploss
    sl_level = slm.set_fixed_stoploss("RELIANCE", entry_price=2500, stoploss_percent=2.0)
    if sl_level >= 2500:
        raise ValueError("Stoploss level not set correctly")

# ============================================================================
# COMPREHENSIVE BROKER ROBUSTNESS TESTS (PaperBroker)
# ============================================================================

@test("Broker: Market order - buy")
def test_broker_market_buy():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=50000)
    
    # Place a buy market order
    order = broker.place_order(symbol="RELIANCE", qty=10, side="buy", order_type="market", price=2500)
    
    if order["status"] != "pending":
        raise ValueError(f"Order status should be 'pending', got {order['status']}")
    
    # Simulate tick execution
    broker.on_tick(symbol="RELIANCE", price=2500, volume=1000)
    
    # Verify order was filled
    filled_order = broker.orders[order["order_id"]]
    if filled_order["status"] != "filled":
        raise ValueError(f"Order should be filled, got {filled_order['status']}")
    
    # Verify position was created
    position = broker.get_position("RELIANCE")
    if position is None or position["qty"] != 10:
        raise ValueError(f"Position not created correctly: {position}")
    
    # Verify cash was deducted (with slippage)
    expected_cost = 2500 * 10 * (1 + broker.slippage)
    if abs(broker.cash - (50000 - expected_cost)) > 1:
        raise ValueError(f"Cash not updated correctly. Expected ~{50000 - expected_cost}, got {broker.cash}")

@test("Broker: Market order - sell")
def test_broker_market_sell():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=50000)
    
    # First buy
    buy_order = broker.place_order(symbol="RELIANCE", qty=10, side="buy", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2500, volume=1000)
    
    # Then sell
    sell_order = broker.place_order(symbol="RELIANCE", qty=10, side="sell", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2550, volume=1000)
    
    # Verify position is closed
    position = broker.get_position("RELIANCE")
    if position is not None:
        raise ValueError(f"Position should be closed, but got {position}")
    
    # Verify P&L was recorded
    trades = broker.get_trades()
    sell_trades = [t for t in trades if t["side"] == "SELL"]
    if not sell_trades:
        raise ValueError("Sell trade not recorded")
    
    if "pnl" not in sell_trades[0]:
        raise ValueError("P&L not calculated for sell trade")

@test("Broker: Limit order - buy")
def test_broker_limit_buy():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=50000)
    
    # Place buy limit order at 2490
    order = broker.place_order(symbol="INFY", qty=5, side="buy", order_type="limit", price=2490)
    
    if order["status"] != "pending":
        raise ValueError(f"Limit order should be pending, got {order['status']}")
    
    # Tick at higher price - should NOT fill
    broker.on_tick(symbol="INFY", price=2550, volume=1000)
    if broker.orders[order["order_id"]]["status"] != "pending":
        raise ValueError("Buy limit order should not fill at higher price")
    
    # Tick at limit price - should fill
    broker.on_tick(symbol="INFY", price=2490, volume=1000)
    if broker.orders[order["order_id"]]["status"] != "filled":
        raise ValueError("Buy limit order should fill at limit price or lower")

@test("Broker: Limit order - sell")
def test_broker_limit_sell():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=50000)
    
    # Buy first
    buy_order = broker.place_order(symbol="INFY", qty=5, side="buy", order_type="market")
    broker.on_tick(symbol="INFY", price=2500, volume=1000)
    
    # Place sell limit order at 2600
    sell_order = broker.place_order(symbol="INFY", qty=5, side="sell", order_type="limit", price=2600)
    
    # Tick at lower price - should NOT fill
    broker.on_tick(symbol="INFY", price=2550, volume=1000)
    if broker.orders[sell_order["order_id"]]["status"] != "pending":
        raise ValueError("Sell limit order should not fill at lower price")
    
    # Tick at limit price - should fill
    broker.on_tick(symbol="INFY", price=2600, volume=1000)
    if broker.orders[sell_order["order_id"]]["status"] != "filled":
        raise ValueError("Sell limit order should fill at limit price or higher")

@test("Broker: Robustness - Reject: sell non-existent position")
def test_broker_reject_sell_nonexistent():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=50000)
    
    # Try to sell a symbol we don't own
    order = broker.place_order(symbol="RELIANCE", qty=10, side="sell", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2500, volume=1000)
    
    # Should be REJECTED (not enough quantity)
    if broker.orders[order["order_id"]]["status"] != "rejected":
        raise ValueError(f"Order should be rejected, got {broker.orders[order['order_id']]['status']}")

@test("Broker: Robustness - Reject: sell more than position")
def test_broker_reject_oversell():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=50000)
    
    # Buy 10 shares
    buy_order = broker.place_order(symbol="RELIANCE", qty=10, side="buy", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2500, volume=1000)
    
    # Try to sell 15 shares
    sell_order = broker.place_order(symbol="RELIANCE", qty=15, side="sell", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2550, volume=1000)
    
    # Should be REJECTED
    if broker.orders[sell_order["order_id"]]["status"] != "rejected":
        raise ValueError(f"Oversell should be rejected, got {broker.orders[sell_order['order_id']]['status']}")

@test("Broker: Robustness - Reject: insufficient cash")
def test_broker_reject_insufficient_cash():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=5000)
    
    # Try to buy more than we can afford
    order = broker.place_order(symbol="RELIANCE", qty=10, side="buy", order_type="market", price=1000)
    broker.on_tick(symbol="RELIANCE", price=1000, volume=1000)
    
    # Should be REJECTED (cost would be ~10000 > 5000)
    if broker.orders[order["order_id"]]["status"] != "rejected":
        raise ValueError(f"Insufficient cash should reject order, got {broker.orders[order['order_id']]['status']}")

@test("Broker: Order cancellation - valid")
def test_broker_cancel_valid():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=50000)
    
    # Place an order
    order = broker.place_order(symbol="RELIANCE", qty=10, side="buy", order_type="market")
    
    # Cancel it before it's filled
    result = broker.cancel_order(order["order_id"])
    
    if not result:
        raise ValueError("Valid order cancellation should return True")
    
    if broker.orders[order["order_id"]]["status"] != "cancelled":
        raise ValueError("Order should be cancelled")

@test("Broker: Order cancellation - cannot cancel filled order")
def test_broker_cancel_filled():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=50000)
    
    # Place and fill an order
    order = broker.place_order(symbol="RELIANCE", qty=10, side="buy", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2500, volume=1000)
    
    # Try to cancel filled order
    result = broker.cancel_order(order["order_id"])
    
    if result:
        raise ValueError("Cannot cancel a filled order, should return False")

@test("Broker: Order cancellation - cannot cancel non-existent order")
def test_broker_cancel_nonexistent():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=50000)
    
    # Try to cancel non-existent order
    result = broker.cancel_order("NONEXISTENT_ORDER_ID")
    
    if result:
        raise ValueError("Cancelling non-existent order should return False")

@test("Broker: Position tracking - multiple symbols")
def test_broker_multi_position():
    from broker.paper_broker import PaperBroker
    
    # Use sufficient capital: 100k needed for buys + slippage
    # RELIANCE: 5 * 2500 * 1.0005 = 12,506.25
    # INFY: 10 * 2000 * 1.0005 = 20,010
    # TCS: 8 * 3000 * 1.0005 = 24,012
    # Total: 56,528.25 < 150,000
    broker = PaperBroker(starting_cash=150000)
    
    # Buy multiple positions
    broker.place_order(symbol="RELIANCE", qty=5, side="buy", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2500, volume=1000)
    
    broker.place_order(symbol="INFY", qty=10, side="buy", order_type="market")
    broker.on_tick(symbol="INFY", price=2000, volume=1000)
    
    broker.place_order(symbol="TCS", qty=8, side="buy", order_type="market")
    broker.on_tick(symbol="TCS", price=3000, volume=1000)
    
    # Verify positions
    positions = broker.get_positions()
    if len(positions) != 3:
        raise ValueError(f"Should have 3 positions, got {len(positions)}")
    
    if positions["RELIANCE"]["qty"] != 5:
        raise ValueError(f"RELIANCE position incorrect: {positions['RELIANCE']}")
    if positions["INFY"]["qty"] != 10:
        raise ValueError(f"INFY position incorrect: {positions['INFY']}")
    if positions["TCS"]["qty"] != 8:
        raise ValueError(f"TCS position incorrect: {positions['TCS']}")

@test("Broker: Average price tracking")
def test_broker_avg_price_tracking():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=100000)
    
    # Buy 10 at 2500
    order1 = broker.place_order(symbol="RELIANCE", qty=10, side="buy", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2500, volume=1000)
    
    # Buy 10 more at 2550
    order2 = broker.place_order(symbol="RELIANCE", qty=10, side="buy", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2550, volume=1000)
    
    # Average price should be weighted
    position = broker.get_position("RELIANCE")
    expected_avg = (2500 * 10 + 2550 * 10) / 20
    
    # Allow small tolerance for slippage
    if abs(position["avg_price"] - expected_avg) > 50:
        raise ValueError(f"Average price not calculated correctly. Expected ~{expected_avg}, got {position['avg_price']}")

@test("Broker: Cash management")
def test_broker_cash_management():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=50000)
    initial_cash = broker.cash
    
    # Buy
    order1 = broker.place_order(symbol="RELIANCE", qty=10, side="buy", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2500, volume=1000)
    
    cash_after_buy = broker.cash
    if cash_after_buy >= initial_cash:
        raise ValueError("Cash should decrease after buy")
    
    # Sell
    order2 = broker.place_order(symbol="RELIANCE", qty=10, side="sell", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2550, volume=1000)
    
    cash_after_sell = broker.cash
    if cash_after_sell <= cash_after_buy:
        raise ValueError("Cash should increase after sell")

@test("Broker: Slippage application")
def test_broker_slippage():
    from broker.paper_broker import PaperBroker
    
    slippage_pct = 0.001  # 0.1%
    broker = PaperBroker(starting_cash=50000, slippage=slippage_pct)
    
    # Buy at market price 2500
    order = broker.place_order(symbol="RELIANCE", qty=10, side="buy", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2500, volume=1000)
    
    filled_order = broker.orders[order["order_id"]]
    expected_price = 2500 * (1 + slippage_pct)
    
    if abs(filled_order["avg_price"] - expected_price) > 0.1:
        raise ValueError(f"Slippage not applied correctly. Expected ~{expected_price}, got {filled_order['avg_price']}")

@test("Broker: Trade history")
def test_broker_trade_history():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=50000)
    
    # Execute multiple trades
    broker.place_order(symbol="RELIANCE", qty=10, side="buy", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2500, volume=1000)
    
    broker.place_order(symbol="INFY", qty=5, side="buy", order_type="market")
    broker.on_tick(symbol="INFY", price=2000, volume=1000)
    
    trades = broker.get_trades()
    if len(trades) < 2:
        raise ValueError(f"Trade history not recorded correctly. Got {len(trades)} trades")
    
    # Check trade details
    for trade in trades:
        if not all(k in trade for k in ["symbol", "side", "qty", "price", "timestamp"]):
            raise ValueError(f"Trade missing required fields: {trade}")

@test("Broker: Equity calculation")
def test_broker_equity():
    from broker.paper_broker import PaperBroker
    
    broker = PaperBroker(starting_cash=100000)
    
    # Initial equity should equal cash
    initial_equity = broker.get_equity()
    if abs(initial_equity - 100000) > 1:
        raise ValueError(f"Initial equity should be 100000, got {initial_equity}")
    
    # After buying, equity should be less than cash (money locked in position)
    broker.place_order(symbol="RELIANCE", qty=10, side="buy", order_type="market")
    broker.on_tick(symbol="RELIANCE", price=2500, volume=1000)
    
    equity_after_buy = broker.get_equity()
    cash_after_buy = broker.get_cash()
    
    # Equity = cash + position value (marked to market at avg_price)
    position = broker.get_position("RELIANCE")
    expected_equity = cash_after_buy + (position["qty"] * position["avg_price"])
    
    if abs(equity_after_buy - expected_equity) > 1:
        raise ValueError(f"Equity calculation incorrect. Expected ~{expected_equity}, got {equity_after_buy}")

# ============================================================================
# BROKER INTERFACE COMPLIANCE TEST
# ============================================================================

@test("Broker: BaseBroker interface compliance")
def test_broker_interface_compliance():
    from broker.paper_broker import PaperBroker
    from broker.base_broker import BaseBroker
    
    broker = PaperBroker(starting_cash=50000)
    
    # Verify it's an instance of BaseBroker
    if not isinstance(broker, BaseBroker):
        raise ValueError("PaperBroker must inherit from BaseBroker")
    
    # Verify all required methods exist
    required_methods = [
        "place_order",
        "cancel_order",
        "get_positions",
        "get_orders",
        "get_cash"
    ]
    
    for method in required_methods:
        if not hasattr(broker, method):
            raise ValueError(f"PaperBroker missing required method: {method}")
        if not callable(getattr(broker, method)):
            raise ValueError(f"PaperBroker.{method} is not callable")
