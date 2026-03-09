"""
Enhanced Backtest Example
Using PortfolioBacktestEngineV2 with advanced metrics
"""

import pandas as pd
from data.smartapi_data import SmartAPIDataProvider
from backtest.portfolio_backtest_v2 import PortfolioBacktestEngineV2
from strategies.sma_intraday import SMAIntraday
import os


# ========== CONFIG ==========
API_KEY = os.getenv("API_KEY")
CLIENT_CODE = os.getenv("CLIENT_CODE")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET")

TOTAL_CAPITAL = 100000
MAX_POSITIONS = 5
MAX_TRADES_PER_DAY = 10

STOCKS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "MARUTI"]

# ========== FETCH DATA ==========
print("Connecting to SmartAPI...")
data_provider = SmartAPIDataProvider(API_KEY, CLIENT_CODE, PASSWORD, TOTP_SECRET)

multi_stock_data = {}

for symbol in STOCKS:
    try:
        print(f"Fetching {symbol}...")
        df = data_provider.get_candles(symbol, interval="5m", lookback_days=10)
        
        if df.empty:
            print(f"⚠ Skipping {symbol} (no data)")
            continue
        
        multi_stock_data[symbol] = df
        print(f"✓ {symbol}: {len(df)} candles")
    
    except Exception as e:
        print(f"✗ {symbol}: {e}")
        continue

if not multi_stock_data:
    print("No data fetched. Exiting.")
    exit(1)

# ========== RUN BACKTEST ==========
print(f"\nBacktesting {len(multi_stock_data)} stocks...\n")

engine = PortfolioBacktestEngineV2(
    strategy_cls=SMAIntraday,
    strategy_config={
        "fast": 5,
        "slow": 20,
    },
    total_capital=TOTAL_CAPITAL,
    max_positions=MAX_POSITIONS,
    max_trades_per_day=MAX_TRADES_PER_DAY,
    slippage=0.0005
)

results = engine.run(multi_stock_data)

# ========== RESULTS ==========
print("\n" + "="*60)
print("BACKTEST RESULTS")
print("="*60)
print(f"Initial Capital:     ₹{TOTAL_CAPITAL:,.2f}")
print(f"Final Capital:       ₹{results['final_cash']:,.2f}")
print(f"Net P&L:             ₹{results['net_pnl']:,.2f}")
print(f"Return:              {results['total_return']*100:.2f}%")
print()
print(f"Total Trades:        {results['total_trades']}")
print(f"Winning Trades:      {results['winning_trades']}")
print(f"Losing Trades:       {results['losing_trades']}")
print(f"Win Rate:            {results['win_rate']*100:.2f}%")
print()
print(f"Avg Win:             ₹{results['avg_win']:,.2f}")
print(f"Avg Loss:            ₹{results['avg_loss']:,.2f}")
print(f"Profit Factor:       {results['profit_factor']:.2f}x")
print(f"Max Drawdown:        {results['max_drawdown']*100:.2f}%")
print(f"Sharpe Ratio:        {results['sharpe_ratio']:.2f}")
print("="*60)

# ========== TRADE DETAILS ==========
print("\nDetailed Trades:")
print("-" * 100)

trades_df = pd.DataFrame(results['trade_log'])
trades_df = trades_df[['timestamp', 'symbol', 'side', 'qty', 'price', 'pnl', 'pnl_percent']]
print(trades_df.to_string(index=False))