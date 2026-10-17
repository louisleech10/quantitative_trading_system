"""
DataSourceManager 單元測試

測試數據源管理器的核心功能，使用真實 K 線（`data_cache/feature_klines/kline_cache.h5` 之 ETHUSDT/1h）。

🔴 只有「真實 K 線檔或該 symbol/週期缺席」才 skip；讀取後之資料驗證或連續性檢查失敗
（`get_dataframe` 拋 ValueError）一律為紅，不得轉成 skip（測試設計章程 §B3）。
"""

from pathlib import Path

import h5py
import pytest
import pandas as pd
from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.Indicators.data_source_manager import DataSourceManager
from momentum.Indicators.types import DataSourceEnum

KLINE_DIR = Path(__file__).resolve().parents[2] / "data_cache" / "feature_klines"
KLINE_FILE = KLINE_DIR / "kline_cache.h5"
SYMBOL, TIMEFRAME = "ETHUSDT", "1h"


def _require_real_kline() -> None:
    if not KLINE_FILE.is_file():
        pytest.skip(f"真實 K 線檔缺席：{KLINE_FILE}")
    with h5py.File(KLINE_FILE, "r") as f:
        if SYMBOL not in f or TIMEFRAME not in f[SYMBOL] or "data" not in f[SYMBOL][TIMEFRAME]:
            pytest.skip(f"真實 K 線缺 {SYMBOL}/{TIMEFRAME}")


class TestDataSourceManager:
    """DataSourceManager 測試類"""

    @pytest.fixture
    def manager(self):
        """創建 DataSourceManager 實例（讀真實 K 線）"""
        _require_real_kline()
        return DataSourceManager(KlineStorageManager(cache_dir=str(KLINE_DIR)))

    def test_get_dataframe_ethusdt(self, manager):
        """測試讀取 ETHUSDT 1h 數據"""
        df = manager.get_dataframe(SYMBOL, TIMEFRAME)

        # 驗證 DataFrame 不為空
        assert df is not None, "DataFrame should not be None"
        assert len(df) > 0, "DataFrame should not be empty"

        # 驗證必需列存在
        required_cols = ['close', 'open', 'high', 'low', 'volume',
                       'taker_buy_volume', 'taker_ratio']
        for col in required_cols:
            assert col in df.columns, f"Column {col} should exist"

    def test_get_data_source_close(self, manager):
        """測試獲取 close 數據源"""
        close = manager.get_data_source(SYMBOL, TIMEFRAME, DataSourceEnum.CLOSE)

        assert close is not None, "Close data should not be None"
        assert len(close) > 0, "Close data should not be empty"
        assert isinstance(close, pd.Series), "Should return pd.Series"

        # 驗證數據有效
        assert (close > 0).all(), "Close prices should be positive"
        # 與 get_dataframe 之 close 欄逐值一致
        df = manager.get_dataframe(SYMBOL, TIMEFRAME)
        assert close.to_numpy().tolist() == df["close"].to_numpy().tolist()

    def test_get_all_data_sources(self, manager):
        """測試獲取所有數據源"""
        all_sources = manager.get_all_data_sources(SYMBOL, TIMEFRAME, required_only=True)

        assert len(all_sources) >= 7, "Should have at least 7 required data sources"

        # 驗證每個數據源
        for ds, series in all_sources.items():
            assert isinstance(series, pd.Series), f"{ds} should be pd.Series"
            assert len(series) > 0, f"{ds} should not be empty"

    def test_validate_dataframe(self, manager):
        """測試 DataFrame 驗證功能：真表為有效，注入 NaN／high<low 之反例須判無效"""
        df = manager.get_dataframe(SYMBOL, TIMEFRAME)
        is_valid, error_msg = manager.validate_dataframe(df)

        assert is_valid, f"DataFrame should be valid, got error: {error_msg}"

        with_nan = df.copy()
        with_nan.loc[with_nan.index[len(with_nan) // 2], "close"] = float("nan")
        bad_valid, bad_msg = manager.validate_dataframe(with_nan)
        assert bad_valid is False
        assert "NaN" in bad_msg

        inverted = df.copy()
        row = inverted.index[len(inverted) // 3]
        inverted.loc[row, "low"] = inverted.loc[row, "high"] * 2
        inv_valid, inv_msg = manager.validate_dataframe(inverted)
        assert inv_valid is False
        assert "High < Low" in inv_msg

    def test_cache_mechanism(self, manager):
        """測試緩存機制"""
        # 第一次讀取（從 HDF5）
        df1 = manager.get_dataframe(SYMBOL, TIMEFRAME, use_cache=True)

        # 第二次讀取（從緩存）
        df2 = manager.get_dataframe(SYMBOL, TIMEFRAME, use_cache=True)

        # 應該是同一個對象
        assert df1 is df2, "Should return cached DataFrame"

        # 清空緩存
        manager.clear_cache()

        # 第三次讀取（重新從 HDF5）
        df3 = manager.get_dataframe(SYMBOL, TIMEFRAME, use_cache=True)

        # 應該是不同對象
        assert df1 is not df3, "Should return new DataFrame after cache clear"
        pd.testing.assert_frame_equal(df1, df3)


if __name__ == "__main__":
    # 簡單的手動測試
    print("Running DataSourceManager tests...")

    manager = DataSourceManager()

    try:
        # 測試讀取數據
        df = manager.get_dataframe("ETHUSDT", "1h")
        print(f"✅ Loaded DataFrame: {len(df)} bars")
        print(f"   Columns: {list(df.columns)}")

        # 測試數據源
        close = manager.get_data_source("ETHUSDT", "1h", DataSourceEnum.CLOSE)
        print(f"✅ Close data: {len(close)} values")

        # 測試所有數據源
        all_sources = manager.get_all_data_sources("ETHUSDT", "1h")
        print(f"✅ All sources: {list(all_sources.keys())}")

        print("\n✅ All manual tests passed!")

    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()
