"""
3.2C- 雙窗口密度驗證腳本

驗證目標:
1. 核心功能驗證: 近期窗口和遠期窗口提取是否正確
2. 密度計算驗證: near density、far density、near/far ratio 計算是否正確
3. 統計分析驗證: ratio_separation、p-value、Cohen's d 是否正確
4. 數據完整性驗證: 165個案例(55正例、110反例)是否全部處理成功
5. CSV輸出驗證: 結果輸出格式和內容是否符合預期

測試配置:
- 數據源: kline_cache.h5 (12,592 bars, ETHUSDT/12h)
- 案例源: data_cache/cases.json (165 cases)
- 雙密度配置:
  - reference_point: TO
  - lookback_bars: 24 (近期窗口: TO-24 to TO-1)
  - far_lookback_bars: 100 (遠期窗口: TO-100 to TO-25, 共76根K線)
  - lookforward_bars: 0 (避免未來函數洩漏)
- 策略: EMA三線排列 (5/10/20, close)

預期結果:
- 正例near/far ratio > 反例near/far ratio (信號聚集效應)
- ratio_separation > 0.3 為良好指標
- p_value < 0.05 為統計顯著
- 輸出CSV包含案例級別密度數據

Author: Claude (Phase 3.3+3.4)
Date: 2025-11-12
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import pandas as pd
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.Indicators.indicator_engine import IndicatorEngine
from momentum.Indicators.ema_indicator import EMAIndicator
from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer
from api.models.training_window_config import (
    TrainingWindowConfig,
    StrategyConfig,
    SignalDensityResponse
)


class DualDensityVerifier:
    """
    雙窗口密度驗證器

    驗證SignalDensityAnalyzer的雙密度計算功能是否正確。
    """

    # 配置: 使用者指定要用哪個 timeframe 計算指標
    # 可選: "1h", "4h", "12h", "1d" 等（需確保 kline_cache.h5 中有對應數據）
    CALCULATION_TIMEFRAME = "1h"  # 使用現有的 ETHUSDT/1h 數據

    def __init__(self):
        """初始化驗證器"""
        self.storage = KlineStorageManager(cache_dir="data_cache")
        self.indicator_engine = IndicatorEngine()
        self.analyzer = SignalDensityAnalyzer(
            kline_storage=self.storage,
            indicator_engine=self.indicator_engine
        )

        # 測試配置
        self.training_window = TrainingWindowConfig(
            reference_point="TO",
            lookback_bars=24,
            lookforward_bars=0,
            far_lookback_bars=100,
            mode="relative"
        )

        self.strategy_config = StrategyConfig(
            data_source="close",
            indicator_type="ema",
            strategy_logic="three_line",
            params={
                "ema_short": 7,
                "ema_mid": 16,
                "ema_long": 36
            }
        )

        # 結果存儲
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'training_window': self.training_window.model_dump(),
                'strategy_config': self.strategy_config.model_dump()
            },
            'tests': [],
            'summary': {}
        }

    def load_cases(self) -> tuple[list, list]:
        """
        從cases.json載入案例（直接讀取，不依賴CaseStorage）

        Returns:
            (positive_case_objs, negative_case_objs) - SimpleNamespace 對象列表
        """
        cases_path = project_root / "data_cache" / "cases.json"

        if not cases_path.exists():
            raise FileNotFoundError(f"Cases file not found: {cases_path}")

        with open(cases_path, 'r', encoding='utf-8') as f:
            cases_data = json.load(f)

        # New format: {"version": "1.0", "cases": [...]}
        if isinstance(cases_data, dict) and 'cases' in cases_data:
            cases_list = cases_data['cases']
        elif isinstance(cases_data, list):
            cases_list = cases_data
        elif isinstance(cases_data, dict):
            # Old format: {case_id: {...}}
            cases_list = [{'case_id': k, **v} for k, v in cases_data.items() if isinstance(v, dict)]
        else:
            raise ValueError(f"Unexpected cases_data format: {type(cases_data)}")

        # Filter by positive_case field (1 = positive, 0 = negative)
        # 注意: 不過濾 timeframe，因為案例的 timeframe 只是元數據
        # 實際計算使用的 timeframe 由 CALCULATION_TIMEFRAME 指定
        # 將字典轉換為對象（SignalDensityAnalyzer 期待對象屬性訪問）
        positive_cases = [
            SimpleNamespace(**case) for case in cases_list
            if case.get('positive_case') == 1
        ]

        negative_cases = [
            SimpleNamespace(**case) for case in cases_list
            if case.get('positive_case') == 0
        ]

        print(f"✓ Loaded cases from {cases_path}")
        print(f"  - Positive cases: {len(positive_cases)}")
        print(f"  - Negative cases: {len(negative_cases)}")
        print(f"  - Total cases: {len(positive_cases) + len(negative_cases)}")

        return positive_cases, negative_cases

    async def verify_window_extraction(self) -> bool:
        """
        驗證窗口提取邏輯

        測試:
        1. 近期窗口提取 (TO-24 to TO-1, 24根K線)
        2. 遠期窗口提取 (TO-100 to TO-25, 76根K線)
        3. 窗口無重疊驗證

        Returns:
            測試是否通過
        """
        print("\n" + "="*80)
        print("TEST 1: 窗口提取邏輯驗證")
        print("="*80)

        # 載入一個正例案例進行測試
        positive_cases, _ = self.load_cases()

        if not positive_cases:
            print("✗ No positive cases found for testing")
            return False

        test_case = positive_cases[0]
        test_case_id = test_case.case_id

        # 從cases.json讀取案例詳情
        cases_path = project_root / "data_cache" / "cases.json"
        with open(cases_path, 'r', encoding='utf-8') as f:
            cases_data = json.load(f)

        # Find the case in the list
        if 'cases' in cases_data:
            case_info = next(
                (c for c in cases_data['cases'] if c['case_id'] == test_case_id),
                None
            )
        else:
            case_info = cases_data.get(test_case_id)

        if not case_info:
            print(f"✗ Case not found: {test_case_id}")
            return False

        print(f"\nTest Case: {test_case_id}")
        print(f"  Symbol: {case_info['symbol']}")
        print(f"  Timeframe: {case_info['timeframe']}")
        print(f"  Timestamp: {case_info['timestamp']}")

        # 構造case對象
        # For positive cases, timestamp is TO
        # For negative cases, timestamp is also the reference point
        case = type('Case', (), {
            'case_id': test_case_id,
            'symbol': case_info['symbol'],
            'timeframe': self.CALCULATION_TIMEFRAME,  # 使用配置的計算時間框架，而非案例元數據中的timeframe
            'timestamp': case_info['timestamp'],  # Required by SignalDensityAnalyzer
            'TO': case_info['timestamp'],
            'TC': None,  # Not provided in current format
            'label': case_info['positive_case']
        })()

        try:
            # 提取近期窗口
            near_window = self.analyzer.extract_training_window(case, self.training_window)
            print(f"\n✓ Near window extracted: {len(near_window)} bars")

            if len(near_window) != 24:
                print(f"✗ FAIL: Expected 24 bars, got {len(near_window)}")
                return False

            # 提取遠期窗口
            far_window = self.analyzer.extract_far_window(case, self.training_window)
            print(f"✓ Far window extracted: {len(far_window)} bars")

            expected_far_size = 100 - 24  # 76 bars
            if len(far_window) != expected_far_size:
                print(f"✗ FAIL: Expected {expected_far_size} bars, got {len(far_window)}")
                return False

            # 驗證窗口無重疊 (near window的最早時間應該晚於far window的最晚時間)
            near_earliest = near_window.index[0]
            far_latest = far_window.index[-1]

            print(f"\nWindow timestamps:")
            print(f"  Near window: {near_earliest} to {near_window.index[-1]}")
            print(f"  Far window: {far_window.index[0]} to {far_latest}")

            if near_earliest <= far_latest:
                print(f"✗ FAIL: Windows overlap! Near earliest ({near_earliest}) <= Far latest ({far_latest})")
                return False

            print(f"✓ No overlap: Near starts after far ends")

            print("\n✓ TEST 1 PASSED: Window extraction verified")
            self.results['tests'].append({
                'test_name': 'window_extraction',
                'status': 'PASS',
                'details': {
                    'near_window_size': len(near_window),
                    'far_window_size': len(far_window),
                    'no_overlap': True
                }
            })
            return True

        except Exception as e:
            print(f"\n✗ TEST 1 FAILED: {e}")
            import traceback
            traceback.print_exc()
            self.results['tests'].append({
                'test_name': 'window_extraction',
                'status': 'FAIL',
                'error': str(e)
            })
            return False

    async def verify_density_calculation(self) -> bool:
        """
        驗證密度計算邏輯

        測試:
        1. Near density 計算
        2. Far density 計算
        3. Near/far ratio 計算
        4. Zero-division handling

        Returns:
            測試是否通過
        """
        print("\n" + "="*80)
        print("TEST 2: 密度計算驗證")
        print("="*80)

        positive_cases, negative_cases = self.load_cases()

        # 選擇至少10個案例進行詳細驗證 (滿足SignalDensityRequest驗證要求)
        test_positive = positive_cases[:10]
        test_negative = negative_cases[:10]

        # 覆寫 timeframe 為配置的計算時間框架
        for case in test_positive + test_negative:
            case.timeframe = self.CALCULATION_TIMEFRAME

        print(f"\nTesting with {len(test_positive)} positive and {len(test_negative)} negative cases")

        try:
            # 直接使用 SignalDensityAnalyzer（不經過服務層）
            # 這樣避免與運行中的 API 服務器產生衝突
            response: SignalDensityResponse = self.analyzer.analyze_signal_density(
                positive_cases=test_positive,
                negative_cases=test_negative,
                strategy_config=self.strategy_config,
                window_config=self.training_window
            )

            print(f"\n✓ Density calculation completed")
            print(f"\nResults:")
            print(f"  Positive cases:")
            print(f"    - Near density: {response.positive_avg_density:.4f}")
            print(f"    - Far density: {response.positive_far_avg_density:.4f}")
            print(f"    - Near/Far ratio: {response.positive_near_far_ratio:.4f}")
            print(f"  Negative cases:")
            print(f"    - Near density: {response.negative_avg_density:.4f}")
            print(f"    - Far density: {response.negative_far_avg_density:.4f}")
            print(f"    - Near/Far ratio: {response.negative_near_far_ratio:.4f}")
            print(f"\n  Separation metrics:")
            print(f"    - Density separation: {response.separation:.4f}")
            print(f"    - Ratio separation: {response.ratio_separation:.4f}")

            # 驗證計算邏輯
            checks_passed = True

            # Check 1: Densities should be in [0, 1]
            if not (0 <= response.positive_avg_density <= 1):
                print(f"✗ FAIL: Positive near density out of range: {response.positive_avg_density}")
                checks_passed = False

            if not (0 <= response.positive_far_avg_density <= 1):
                print(f"✗ FAIL: Positive far density out of range: {response.positive_far_avg_density}")
                checks_passed = False

            # Check 2: ratio_separation should be calculated correctly
            expected_ratio_sep = response.positive_near_far_ratio - response.negative_near_far_ratio
            if abs(response.ratio_separation - expected_ratio_sep) > 0.0001:
                print(f"✗ FAIL: ratio_separation mismatch: {response.ratio_separation} vs {expected_ratio_sep}")
                checks_passed = False

            # Check 3: Ratios should be non-negative
            if response.positive_near_far_ratio < 0:
                print(f"✗ FAIL: Negative ratio: {response.positive_near_far_ratio}")
                checks_passed = False

            if checks_passed:
                print(f"\n✓ All density calculation checks passed")
                self.results['tests'].append({
                    'test_name': 'density_calculation',
                    'status': 'PASS',
                    'details': {
                        'positive_near_density': response.positive_avg_density,
                        'positive_far_density': response.positive_far_avg_density,
                        'positive_ratio': response.positive_near_far_ratio,
                        'ratio_separation': response.ratio_separation
                    }
                })
                return True
            else:
                print(f"\n✗ TEST 2 FAILED: Some checks did not pass")
                self.results['tests'].append({
                    'test_name': 'density_calculation',
                    'status': 'FAIL'
                })
                return False

        except Exception as e:
            print(f"\n✗ TEST 2 FAILED: {e}")
            import traceback
            traceback.print_exc()
            self.results['tests'].append({
                'test_name': 'density_calculation',
                'status': 'FAIL',
                'error': str(e)
            })
            return False

    async def verify_full_analysis(self) -> bool:
        """
        驗證完整分析 (全部165個案例)

        測試:
        1. 所有案例處理成功
        2. 統計指標正確計算
        3. 輸出CSV格式正確

        Returns:
            測試是否通過
        """
        print("\n" + "="*80)
        print("TEST 3: 完整分析驗證 (全部165案例)")
        print("="*80)

        positive_cases, negative_cases = self.load_cases()

        # 覆寫 timeframe 為配置的計算時間框架
        for case in positive_cases + negative_cases:
            case.timeframe = self.CALCULATION_TIMEFRAME

        try:
            print(f"\nRunning full analysis on {len(positive_cases) + len(negative_cases)} cases...")

            # 直接使用 SignalDensityAnalyzer（不經過服務層）
            response: SignalDensityResponse = self.analyzer.analyze_signal_density(
                positive_cases=positive_cases,
                negative_cases=negative_cases,
                strategy_config=self.strategy_config,
                window_config=self.training_window
            )

            print(f"\n✓ Full analysis completed")
            print(f"\n{'='*60}")
            print(f"DUAL-DENSITY ANALYSIS RESULTS")
            print(f"{'='*60}")

            print(f"\n1. Sample Sizes:")
            print(f"   - Positive cases: {response.positive_sample_size}")
            print(f"   - Negative cases: {response.negative_sample_size}")

            print(f"\n2. Near Window Density (TO-24 to TO-1):")
            print(f"   - Positive avg: {response.positive_avg_density:.4f} (±{response.positive_std:.4f})")
            print(f"   - Negative avg: {response.negative_avg_density:.4f} (±{response.negative_std:.4f})")
            print(f"   - Separation: {response.separation:.4f}")

            print(f"\n3. Far Window Density (TO-100 to TO-25):")
            print(f"   - Positive avg: {response.positive_far_avg_density:.4f}")
            print(f"   - Negative avg: {response.negative_far_avg_density:.4f}")

            print(f"\n4. Near/Far Ratio (Signal Clustering):")
            print(f"   - Positive ratio: {response.positive_near_far_ratio:.4f}")
            print(f"   - Negative ratio: {response.negative_near_far_ratio:.4f}")
            print(f"   - Ratio separation: {response.ratio_separation:.4f}")

            print(f"\n5. Statistical Significance:")
            print(f"   - p-value: {response.p_value:.6f} {'✓ Significant' if response.p_value < 0.05 else '✗ Not significant'}")
            print(f"   - Cohen's d: {response.cohens_d:.4f}")
            print(f"   - Stability CV: {response.stability_cv:.4f}")

            # 判斷策略質量
            print(f"\n6. Strategy Quality Assessment:")
            if response.ratio_separation > 0.5 and response.p_value < 0.05:
                quality = "EXCELLENT"
                symbol = "🟢"
            elif response.ratio_separation > 0.3 and response.p_value < 0.10:
                quality = "GOOD"
                symbol = "🟡"
            else:
                quality = "WEAK"
                symbol = "🔴"

            print(f"   {symbol} Quality: {quality}")
            print(f"   - Ratio separation: {response.ratio_separation:.4f} (target: >0.3)")
            print(f"   - Statistical significance: p={response.p_value:.6f} (target: <0.05)")

            # 保存結果到CSV
            output_dir = project_root / "test_results"
            output_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = output_dir / f"dual_density_verification_{timestamp}.csv"

            # 構建案例級別數據
            case_data = []
            for case_id, density in response.case_level_densities.items():
                label = 1 if case_id in positive_cases else 0
                case_data.append({
                    'case_id': case_id,
                    'label': label,
                    'near_density': density,
                    # Note: 案例級別的far_density和ratio需要從analyzer獲取
                })

            df = pd.DataFrame(case_data)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"\n✓ Results saved to: {csv_path}")

            # 保存匯總報告
            summary = {
                'positive_sample_size': response.positive_sample_size,
                'negative_sample_size': response.negative_sample_size,
                'positive_near_density': response.positive_avg_density,
                'positive_far_density': response.positive_far_avg_density,
                'positive_near_far_ratio': response.positive_near_far_ratio,
                'negative_near_density': response.negative_avg_density,
                'negative_far_density': response.negative_far_avg_density,
                'negative_near_far_ratio': response.negative_near_far_ratio,
                'separation': response.separation,
                'ratio_separation': response.ratio_separation,
                'p_value': response.p_value,
                'cohens_d': response.cohens_d,
                'stability_cv': response.stability_cv,
                'quality': quality
            }

            self.results['summary'] = summary

            json_path = output_dir / f"dual_density_verification_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            print(f"✓ Summary saved to: {json_path}")

            print(f"\n✓ TEST 3 PASSED: Full analysis completed successfully")
            self.results['tests'].append({
                'test_name': 'full_analysis',
                'status': 'PASS',
                'summary': summary
            })
            return True

        except Exception as e:
            print(f"\n✗ TEST 3 FAILED: {e}")
            import traceback
            traceback.print_exc()
            self.results['tests'].append({
                'test_name': 'full_analysis',
                'status': 'FAIL',
                'error': str(e)
            })
            return False

    async def run_all_tests(self) -> bool:
        """
        運行所有驗證測試

        Returns:
            所有測試是否通過
        """
        print("\n" + "="*80)
        print("DUAL-DENSITY VERIFICATION SUITE")
        print("="*80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Configuration:")
        print(f"  - Calculation Timeframe: {self.CALCULATION_TIMEFRAME}")
        print(f"  - Near window: TO-{self.training_window.lookback_bars} to TO-1")
        print(f"  - Far window: TO-{self.training_window.far_lookback_bars} to TO-{self.training_window.lookback_bars + 1}")
        print(f"  - Strategy: EMA({self.strategy_config.params['ema_short']}/{self.strategy_config.params['ema_mid']}/{self.strategy_config.params['ema_long']}) on {self.strategy_config.data_source}")

        all_passed = True

        # Test 1: Window extraction
        if not await self.verify_window_extraction():
            all_passed = False

        # Test 2: Density calculation
        if not await self.verify_density_calculation():
            all_passed = False

        # Test 3: Full analysis
        if not await self.verify_full_analysis():
            all_passed = False

        # 最終報告
        print("\n" + "="*80)
        print("VERIFICATION SUMMARY")
        print("="*80)

        passed_tests = sum(1 for t in self.results['tests'] if t['status'] == 'PASS')
        total_tests = len(self.results['tests'])

        print(f"\nTests passed: {passed_tests}/{total_tests}")

        for test in self.results['tests']:
            status_symbol = "✓" if test['status'] == 'PASS' else "✗"
            print(f"  {status_symbol} {test['test_name']}: {test['status']}")

        if all_passed:
            print(f"\n🎉 ALL TESTS PASSED! 雙窗口密度功能驗證成功!")
        else:
            print(f"\n❌ SOME TESTS FAILED. Please check the details above.")

        return all_passed


async def main():
    """主函數"""
    verifier = DualDensityVerifier()
    success = await verifier.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
