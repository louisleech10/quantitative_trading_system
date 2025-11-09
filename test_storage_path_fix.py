"""
測試存儲路徑修復
驗證批次下載使用統一的存儲路徑，數據不會互相覆蓋
"""
import sys
from pathlib import Path
import time

# 添加項目路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.core.config import settings
from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.DataExtraction.kline_download_service import KlineDownloadService
from momentum.DataExtraction.providers.binance_provider import BinanceProvider
from datetime import datetime
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_unified_storage_path():
    """測試統一存儲路徑"""
    
    logger.info("=" * 80)
    logger.info("測試場景：批次下載使用統一存儲路徑")
    logger.info("=" * 80)
    
    # 使用配置的路徑創建 storage（模擬 BatchDownloadService 的行為）
    storage = KlineStorageManager(cache_dir=str(settings.data_cache_path))
    logger.info(f"📁 Storage 路徑: {storage.hdf5_path}")
    
    download_service = KlineDownloadService(storage_manager=storage)
    
    # 註冊 Binance provider
    binance_provider = BinanceProvider()
    download_service.registry.register('binance', binance_provider)
    
    symbol = "ETHUSDT"
    timeframe = "1h"
    
    # 步驟1: 下載範圍1 (2024年5月 - 歷史數據)
    logger.info("\n步驟1: 下載範圍1 (2024-05-20 to 2024-05-27)")
    df1 = download_service.download_klines(
        symbol=symbol,
        timeframe=timeframe,
        start_time=datetime(2024, 5, 20, 20, 0),
        end_time=datetime(2024, 5, 27, 12, 0),
        source="binance",
        save_to_storage=True  # 會調用 append_klines
    )
    logger.info(f"✅ 範圍1下載完成: {len(df1)} K-lines")
    
    # 檢查 HDF5 數據
    check1 = storage.read_klines(symbol, timeframe, validate_continuity=False)
    if check1 is not None:
        logger.info(f"📊 HDF5檢查1: {len(check1)} K-lines")
        logger.info(f"   時間範圍: {datetime.utcfromtimestamp(check1['timestamp'].min())} to {datetime.utcfromtimestamp(check1['timestamp'].max())}")
    else:
        logger.error("❌ 範圍1數據未找到")
        return False
    
    time.sleep(0.5)
    
    # 步驟2: 下載範圍2 (2025年10月 - 近期數據)
    logger.info("\n步驟2: 下載範圍2 (2025-10-20 to 2025-10-27)")
    df2 = download_service.download_klines(
        symbol=symbol,
        timeframe=timeframe,
        start_time=datetime(2025, 10, 20, 20, 0),
        end_time=datetime(2025, 10, 27, 12, 0),
        source="binance",
        save_to_storage=True  # 會調用 append_klines，應該合併而非覆蓋
    )
    logger.info(f"✅ 範圍2下載完成: {len(df2)} K-lines")
    
    # 檢查 HDF5 數據（關鍵檢查：應該包含兩個範圍）
    check2 = storage.read_klines(symbol, timeframe, validate_continuity=False)
    if check2 is not None:
        logger.info(f"📊 HDF5檢查2: {len(check2)} K-lines")
        logger.info(f"   時間範圍: {datetime.utcfromtimestamp(check2['timestamp'].min())} to {datetime.utcfromtimestamp(check2['timestamp'].max())}")
    else:
        logger.error("❌ 範圍2數據未找到")
        return False
    
    # 驗證結果
    logger.info("\n" + "=" * 80)
    logger.info("驗證結果")
    logger.info("=" * 80)
    
    expected_total = len(df1) + len(df2)
    actual_total = len(check2)
    
    # 檢查是否包含範圍1的數據
    range1_start = df1['timestamp'].min()
    range1_end = df1['timestamp'].max()
    range1_data = check2[(check2['timestamp'] >= range1_start) & (check2['timestamp'] <= range1_end)]
    has_range1 = len(range1_data) > 0
    
    # 檢查是否包含範圍2的數據
    range2_start = df2['timestamp'].min()
    range2_end = df2['timestamp'].max()
    range2_data = check2[(check2['timestamp'] >= range2_start) & (check2['timestamp'] <= range2_end)]
    has_range2 = len(range2_data) > 0
    
    logger.info(f"期望總數: {expected_total} K-lines ({len(df1)} + {len(df2)})")
    logger.info(f"實際總數: {actual_total} K-lines")
    logger.info(f"包含範圍1數據: {'✅' if has_range1 else '❌'} ({len(range1_data)} K-lines)")
    logger.info(f"包含範圍2數據: {'✅' if has_range2 else '❌'} ({len(range2_data)} K-lines)")
    
    # 計算合理誤差（考慮下載時間邊界可能有重疊）
    tolerance = 0.05  # 5% 容錯
    min_expected = int(expected_total * (1 - tolerance))
    max_expected = int(expected_total * (1 + tolerance))
    
    if has_range1 and has_range2 and min_expected <= actual_total <= max_expected:
        logger.info("\n🎉 測試通過！")
        logger.info(f"   ✅ 數據沒有被覆蓋")
        logger.info(f"   ✅ append_klines 功能正常")
        logger.info(f"   ✅ 存儲路徑統一: {storage.hdf5_path}")
        return True
    else:
        logger.error("\n❌ 測試失敗！")
        if not has_range1:
            logger.error("   ❌ 範圍1數據丟失（被覆蓋）")
        if not has_range2:
            logger.error("   ❌ 範圍2數據丟失")
        if not (min_expected <= actual_total <= max_expected):
            logger.error(f"   ❌ 數據總量異常: 期望 {expected_total}, 實際 {actual_total}")
        return False

if __name__ == "__main__":
    try:
        success = test_unified_storage_path()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"測試異常: {e}", exc_info=True)
        sys.exit(1)
