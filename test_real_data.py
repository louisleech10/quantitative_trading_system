#!/usr/bin/env python3
"""
測試真實數據格式腳本
用 BTCUSDT 抓取小段時間的數據，查看實際格式
"""

import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "momentum" / "DataExtraction"))

# 設置環境變數路徑
os.environ.setdefault('PYTHONPATH', str(project_root))

def test_data_loader():
    """測試數據加載器"""
    print("🔄 開始測試 DataLoader...")
    
    try:
        # 導入必要模組
        from momentum.DataExtraction.data_loader_momentum import DataLoader
        from api.core.config import settings
        
        # 獲取 API 憑證
        api_key, secret_key = settings.get_binance_credentials()
        
        if not api_key or not secret_key:
            print("❌ 錯誤：未找到 Binance API 憑證")
            print("請確認 .env 檔案中有設定 BINANCE_API_KEY 和 BINANCE_SECRET_KEY")
            return None
            
        print(f"✅ API 憑證已讀取 (Key: {api_key[:8]}...)")
        
        # 初始化 DataLoader
        data_loader = DataLoader(
            cache_dir=str(settings.data_cache_path),
            api_key=api_key,
            api_secret=secret_key
        )
        
        print("✅ DataLoader 初始化成功")
        
        # 測試獲取小段數據
        symbol = "BTCUSDT"
        end_time = datetime.now()
        start_time = end_time - timedelta(days=3)  # 只抓3天數據
        
        print(f"📊 正在獲取 {symbol} 數據...")
        print(f"   時間範圍: {start_time.strftime('%Y-%m-%d')} 到 {end_time.strftime('%Y-%m-%d')}")
        
        # 獲取4小時K線數據
        data = data_loader.get_historical_data(
            symbol=symbol,
            start_time=start_time.strftime('%Y-%m-%d'),
            end_time=end_time.strftime('%Y-%m-%d'),
            interval='4h'
        )
        
        if data.empty:
            print("❌ 沒有獲取到數據")
            return None
            
        print(f"✅ 成功獲取 {len(data)} 根K線數據")
        print(f"📋 數據欄位: {list(data.columns)}")
        print(f"📅 時間範圍: {data.index[0]} 到 {data.index[-1]}")
        
        # 顯示前幾筆數據
        print(f"\n📊 前3筆數據預覽:")
        print(data.head(3).to_string())
        
        return data_loader, data
        
    except ImportError as e:
        print(f"❌ 導入錯誤: {str(e)}")
        print("請確認 momentum 模組路徑正確")
        return None
        
    except Exception as e:
        print(f"❌ 測試 DataLoader 時出錯: {str(e)}")
        return None

def test_search_engine(data_loader, sample_data):
    """測試搜索引擎"""
    print("\n🔍 開始測試 CaseSearchEngine...")
    
    try:
        from momentum.DataExtraction.case_search_engine import (
            CaseSearchEngine, SearchConfiguration, FilterCondition
        )
        
        # 初始化搜索引擎
        search_engine = CaseSearchEngine(data_loader)
        print("✅ CaseSearchEngine 初始化成功")
        
        # 創建簡單的搜索配置
        config = SearchConfiguration(
            name="BTC_Test_Search",
            timeframe='4h',
            lookback_periods=20,  # 減少回溯期間
            forward_periods=10,   # 減少前瞻期間
            sample_limit=5,       # 只要5個案例
            min_volume=1000       # 最小成交量
        )
        
        # 添加價格變化條件（5%以上漲幅）
        price_condition = FilterCondition(
            condition_type='initial',
            parameter='price_change',
            operator='>=',
            value=0.05,  # 5%
            description='價格漲幅大於5%'
        )
        config.add_initial_condition(price_condition)
        
        print(f"📋 搜索配置: {config.name}")
        print(f"   條件: 價格漲幅 >= 5%")
        print(f"   樣本限制: {config.sample_limit}")
        
        # 執行搜索（只搜索 BTCUSDT）
        print(f"🔍 正在搜索 BTCUSDT 案例...")
        
        # 使用正確的方法名稱並提供 symbols 參數
        import asyncio
        results = asyncio.run(search_engine.search_cases(
            config=config,
            symbols=["BTCUSDT"],  # 只搜索 BTCUSDT
            batch_size=1,         # 小批次
            save_results=False    # 不保存結果
        ))
        
        if not results:
            print("❌ 沒有找到符合條件的案例")
            return None
            
        print(f"✅ 找到 {len(results)} 個案例")
        
        # 顯示第一個案例的完整格式
        if results:
            first_case = results[0]
            print(f"\n📊 第一個案例的完整數據格式:")
            print(json.dumps(first_case, indent=2, default=str, ensure_ascii=False))
            
        return results
        
    except Exception as e:
        print(f"❌ 測試 CaseSearchEngine 時出錯: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """主函數"""
    print("🚀 開始測試真實數據格式...\n")
    
    # 測試數據加載器
    result = test_data_loader()
    if result is None:
        print("❌ DataLoader 測試失敗，停止測試")
        return
        
    data_loader, sample_data = result
    
    # 測試搜索引擎
    search_results = test_search_engine(data_loader, sample_data)
    
    if search_results:
        print(f"\n🎉 測試完成！")
        print(f"✅ 成功獲取真實數據格式")
        print(f"📁 詳細格式請查看上方的 JSON 輸出")
        
        # 保存結果到檔案
        output_file = project_root / "test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(search_results, f, indent=2, default=str, ensure_ascii=False)
        print(f"💾 結果已保存到: {output_file}")
        
    else:
        print(f"\n❌ 測試失敗，無法獲取真實數據格式")

if __name__ == "__main__":
    main()