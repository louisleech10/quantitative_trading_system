"""
Phase 3.1.1 EMA 計算驗證 - Binance 圖表比對版

目的：
1. 輸出系統計算的 EMA 值及對應時間點
2. 提供可與 Binance 圖表直接比對的格式化數據
3. 驗證計算正確性

驗證步驟：
1. 運行此腳本獲取 EMA 值（匯出為 CSV）
2. 打開 CSV，找到想比對的時間點
3. 打開 Binance 圖表，切換到對應時間框架
4. 添加 EMA 指標，比對數值
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from momentum.Indicators import EMAIndicator
from momentum.DataExtraction.kline_storage import KlineStorageManager

# 初始化
indicator = EMAIndicator()
storage_manager = KlineStorageManager()

# 配置參數
symbol = "ETHUSDT"
timeframe = "12h"
ema_periods = [12, 26, 50]

print("=" * 100)
print(f"📊 {symbol} {timeframe} EMA 驗證報告 - 與 Binance 比對")
print("=" * 100)

try:
    # 步驟1: 讀取HDF5數據
    print(f"\n📦 正在讀取 {symbol}/{timeframe} 的HDF5數據...")
    df = storage_manager.read_klines(
        symbol=symbol,
        timeframe=timeframe,
        validate_continuity=False  # K線下載時已檢查，這裡不重複
    )
    
    if df is None or len(df) == 0:
        print(f"\n❌ 錯誤: 無法讀取 {symbol}/{timeframe} 的數據")
        print(f"請確保已執行批量K線下載")
        sys.exit(1)
    
    hdf5_start_ts = df['timestamp'].iloc[0]
    hdf5_end_ts = df['timestamp'].iloc[-1]
    hdf5_start_time = datetime.utcfromtimestamp(hdf5_start_ts).replace(tzinfo=timezone.utc)
    hdf5_end_time = datetime.utcfromtimestamp(hdf5_end_ts).replace(tzinfo=timezone.utc)
    
    print(f"✅ 成功讀取 {len(df)} 根K線")
    print(f"   數據範圍: {hdf5_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} ~ {hdf5_end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # 步驟2: 計算 EMA（對所有 K 線）
    print(f"\n📊 計算 EMA{ema_periods}...")
    close_data = df['close']
    ema_results = {}
    for period in ema_periods:
        ema_results[f'EMA_{period}'] = indicator.calculate(close_data, period=period)
    
    print(f"✅ EMA 計算完成")
    
    # 步驟3: 準備輸出資料
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
    
    # 加入 EMA 欄位
    for ema_name, ema_values in ema_results.items():
        df[ema_name] = ema_values

except Exception as e:
    print(f"\n❌ 驗證過程發生錯誤: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # 確保 HDF5 資源被釋放
    if 'storage_manager' in locals():
        del storage_manager
    import gc
    gc.collect()

# 步驟4: 顯示驗證結果
print(f"\n{'='*100}")
print(f"📊 資料摘要")
print(f"{'='*100}")
print(f"\n資料範圍:")
print(f"  起始: {df['datetime'].iloc[0]}")
print(f"  結束: {df['datetime'].iloc[-1]}")
print(f"  總筆數: {len(df)} 根 K 線")

# 顯示最近 15 根 K 線的 EMA 值
print(f"\n{'='*100}")
print(f"📈 最近 15 根 K 線的 EMA 值")
print(f"{'='*100}")
print(f"\n{'時間 (UTC)':<25} {'收盤價':>12} {'EMA(12)':>12} {'EMA(26)':>12} {'EMA(50)':>12}")
print("-" * 100)

recent_data = df.tail(15)
for idx, row in recent_data.iterrows():
    dt_str = row['datetime'].strftime('%Y-%m-%d %H:%M:%S')
    ema_12 = row['EMA_12'] if pd.notna(row['EMA_12']) else float('nan')
    ema_26 = row['EMA_26'] if pd.notna(row['EMA_26']) else float('nan')
    ema_50 = row['EMA_50'] if pd.notna(row['EMA_50']) else float('nan')
    print(f"{dt_str:<25} {row['close']:>12.2f} {ema_12:>12.2f} {ema_26:>12.2f} {ema_50:>12.2f}")

# 匯出 CSV 供進一步分析
csv_filename = f"{symbol}_{timeframe}_EMA_驗證_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
df.to_csv(csv_filename, index=False)

print(f"\n{'='*100}")
print(f"📋 驗證方式")
print(f"{'='*100}")
print(f"""
1. CSV 檔案已匯出: {csv_filename}

2. 開啟 CSV，找到想比對的時間點（所有 HDF5 資料都在裡面）

3. 打開 Binance 圖表: https://www.binance.com/zh-TC/trade/{symbol.replace('USDT', '_USDT')}
   - 設置時間框架: {timeframe}
   - 添加 EMA 指標: 週期 12, 26, 50

4. 比對對應時間點的 EMA 值

注意：
- CSV 前面的資料可能包含暖機期（EMA 值為 NaN 或不穩定）
- 建議從有穩定 EMA 值的時間點開始比對
- 使用者自行決定從哪一行開始驗證
""")

print(f"\n{'='*100}")
print(f"✅ 驗證腳本執行完成")
print(f"{'='*100}\n")
