
import pandas as pd

# 檢查某個檔案的數據
file_path = "data_cache/ETHUSDT_12h.h5"
df = pd.read_hdf(file_path, key='data')  # 正確的 key 是 'data'

print(f"數據筆數: {len(df)}")
print(f"日期範圍: {df.index[0]} 至 {df.index[-1]}")
print(f"欄位: {df.columns.tolist()}")
print(f"缺失值: {df.isnull().sum().sum()}")

# 查看最近10筆收盤價
print("\n最近10筆收盤價:")
print(df['close'].tail(10))
print(df['high'].tail(10))
print(df['volume'].tail(10))