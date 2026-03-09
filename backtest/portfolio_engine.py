import pandas as pd
from typing import Dict, Any, List
from collections import defaultdict


class PortfolioBacktestEngine:
    """
    Portfolio-level intraday backtester (v1)

    Features:
    - Multi-symbol intraday backtest
    - Shared capital pool
    - Max open positions cap
    - Max trades per day cap
    - FIFO signal execution
    - Angel One brokerage model
    - Intraday square-off
    """

    def __init__(
        self,
        strategy_cls,
        strategy_config: Dict[str, Any],
        total_capital: float = 10000,
        max_positions: int = 3,
        max_trades_per_day: int = 10,
        slippage: float = 0.0005
    ):
        self.strategy_cls = strategy_cls
        self.strategy_config = strategy_config
        self.initial_capital = total_capital
        self.cash = total_capital
        self.max_positions = max_positions
        self.max_trades_per_day = max_trades_per_day
        self.slippage = slippage

        self.positions = {}  # symbol -> {qty, avg_price}
        self.trade_log: List[Dict] = []
        self.daily_trade_count = 0
        self.brokerage_paid = 0

        self.strategies = {}  # symbol -> strategy instance

    # -----------------------------
    # Angel One brokerage
    # -----------------------------
    def _brokerage(self, order_value):
        fee = min(20, order_value * 0.001)
        self.brokerage_paid += fee
        return fee

    # -----------------------------
    # Position sizing (equal capital)
    # -----------------------------
    def _capital_per_trade(self):
        return self.initial_capital / self.max_positions

    # -----------------------------
    # Execute BUY
    # -----------------------------
    def _buy(self, symbol, price, ts):
        if symbol in self.positions:
            return

        capital = self._capital_per_trade()
        qty = int(capital // price)
        if qty <= 0:
            return

        exec_price = price * (1 + self.slippage)
        order_value = exec_price * qty
        fee = self._brokerage(order_value)
        total_cost = order_value + fee

        if total_cost > self.cash:
            return

        self.cash -= total_cost
        self.positions[symbol] = {"qty": qty, "avg_price": exec_price}

        self.trade_log.append({
            "timestamp": ts,
            "symbol": symbol,
            "side": "buy",
            "qty": qty,
            "price": exec_price,
            "pnl": None
        })

    # -----------------------------
    # Execute SELL
    # -----------------------------
    def _sell(self, symbol, price, ts):
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        qty = pos["qty"]
        avg = pos["avg_price"]

        exec_price = price * (1 - self.slippage)
        order_value = exec_price * qty
        fee = self._brokerage(order_value)

        proceeds = order_value - fee
        pnl = (exec_price - avg) * qty

        self.cash += proceeds
        del self.positions[symbol]

        self.trade_log.append({
            "timestamp": ts,
            "symbol": symbol,
            "side": "sell",
            "qty": qty,
            "price": exec_price,
            "pnl": pnl
        })

    # -----------------------------
    # Main Run
    # -----------------------------
    def run(self, data: Dict[str, pd.DataFrame]):

        # init strategies per symbol
        for symbol in data:
            cfg = dict(self.strategy_config)
            cfg["symbol"] = symbol
            strat = self.strategy_cls(cfg)
            strat.on_start()
            self.strategies[symbol] = strat

        # align timestamps
        common_index = None
        for df in data.values():
            idx = set(df.index)
            common_index = idx if common_index is None else common_index & idx
        timeline = sorted(common_index)

        current_day = None

        for ts in timeline:

            day = ts.date()
            if current_day != day:
                self.daily_trade_count = 0
                current_day = day

            signals = []

            # collect signals
            for symbol, df in data.items():
                bar = df.loc[ts]
                bar_dict = {
                    "timestamp": ts,
                    "open": float(bar["open"]),
                    "high": float(bar["high"]),
                    "low": float(bar["low"]),
                    "close": float(bar["close"]),
                    "volume": float(bar["volume"])
                }

                signal = self.strategies[symbol].on_bar(bar_dict)
                if signal:
                    signals.append((symbol, signal))

            # execute FIFO
            for symbol, signal in signals:

                if self.daily_trade_count >= self.max_trades_per_day:
                    break

                if signal["action"] == "buy":
                    if len(self.positions) < self.max_positions:
                        self._buy(symbol, signal.get("price", bar_dict["close"]), ts)
                        self.daily_trade_count += 1

                elif signal["action"] == "sell":
                    if symbol in self.positions:
                        self._sell(symbol, signal.get("price", bar_dict["close"]), ts)
                        self.daily_trade_count += 1

        # square-off all at end
        last_ts = timeline[-1]
        for symbol in list(self.positions.keys()):
            last_price = float(data[symbol].iloc[-1]["close"])
            self._sell(symbol, last_price, last_ts)

        return self._summary()

    # -----------------------------
    # Metrics
    # -----------------------------
    def _summary(self):
        pnl = self.cash - self.initial_capital
        closed = [t for t in self.trade_log if t["pnl"] is not None]
        wins = [t for t in closed if t["pnl"] > 0]

        win_rate = len(wins) / len(closed) if closed else 0

        return {
            "final_cash": self.cash,
            "pnl": pnl,
            "win_rate": win_rate,
            "total_trades": len(self.trade_log),
            "brokerage_paid": self.brokerage_paid
        }