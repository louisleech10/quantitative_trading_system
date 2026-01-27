#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試項目 2.1: 三線順勢策略信號生成驗證

功能:
1. 從HDF5讀取ETHUSDT 12h K線數據
2. 計算三條EMA (12, 26, 50)
3. 生成三線順勢信號 (買入: EMA_12 > EMA_26 > EMA_50, 賣出: EMA_12 < EMA_26 < EMA_50)
4. 輸出CSV檔案供Binance圖表比對
5. 生成統計報告

輸出:
- ETHUSDT_12h_三線順勢_BUY信號_[timestamp].csv
- ETHUSDT_12h_三線順勢_SELL信號_[timestamp].csv
- ETHUSDT_12h_三線順勢_完整數據_[timestamp].csv
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

# 添加項目路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.Indicators.ema_indicator import EMAIndicator

def main():
    print("=" * 80)
    print("測試項目 2.1: 三線順勢策略信號生成驗證")
    print("=" * 80)

    # 配置參數
    symbol = "ETHUSDT"
    timeframe = "1h"
    ema_periods = {
        'short': 12,
        'mid': 26,
        'long': 50
    }

    print(f"\n【測試配置】")
    print(f"交易對: {symbol}")
    print(f"時間週期: {timeframe}")
    print(f"EMA參數: 短期={ema_periods['short']}, 中期={ema_periods['mid']}, 長期={ema_periods['long']}")

    # ========================================================================
    # Step 1: 讀取K線數據
    # ========================================================================
    print(f"\n【Step 1】讀取K線數據...")

    storage = KlineStorageManager()

    try:
        df = storage.read_klines(symbol=symbol, timeframe=timeframe)
        print(f"✓ 成功讀取 {len(df)} 根K線")
        print(f"  時間範圍: {pd.to_datetime(df['timestamp'].iloc[0], unit='s', utc=True)} ~ {pd.to_datetime(df['timestamp'].iloc[-1], unit='s', utc=True)}")
    except Exception as e:
        print(f"✗ 讀取K線失敗: {e}")
        return

    # 添加UTC時間欄位 (用於Binance比對)
    df['datetime_utc'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)

    # ========================================================================
    # Step 2: 計算EMA指標
    # ========================================================================
    print(f"\n【Step 2】計算EMA指標...")

    indicator = EMAIndicator()

    try:
        # 計算三條EMA
        ema_short = indicator.calculate(df['close'], period=ema_periods['short'])
        ema_mid = indicator.calculate(df['close'], period=ema_periods['mid'])
        ema_long = indicator.calculate(df['close'], period=ema_periods['long'])

        # 添加到DataFrame
        df['ema_12'] = ema_short
        df['ema_26'] = ema_mid
        df['ema_50'] = ema_long

        # 檢查NaN值
        nan_count_short = ema_short.isna().sum()
        nan_count_mid = ema_mid.isna().sum()
        nan_count_long = ema_long.isna().sum()

        print(f"✓ EMA計算完成")
        print(f"  EMA_{ema_periods['short']}: {nan_count_short} NaN值 (預期: {ema_periods['short']-1})")
        print(f"  EMA_{ema_periods['mid']}: {nan_count_mid} NaN值 (預期: {ema_periods['mid']-1})")
        print(f"  EMA_{ema_periods['long']}: {nan_count_long} NaN值 (預期: {ema_periods['long']-1})")

    except Exception as e:
        print(f"✗ EMA計算失敗: {e}")
        return

    # ========================================================================
    # Step 3: 生成三線順勢信號
    # ========================================================================
    print(f"\n【Step 3】生成三線順勢信號...")

    # 三線順勢條件
    # 買入信號 (多頭排列): EMA_short > EMA_mid > EMA_long
    buy_condition = (df['ema_12'] > df['ema_26']) & (df['ema_26'] > df['ema_50'])

    # 賣出信號 (空頭排列): EMA_short < EMA_mid < EMA_long
    sell_condition = (df['ema_12'] < df['ema_26']) & (df['ema_26'] < df['ema_50'])

    # 添加信號欄位
    df['buy_signal'] = buy_condition
    df['sell_signal'] = sell_condition

    # 統計信號數量
    buy_count = buy_condition.sum()
    sell_count = sell_condition.sum()
    valid_bars = len(df) - df['ema_50'].isna().sum()  # 扣除warmup期間

    print(f"✓ 信號生成完成")
    print(f"  有效K線數: {valid_bars}")
    print(f"  買入信號 (多頭排列): {buy_count} 次 ({buy_count/valid_bars*100:.2f}%)")
    print(f"  賣出信號 (空頭排列): {sell_count} 次 ({sell_count/valid_bars*100:.2f}%)")

    # ========================================================================
    # Step 4: 提取信號點位
    # ========================================================================
    print(f"\n【Step 4】提取信號點位...")

    # 買入信號點位
    buy_signals_df = df[df['buy_signal']].copy()
    buy_signals_df['signal_type'] = 'BUY'
    buy_signals_df['datetime_utc_str'] = buy_signals_df['datetime_utc'].dt.strftime('%Y-%m-%d %H:%M:%S UTC')

    # 賣出信號點位
    sell_signals_df = df[df['sell_signal']].copy()
    sell_signals_df['signal_type'] = 'SELL'
    sell_signals_df['datetime_utc_str'] = sell_signals_df['datetime_utc'].dt.strftime('%Y-%m-%d %H:%M:%S UTC')

    # 選擇輸出欄位
    output_columns = [
        'timestamp',
        'datetime_utc_str',
        'close',
        'ema_12',
        'ema_26',
        'ema_50',
        'signal_type'
    ]

    buy_export = buy_signals_df[output_columns].copy()
    sell_export = sell_signals_df[output_columns].copy()

    print(f"✓ 信號點位提取完成")
    print(f"  買入信號點位: {len(buy_export)}")
    print(f"  賣出信號點位: {len(sell_export)}")

    # ========================================================================
    # Step 5: 輸出CSV檔案
    # ========================================================================
    print(f"\n【Step 5】輸出CSV檔案...")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 輸出買入信號
    buy_filename = f"{symbol}_{timeframe}_三線順勢_BUY信號_{timestamp}.csv"
    buy_export.to_csv(buy_filename, index=False, encoding='utf-8-sig')
    print(f"✓ 買入信號已輸出: {buy_filename}")

    # 輸出賣出信號
    sell_filename = f"{symbol}_{timeframe}_三線順勢_SELL信號_{timestamp}.csv"
    sell_export.to_csv(sell_filename, index=False, encoding='utf-8-sig')
    print(f"✓ 賣出信號已輸出: {sell_filename}")

    # 輸出完整數據 (包含所有K線與EMA值)
    full_data_columns = [
        'timestamp',
        'datetime_utc',
        'open',
        'high',
        'low',
        'close',
        'volume',
        'ema_12',
        'ema_26',
        'ema_50',
        'buy_signal',
        'sell_signal'
    ]

    df['datetime_utc_str'] = df['datetime_utc'].dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    full_export = df[['timestamp', 'datetime_utc_str', 'open', 'high', 'low', 'close', 'volume',
                      'ema_12', 'ema_26', 'ema_50', 'buy_signal', 'sell_signal']].copy()

    full_filename = f"{symbol}_{timeframe}_三線順勢_完整數據_{timestamp}.csv"
    full_export.to_csv(full_filename, index=False, encoding='utf-8-sig')
    print(f"✓ 完整數據已輸出: {full_filename}")

    # ========================================================================
    # Step 6: 顯示信號範例
    # ========================================================================
    print(f"\n【Step 6】信號範例展示...")

    if len(buy_export) > 0:
        print(f"\n--- 買入信號範例 (前5筆) ---")
        print(buy_export.head().to_string(index=False))
    else:
        print(f"\n--- 無買入信號 ---")

    if len(sell_export) > 0:
        print(f"\n--- 賣出信號範例 (前5筆) ---")
        print(sell_export.head().to_string(index=False))
    else:
        print(f"\n--- 無賣出信號 ---")

    # ========================================================================
    # Step 7: 統計報告
    # ========================================================================
    print(f"\n{'=' * 80}")
    print("【統計報告】")
    print(f"{'=' * 80}")
    print(f"交易對: {symbol}")
    print(f"時間週期: {timeframe}")
    print(f"EMA參數: 短期={ema_periods['short']}, 中期={ema_periods['mid']}, 長期={ema_periods['long']}")
    print(f"\n數據統計:")
    print(f"  總K線數: {len(df)}")
    print(f"  有效K線數 (扣除warmup): {valid_bars}")
    print(f"  Warmup期間: {len(df) - valid_bars} 根K線")
    print(f"\n信號統計:")
    print(f"  買入信號 (多頭排列): {buy_count} 次 ({buy_count/valid_bars*100:.2f}%)")
    print(f"  賣出信號 (空頭排列): {sell_count} 次 ({sell_count/valid_bars*100:.2f}%)")
    print(f"  中性 (不符合三線順勢): {valid_bars - buy_count - sell_count} 次 ({(valid_bars - buy_count - sell_count)/valid_bars*100:.2f}%)")

    if buy_count > 0:
        print(f"\n買入信號密度分析:")
        print(f"  平均間隔: {valid_bars/buy_count:.2f} 根K線")
        print(f"  首次出現: {buy_export.iloc[0]['datetime_utc_str']}")
        print(f"  最後出現: {buy_export.iloc[-1]['datetime_utc_str']}")

    if sell_count > 0:
        print(f"\n賣出信號密度分析:")
        print(f"  平均間隔: {valid_bars/sell_count:.2f} 根K線")
        print(f"  首次出現: {sell_export.iloc[0]['datetime_utc_str']}")
        print(f"  最後出現: {sell_export.iloc[-1]['datetime_utc_str']}")

    # ========================================================================
    # Step 8: Binance比對說明
    # ========================================================================
    print(f"\n{'=' * 80}")
    print("【Binance圖表比對說明】")
    print(f"{'=' * 80}")
    print(f"\n步驟 1: 打開Binance圖表")
    print(f"  網址: https://www.binance.com/zh-TC/trade/ETH_USDT")
    print(f"\n步驟 2: 設定圖表參數")
    print(f"  - 時間週期: 選擇 12h")
    print(f"  - 添加指標: MA (移動平均線)")
    print(f"    - EMA 12 (藍色)")
    print(f"    - EMA 26 (橙色)")
    print(f"    - EMA 50 (紅色)")
    print(f"\n步驟 3: 使用CSV檔案比對")
    print(f"  - 打開CSV檔案: {buy_filename}")
    print(f"  - 從CSV找到一個信號的 datetime_utc_str (例如: 2024-11-08 12:00:00 UTC)")
    print(f"  - 在Binance圖表上找到對應的時間點")
    print(f"  - 比對EMA值:")
    print(f"    ✓ CSV的 ema_12 應該 = Binance圖表的 EMA(12) 值")
    print(f"    ✓ CSV的 ema_26 應該 = Binance圖表的 EMA(26) 值")
    print(f"    ✓ CSV的 ema_50 應該 = Binance圖表的 EMA(50) 值")
    print(f"  - 比對信號邏輯:")
    print(f"    ✓ 買入信號: 藍線(EMA12) > 橙線(EMA26) > 紅線(EMA50) (多頭排列)")
    print(f"    ✓ 賣出信號: 藍線(EMA12) < 橙線(EMA26) < 紅線(EMA50) (空頭排列)")
    print(f"\n步驟 4: 驗證信號準確性")
    print(f"  - 隨機選擇5-10個信號點位進行比對")
    print(f"  - 確認EMA值與信號邏輯與Binance圖表一致")
    print(f"  - 記錄任何差異或異常")

    print(f"\n{'=' * 80}")
    print("測試完成!")
    print(f"{'=' * 80}\n")

if __name__ == "__main__":
    main()
