import pandas as pd
from data.smartapi_data import SmartAPIDataProvider
from backtest.portfolio_engine import PortfolioBacktestEngine
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

engine = PortfolioBacktestEngine(
    strategy_cls=SMAIntraday,
    strategy_config={
        "fast": 5,
        "slow": 20,
        "qty": 10
    },
    total_capital=TOTAL_CAPITAL,
    max_positions=MAX_POSITIONS,
    max_trades_per_day=MAX_TRADES_PER_DAY
)

result = engine.run(multi_stock_data)

# -----------------------------------
# RESULTS
# -----------------------------------
print("\n========== RESULTS ==========")
print(f"Final Cash: ₹{result['final_cash']:.2f}")
print(f"Net PnL: ₹{result['pnl']:.2f}")
print(f"Win Rate: {result['win_rate']*100:.2f}%")
print(f"Total Trades: {result['total_trades']}")
print(f"Brokerage Paid: ₹{result['brokerage_paid']:.2f}")
print("================================")