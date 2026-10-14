"""
K線存儲系統測試腳本
測試數據：ETHUSDT, 1h, 100根K線

驗收標準：
1. ✅ 可成功創建HDF5檔案並寫入測試數據
2. ✅ 可按symbol和timeframe正確讀取數據
3. ✅ metadata正確記錄和更新
4. ✅ 支援增量追加數據
5. ✅ 數據格式符合KLINE_DATA_SPECIFICATION.md
"""

import sys
import os
from pathlib import Path
import logging

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from momentum.DataExtraction.kline_storage import KlineStorageManager
from binance.client import Client
import pandas as pd
from datetime import datetime, timedelta

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_binance_klines(symbol: str = "ETHUSDT", interval: str = "1h", limit: int = 100):
    """
    從Binance API獲取K線數據

    Args:
        symbol: 交易對
        interval: 時間間隔
        limit: 數量

    Returns:
        pd.DataFrame: K線數據
    """
    try:
        logger.info(f"Fetching {limit} klines for {symbol} {interval} from Binance...")

        # 初始化Binance客戶端（不需要API key讀取公開數據）
        client = Client("", "")

        # 獲取K線數據
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)

        # 轉換為DataFrame
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
            'taker_buy_quote_volume', 'ignore'
        ])

        # 轉換數據類型
        df['timestamp'] = (df['open_time'] / 1000).astype('int64')  # 毫秒轉秒
        df['open'] = df['open'].astype('float32')
        df['high'] = df['high'].astype('float32')
        df['low'] = df['low'].astype('float32')
        df['close'] = df['close'].astype('float32')
        df['volume'] = df['volume'].astype('float32')
        df['taker_buy_volume'] = df['taker_buy_volume'].astype('float32')
        df['quote_volume'] = df['quote_volume'].astype('float32')
        df['number_of_trades'] = df['trades'].astype('int32')

        # 計算taker_ratio
        df['taker_ratio'] = (df['taker_buy_volume'] / df['volume']).fillna(0.5).astype('float32')
        # 確保範圍在0-1之間
        df['taker_ratio'] = df['taker_ratio'].clip(0, 1)

        # 選擇需要的欄位
        result_df = df[[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'taker_buy_volume', 'taker_ratio', 'quote_volume', 'number_of_trades'
        ]]

        logger.info(f"Successfully fetched {len(result_df)} klines")
        logger.info(f"Time range: {datetime.fromtimestamp(result_df['timestamp'].min())} to "
                   f"{datetime.fromtimestamp(result_df['timestamp'].max())}")

        return result_df

    except Exception as e:
        logger.error(f"Failed to fetch klines: {e}")
        raise


def test_basic_write_read():
    """
    測試1: 基本寫入和讀取功能
    驗收標準 1 & 2
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Basic Write and Read")
    logger.info("="*80)

    # 創建測試用的緩存目錄
    test_cache_dir = "./data/test_kline_storage"

    # 清理舊的測試數據
    import shutil
    if Path(test_cache_dir).exists():
        shutil.rmtree(test_cache_dir)
        logger.info(f"Cleaned up old test directory: {test_cache_dir}")

    # 初始化storage manager
    storage = KlineStorageManager(cache_dir=test_cache_dir)

    # 獲取測試數據
    df = fetch_binance_klines("ETHUSDT", "1h", 100)

    # 寫入數據
    logger.info("\nWriting klines to HDF5...")
    success = storage.write_klines("ETHUSDT", "1h", df, data_source="binance")

    if not success:
        logger.error("❌ Failed to write klines!")
        return False

    logger.info("✅ Successfully wrote klines to HDF5")

    # 讀取數據
    logger.info("\nReading klines from HDF5...")
    df_read = storage.read_klines("ETHUSDT", "1h")

    if df_read is None:
        logger.error("❌ Failed to read klines!")
        return False

    logger.info(f"✅ Successfully read {len(df_read)} klines from HDF5")

    # 驗證數據一致性
    if len(df) != len(df_read):
        logger.error(f"❌ Data length mismatch: wrote {len(df)}, read {len(df_read)}")
        return False

    logger.info("✅ Data length matches")

    # 驗證timestamp一致
    if not (df['timestamp'].values == df_read['timestamp'].values).all():
        logger.error("❌ Timestamp mismatch!")
        return False

    logger.info("✅ Timestamps match")

    logger.info("\n" + "="*80)
    logger.info("TEST 1: PASSED ✅")
    logger.info("="*80)

    return True


def test_metadata():
    """
    測試2: Metadata管理
    驗收標準 3
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Metadata Management")
    logger.info("="*80)

    test_cache_dir = "./data/test_kline_storage"
    storage = KlineStorageManager(cache_dir=test_cache_dir)

    # 讀取metadata
    logger.info("\nReading metadata...")
    metadata = storage.get_metadata("ETHUSDT", "1h")

    if metadata is None:
        logger.error("❌ Failed to read metadata!")
        return False

    logger.info(f"✅ Successfully read metadata:")
    for key, value in metadata.items():
        logger.info(f"  {key}: {value}")

    # 驗證必要欄位
    required_fields = ['time_range_start', 'time_range_end', 'total_bars',
                      'last_updated', 'data_source', 'timeframe']

    missing_fields = [field for field in required_fields if field not in metadata]
    if missing_fields:
        logger.error(f"❌ Missing metadata fields: {missing_fields}")
        return False

    logger.info("✅ All required metadata fields present")

    # 驗證metadata數值正確
    df = storage.read_klines("ETHUSDT", "1h")
    if metadata['total_bars'] != len(df):
        logger.error(f"❌ total_bars mismatch: metadata={metadata['total_bars']}, actual={len(df)}")
        return False

    if metadata['time_range_start'] != int(df['timestamp'].min()):
        logger.error("❌ time_range_start mismatch!")
        return False

    if metadata['time_range_end'] != int(df['timestamp'].max()):
        logger.error("❌ time_range_end mismatch!")
        return False

    logger.info("✅ Metadata values are correct")

    logger.info("\n" + "="*80)
    logger.info("TEST 2: PASSED ✅")
    logger.info("="*80)

    return True


def test_append():
    """
    測試3: 增量追加數據
    驗收標準 4
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Append Klines")
    logger.info("="*80)

    test_cache_dir = "./data/test_kline_storage"
    storage = KlineStorageManager(cache_dir=test_cache_dir)

    # 獲取新的數據（最新50根）
    logger.info("\nFetching new klines to append...")
    df_new = fetch_binance_klines("ETHUSDT", "1h", 50)

    # 記錄追加前的數據量
    df_before = storage.read_klines("ETHUSDT", "1h")
    count_before = len(df_before)
    logger.info(f"Klines before append: {count_before}")

    # 追加數據
    logger.info("\nAppending new klines...")
    success = storage.append_klines("ETHUSDT", "1h", df_new)

    if not success:
        logger.error("❌ Failed to append klines!")
        return False

    logger.info("✅ Successfully appended klines")

    # 讀取追加後的數據
    df_after = storage.read_klines("ETHUSDT", "1h")
    count_after = len(df_after)
    logger.info(f"Klines after append: {count_after}")

    # 驗證數據量增加（或去重後保持）
    if count_after < count_before:
        logger.error(f"❌ Data count decreased after append!")
        return False

    logger.info(f"✅ Data count after append: {count_after} (before: {count_before})")

    # 驗證無重複timestamp
    if df_after['timestamp'].duplicated().any():
        logger.error("❌ Duplicate timestamps found after append!")
        return False

    logger.info("✅ No duplicate timestamps")

    logger.info("\n" + "="*80)
    logger.info("TEST 3: PASSED ✅")
    logger.info("="*80)

    return True


def test_data_validation():
    """
    測試4: 數據格式驗證
    驗收標準 5
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Data Format Validation")
    logger.info("="*80)

    test_cache_dir = "./data/test_kline_storage"
    storage = KlineStorageManager(cache_dir=test_cache_dir)

    # 讀取數據
    df = storage.read_klines("ETHUSDT", "1h")

    logger.info("\nValidating data format...")

    # 檢查必需欄位
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'taker_buy_volume', 'taker_ratio']

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"❌ Missing required columns: {missing_cols}")
        return False

    logger.info("✅ All required columns present")

    # 檢查OHLC合理性
    if not (df['high'] >= df['low']).all():
        logger.error("❌ high < low found!")
        return False

    if not (df['high'] >= df['open']).all():
        logger.error("❌ high < open found!")
        return False

    if not (df['high'] >= df['close']).all():
        logger.error("❌ high < close found!")
        return False

    logger.info("✅ OHLC values are valid")

    # 檢查taker_ratio範圍
    if not ((df['taker_ratio'] >= 0) & (df['taker_ratio'] <= 1)).all():
        invalid_count = ((df['taker_ratio'] < 0) | (df['taker_ratio'] > 1)).sum()
        logger.error(f"❌ Invalid taker_ratio values found: {invalid_count}")
        return False

    logger.info("✅ taker_ratio values are in valid range [0, 1]")

    # 檢查volume >= 0
    if not (df['volume'] >= 0).all():
        logger.error("❌ Negative volume found!")
        return False

    logger.info("✅ Volume values are non-negative")

    # 檢查數據類型
    logger.info("\nChecking data types...")
    logger.info(f"  timestamp: {df['timestamp'].dtype}")
    logger.info(f"  open: {df['open'].dtype}")
    logger.info(f"  high: {df['high'].dtype}")
    logger.info(f"  low: {df['low'].dtype}")
    logger.info(f"  close: {df['close'].dtype}")
    logger.info(f"  volume: {df['volume'].dtype}")
    logger.info(f"  taker_ratio: {df['taker_ratio'].dtype}")

    logger.info("\n" + "="*80)
    logger.info("TEST 4: PASSED ✅")
    logger.info("="*80)

    return True


def test_cache_index():
    """
    測試5: 全局索引功能
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Cache Index")
    logger.info("="*80)

    test_cache_dir = "./data/test_kline_storage"
    storage = KlineStorageManager(cache_dir=test_cache_dir)

    # 讀取索引
    logger.info("\nReading cache index...")
    cache_index = storage.get_cache_index()

    logger.info(f"Cache index: {cache_index}")

    # 驗證ETHUSDT存在
    if "ETHUSDT" not in cache_index:
        logger.error("❌ ETHUSDT not found in cache index!")
        return False

    logger.info("✅ ETHUSDT found in cache index")

    # 驗證1h timeframe存在
    if "1h" not in cache_index["ETHUSDT"]:
        logger.error("❌ 1h timeframe not found for ETHUSDT!")
        return False

    logger.info("✅ 1h timeframe found for ETHUSDT")

    logger.info("\n" + "="*80)
    logger.info("TEST 5: PASSED ✅")
    logger.info("="*80)

    return True


def test_data_integrity():
    """
    測試6: 數據完整性檢查
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 6: Data Integrity Check")
    logger.info("="*80)

    test_cache_dir = "./data/test_kline_storage"
    storage = KlineStorageManager(cache_dir=test_cache_dir)

    # 執行完整性檢查
    logger.info("\nPerforming integrity check...")
    report = storage.check_data_integrity("ETHUSDT", "1h")

    logger.info(f"\nIntegrity Report:")
    logger.info(f"  is_valid: {report['is_valid']}")
    logger.info(f"  errors: {report['errors']}")
    logger.info(f"  warnings: {report['warnings']}")
    logger.info(f"  stats: {report['stats']}")

    if not report['is_valid']:
        logger.error("❌ Integrity check failed!")
        logger.error(f"Errors: {report['errors']}")
        return False

    logger.info("✅ Integrity check passed")

    logger.info("\n" + "="*80)
    logger.info("TEST 6: PASSED ✅")
    logger.info("="*80)

    return True


def main():
    """
    執行所有測試
    """
    logger.info("\n" + "="*80)
    logger.info("K線存儲系統測試開始")
    logger.info("測試數據: ETHUSDT, 1h, 100根K線")
    logger.info("="*80)

    tests = [
        ("基本寫入和讀取", test_basic_write_read),
        ("Metadata管理", test_metadata),
        ("增量追加數據", test_append),
        ("數據格式驗證", test_data_validation),
        ("全局索引功能", test_cache_index),
        ("數據完整性檢查", test_data_integrity),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            logger.error(f"\n❌ Test '{test_name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # 總結
    logger.info("\n" + "="*80)
    logger.info("測試總結")
    logger.info("="*80)

    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not result:
            all_passed = False

    logger.info("\n" + "="*80)
    if all_passed:
        logger.info("所有測試通過！ ✅✅✅")
        logger.info("\n驗收標準檢查:")
        logger.info("✅ 1. 可成功創建HDF5檔案並寫入測試數據")
        logger.info("✅ 2. 可按symbol和timeframe正確讀取數據")
        logger.info("✅ 3. metadata正確記錄和更新")
        logger.info("✅ 4. 支援增量追加數據")
        logger.info("✅ 5. 數據格式符合KLINE_DATA_SPECIFICATION.md")
    else:
        logger.error("部分測試失敗！ ❌")

    logger.info("="*80 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


def test_real_kline_roundtrip_and_inclusive_range_read_tmp(tmp_path, monkeypatch):
    """TESTREG 純增改寫：真實 kline（data_cache/feature_klines/kline_cache.h5，h5py 獨立讀）寫入 tmp 後讀回逐欄位元相等
    （值＋dtype），且時間範圍讀取為閉區間 [start, end]、索引為 RangeIndex。不打網路、不寫 repo。"""
    import h5py

    monkeypatch.setenv("LEGACY_KLINE_CACHE_DIR", str(tmp_path / "no_legacy"))
    with h5py.File(Path(__file__).resolve().parents[1] / "data_cache" / "feature_klines" / "kline_cache.h5", "r") as f:
        sym = sorted(k for k in f.keys() if k != "_metadata")[0]
        tf = sorted(f[sym].keys())[0]
        src = pd.DataFrame(f[sym][tf]["data"][()][:120])
    storage = KlineStorageManager(cache_dir=str(tmp_path / "store"))
    ok = storage.write_klines(sym, tf, src.copy(), data_source="replay_of_real_cache")
    back = storage.read_klines(sym, tf)
    assert ok and back is not None and back.equals(src), "寫讀往返不相等（值或 dtype）"

    lo, hi = int(src["timestamp"].iloc[10]), int(src["timestamp"].iloc[29])
    part = storage.read_klines(sym, tf, start_time=lo, end_time=hi)
    assert part is not None and part["timestamp"].tolist() == src["timestamp"].iloc[10:30].tolist() and part.index.equals(pd.RangeIndex(20)), "範圍讀取非閉區間"


def test_real_kline_metadata_fields_match_written_data_tmp(tmp_path, monkeypatch):
    """TESTREG 純增改寫：metadata 之 total_bars／time_range／data_source／timeframe 等於寫入資料（獨立讀之真實 kline）。"""
    import h5py

    monkeypatch.setenv("LEGACY_KLINE_CACHE_DIR", str(tmp_path / "no_legacy"))
    with h5py.File(Path(__file__).resolve().parents[1] / "data_cache" / "feature_klines" / "kline_cache.h5", "r") as f:
        sym = sorted(k for k in f.keys() if k != "_metadata")[0]
        tf = sorted(f[sym].keys())[0]
        src = pd.DataFrame(f[sym][tf]["data"][()][:120])
    storage = KlineStorageManager(cache_dir=str(tmp_path / "store"))
    ok = storage.write_klines(sym, tf, src.copy(), data_source="replay_of_real_cache")
    meta = storage.get_metadata(sym, tf)
    assert (ok and meta is not None and int(meta["total_bars"]) == len(src)
            and int(meta["time_range_start"]) == int(src["timestamp"].iloc[0])
            and int(meta["time_range_end"]) == int(src["timestamp"].iloc[-1])
            and meta["data_source"] == "replay_of_real_cache" and meta["timeframe"] == tf), meta


def test_real_kline_append_overlap_keeps_revised_last_bar_tmp(tmp_path, monkeypatch):
    """TESTREG 純增改寫：先寫入「最後一根尚未收完」之版本（真實 bar 之 volume／taker_buy_volume 減半，比例不變），
    再 append 與其重疊之真實後續資料 ⇒ 讀回須逐位元等於真實 150 根（重疊列取新值、無重複），metadata 同步更新。"""
    import h5py

    monkeypatch.setenv("LEGACY_KLINE_CACHE_DIR", str(tmp_path / "no_legacy"))
    with h5py.File(Path(__file__).resolve().parents[1] / "data_cache" / "feature_klines" / "kline_cache.h5", "r") as f:
        sym = sorted(k for k in f.keys() if k != "_metadata")[0]
        tf = sorted(f[sym].keys())[0]
        full = pd.DataFrame(f[sym][tf]["data"][()][:150])
    existing = full.iloc[:100].copy()
    existing.loc[99, "volume"] = existing.loc[99, "volume"] / 2
    existing.loc[99, "taker_buy_volume"] = existing.loc[99, "taker_buy_volume"] / 2
    storage = KlineStorageManager(cache_dir=str(tmp_path / "store"))
    ok_write = storage.write_klines(sym, tf, existing, data_source="replay_of_real_cache")
    ok_append = storage.append_klines(sym, tf, full.iloc[99:].reset_index(drop=True).copy())
    back = storage.read_klines(sym, tf)
    meta = storage.get_metadata(sym, tf)
    assert (ok_write and ok_append and back is not None and back.equals(full)
            and int(meta["total_bars"]) == 150 and int(meta["time_range_end"]) == int(full["timestamp"].iloc[-1])), \
        "append 重疊列未取新值或 metadata 未更新"


def test_real_kline_cache_index_lists_all_timeframes_sorted_tmp(tmp_path, monkeypatch):
    """TESTREG 純增改寫：同一 symbol 依逆序寫入多個 timeframe ⇒ 全局索引恰為 {symbol: 排序後之 timeframe 清單}。"""
    import h5py

    monkeypatch.setenv("LEGACY_KLINE_CACHE_DIR", str(tmp_path / "no_legacy"))
    with h5py.File(Path(__file__).resolve().parents[1] / "data_cache" / "feature_klines" / "kline_cache.h5", "r") as f:
        sym = sorted(k for k in f.keys() if k != "_metadata")[0]
        tfs = sorted(f[sym].keys())
        frames = {tf: pd.DataFrame(f[sym][tf]["data"][()][:30]) for tf in tfs}
    storage = KlineStorageManager(cache_dir=str(tmp_path / "store"))
    oks = [storage.write_klines(sym, tf, frames[tf], data_source="replay_of_real_cache") for tf in reversed(tfs)]
    assert len(tfs) >= 2 and all(oks) and storage.get_cache_index() == {sym: sorted(tfs)}, storage.get_cache_index()


def test_real_kline_write_rejects_low_above_close_tmp(tmp_path, monkeypatch):
    """TESTREG 純增改寫：真實 kline 中一根下跌 bar 之 low 改為 (open+close)/2（low>close 但 ≤open≤high）⇒
    寫入須被拒、且不得落任何資料。"""
    import h5py

    monkeypatch.setenv("LEGACY_KLINE_CACHE_DIR", str(tmp_path / "no_legacy"))
    with h5py.File(Path(__file__).resolve().parents[1] / "data_cache" / "feature_klines" / "kline_cache.h5", "r") as f:
        sym = sorted(k for k in f.keys() if k != "_metadata")[0]
        tf = sorted(f[sym].keys())[0]
        src = pd.DataFrame(f[sym][tf]["data"][()][:120])
    i = int(src.index[src["close"] < src["open"]][0])
    bad = src.copy()
    bad.loc[i, "low"] = (bad.loc[i, "open"] + bad.loc[i, "close"]) / 2
    storage = KlineStorageManager(cache_dir=str(tmp_path / "store"))
    ok = storage.write_klines(sym, tf, bad, data_source="replay_of_real_cache")
    assert (bad.loc[i, "low"] > bad.loc[i, "close"] and bad.loc[i, "low"] <= bad.loc[i, "open"] <= bad.loc[i, "high"]
            and ok is False and storage.read_klines(sym, tf) is None), "low>close 之 bar 未被拒"


def test_real_kline_integrity_report_uses_timeframe_spacing_tmp(tmp_path, monkeypatch):
    """TESTREG 純增改寫：連續之真實 kline（非 1h 週期）⇒ 完整性報告 is_valid、無錯誤無警告，
    stats 恰為 {total_bars, time_range}（值對獨立讀入之資料）。"""
    import h5py

    monkeypatch.setenv("LEGACY_KLINE_CACHE_DIR", str(tmp_path / "no_legacy"))
    with h5py.File(Path(__file__).resolve().parents[1] / "data_cache" / "feature_klines" / "kline_cache.h5", "r") as f:
        sym = sorted(k for k in f.keys() if k != "_metadata")[0]
        tf = sorted(f[sym].keys())[0]
        src = pd.DataFrame(f[sym][tf]["data"][()][:120])
    storage = KlineStorageManager(cache_dir=str(tmp_path / "store"))
    ok = storage.write_klines(sym, tf, src.copy(), data_source="replay_of_real_cache")
    expected_stats = {"total_bars": len(src),
                      "time_range": {"start": int(src["timestamp"].iloc[0]), "end": int(src["timestamp"].iloc[-1])}}
    report: dict = {}
    assert (ok and (report := storage.check_data_integrity(sym, tf))["is_valid"] is True
            and report["errors"] == [] and report["warnings"] == []
            and report["stats"] == expected_stats), report
