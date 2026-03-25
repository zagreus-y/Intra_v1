"""
Stock Selection and Feature Engineering Pipeline

Ranks stocks daily based on early momentum signals
"""

import numpy as np
from typing import Dict, List, Tuple


class FeatureEngine:
    """Compute features from first 3 candles (15 mins) of the day."""
    
    def compute(self, day_data: Dict[str, 'pd.DataFrame']) -> Dict[str, Dict[str, float]]:
        """
        Args:
            day_data: Dict[symbol -> DataFrame] with OHLCV
            
        Returns:
            Dict[symbol -> {range, momentum, volume, avg_price}]
        """
        features = {}
        
        for symbol, df in day_data.items():
            if len(df) < 3:
                continue
            
            first_3 = df.iloc[:3]
            
            open_price = first_3.iloc[0]["open"]
            high = first_3["high"].max()
            low = first_3["low"].min()
            close = first_3.iloc[-1]["close"]
            volume = first_3["volume"].sum()
            
            # Avoid division by zero
            if open_price <= 0:
                continue
            
            range_pct = (high - low) / open_price
            momentum = (close - open_price) / open_price
            
            features[symbol] = {
                "range": range_pct,
                "momentum": momentum,
                "volume": volume,
                "avg_price": first_3["close"].mean()
            }
        
        return features


class SelectionEngine:
    """Score and rank stocks for trading."""
    
    def __init__(self, 
                 range_weight: float = 0.4,
                 momentum_weight: float = 0.4,
                 volume_weight: float = 0.2):
        """
        Args:
            range_weight: Weight for price range
            momentum_weight: Weight for momentum
            volume_weight: Weight for volume
        """
        self.range_weight = range_weight
        self.momentum_weight = momentum_weight
        self.volume_weight = volume_weight
        
        # Ensure weights sum to 1
        total = range_weight + momentum_weight + volume_weight
        self.range_weight /= total
        self.momentum_weight /= total
        self.volume_weight /= total
    
    def score(self, features: Dict[str, Dict]) -> Dict[str, float]:
        """Score each symbol."""
        scored = {}
        
        for symbol, f in features.items():
            # Normalize volume with log
            vol_score = np.log1p(f["volume"]) / 10  # Scale down
            
            score = (
                self.range_weight * f["range"] +
                self.momentum_weight * abs(f["momentum"]) +
                self.volume_weight * vol_score
            )
            scored[symbol] = score
        
        return scored
    
    def select_and_rank(self, 
                        features: Dict[str, Dict], 
                        top_k: int = 15) -> Tuple[List[str], Dict[str, float]]:
        """
        Select top K stocks by score.
        
        Returns:
            (selected_symbols, scores_dict)
        """
        scores = self.score(features)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected = [s for s, _ in ranked[:top_k]]
        
        return selected, scores