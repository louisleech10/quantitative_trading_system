"""
Phase 3.1.1 EMA 計算驗證 - Binance 圖表比對版

目的：
1. 輸出系統計算的 EMA 值及對應時間點
2. 提供可與 Binance 圖表直接比對的格式化數據
3. 驗證計算正確性

驗證步驟：
1. 運行此腳本獲取 EMA 值
2. 打開 Binance: https://www.binance.com/zh-TC/trade/BTC_USDT
3. 切換到 12h 時間框架
4. 添加指標: EMA(12), EMA(26), EMA(50)
5. 對比關鍵時間點的數值
"""

import pandas as pd
from momentum.Indicators import EMAIndicator, DataSourceManager
from datetime import datetime, timezone

# 初始化
indicator = EMAIndicator()
manager = DataSourceManager()

# 獲取數據
symbol = "BTCUSDT"
timeframe = "12h"
df = manager.get_dataframe(symbol, timeframe)
close_data = df['close']

# 計算 EMA
ema_12 = indicator.calculate(close_data, period=12)
ema_26 = indicator.calculate(close_data, period=26)
ema_50 = indicator.calculate(close_data, period=50)

# 將 timestamp 轉換為 datetime
df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)

# 創建結果 DataFrame
result_df = pd.DataFrame({
    'datetime': df['datetime'],
    'close': df['close'],
    'EMA_12': ema_12,
    'EMA_26': ema_26,
    'EMA_50': ema_50
})

# 去除前面的 NaN 值（EMA warmup period）
result_df = result_df[result_df['EMA_50'].notna()].copy()

print("=" * 100)
print(f"📊 {symbol} {timeframe} EMA 驗證報告 - 與 Binance 比對")
print("=" * 100)

# 顯示數據範圍
print(f"\n數據範圍:")
print(f"  起始: {result_df['datetime'].iloc[0]}")
print(f"  結束: {result_df['datetime'].iloc[-1]}")
print(f"  總筆數: {len(result_df)} 根 K線")

# 顯示最近 15 筆數據（完整表格）
print(f"\n{'='*100}")
print(f"📈 最近 15 根 K線的 EMA 值（可與 Binance 圖表比對）")
print(f"{'='*100}")
print(f"\n{'時間 (UTC)':<25} {'收盤價':>12} {'EMA(12)':>12} {'EMA(26)':>12} {'EMA(50)':>12}")
print("-" * 100)

recent_data = result_df.tail(15)
for idx, row in recent_data.iterrows():
    dt_str = row['datetime'].strftime('%Y-%m-%d %H:%M:%S')
    print(f"{dt_str:<25} {row['close']:>12.2f} {row['EMA_12']:>12.2f} {row['EMA_26']:>12.2f} {row['EMA_50']:>12.2f}")

# 顯示關鍵驗證點
print(f"\n{'='*100}")
print(f"🎯 關鍵驗證點（建議在 Binance 圖表上標記）")
print(f"{'='*100}")

# 最新一筆
latest = result_df.iloc[-1]
print(f"\n1️⃣  最新 K線（當前）:")
print(f"   時間: {latest['datetime'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"   收盤: {latest['close']:.2f} USDT")
print(f"   EMA(12): {latest['EMA_12']:.2f}")
print(f"   EMA(26): {latest['EMA_26']:.2f}")
print(f"   EMA(50): {latest['EMA_50']:.2f}")

# 7 天前（約 14 根 12h K線）
if len(result_df) >= 14:
    week_ago = result_df.iloc[-14]
    print(f"\n2️⃣  7天前:")
    print(f"   時間: {week_ago['datetime'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   收盤: {week_ago['close']:.2f} USDT")
    print(f"   EMA(12): {week_ago['EMA_12']:.2f}")
    print(f"   EMA(26): {week_ago['EMA_26']:.2f}")
    print(f"   EMA(50): {week_ago['EMA_50']:.2f}")

# 30 天前（約 60 根 12h K線）
if len(result_df) >= 60:
    month_ago = result_df.iloc[-60]
    print(f"\n3️⃣  30天前:")
    print(f"   時間: {month_ago['datetime'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   收盤: {month_ago['close']:.2f} USDT")
    print(f"   EMA(12): {month_ago['EMA_12']:.2f}")
    print(f"   EMA(26): {month_ago['EMA_26']:.2f}")
    print(f"   EMA(50): {month_ago['EMA_50']:.2f}")

# Binance 驗證指引
print(f"\n{'='*100}")
print(f"📋 Binance 圖表驗證步驟")
print(f"{'='*100}")
print(f"""
1. 打開 Binance 圖表:
   https://www.binance.com/zh-TC/trade/BTC_USDT

2. 設置時間框架:
   點擊圖表右上角，選擇「12h」

3. 添加 EMA 指標:
   - 點擊「指標」按鈕
   - 搜索「EMA」
   - 添加 3 條 EMA: 週期分別為 12, 26, 50

4. 驗證方法:
   - 將滑鼠移動到最新 K線上
   - 查看 Tooltip 顯示的 EMA 值
   - 與上面「最新 K線」的數值比對
   - 誤差應在 ±0.5% 以內（考慮 Binance 實時更新）

5. 歷史數據驗證:
   - 點擊圖表上的特定 K線（如 7天前、30天前）
   - 記錄 EMA 值
   - 與上面「關鍵驗證點」比對
   - 歷史數據誤差應 < ±0.1%

6. 通過標準:
   ✅ 至少 3 個驗證點的 EMA 值與 Binance 誤差 < 0.5%
   ✅ 歷史固定時間點的誤差 < 0.1%
   ✅ EMA 線的走勢趨勢一致
""")

# 匯出 CSV 供進一步分析
csv_filename = f"{symbol}_{timeframe}_EMA_驗證_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
result_df.to_csv(csv_filename, index=False)
print(f"\n💾 完整數據已匯出至: {csv_filename}")
print(f"   可用 Excel 打開進行詳細比對")

print(f"\n{'='*100}")
print(f"驗證完成！請按照上述步驟在 Binance 圖表上進行比對。")
print(f"{'='*100}\n")
