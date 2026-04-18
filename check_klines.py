import sys
import os

# Add current directory to sys.path to import local modules
sys.path.append(os.getcwd())

from momentum.factories import create_kline_storage_manager

candidates = [
    ("BTCUSDT", "12h"),
    ("ETHUSDT", "1h"),
    ("ETHUSDT", "12h"),
    ("BTCUSDT", "1h"),
    ("SOLUSDT", "1h"),
    ("SOLUSDT", "12h")
]

manager = create_kline_storage_manager()

print(f"{'Symbol':<10} | {'TF':<5} | {'Status':<5} | {'Rows/Error'}")
print("-" * 50)

for symbol, timeframe in candidates:
    try:
        df = manager.read_klines(symbol, timeframe)
        print(f"{symbol:<10} | {timeframe:<5} | PASS  | {len(df)} rows")
    except Exception as e:
        # Get a short error message
        error_msg = str(e).split('\n')[0][:50]
        print(f"{symbol:<10} | {timeframe:<5} | FAIL  | {error_msg}")

