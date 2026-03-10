# Intraday Algo Trading Framework

A professional, modular intraday trading framework for NSE equities with SmartAPI (Angel One) integration.

## 🎯 Quick Start

### 1. Setup Environment
For Windows: Edit setup.ps1 to fill your credentials
Run ./setup.ps1 
if error: 
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
For Linux set environment variables:
```bash
set API_KEY=your_angel_api_key
set CLIENT_CODE=your_client_code  
set PASSWORD=your_trading_pin
set TOTP_SECRET=your_totp_secret
```
install requirements txt

### 2. Run Backtest

```bash
#Sanity Check
python sanity_check.py
python backtest_all_strategies.py
```

### 3. If Results Look Good
- Deploy to **Paper Trading** (next phase)
- Then go **Live** with real capital

---

## 📁 Project Structure

### Core Files
- **`backtest_all_strategies.py`** - Main entry point for backtesting
  - Test IntradayStrategies from ./strategies on 5m Candles for past 15 days, for a pool of hardcoded 20 stocks.
  - Change this file for customization

### Engines & Brokers
- **`backtest/portfolio_backtest_v2.py`** - Advanced backtest engine
  - Multi-symbol support
  - Daily position square-off (intraday)
  - Warmup period (avoids false signals)
  - Dynamic capital allocation
  
- **`broker/paper_broker_v2.py`** - Paper trading simulator
  - only skeleton/ todo

- **`broker/smartapi_broker.py`** - Real broker (Angel One)
  - only skeleton/ todo

### Data Providers
- **`data/base_data_provider.py`** - Abstract interface
- **`data/smartapi_data.py`** - Angel One implementation
  - Fetch OHLCV candles
  - LTP quotes
  - Market hours check

### Strategies
- **`strategies/intraday_strategies.py`** - Alternative strategies
  - `TrendFollowingWithFilter`
  - `VWAPMeanReversion`
  - `RSIOverbought`
  - `BreakoutStrategy`

- **`strategies/base_strategy.py`** - Abstract base for all strategies
- **`strategies/trend_filter.py`** - Trend detection helper
- **`strategies/signal_ranker.py`** - Stock competition ranking

### Risk Management
- **`risk/position_sizer.py`** - Position sizing utilities
- **`risk/stoploss_manager.py`** - Stoploss handling

---

## 🚀 Key Features

### Engine Improvements
✅ **Daily Management**
- Square-off all positions at EOD
- Reset strategies daily
- Reset daily counters

✅ **Signal Quality**
- Warmup period (ignore first N candles)
  - Prevents SMA/RSI false signals
  - Let indicators stabilize
- Minimum trade value (₹3000 default)
  - Prevents capital fragmentation

✅ **Execution**
- Dynamic slippage by price tier/ not implemented yet.
  - Large caps: 0.05%
  - Mid caps: 0.15%
  - Small caps: 0.5%
- Angel One brokerage model: min(₹20, 0.1%) per trade

✅ **Metrics**
- Win rate, Profit Factor, Sharpe ratio
- Max drawdown, Return %
- Detailed trade logging

### Strategy Improvements
✅ **Trend Filtering**
- Only trade with trend direction
- Reduces whipsaws by 10-15%

✅ **Multi-Signal Confirmation**
- Requires 2+ signals to enter trade
- Combines: Trend + RSI + Volume + VWAP
- Better signal quality = higher win rate

✅ **Better Intraday Indicators**
- VWAP (mean reversion)
- RSI (overbought/oversold)
- Breakout (trend confirmation)
- Dynamic stoploss


---

## 🔄 Workflow

### 1. Backtest Phase
```
python backtest_all_strategies.py
↓
Next
 Optimize parameters
 Paper Trading


### 2. Paper Trading Phase (Next)
```
Simulate live trading for 5-10 days
Monitor: Order fills, slippage, capital preservation
↓
If consistent profitable → Live Trading with small capital
```

### 3. Live Trading Phase (Final)
```
Deploy with 1-2% of capital risk per trade
Daily monitoring, weekly review
Scale up only after 4+ weeks of consistent profit
```

---

## 🛠️ Customization

### Change Stock Pool
Edit `backtest_all_strategies.py`:
```python
STOCKS = [
    "RELIANCE", "TCS", "INFY",  # Add/remove symbols
    # ... more stocks
]
```

### Change Strategy
```python
from strategies.intraday_strategies import VWAPMeanReversion

engine = PortfolioBacktestEngineV2(
    strategy_cls=VWAPMeanReversion,  # Change this
    strategy_config={...}
)
```

### Optimize Parameters
```python
strategy_config={
    "fast_sma": 8,      # Try 5, 8, 10
    "slow_sma": 20,     # Try 15, 20, 25
    "rsi_period": 14,   # Try 10, 14, 21
    ...
}
```

### Adjust Risk
```python
engine = PortfolioBacktestEngineV2(
    total_capital=100000,      # Your capital
    max_positions=5,           # concurrent positions
    max_trades_per_day=15,     # daily trades
    min_trade_value=3000.0,    # minimum per trade
    warmup_candles=20,         # signals to ignore
    intraday_only=True,        # square off at EOD
)
```

---

## 📝 Trading Rules

### Exit Conditions
1. **Stoploss Hit**: 2% below entry
2. **Profit Target**: Built into strategy signals
3. **Trend Reversal**: Exit if trend changes
4. **EOD Squareoff**: Close all at market close

---

## ⚠️ Risk Management

- **Max Capital at Risk**: 2% per trade (built-in)
- **Daily Loss Limit**: Stop trading if max losses hit
- **Position Size**: Equal allocation per position
- **Brokerage Cost**: ₹20 + 0.1% modeled in backtest

---

## 🎯 Next Steps

1. ✅ Run `backtest_all_strategies.py` 
2. ✅ Review results (win rate, profit factor)
3. Make Screening script to find treding stocks for the day from the pool of Stocks

---

## 📞 Architecture Overview

```
User Trade Request
    ↓
Strategy (MultiSignalHybrid)
    ↓
Signals (Buy/Sell with stoploss)
    ↓
Broker (Paper/SmartAPI)
    ↓
Execution (Market/Limit orders)
    ↓
Position Management
    ↓
P&L Tracking & Logging
```


