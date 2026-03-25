"""
Enhanced Portfolio Backtest Engine V2.1

Critical Improvements:
- Daily position square-off (intraday only)
- Warmup period per day (ignore first N candles)
- Capital fragmentation avoidance (minimum trade size)
- Dynamic slippage based on price tier
- Per-symbol strategy reset daily
- Better tracking of intraday vs multi-day rules

Features:
- Multi-symbol backtesting
- Smart capital allocation with minimums
- Risk metrics: Sharpe, drawdown, win rate, profit factor
- Stoploss support
- Detailed trade logging
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict


class PortfolioBacktestEngineV2:
    """
    Production-grade multi-symbol intraday backtest engine.
    """

    def __init__(
        self,
        strategy_cls,
        strategy_config: Dict[str, Any],
        total_capital: float = 100000,
        max_positions: int = 3,
        max_trades_per_day: int = 10,
        slippage: float = 0.0005,  # 0.05% for large-caps
        brokerage_per_trade: Optional[callable] = None,
        min_trade_value: float = 2000.0,  # Minimum ₹2000 per trade
        warmup_candles: int = 20,  # Ignore first N candles per day
        intraday_only: bool = True,  # Square off at EOD
        dynamic_slippage: bool = False  # Scale slippage by price tier
    ):
        """
        Args:
            strategy_cls: Strategy class
            strategy_config: Strategy config dict
            total_capital: Total capital for backtest
            max_positions: Max concurrent positions
            max_trades_per_day: Max trades per day
            slippage: Base slippage % (0.0005 = 0.05%)
            brokerage_per_trade: Function(trade_value) -> fee. Defaults to Angel One model.
            min_trade_value: Minimum position value in ₹ (e.g., 2000)
            warmup_candles: Ignore first N candles per day (let indicators stabilize)
            intraday_only: Square off all positions at EOD
            dynamic_slippage: Adjust slippage based on price tier
        """
        self.strategy_cls = strategy_cls
        self.strategy_config = strategy_config
        
        self.initial_capital = total_capital
        self.cash = total_capital
        self.max_positions = max_positions
        self.max_trades_per_day = max_trades_per_day
        self.slippage = slippage
        self.min_trade_value = min_trade_value
        self.warmup_candles = warmup_candles
        self.intraday_only = intraday_only
        self.dynamic_slippage = dynamic_slippage
        
        # Brokerage: default Angel One (min 20, 0.1%)
        self.brokerage_func = brokerage_per_trade or self._default_brokerage
        
        # State
        self.positions: Dict[str, Dict] = {}  # symbol -> {qty, entry_price, entry_ts, stop_loss, ...}
        self.trade_log: List[Dict] = []
        self.daily_trade_count = 0
        self.daily_trade_date = None
        self.daily_candle_count: Dict[str, int] = {}  # symbol -> candles seen today
        
        self.strategies: Dict[str, Any] = {}
        self.portfolio_value_log: List[Dict] = []
        
    # ============ BROKERAGE ============
    def _default_brokerage(self, order_value: float) -> float:
        """Angel One: min(20, 0.1% of trade value)."""
        return min(20, order_value * 0.001)
    
    def _get_slippage(self, price: float) -> float:
        """
        Get slippage % based on price tier (if dynamic_slippage enabled).
        
        Tiers:
        - Large caps (>500): 0.05%
        - Mid caps (100-500): 0.15%
        - Small caps (<100): 0.5%
        """
        if not self.dynamic_slippage:
            return self.slippage
        
        if price >= 500:
            return 0.0005  # 0.05%
        elif price >= 100:
            return 0.0015  # 0.15%
        else:
            return 0.005   # 0.5%
    
    # ============ POSITION MANAGEMENT ============
    def _capital_per_position(self, score):
        base = self.initial_capital / self.max_positions
        return base * (0.5 + score)  
        # range: 0.5x → 1.5x
    
    def _can_open_position(self, symbol: str) -> bool:
        """Check if we can open a new position."""
        if symbol in self.positions:
            return False
        if len(self.positions) >= self.max_positions:
            return False
        if self.daily_trade_count >= self.max_trades_per_day:
            return False
        if self.cash < self.min_trade_value:
            return False
        return True
    
    def _is_in_warmup(self, symbol: str) -> bool:
        """Check if symbol is still in warmup period (first N candles of day)."""
        candle_count = self.daily_candle_count.get(symbol, 0)
        return candle_count < self.warmup_candles
    
    # ============ EXECUTION ============
    def _execute_buy(
        self,
        symbol: str,
        price: float,
        ts: datetime,
        score: float = 0.5,
        stop_loss: Optional[float] = None
    ) -> bool:
        """Execute a buy order. Returns True if successful."""
        
        # Check warmup
        if self._is_in_warmup(symbol):
            return False
        
        if not self._can_open_position(symbol):
            return False
        
        capital = self._capital_per_position(score)
        slippage_pct = self._get_slippage(price)
        exec_price = price * (1 + slippage_pct)
        
        qty = int(capital / exec_price)
        if qty <= 0:
            return False
        
        order_value = exec_price * qty
        
        # Check minimum trade value
        if order_value < self.min_trade_value:
            return False
        
        fee = self.brokerage_func(order_value)
        total_cost = order_value + fee
        
        if total_cost > self.cash:
            return False
        
        self.cash -= total_cost
        self.positions[symbol] = {
            "qty": qty,
            "entry_price": exec_price,
            "entry_ts": ts,
            "stop_loss": stop_loss,
            "highest_price": exec_price,
            "trade_id": len(self.trade_log)
        }
        
        self.daily_trade_count += 1
        
        self.trade_log.append({
            "trade_id": len(self.trade_log),
            "date": ts.date(),
            "timestamp": ts,
            "symbol": symbol,
            "side": "BUY",
            "qty": qty,
            "price": exec_price,
            "brokerage_buy": fee,
            "brokerage_sell": None,
            "pnl": None,
            "pnl_percent": None,
            "exit_time": None,
            "status": "open",
            "exit_reason": None
        })
        
        return True
    
    def _execute_sell(
        self,
        symbol: str,
        price: float,
        ts: datetime,
        reason: str = "signal"
    ) -> bool:
        """Execute a sell order. Returns True if successful."""
        
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        slippage_pct = self._get_slippage(price)
        exec_price = price * (1 - slippage_pct)
        order_value = exec_price * pos["qty"]
        fee = self.brokerage_func(order_value)
        
        proceeds = order_value - fee
        entry_price = pos["entry_price"]
        pnl = (exec_price - entry_price) * pos["qty"]
        pnl_percent = (pnl / (entry_price * pos["qty"])) * 100 if entry_price > 0 else 0
        
        self.cash += proceeds
        
        # Record exit in trade log
        trade_id = pos["trade_id"]
        self.trade_log[trade_id]["side"] = "BUY+SELL"
        self.trade_log[trade_id]["pnl"] = pnl
        self.trade_log[trade_id]["pnl_percent"] = pnl_percent
        self.trade_log[trade_id]["exit_time"] = ts
        self.trade_log[trade_id]["status"] = "closed"
        self.trade_log[trade_id]["exit_reason"] = reason
        self.trade_log[trade_id]["exit_price"] = exec_price
        self.trade_log[trade_id]["brokerage_sell"] = fee
        
        del self.positions[symbol]
        self.daily_trade_count += 1
        
        return True
    
    def _check_stoploss(self, symbol: str, price: float, ts: datetime) -> bool:
        """Check and execute stoploss if hit. Returns True if hit."""
        
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        
        # Update highest price (for trailing stop)
        if price > pos["highest_price"]:
            pos["highest_price"] = price
        
        # Check stoploss
        if pos["stop_loss"] and price <= pos["stop_loss"]:
            return self._execute_sell(symbol, price, ts, reason="stoploss")
        
        return False
    
    def _reset_daily_state(self):
        """Reset daily counters at EOD."""
        self.daily_trade_count = 0
        self.daily_candle_count = {}
    
    def _reset_strategies_daily(self):
        """Reset strategy state daily (fresh start each day)."""
        for symbol in self.strategies:
            cfg = dict(self.strategy_config)
            cfg["symbol"] = symbol
            strat = self.strategy_cls(cfg)
            strat.on_start()
            self.strategies[symbol] = strat
    
    # ============ MAIN BACKTEST ============
    def run(self, data: Dict[str, pd.DataFrame], daily_selection: Dict = None) -> Dict[str, Any]:
        """
        Run multi-symbol portfolio backtest with optional daily stock filtering.
        
        Args:
            data: Dict[symbol -> DataFrame with OHLCV]
            daily_selection: Dict[date -> list of selected symbols] for daily filtering
        
        Returns:
            Results dictionary with metrics
        """
        
        # Initialize all strategies first (even for filtered symbols)
        for symbol in data:
            cfg = dict(self.strategy_config)
            cfg["symbol"] = symbol
            strat = self.strategy_cls(cfg)
            strat.on_start()
            self.strategies[symbol] = strat
        
        # Align timestamps across all symbols
        common_index = None
        for df in data.values():
            idx = set(df.index)
            common_index = idx if common_index is None else common_index & idx
    
        if not common_index:
            raise ValueError("No common timestamps across symbols")
        
        timeline = sorted(common_index)
        
        # Track which symbols are allowed today
        allowed_symbols = set(data.keys())
        
        # Backtest loop
        for ts in timeline:
            current_day = ts.date()
            
            # Day change: square off all positions and reset
            if current_day != self.daily_trade_date:
                # Close all open positions at previous day's close
                if self.intraday_only and self.positions:
                    prev_ts = timeline[timeline.index(ts) - 1] if timeline.index(ts) > 0 else None
                    if prev_ts:
                        for symbol in list(self.positions.keys()):
                            prev_price = float(data[symbol].loc[prev_ts, "close"])
                            self._execute_sell(symbol, prev_price, prev_ts, reason="eod_squareoff")
                
                # Update allowed symbols for today
                if daily_selection and current_day in daily_selection:
                    allowed_symbols = set(daily_selection[current_day])
                else:
                    allowed_symbols = set(data.keys())
                
                # Reset daily state
                self._reset_daily_state()
                self._reset_strategies_daily()
                self.daily_trade_date = current_day
            
            # Increment candle count per symbol
            for symbol in data:
                self.daily_candle_count[symbol] = self.daily_candle_count.get(symbol, 0) + 1
            
            # Check stoploss for all positions
            for symbol in list(self.positions.keys()):
                row = data[symbol].loc[ts]
                self._check_stoploss(symbol, float(row["close"]), ts)
            
            # Get signals from strategies (only for allowed symbols)
            signals = []
            for symbol in data:
                # Skip if not in today's allowed list
                if symbol not in allowed_symbols:
                    continue
                
                if symbol not in self.strategies:
                    continue
                
                row = data[symbol].loc[ts]
                bar = {
                    "timestamp": ts,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"])
                }
                
                signal = self.strategies[symbol].on_bar(bar)
                
                if signal:
                    # Include score in signal for ranking
                    score = signal.get("score", 0)
                    signals.append((symbol, signal, score))
            
            # Normalize scores to 0-1 range
            if signals:
                scores_list = [s[2] for s in signals]
                max_score = max(scores_list) if scores_list else 1
                normalized_signals = [
                    (sym, sig, score / max_score if max_score > 0 else score)
                    for sym, sig, score in signals
                ]
            else:
                normalized_signals = []
            
            # Execute signals in score order
            for symbol, signal, score in normalized_signals:
                action = signal.get("action")
                
                if action == "buy":
                    self._execute_buy(
                        symbol,
                        signal.get("price", data[symbol].loc[ts, "close"]),
                        ts,
                        score,
                        stop_loss=signal.get("stoploss")
                    )
                
                elif action == "sell":
                    self._execute_sell(
                        symbol,
                        signal.get("price", data[symbol].loc[ts, "close"]),
                        ts
                    )
            
            # Log portfolio value
            portfolio_value = self.cash
            for symbol, pos in self.positions.items():
                current_price = float(data[symbol].loc[ts, "close"])
                portfolio_value += pos["qty"] * current_price
            
            self.portfolio_value_log.append({
                "timestamp": ts,
                "cash": self.cash,
                "portfolio_value": portfolio_value,
                "num_positions": len(self.positions)
            })
        
        # Final EOD square-off
        if self.intraday_only and self.positions:
            final_ts = timeline[-1]
            for symbol in list(self.positions.keys()):
                final_price = float(data[symbol].loc[final_ts, "close"])
                self._execute_sell(symbol, final_price, final_ts, reason="eod_squareoff")
        
        # Calculate metrics
        return self._calculate_metrics()
    
    # ============ METRICS ============
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive backtest metrics."""
        
        # Basic metrics
        final_cash = self.cash
        net_pnl = final_cash - self.initial_capital
        
        # Trade metrics
        closed_trades = [t for t in self.trade_log if t["status"] == "closed"]
        winning_trades = [t for t in closed_trades if t["pnl"] > 0]
        losing_trades = [t for t in closed_trades if t["pnl"] < 0]
        breakeven_trades = [t for t in closed_trades if t["pnl"] == 0]
        
        win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0
        avg_win = np.mean([t["pnl"] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t["pnl"] for t in losing_trades]) if losing_trades else 0
        
        total_wins = sum([t["pnl"] for t in winning_trades])
        total_losses = abs(sum([t["pnl"] for t in losing_trades]))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Round-trip brokerage cost
        total_brokerage = sum(
            (t.get("brokerage_buy", 0) or 0) + (t.get("brokerage_sell", 0) or 0)
            for t in self.trade_log
            if t["status"] == "closed"
        )
        
        # Drawdown
        portfolio_values = [log["portfolio_value"] for log in self.portfolio_value_log]
        if len(portfolio_values) > 1:
            running_max = np.maximum.accumulate(portfolio_values)
            drawdown = (np.array(portfolio_values) - running_max) / running_max
            max_drawdown = np.min(drawdown)
        else:
            max_drawdown = 0
        
        # Return metrics
        total_return = (final_cash - self.initial_capital) / self.initial_capital
        
        # Sharpe ratio
        pnls = [t["pnl"] for t in closed_trades if t["pnl"] is not None]
        sharpe = 0
        if len(pnls) > 1:
            daily_returns = np.array(pnls) / self.initial_capital
            if np.std(daily_returns) > 0:
                sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
        
        return {
            "final_cash": final_cash,
            "net_pnl": net_pnl,
            "total_return": total_return,
            "total_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "breakeven_trades": len(breakeven_trades),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "largest_win": max([t["pnl"] for t in closed_trades], default=0),
            "largest_loss": min([t["pnl"] for t in closed_trades], default=0),
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "total_brokerage": total_brokerage,
            "trade_log": self.trade_log,
            "portfolio_log": self.portfolio_value_log
        }
