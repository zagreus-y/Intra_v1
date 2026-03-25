"""
Stock Selection and Feature Engineering Pipeline

Ranks stocks daily based on early momentum signals
"""

import numpy as np
from typing import Dict, List, Tuple


import numpy as np

class FeatureEngine:
    def compute(self, day_data):
        features = {}

        # --- Get index (for relative strength) ---
        index_symbol = "NIFTY"
        index_df = day_data.get(index_symbol)

        if index_df is not None and len(index_df) >= 3:
            idx_open = index_df.iloc[0]["open"]
            idx_close = index_df.iloc[2]["close"]
            index_return = (idx_close - idx_open) / idx_open
        else:
            index_return = 0

        for symbol, df in day_data.items():
            if len(df) < 3:
                continue

            first_3 = df.iloc[:3]

            open_price = first_3.iloc[0]["open"]
            high = first_3["high"].max()
            low = first_3["low"].min()
            close = first_3.iloc[-1]["close"]
            volume = first_3["volume"].sum()

            # --- Previous close (for gap) ---
            prev_close = df.iloc[0]["close"] if len(df) > 1 else open_price

            if open_price <= 0 or prev_close <= 0:
                continue

            # --- FEATURES ---

            # 1. Gap %
            gap = (open_price - prev_close) / prev_close

            # 2. Range (volatility)
            range_pct = (high - low) / open_price

            # 3. Momentum (first 15m)
            momentum = (close - open_price) / open_price

            # 4. RVOL (approx: normalize by log volume)
            rvol = np.log1p(volume)

            # 5. VWAP
            typical_price = (first_3["high"] + first_3["low"] + first_3["close"]) / 3
            vwap = (typical_price * first_3["volume"]).sum() / first_3["volume"].sum()

            vwap_dist = (close - vwap) / vwap if vwap > 0 else 0

            # 6. Relative Strength vs index
            stock_return = momentum
            rs = stock_return - index_return

            features[symbol] = {
                "gap": gap,
                "range": range_pct,
                "momentum": momentum,
                "rvol": rvol,
                "vwap_dist": vwap_dist,
                "rs": rs
            }

        return features


class SelectionEngine:
    def score(self, features):
        scores = {}

        for s, f in features.items():
            score = (
                0.30 * f["rvol"] +
                0.20 * f["range"] +
                0.15 * abs(f["gap"]) +
                0.15 * abs(f["vwap_dist"]) +
                0.20 * f["rs"]
            )
            scores[s] = score

        return scores

    def select_and_rank(self, features, top_k=15):
        scores = self.score(features)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        selected = [s for s, _ in ranked[:top_k]]

        return selected, scores