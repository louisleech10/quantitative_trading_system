"""
Debug 時間戳匹配問題
"""
import h5py
import pandas as pd
import json
from datetime import datetime

# 1. 檢查 K 線數據
print("=" * 60)
print("1. K 線數據時間戳檢查")
print("=" * 60)

h5_path = 'data_cache/kline_cache.h5'

# 先查看結構
print("查看 HDF5 檔案結構...")
with h5py.File(h5_path, 'r') as f:
    def print_attrs(name, obj):
        print(f'{name}')
        if isinstance(obj, h5py.Group):
            for key in obj.attrs.keys():
                print(f'  attr: {key} = {obj.attrs[key]}')
        elif isinstance(obj, h5py.Dataset):
            print(f'  shape: {obj.shape}, dtype: {obj.dtype}')
    f.visititems(print_attrs)

# 讀取數據
with h5py.File(h5_path, 'r') as f:
    dataset = f['ETHUSDT/1h/data']
    data = dataset[:]
    df = pd.DataFrame(data)

print(f'總行數: {len(df)}')
print(f'\n欄位: {df.columns.tolist()}')
print(f'\ntimestamp 範例:')
print(df['timestamp'].head())

ts_min = df['timestamp'].min()
ts_max = df['timestamp'].max()

print(f'\ntimestamp 最小值: {ts_min}')
print(f'timestamp 最大值: {ts_max}')

# 判斷單位
if ts_min > 10**12:
    print('\ntimestamp 單位: 毫秒')
    dt_min = datetime.fromtimestamp(ts_min / 1000)
    dt_max = datetime.fromtimestamp(ts_max / 1000)
else:
    print('\ntimestamp 單位: 秒')
    dt_min = datetime.fromtimestamp(ts_min)
    dt_max = datetime.fromtimestamp(ts_max)

print(f'時間範圍: {dt_min} ~ {dt_max}')

# 2. 檢查案例數據
print("\n" + "=" * 60)
print("2. 案例數據時間戳檢查")
print("=" * 60)

with open('data_cache/cases.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

cases = data.get('cases', [])
ethusdt_cases = [c for c in cases if c.get('symbol') == 'ETHUSDT']

print(f'ETHUSDT 案例數: {len(ethusdt_cases)}')

if ethusdt_cases:
    first_case = ethusdt_cases[0]
    last_case = ethusdt_cases[-1]
    
    case_ts_min = first_case['timestamp']
    case_ts_max = last_case['timestamp']
    
    print(f'\n案例 timestamp 範例: {case_ts_min}')
    print(f'案例 timestamp 單位: 秒')
    print(f'時間範圍: {datetime.fromtimestamp(case_ts_min)} ~ {datetime.fromtimestamp(case_ts_max)}')

# 3. 檢查匹配問題
print("\n" + "=" * 60)
print("3. 時間戳匹配診斷")
print("=" * 60)

# 建立 timestamp_sec 欄位（模擬 xgboost_batch_service 的邏輯）
if ts_min > 10**12:  # 毫秒
    df['timestamp_sec'] = (df['timestamp'] // 1000).astype(int)
    print(f'\nK 線 timestamp 單位: 毫秒')
else:  # 秒
    df['timestamp_sec'] = df['timestamp'].astype(int)
    print(f'\nK 線 timestamp 單位: 秒')
    
print(f'timestamp 範例: {df["timestamp"].head().tolist()}')
print(f'timestamp_sec 範例: {df["timestamp_sec"].head().tolist()}')

# 測試匹配
print(f'\n測試匹配第一個案例:')
case_ts = ethusdt_cases[0]['timestamp']
print(f'案例時間戳: {case_ts}')
matched = df[df['timestamp_sec'] == case_ts]
print(f'匹配結果: {len(matched)} 行')

if len(matched) == 0:
    print(f'\n❌ 無法匹配！')
    print(f'可能原因：')
    print(f'1. timestamp 欄位不存在或格式不對')
    print(f'2. 案例時間戳與 K 線時間戳單位不一致')
    print(f'3. 案例時間超出 K 線數據範圍')
    
    # 檢查最接近的時間戳
    df['time_diff'] = (df['timestamp_sec'] - case_ts).abs()
    closest = df.nsmallest(5, 'time_diff')[['timestamp_sec', 'time_diff']]
    print(f'\n最接近的 5 個時間戳:')
    print(closest)
else:
    print(f'✅ 匹配成功！')
    print(matched[['timestamp', 'timestamp_sec']].head())
