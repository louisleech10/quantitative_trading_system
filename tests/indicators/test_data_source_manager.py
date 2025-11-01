"""
DataSourceManager 單元測試

測試數據源管理器的核心功能，使用真實的 ETHUSDT_1h.h5 數據。
"""

import pytest
import pandas as pd
from momentum.Indicators.data_source_manager import DataSourceManager
from momentum.Indicators.types import DataSourceEnum


class TestDataSourceManager:
    """DataSourceManager 測試類"""

    @pytest.fixture
    def manager(self):
        """創建 DataSourceManager 實例"""
        return DataSourceManager()

    def test_get_dataframe_ethusdt(self, manager):
        """測試讀取 ETHUSDT 1h 數據"""
        try:
            df = manager.get_dataframe("ETHUSDT", "1h")

            # 驗證 DataFrame 不為空
            assert df is not None, "DataFrame should not be None"
            assert len(df) > 0, "DataFrame should not be empty"

            # 驗證必需列存在
            required_cols = ['close', 'open', 'high', 'low', 'volume',
                           'taker_buy_volume', 'taker_ratio']
            for col in required_cols:
                assert col in df.columns, f"Column {col} should exist"

            print(f"✅ Successfully loaded {len(df)} bars from ETHUSDT/1h")

        except ValueError as e:
            pytest.skip(f"ETHUSDT data not available: {e}")

    def test_get_data_source_close(self, manager):
        """測試獲取 close 數據源"""
        try:
            close = manager.get_data_source("ETHUSDT", "1h", DataSourceEnum.CLOSE)

            assert close is not None, "Close data should not be None"
            assert len(close) > 0, "Close data should not be empty"
            assert isinstance(close, pd.Series), "Should return pd.Series"

            # 驗證數據有效
            assert (close > 0).all(), "Close prices should be positive"

            print(f"✅ Close data: {len(close)} values, range [{close.min():.2f}, {close.max():.2f}]")

        except ValueError as e:
            pytest.skip(f"ETHUSDT data not available: {e}")

    def test_get_all_data_sources(self, manager):
        """測試獲取所有數據源"""
        try:
            all_sources = manager.get_all_data_sources("ETHUSDT", "1h", required_only=True)

            assert len(all_sources) >= 7, "Should have at least 7 required data sources"

            # 驗證每個數據源
            for ds, series in all_sources.items():
                assert isinstance(series, pd.Series), f"{ds} should be pd.Series"
                assert len(series) > 0, f"{ds} should not be empty"

            print(f"✅ Loaded {len(all_sources)} data sources")

        except ValueError as e:
            pytest.skip(f"ETHUSDT data not available: {e}")

    def test_validate_dataframe(self, manager):
        """測試 DataFrame 驗證功能"""
        try:
            df = manager.get_dataframe("ETHUSDT", "1h")
            is_valid, error_msg = manager.validate_dataframe(df)

            assert is_valid, f"DataFrame should be valid, got error: {error_msg}"

            print("✅ DataFrame validation passed")

        except ValueError as e:
            pytest.skip(f"ETHUSDT data not available: {e}")

    def test_cache_mechanism(self, manager):
        """測試緩存機制"""
        try:
            # 第一次讀取（從 HDF5）
            df1 = manager.get_dataframe("ETHUSDT", "1h", use_cache=True)

            # 第二次讀取（從緩存）
            df2 = manager.get_dataframe("ETHUSDT", "1h", use_cache=True)

            # 應該是同一個對象
            assert df1 is df2, "Should return cached DataFrame"

            # 清空緩存
            manager.clear_cache()

            # 第三次讀取（重新從 HDF5）
            df3 = manager.get_dataframe("ETHUSDT", "1h", use_cache=True)

            # 應該是不同對象
            assert df1 is not df3, "Should return new DataFrame after cache clear"

            print("✅ Cache mechanism working correctly")

        except ValueError as e:
            pytest.skip(f"ETHUSDT data not available: {e}")


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
