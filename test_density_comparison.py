#!/usr/bin/env python3
"""
比對單參數測試與 Optuna 的密度計算結果
確保相同輸入產生相同輸出

使用方法:
    python test_density_comparison.py

此腳本會:
1. 獲取 ETHUSDT 的所有案例
2. 使用固定的策略配置調用密度分析 API
3. 輸出詳細的輸入參數和結果，供比對

Author: Claude (Debug Script)
Date: 2025-12-11
"""

import requests
import json
import sys

API_BASE_URL = "http://localhost:8000"


def test_density_consistency():
    """測試密度計算一致性"""

    print("=" * 60)
    print("Optuna vs 單參數測試 - 密度計算一致性驗證")
    print("=" * 60)

    # 1. 獲取案例列表
    print("\n[步驟 1] 獲取案例列表...")
    try:
        cases_response = requests.get(f"{API_BASE_URL}/api/v1/case/list", timeout=10)
        cases_response.raise_for_status()
        cases_data = cases_response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ 無法連接到後端 API: {e}")
        print("請確認後端服務已啟動 (通常是 http://localhost:8000)")
        sys.exit(1)

    positive_cases = []
    negative_cases = []

    for case in cases_data.get('cases', []):
        if case.get('symbol') == 'ETHUSDT':
            if case.get('positive_case') == 1:
                positive_cases.append(case['case_id'])
            else:
                negative_cases.append(case['case_id'])

    print(f"  正例: {len(positive_cases)} 個")
    print(f"  反例: {len(negative_cases)} 個")

    if len(positive_cases) < 1 or len(negative_cases) < 1:
        print(f"❌ 案例數量不足 (需要至少各1個)")
        sys.exit(1)

    # 排序以確保順序一致
    positive_cases_sorted = sorted(positive_cases)
    negative_cases_sorted = sorted(negative_cases)

    print(f"\n[案例ID列表 - 用於比對]")
    print(f"  正例前5個: {positive_cases_sorted[:5]}")
    print(f"  反例前5個: {negative_cases_sorted[:5]}")

    # 2. 定義相同的配置 (與 Optuna Trial #0 相同)
    strategy_config = {
        "data_source": "volume",
        "indicator_type": "ema",
        "strategy_logic": "three_line",
        "params": {
            "short_period": 6,
            "mid_period": 18,
            "long_period": 30
        }
    }

    training_window = {
        "reference_point": "TO",
        "lookback_bars": 24,
        "lookforward_bars": 48,
        "far_lookback_bars": 100,
        "mode": "relative"
    }

    print(f"\n[步驟 2] 策略配置:")
    print(f"  data_source: {strategy_config['data_source']}")
    print(f"  indicator_type: {strategy_config['indicator_type']}")
    print(f"  strategy_logic: {strategy_config['strategy_logic']}")
    print(f"  params: {strategy_config['params']}")

    print(f"\n[步驟 3] 窗口配置:")
    print(f"  reference_point: {training_window['reference_point']}")
    print(f"  lookback_bars (Near): {training_window['lookback_bars']}")
    print(f"  far_lookback_bars (Far): {training_window['far_lookback_bars']}")
    print(f"  mode: {training_window['mode']}")

    # 3. 調用密度分析 API（模擬單參數測試）
    density_request = {
        "strategy_config": strategy_config,
        "training_window": training_window,
        "positive_cases": positive_cases_sorted,
        "negative_cases": negative_cases_sorted
    }

    print(f"\n[步驟 4] 調用密度分析 API...")

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/signal-analysis/density",
            json=density_request,
            timeout=60
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ API 調用失敗: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  響應內容: {e.response.text}")
        sys.exit(1)

    result = response.json()

    # 4. 輸出結果
    print("\n" + "=" * 60)
    print("密度分析結果")
    print("=" * 60)

    # 基本指標
    print(f"\n[基本指標]")
    print(f"  Separation: {result.get('separation', 'N/A'):.6f}")
    print(f"  P-value: {result.get('p_value', 'N/A'):.6f}")

    # 近期密度
    print(f"\n[近期密度 (Near Window)]")
    print(f"  正例平均密度: {result.get('positive_avg_density', 'N/A'):.6f}")
    print(f"  反例平均密度: {result.get('negative_avg_density', 'N/A'):.6f}")

    # 遠期密度 (如果有)
    if result.get('positive_far_density') is not None:
        print(f"\n[遠期密度 (Far Window)]")
        print(f"  正例遠期密度: {result.get('positive_far_density', 'N/A'):.6f}")
        print(f"  反例遠期密度: {result.get('negative_far_density', 'N/A'):.6f}")

    # Near/Far 比率 (如果有)
    if result.get('positive_near_far_ratio') is not None:
        print(f"\n[Near/Far 比率]")
        print(f"  正例 Near/Far: {result.get('positive_near_far_ratio', 'N/A'):.6f}")
        print(f"  反例 Near/Far: {result.get('negative_near_far_ratio', 'N/A'):.6f}")
        print(f"  Ratio Separation: {result.get('ratio_separation', 'N/A'):.6f}")

    # 樣本數
    print(f"\n[樣本數]")
    print(f"  正例樣本數: {result.get('positive_sample_size', 'N/A')}")
    print(f"  反例樣本數: {result.get('negative_sample_size', 'N/A')}")

    # 警告信息
    if result.get('warnings'):
        print(f"\n[警告]")
        for warning in result.get('warnings', []):
            print(f"  ⚠️ {warning}")

    print("\n" + "=" * 60)
    print("比對說明")
    print("=" * 60)
    print("""
請將以上結果與後端日誌中的 [DEBUG] 輸出進行比對:

1. 執行 Optuna 優化 (1個 Trial):
   - 在前端設置相同的配置
   - 設置 n_trials = 1
   - 啟動優化
   - 查看後端日誌中的 [DEBUG] Optuna 優化配置

2. 執行單參數測試:
   - 在前端設置相同的配置
   - 點擊「執行測試」
   - 查看後端日誌中的 [DEBUG] 信號密度分析輸入參數

3. 比對以下項目:
   - positive_cases 列表是否完全相同
   - negative_cases 列表是否完全相同
   - training_window 配置是否完全相同
   - strategy_config 配置是否完全相同
   - 最終的 Separation 值是否一致
""")

    return result


def main():
    """主函數"""
    try:
        result = test_density_consistency()
        print("\n✅ 驗證腳本執行完成")
        return 0
    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
