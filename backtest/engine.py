import pandas as pd
from typing import Dict, Any, List


class BacktestEngine:
    """
    Minimal single-symbol intraday backtest engine.
    Designed for SmartAPI OHLCV candle data.

    Strategy must return:
    {'action': 'buy'/'sell', 'price': float, 'qty': int}
    """

    def __init__(
        self,
        strategy_cls,
        strategy_config: Dict[str, Any],
        starting_cash: float = 100000.0,
        slippage: float = 0.0,             # % slippage (0.001 = 0.1%)
        commission_per_trade: float = 0.0
    ):
        self.strategy_cls = strategy_cls
        self.strategy_config = strategy_config
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.slippage = slippage
        self.commission = commission_per_trade

        self.position_qty = 0
        self.avg_price = 0.0
        self.trade_log: List[Dict[str, Any]] = []

    # -------------------------
    # Execution helpers
    # -------------------------
    def _buy(self, qty: int, price: float, ts):
        exec_price = price * (1 + self.slippage)
        cost = (exec_price * qty) + self.commission

        if cost > self.cash:
            return

        prev_val = self.avg_price * self.position_qty
        new_val = prev_val + (exec_price * qty)

        self.position_qty += qty
        self.avg_price = new_val / self.position_qty
        self.cash -= cost

        self.trade_log.append({
            "side": "buy",
            "qty": qty,
            "price": exec_price,
            "timestamp": ts,
            "pnl": None
        })

    def _sell(self, qty: int, price: float, ts):
        if qty > self.position_qty:
            return

        exec_price = price * (1 - self.slippage)
        proceeds = (exec_price * qty) - self.commission
        pnl = (exec_price - self.avg_price) * qty

        self.cash += proceeds
        self.position_qty -= qty

        if self.position_qty == 0:
            self.avg_price = 0.0

        self.trade_log.append({
            "side": "sell",
            "qty": qty,
            "price": exec_price,
            "timestamp": ts,
            "pnl": pnl
        })

    # -------------------------
    # Main Backtest Loop
    # -------------------------
    def run(self, df: pd.DataFrame):

        if df.empty:
            raise ValueError("DataFrame is empty")

        self.strategy = self.strategy_cls(self.strategy_config)
        self.strategy.on_start()

        for ts, row in df.iterrows():
            bar = {
                "timestamp": ts,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"])
            }

            signal = self.strategy.on_bar(bar)

            if signal and isinstance(signal, dict):
                action = signal.get("action")
                price = float(signal.get("price", bar["close"]))
                qty = int(signal.get("qty", 0))

                if action == "buy":
                    self._buy(qty, price, ts)

                elif action == "sell":
                    self._sell(qty, price, ts)

        self.strategy.on_stop()

        # Force exit at last candle
        if self.position_qty > 0:
            last_price = float(df.iloc[-1]["close"])
            self._sell(self.position_qty, last_price, df.index[-1])

        return self._summary()

    # -------------------------
    # Metrics
    # -------------------------
    def _summary(self):
        pnl = self.cash - self.starting_cash
        trades = self.trade_log

        closed = [t for t in trades if t["pnl"] is not None]
        wins = [t for t in closed if t["pnl"] > 0]

        win_rate = len(wins) / len(closed) if closed else 0

        equity = self.starting_cash
        peak = equity
        max_dd = 0

        for t in closed:
            equity += t["pnl"]
            peak = max(peak, equity)
            dd = peak - equity
            max_dd = max(max_dd, dd)

        return {
            "final_cash": self.cash,
            "pnl": pnl,
            "trades": trades,
            "win_rate": win_rate,
            "max_drawdown": max_dd
        }