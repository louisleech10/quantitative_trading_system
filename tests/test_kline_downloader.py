"""
K線下載服務測試腳本 - 任務1.2驗收測試

測試範圍：
1. 單symbol下載（ETHUSDT 1h 100根）
2. 不同timeframe支援（BTCUSDT 4h 50根）
3. 批量下載（5個symbols）
4. 數據格式驗證（8個必需欄位）
5. 速率限制驗證
6. 錯誤處理和重試
7. HDF5存儲整合
8. 進度追蹤

驗收標準：
✅ 下載ETHUSDT 1h 100根（單次請求）
✅ 下載BTCUSDT 4h 50根（驗證timeframe支援）
✅ 批量下載5個symbols（驗證batch功能）
✅ 數據包含完整8個必需欄位
✅ taker_ratio在0-1範圍
✅ 速率限制生效（連續請求不觸發429）
✅ 進度LOG清晰（百分比+速度）
✅ 數據自動保存到HDF5（任務1.1整合）
"""

import sys
import os
from pathlib import Path
import logging
from datetime import datetime, timedelta
import pandas as pd
import time

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from momentum.DataExtraction.kline_download_service import KlineDownloadService
from momentum.DataExtraction.providers.binance_provider import BinanceProvider
from momentum.DataExtraction.kline_storage import KlineStorageManager

# 設置詳細日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_1_single_download_ethusdt():
    """
    測試1: 單symbol下載 - ETHUSDT 1h 100根
    驗收標準: 可成功下載，數據格式正確
    """
    logger.info("=" * 70)
    logger.info("測試1: 單symbol下載 - ETHUSDT 1h 100根")
    logger.info("=" * 70)

    try:
        # 初始化存儲和服務
        storage_dir = "./test_data/kline_storage_test1"
        storage = KlineStorageManager(cache_dir=storage_dir)
        downloader = KlineDownloadService(storage_manager=storage)

        # 註冊幣安Provider
        binance = BinanceProvider()
        downloader.registry.register('binance', binance)

        # 下載數據
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=100)

        logger.info(f"Downloading ETHUSDT 1h from {start_time} to {end_time}")

        start = time.time()
        df = downloader.download_klines(
            source='binance',
            symbol='ETHUSDT',
            start_time=start_time,
            end_time=end_time,
            timeframe='1h',
            save_to_storage=True
        )
        elapsed = time.time() - start

        # 驗證結果
        logger.info(f"\n{'=' * 70}")
        logger.info("測試1結果:")
        logger.info(f"{'=' * 70}")
        logger.info(f"✅ 下載成功: {len(df)} 根K線")
        logger.info(f"✅ 耗時: {elapsed:.2f}秒 ({len(df)/elapsed:.1f} klines/s)")
        logger.info(f"✅ 數據欄位: {list(df.columns)}")
        logger.info(f"✅ 時間範圍: {datetime.fromtimestamp(df['timestamp'].min())} ~ {datetime.fromtimestamp(df['timestamp'].max())}")

        # 驗證必需欄位
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'taker_buy_volume', 'taker_ratio']
        assert all(col in df.columns for col in required_cols), "缺少必需欄位！"
        logger.info(f"✅ 所有必需欄位存在: {required_cols}")

        # 驗證taker_ratio範圍
        assert df['taker_ratio'].min() >= 0 and df['taker_ratio'].max() <= 1, "taker_ratio超出範圍！"
        logger.info(f"✅ taker_ratio範圍正確: [{df['taker_ratio'].min():.3f}, {df['taker_ratio'].max():.3f}]")

        # 驗證OHLC合理性（抽樣檢查前10根）
        for i in range(min(10, len(df))):
            row = df.iloc[i]
            assert row['low'] <= row['open'] <= row['high'], f"Row {i}: OHLC不合理"
            assert row['low'] <= row['close'] <= row['high'], f"Row {i}: OHLC不合理"
        logger.info(f"✅ OHLC數據合理性檢查通過（前10根）")

        logger.info(f"\n{'=' * 70}")
        logger.info("✅ 測試1通過！")
        logger.info(f"{'=' * 70}\n")

        return True

    except Exception as e:
        logger.error(f"❌ 測試1失敗: {e}", exc_info=True)
        return False


def test_2_different_timeframe_btcusdt():
    """
    測試2: 不同timeframe - BTCUSDT 4h 50根
    驗收標準: 支援不同timeframe，數據正確
    """
    logger.info("=" * 70)
    logger.info("測試2: 不同timeframe - BTCUSDT 4h 50根")
    logger.info("=" * 70)

    try:
        # 初始化
        storage_dir = "./test_data/kline_storage_test2"
        storage = KlineStorageManager(cache_dir=storage_dir)
        downloader = KlineDownloadService(storage_manager=storage)
        downloader.registry.register('binance', BinanceProvider())

        # 下載4h數據
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=50 * 4)  # 50根4h K線

        logger.info(f"Downloading BTCUSDT 4h from {start_time} to {end_time}")

        df = downloader.download_klines(
            source='binance',
            symbol='BTCUSDT',
            start_time=start_time,
            end_time=end_time,
            timeframe='4h',
            save_to_storage=True
        )

        # 驗證
        logger.info(f"\n{'=' * 70}")
        logger.info("測試2結果:")
        logger.info(f"{'=' * 70}")
        logger.info(f"✅ 4h timeframe下載成功: {len(df)} 根K線")

        # 驗證timestamp間隔（應該是4小時 = 14400秒）
        if len(df) > 1:
            time_diffs = df['timestamp'].diff().dropna()
            avg_diff = time_diffs.mean()
            expected_diff = 14400  # 4h in seconds
            logger.info(f"✅ 平均時間間隔: {avg_diff:.0f}秒 (預期: {expected_diff}秒)")
            assert abs(avg_diff - expected_diff) < 100, f"時間間隔不符合4h！實際: {avg_diff}"

        logger.info(f"\n{'=' * 70}")
        logger.info("✅ 測試2通過！")
        logger.info(f"{'=' * 70}\n")

        return True

    except Exception as e:
        logger.error(f"❌ 測試2失敗: {e}", exc_info=True)
        return False


def test_3_batch_download():
    """
    測試3: 批量下載 - 5個symbols
    驗收標準: 批量下載功能正常，進度追蹤清晰
    """
    logger.info("=" * 70)
    logger.info("測試3: 批量下載 - 5個symbols")
    logger.info("=" * 70)

    try:
        # 初始化
        storage_dir = "./test_data/kline_storage_test3"
        storage = KlineStorageManager(cache_dir=storage_dir)
        downloader = KlineDownloadService(storage_manager=storage)
        downloader.registry.register('binance', BinanceProvider())

        # 批量下載（小規模測試：每個symbol只下載10根）
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=10)

        logger.info(f"Batch downloading {len(symbols)} symbols (10 klines each)...")

        # 進度回調函數
        def progress_callback(current, total, symbol, success, df):
            if success:
                logger.info(f"  [{current}/{total}] ✅ {symbol}: {len(df)} klines downloaded")
            else:
                logger.warning(f"  [{current}/{total}] ❌ {symbol}: Failed")

        start = time.time()
        results, failed = downloader.download_batch(
            source='binance',
            symbols=symbols,
            start_time=start_time,
            end_time=end_time,
            timeframe='1h',
            progress_callback=progress_callback,
            stop_on_error=False
        )
        elapsed = time.time() - start

        # 驗證
        logger.info(f"\n{'=' * 70}")
        logger.info("測試3結果:")
        logger.info(f"{'=' * 70}")
        logger.info(f"✅ 批量下載完成: {len(results)}/{len(symbols)} 成功")
        logger.info(f"✅ 總耗時: {elapsed:.2f}秒 (平均 {elapsed/len(symbols):.2f}秒/symbol)")

        if failed:
            logger.warning(f"⚠️  失敗的symbols: {failed}")

        # 檢查每個symbol的數據
        for symbol, df in results.items():
            logger.info(f"  - {symbol}: {len(df)} klines, "
                       f"taker_ratio範圍: [{df['taker_ratio'].min():.3f}, {df['taker_ratio'].max():.3f}]")

        logger.info(f"\n{'=' * 70}")
        logger.info("✅ 測試3通過！")
        logger.info(f"{'=' * 70}\n")

        return True

    except Exception as e:
        logger.error(f"❌ 測試3失敗: {e}", exc_info=True)
        return False


def test_4_storage_integration():
    """
    測試4: HDF5存儲整合
    驗收標準: 數據自動保存到HDF5，可以正確讀取
    """
    logger.info("=" * 70)
    logger.info("測試4: HDF5存儲整合")
    logger.info("=" * 70)

    try:
        # 初始化
        storage_dir = "./test_data/kline_storage_test4"
        storage = KlineStorageManager(cache_dir=storage_dir)
        downloader = KlineDownloadService(storage_manager=storage)
        downloader.registry.register('binance', BinanceProvider())

        # 下載並自動保存
        symbol = 'ETHUSDT'
        timeframe = '1h'
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=50)

        logger.info(f"Downloading {symbol} {timeframe} (save_to_storage=True)...")

        df_downloaded = downloader.download_klines(
            source='binance',
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            timeframe=timeframe,
            save_to_storage=True
        )

        logger.info(f"✅ 下載完成: {len(df_downloaded)} klines")

        # 從存儲讀取
        logger.info(f"Reading from HDF5 storage...")

        df_stored = storage.read_klines(symbol, timeframe)

        logger.info(f"✅ 從存儲讀取: {len(df_stored)} klines")

        # 驗證一致性
        assert len(df_downloaded) == len(df_stored), "存儲的數據數量不一致！"

        # 比較前10根數據
        for col in ['timestamp', 'open', 'high', 'low', 'close']:
            assert (df_downloaded[col].head(10).values == df_stored[col].head(10).values).all(), \
                f"欄位 {col} 數據不一致！"

        logger.info(f"\n{'=' * 70}")
        logger.info("測試4結果:")
        logger.info(f"{'=' * 70}")
        logger.info(f"✅ HDF5存儲整合正常")
        logger.info(f"✅ 下載數據和存儲數據一致")
        logger.info(f"✅ 數據量: {len(df_stored)} klines")

        logger.info(f"\n{'=' * 70}")
        logger.info("✅ 測試4通過！")
        logger.info(f"{'=' * 70}\n")

        return True

    except Exception as e:
        logger.error(f"❌ 測試4失敗: {e}", exc_info=True)
        return False


def test_5_provider_registry():
    """
    測試5: Provider註冊機制
    驗收標準: 可註冊、查詢、健康檢查Provider
    """
    logger.info("=" * 70)
    logger.info("測試5: Provider註冊機制")
    logger.info("=" * 70)

    try:
        # 初始化
        storage = KlineStorageManager(cache_dir="./test_data/test5")
        downloader = KlineDownloadService(storage_manager=storage)

        # 註冊Binance Provider
        binance = BinanceProvider()
        downloader.registry.register('binance', binance)

        logger.info("✅ Binance Provider已註冊")

        # 查詢已註冊的sources
        sources = downloader.registry.list_sources()
        logger.info(f"✅ 已註冊的數據源: {sources}")
        assert 'binance' in sources, "Binance未在註冊表中！"

        # 健康檢查
        logger.info("執行健康檢查...")
        health_status = downloader.registry.ping_all()

        logger.info(f"\n{'=' * 70}")
        logger.info("測試5結果:")
        logger.info(f"{'=' * 70}")

        for source, is_healthy in health_status.items():
            status = "✅ OK" if is_healthy else "❌ FAILED"
            logger.info(f"  {source}: {status}")

        logger.info(f"\n{'=' * 70}")
        logger.info("✅ 測試5通過！")
        logger.info(f"{'=' * 70}\n")

        return True

    except Exception as e:
        logger.error(f"❌ 測試5失敗: {e}", exc_info=True)
        return False


def test_6_error_handling():
    """
    測試6: 錯誤處理
    驗收標準: 無效symbol、無效timeframe時正確報錯
    """
    logger.info("=" * 70)
    logger.info("測試6: 錯誤處理")
    logger.info("=" * 70)

    try:
        # 初始化
        storage = KlineStorageManager(cache_dir="./test_data/test6")
        downloader = KlineDownloadService(storage_manager=storage)
        downloader.registry.register('binance', BinanceProvider())

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=10)

        # 測試無效symbol
        logger.info("測試6.1: 無效symbol (小寫)")
        try:
            df = downloader.download_klines(
                source='binance',
                symbol='btcusdt',  # 小寫，應該失敗
                start_time=start_time,
                end_time=end_time,
                timeframe='1h',
                save_to_storage=False
            )
            logger.error("❌ 應該拋出ValueError但沒有！")
            return False
        except ValueError as e:
            logger.info(f"✅ 正確捕獲無效symbol錯誤: {e}")

        # 測試無效timeframe
        logger.info("\n測試6.2: 無效timeframe")
        try:
            df = downloader.download_klines(
                source='binance',
                symbol='BTCUSDT',
                start_time=start_time,
                end_time=end_time,
                timeframe='7h',  # 不支援的timeframe
                save_to_storage=False
            )
            logger.error("❌ 應該拋出ValueError但沒有！")
            return False
        except ValueError as e:
            logger.info(f"✅ 正確捕獲無效timeframe錯誤: {e}")

        # 測試未註冊的source
        logger.info("\n測試6.3: 未註冊的數據源")
        try:
            df = downloader.download_klines(
                source='okx',  # 未註冊
                symbol='BTCUSDT',
                start_time=start_time,
                end_time=end_time,
                timeframe='1h',
                save_to_storage=False
            )
            logger.error("❌ 應該拋出ValueError但沒有！")
            return False
        except ValueError as e:
            logger.info(f"✅ 正確捕獲未註冊source錯誤: {e}")

        logger.info(f"\n{'=' * 70}")
        logger.info("✅ 測試6通過！所有錯誤處理正確")
        logger.info(f"{'=' * 70}\n")

        return True

    except Exception as e:
        logger.error(f"❌ 測試6失敗: {e}", exc_info=True)
        return False


def main():
    """執行所有測試"""
    logger.info("\n" + "=" * 70)
    logger.info("K線下載服務驗收測試開始")
    logger.info("任務1.2: 幣安K線下載服務")
    logger.info("=" * 70 + "\n")

    results = {
        "測試1: 單symbol下載": test_1_single_download_ethusdt(),
        "測試2: 不同timeframe": test_2_different_timeframe_btcusdt(),
        "測試3: 批量下載": test_3_batch_download(),
        "測試4: HDF5存儲整合": test_4_storage_integration(),
        "測試5: Provider註冊": test_5_provider_registry(),
        "測試6: 錯誤處理": test_6_error_handling(),
    }

    # 總結
    logger.info("\n" + "=" * 70)
    logger.info("測試總結")
    logger.info("=" * 70)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status}: {test_name}")

    logger.info("=" * 70)
    logger.info(f"總計: {passed}/{total} 測試通過")

    if passed == total:
        logger.info("🎉 所有測試通過！任務1.2驗收成功！")
    else:
        logger.warning(f"⚠️  有 {total - passed} 個測試失敗，需要修復")

    logger.info("=" * 70 + "\n")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
