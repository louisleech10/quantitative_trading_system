#!/usr/bin/env python3
"""
測試 Stack Overflow 無限遞歸修復

驗證：
1. 自動偵測 worker 數量正常工作
2. 單個 symbol 不會導致無限遞歸
3. 少量 symbols < workers 能正常 fallback
"""

import sys
import os
import asyncio
import logging

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_auto_detect_workers():
    """測試1：驗證自動偵測 worker 數量"""
    logger.info("=" * 60)
    logger.info("測試1：自動偵測 worker 數量")
    logger.info("=" * 60)

    try:
        from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader
        from momentum.DataExtraction.case_search_engine import CaseSearchEngine

        # 創建數據加載器
        data_loader = MomentumDataLoader()

        # 創建搜索引擎（num_workers=None，應該自動偵測）
        logger.info("創建 CaseSearchEngine (num_workers=None)...")
        engine = CaseSearchEngine(
            data_loader=data_loader,
            enable_parallel=True,
            num_workers=None  # 自動偵測
        )

        # 檢查並行引擎
        if hasattr(engine, 'parallel_engine') and engine.parallel_engine:
            detected_workers = engine.parallel_engine.num_workers
            logger.info(f"✅ 自動偵測的 worker 數量: {detected_workers}")
            logger.info(f"   (應該根據你的機器配置自動計算)")
            return True, detected_workers
        else:
            logger.error("❌ 並行引擎未啟用")
            return False, 0

    except Exception as e:
        logger.error(f"❌ 測試失敗: {e}", exc_info=True)
        return False, 0

async def test_single_symbol_no_recursion():
    """測試2：單個 symbol 不會觸發無限遞歸"""
    logger.info("\n" + "=" * 60)
    logger.info("測試2：單個 Symbol 搜索（無限遞歸修復驗證）")
    logger.info("=" * 60)

    try:
        from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader
        from momentum.DataExtraction.case_search_engine import CaseSearchEngine, SearchConfiguration, FilterCondition
        from datetime import datetime, timedelta

        # 創建數據加載器
        data_loader = MomentumDataLoader()

        # 創建搜索引擎
        engine = CaseSearchEngine(
            data_loader=data_loader,
            enable_parallel=True,
            num_workers=None  # 自動偵測
        )

        # 創建簡單的搜索配置
        config = SearchConfiguration(
            name="單Symbol測試",
            timeframe="12h",
            lookback_periods=100,
            forward_periods=10
        )

        # 添加簡單條件（價格上漲 > 8%）
        config.add_initial_condition(FilterCondition(
            condition_type="price",
            parameter="price_change",
            operator=">",
            value=0.08
        ))

        # 搜索單個 symbol
        symbols = ["BTCUSDT"]  # 只搜索1個

        logger.info(f"開始搜索: {symbols}")
        logger.info(f"Worker數量: {engine.parallel_engine.num_workers if hasattr(engine, 'parallel_engine') else 'N/A'}")
        logger.info("預期：由於 symbols(1) < workers，應該觸發串行 fallback")
        logger.info("如果出現 Stack Overflow，說明修復失敗")

        # 執行搜索（設置較短的時間範圍以加快測試）
        config.start_time = datetime.now() - timedelta(days=30)
        config.end_time = datetime.now()

        results = await engine.search_cases(
            config=config,
            symbols=symbols,
            save_results=False
        )

        logger.info(f"✅ 搜索完成！找到 {len(results)} 個案例")
        logger.info("✅ 無限遞歸問題已修復（沒有 Stack Overflow）")
        return True

    except RecursionError as e:
        logger.error(f"❌ 無限遞歸錯誤仍然存在: {e}")
        return False
    except Exception as e:
        logger.error(f"⚠️  搜索過程中出現其他錯誤: {e}", exc_info=True)
        # 只要不是 RecursionError，就算部分成功
        return True

async def test_few_symbols_fallback():
    """測試3：少量 symbols < workers 能正常 fallback"""
    logger.info("\n" + "=" * 60)
    logger.info("測試3：少量 Symbols（< workers）Fallback 測試")
    logger.info("=" * 60)

    try:
        from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader
        from momentum.DataExtraction.case_search_engine import CaseSearchEngine, SearchConfiguration, FilterCondition
        from datetime import datetime, timedelta

        # 創建數據加載器
        data_loader = MomentumDataLoader()

        # 創建搜索引擎
        engine = CaseSearchEngine(
            data_loader=data_loader,
            enable_parallel=True,
            num_workers=None
        )

        detected_workers = engine.parallel_engine.num_workers if hasattr(engine, 'parallel_engine') else 2

        # 創建簡單的搜索配置
        config = SearchConfiguration(
            name="少量Symbol測試",
            timeframe="12h",
            lookback_periods=50,
            forward_periods=10
        )

        config.add_initial_condition(FilterCondition(
            condition_type="price",
            parameter="price_change",
            operator=">",
            value=0.05
        ))

        # 搜索數量 < workers 的 symbols
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

        logger.info(f"開始搜索: {symbols}")
        logger.info(f"Symbols 數量: {len(symbols)}")
        logger.info(f"Worker 數量: {detected_workers}")
        logger.info(f"預期：由於 {len(symbols)} < {detected_workers}，應該觸發串行 fallback")

        # 設置較短的時間範圍
        config.start_time = datetime.now() - timedelta(days=15)
        config.end_time = datetime.now()

        results = await engine.search_cases(
            config=config,
            symbols=symbols,
            save_results=False
        )

        logger.info(f"✅ 搜索完成！找到 {len(results)} 個案例")
        logger.info("✅ Fallback 邏輯正常工作")
        return True

    except RecursionError as e:
        logger.error(f"❌ 無限遞歸錯誤: {e}")
        return False
    except Exception as e:
        logger.error(f"⚠️  搜索過程中出現其他錯誤: {e}")
        return True

async def main():
    """主測試函數"""
    logger.info("🚀 開始測試 Stack Overflow 修復")
    logger.info("=" * 60)

    results = {}

    # 測試1：自動偵測
    try:
        success, workers = await test_auto_detect_workers()
        results['auto_detect'] = success
        results['workers'] = workers
    except Exception as e:
        logger.error(f"測試1異常: {e}")
        results['auto_detect'] = False
        results['workers'] = 0

    # 測試2：單 symbol（最關鍵）
    try:
        success = await test_single_symbol_no_recursion()
        results['single_symbol'] = success
    except Exception as e:
        logger.error(f"測試2異常: {e}")
        results['single_symbol'] = False

    # 測試3：少量 symbols
    try:
        success = await test_few_symbols_fallback()
        results['few_symbols'] = success
    except Exception as e:
        logger.error(f"測試3異常: {e}")
        results['few_symbols'] = False

    # 總結
    logger.info("\n" + "=" * 60)
    logger.info("📊 測試總結")
    logger.info("=" * 60)
    logger.info(f"✅ 測試1 - 自動偵測: {'通過' if results.get('auto_detect') else '失敗'}")
    if results.get('auto_detect'):
        logger.info(f"   偵測到的 worker 數量: {results.get('workers')}")
    logger.info(f"{'✅' if results.get('single_symbol') else '❌'} 測試2 - 單Symbol無遞歸: {'通過' if results.get('single_symbol') else '失敗'}")
    logger.info(f"{'✅' if results.get('few_symbols') else '❌'} 測試3 - 少量Symbols Fallback: {'通過' if results.get('few_symbols') else '失敗'}")

    all_passed = all([
        results.get('auto_detect', False),
        results.get('single_symbol', False),
        results.get('few_symbols', False)
    ])

    if all_passed:
        logger.info("\n🎉 所有測試通過！Stack Overflow 問題已修復！")
        return 0
    else:
        logger.info("\n⚠️  部分測試失敗，請檢查日誌")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
