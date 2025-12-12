"""
live_runner.py

Bar-driven LiveRunner (Complete rewrite)

Features
- Works with your NSEDataHybrid.get_ohlcv() and .get_live_quote()
- Primes symbol-specific NSE session (referer + warm cookies)
- Builds 1m/5m bar loop (interval-driven polling)
- Uses live LTP for stoploss checks (faster reaction than bar-close)
- Converts cumulative "total traded volume" -> per-bar volume
- Position sizing via optional position_sizer or default percent-of-equity
- Sets a simple fixed stoploss after buys (via StopLossManager)
- Gracefully handles network/JSON glitches and KeyboardInterrupt
- Simple logging to stdout
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable


# Helper: map interval string to seconds
_INTERVAL_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
}


class LiveRunner:
    def __init__(
        self,
        data_provider,
        broker,
        strategy,
        stoploss_manager,
        interval: str = "1m",
        position_sizer: Optional[Callable[..., int]] = None,
        default_risk: float = 50.0,     # rupees risk per trade (fallback)
        default_allocation: float = 0.2 # fraction of equity used if no sizer
    ):
        """
        data_provider: object with get_ohlcv(symbol, interval, lookback)
                       get_live_quote(symbol)
                       _warm_cookies(symbol) (optional)
                       is_market_open() (optional)
        broker: must implement place_order(symbol, qty, side, order_type, price),
                get_cash(), get_positions()
        strategy: must implement on_start(symbol), on_bar(symbol, bar), on_stop(symbol)
                  and return signal dict {"action":"buy"/"sell", "qty": int|None, "price": float|None}
        stoploss_manager: must implement set_fixed(symbol, entry, sl), on_tick(symbol, price), clear(symbol)
        position_sizer: optional function(...)->qty. Signature used here:
                       position_sizer(cash, price, bar, risk) -> qty
        """

        # Components
        self.data = data_provider
        self.broker = broker
        self.strategy = strategy
        self.slm = stoploss_manager

        # Behaviour config
        self.interval = interval if interval in _INTERVAL_SECONDS else "1m"
        self.poll_delay = _INTERVAL_SECONDS.get(self.interval, 60)
        self.position_sizer = position_sizer
        self.risk_amount = default_risk
        self.default_allocation = default_allocation

        # Runner state
        self.last_bar_ts: Optional[datetime] = None
        self.active_symbol: Optional[str] = None

        # Track cumulative volume to convert to per-bar
        # structure: { symbol: last_cumulative_volume_int }
        self._last_cumulative_volume: Dict[str, int] = {}

    # -----------------------------
    # Public: start the live loop
    # -----------------------------
    def run(self, symbol: str, poll_delay: Optional[int] = None):
        """
        Start the bar-driven live loop for a single symbol.
        poll_delay: optional override seconds between polls (otherwise derived from interval)
        """
        self.active_symbol = symbol
        if poll_delay is None:
            poll_delay = self.poll_delay

        print(f"[LiveRunner] START {symbol} interval={self.interval} poll_delay={poll_delay}s")
        # Prime NSE session for the symbol (some providers require symbol-specific warming)
        try:
            if hasattr(self.data, "headers"):
                # set symbol-specific referer if provider supports it
                try:
                    self.data.headers["Referer"] = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"
                except Exception:
                    pass
            if hasattr(self.data, "_warm_cookies"):
                try:
                    self.data._warm_cookies(symbol)
                except Exception:
                    pass
            # warm a live tick to ensure session is primed
            try:
                _ = self.data.get_live_quote(symbol)
            except Exception:
                pass
        except Exception:
            # not fatal; continue
            pass

        # Notify strategy
        try:
            self.strategy.on_start(symbol)
        except TypeError:
            # fallback if strategy.on_start expects no args
            self.strategy.on_start()

        # Loop
        try:
            while True:
                # If data provider has is_market_open() and market closed -> sleep until open
                try:
                    if hasattr(self.data, "is_market_open") and callable(self.data.is_market_open):
                        if not self.data.is_market_open():
                            print("[LiveRunner] Market closed. Sleeping 30s ...")
                            time.sleep(30)
                            continue
                except Exception:
                    # on any error, continue to fetch and attempt
                    pass

                bar = self._get_latest_bar(symbol)
                if bar is None:
                    time.sleep(poll_delay)
                    continue

                ts = bar["timestamp"]
                # Skip extremely stale bars
                age = (datetime.now(ts.tzinfo) - ts).total_seconds()
                if age > 120:
                    # bar older than 2 minutes — warn and skip
                    print(f"[LiveRunner] WARN stale bar (age={int(age)}s) ts={ts}. Skipping.")
                    time.sleep(poll_delay)
                    continue

                # Only react to new bar timestamps
                if self.last_bar_ts is None or ts > self.last_bar_ts:
                    self.last_bar_ts = ts
                    try:
                        self._process_bar(symbol, bar)
                    except Exception as e:
                        print("[LiveRunner] ERROR processing bar:", e)

                time.sleep(poll_delay)

        except KeyboardInterrupt:
            print("[LiveRunner] KeyboardInterrupt received. Shutting down cleanly...")
        finally:
            try:
                self.strategy.on_stop(symbol)
            except TypeError:
                self.strategy.on_stop()
            print("[LiveRunner] Stopped.")

    # -----------------------------
    # Internal: fetch most recent bar (dict)
    # -----------------------------
    def _get_latest_bar(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Uses data.get_ohlcv(symbol, interval, lookback) to fetch recent bars and convert to dict.
        Converts cumulative volume -> per-bar volume if possible.
        """
        try:
            df = self.data.get_ohlcv(symbol, interval=self.interval, lookback=5)
        except Exception as e:
            print("[LiveRunner] get_ohlcv error:", e)
            return None

        if df is None or df.empty:
            return None

        # Ensure index is DatetimeIndex and timezone-aware
        try:
            last = df.iloc[-1]
            ts = df.index[-1]
        except Exception as e:
            print("[LiveRunner] malformed OHLCV dataframe:", e)
            return None

        # Read cumulative volume (some providers give cumulative quantity traded)
        cumulative_vol = int(last.get("volume", 0) or 0)

        # Compute per-bar volume
        prev_cum = self._last_cumulative_volume.get(symbol)
        if prev_cum is None:
            per_bar_vol = cumulative_vol  # first observed -> treat as bar vol
        else:
            per_bar_vol = max(0, cumulative_vol - prev_cum)

        # Update last cumulative
        self._last_cumulative_volume[symbol] = cumulative_vol

        try:
            return {
                "timestamp": ts,
                "open": float(last["open"]),
                "high": float(last["high"]),
                "low": float(last["low"]),
                "close": float(last["close"]),
                "volume": int(per_bar_vol),
            }
        except Exception as e:
            print("[LiveRunner] convert bar fields failed:", e)
            return None

    # -----------------------------
    # Internal: determine qty (sizer)
    # -----------------------------
    def _compute_qty(self, symbol: str, price: float, bar: Dict[str, Any]) -> int:
        # If strategy provided explicit sizer, use it
        if self.position_sizer:
            try:
                qty = int(self.position_sizer(
                    cash=self.broker.get_cash(),
                    price=price,
                    bar=bar,
                    risk=self.risk_amount
                ))
                return max(1, qty)
            except Exception as e:
                print("[LiveRunner] position_sizer error:", e)

        # Default: allocate default_allocation fraction of cash
        try:
            cash = float(self.broker.get_cash())
            target_value = cash * float(self.default_allocation)
            qty = int(target_value // price) if price > 0 else 0
            return max(1, qty)
        except Exception as e:
            print("[LiveRunner] compute_qty fallback error:", e)
            return 1

    # -----------------------------
    # Internal: set a simple fixed SL after entry
    # -----------------------------
    def _set_stoploss(self, symbol: str, entry_price: float):
        # default: 0.3% fixed SL below entry (round to 2 decimals)
        sl_price = round(entry_price * 0.997, 2)
        try:
            self.slm.set_fixed(symbol, entry_price, sl_price)
            print(f"[LiveRunner][SL] set fixed SL for {symbol} at {sl_price}")
        except Exception as e:
            print("[LiveRunner][SL] set_fixed error:", e)

    # -----------------------------
    # Internal: execute trade via broker
    # -----------------------------
    def _execute_trade(self, symbol: str, action: str, qty: int, price: float):
        side = "buy" if action.lower() == "buy" else "sell"
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] EXECUTE {side.upper()} {symbol} qty={qty} price={price}")

        try:
            order = self.broker.place_order(
                symbol=symbol,
                qty=qty,
                side=side,
                order_type="market",
                price=price
            )
        except Exception as e:
            print("[LiveRunner] broker.place_order error:", e)
            return

        if not isinstance(order, dict):
            print("[LiveRunner] Unexpected order response:", order)
            return

        if order.get("status") == "rejected":
            print("[LiveRunner] Order rejected:", order.get("reason"))
            return

        print("[LiveRunner] Order filled:", order)

        if side == "buy":
            # set SL after a successful buy
            self._set_stoploss(symbol, price)
        else:
            # clear SL on sells
            try:
                self.slm.clear(symbol)
            except Exception:
                pass

    # -----------------------------
    # Internal: process an incoming bar
    # -----------------------------
    def _process_bar(self, symbol: str, bar: Dict[str, Any]):
        """
        Flow:
          1) Check SL using live LTP (faster reaction)
          2) Ask strategy for signal
          3) Compute qty if needed
          4) Execute trade
        """
        # 1) Check stoploss using live LTP if available
        try:
            tick = None
            try:
                tick = self.data.get_live_quote(symbol)
            except Exception:
                tick = None

            current_price = tick["ltp"] if tick and "ltp" in tick else bar["close"]

            sl_state = None
            try:
                sl_state = self.slm.on_tick(symbol, current_price)
            except Exception as e:
                print("[LiveRunner][SL] on_tick error:", e)

            if sl_state == "hit":
                pos = int(self.broker.get_positions().get(symbol, 0))
                if pos > 0:
                    print(f"[LiveRunner][SL] Stoploss HIT for {symbol} at {current_price} — exiting {pos}")
                    self._execute_trade(symbol, "sell", pos, current_price)
                    return
        except Exception as e:
            print("[LiveRunner] SL-check error:", e)

        # 2) Strategy signal
        try:
            # Strategy API: strategy.on_bar(symbol, bar) is preferred
            try:
                signal = self.strategy.on_bar(symbol, bar)
            except TypeError:
                # fallback to older signature strategy.on_bar(bar)
                signal = self.strategy.on_bar(bar)
        except Exception as e:
            print("[LiveRunner] strategy.on_bar error:", e)
            return

        if not signal:
            return

        action = signal.get("action")
        if not action or action.lower() not in ("buy", "sell"):
            return

        price = signal.get("price", bar["close"])
        qty = signal.get("qty")

        # Compute qty if not provided
        if qty is None:
            qty = self._compute_qty(symbol, price, bar)

        # Sanity: qty positive
        if qty <= 0:
            print("[LiveRunner] computed zero qty, skipping")
            return

        # Execute
        self._execute_trade(symbol, action.lower(), int(qty), float(price))
