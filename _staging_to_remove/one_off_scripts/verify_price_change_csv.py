"""
驗證 CSV 中的 Price_Change_% 使用的計算方式

使用方法：
1. 下載兩個 CSV 檔案（一個用 OPEN_TO_CLOSE，一個用 CLOSE_TO_CLOSE）
2. 執行此腳本：python verify_price_change_csv.py <csv路徑>

此腳本會：
- 檢查 CSV 中的 Price_Change_% 欄位
- 重新計算 OPEN_TO_CLOSE 和 CLOSE_TO_CLOSE 兩種方式
- 比對哪一種計算方式與 CSV 中的數值最接近
"""

import pandas as pd
import sys
import numpy as np

def verify_price_change_method(csv_path: str):
    """驗證 CSV 中使用的價格計算方式"""
    
    print("=" * 70)
    print(f"驗證文件: {csv_path}")
    print("=" * 70)
    
    # 讀取 CSV
    df = pd.read_csv(csv_path)
    
    print(f"\n✓ 讀取 {len(df)} 條記錄")
    print(f"✓ 欄位: {list(df.columns)}\n")
    
    # 檢查必要欄位
    required_cols = ['Open', 'Close', 'Price_Change_%']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"❌ 缺少必要欄位: {missing}")
        return
    
    # 取前10個案例進行驗證
    sample_size = min(10, len(df))
    print(f"驗證前 {sample_size} 個案例：\n")
    
    matches_open_to_close = 0
    matches_close_to_close = 0
    
    for i in range(sample_size):
        row = df.iloc[i]
        csv_value = row['Price_Change_%']
        open_price = row['Open']
        close_price = row['Close']
        
        # 計算 OPEN_TO_CLOSE
        calc_open_to_close = ((close_price - open_price) / open_price) * 100
        
        # 計算 CLOSE_TO_CLOSE（需要前一根的收盤價）
        if i > 0:
            prev_close = df.iloc[i-1]['Close']
            calc_close_to_close = ((close_price - prev_close) / prev_close) * 100
        else:
            calc_close_to_close = np.nan
        
        # 比對差異
        diff_open_to_close = abs(csv_value - calc_open_to_close)
        diff_close_to_close = abs(csv_value - calc_close_to_close) if not np.isnan(calc_close_to_close) else 999
        
        # 判斷使用哪種方式（容許 0.01% 的誤差）
        if diff_open_to_close < 0.01:
            method = "OPEN_TO_CLOSE ✓"
            matches_open_to_close += 1
        elif diff_close_to_close < 0.01:
            method = "CLOSE_TO_CLOSE ✓"
            matches_close_to_close += 1
        else:
            method = "UNKNOWN ⚠️"
        
        print(f"案例 {i+1}:")
        print(f"  CSV Price_Change_%:     {csv_value:8.2f}%")
        print(f"  OPEN_TO_CLOSE 計算:     {calc_open_to_close:8.2f}% (差異: {diff_open_to_close:.4f})")
        if not np.isnan(calc_close_to_close):
            print(f"  CLOSE_TO_CLOSE 計算:    {calc_close_to_close:8.2f}% (差異: {diff_close_to_close:.4f})")
        else:
            print(f"  CLOSE_TO_CLOSE 計算:    N/A (第一根K線)")
        print(f"  判斷使用方式: {method}")
        print()
    
    # 統計結果
    print("=" * 70)
    print("統計結果:")
    print("=" * 70)
    print(f"符合 OPEN_TO_CLOSE:   {matches_open_to_close}/{sample_size}")
    print(f"符合 CLOSE_TO_CLOSE:  {matches_close_to_close}/{sample_size}")
    print()
    
    if matches_open_to_close > matches_close_to_close:
        print("✅ 結論: CSV 使用 OPEN_TO_CLOSE 計算方式")
        print("   (當根收盤價 - 當根開盤價) / 當根開盤價")
    elif matches_close_to_close > matches_open_to_close:
        print("✅ 結論: CSV 使用 CLOSE_TO_CLOSE 計算方式")
        print("   (當根收盤價 - 前根收盤價) / 前根收盤價")
    else:
        print("⚠️ 結論: 無法確定使用的計算方式")
    print("=" * 70)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python verify_price_change_csv.py <CSV文件路徑>")
        print("\n範例:")
        print("  python verify_price_change_csv.py case_search_results_2026-01-27.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    verify_price_change_method(csv_path)
