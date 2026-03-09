"""
Multi-Signal Hybrid Strategy Backtest

This is the recommended strategy combining:
- Trend filtering (trade with trend only)
- Multi-signal confirmation (2+ confirmations required)
- Better entry/exit logic

Expected results: 55-65% win rate, better profit factor
"""

import pandas as pd
from data.smartapi_data import SmartAPIDataProvider
from backtest.portfolio_backtest_v2 import PortfolioBacktestEngineV2
from strategies.multi_signal_hybrid import MultiSignalHybrid
from data.instrument_mapper import AngelInstrumentMapper
import os

# ========== CONFIG ==========
API_KEY = os.getenv("API_KEY")
CLIENT_CODE = os.getenv("CLIENT_CODE")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET")

TOTAL_CAPITAL = 100000
MAX_POSITIONS = 5
MAX_TRADES_PER_DAY = 15

# Stock pool (50-100 stocks as you mentioned)
STOCKS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "MARUTI", "BAJAJFINSV", "LT", "ITC", "WIPRO",
    "HDFC", "SUNPHARMA", "ASIANPAINT", "DRREDDY", "HEROMOTOCO",
    "SBIN", "AXISBANK", "KOTAKBANK", "INDUSIND", "BAJAJFINSV"
]

# ========== FETCH DATA ==========
print("="*70)
print("Multi-Signal Hybrid Strategy Backtest")
print("="*70)
print("\nConnecting to SmartAPI...")

try:
    data_provider = SmartAPIDataProvider(API_KEY, CLIENT_CODE, PASSWORD, TOTP_SECRET)
except Exception as e:
    print(f"✗ SmartAPI connection failed: {e}")
    print("Make sure API_KEY, CLIENT_CODE, PASSWORD, TOTP_SECRET are set in environment")
    exit(1)

multi_stock_data = {}

for symbol in STOCKS:
    try:
        print(f"Fetching {symbol}...", end=" ")
        df = data_provider.get_candles(symbol, interval="5m", lookback_days=15)
        
        if df.empty:
            print("✗ (no data)")
            continue
        
        multi_stock_data[symbol] = df
        print(f"✓ ({len(df)} candles)")
    
    except Exception as e:
        print(f"✗ ({str(e)[:50]})")
        continue

if not multi_stock_data:
    print("\n✗ No data fetched. Exiting.")
    exit(1)

print(f"\n✓ Successfully loaded data for {len(multi_stock_data)} stocks\n")

# ========== RUN BACKTEST ==========
print("Running backtest with Multi-Signal Hybrid strategy...")
print("-"*70)

engine = PortfolioBacktestEngineV2(
    strategy_cls=MultiSignalHybrid,
    strategy_config={
        "fast_sma": 8,
        "slow_sma": 20,
        "rsi_period": 14,
        "rsi_oversold": 35,
        "rsi_overbought": 65,
        "volume_lookback": 20,
        "vwap_deviation": 2.5
    },
    total_capital=TOTAL_CAPITAL,
    max_positions=MAX_POSITIONS,
    max_trades_per_day=MAX_TRADES_PER_DAY,
    min_trade_value=3000.0,        # ₹3000 minimum per trade (avoids fragmentation)
    warmup_candles=20,             # Ignore first 20 candles per day (let indicators stabilize)
    intraday_only=True,            # Square off all positions at EOD
    dynamic_slippage=True          # Scale slippage by price tier
)

result = engine.run(multi_stock_data)

# ========== RESULTS ==========
print("\n" + "="*70)
print("BACKTEST RESULTS")
print("="*70)

print(f"\nCapital Performance:")
print(f"  Initial:        ₹{TOTAL_CAPITAL:>12,.2f}")
print(f"  Final:          ₹{result['final_cash']:>12,.2f}")
print(f"  Net P&L:        ₹{result['net_pnl']:>12,.2f}")
print(f"  Return:         {result['total_return']*100:>12.2f}%")

print(f"\nTrade Statistics:")
print(f"  Total Trades:   {result['total_trades']:>12}")
print(f"  Winning Trades: {result['winning_trades']:>12}")
print(f"  Losing Trades:  {result['losing_trades']:>12}")
print(f"  Win Rate:       {result['win_rate']*100:>12.1f}%")
print(f"  Breakeven:      {result['breakeven_trades']:>12}")

print(f"\nPnL Metrics:")
print(f"  Avg Win:        ₹{result['avg_win']:>12,.2f}")
print(f"  Avg Loss:       ₹{result['avg_loss']:>12,.2f}")
print(f"  Largest Win:    ₹{result['largest_win']:>12,.2f}")
print(f"  Largest Loss:   ₹{result['largest_loss']:>12,.2f}")
print(f"  Profit Factor:  {result['profit_factor']:>12.2f}x")

print(f"\nRisk Metrics:")
print(f"  Max Drawdown:   {result['max_drawdown']*100:>12.2f}%")
print(f"  Sharpe Ratio:   {result['sharpe_ratio']:>12.2f}")
print(f"  Total Brokerage:₹{result['total_brokerage']:>12,.2f}")

print("="*70)

# ========== ANALYSIS & RECOMMENDATIONS ==========
print("\n" + "="*70)
print("ANALYSIS")
print("="*70)

if result['win_rate'] > 0.50:
    print("✅ Win rate > 50% - Strategy is profitable long-term")
elif result['win_rate'] > 0.40:
    print("⚠️  Win rate 40-50% - Acceptable with good profit factor")
else:
    print("❌ Win rate < 40% - May need optimization")

if result['profit_factor'] > 1.5:
    print("✅ Profit factor > 1.5 - Strong profitability")
elif result['profit_factor'] > 1.0:
    print("⚠️  Profit factor 1.0-1.5 - Needs improvement")
else:
    print("❌ Profit factor < 1.0 - Not profitable")

if result['sharpe_ratio'] > 1.0:
    print("✅ Sharpe ratio > 1.0 - Good risk-adjusted returns")
elif result['sharpe_ratio'] > 0:
    print("⚠️  Sharpe ratio 0-1.0 - Acceptable")
else:
    print("❌ Sharpe ratio < 0 - Negative risk-adjusted returns")

if result['max_drawdown'] > -0.10:
    print("✅ Max drawdown < 10% - Good drawdown control")
else:
    print("⚠️  Max drawdown > 10% - Consider wider stoploss or position sizing")

print("\n" + "="*70)
print("RECOMMENDATIONS")
print("="*70)

print("""
Key Improvements Over Original SMA Strategy:
✓ Trend filtering reduces false signals
✓ Multi-signal confirmation (2+ required to trade)
✓ Better entry logic (Trend + RSI + Volume + VWAP alignment)
✓ Warmup period avoids early-session noise
✓ Minimum trade value prevents capital fragmentation

Next Steps:
1. If Win Rate > 50%: Test on paper trading for 1-2 weeks
2. If Profit Factor > 1.0: Ready for live trading with small capital
3. Optimize parameters:
   - Adjust fast_sma (currently 8) - try 5, 8, 10
   - Adjust slow_sma (currently 20) - try 15, 20, 25
   - Adjust stoploss % (currently 2%) - try 1.5%, 2%, 2.5%
4. Consider combining with other indicators (volume, moving average)
5. Test on different stocks to find optimal universe

Current Strategy Status:
""")

if result['net_pnl'] > 0 and result['win_rate'] > 0.45:
    print("🟢 READY FOR PAPER TRADING")
    print("   Deploy on paper broker for 5-10 trading days before live capital")
elif result['net_pnl'] > 0 or result['profit_factor'] > 1.0:
    print("🟡 PROMISING BUT NEEDS TUNING")
    print("   Try optimizing parameters or testing on larger dataset")
else:
    print("🔴 NEEDS IMPROVEMENT")
    print("   Adjust parameters or try different strategy (RSI, VWAP, Breakout)")
    print("   Run backtest_improved_strategies.py to compare all options")

print("\n" + "="*70)

# ========== SAVE TRADE LOG ==========
trades_df = pd.DataFrame(result['trade_log'])
if not trades_df.empty:
    trades_df = trades_df[['timestamp', 'symbol', 'side', 'qty', 'price', 'pnl', 'pnl_percent']]
    
    # Print sample trades
    print(f"\nSample Executed Trades ({min(5, len(trades_df))} of {len(trades_df)}):")
    print("-"*70)
    print(trades_df.head(5).to_string(index=False))
    
    # Save to CSV
    trades_df.to_csv("trade_log_latest.csv", index=False)
    print(f"\n✓ Full trade log saved to: trade_log_latest.csv")
