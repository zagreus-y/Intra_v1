import pandas as pd
from data.smartapi_data import SmartAPIDataProvider
from backtest.portfolio_backtest_v2 import PortfolioBacktestEngineV2
from strategies.sma_intraday import SMAIntraday

# -----------------------------------
# CONFIG
# -----------------------------------

import os

API_KEY = os.getenv("API_KEY")
CLIENT_CODE = os.getenv("CLIENT_CODE")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET")

EXCHANGE = "NSE"
INTERVAL = "FIVE_MINUTE"
LOOKBACK_DAYS = 5

TOTAL_CAPITAL = 10000
MAX_POSITIONS = 3
MAX_TRADES_PER_DAY = 10

# Example pool (replace with your real pool)
from data.instrument_mapper import AngelInstrumentMapper

mapper = AngelInstrumentMapper()

STOCKS = mapper.get_tokens([
    "RELIANCE",
    "TCS",
    "INFY",
    "HDFCBANK",
    "ICICIBANK"
])
# -----------------------------------
# FETCH DATA
# -----------------------------------
print("Connecting to SmartAPI...")
dp = SmartAPIDataProvider(API_KEY, CLIENT_CODE, PASSWORD, TOTP_SECRET)

multi_stock_data = {}

for symbol, token in STOCKS.items():
    print(f"Fetching {symbol}...")
    candles = dp.get_intraday_candles(
        symbol_token=token,
        symbol=symbol,  # Add this line
        exchange=EXCHANGE,
        interval=INTERVAL,
        lookback_days=LOOKBACK_DAYS
    )

    if not candles:
        print(f"Skipping {symbol} (no data)")
        continue

    df = pd.DataFrame(candles, columns=[
        "datetime", "open", "high", "low", "close", "volume"
    ])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)
    df = df.astype(float)

    multi_stock_data[symbol] = df

if not multi_stock_data:
    print("No data fetched.")
    exit()

print(f"\nLoaded data for {len(multi_stock_data)} stocks")

# -----------------------------------
# RUN PORTFOLIO BACKTEST
# -----------------------------------
print("\nRunning Portfolio Backtest...\n")

# Key improvements:
# - min_trade_value: Only trade if position size > ₹2000 (avoids capital fragmentation)
# - warmup_candles: Ignore first 20 candles per day (let indicators stabilize)
# - intraday_only: Square off all positions at EOD
# - dynamic_slippage: Scale slippage by stock price tier (large/mid/smallcap)

engine = PortfolioBacktestEngineV2(
    strategy_cls=SMAIntraday,
    strategy_config={
        "fast": 5,
        "slow": 20,
        "qty": 10
    },
    # brokerage_per_trade=lambda order_value: 0,
    total_capital=TOTAL_CAPITAL,
    max_positions=MAX_POSITIONS,
    max_trades_per_day=MAX_TRADES_PER_DAY,
    min_trade_value=2000.0,        # ₹2000 minimum per trade
    warmup_candles=20,              # Ignore first 20 candles per day
    intraday_only=True,             # Square off at EOD
    dynamic_slippage=True           # Adjust slippage by price tier
)

result = engine.run(multi_stock_data)

# -----------------------------------
# RESULTS
# -----------------------------------
print("\n========== RESULTS ==========")
print(f"Final Cash: ₹{result['final_cash']:.2f}")
print(f"Net PnL: ₹{result['net_pnl']:.2f}")
print(f"Return: {result['total_return']*100:.2f}%")
print(f"Win Rate: {result['win_rate']*100:.2f}%")
print(f"Total Trades: {result['total_trades']}")
print(f"Profit Factor: {result['profit_factor']:.2f}x")
print(f"Max Drawdown: {result['max_drawdown']*100:.2f}%")
print(f"Sharpe Ratio: {result['sharpe_ratio']:.2f}")
print("================================")

print("\n" + "="*70)
print("BACKTEST RESULTS")
print("="*70)
print(f"Initial Capital:     ₹{TOTAL_CAPITAL:,.2f}")
print(f"Final Capital:       ₹{result['final_cash']:,.2f}")
print(f"Net P&L:             ₹{result['net_pnl']:,.2f}")
print(f"Return:              {result['total_return']*100:.2f}%")
print()
print(f"Total Trades:        {result['total_trades']}")
print(f"Winning Trades:      {result['winning_trades']}")
print(f"Losing Trades:       {result['losing_trades']}")
print(f"Breakeven Trades:    {result['breakeven_trades']}")
print(f"Win Rate:            {result['win_rate']*100:.2f}%")
print()
print(f"Avg Win:             ₹{result['avg_win']:,.2f}")
print(f"Avg Loss:            ₹{result['avg_loss']:,.2f}")
print(f"Largest Win:         ₹{result['largest_win']:,.2f}")
print(f"Largest Loss:        ₹{result['largest_loss']:,.2f}")
print(f"Profit Factor:       {result['profit_factor']:.2f}x")
print()
print(f"Max Drawdown:        {result['max_drawdown']*100:.2f}%")
print(f"Sharpe Ratio:        {result['sharpe_ratio']:.2f}")
print(f"Total Brokerage:     ₹{result['total_brokerage']:,.2f}")
print("="*70)