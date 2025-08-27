#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正搜索引擎的數據加載調用問題
這是一個臨時補丁，修正 case_search_engine.py 中的 tuple 參數問題
"""

import sys
import os
from pathlib import Path

# 添加項目路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

def fix_search_engine():
    """修正搜索引擎檔案中的參數傳遞問題"""
    
    # 搜索引擎檔案路徑
    search_engine_path = Path(__file__).parent / "momentum" / "DataExtraction" / "case_search_engine.py"
    
    if not search_engine_path.exists():
        print(f"❌ 找不到搜索引擎檔案: {search_engine_path}")
        return False
    
    try:
        # 讀取原始檔案
        with open(search_engine_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 備份原始檔案
        backup_path = search_engine_path.with_suffix('.py.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 已備份原始檔案到: {backup_path}")
        
        # 查找需要修正的代碼段
        old_code = '''            data = self.data_loader.get_historical_data(
                symbol=symbol,
                start_time=config.time_range,
                end_time=config.time_range,
                interval=config.timeframe
            )'''
        
        new_code = '''            # 修正：正確傳遞時間範圍參數
            if hasattr(config, 'time_range') and config.time_range:
                start_time, end_time = config.time_range
            else:
                start_time, end_time = config.start_time, config.end_time
                
            data = self.data_loader.get_historical_data(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                interval=config.timeframe
            )'''
        
        # 執行替換
        if old_code in content:
            new_content = content.replace(old_code, new_code)
            
            # 寫入修正後的檔案
            with open(search_engine_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("✅ 已成功修正搜索引擎檔案")
            print("📝 修正內容:")
            print("   - 修正了 time_range tuple 參數問題")
            print("   - 正確分離開始時間和結束時間")
            return True
        else:
            print("⚠️  未找到需要修正的代碼段")
            print("   可能檔案已經被修正過，或者代碼結構已改變")
            return False
            
    except Exception as e:
        print(f"❌ 修正檔案時出錯: {str(e)}")
        return False

def restore_search_engine():
    """恢復搜索引擎檔案的原始版本"""
    
    search_engine_path = Path(__file__).parent / "momentum" / "DataExtraction" / "case_search_engine.py"
    backup_path = search_engine_path.with_suffix('.py.backup')
    
    if not backup_path.exists():
        print("❌ 找不到備份檔案")
        return False
    
    try:
        # 從備份恢復
        with open(backup_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open(search_engine_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已恢復搜索引擎檔案到原始版本")
        return True
        
    except Exception as e:
        print(f"❌ 恢復檔案時出錯: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="修正或恢復搜索引擎檔案")
    parser.add_argument('action', choices=['fix', 'restore'], 
                       help="執行動作: fix=修正問題, restore=恢復原始版本")
    
    args = parser.parse_args()
    
    if args.action == 'fix':
        print("🔧 開始修正搜索引擎檔案...")
        success = fix_search_engine()
        if success:
            print("\n🎉 修正完成！現在可以重新運行 test_search_validation.py")
        else:
            print("\n❌ 修正失敗，請檢查錯誤訊息")
    
    elif args.action == 'restore':
        print("↩️  恢復搜索引擎檔案...")
        success = restore_search_engine()
        if success:
            print("\n✅ 恢復完成")
        else:
            print("\n❌ 恢復失敗")