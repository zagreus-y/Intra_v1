"""
SmartAPI Data Provider (Angel One broker)
Implements the DataProvider interface.
"""

from SmartApi import SmartConnect
import pyotp
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List
from .base_data_provider import DataProvider


class SmartAPIDataProvider(DataProvider):
    """
    Angel One SmartAPI implementation of DataProvider.
    """

    def __init__(
        self,
        api_key: str,
        client_code: str,
        password: str,
        totp_secret: str
    ):
        self.api_key = api_key
        self.client_code = client_code
        self.password = password
        self.totp_secret = totp_secret
        self.obj = None
        self.jwtToken = None
        self.refreshToken = None
        self._login()

    def _login(self):
        """Authenticate and create session."""
        self.obj = SmartConnect(api_key=self.api_key)
        totp = pyotp.TOTP(self.totp_secret).now()
        
        session = self.obj.generateSession(
            self.client_code, 
            self.password, 
            totp
        )

        if not session.get("status"):
            raise Exception(f"SmartAPI login failed: {session}")

        self.jwtToken = session.get("data", {}).get("jwtToken")
        self.refreshToken = session.get("data", {}).get("refreshToken")
        print("✓ SmartAPI login successful")

    def get_candles(
        self,
        symbol: str,
        interval: str = "5m",
        lookback_days: int = 5,
        exchange: str = "NSE"
    ) -> pd.DataFrame:
        """
        Fetch OHLCV candles from SmartAPI.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            interval: Candle interval ("1m", "5m", "15m", "1h", "daily")
            lookback_days: Number of days to fetch
            exchange: Exchange name (default "NSE")
            
        Returns:
            DataFrame with columns: [datetime, open, high, low, close, volume]
            Index is datetime
        """
        # Map interval names
        interval_map = {
            "1m": "ONE_MINUTE",
            "5m": "FIVE_MINUTE",
            "15m": "FIFTEEN_MINUTE",
            "1h": "HOURLY",
            "daily": "DAILY"
        }
        
        api_interval = interval_map.get(interval, "FIVE_MINUTE")
        
        to_date = datetime.now()
        from_date = to_date - timedelta(days=lookback_days)

        token = self._get_token(symbol, exchange)
        
        params = {
            "exchange": exchange,
            "tradingsymbol": symbol,
            "symboltoken": token,
            "interval": api_interval,
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M")
        }

        data = self.obj.getCandleData(params)

        if not data.get("status"):
            raise Exception(f"Failed to fetch candles: {data}")

        candles = data.get("data", [])
        if not candles:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(candles, columns=[
            "datetime", "open", "high", "low", "close", "volume"
        ])
        
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        df = df.astype(float)
        
        return df

    def get_ltp(self, symbol: str, exchange: str = "NSE") -> float:
        """
        Fetch Last Traded Price.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name (default "NSE")
            
        Returns:
            Last traded price as float
        """
        token = self._get_token(symbol, exchange)
        ltp_data = self.obj.ltpData(exchange, symbol, token)
        
        if not ltp_data.get("status"):
            raise Exception(f"Failed to fetch LTP: {ltp_data}")
        
        return float(ltp_data["data"]["ltp"])

    def is_market_open(self) -> bool:
        """
        Check if NSE market is open (9:15 AM - 3:30 PM IST, Mon-Fri).
        
        Returns:
            True if market is open, False otherwise
        """
        import pytz
        
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        
        # Weekend check
        if now.weekday() >= 5:
            return False
        
        # Market hours: 9:15 AM to 3:30 PM
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return market_open <= now <= market_close

    def _get_token(self, symbol: str, exchange: str = "NSE") -> str:
        """
        Fetch token from Angel One master instrument list.
        Caches tokens for performance.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            exchange: Exchange name (default "NSE")
            
        Returns:
            Token string for the symbol
        """
        if not hasattr(self, '_token_cache'):
            self._token_cache = {}
        
        cache_key = f"{symbol}_{exchange}"
        
        if cache_key in self._token_cache:
            return self._token_cache[cache_key]
        
        from data.instrument_mapper import AngelInstrumentMapper
        
        mapper = AngelInstrumentMapper()
        tokens = mapper.get_tokens([symbol])
        
        if symbol not in tokens:
            raise ValueError(f"Symbol {symbol} not found in Angel One master list")
        
        token = tokens[symbol]
        self._token_cache[cache_key] = token
        return token

    def get_profile(self) -> dict:
        """Get user profile info."""
        return self.obj.getProfile(self.refreshToken)

    # ============ BACKWARDS COMPATIBILITY METHODS ============
    # These methods support old code that uses the previous interface
    
    def get_intraday_candles(
        self,
        symbol_token: str = None,
        symbol: str = None,
        exchange: str = "NSE",
        interval: str = "FIVE_MINUTE",
        lookback_days: int = 5
    ) -> List[List]:
        """
        DEPRECATED: Use get_candles() instead.
        
        Backwards compatibility method for old code.
        Converts raw Angel One candle format to list of lists.
        
        Args:
            symbol_token: Angel One token OR symbol name (for backwards compat)
            symbol: Symbol name (optional, takes precedence over symbol_token)
            exchange: Exchange name
            interval: Angel One interval format (ONE_MINUTE, FIVE_MINUTE, etc.)
            lookback_days: Number of days to fetch
            
        Returns:
            List of [timestamp, open, high, low, close, volume]
        """
        # Determine which symbol to use
        if symbol is None:
            symbol = symbol_token
        
        # Map interval format
        interval_map = {
            "ONE_MINUTE": "1m",
            "FIVE_MINUTE": "5m",
            "FIFTEEN_MINUTE": "15m",
            "HOURLY": "1h",
            "DAILY": "daily"
        }
        
        interval_short = interval_map.get(interval, "5m")
        
        # Get dataframe
        df = self.get_candles(symbol, interval=interval_short, lookback_days=lookback_days, exchange=exchange)
        
        if df.empty:
            return []
        
        # Convert to list of lists format [timestamp, open, high, low, close, volume]
        result = []
        for ts, row in df.iterrows():
            result.append([
                str(ts),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                int(row["volume"])
            ])
        
        return result

    def get_live_quote(self, symbol: str, exchange: str = "NSE") -> dict:
        """
        Get live market data for a symbol.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            
        Returns:
            Dictionary with ltp, bid, ask, etc. from Angel One ltpData
        """
        token = self._get_token(symbol, exchange)
        ltp_data = self.obj.ltpData(exchange, symbol, token)
        
        if not ltp_data.get("status"):
            return {"ltp": None, "bid": None, "ask": None}
        
        data = ltp_data.get("data", {})
        return {
            "ltp": float(data.get("ltp", 0)),
            "bid": float(data.get("bid", 0)),
            "ask": float(data.get("ask", 0)),
            "volume": int(data.get("volume", 0)),
            "timestamp": data.get("exchange_time")
        }