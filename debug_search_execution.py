#!/usr/bin/env python3
"""
搜索執行錯誤的調試腳本
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# 添加項目路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_search_engine_directly():
    """直接測試搜索引擎"""
    print("🔍 直接測試搜索引擎...")
    
    try:
        from momentum.DataExtraction.case_search_engine import CaseSearchEngine, SearchConfiguration, FilterCondition
        from momentum.DataExtraction.data_loader_momentum import DataLoader
        from api.core.config import settings
        
        # 獲取API憑證
        api_key, secret_key = settings.get_binance_credentials()
        
        # 初始化數據加載器
        data_loader = DataLoader(
            cache_dir=str(settings.data_cache_path),
            api_key=api_key,
            api_secret=secret_key
        )
        
        # 初始化搜索引擎
        search_engine = CaseSearchEngine(data_loader)
        
        # 創建簡單的搜索配置
        config = SearchConfiguration(
            name="Direct_Test_Search",
            timeframe='4h',
            lookback_periods=10,
            forward_periods=5,
            sample_limit=5,
            min_volume=0,
            time_range=("2023-01-01", "2023-12-31")
        )
        
        # 添加簡單條件
        condition = FilterCondition(
            condition_type='initial',
            parameter='price_change',
            operator='>=',
            value=0.01,  # 1%
            description='價格漲幅大於1%'
        )
        config.add_initial_condition(condition)
        
        print(f"執行搜索配置: {config.name}")
        
        # 執行搜索
        results = await search_engine.search_cases(
            config=config,
            symbols=["BTCUSDT"],
            batch_size=1,
            save_results=False
        )
        
        print(f"搜索結果類型: {type(results)}")
        print(f"搜索結果: {results}")
        
        if results is None:
            print("❌ 搜索引擎返回 None")
            return None
        elif len(results) == 0:
            print("⚠️ 搜索引擎返回空列表")
            return []
        else:
            print(f"✅ 搜索引擎返回 {len(results)} 個結果")
            print(f"第一個結果示例:")
            print(json.dumps(results[0], indent=2, default=str, ensure_ascii=False))
            return results
            
    except Exception as e:
        print(f"❌ 直接測試搜索引擎失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def test_api_service():
    """測試API服務"""
    print("\n🔍 測試API服務...")
    
    try:
        from api.services.standalone_search_service import StandaloneSearchService
        from api.models.requests import SearchConfigRequest, FilterConditionRequest, TimeframeEnum, OperatorEnum, ConditionTypeEnum
        from datetime import date
        
        # 初始化服務
        service = StandaloneSearchService()
        
        # 創建搜索請求
        condition = FilterConditionRequest(
            condition_type=ConditionTypeEnum.PRICE,
            parameter="price_change",
            operator=OperatorEnum.GREATER_EQUAL,
            value=0.03,
            description="價格漲幅大於3%"
        )
        
        request = SearchConfigRequest(
            name="API_Test_Search",
            timeframe=TimeframeEnum.HOUR_4,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            lookback_periods=10,
            forward_periods=5,
            sample_limit=5,
            min_volume=1000,
            exclude_new_listing_days=7,
            initial_conditions=[condition],
            advanced_conditions=[]
        )
        
        print(f"執行API搜索: {request.name}")
        
        # 執行搜索
        task_id = await service.execute_search(request, symbols=["BTCUSDT"])
        
        print(f"任務ID: {task_id}")
        
        # 等待搜索完成
        max_wait = 30  # 最多等30秒
        wait_time = 0
        
        while wait_time < max_wait:
            await asyncio.sleep(1)
            wait_time += 1
            
            task_info = service.get_task_status(task_id)
            if task_info is None:
                print(f"❌ 無法獲取任務狀態")
                break
                
            print(f"任務狀態: {task_info.status}")
            
            if task_info.status == "completed":
                # 獲取結果
                result = service.get_task_result(task_id)
                if result:
                    print(f"✅ API搜索完成，找到 {len(result.cases)} 個案例")
                    if len(result.cases) > 0:
                        print(f"第一個案例示例:")
                        case = result.cases[0]
                        print(f"  Symbol: {case.symbol}")
                        print(f"  Timestamp: {case.timestamp}")
                        print(f"  Open: {case.open}")
                        print(f"  High: {case.high}")
                        print(f"  Low: {case.low}")
                        print(f"  Close: {case.close}")
                    return result
                else:
                    print(f"❌ 無法獲取搜索結果")
                    break
            elif task_info.status == "failed":
                print(f"❌ 搜索失敗: {task_info.error_message}")
                break
        
        if wait_time >= max_wait:
            print(f"⏰ 搜索超時")
        
        return None
        
    except Exception as e:
        print(f"❌ 測試API服務失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def test_frontend_api_call():
    """模擬前端API調用"""
    print("\n🔍 模擬前端API調用...")
    
    try:
        import aiohttp
        
        # 創建前端風格的請求
        request_data = {
            "config": {
                "name": "Frontend_Test_Search",
                "description": "測試前端調用",
                "timeframe": "4h",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "lookback_periods": 20,
                "forward_periods": 10,
                "sample_limit": 10,
                "min_volume": 1000,
                "exclude_new_listing_days": 7,
                "initial_conditions": [{
                    "condition_type": "price",
                    "parameter": "price_change",
                    "operator": ">=",
                    "value": 0.03,
                    "description": "價格漲幅大於3%"
                }],
                "advanced_conditions": []
            },
            "symbols": ["BTCUSDT"],
            "save_results": False
        }
        
        # 發送請求
        async with aiohttp.ClientSession() as session:
            print("發送搜索請求...")
            async with session.post(
                'http://localhost:8000/api/v1/search/execute',
                json=request_data,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ 請求失敗: {response.status} - {error_text}")
                    return None
                
                execute_data = await response.json()
                print(f"搜索請求成功，任務ID: {execute_data['data']['task_id']}")
                
                task_id = execute_data['data']['task_id']
                
                # 輪詢結果
                max_wait = 30
                wait_time = 0
                
                while wait_time < max_wait:
                    await asyncio.sleep(2)
                    wait_time += 2
                    
                    # 檢查任務狀態
                    async with session.get(
                        f'http://localhost:8000/api/v1/search/task/{task_id}'
                    ) as status_response:
                        
                        if status_response.status != 200:
                            print(f"❌ 獲取狀態失敗: {status_response.status}")
                            break
                            
                        status_data = await status_response.json()
                        task_status = status_data['data']['status']
                        print(f"任務狀態: {task_status}")
                        
                        if task_status == "completed":
                            # 獲取結果
                            async with session.get(
                                f'http://localhost:8000/api/v1/search/task/{task_id}/result'
                            ) as result_response:
                                
                                if result_response.status != 200:
                                    error_text = await result_response.text()
                                    print(f"❌ 獲取結果失敗: {result_response.status} - {error_text}")
                                    break
                                    
                                result_data = await result_response.json()
                                
                                if result_data['success']:
                                    cases = result_data['data']['cases']
                                    print(f"✅ 前端API調用成功，找到 {len(cases)} 個案例")
                                    
                                    if len(cases) > 0:
                                        case = cases[0]
                                        print(f"第一個案例:")
                                        print(f"  Symbol: {case['symbol']}")
                                        print(f"  Timestamp: {case['timestamp']}")
                                        print(f"  Open: {case.get('open', 'N/A')}")
                                        print(f"  High: {case.get('high', 'N/A')}")
                                        print(f"  Low: {case.get('low', 'N/A')}")
                                        print(f"  Close: {case['close']}")
                                        print(f"  Future 24h Return: {case.get('future24_close_return', 'N/A')}")
                                        print(f"  Future 48h Return: {case.get('future48_close_return', 'N/A')}")
                                        
                                    return result_data['data']
                                else:
                                    print(f"❌ API返回失敗: {result_data.get('error', {}).get('message', 'Unknown error')}")
                                    break
                                    
                        elif task_status == "failed":
                            error_msg = status_data['data'].get('error_message', 'Unknown error')
                            print(f"❌ 搜索任務失敗: {error_msg}")
                            break
                
                if wait_time >= max_wait:
                    print(f"⏰ 前端API調用超時")
                
        return None
        
    except Exception as e:
        print(f"❌ 模擬前端API調用失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """主測試函數"""
    print("🚀 開始全面診斷搜索執行錯誤...\n")
    
    # 測試1: 直接測試搜索引擎
    print("=" * 60)
    engine_result = await test_search_engine_directly()
    
    # 測試2: 測試API服務
    print("=" * 60)
    api_result = await test_api_service()
    
    # 測試3: 模擬前端API調用
    print("=" * 60)
    frontend_result = await test_frontend_api_call()
    
    # 總結
    print("\n" + "=" * 60)
    print("🎯 診斷總結:")
    print(f"   • 搜索引擎直接測試: {'✅ 正常' if engine_result is not None else '❌ 異常'}")
    print(f"   • API服務測試: {'✅ 正常' if api_result is not None else '❌ 異常'}")
    print(f"   • 前端API調用測試: {'✅ 正常' if frontend_result is not None else '❌ 異常'}")
    
    if engine_result is None:
        print("\n🔧 建議修復步驟:")
        print("   1. 檢查數據加載器配置")
        print("   2. 檢查搜索條件是否過於嚴格")
        print("   3. 檢查時間範圍是否有數據")
        print("   4. 檢查API憑證是否正確")
    
    if api_result is None and engine_result is not None:
        print("\n🔧 API服務問題:")
        print("   1. 檢查請求轉換邏輯")
        print("   2. 檢查數據格式轉換")
        print("   3. 檢查異常處理")
    
    if frontend_result is None and api_result is not None:
        print("\n🔧 前端API調用問題:")
        print("   1. 檢查請求格式")
        print("   2. 檢查API端點URL")
        print("   3. 檢查CORS設置")

if __name__ == "__main__":
    asyncio.run(main())