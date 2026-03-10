# CLEANUP GUIDE

## New Structure (FINAL)

### Root Level - Example Scripts
✅ **backtest.py** - ONLY backtest example (replaces all others)
   - Tests MultiSignalHybrid strategy
   - Shows best practices
   - Use this one for all testing

### /backtest/ - Engine
✅ **portfolio_backtest_v2.py** - ONLY engine needed
   - Production-grade multi-symbol backtest
   - Handles everything the old engines did, plus better

### /strategies/ - Final Set
✅ **base_strategy.py** - Required abstract class
✅ **multi_signal_hybrid.py** - MAIN STRATEGY (best performer)
✅ **intraday_strategies.py** - Alternative strategies (reference only)
✅ **trend_filter.py** - Helper utility
✅ **signal_ranker.py** - Helper utility (stock competition)

---

## DELETE THESE (Old/Duplicate Files)

Run from project root:
```bash
# Backtest examples (duplicates - keep only backtest.py)
rm backtest_example.py
rm backtest_hybrid.py
rm backtest_improved_strategies.py
rm portfolio_backtest_sanity.py

# Old sanity tests
rm live_trade_sanity.py
rm broker_sanity.py
rm data_sanity.py

# Old engine
rm backtest/portfolio_engine.py
rm backtest/engine.py

# Old strategies
rm strategies/sma_intraday.py
rm strategies/vwap_scalper.py
```

Or on Windows PowerShell:
```powershell
# Backtest examples
Remove-Item backtest_example.py
Remove-Item backtest_hybrid.py
Remove-Item backtest_improved_strategies.py
Remove-Item portfolio_backtest_sanity.py

# Old tests
Remove-Item live_trade_sanity.py
Remove-Item broker_sanity.py
Remove-Item data_sanity.py

# Old code
Remove-Item backtest\portfolio_engine.py
Remove-Item backtest\engine.py
Remove-Item strategies\sma_intraday.py
Remove-Item strategies\vwap_scalper.py
```

---

## Before / After Structure

### BEFORE (Messy)
```
Intra_v1/
├── backtest_example.py              ❌ OLD
├── backtest_hybrid.py               ❌ OLD
├── backtest_improved_strategies.py  ❌ OLD
├── portfolio_backtest_sanity.py     ❌ OLD
├── live_trade_sanity.py             ❌ OLD
├── broker_sanity.py                 ❌ OLD
├── data_sanity.py                   ❌ OLD
├── backtest/
│   ├── portfolio_engine.py          ❌ OLD
│   └── engine.py                    ❌ OLD
└── strategies/
    ├── sma_intraday.py              ❌ OLD
    └── vwap_scalper.py              ❌ OLD
```

### AFTER (Clean)
```
Intra_v1/
├── backtest.py                      ✅ ONLY example needed
├── setup.ps1
├── smartapi_readme.md
└── backtest/
    └── portfolio_backtest_v2.py     ✅ ONLY engine needed
└── strategies/
    ├── base_strategy.py             ✅ Required base
    ├── multi_signal_hybrid.py       ✅ BEST strategy
    ├── intraday_strategies.py       ✅ Alternatives (ref only)
    ├── trend_filter.py              ✅ Helper
    └── signal_ranker.py             ✅ Helper
```

---

## Usage

### Single Command to Test Everything:
```bash
python backtest.py
```

### To Use Different Strategy:
Edit backtest.py and change strategy_cls:
```python
from strategies.intraday_strategies import TrendFollowingWithFilter
# or VWAPMeanReversion, RSIOverbought, BreakoutStrategy
```

---

## File Sizes (Optional Cleanup)
- __pycache__ folders - can safely delete (auto-generated)
- .git - keep for version control
- logs/ - monitoring logs (safe to clean periodically)
- trade_log_latest.csv - trading results (archive if needed)
