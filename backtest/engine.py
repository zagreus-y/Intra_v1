"""
Enhanced Backtest Engine (single/multi-symbol)

Features:
- Works with strategy classes that implement BaseStrategy (on_start, on_bar, on_stop)
- Accepts either:
    - a pandas.DataFrame (single-symbol OHLCV indexed by timestamp), or
    - a dict[str -> DataFrame] for multi-symbol backtests (all frames must share index)
- Position sizing hooks (pass a sizing function or let strategy supply qty)
- StopLossManager integration (optional)
- Slippage (fraction) and commission (absolute per order or percent) support
- Detailed trade log + summary metrics (pnl, win_rate, max_drawdown, trades)
"""

import pandas as pd
from typing import Dict, Any, Callable, Optional, List, Union
from datetime import datetime

# Import your helpers (adjust import path if your project layout differs)
try:
    from risk.position_sizer import size_by_percent, size_by_risk, size_by_capital
    from risk.stoploss import StopLossManager
except Exception:
    # If running standalone for tests, define light fallbacks
    def size_by_percent(equity, percent, price): 
        return int((equity * percent) // price) if percent > 0 else 0
    def size_by_risk(equity, risk_per_trade, entry_price, stop_price):
        rps = abs(entry_price - stop_price)
        return int(risk_per_trade // rps) if rps > 0 else 0
    class StopLossManager:
        def __init__(self): self.sl = {}
        def set_fixed(self,*a,**k): pass
        def set_trailing(self,*a,**k): pass
        def on_tick(self,*a,**k): return None
        def clear(self,*a,**k): pass

class BacktestEngine:
    def __init__(
        self,
        strategy_cls,
        strategy_config: Dict[str, Any],
        starting_cash: float = 100000.0,
        slippage: float = 0.0,               # fractional (e.g. 0.001 = 0.1%)
        commission_per_trade: float = 0.0,   # absolute per executed order
        commission_pct: float = 0.0,         # fraction of trade value
        position_sizer: Optional[Callable] = None,  # custom sizing function
        stoploss_manager: Optional[StopLossManager] = None,
    ):
        self.strategy_cls = strategy_cls
        self.strategy_config = strategy_config
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.slippage = float(slippage)
        self.comm_abs = float(commission_per_trade)
        self.comm_pct = float(commission_pct)
        self.position_sizer = position_sizer
        self.stoploss_manager = stoploss_manager or StopLossManager()

        # runtime state
        self.strategy = None
        self.positions: Dict[str, int] = {}     # symbol -> qty
        self.avg_cost: Dict[str, float] = {}    # symbol -> average entry price
        self.trade_log: List[Dict[str, Any]] = []

    # -------------------------
    # Utils
    # -------------------------
    def _apply_slippage(self, price: float, side: str) -> float:
        if side == 'buy':
            return price * (1 + self.slippage)
        return price * (1 - self.slippage)

    def _apply_commission(self, trade_value: float) -> float:
        return self.comm_abs + (trade_value * self.comm_pct)

    def _execute_buy(self, symbol: str, qty: int, price: float, ts: datetime):
        if qty <= 0:
            return None
        exec_price = self._apply_slippage(price, 'buy')
        value = exec_price * qty
        commission = self._apply_commission(value)
        total_cost = value + commission

        if total_cost > self.cash:
            # Not enough cash
            return {'status': 'rejected', 'reason': 'insufficient_cash'}

        self.cash -= total_cost
        prev_qty = self.positions.get(symbol, 0)
        prev_cost = self.avg_cost.get(symbol, 0.0)

        new_qty = prev_qty + qty
        new_avg = ((prev_cost * prev_qty) + (exec_price * qty)) / new_qty if new_qty > 0 else 0.0
        self.positions[symbol] = new_qty
        self.avg_cost[symbol] = new_avg

        trade = {
            'symbol': symbol,
            'side': 'buy',
            'qty': qty,
            'price': exec_price,
            'commission': commission,
            'timestamp': ts,
            'pnl': None
        }
        self.trade_log.append(trade)
        return trade

    def _execute_sell(self, symbol: str, qty: int, price: float, ts: datetime):
        if qty <= 0:
            return None
        pos = self.positions.get(symbol, 0)
        if qty > pos:
            return {'status': 'rejected', 'reason': 'insufficient_position'}

        exec_price = self._apply_slippage(price, 'sell')
        value = exec_price * qty
        commission = self._apply_commission(value)
        self.cash += (value - commission)

        avg = self.avg_cost.get(symbol, 0.0)
        realized_pnl = (exec_price - avg) * qty

        new_qty = pos - qty
        if new_qty == 0:
            # clear avg cost
            self.avg_cost.pop(symbol, None)
            self.positions.pop(symbol, None)
        else:
            self.positions[symbol] = new_qty

        trade = {
            'symbol': symbol,
            'side': 'sell',
            'qty': qty,
            'price': exec_price,
            'commission': commission,
            'timestamp': ts,
            'pnl': realized_pnl
        }
        self.trade_log.append(trade)
        return trade

    # -------------------------
    # Core runner (single-symbol or multi)
    # -------------------------
    def run(self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]):
        """
        data: DataFrame (single symbol) OR dict(symbol -> DataFrame)
        All DataFrames must have columns: open, high, low, close, volume and a DatetimeIndex.
        """
        # Normalize multi/single
        multi = isinstance(data, dict)
        if not multi:
            # single symbol - infer symbol name from strategy_config or use 'SYM'
            sym = self.strategy_config.get('symbol', 'SYM')
            data = {sym: data}

        # Validate data lengths and indices (basic)
        symbols = list(data.keys())
        for s in symbols:
            if not isinstance(data[s], pd.DataFrame) or data[s].empty:
                raise ValueError(f"No data for symbol {s}")

        # If multi-symbol, ensure indexes align: use intersection
        if len(symbols) > 1:
            idx = None
            for s in symbols:
                if idx is None:
                    idx = set(data[s].index)
                else:
                    idx = idx.intersection(set(data[s].index))
            idx = sorted(idx)
        else:
            idx = list(data[symbols[0]].index)

        # Instantiate strategy
        self.strategy = self.strategy_cls(self.strategy_config)
        self.strategy.on_start()

        # Run over timestamps (bars)
        for ts in idx:
            # construct per-symbol bar dict for this timestamp
            bars = {}
            for s in symbols:
                row = data[s].loc[ts]
                bars[s] = {
                    'timestamp': ts,
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row.get('volume', 0))
                }

            # For single-symbol strategies, pass bar dict or bar object depending on API
            # We call strategy.on_bar with a single bar (if single symbol) or dict(symbol->bar) if multi
            strategy_input = bars[symbols[0]] if len(symbols) == 1 else bars
            signal = self.strategy.on_bar(strategy_input)

            # Strategy returns signals as: {'action':'buy'/'sell', 'price':float, 'qty': optional int}
            if signal and isinstance(signal, dict) and 'action' in signal:
                s_sym = self.strategy_config.get('symbol', symbols[0])
                action = signal['action']
                price = float(signal.get('price', bars[s_sym]['close']))
                qty = int(signal.get('qty', 0)) if signal.get('qty') is not None else None

                # determine qty if None: use provided position_sizer or config
                if qty is None:
                    # prefer strategy-config sizing keys
                    if self.position_sizer:
                        # position_sizer(engine_cash, strategy_config, entry_price, bars) -> qty
                        qty = int(self.position_sizer(self.cash, self.strategy_config, price, bars))
                    else:
                        # fallback: percent_of_equity in config or fixed capital
                        pct = float(self.strategy_config.get('percent_of_equity', 0.2))
                        qty = size_by_percent(self.cash, pct, price)

                # Execute
                ts_dt = pd.to_datetime(ts)
                if action == 'buy':
                    res = self._execute_buy(s_sym, qty, price, ts_dt)
                    # set stoploss if provided in strategy config (example)
                    stop_cfg = self.strategy_config.get('stoploss')  # dict with type and params
                    if stop_cfg and isinstance(stop_cfg, dict):
                        stype = stop_cfg.get('type', 'fixed')
                        if stype == 'fixed':
                            stop_price = stop_cfg.get('stop_price')
                            if stop_price:
                                self.stoploss_manager.set_fixed(s_sym, price, stop_price)
                        elif stype == 'trailing':
                            trail = stop_cfg.get('trail_points', 0)
                            self.stoploss_manager.set_trailing(s_sym, price, trail)

                elif action == 'sell':
                    res = self._execute_sell(s_sym, qty, price, ts_dt)
                    # clear stoploss for symbol
                    self.stoploss_manager.clear(s_sym)

            # check stoplosses using the close price (intraday engine should use ticks)
            for s in symbols:
                sl_hit = self.stoploss_manager.on_tick(s, bars[s]['close'])
                if sl_hit == 'hit':
                    # force exit full position
                    pos_qty = self.positions.get(s, 0)
                    if pos_qty > 0:
                        self._execute_sell(s, pos_qty, bars[s]['close'], pd.to_datetime(ts))
                        self.stoploss_manager.clear(s)

        # End run
        self.strategy.on_stop()

        # Close remaining positions at last close
        for s in list(self.positions.keys()):
            qty = self.positions.get(s, 0)
            if qty > 0:
                last_price = float(data[s].iloc[-1]['close'])
                self._execute_sell(s, qty, last_price, pd.to_datetime(data[s].index[-1]))

        return self._summary()

    # -------------------------
    # Metrics and summary
    # -------------------------
    def _summary(self) -> Dict[str, Any]:
        pnl = self.cash - self.starting_cash
        trades = self.trade_log

        wins = [t for t in trades if t['pnl'] is not None and t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] is not None and t['pnl'] <= 0]

        win_rate = (len(wins) / len([t for t in trades if t['pnl'] is not None])) if trades else 0.0

        # equity curve for drawdown
        equity = self.starting_cash
        equity_curve = []
        for t in trades:
            if t['pnl'] is not None:
                equity += t['pnl']
            equity_curve.append(equity)

        peak = -float('inf')
        max_dd = 0.0
        peak = self.starting_cash
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val)
            if dd > max_dd:
                max_dd = dd

        return {
            'final_cash': self.cash,
            'pnl': pnl,
            'trades': trades,
            'num_trades': len(trades),
            'win_rate': win_rate,
            'max_drawdown': max_dd
        }
