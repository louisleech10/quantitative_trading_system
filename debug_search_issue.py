#!/usr/bin/env python3
"""
Debug Case Search Engine 搜索結果為 0 的問題
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# 添加項目路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def debug_data_loader():
    """測試數據加載器並檢查 OHLC 數據"""
    print("🔍 Debug 1: 檢查數據加載器...")
    
    try:
        from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumStrategyDataLoader
        
        # 初始化數據加載器
        data_loader = MomentumStrategyDataLoader()
        print("✅ DataLoader 初始化成功")
        
        # 測試獲取 BTCUSDT 數據（最近7天）
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        print(f"📅 獲取時間範圍: {start_time} 到 {end_time}")
        
        data = data_loader.get_historical_data(
            symbol="BTCUSDT",
            start_time=start_time,
            end_time=end_time,
            interval="4h"
        )
        
        if data.empty:
            print("❌ 沒有獲取到數據")
            return None
            
        print(f"✅ 成功獲取 {len(data)} 根K線數據")
        print(f"📋 數據欄位: {list(data.columns)}")
        
        # 檢查 OHLC 欄位
        expected_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in expected_cols if col not in data.columns]
        
        if missing_cols:
            print(f"⚠️  缺少的 OHLC 欄位: {missing_cols}")
        else:
            print("✅ OHLC 數據完整")
        
        # 顯示前幾筆數據
        print(f"\n📊 前3筆數據預覽:")
        print(data.head(3).to_string())
        
        # 檢查數據質量
        print(f"\n📈 數據質量檢查:")
        print(f"   • 空值數量: {data.isnull().sum().sum()}")
        print(f"   • 重複索引: {data.index.duplicated().sum()}")
        
        # 計算價格變化
        if 'close' in data.columns:
            data['price_change'] = data['close'].pct_change()
            max_change = data['price_change'].max()
            min_change = data['price_change'].min()
            print(f"   • 最大價格變化: {max_change:.4f} ({max_change*100:.2f}%)")
            print(f"   • 最小價格變化: {min_change:.4f} ({min_change*100:.2f}%)")
            
            # 檢查有多少K線滿足3%漲幅條件
            high_change_count = (data['price_change'] >= 0.03).sum()
            print(f"   • 滿足3%漲幅的K線數: {high_change_count}")
            
            if high_change_count > 0:
                print(f"   • 最高漲幅的時間點:")
                top_changes = data.nlargest(3, 'price_change')[['close', 'price_change']]
                print(top_changes.to_string())
        
        return data_loader, data
        
    except Exception as e:
        print(f"❌ Debug DataLoader 時出錯: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def debug_search_engine(data_loader, sample_data):
    """測試搜索引擎，使用更寬鬆的條件"""
    print("\n🔍 Debug 2: 檢查搜索引擎...")
    
    try:
        from momentum.DataExtraction.case_search_engine import (
            CaseSearchEngine, SearchConfiguration, FilterCondition
        )
        
        # 初始化搜索引擎
        search_engine = CaseSearchEngine(data_loader)
        print("✅ CaseSearchEngine 初始化成功")
        
        # 創建寬鬆的搜索配置
        config = SearchConfiguration(
            name="Debug_Search",
            timeframe='4h',
            lookback_periods=10,   # 減少回溯期間
            forward_periods=5,     # 減少前瞻期間
            sample_limit=10,       # 只要10個案例
            min_volume=0           # 取消最小成交量限制
        )
        
        # 添加寬鬆的價格變化條件（1%以上漲幅）
        price_condition = FilterCondition(
            condition_type='initial',
            parameter='price_change',
            operator='>=',
            value=0.01,  # 1%
            description='價格漲幅大於1%'
        )
        config.add_initial_condition(price_condition)
        
        print(f"📋 搜索配置: {config.name}")
        print(f"   條件: 價格漲幅 >= 1%")
        print(f"   樣本限制: {config.sample_limit}")
        
        # 執行搜索（只搜索 BTCUSDT）
        print(f"🔍 正在搜索 BTCUSDT 案例...")
        
        import asyncio
        results = asyncio.run(search_engine.search_cases(
            config=config,
            symbols=["BTCUSDT"],
            batch_size=1,
            save_results=False
        ))
        
        if not results:
            print("❌ 仍然沒有找到符合條件的案例")
            
            # 嘗試更寬鬆的條件
            print("\n🔍 嘗試更寬鬆的搜索條件...")
            
            # 移除所有條件，只搜索原始數據
            simple_config = SearchConfiguration(
                name="Ultra_Simple_Search",
                timeframe='4h',
                lookback_periods=5,
                forward_periods=3,
                sample_limit=5,
                min_volume=0
            )
            
            results = asyncio.run(search_engine.search_cases(
                config=simple_config,
                symbols=["BTCUSDT"],
                batch_size=1,
                save_results=False
            ))
            
            if results:
                print(f"✅ 使用簡單配置找到 {len(results)} 個案例")
            else:
                print("❌ 即使使用最簡單的配置也沒有找到案例")
                return None
        else:
            print(f"✅ 找到 {len(results)} 個案例")
        
        # 顯示第一個案例的完整格式
        if results:
            first_case = results[0]
            print(f"\n📊 第一個案例的完整數據格式:")
            print(json.dumps(first_case, indent=2, default=str, ensure_ascii=False))
            
            # 檢查數據完整性
            print(f"\n🔍 數據完整性檢查:")
            required_fields = ['symbol', 'timestamp', 'close', 'volume', 'price_change']
            for field in required_fields:
                if field in first_case:
                    print(f"   ✅ {field}: {first_case[field]}")
                else:
                    print(f"   ❌ 缺少: {field}")
        
        return results
        
    except Exception as e:
        print(f"❌ Debug CaseSearchEngine 時出錯: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def debug_api_integration():
    """測試 API 整合狀況"""
    print("\n🔍 Debug 3: 檢查 API 整合...")
    
    try:
        from api.services.standalone_search_service import StandaloneSearchService
        
        # 初始化服務
        service = StandaloneSearchService()
        print("✅ StandaloneSearchService 初始化成功")
        
        # 檢查 momentum 模組是否可用
        if hasattr(service, 'momentum_available'):
            print(f"   • Momentum 模組可用: {service.momentum_available}")
        
        if hasattr(service, 'data_loader'):
            print(f"   • DataLoader 可用: {service.data_loader is not None}")
        
        if hasattr(service, 'search_engine'):
            print(f"   • SearchEngine 可用: {service.search_engine is not None}")
        
        return service
        
    except Exception as e:
        print(f"❌ Debug API 整合時出錯: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """主函數"""
    print("🚀 開始 Debug Case Search 問題...\n")
    
    # Debug 1: 數據加載器
    result = debug_data_loader()
    if result is None:
        print("\n❌ DataLoader 測試失敗，停止測試")
        return
        
    data_loader, sample_data = result
    
    # Debug 2: 搜索引擎
    search_results = debug_search_engine(data_loader, sample_data)
    
    # Debug 3: API 整合
    api_service = debug_api_integration()
    
    print(f"\n🎯 Debug 總結:")
    print(f"   • DataLoader: {'✅ 正常' if result else '❌ 異常'}")
    print(f"   • SearchEngine: {'✅ 正常' if search_results else '❌ 異常'}")
    print(f"   • API Service: {'✅ 正常' if api_service else '❌ 異常'}")
    
    if search_results:
        print(f"\n💡 建議:")
        print(f"   • 搜索引擎功能正常，可能是前端發送的搜索條件過於嚴格")
        print(f"   • 建議檢查前端界面的默認參數設置")
        print(f"   • 可以從更寬鬆的條件開始測試")
    else:
        print(f"\n⚠️  需要進一步調查:")
        print(f"   • 搜索引擎無法找到符合條件的案例")
        print(f"   • 可能是數據處理邏輯有問題")
        print(f"   • 或者是搜索條件評估邏輯有錯誤")

if __name__ == "__main__":
    main()