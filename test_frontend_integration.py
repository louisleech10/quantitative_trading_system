"""
前端整合測試腳本 - Phase 3-6 Frontend Integration

測試項目:
1. Trial Comparison API (/api/v1/optimization/trials/compare)
2. ML Pipeline Creation API (/api/v1/ml-pipeline/create)
3. ML Pipeline List/Detail APIs
4. 端到端工作流程測試

Author: Claude
Date: 2026-01-11
"""

import requests
import json
from datetime import datetime
from pathlib import Path

API_BASE = "http://localhost:8000"
TEST_STUDY_NAME = "momentum_optimization_001"  # 需要有實際的 study

def test_trial_comparison():
    """
    測試 1: Trial 比較 API
    
    測試步驟:
    1. 調用 /api/v1/optimization/trials/compare
    2. 驗證返回的統計資訊
    3. 確認推薦結果
    """
    print("\n" + "="*80)
    print("測試 1: Trial 比較 API")
    print("="*80)
    
    # 假設我們要比較 trial 1, 2, 3, 5, 10
    trial_numbers = "1,2,3,5,10"
    url = f"{API_BASE}/api/v1/optimization/trials/compare"
    params = {
        "study_name": TEST_STUDY_NAME,
        "trial_numbers": trial_numbers
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API 調用成功")
            print(f"  Best Trial: #{data['data']['best_trial_number']}")
            print(f"  Best Value: {data['data']['best_value']:.4f}")
            print(f"  Value Mean: {data['data']['value_mean']:.4f}")
            print(f"  Value Std: {data['data']['value_std']:.4f}")
            print(f"  Recommendation: {data['data']['recommendation'][:100]}...")
            return data['data']
        else:
            print(f"❌ API 調用失敗: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ 無法連接到 API 服務器，請確認服務已啟動")
        print("   提示: 在另一個終端機執行 `python run_api.py`")
        return None
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return None


def test_create_single_indicator_pipeline(trial_number: int = 5):
    """
    測試 2: 創建單一指標 Pipeline
    
    測試步驟:
    1. 創建一個繼承 Trial 參數的 Pipeline
    2. 驗證 Pipeline ID
    3. 查詢 Pipeline 詳情
    """
    print("\n" + "="*80)
    print("測試 2: 創建單一指標 Pipeline")
    print("="*80)
    
    url = f"{API_BASE}/api/v1/ml-pipeline/create"
    payload = {
        "study_name": TEST_STUDY_NAME,
        "trial_number": trial_number,
        "strategy_type": "ema_three_line",
        "pipeline_name": f"EMA Test Pipeline (Trial {trial_number})",
        "user_notes": "這是一個測試用的 Pipeline，用於驗證單一指標模式是否正常運作。選擇此 trial 是因為其穩定性較高。",
        "selected_by": "test_script",
        "use_xgboost_tuning": True,
        "indicators": None  # 單一指標模式
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Pipeline 創建成功")
            print(f"  Pipeline ID: {data['pipeline_id']}")
            print(f"  Mode: {data['pipeline_summary']['mode']}")
            print(f"  Feature Count: {data['pipeline_summary']['feature_count']}")
            print(f"  Indicators: {len(data['pipeline_summary']['indicators'])}")
            return data['pipeline_id']
        else:
            print(f"❌ Pipeline 創建失敗: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return None


def test_create_multi_indicator_pipeline(trial_number: int = 5):
    """
    測試 3: 創建多指標 Pipeline
    
    測試步驟:
    1. 創建一個包含 EMA + RSI + MACD 的 Pipeline
    2. 驗證指標配置
    3. 確認特徵名稱生成
    """
    print("\n" + "="*80)
    print("測試 3: 創建多指標 Pipeline")
    print("="*80)
    
    url = f"{API_BASE}/api/v1/ml-pipeline/create"
    payload = {
        "study_name": TEST_STUDY_NAME,
        "trial_number": trial_number,
        "strategy_type": "ema_three_line",
        "pipeline_name": f"Multi-Indicator Test Pipeline (Trial {trial_number})",
        "user_notes": "這是一個測試用的多指標 Pipeline，包含 EMA、RSI 和 MACD 三種指標的組合。",
        "selected_by": "test_script",
        "use_xgboost_tuning": False,
        "indicators": [
            {
                "indicator_type": "ema_three_line",
                "params": {
                    "short_period": 5,
                    "mid_period": 20,
                    "long_period": 60,
                    "volume_threshold": 1000000
                },
                "data_source": "close"
            },
            {
                "indicator_type": "rsi",
                "params": {
                    "period": 14,
                    "overbought": 70,
                    "oversold": 30
                },
                "data_source": "close"
            },
            {
                "indicator_type": "macd",
                "params": {
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9
                },
                "data_source": "close"
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 多指標 Pipeline 創建成功")
            print(f"  Pipeline ID: {data['pipeline_id']}")
            print(f"  Mode: {data['pipeline_summary']['mode']}")
            print(f"  Feature Count: {data['pipeline_summary']['feature_count']}")
            print(f"  Indicators: {len(data['pipeline_summary']['indicators'])}")
            for idx, ind in enumerate(data['pipeline_summary']['indicators'], 1):
                print(f"    {idx}. {ind['type']} on {ind['data_source']}")
            return data['pipeline_id']
        else:
            print(f"❌ 多指標 Pipeline 創建失敗: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return None


def test_get_pipeline_detail(pipeline_id: str):
    """
    測試 4: 查詢 Pipeline 詳情
    """
    print("\n" + "="*80)
    print("測試 4: 查詢 Pipeline 詳情")
    print("="*80)
    
    url = f"{API_BASE}/api/v1/ml-pipeline/{pipeline_id}"
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Pipeline 詳情查詢成功")
            pipeline_data = data['data']
            print(f"  Study Name: {pipeline_data['study_name']}")
            print(f"  Trial Number: {pipeline_data['trial_number']}")
            print(f"  User Notes: {pipeline_data['user_notes'][:50]}...")
            print(f"  Feature Engineering Config:")
            print(f"    - Indicators: {len(pipeline_data['feature_engineering_config']['indicators'])}")
            print(f"    - Features: {len(pipeline_data['feature_engineering_config']['all_feature_names'])}")
            return True
        else:
            print(f"❌ 查詢失敗: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False


def test_list_pipelines():
    """
    測試 5: 列出所有 Pipelines
    """
    print("\n" + "="*80)
    print("測試 5: 列出所有 Pipelines")
    print("="*80)
    
    url = f"{API_BASE}/api/v1/ml-pipeline/list"
    params = {"limit": 10, "offset": 0}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Pipeline 列表查詢成功")
            print(f"  Total Pipelines: {data['total']}")
            print(f"  Returned: {len(data['data'])}")
            for idx, pipeline in enumerate(data['data'][:3], 1):
                print(f"    {idx}. {pipeline['pipeline_id']}")
                print(f"       - Trial: #{pipeline['trial_number']}")
                print(f"       - Features: {pipeline['feature_count']}")
            return True
        else:
            print(f"❌ 查詢失敗: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False


def run_all_tests():
    """
    執行所有測試
    """
    print("\n" + "="*80)
    print("前端整合測試 - Phase 3-6 Frontend Integration")
    print("="*80)
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Base URL: {API_BASE}")
    print(f"Test Study: {TEST_STUDY_NAME}")
    
    results = {
        "trial_comparison": False,
        "single_indicator_pipeline": False,
        "multi_indicator_pipeline": False,
        "pipeline_detail": False,
        "pipeline_list": False
    }
    
    # 測試 1: Trial 比較
    comparison_data = test_trial_comparison()
    results["trial_comparison"] = comparison_data is not None
    
    # 如果 Trial 比較成功，使用最佳 trial 繼續測試
    best_trial = comparison_data['best_trial_number'] if comparison_data else 1
    
    # 測試 2: 創建單一指標 Pipeline
    single_pipeline_id = test_create_single_indicator_pipeline(trial_number=best_trial)
    results["single_indicator_pipeline"] = single_pipeline_id is not None
    
    # 測試 3: 創建多指標 Pipeline
    multi_pipeline_id = test_create_multi_indicator_pipeline(trial_number=best_trial)
    results["multi_indicator_pipeline"] = multi_pipeline_id is not None
    
    # 測試 4: 查詢 Pipeline 詳情（使用任一成功創建的 Pipeline）
    if single_pipeline_id:
        results["pipeline_detail"] = test_get_pipeline_detail(single_pipeline_id)
    elif multi_pipeline_id:
        results["pipeline_detail"] = test_get_pipeline_detail(multi_pipeline_id)
    
    # 測試 5: 列出所有 Pipelines
    results["pipeline_list"] = test_list_pipelines()
    
    # 顯示測試摘要
    print("\n" + "="*80)
    print("測試摘要")
    print("="*80)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    print(f"\n總計: {passed_tests}/{total_tests} 測試通過 ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("\n🎉 所有測試通過！前端整合功能正常運作。")
    else:
        print("\n⚠️ 部分測試失敗，請檢查上述錯誤訊息。")
        print("   常見問題:")
        print("   1. API 服務未啟動: 執行 `python run_api.py`")
        print("   2. Study 不存在: 確認 TEST_STUDY_NAME 變量指向有效的 study")
        print("   3. Trial 數量不足: 確保 study 至少有 5-10 個 trials")


if __name__ == "__main__":
    print("""
前端整合測試腳本
================

此腳本測試 Phase 3-6 的前端整合功能，包括:
1. Trial 比較 API
2. ML Pipeline 創建（單一指標 & 多指標）
3. Pipeline 查詢與列表

使用說明:
1. 確保 API 服務已啟動: python run_api.py
2. 確認 TEST_STUDY_NAME 指向有效的 Optuna study
3. 執行此腳本: python test_frontend_integration.py

注意事項:
- 此腳本會實際創建 Pipeline 配置文件
- 測試文件會儲存在 data_cache/ml_pipelines/
- 可以手動刪除測試生成的文件
""")
    
    input("按 Enter 鍵開始測試...")
    run_all_tests()
