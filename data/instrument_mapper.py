import requests
import pandas as pd
import os
import json

MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
CACHE_FILE = "data/instruments_nse_eq.json"


class AngelInstrumentMapper:

    def __init__(self, force_refresh: bool = False):
        """
        force_refresh=True → re-download master file
        """
        if force_refresh or not os.path.exists(CACHE_FILE):
            # print("Downloading instrument master...")
            self.symbol_to_token = self._download_and_build()
            self._save_cache()
        else:
            # print("Loading instruments from cache...")
            self.symbol_to_token = self._load_cache()

        # print(f"Loaded {len(self.symbol_to_token)} NSE equity instruments")

    # -----------------------------------
    # Download and build mapping
    # -----------------------------------
    def _download_and_build(self):
        resp = requests.get(MASTER_URL, timeout=30)
        resp.raise_for_status()

        master = resp.json()
        df = pd.DataFrame(master)

        # Filter NSE Equity
        df = df[
            (df["exch_seg"] == "NSE") &
            (df["symbol"].str.endswith("-EQ"))
        ]

        mapping = {
            row["symbol"].replace("-EQ", ""): row["token"]
            for _, row in df.iterrows()
        }

        return mapping

    # -----------------------------------
    def _save_cache(self):
        os.makedirs("data", exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(self.symbol_to_token, f)

    # -----------------------------------
    def _load_cache(self):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)

    # -----------------------------------
    # Public lookup
    # -----------------------------------
    def get_token(self, symbol: str):
        token = self.symbol_to_token.get(symbol.upper())
        if not token:
            raise ValueError(f"Token not found for symbol: {symbol}")
        return token

    def get_tokens(self, symbols):
        return {s: self.get_token(s) for s in symbols}

    def all_symbols(self):
        return list(self.symbol_to_token.keys())


# -----------------------------------
# Example Usage
# -----------------------------------
if __name__ == "__main__":

    mapper = AngelInstrumentMapper(force_refresh=False)

    # Single lookup
    print("RELIANCE token:", mapper.get_token("RELIANCE"))

    # Multiple lookup
    pool = ["RELIANCE", "TCS", "INFY"]
    print("Pool tokens:", mapper.get_tokens(pool))

    # Total available stocks
    print("Total NSE EQ stocks:", len(mapper.all_symbols()))