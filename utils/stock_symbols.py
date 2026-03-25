import requests
import pandas as pd

def get_nse_index(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    data = requests.get(url, headers=headers).json()
    return [item["symbol"] for item in data["data"]]

# NSE index endpoints
NIFTY200_URL = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20200"
MIDCAP100_URL = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20MIDCAP%20100"
SMALLCAP100_URL = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20SMALLCAP%20100"

nifty200 = set(get_nse_index(NIFTY200_URL))
midcap100 = set(get_nse_index(MIDCAP100_URL))
smallcap100 = set(get_nse_index(SMALLCAP100_URL))

# Combine (avoid duplicates)
combined = list(nifty200 | midcap100 | smallcap100)

# Sort for consistency
combined.sort()
file_path = "nifty_universe.txt"

with open(file_path, "w") as f:
    # Option 1: one line (your preferred format)
    formatted = ', '.join([f'"{s}"' for s in combined])
    f.write(formatted)

print(f"Total symbols: {len(combined)}")
print(combined[:50])