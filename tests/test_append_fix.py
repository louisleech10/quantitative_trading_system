"""
測試批次下載append修復
驗證多個時間範圍的數據不會互相覆蓋
"""
import sys
from pathlib import Path

# 添加項目路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from momentum.DataExtraction.kline_download_service import KlineDownloadService
from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.DataExtraction.providers.binance_provider import BinanceProvider
from datetime import datetime
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_multi_range_append():
    """測試多個時間範圍的下載，驗證append而非覆蓋"""
    
    storage = KlineStorageManager()
    download_service = KlineDownloadService(storage_manager=storage)
    
    # 註冊 Binance provider
    binance_provider = BinanceProvider()
    download_service.registry.register('binance', binance_provider)
    
    symbol = "ETHUSDT"
    timeframe = "1h"
    
    logger.info("=" * 80)
    logger.info("測試場景：批次下載多個不連續時間範圍")
    logger.info("=" * 80)
    
    # 範圍1: 2024年5月 (歷史數據)
    logger.info("\n步驟1: 下載範圍1 (2024-05-20 to 2024-05-27)")
    df1 = download_service.download_klines(
        symbol=symbol,
        timeframe=timeframe,
        start_time=datetime(2024, 5, 20, 20, 0),
        end_time=datetime(2024, 5, 27, 12, 0),
        source="binance",
        save_to_storage=True
    )
    logger.info(f"✅ 範圍1下載完成: {len(df1)} K-lines")
    logger.info(f"   時間範圍: {df1['timestamp'].min()} to {df1['timestamp'].max()}")
    
    # 檢查HDF5數據（多區間 append 允許不連續）
    check1 = storage.read_klines(symbol, timeframe, validate_continuity=False)
    logger.info(f"📊 HDF5檢查1: {len(check1)} K-lines")
    logger.info(f"   時間範圍: {datetime.utcfromtimestamp(check1['timestamp'].min())} to {datetime.utcfromtimestamp(check1['timestamp'].max())}")
    
    # 範圍2: 2025年10月 (近期數據)
    logger.info("\n步驟2: 下載範圍2 (2025-10-20 to 2025-10-27)")
    df2 = download_service.download_klines(
        symbol=symbol,
        timeframe=timeframe,
        start_time=datetime(2025, 10, 20, 20, 0),
        end_time=datetime(2025, 10, 27, 12, 0),
        source="binance",
        save_to_storage=True
    )
    logger.info(f"✅ 範圍2下載完成: {len(df2)} K-lines")
    logger.info(f"   時間範圍: {df2['timestamp'].min()} to {df2['timestamp'].max()}")
    
    # 檢查HDF5數據 (關鍵檢查：應該包含兩個範圍)
    check2 = storage.read_klines(symbol, timeframe, validate_continuity=False)
    logger.info(f"📊 HDF5檢查2: {len(check2)} K-lines")
    logger.info(f"   時間範圍: {datetime.utcfromtimestamp(check2['timestamp'].min())} to {datetime.utcfromtimestamp(check2['timestamp'].max())}")
    
    # 驗證結果
    logger.info("\n" + "=" * 80)
    logger.info("驗證結果")
    logger.info("=" * 80)
    
    expected_total = len(df1) + len(df2)
    actual_total = len(check2)
    
    # 檢查是否包含範圍1的數據
    range1_start = df1['timestamp'].min()
    range1_end = df1['timestamp'].max()
    has_range1 = ((check2['timestamp'] >= range1_start) & (check2['timestamp'] <= range1_end)).any()
    
    # 檢查是否包含範圍2的數據
    range2_start = df2['timestamp'].min()
    range2_end = df2['timestamp'].max()
    has_range2 = ((check2['timestamp'] >= range2_start) & (check2['timestamp'] <= range2_end)).any()
    
    logger.info(f"期望總數: {expected_total} K-lines")
    logger.info(f"實際總數: {actual_total} K-lines")
    logger.info(f"包含範圍1數據: {'✅' if has_range1 else '❌'}")
    logger.info(f"包含範圍2數據: {'✅' if has_range2 else '❌'}")
    
    if not (has_range1 and has_range2 and actual_total >= expected_total * 0.9):
        logger.error("\n❌ 測試失敗！數據可能被覆蓋")
        if not has_range1:
            logger.error("   範圍1數據丟失")
        if not has_range2:
            logger.error("   範圍2數據丟失")
    assert has_range1, "範圍1數據丟失"
    assert has_range2, "範圍2數據丟失"
    assert actual_total >= expected_total * 0.9, "總筆數不足，可能發生覆蓋"
    logger.info("\n🎉 測試通過！數據沒有被覆蓋，append功能正常")

if __name__ == "__main__":
    try:
        test_multi_range_append()
        sys.exit(0)
    except Exception as e:
        logger.error(f"測試異常: {e}", exc_info=True)
        sys.exit(1)
