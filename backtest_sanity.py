import pandas as pd

from backtest.engine import BacktestEngine
from strategies.sma_intraday import SMAIntraday
from strategies.vwap_scalper import VWAPScalper
from data.nse_data import NSEDataHybrid
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)


# ---------------------------------------------------
# Step 1: Get historical data (bars) for backtesting
# ---------------------------------------------------
dp = NSEDataHybrid()

symbol = "TATASTEEL"

# daily for now — intraday works too if you request 5m/1m (yfinance fallback)
df = dp.get_historical("TATASTEEL", interval="5m", days=30)


if df.empty:
    print("No data found.")
    exit()

# ---------------------------------------------------
# Step 2: Run SMA backtest
# ---------------------------------------------------
print("\n=== Running SMA Intraday Backtest ===")
engine1 = BacktestEngine(
    strategy_cls=SMAIntraday,
    strategy_config={"fast": 5, "slow": 20, "symbol": symbol},
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
    strategy_config={"symbol": symbol},
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
