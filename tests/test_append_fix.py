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


def test_multi_range_append_isolated_cache_sum_and_revision(tmp_path, monkeypatch):
    """TESTREG 4.2 純增：密封版多區間 append（tmp_path 快取、Binance client 以回放替身）。

    原目標直連 Binance 並寫生產 ./data_cache；生產快取已有歷史時總數斷言恆成立。
    本測試於**空快取**驗：兩區間並存、總筆數＝兩段之和（手算各 161 根）、各區間以
    read_klines 時間切片取回筆數不變；再下載與第二段尾端重疊之 3 根「修訂值」，
    去重須保留最新下載（keep last），總筆數不變。
    """
    monkeypatch.setenv("LEGACY_KLINE_CACHE_DIR", str(tmp_path / "legacy_empty"))
    storage = KlineStorageManager(cache_dir=str(tmp_path / "cache"))
    service = KlineDownloadService(storage_manager=storage, failure_log_path=str(tmp_path / "failures.json"))
    provider = BinanceProvider()
    revision = {"close_bump": 0.0}
    hour_ms = 3_600_000

    class _ReplayClient:
        """Binance get_klines 契約替身：startTime／endTime 皆 inclusive、整點對齊、limit 截斷。"""

        def ping(self):
            return {}

        def get_klines(self, *, symbol, interval, startTime, endTime, limit):
            rows = []
            ts = -(-int(startTime) // hour_ms) * hour_ms
            while ts <= int(endTime) and len(rows) < int(limit):
                base = 1000.0 + float((ts // hour_ms) % 97) + revision["close_bump"]
                close = base + 0.5
                rows.append([ts, str(base), str(base + 1.0), str(base - 1.0), str(close), "10.0",
                             ts + hour_ms - 1, "10000.0", 5, "4.0", "4000.0", "0"])
                ts += hour_ms
            return rows

    provider.client = _ReplayClient()
    service.registry.register("binance", provider)

    df1 = service.download_klines(symbol="ETHUSDT", timeframe="1h", start_time=datetime(2024, 5, 20, 20, 0),
                                  end_time=datetime(2024, 5, 27, 12, 0), source="binance", save_to_storage=True)
    df2 = service.download_klines(symbol="ETHUSDT", timeframe="1h", start_time=datetime(2025, 10, 20, 20, 0),
                                  end_time=datetime(2025, 10, 27, 12, 0), source="binance", save_to_storage=True)
    revision["close_bump"] = 7.0
    service.download_klines(symbol="ETHUSDT", timeframe="1h", start_time=datetime(2025, 10, 27, 10, 0),
                            end_time=datetime(2025, 10, 27, 12, 0), source="binance", save_to_storage=True)

    full = storage.read_klines("ETHUSDT", "1h", validate_continuity=False)
    r1 = storage.read_klines("ETHUSDT", "1h", start_time=int(df1["timestamp"].min()),
                             end_time=int(df1["timestamp"].max()), validate_continuity=False)
    r2 = storage.read_klines("ETHUSDT", "1h", start_time=int(df2["timestamp"].min()),
                             end_time=int(df2["timestamp"].max()), validate_continuity=False)
    rev_start = int((datetime(2025, 10, 27, 10, 0) - datetime(1970, 1, 1)).total_seconds())
    tail_close = full.loc[full["timestamp"] >= rev_start, "close"].tolist()
    expected_tail = [1000.0 + float((s * 1000 // hour_ms) % 97) + 7.5 for s in (rev_start, rev_start + 3600, rev_start + 7200)]
    assert (len(df1), len(df2), len(full), len(r1), len(r2)) == (161, 161, 322, 161, 161) and tail_close == expected_tail
