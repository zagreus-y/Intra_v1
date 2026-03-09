import pandas as pd
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from backtest.engine import BacktestEngine
from strategies.sma_intraday import SMAIntraday
from strategies.vwap_scalper import VWAPScalper
from data.smartapi_data import SmartAPIDataProvider


# ---------------------------------------------------
# Step 1: Fetch Intraday Historical Data from SmartAPI
# ---------------------------------------------------
import os

API_KEY = os.getenv("API_KEY")
CLIENT_CODE = os.getenv("CLIENT_CODE")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET")
print("Using API_KEY:", API_KEY)

SYMBOL = "TATASTEEL"
SYMBOL_TOKEN = "3499"   # You must map symbols → tokens later
EXCHANGE = "NSE"

print("Connecting to SmartAPI...")
dp = SmartAPIDataProvider(API_KEY, CLIENT_CODE, PASSWORD, TOTP_SECRET)

candles = dp.get_intraday_candles(
    symbol_token=SYMBOL_TOKEN,
    exchange=EXCHANGE,
    interval="FIVE_MINUTE",
    lookback_days=5
)

if not candles:
    print("No data found.")
    exit()

# Convert to DataFrame
df = pd.DataFrame(candles, columns=[
    "datetime", "open", "high", "low", "close", "volume"
])

df["datetime"] = pd.to_datetime(df["datetime"])
df.set_index("datetime", inplace=True)
df = df.astype(float)

print(f"Loaded {len(df)} candles")


# ---------------------------------------------------
# Step 2: Run SMA backtest
# ---------------------------------------------------

print("\n=== Running SMA Intraday Backtest ===")

engine1 = BacktestEngine(
    strategy_cls=SMAIntraday,
    strategy_config={"fast": 5, "slow": 20, "symbol": SYMBOL},
    starting_cash=10000,
    slippage=0.0005,
    commission_per_trade=2.0
)

result1 = engine1.run(df)

print("Final Cash:", result1["final_cash"])
print("PnL:", result1["pnl"])
print("Win Rate:", result1["win_rate"])
print("Max Drawdown:", result1["max_drawdown"])
print("Trades:", len(result1["trades"]))
print(result1["trades"][:5])


# ---------------------------------------------------
# Step 3: Run VWAP Scalper Backtest
# ---------------------------------------------------

print("\n=== Running VWAP Scalper Backtest ===")

engine2 = BacktestEngine(
    strategy_cls=VWAPScalper,
    strategy_config={"symbol": SYMBOL},
    starting_cash=10000,
    slippage=0.0005,
    commission_per_trade=2.0
)

result2 = engine2.run(df)

print("Final Cash:", result2["final_cash"])
print("PnL:", result2["pnl"])
print("Win Rate:", result2["win_rate"])
print("Max Drawdown:", result2["max_drawdown"])
print("Trades:", len(result2["trades"]))
print(result2["trades"][:5])