#!/usr/bin/env python3
"""
測試 Optuna 優化完整流程
測試從創建任務到獲取結果的整個流程
"""

import requests
import json
import time
from typing import Dict, List
import pytest

API_BASE_URL = "http://localhost:8000"


def _is_api_reachable() -> bool:
    """Check whether local optimization API endpoint is reachable."""
    try:
        requests.get(API_BASE_URL, timeout=2)
        return True
    except requests.RequestException:
        return False


@pytest.mark.slow
def test_optimization_flow():
    """測試完整優化流程"""

    if not _is_api_reachable():
        pytest.skip(f"Optimization API not reachable at {API_BASE_URL}")

    print("=" * 60)
    print("Optuna 優化流程測試")
    print("=" * 60)

    # Step 1: 獲取案例列表
    print("\n[Step 1] 獲取案例列表...")
    cases_response = requests.get(f"{API_BASE_URL}/api/v1/case/list")
    if not cases_response.ok:
        print(f"❌ 獲取案例失敗: {cases_response.status_code}")
        return

    cases_data = cases_response.json()
    print(f"✅ 成功獲取 {cases_data['total']} 個案例")

    # 過濾 ETHUSDT 案例
    positive_cases = []
    negative_cases = []

    for case in cases_data['cases']:
        if case['symbol'] == 'ETHUSDT':
            if case['positive_case'] == 1:
                positive_cases.append(case['case_id'])
            elif case['positive_case'] == 0:
                negative_cases.append(case['case_id'])

    print(f"   - ETHUSDT 正例: {len(positive_cases)} 個")
    print(f"   - ETHUSDT 反例: {len(negative_cases)} 個")

    if len(positive_cases) == 0 or len(negative_cases) == 0:
        print("❌ 案例數量不足")
        return

    # Step 2: 創建優化任務
    print("\n[Step 2] 創建優化任務...")
    task_payload = {
        "study_name": f"ETHUSDT_test_{int(time.time())}",
        "positive_cases": positive_cases[:10],  # 使用前10個正例
        "negative_cases": negative_cases[:10],  # 使用前10個反例
        "training_window": {
            "reference_point": "TO",
            "lookback_bars": 24,
            "lookforward_bars": 0,
            "far_lookback_bars": 100,
            "mode": "relative"
        },
        "sampler_type": "TPE",
        "n_trials": 5,  # 少量 trials 用於快速測試
        "n_jobs": 1,
        "use_multi_objective": False,
        "parameter_ranges": {
            "ema_short_range": [5, 19],
            "ema_mid_range": [21, 49],
            "ema_long_range": [51, 200],
            "data_sources": ["close"],
            "strategy_logics": ["three_line"]
        }
    }

    create_response = requests.post(
        f"{API_BASE_URL}/api/v1/optimization/tasks",
        json=task_payload,
        headers={"Content-Type": "application/json"}
    )

    if not create_response.ok:
        print(f"❌ 創建任務失敗: {create_response.status_code}")
        print(f"   錯誤詳情: {create_response.text}")
        return

    create_data = create_response.json()
    task_id = create_data['task_id']
    print(f"✅ 任務已創建: {task_id}")
    print(f"   狀態: {create_data.get('status', 'N/A')}")

    # Step 3: 啟動優化任務
    print("\n[Step 3] 啟動優化任務...")
    start_response = requests.post(
        f"{API_BASE_URL}/api/v1/optimization/tasks/{task_id}/start"
    )

    if not start_response.ok:
        print(f"❌ 啟動任務失敗: {start_response.status_code}")
        print(f"   錯誤詳情: {start_response.text}")
        return

    start_data = start_response.json()
    print(f"✅ 任務已啟動")
    print(f"   狀態: {start_data.get('status', 'N/A')}")

    # Step 4: 輪詢任務狀態
    print("\n[Step 4] 監控任務進度...")
    max_wait = 300  # 最多等待5分鐘
    start_time = time.time()

    while time.time() - start_time < max_wait:
        status_response = requests.get(
            f"{API_BASE_URL}/api/v1/optimization/tasks/{task_id}"
        )

        if not status_response.ok:
            print(f"❌ 查詢狀態失敗: {status_response.status_code}")
            break

        status_data = status_response.json()
        # API 返回結構是 {"success": true, "data": {...}}
        data = status_data.get('data', status_data)
        current_status = data.get('status', 'UNKNOWN')
        progress = data.get('progress', {})

        print(f"   [{int(time.time() - start_time)}s] 狀態: {current_status}", end="")
        if progress:
            completed = progress.get('completed_trials', 0)
            total = progress.get('total_trials', 0)
            print(f" - 進度: {completed}/{total} trials", end="")
        print()

        if current_status == 'completed':
            print("\n✅ 優化完成！")
            break
        elif current_status == 'failed':
            print("\n❌ 優化失敗")
            error_msg = data.get('error_message', '未知錯誤')
            print(f"   錯誤: {error_msg}")
            return

        time.sleep(5)  # 每5秒查詢一次
    else:
        print("\n⚠️ 超時，任務仍在運行中")
        print(f"   可以訪問前端查看結果: http://localhost:3000/optimization-result/{task_id}")
        return

    # Step 5: 獲取優化結果
    print("\n[Step 5] 獲取優化結果...")
    result_response = requests.get(
        f"{API_BASE_URL}/api/v1/optimization/tasks/{task_id}/result"
    )

    if not result_response.ok:
        print(f"❌ 獲取結果失敗: {result_response.status_code}")
        return

    result_data = result_response.json()
    result = result_data.get('result', {})

    print("✅ 優化結果:")
    print(f"   - 最佳 Sharpe Ratio: {result.get('best_value', 'N/A')}")
    print(f"   - 最佳 Trial: #{result.get('best_trial_number', 'N/A')}")

    best_params = result.get('best_params', {})
    if best_params:
        print("   - 最佳參數:")
        for key, value in best_params.items():
            print(f"     • {key}: {value}")

    # Step 6: 測試分析 API
    print("\n[Step 6] 測試分析 API...")

    # 6.1 參數重要性
    importance_response = requests.get(
        f"{API_BASE_URL}/api/v1/optimization/tasks/{task_id}/analysis/param-importance"
    )
    if importance_response.ok:
        importance_data = importance_response.json()
        importances = importance_data.get('data', {}).get('importances', [])
        print(f"   ✅ 參數重要性: {len(importances)} 個參數")
        for imp in importances[:3]:  # 顯示前3個
            print(f"      • {imp.get('parameter_name')}: {imp.get('importance', 0):.4f}")
    else:
        print(f"   ⚠️ 參數重要性 API 失敗: {importance_response.status_code}")

    # 6.2 收斂分析
    convergence_response = requests.get(
        f"{API_BASE_URL}/api/v1/optimization/tasks/{task_id}/analysis/convergence"
    )
    if convergence_response.ok:
        convergence_data = convergence_response.json()
        print(f"   ✅ 收斂分析: 成功")
    else:
        print(f"   ⚠️ 收斂分析 API 失敗: {convergence_response.status_code}")

    # 6.3 穩定性分析
    stability_response = requests.get(
        f"{API_BASE_URL}/api/v1/optimization/tasks/{task_id}/analysis/stability"
    )
    if stability_response.ok:
        stability_data = stability_response.json()
        print(f"   ✅ 穩定性分析: 成功")
    else:
        print(f"   ⚠️ 穩定性分析 API 失敗: {stability_response.status_code}")

    # 6.4 Top Trials
    trials_response = requests.get(
        f"{API_BASE_URL}/api/v1/optimization/tasks/{task_id}/trials?top_n=5"
    )
    if trials_response.ok:
        trials_data = trials_response.json()
        trials = trials_data.get('trials', [])
        print(f"   ✅ Top Trials: {len(trials)} 個")
    else:
        print(f"   ⚠️ Top Trials API 失敗: {trials_response.status_code}")

    print("\n" + "=" * 60)
    print("測試完成！")
    print(f"前端結果頁面: http://localhost:3000/optimization-result/{task_id}")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_optimization_flow()
    except KeyboardInterrupt:
        print("\n\n⚠️ 測試被用戶中斷")
    except Exception as e:
        print(f"\n\n❌ 測試過程中發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
