from data.nse_data import NSEDataHybrid
import time

dp = NSEDataHybrid()

for _ in range(10):
    df = dp.get_ohlcv("TATASTEEL", interval="1m", lookback=5)
    print(df.tail())
    time.sleep(10)
