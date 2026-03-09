"""
Signal Ranking & Competition System

When multiple stocks signal at the same time, pick the best ones.
Rank by signal strength, volatility, and recent performance.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from collections import deque


class SignalRanker:
    """
    Ranks signals from competing stocks.
    Use this to allocate capital to the best setups only.
    """

    def __init__(self, lookback_bars: int = 20):
        """
        Args:
            lookback_bars: Number of bars to analyze for signal quality
        """
        self.lookback_bars = lookback_bars
        self.recent_prices: Dict[str, deque] = {}
        self.recent_volumes: Dict[str, deque] = {}

    def add_bar(self, symbol: str, price: float, volume: float) -> None:
        """Track price and volume for a symbol."""
        if symbol not in self.recent_prices:
            self.recent_prices[symbol] = deque(maxlen=self.lookback_bars)
            self.recent_volumes[symbol] = deque(maxlen=self.lookback_bars)
        
        self.recent_prices[symbol].append(price)
        self.recent_volumes[symbol].append(volume)

    def _get_volatility(self, symbol: str) -> float:
        """Calculate volatility (standard deviation of returns)."""
        if symbol not in self.recent_prices or len(self.recent_prices[symbol]) < 2:
            return 0.0
        
        prices = list(self.recent_prices[symbol])
        returns = np.diff(prices) / np.array(prices[:-1])
        volatility = np.std(returns)
        return volatility

    def _get_momentum(self, symbol: str) -> float:
        """Calculate momentum (recent return)."""
        if symbol not in self.recent_prices or len(self.recent_prices[symbol]) < 2:
            return 0.0
        
        prices = list(self.recent_prices[symbol])
        momentum = (prices[-1] - prices[0]) / prices[0]
        return momentum

    def _get_volume_strength(self, symbol: str) -> float:
        """
        Calculate volume strength (current volume vs average).
        Returns: ratio of recent volume to average
        """
        if symbol not in self.recent_volumes or len(self.recent_volumes[symbol]) < 2:
            return 1.0
        
        volumes = list(self.recent_volumes[symbol])
        current_vol = volumes[-1]
        avg_vol = np.mean(volumes[:-1])
        
        if avg_vol == 0:
            return 1.0
        
        return current_vol / avg_vol

    def rank_signals(self, signals: List[Tuple[str, Dict]]) -> List[Tuple[str, Dict, float]]:
        """
        Rank signals by quality.
        
        Args:
            signals: List of (symbol, signal_dict) tuples
            
        Returns:
            List of (symbol, signal_dict, score) sorted by score (highest first)
        """
        ranked = []
        
        for symbol, signal in signals:
            # Base score from signal type
            action = signal.get("action", "").lower()
            base_score = 1.0 if action in ("buy", "sell") else 0.0
            
            # Add points for momentum (trades in direction of momentum)
            momentum = self._get_momentum(symbol)
            if action == "buy":
                momentum_score = max(0, momentum * 100)  # Reward upward momentum
            else:
                momentum_score = max(0, -momentum * 100)  # Reward downward momentum
            
            # Add points for volume strength
            vol_strength = self._get_volume_strength(symbol)
            vol_score = max(0, (vol_strength - 1) * 50)  # Reward above-average volume
            
            # Add points for volatility (some is good, too much is risky)
            volatility = self._get_volatility(symbol)
            vol_risk_score = min(50, max(0, volatility * 100))  # Cap at 50
            
            # Total score
            total_score = base_score * 100 + momentum_score + vol_score + vol_risk_score
            
            ranked.append((symbol, signal, total_score))
        
        # Sort by score (highest first)
        ranked.sort(key=lambda x: x[2], reverse=True)
        
        return ranked

    def get_best_signals(self, signals: List[Tuple[str, Dict]], top_n: int = 3) -> List[Tuple[str, Dict]]:
        """
        Get top N signals by quality.
        
        Args:
            signals: List of (symbol, signal_dict) tuples
            top_n: Number of best signals to return
            
        Returns:
            List of top (symbol, signal_dict) tuples
        """
        ranked = self.rank_signals(signals)
        return [(sym, sig) for sym, sig, _ in ranked[:top_n]]


class ConflictResolver:
    """
    When multiple stocks compete for the same capital pool,
    resolve conflicts intelligently.
    """

    @staticmethod
    def filter_by_price(signals: List[Tuple[str, Dict, float]], min_price: float = 50, max_price: float = 5000) -> List[Tuple[str, Dict, float]]:
        """Filter signals by price range (avoid microcaps and expensive stocks)."""
        filtered = []
        for symbol, signal, score in signals:
            price = signal.get("price", 100)
            if min_price <= price <= max_price:
                filtered.append((symbol, signal, score))
        return filtered

    @staticmethod
    def filter_by_recent_loss(symbol_to_recent_pnl: Dict[str, float], signals: List[Tuple[str, Dict, float]]) -> List[Tuple[str, Dict, float]]:
        """
        Don't immediately re-trade a stock that just lost.
        Cooldown period mental accounting.
        """
        filtered = []
        for symbol, signal, score in signals:
            recent_pnl = symbol_to_recent_pnl.get(symbol, 0)
            # Only penalize if loss was very recent (reduce score by 50% if lost)
            if recent_pnl < -50:
                score *= 0.5
            filtered.append((symbol, signal, score))
        return filtered

    @staticmethod
    def allocate_capital(
        signals: List[Tuple[str, Dict, float]],
        available_capital: float,
        per_position_capital: float,
        max_positions: int
    ) -> Dict[str, float]:
        """
        Allocate capital to best signals.
        
        Returns: Dict[symbol -> allocated_capital]
        """
        allocation = {}
        remaining_capital = available_capital
        
        for symbol, signal, score in signals[:max_positions]:  # Top N signals
            if remaining_capital >= per_position_capital:
                allocation[symbol] = per_position_capital
                remaining_capital -= per_position_capital
        
        return allocation
