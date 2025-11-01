#!/usr/bin/env python3
"""
Phase 3.2 任務使用範例

展示如何使用指標計算引擎為 Phase 3.2（信號密度分析）提供數據。

使用方法：
    python3 examples/phase3_2_usage_example.py
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
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def prepare_indicators_for_signal_density_analysis():
    """
    為 Phase 3.2 準備指標數據

    流程：
    1. 載入配置文件
    2. 使用預設的 "full_indicator_set" 配置
    3. 批量計算所有指標
    4. 返回 DataFrame 供後續分析
    """
    from momentum.Indicators import (
        IndicatorEngine,
        EMAIndicator,
        ConfigLoader
    )

    print("="*60)
    print("Phase 3.2 - 準備指標數據")
    print("="*60)

    # 步驟 1: 註冊指標
    logger.info("註冊指標...")
    IndicatorEngine.register("ema", EMAIndicator)
    engine = IndicatorEngine()

    # 步驟 2: 載入配置
    logger.info("載入配置文件...")
    loader = ConfigLoader()
    loader.load_config()

    # 步驟 3: 獲取完整指標集配置
    logger.info("獲取 'full_indicator_set' 預設配置...")
    configs = loader.get_calculation_preset("full_indicator_set")
    print(f"\n將計算 {len(configs)} 個指標:")
    for i, config in enumerate(configs, 1):
        print(f"  {i}. {config.get('output_name', 'N/A')}")

    # 步驟 4: 批量計算指標
    symbol = "ETHUSDT"
    timeframe = "1h"

    logger.info(f"批量計算 {symbol} {timeframe} 的所有指標...")
    indicators_df = engine.calculate_indicators(
        symbol=symbol,
        timeframe=timeframe,
        configs=configs
    )

    # 步驟 5: 檢查結果
    print(f"\n✅ 指標計算完成:")
    print(f"   - 指標數量: {len(indicators_df.columns)}")
    print(f"   - 數據長度: {len(indicators_df)} 根 K 線")
    print(f"   - 指標列表: {list(indicators_df.columns)}")

    # 顯示統計信息
    print(f"\n各指標有效值數量:")
    for col in indicators_df.columns:
        valid_count = indicators_df[col].notna().sum()
        valid_pct = (valid_count / len(indicators_df)) * 100
        print(f"   - {col}: {valid_count} ({valid_pct:.1f}%)")

    # 顯示最近 5 個值
    print(f"\n最近 5 根 K 線的指標值:")
    print(indicators_df.tail())

    return indicators_df


def combine_with_kline_data():
    """
    將指標與 K 線數據合併（完整的分析數據集）
    """
    from momentum.Indicators import IndicatorEngine, EMAIndicator, ConfigLoader
    from momentum.DataExtraction.kline_storage import KlineStorageManager

    print("\n" + "="*60)
    print("合併指標與 K 線數據")
    print("="*60)

    # 註冊指標
    IndicatorEngine.register("ema", EMAIndicator)
    engine = IndicatorEngine()

    # 載入配置
    loader = ConfigLoader()
    loader.load_config()

    # 讀取 K 線數據
    logger.info("讀取 K 線數據...")
    storage = KlineStorageManager()
    symbol = "ETHUSDT"
    timeframe = "1h"
    df_klines = storage.read_klines(symbol, timeframe)

    print(f"\nK 線數據:")
    print(f"   - 數據長度: {len(df_klines)}")
    print(f"   - 原始列: {list(df_klines.columns)}")

    # 計算指標
    logger.info("計算指標...")
    configs = loader.get_calculation_preset("full_indicator_set")
    indicators_df = engine.calculate_indicators(symbol, timeframe, configs)

    # 合併數據
    logger.info("合併 K 線與指標數據...")
    # 方式 1: 使用 join（推薦）
    # df_combined = df_klines.join(indicators_df)

    # 方式 2: 逐列添加（更清晰）
    for col in indicators_df.columns:
        df_klines[col] = indicators_df[col].values

    print(f"\n✅ 數據合併完成:")
    print(f"   - 總列數: {len(df_klines.columns)}")
    print(f"   - K 線列: {8}（timestamp, open, high, low, close, volume, taker_buy_volume, taker_ratio）")
    print(f"   - 指標列: {len(indicators_df.columns)}")

    # 顯示合併後的數據
    print(f"\n完整數據集（前 3 列 + 指標）:")
    cols_to_show = ['timestamp', 'close', 'volume'] + list(indicators_df.columns)
    print(df_klines[cols_to_show].tail())

    return df_klines


def calculate_for_multiple_symbols():
    """
    為多個交易對計算指標（批量處理）
    """
    from momentum.Indicators import IndicatorEngine, EMAIndicator, ConfigLoader

    print("\n" + "="*60)
    print("多交易對批量計算")
    print("="*60)

    # 註冊指標
    IndicatorEngine.register("ema", EMAIndicator)
    engine = IndicatorEngine()

    # 載入配置
    loader = ConfigLoader()
    loader.load_config()
    configs = loader.get_calculation_preset("full_indicator_set")

    # 交易對列表（根據實際可用數據調整）
    symbols = ["ETHUSDT"]  # 可以添加更多: "BTCUSDT", "BNBUSDT" 等
    timeframe = "1h"

    all_results = {}

    for symbol in symbols:
        try:
            logger.info(f"計算 {symbol} 的指標...")
            indicators_df = engine.calculate_indicators(
                symbol=symbol,
                timeframe=timeframe,
                configs=configs
            )
            all_results[symbol] = indicators_df
            print(f"   ✅ {symbol}: {len(indicators_df.columns)} 個指標, {len(indicators_df)} 根 K 線")
        except Exception as e:
            logger.error(f"   ❌ {symbol}: {e}")

    print(f"\n✅ 批量計算完成:")
    print(f"   - 成功: {len(all_results)}/{len(symbols)} 個交易對")

    return all_results


def export_to_csv_for_analysis():
    """
    導出指標數據為 CSV（方便外部分析工具使用）
    """
    from momentum.Indicators import IndicatorEngine, EMAIndicator, ConfigLoader
    from momentum.DataExtraction.kline_storage import KlineStorageManager
    import pandas as pd

    print("\n" + "="*60)
    print("導出數據為 CSV")
    print("="*60)

    # 註冊指標
    IndicatorEngine.register("ema", EMAIndicator)
    engine = IndicatorEngine()

    # 載入配置並計算
    loader = ConfigLoader()
    loader.load_config()
    configs = loader.get_calculation_preset("full_indicator_set")

    # 讀取 K 線並計算指標
    storage = KlineStorageManager()
    df_klines = storage.read_klines("ETHUSDT", "1h")
    indicators_df = engine.calculate_indicators("ETHUSDT", "1h", configs)

    # 合併數據
    for col in indicators_df.columns:
        df_klines[col] = indicators_df[col].values

    # 導出
    output_path = project_root / "examples" / "ethusdt_1h_with_indicators.csv"
    logger.info(f"導出到: {output_path}")
    df_klines.to_csv(output_path, index=False)

    print(f"\n✅ 數據已導出:")
    print(f"   - 文件: {output_path}")
    print(f"   - 行數: {len(df_klines)}")
    print(f"   - 列數: {len(df_klines.columns)}")
    print(f"\n可以使用以下方式讀取:")
    print(f"   import pandas as pd")
    print(f"   df = pd.read_csv('{output_path}')")


def main():
    """主函數"""
    print("\n" + "="*60)
    print("Phase 3.2 指標計算引擎使用演示")
    print("="*60)
    print("\n這個範例展示如何為 Phase 3.2（信號密度分析）準備數據\n")

    try:
        # 範例 1: 準備指標數據
        indicators_df = prepare_indicators_for_signal_density_analysis()

        # 範例 2: 與 K 線數據合併
        df_combined = combine_with_kline_data()

        # 範例 3: 多交易對批量計算
        # all_results = calculate_for_multiple_symbols()

        # 範例 4: 導出為 CSV
        # export_to_csv_for_analysis()

        # 總結
        print("\n" + "="*60)
        print("✅ Phase 3.2 數據準備完成")
        print("="*60)
        print("\n下一步（Phase 3.2 任務）:")
        print("  1. 使用 indicators_df 或 df_combined 進行信號密度分析")
        print("  2. 計算每個指標的信號觸發頻率")
        print("  3. 分析信號重疊區域")
        print("  4. 生成信號密度熱力圖")

    except FileNotFoundError as e:
        logger.error(f"數據文件不存在: {e}")
        print("\n❌ 請確保 ETHUSDT_1h.h5 數據文件存在")
        sys.exit(1)
    except Exception as e:
        logger.error(f"運行失敗: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
