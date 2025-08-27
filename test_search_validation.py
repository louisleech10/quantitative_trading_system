#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Case Search2 參數驗證測試檔案
用於驗證搜索參數和計算結果的準確性

使用方法：
1. 修改下方的 USER_CONFIG 區域中的參數
2. 運行腳本：python test_search_validation.py
3. 檢查輸出的 CSV 檔案和控制台報告
"""

import sys
import os
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path

# 添加項目路徑 - 參照現有檔案的路徑設定方式
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # 回到 quantitative_trading_system 根目錄
sys.path.append(parent_dir)

# 導入必要模組 - 使用與現有檔案相同的import方式
from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader
from momentum.DataExtraction.case_search_engine import SearchConfiguration, FilterCondition

# ===== 使用者可修改區域 START =====

# 基本搜索參數 - 您可以直接修改這些值
USER_CONFIG = {
    # 時間設定
    'start_date': '2024-02-01',    # 開始日期 (YYYY-MM-DD)
    'end_date': '2025-05-31',      # 結束日期 (YYYY-MM-DD)
    'timeframe': '1d',             # 時間週期: '1h', '4h', '12h', '1d'
    
    # K線參數
    'lookback_periods': 20,        # 回溯K線數量
    'forward_periods': 10,         # 向前看K線數量
    
    # 採樣參數
    'sample_limit': 100,           # 樣本數量限制
    'min_volume': 1000,            # 最小成交量 (USDT)
    'exclude_new_listing_days': 7, # 排除新上市後天數
    
    # 篩選條件參數
    'price_change_threshold': 0.03,  # 價格變化閾值 (3% = 0.03)
    
    # 交易對設定
    'symbols': ['BTCUSDT'],        # 要搜索的交易對列表
    
    # 批次處理
    'batch_size': 20,              # 每批處理的交易對數量
}

# ===== 使用者可修改區域 END =====

# 設置日誌格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_search_configuration():
    """根據用戶配置創建搜索配置"""
    
    # 創建搜索配置
    config = SearchConfiguration(
        name="Parameter_Validation_Test",
        description="參數驗證測試搜索",
        timeframe=USER_CONFIG['timeframe'],
        lookback_periods=USER_CONFIG['lookback_periods'],
        forward_periods=USER_CONFIG['forward_periods'],
        time_range=(USER_CONFIG['start_date'], USER_CONFIG['end_date']),
        sample_limit=USER_CONFIG['sample_limit'],
        min_volume=USER_CONFIG['min_volume'],
        exclude_new_listing_days=USER_CONFIG['exclude_new_listing_days']
    )
    
    # 手動添加 time_range 屬性以確保兼容性（參照 API 服務的做法）
    config.time_range = (USER_CONFIG['start_date'], USER_CONFIG['end_date'])
    
    # 添加價格變化條件
    price_condition = FilterCondition(
        condition_type="price",
        parameter="price_change",
        operator=">=",
        value=USER_CONFIG['price_change_threshold'],
        description=f"價格漲幅大於{USER_CONFIG['price_change_threshold']*100}%"
    )
    config.add_initial_condition(price_condition)
    
    # 添加成交量條件
    if USER_CONFIG['min_volume'] > 0:
        volume_condition = FilterCondition(
            condition_type="volume",
            parameter="volume",
            operator=">=",
            value=USER_CONFIG['min_volume'],
            description=f"成交量大於{USER_CONFIG['min_volume']} USDT"
        )
        config.add_initial_condition(volume_condition)
    
    return config
    if USER_CONFIG['min_volume'] > 0:
        volume_condition = FilterCondition(
            condition_type="volume",
            parameter="volume",
            operator=">=",
            value=USER_CONFIG['min_volume'],
            description=f"成交量大於{USER_CONFIG['min_volume']} USDT"
        )
        config.add_initial_condition(volume_condition)
    
    return config

def print_configuration_summary():
    """打印配置摘要"""
    print("\n" + "="*60)
    print("📋 搜索配置摘要")
    print("="*60)
    print(f"🕐 時間範圍: {USER_CONFIG['start_date']} 到 {USER_CONFIG['end_date']}")
    print(f"📊 時間週期: {USER_CONFIG['timeframe']}")
    print(f"📈 交易對: {', '.join(USER_CONFIG['symbols'])}")
    print(f"🎯 價格變化閾值: {USER_CONFIG['price_change_threshold']*100}%")
    print(f"💰 最小成交量: {USER_CONFIG['min_volume']:,} USDT")
    print(f"📊 樣本限制: {USER_CONFIG['sample_limit']:,}")
    print(f"⏮️  回溯K線: {USER_CONFIG['lookback_periods']}")
    print(f"⏭️  向前K線: {USER_CONFIG['forward_periods']}")
    print("="*60)

def validate_configuration():
    """驗證配置的合理性"""
    errors = []
    warnings = []
    
    # 檢查日期格式和範圍
    try:
        start = datetime.strptime(USER_CONFIG['start_date'], '%Y-%m-%d')
        end = datetime.strptime(USER_CONFIG['end_date'], '%Y-%m-%d')
        if start >= end:
            errors.append("開始日期必須早於結束日期")
        if (end - start).days < 7:
            warnings.append("時間範圍少於7天，可能找不到足夠的案例")
    except ValueError:
        errors.append("日期格式錯誤，請使用 YYYY-MM-DD 格式")
    
    # 檢查參數範圍
    if USER_CONFIG['price_change_threshold'] < 0:
        warnings.append("價格變化閾值為負數，將尋找下跌案例")
    if USER_CONFIG['price_change_threshold'] > 0.5:
        warnings.append("價格變化閾值超過50%，可能很難找到案例")
    
    if USER_CONFIG['sample_limit'] > 10000:
        warnings.append("樣本限制很大，搜索可能需要很長時間")
    
    if USER_CONFIG['timeframe'] not in ['1h', '4h', '12h', '1d']:
        errors.append("不支持的時間週期，請使用: 1h, 4h, 12h, 1d")
    
    # 打印驗證結果
    if errors:
        print("\n❌ 配置錯誤:")
        for error in errors:
            print(f"   • {error}")
        return False
    
    if warnings:
        print("\n⚠️  配置警告:")
        for warning in warnings:
            print(f"   • {warning}")
    
    return True

def save_results_to_csv(cases, config):
    """保存結果到CSV檔案"""
    if not cases:
        logger.warning("沒有找到任何案例，無法保存CSV")
        return None
    
    # 創建結果目錄
    results_dir = Path("test_results")
    results_dir.mkdir(exist_ok=True)
    
    # 生成檔案名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f"case_search_validation_{timestamp}.csv"
    csv_path = results_dir / csv_filename
    
    try:
        # 轉換為DataFrame
        df = pd.DataFrame(cases)
        
        # 保存到CSV
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        logger.info(f"✅ 結果已保存到: {csv_path}")
        print(f"\n📄 結果檔案: {csv_path}")
        
        return csv_path
        
    except Exception as e:
        logger.error(f"保存CSV時出錯: {str(e)}")
        return None

def analyze_results(cases):
    """分析搜索結果"""
    if not cases:
        print("\n❌ 沒有找到任何案例進行分析")
        return
    
    print("\n" + "="*60)
    print("📊 結果分析報告")
    print("="*60)
    
    # 基本統計
    print(f"✅ 找到案例總數: {len(cases)}")
    
    # 按交易對統計
    if cases:
        symbols = {}
        for case in cases:
            symbol = case.get('symbol', 'Unknown')
            symbols[symbol] = symbols.get(symbol, 0) + 1
        
        print(f"📈 交易對分布:")
        for symbol, count in symbols.items():
            print(f"   • {symbol}: {count} 個案例")
    
    # 時間分布分析
    try:
        timestamps = [case.get('timestamp') for case in cases if case.get('timestamp')]
        if timestamps:
            timestamps.sort()
            print(f"⏰ 時間範圍: {timestamps[0]} 到 {timestamps[-1]}")
    except:
        pass
    
    # 參數統計 (如果案例包含這些資訊)
    try:
        if cases and 'price_change' in cases[0]:
            price_changes = [case.get('price_change', 0) for case in cases if case.get('price_change') is not None]
            if price_changes:
                avg_change = sum(price_changes) / len(price_changes)
                print(f"💹 平均價格變化: {avg_change*100:.2f}%")
                print(f"📊 最大價格變化: {max(price_changes)*100:.2f}%")
    except:
        pass
    
    print("="*60)

async def main():
    """主函數"""
    try:
        print("\n🚀 Case Search 參數驗證測試開始...")
        
        # 打印配置摘要
        print_configuration_summary()
        
        # 驗證配置
        if not validate_configuration():
            print("\n❌ 配置驗證失敗，請修正錯誤後重試")
            return
        
        print("\n✅ 配置驗證通過")
        
        # 初始化數據加載器
        print("\n📡 初始化數據加載器...")
        data_loader = MomentumDataLoader()
        
        # 創建搜索配置
        config = create_search_configuration()
        
        # 執行搜索
        print(f"\n🔍 開始搜索案例...")
        print(f"   交易對: {USER_CONFIG['symbols']}")
        print(f"   批次大小: {USER_CONFIG['batch_size']}")
        
        cases = await data_loader.search_engine.search_cases(
            config=config,
            symbols=USER_CONFIG['symbols'],
            batch_size=USER_CONFIG['batch_size'],
            save_results=False  # 我們會手動保存CSV
        )
        
        # 分析結果
        analyze_results(cases)
        
        # 保存結果
        if cases:
            csv_path = save_results_to_csv(cases, config)
            if csv_path:
                print(f"\n🎉 測試完成！請檢查 CSV 檔案: {csv_path}")
                
                # 打印CSV檢查提醒
                print("\n📋 CSV 檔案檢查清單:")
                print("   ✅ 確認時間範圍是否正確")
                print("   ✅ 檢查所有20個參數是否存在")
                print("   ✅ 驗證計算值是否合理")
                print("   ✅ 確認案例數量符合預期")
        else:
            print("\n⚠️  沒有找到符合條件的案例")
            print("   建議：")
            print("   • 放寬價格變化閾值")
            print("   • 擴大時間範圍")
            print("   • 降低最小成交量要求")
            print("   • 嘗試不同的交易對")
        
    except Exception as e:
        logger.error(f"執行過程中出錯: {str(e)}", exc_info=True)
        print(f"\n❌ 錯誤: {str(e)}")
        print("請檢查錯誤訊息並修正配置")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())