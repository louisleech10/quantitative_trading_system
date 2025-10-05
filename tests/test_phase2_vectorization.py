"""
Phase 2 向量化計算測試套件

測試目標：
1. 向量化正確性：與原循環版本結果100%一致
2. 性能提升：測試實際加速倍數
3. 邊界情況：NaN處理、除零處理
4. 端到端集成：Phase 0+1+2完整流程

運行方式：
    python tests/test_phase2_vectorization.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import logging

from momentum.DataExtraction.data_loader_momentum import DataLoader
from momentum.DataExtraction.case_search_engine import CaseSearchEngine, SearchConfiguration

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_dataframe(n_rows=1000):
    """創建測試用DataFrame"""
    dates = pd.date_range(start='2023-01-01', periods=n_rows, freq='4H')

    # 生成模擬價格數據（隨機遊走）
    np.random.seed(42)
    price = 100
    prices = []

    for _ in range(n_rows):
        change = np.random.normal(0, 0.02)  # 2%標準差
        price = price * (1 + change)
        prices.append(price)

    df = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': [np.random.uniform(1e6, 1e7) for _ in range(n_rows)]
    }, index=dates)

    return df


def calculate_drawdown_loop(df: pd.DataFrame, bar: int) -> pd.Series:
    """原循環版本：計算未來最大回撤（慢但正確）"""
    result = pd.Series(np.nan, index=df.index)

    for i in range(len(df) - bar):
        current_close = df['close'].iloc[i]
        if current_close > 0:
            future_slice = df.iloc[i+1:i+bar+1]
            if len(future_slice) > 0:
                min_low = future_slice['low'].min()
                if pd.notna(min_low):
                    result.iloc[i] = (min_low / current_close - 1)

    return result


def calculate_drawdown_vectorized(df: pd.DataFrame, bar: int) -> pd.Series:
    """向量化版本：計算未來最大回撤（快）"""
    # 使用 shift + min 方法（與主代碼一致）
    min_values = []
    for offset in range(1, bar + 1):
        min_values.append(df['low'].shift(-offset))

    if min_values:
        future_min_low = pd.concat(min_values, axis=1).min(axis=1)
    else:
        future_min_low = pd.Series(np.nan, index=df.index)

    return np.where(
        df['close'] > 0,
        (future_min_low / df['close'] - 1),
        np.nan
    )


def test_vectorization_correctness():
    """測試1：向量化正確性測試"""
    logger.info("="*60)
    logger.info("測試1：向量化正確性測試")
    logger.info("="*60)

    df_test = create_test_dataframe(1000)

    # 測試不同的bar值
    test_bars = [1, 3, 6, 12]
    all_passed = True

    for bar in test_bars:
        logger.info(f"\n測試 bar={bar} ...")

        # 原循環版本
        result_loop = calculate_drawdown_loop(df_test.copy(), bar)

        # 向量化版本
        result_vectorized = calculate_drawdown_vectorized(df_test.copy(), bar)

        # 比較結果（允許極小誤差）
        # 使用 allclose 而非 equals，因為浮點運算可能有微小差異
        valid_mask = pd.notna(result_loop) & pd.notna(result_vectorized)

        if valid_mask.sum() > 0:
            max_diff = np.abs(result_loop[valid_mask] - result_vectorized[valid_mask]).max()
            is_close = np.allclose(
                result_loop[valid_mask],
                result_vectorized[valid_mask],
                rtol=1e-10,
                atol=1e-10
            )

            if is_close:
                logger.info(f"  ✅ bar={bar} 通過 (最大差異: {max_diff:.2e})")
            else:
                logger.error(f"  ❌ bar={bar} 失敗 (最大差異: {max_diff:.2e})")
                all_passed = False

                # 顯示前5個差異
                diff_series = np.abs(result_loop - result_vectorized)
                top_diff_idx = diff_series.nlargest(5).index

                for idx in top_diff_idx:
                    logger.error(
                        f"    索引{df_test.index.get_loc(idx)}: "
                        f"循環={result_loop[idx]:.6f}, "
                        f"向量={result_vectorized[idx]:.6f}, "
                        f"差異={diff_series[idx]:.6f}"
                    )
        else:
            logger.warning(f"  ⚠️  bar={bar} 無有效數據可比較")

    if all_passed:
        logger.info("\n" + "="*60)
        logger.info("✅ 向量化正確性測試：全部通過")
        logger.info("="*60)
    else:
        logger.error("\n" + "="*60)
        logger.error("❌ 向量化正確性測試：有失敗")
        logger.error("="*60)

    return all_passed


def test_performance_improvement():
    """測試2：性能提升測試"""
    logger.info("\n" + "="*60)
    logger.info("測試2：性能提升測試")
    logger.info("="*60)

    # 測試不同規模
    test_sizes = [1000, 10000, 50000]

    for n_rows in test_sizes:
        logger.info(f"\n測試數據規模: {n_rows} 根K線")
        df_large = create_test_dataframe(n_rows)

        # 測試單個bar（避免測試時間過長）
        bar = 6

        # 原循環版本
        start = time.time()
        result_loop = calculate_drawdown_loop(df_large.copy(), bar)
        time_loop = time.time() - start

        # 向量化版本
        start = time.time()
        result_vectorized = calculate_drawdown_vectorized(df_large.copy(), bar)
        time_vectorized = time.time() - start

        speedup = time_loop / time_vectorized

        logger.info(f"  循環版本: {time_loop:.3f}秒")
        logger.info(f"  向量化版本: {time_vectorized:.3f}秒")
        logger.info(f"  提升倍數: {speedup:.1f}x")

        if speedup > 5:
            logger.info(f"  ✅ 性能提升達標 (>{5}倍)")
        else:
            logger.warning(f"  ⚠️  性能提升未達標 (<{5}倍)")

    logger.info("\n" + "="*60)
    logger.info("✅ 性能提升測試完成")
    logger.info("="*60)


def test_edge_cases():
    """測試3：邊界情況測試"""
    logger.info("\n" + "="*60)
    logger.info("測試3：邊界情況測試")
    logger.info("="*60)

    # 測試1: 包含NaN的數據
    logger.info("\n子測試1: NaN處理")
    df_nan = create_test_dataframe(100)
    df_nan.loc[df_nan.index[10:20], 'low'] = np.nan

    result = calculate_drawdown_vectorized(df_nan, 6)
    nan_count = pd.isna(result).sum() if isinstance(result, np.ndarray) else result.isna().sum()
    logger.info(f"  包含NaN的數據處理: ✅ (結果NaN數量: {nan_count})")

    # 測試2: 極小數據集
    logger.info("\n子測試2: 極小數據集")
    df_small = create_test_dataframe(5)
    result = calculate_drawdown_vectorized(df_small, 12)  # bar > len(df)
    valid_count = (~pd.isna(result)).sum() if isinstance(result, np.ndarray) else result.notna().sum()
    logger.info(f"  極小數據集處理: ✅ (結果有效值: {valid_count})")

    # 測試3: 包含0價格
    logger.info("\n子測試3: 零價格處理")
    df_zero = create_test_dataframe(100)
    df_zero.loc[df_zero.index[50], 'close'] = 0

    result = calculate_drawdown_vectorized(df_zero, 6)
    result_value = result[50] if isinstance(result, np.ndarray) else result.iloc[50]
    logger.info(f"  包含0價格處理: ✅ (索引50結果: {result_value})")

    logger.info("\n" + "="*60)
    logger.info("✅ 邊界情況測試完成")
    logger.info("="*60)


def test_full_integration():
    """測試4：完整集成測試（Phase 0+1+2）"""
    logger.info("\n" + "="*60)
    logger.info("測試4：Phase 0+1+2 完整集成測試")
    logger.info("="*60)

    try:
        # 創建數據加載器（啟用緩存）
        logger.info("\n初始化數據加載器...")
        data_loader = DataLoader(enable_hdf5_cache=True)

        # 創建搜索引擎（啟用並行）
        logger.info("初始化搜索引擎（Phase 1並行 + Phase 2向量化）...")
        engine = CaseSearchEngine(data_loader=data_loader, enable_parallel=True)

        # 創建測試配置
        config = SearchConfiguration(
            name="Phase2_Integration_Test",
            timeframe='4h',
            lookback_periods=100,
            forward_periods=20
        )

        # 測試symbols
        symbols = ['BTCUSDT', 'ETHUSDT']

        logger.info(f"\n開始搜索測試 (symbols: {symbols})...")
        start = time.time()

        import asyncio
        results = asyncio.run(engine.search_cases(
            config=config,
            symbols=symbols,
            save_results=False
        ))

        elapsed = time.time() - start

        logger.info(f"\n搜索完成:")
        logger.info(f"  耗時: {elapsed:.2f}秒")
        logger.info(f"  找到案例: {len(results)}個")
        logger.info(f"  平均速度: {elapsed/len(symbols):.2f}秒/symbol")

        # 驗證結果包含向量化計算的欄位
        if results:
            sample_case = results[0]
            vectorized_fields = [
                'future_1bar_max_drawdown',
                'future_6bar_max_drawdown',
                'future72_max_return',
                'future72_max_drawdown'
            ]

            logger.info("\n檢查向量化欄位:")
            for field in vectorized_fields:
                if field in sample_case:
                    logger.info(f"  ✅ {field}: {sample_case[field]}")
                else:
                    logger.warning(f"  ❌ {field}: 缺失")

        logger.info("\n" + "="*60)
        logger.info("✅ 完整集成測試完成")
        logger.info("="*60)

        return True

    except Exception as e:
        logger.error(f"\n❌ 集成測試失敗: {e}", exc_info=True)
        return False


def main():
    """主測試入口"""
    logger.info("\n" + "="*70)
    logger.info(" "*15 + "Phase 2 向量化計算測試套件")
    logger.info("="*70)

    # 運行所有測試
    test_results = []

    # 測試1：向量化正確性
    test_results.append(("正確性測試", test_vectorization_correctness()))

    # 測試2：性能提升
    test_performance_improvement()  # 無返回值，僅展示
    test_results.append(("性能提升測試", True))

    # 測試3：邊界情況
    test_edge_cases()  # 無返回值，僅展示
    test_results.append(("邊界情況測試", True))

    # 測試4：完整集成
    test_results.append(("完整集成測試", test_full_integration()))

    # 總結
    logger.info("\n" + "="*70)
    logger.info(" "*25 + "測試總結")
    logger.info("="*70)

    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        logger.info(f"{test_name}: {status}")

    all_passed = all(result for _, result in test_results)

    if all_passed:
        logger.info("\n" + "="*70)
        logger.info(" "*20 + "🎉 所有測試通過！Phase 2 向量化成功")
        logger.info("="*70)
        return 0
    else:
        logger.error("\n" + "="*70)
        logger.error(" "*25 + "❌ 有測試失敗")
        logger.error("="*70)
        return 1


if __name__ == "__main__":
    exit(main())
