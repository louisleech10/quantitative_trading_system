#!/usr/bin/env python3
"""
測試參數範圍修復是否生效
使用更窄的參數範圍來驗證 Optuna 是否尊重前端配置
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:8000"

def test_parameter_range_fix():
    """
    測試參數範圍修復

    用戶配置: Short 3-12, Mid 14-18, Long 20-33
    預期結果: 所有 trials 的參數都在這些範圍內
    """

    print("=" * 60)
    print("參數範圍修復驗證測試")
    print("=" * 60)

    # 獲取案例
    print("\n[Step 1] 獲取 ETHUSDT 案例...")
    cases_response = requests.get(f"{API_BASE_URL}/api/v1/case/list")
    if not cases_response.ok:
        print(f"❌ 獲取案例失敗: {cases_response.status_code}")
        return

    cases_data = cases_response.json()
    positive_cases = []
    negative_cases = []

    for case in cases_data['cases']:
        if case['symbol'] == 'ETHUSDT':
            if case['positive_case'] == 1:
                positive_cases.append(case['case_id'])
            elif case['positive_case'] == 0:
                negative_cases.append(case['case_id'])

    print(f"✅ 正例: {len(positive_cases)} 個, 反例: {len(negative_cases)} 個")

    # 創建優化任務 - 使用窄範圍
    print("\n[Step 2] 創建優化任務...")
    print("   配置範圍:")
    print("   - Short:  3-12")
    print("   - Mid:   14-18")
    print("   - Long:  20-33")

    task_payload = {
        "study_name": f"RANGE_TEST_{int(time.time())}",
        "positive_cases": positive_cases[:5],
        "negative_cases": negative_cases[:5],
        "training_window": {
            "reference_point": "TO",
            "lookback_bars": 24,
            "lookforward_bars": 0,
            "far_lookback_bars": 100,
            "mode": "relative"
        },
        "sampler_type": "TPE",
        "n_trials": 10,
        "n_jobs": 1,
        "use_multi_objective": False,
        "parameter_ranges": {
            "ema_short_range": [3, 12],
            "ema_mid_range": [14, 18],
            "ema_long_range": [20, 33],
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
        print(f"   錯誤: {create_response.text}")
        return

    create_data = create_response.json()
    task_id = create_data['task_id']
    print(f"✅ 任務已創建: {task_id}")

    # 啟動任務
    print("\n[Step 3] 啟動優化...")
    start_response = requests.post(
        f"{API_BASE_URL}/api/v1/optimization/tasks/{task_id}/start"
    )

    if not start_response.ok:
        print(f"❌ 啟動失敗: {start_response.status_code}")
        return

    print("✅ 任務已啟動，等待完成...")

    # 等待完成
    max_wait = 120
    start_time = time.time()

    while time.time() - start_time < max_wait:
        status_response = requests.get(
            f"{API_BASE_URL}/api/v1/optimization/tasks/{task_id}"
        )

        if status_response.ok:
            status_data = status_response.json()
            data = status_data.get('data', status_data)
            current_status = data.get('status', 'UNKNOWN')

            if current_status == 'completed':
                print("✅ 優化完成！")
                break
            elif current_status == 'failed':
                print("❌ 優化失敗")
                return

        time.sleep(3)
    else:
        print("⚠️ 超時")
        return

    # 獲取所有 trials
    print("\n[Step 4] 驗證參數範圍...")
    trials_response = requests.get(
        f"{API_BASE_URL}/api/v1/optimization/tasks/{task_id}/trials?top_n=100"
    )

    if not trials_response.ok:
        print(f"❌ 獲取 trials 失敗: {trials_response.status_code}")
        return

    trials_data = trials_response.json()
    trials = trials_data.get('trials', [])

    # 驗證參數範圍
    violations = []
    for trial in trials:
        trial_number = trial.get('number', trial.get('trial_number'))
        if trial.get('state') == 'COMPLETE':
            params = trial.get('params', {})
            short = params.get('short_period')
            mid = params.get('mid_period')
            long = params.get('long_period')

            if short is not None and (short < 3 or short > 12):
                violations.append(f"Trial #{trial_number}: short_period={short} (超出 3-12)")
            if mid is not None and (mid < 14 or mid > 18):
                violations.append(f"Trial #{trial_number}: mid_period={mid} (超出 14-18)")
            if long is not None and (long < 20 or long > 33):
                violations.append(f"Trial #{trial_number}: long_period={long} (超出 20-33)")

    print(f"   總共 {len(trials)} 個 trials")
    completed = sum(1 for t in trials if t.get('state') == 'COMPLETE')
    print(f"   完成 {completed} 個")

    if violations:
        print(f"\n❌ 發現 {len(violations)} 個參數範圍違規:")
        for v in violations:
            print(f"   • {v}")
    else:
        print("\n✅ 所有參數都在配置範圍內！")
        print("   修復驗證成功：Optuna 現在尊重前端配置的參數範圍")

    # 顯示幾個示例參數
    print("\n[Step 5] 示例參數:")
    completed_trials = [t for t in trials if t.get('state') == 'COMPLETE']
    for trial in completed_trials[:5]:
        trial_number = trial.get('number', trial.get('trial_number'))
        params = trial.get('params', {})
        print(f"   Trial #{trial_number}: "
              f"short={params.get('short_period')}, "
              f"mid={params.get('mid_period')}, "
              f"long={params.get('long_period')}")

    print("\n" + "=" * 60)
    print("測試完成！")
    print(f"前端頁面: http://localhost:3000/optimization-result/{task_id}")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_parameter_range_fix()
    except KeyboardInterrupt:
        print("\n\n⚠️ 測試被中斷")
    except Exception as e:
        print(f"\n\n❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
