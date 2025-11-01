#!/usr/bin/env python3
"""
指標計算範例

展示如何使用指標計算引擎進行各種計算場景。

使用方法：
    python3 examples/calculate_indicators_example.py

需求：
    - ETHUSDT_1h.h5 數據文件存在
    - 已安裝 pandas, pyyaml 等依賴
"""

import sys
import logging
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_basic_single_indicator():
    """範例 1: 基本單指標計算"""
    print("\n" + "="*60)
    print("範例 1: 基本單指標計算")
    print("="*60)

    from momentum.Indicators import (
        IndicatorEngine,
        EMAIndicator,
        DataSourceEnum
    )

    # 註冊 EMA 指標
    IndicatorEngine.register("ema", EMAIndicator)

    # 創建引擎
    engine = IndicatorEngine()

    # 計算 EMA
    logger.info("計算 ETHUSDT 1h 收盤價的 20 期 EMA...")
    ema = engine.calculate_indicator(
        indicator_name="ema",
        data_source=DataSourceEnum.CLOSE,
        symbol="ETHUSDT",
        timeframe="1h",
        period=20
    )

    # 顯示結果
    print(f"\n✅ EMA 計算完成:")
    print(f"   - 數據長度: {len(ema)}")
    print(f"   - 有效值數量: {ema.notna().sum()}")
    print(f"   - 最新 EMA: {ema.iloc[-1]:.2f}")
    print(f"\n最近 5 個值:")
    print(ema.tail())


def example_2_multi_period_ema():
    """範例 2: 多週期 EMA 計算"""
    print("\n" + "="*60)
    print("範例 2: 多週期 EMA 計算（20/50/100）")
    print("="*60)

    from momentum.Indicators import IndicatorEngine, EMAIndicator, DataSourceEnum
    import pandas as pd

    # 註冊並創建引擎
    IndicatorEngine.register("ema", EMAIndicator)
    engine = IndicatorEngine()

    # 計算多個週期
    periods = [20, 50, 100]
    results = {}

    logger.info("計算多週期 EMA...")
    for period in periods:
        ema = engine.calculate_indicator(
            "ema",
            DataSourceEnum.CLOSE,
            "ETHUSDT",
            "1h",
            period=period
        )
        results[f"ema_{period}"] = ema
        print(f"   ✅ EMA-{period}: {ema.notna().sum()} 個有效值")

    # 合併為 DataFrame
    df = pd.DataFrame(results)

    print(f"\n最近 5 個週期的 EMA 值:")
    print(df.tail())

    # 計算均線排列（判斷趨勢）
    latest = df.iloc[-1]
    if latest['ema_20'] > latest['ema_50'] > latest['ema_100']:
        print("\n📈 均線多頭排列（上升趨勢）")
    elif latest['ema_20'] < latest['ema_50'] < latest['ema_100']:
        print("\n📉 均線空頭排列（下降趨勢）")
    else:
        print("\n📊 均線交織（震盪行情）")


def example_3_batch_calculation():
    """範例 3: 批量計算（配置驅動）"""
    print("\n" + "="*60)
    print("範例 3: 批量計算（配置驅動）")
    print("="*60)

    from momentum.Indicators import IndicatorEngine, EMAIndicator

    # 註冊並創建引擎
    IndicatorEngine.register("ema", EMAIndicator)
    engine = IndicatorEngine()

    # 定義批量計算配置
    configs = [
        {
            "indicator": "ema",
            "data_source": "close",
            "params": {"period": 20},
            "output_name": "ema_close_20"
        },
        {
            "indicator": "ema",
            "data_source": "volume",
            "params": {"period": 20},
            "output_name": "ema_volume_20"
        },
        {
            "indicator": "ema",
            "data_source": "taker_ratio",
            "params": {"period": 20},
            "output_name": "ema_taker_ratio_20"
        }
    ]

    # 批量計算
    logger.info("執行批量計算...")
    results = engine.calculate_indicators(
        symbol="ETHUSDT",
        timeframe="1h",
        configs=configs
    )

    print(f"\n✅ 批量計算完成:")
    print(f"   - 計算了 {len(results.columns)} 個指標")
    print(f"   - 數據長度: {len(results)} 行")

    print(f"\n指標列表:")
    for col in results.columns:
        valid_count = results[col].notna().sum()
        print(f"   - {col}: {valid_count} 個有效值")

    print(f"\n最近 5 個值:")
    print(results.tail())


def example_4_config_file_based():
    """範例 4: 使用配置文件"""
    print("\n" + "="*60)
    print("範例 4: 使用 YAML 配置文件")
    print("="*60)

    from momentum.Indicators import (
        IndicatorEngine,
        EMAIndicator,
        ConfigLoader
    )

    # 註冊指標
    IndicatorEngine.register("ema", EMAIndicator)
    engine = IndicatorEngine()

    # 載入配置文件
    logger.info("載入配置文件...")
    loader = ConfigLoader()
    loader.load_config()

    # 列出所有可用指標
    indicators = loader.list_indicators()
    print(f"\n配置文件中的指標: {indicators}")

    # 獲取 EMA 信息
    ema_info = loader.get_indicator_info("ema")
    print(f"\nEMA 指標信息:")
    print(f"   - 類名: {ema_info['class_name']}")
    print(f"   - 描述: {ema_info['description']}")
    print(f"   - 默認參數: {ema_info['default_params']}")
    print(f"   - 參數範圍: {ema_info['param_ranges']['period']}")

    # 列出預設配置
    presets = loader.list_calculation_presets()
    print(f"\n可用的預設配置: {presets}")

    # 使用預設配置計算
    logger.info("使用預設配置 'ema_multi_period' 計算...")
    preset_configs = loader.get_calculation_preset("ema_multi_period")
    results = engine.calculate_indicators("ETHUSDT", "1h", preset_configs)

    print(f"\n✅ 預設配置計算完成:")
    print(f"   - 指標: {list(results.columns)}")
    print(f"\n最近 5 個值:")
    print(results.tail())


def example_5_combine_with_klines():
    """範例 5: 與 K 線數據結合"""
    print("\n" + "="*60)
    print("範例 5: 將指標合併到 K 線數據")
    print("="*60)

    from momentum.Indicators import IndicatorEngine, EMAIndicator, DataSourceEnum
    from momentum.DataExtraction.kline_storage import KlineStorageManager

    # 註冊指標
    IndicatorEngine.register("ema", EMAIndicator)
    engine = IndicatorEngine()

    # 讀取 K 線數據
    logger.info("讀取 K 線數據...")
    storage = KlineStorageManager()
    df_klines = storage.read_klines("ETHUSDT", "1h")

    print(f"\nK 線數據:")
    print(f"   - 數據長度: {len(df_klines)}")
    print(f"   - 時間範圍: {df_klines['timestamp'].min()} ~ {df_klines['timestamp'].max()}")
    print(f"   - 列: {list(df_klines.columns)}")

    # 計算多個 EMA
    logger.info("計算 EMA 指標...")
    periods = [20, 50]
    for period in periods:
        ema = engine.calculate_indicator(
            "ema",
            DataSourceEnum.CLOSE,
            "ETHUSDT",
            "1h",
            period=period
        )
        df_klines[f'ema_{period}'] = ema.values  # 使用 .values 對齊索引

    # 顯示合併後的數據
    print(f"\n✅ 指標已添加到 K 線數據:")
    print(f"   - 新增列: {[col for col in df_klines.columns if 'ema' in col]}")

    print(f"\n最近 5 根 K 線（含指標）:")
    print(df_klines[['timestamp', 'close', 'ema_20', 'ema_50']].tail())

    # 分析：找出金叉/死叉點
    logger.info("分析均線交叉...")
    df_klines['ema_diff'] = df_klines['ema_20'] - df_klines['ema_50']
    df_klines['ema_cross'] = df_klines['ema_diff'].diff()

    # 金叉：從負變正
    golden_cross = df_klines[(df_klines['ema_diff'] > 0) & (df_klines['ema_cross'] > 0)]
    # 死叉：從正變負
    death_cross = df_klines[(df_klines['ema_diff'] < 0) & (df_klines['ema_cross'] < 0)]

    print(f"\n📊 均線交叉分析:")
    print(f"   - 金叉（買入信號）次數: {len(golden_cross)}")
    print(f"   - 死叉（賣出信號）次數: {len(death_cross)}")

    if len(golden_cross) > 0:
        print(f"\n最近一次金叉:")
        print(golden_cross[['timestamp', 'close', 'ema_20', 'ema_50']].tail(1))


def example_6_performance_test():
    """範例 6: 性能測試"""
    print("\n" + "="*60)
    print("範例 6: 性能測試")
    print("="*60)

    from momentum.Indicators import IndicatorEngine, EMAIndicator, DataSourceEnum
    import time

    # 註冊並創建引擎
    IndicatorEngine.register("ema", EMAIndicator)
    engine = IndicatorEngine()

    # 測試單次計算
    logger.info("測試單次計算性能...")
    start = time.time()
    ema = engine.calculate_indicator(
        "ema",
        DataSourceEnum.CLOSE,
        "ETHUSDT",
        "1h",
        period=20
    )
    elapsed = (time.time() - start) * 1000

    print(f"\n單次計算:")
    print(f"   - 數據量: {len(ema)} 根 K 線")
    print(f"   - 耗時: {elapsed:.2f} ms")
    print(f"   - 平均: {elapsed/len(ema):.4f} ms/根")

    # 測試批量計算
    configs = [
        {"indicator": "ema", "data_source": "close", "params": {"period": p}}
        for p in [10, 20, 30, 50, 100]
    ]

    logger.info("測試批量計算性能...")
    start = time.time()
    results = engine.calculate_indicators("ETHUSDT", "1h", configs)
    elapsed = (time.time() - start) * 1000

    print(f"\n批量計算 ({len(configs)} 個指標):")
    print(f"   - 總耗時: {elapsed:.2f} ms")
    print(f"   - 平均: {elapsed/len(configs):.2f} ms/指標")

    # 查看緩存效果
    stats = engine.get_stats()
    print(f"\n引擎統計:")
    print(f"   - 已註冊指標: {stats['registered_indicators']}")
    print(f"   - 緩存大小: {stats['cache_size']}")


def main():
    """運行所有範例"""
    print("\n" + "="*60)
    print("指標計算引擎 - 完整範例演示")
    print("="*60)

    try:
        # 運行所有範例
        example_1_basic_single_indicator()
        example_2_multi_period_ema()
        example_3_batch_calculation()
        example_4_config_file_based()
        example_5_combine_with_klines()
        example_6_performance_test()

        # 總結
        print("\n" + "="*60)
        print("✅ 所有範例運行完成！")
        print("="*60)
        print("\n下一步:")
        print("  1. 查看 docs/indicator_api_usage.md 了解更多 API")
        print("  2. 查看 docs/indicator_extension_guide.md 學習添加新指標")
        print("  3. 修改 config/indicators.yaml 自定義配置")

    except FileNotFoundError as e:
        logger.error(f"數據文件不存在: {e}")
        print("\n❌ 請確保 ETHUSDT_1h.h5 數據文件存在")
        print("   路徑: momentum/DataExtraction/data/ETHUSDT_1h.h5")
        sys.exit(1)
    except Exception as e:
        logger.error(f"範例運行失敗: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
