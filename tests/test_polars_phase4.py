"""Phase 4 Polars integration tests (T4.1~T4.4, T4.B1~T4.B3).

Tests verify numerical equivalence between Polars and pandas paths
for L1→L2 derived features and L6.5 preprocessing.
"""

from __future__ import annotations

import os
from typing import Dict

import numpy as np
import pandas as pd
import pytest


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_layer1_df() -> pd.DataFrame:
    """產生模擬 L1 atomic indicator DataFrame（100 rows × 20 cols）"""
    np.random.seed(42)
    n_rows = 100
    n_cols = 20
    data = np.random.randn(n_rows, n_cols).astype(np.float32)
    # Insert some NaN patterns (mimicking rolling indicator output)
    data[:5, :] = np.nan  # First 5 rows NaN (min_periods)
    data[50:52, 3] = np.nan  # Scattered NaN
    columns = [f"close_trend_EMA_{i * 5}" for i in range(1, n_cols + 1)]
    index = pd.date_range("2024-01-01", periods=n_rows, freq="1h")
    return pd.DataFrame(data, columns=columns, index=index)


@pytest.fixture
def sample_raw_data() -> pd.DataFrame:
    """產生模擬 raw OHLCV 資料"""
    np.random.seed(123)
    n_rows = 100
    index = pd.date_range("2024-01-01", periods=n_rows, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n_rows) * 0.5)
    return pd.DataFrame({
        "open": close + np.random.randn(n_rows) * 0.1,
        "high": close + np.abs(np.random.randn(n_rows)) * 0.5,
        "low": close - np.abs(np.random.randn(n_rows)) * 0.5,
        "close": close,
        "volume": np.random.randint(1000, 10000, n_rows).astype(float),
    }, index=index)


@pytest.fixture
def sample_feature_info() -> Dict:
    """產生模擬 indicator specs for derived operator engine"""
    return {
        f"close_trend_EMA_{i * 5}": {
            "source": "close",
            "category": "trend",
            "indicator": "EMA",
            "params": [i * 5],
        }
        for i in range(1, 21)
    }


@pytest.fixture
def empty_df() -> pd.DataFrame:
    """空 DataFrame"""
    return pd.DataFrame(dtype=np.float32)


@pytest.fixture
def all_nan_df() -> pd.DataFrame:
    """全 NaN DataFrame"""
    n_rows = 50
    index = pd.date_range("2024-01-01", periods=n_rows, freq="1h")
    data = np.full((n_rows, 5), np.nan, dtype=np.float32)
    columns = [f"col_{i}" for i in range(5)]
    return pd.DataFrame(data, columns=columns, index=index)


# ─── T4.1: test_polars_l2_vs_pandas_l2 ──────────────────────────────────────

class TestPolarsL2VsPandasL2:
    """T4.1: Polars L2 derived features vs pandas L2 — 全量數值等價"""

    def test_polars_l2_vs_pandas_l2(self, sample_layer1_df, sample_raw_data, sample_feature_info):
        """測試 Polars L2 output 與 pandas L2 output 數值等價 (atol=1e-4, float32 precision)"""
        from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine

        config = {
            "enabled": True,
            "ratio": {"enabled": True},
            "cross": {"enabled": True},
            "momentum": {"enabled": True, "lags": [1, 5, 10]},
            "distance": {"enabled": True, "apply_to": "all"},
            "binary_signal": {"enabled": False},
            "signed_strength": {"enabled": False},
            "worldquant": {"enabled": False},
        }
        engine = DerivedOperatorEngine(config)

        # Pandas path
        pandas_result = engine.compute_all(sample_layer1_df, sample_raw_data, sample_feature_info)

        # Polars path
        polars_result = engine.compute_all_polars(sample_layer1_df, sample_raw_data, sample_feature_info)

        # Verify shapes match
        assert pandas_result.shape[0] == polars_result.shape[0], (
            f"Row count mismatch: pandas={pandas_result.shape[0]}, polars={polars_result.shape[0]}"
        )

        # Find common columns (Polars path may have same columns in different order)
        common_cols = sorted(set(pandas_result.columns) & set(polars_result.columns))
        assert len(common_cols) > 0, "No common columns between pandas and polars results"

        # Numerical equivalence check (float32 precision: atol=1e-4 for large-magnitude Distance cols)
        for col in common_cols:
            pd_col = pandas_result[col].values.astype(np.float64)
            pl_col = polars_result[col].values.astype(np.float64)
            # Both NaN mask
            pd_nan = np.isnan(pd_col)
            pl_nan = np.isnan(pl_col)
            np.testing.assert_array_equal(
                pd_nan, pl_nan,
                err_msg=f"NaN pattern mismatch in column '{col}'"
            )
            # Numeric comparison on non-NaN values
            valid = ~pd_nan
            if valid.any():
                np.testing.assert_allclose(
                    pd_col[valid], pl_col[valid],
                    atol=1e-5, rtol=1e-6,
                    err_msg=f"Numerical mismatch in column '{col}'"
                )


# ─── T4.2: test_polars_l65_vs_pandas_l65 ────────────────────────────────────

class TestPolarsL65VsPandasL65:
    """T4.2: Polars L6.5 preprocessing vs pandas L6.5 — 全量數值等價"""

    def test_polars_l65_vs_pandas_l65(self, sample_layer1_df):
        """測試 Polars L6.5 output 與 pandas L6.5 output 數值等價 (atol=1e-5)"""
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        config = {
            "winsorization": {"enabled": True, "method": "sigma", "sigma_k": 3.0, "apply_to": "all"},
            "rank_transform": {"enabled": True, "window": 20, "apply_to": "all"},
            "adaptive_zscore": {"enabled": True, "windows": [20], "epsilon": 1e-8, "apply_to": "all"},
            "gaussian_normalize": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "fractional_differencing": {"enabled": False},
            "mode": "replace",
        }

        # Pandas path
        preprocessor_pd = FeaturePreprocessor(config)
        os.environ["FFACT_USE_POLARS"] = "0"
        try:
            pandas_result = preprocessor_pd.transform(sample_layer1_df.copy())
        finally:
            os.environ.pop("FFACT_USE_POLARS", None)

        # Polars path
        preprocessor_pl = FeaturePreprocessor(config)
        os.environ["FFACT_USE_POLARS"] = "1"
        try:
            polars_result = preprocessor_pl.transform(sample_layer1_df.copy())
        finally:
            os.environ.pop("FFACT_USE_POLARS", None)

        assert pandas_result.shape == polars_result.shape, (
            f"Shape mismatch: pandas={pandas_result.shape}, polars={polars_result.shape}"
        )
        assert list(pandas_result.columns) == list(polars_result.columns), (
            "Column name mismatch"
        )

        for col in pandas_result.columns:
            pd_col = pandas_result[col].values.astype(np.float64)
            pl_col = polars_result[col].values.astype(np.float64)
            pd_nan = np.isnan(pd_col)
            pl_nan = np.isnan(pl_col)
            np.testing.assert_array_equal(
                pd_nan, pl_nan,
                err_msg=f"NaN pattern mismatch in column '{col}'"
            )
            valid = ~pd_nan
            if valid.any():
                np.testing.assert_allclose(
                    pd_col[valid], pl_col[valid],
                    atol=1e-5, rtol=0,
                    err_msg=f"Numerical mismatch in column '{col}'"
                )


# ─── T4.3: test_polars_nan_min_periods ───────────────────────────────────────

class TestPolarsNanMinPeriods:
    """T4.3: NaN 行數一致（rolling 開頭 NaN pattern）"""

    def test_polars_nan_min_periods(self, sample_layer1_df):
        """測試 Polars path 的 rolling 操作 NaN 行數與 pandas 一致"""
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        config = {
            "winsorization": {"enabled": False},
            "rank_transform": {"enabled": True, "window": 10, "apply_to": "all"},
            "adaptive_zscore": {"enabled": True, "windows": [10], "epsilon": 1e-8, "apply_to": "all"},
            "gaussian_normalize": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "fractional_differencing": {"enabled": False},
            "mode": "replace",
        }

        # Pandas path
        os.environ["FFACT_USE_POLARS"] = "0"
        try:
            pandas_result = FeaturePreprocessor(config).transform(sample_layer1_df.copy())
        finally:
            os.environ.pop("FFACT_USE_POLARS", None)

        # Polars path
        os.environ["FFACT_USE_POLARS"] = "1"
        try:
            polars_result = FeaturePreprocessor(config).transform(sample_layer1_df.copy())
        finally:
            os.environ.pop("FFACT_USE_POLARS", None)

        # Compare NaN counts per column
        for col in pandas_result.columns:
            pd_nan_count = pandas_result[col].isna().sum()
            pl_nan_count = polars_result[col].isna().sum()
            assert pd_nan_count == pl_nan_count, (
                f"NaN count mismatch in '{col}': pandas={pd_nan_count}, polars={pl_nan_count}"
            )


# ─── T4.4: test_polars_division_by_zero ──────────────────────────────────────

class TestPolarsDivisionByZero:
    """T4.4: NaN/inf 行為一致"""

    def test_polars_division_by_zero(self):
        """測試 Polars 除以零行為：inf → NaN 對齊 pandas"""
        from momentum.FeatureEngineering.polars_adapter import (
            pandas_to_polars,
            polars_l2_derived_ratio,
            polars_to_pandas,
        )

        # Create data with zeros in denominator
        n_rows = 20
        index = pd.date_range("2024-01-01", periods=n_rows, freq="1h")
        df = pd.DataFrame({
            "numerator": np.arange(n_rows, dtype=np.float32),
            "denominator": np.array([0.0] * 5 + list(range(1, 16)), dtype=np.float32),
        }, index=index)

        # Pandas: A / B where B has zeros → NaN (via replace(0, nan))
        pd_denom = df["denominator"].replace(0, np.nan)
        pd_ratio = df["numerator"] / pd_denom

        # Polars path
        pairs = [("numerator", "denominator", "ratio_result")]
        pl_df = pandas_to_polars(df)
        pl_result = polars_l2_derived_ratio(pl_df, pairs)
        pl_pandas = polars_to_pandas(pl_result, index=index)

        # Compare: both should have NaN where denominator was 0
        pd_values = pd_ratio.values.astype(np.float64)
        pl_values = pl_pandas["ratio_result"].values.astype(np.float64)

        pd_nan = np.isnan(pd_values)
        pl_nan = np.isnan(pl_values)
        np.testing.assert_array_equal(pd_nan, pl_nan, err_msg="NaN pattern mismatch on division by zero")

        valid = ~pd_nan
        if valid.any():
            np.testing.assert_allclose(
                pd_values[valid], pl_values[valid],
                atol=1e-6, rtol=0,
                err_msg="Numerical mismatch after division"
            )


# ─── T4.B1: Polars null vs NaN ───────────────────────────────────────────────

class TestPolarsNullVsNan:
    """T4.B1: Polars null → NaN 統一轉換"""

    def test_polars_null_converted_to_nan(self):
        """測試 Polars null 在轉回 pandas 時統一為 NaN"""
        from momentum.FeatureEngineering.polars_adapter import (
            pandas_to_polars,
            polars_to_pandas,
        )

        # Create DataFrame with NaN
        df = pd.DataFrame({
            "a": [1.0, np.nan, 3.0, np.nan, 5.0],
            "b": [np.nan, 2.0, np.nan, 4.0, np.nan],
        }, dtype=np.float32)

        # Convert to Polars (NaN → null in Polars)
        pl_df = pandas_to_polars(df)

        # Verify nulls exist
        assert pl_df["a"].null_count() > 0 or pl_df["a"].is_nan().sum() > 0

        # Convert back to pandas
        result = polars_to_pandas(pl_df)

        # All original NaN positions should be NaN in result
        for col in df.columns:
            original_nan = df[col].isna()
            result_nan = result[col].isna()
            np.testing.assert_array_equal(
                original_nan.values, result_nan.values,
                err_msg=f"NaN/null mismatch in column '{col}'"
            )

    def test_polars_inf_converted_to_nan(self):
        """測試 Polars inf 在 ensure_nan_semantics 後轉為 null/NaN"""
        from momentum.FeatureEngineering.polars_adapter import (
            ensure_nan_semantics,
            polars_to_pandas,
        )
        import polars as pl

        pl_df = pl.DataFrame({
            "a": [1.0, float("inf"), -float("inf"), 4.0, float("nan")],
        })

        # Apply nan semantics
        cleaned = ensure_nan_semantics(pl_df)
        result = polars_to_pandas(cleaned)

        # inf should become NaN
        assert np.isnan(result["a"].iloc[1]), "inf should become NaN"
        assert np.isnan(result["a"].iloc[2]), "-inf should become NaN"
        assert np.isnan(result["a"].iloc[4]), "NaN should stay NaN"
        assert result["a"].iloc[0] == 1.0, "Normal value should be preserved"
        assert result["a"].iloc[3] == 4.0, "Normal value should be preserved"


# ─── T4.B2: float64 → float32 精度損失 ──────────────────────────────────────

class TestFloat32Precision:
    """T4.B2: float64 → float32 precision loss < 1e-6"""

    def test_float32_precision_loss(self):
        """測試 float64→float32 精度損失在可接受範圍內"""
        from momentum.FeatureEngineering.polars_adapter import (
            pandas_to_polars,
            polars_to_pandas,
        )

        # Create float64 data with varied magnitudes
        np.random.seed(99)
        data = np.random.randn(100, 10) * 1000  # Large values
        df = pd.DataFrame(data, columns=[f"col_{i}" for i in range(10)])

        # Round-trip: pandas(f64) → polars(f32) → pandas(f32)
        pl_df = pandas_to_polars(df)
        result = polars_to_pandas(pl_df)

        # Check precision loss
        for col in df.columns:
            original = df[col].values.astype(np.float32)
            converted = result[col].values
            max_diff = np.max(np.abs(original - converted))
            assert max_diff < 1e-6, (
                f"Precision loss too large in '{col}': max_diff={max_diff}"
            )


# ─── T4.B3: Empty DataFrame ─────────────────────────────────────────────────

class TestEmptyDataFrame:
    """T4.B3: 空 DataFrame 正確處理"""

    def test_polars_empty_df_l2(self):
        """測試空 DataFrame 通過 Polars L2 path 不 crash"""
        from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine

        config = {
            "enabled": True,
            "ratio": {"enabled": True},
            "cross": {"enabled": True},
            "momentum": {"enabled": True, "lags": [1, 5]},
            "distance": {"enabled": False},
            "binary_signal": {"enabled": False},
            "signed_strength": {"enabled": False},
            "worldquant": {"enabled": False},
        }
        engine = DerivedOperatorEngine(config)
        empty = pd.DataFrame(dtype=np.float32)
        raw = pd.DataFrame({"close": []}, dtype=np.float32)

        result = engine.compute_all_polars(empty, raw, {})
        assert result.empty

    def test_polars_empty_df_l65(self):
        """測試空 DataFrame 通過 Polars L6.5 path 不 crash"""
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        config = {
            "winsorization": {"enabled": True, "method": "sigma", "sigma_k": 3.0, "apply_to": "all"},
            "rank_transform": {"enabled": True, "window": 20, "apply_to": "all"},
            "adaptive_zscore": {"enabled": True, "windows": [20], "apply_to": "all"},
            "gaussian_normalize": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "fractional_differencing": {"enabled": False},
            "mode": "replace",
        }

        preprocessor = FeaturePreprocessor(config)
        empty = pd.DataFrame(dtype=np.float32)

        os.environ["FFACT_USE_POLARS"] = "1"
        try:
            result = preprocessor.transform(empty)
        finally:
            os.environ.pop("FFACT_USE_POLARS", None)

        assert result.empty or result.shape[0] == 0

    def test_polars_all_nan_df_l65(self, all_nan_df):
        """測試全 NaN DataFrame 通過 Polars L6.5 path 不 crash"""
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        config = {
            "winsorization": {"enabled": True, "method": "sigma", "sigma_k": 3.0, "apply_to": "all"},
            "rank_transform": {"enabled": True, "window": 20, "apply_to": "all"},
            "adaptive_zscore": {"enabled": True, "windows": [20], "apply_to": "all"},
            "gaussian_normalize": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "fractional_differencing": {"enabled": False},
            "mode": "replace",
        }

        preprocessor = FeaturePreprocessor(config)

        os.environ["FFACT_USE_POLARS"] = "1"
        try:
            result = preprocessor.transform(all_nan_df.copy())
        finally:
            os.environ.pop("FFACT_USE_POLARS", None)

        # All NaN input should produce all NaN output (or constant fills)
        assert result.shape == all_nan_df.shape
        # Winsorization on all NaN → NaN (no valid std)
        # rank on all NaN → NaN
        # zscore on all NaN → NaN
        for col in result.columns:
            assert result[col].isna().all(), f"Expected all NaN in '{col}' but got non-NaN values"


# ─── Additional: polars_adapter unit tests ───────────────────────────────────

class TestPolarsAdapter:
    """Polars adapter 基礎功能測試"""

    def test_polars_enabled_default_off(self):
        """測試 FFACT_USE_POLARS 預設為關閉"""
        from momentum.FeatureEngineering.polars_adapter import polars_enabled

        os.environ.pop("FFACT_USE_POLARS", None)
        assert not polars_enabled()

    def test_polars_enabled_on(self):
        """測試 FFACT_USE_POLARS=1 啟用"""
        from momentum.FeatureEngineering.polars_adapter import polars_enabled

        os.environ["FFACT_USE_POLARS"] = "1"
        try:
            assert polars_enabled()
        finally:
            os.environ.pop("FFACT_USE_POLARS", None)

    def test_pandas_to_polars_roundtrip(self, sample_layer1_df):
        """測試 pandas → polars → pandas 完整 roundtrip"""
        from momentum.FeatureEngineering.polars_adapter import (
            pandas_to_polars,
            polars_to_pandas,
        )

        pl_df = pandas_to_polars(sample_layer1_df)
        result = polars_to_pandas(pl_df, index=sample_layer1_df.index)

        assert result.shape == sample_layer1_df.shape
        assert list(result.columns) == list(sample_layer1_df.columns)

        for col in sample_layer1_df.columns:
            original = sample_layer1_df[col].values.astype(np.float32)
            converted = result[col].values.astype(np.float32)
            orig_nan = np.isnan(original)
            conv_nan = np.isnan(converted)
            np.testing.assert_array_equal(orig_nan, conv_nan)
            valid = ~orig_nan
            if valid.any():
                np.testing.assert_allclose(
                    original[valid], converted[valid], atol=1e-7, rtol=0
                )

    def test_ensure_nan_semantics_no_inf(self):
        """測試 ensure_nan_semantics 不影響正常數值"""
        from momentum.FeatureEngineering.polars_adapter import ensure_nan_semantics
        import polars as pl

        pl_df = pl.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
        result = ensure_nan_semantics(pl_df)
        assert result["a"].to_list() == [1.0, 2.0, 3.0]
        assert result["b"].to_list() == [4.0, 5.0, 6.0]


# ─── Real H5 integration test ────────────────────────────────────────────────

class TestPolarsRealH5:
    """使用真實 h5 資料的整合測試"""

    KLINE_PATH = "/Users/louis/Desktop/quantitative_trading_system/data_cache/kline_cache.h5"

    @pytest.fixture
    def real_kline_data(self):
        """載入真實 ETHUSDT 1h K-line 資料"""
        import h5py

        if not os.path.exists(self.KLINE_PATH):
            pytest.skip("Kline cache not available")

        try:
            with h5py.File(self.KLINE_PATH, "r") as f:
                # Try common group patterns
                for key in ["ETHUSDT/1h", "ETHUSDT_1h", "ETHUSDT"]:
                    if key in f:
                        group = f[key]
                        if "data" in group:
                            data = group["data"][:]
                            break
                        if "klines" in group:
                            data = group["klines"][:]
                            break
                        if hasattr(group, "shape"):
                            data = group[:]
                            break
                else:
                    available = list(f.keys())
                    pytest.skip(f"No ETHUSDT data found. Available: {available[:5]}")
        except Exception as e:
            pytest.skip(f"Cannot read kline h5: {e}")

        # Build DataFrame — handle structured array (named fields) or 2D array
        if data.dtype.names:
            # Structured array with named fields
            df = pd.DataFrame({
                "open": data["open"].astype(np.float64),
                "high": data["high"].astype(np.float64),
                "low": data["low"].astype(np.float64),
                "close": data["close"].astype(np.float64),
                "volume": data["volume"].astype(np.float64),
            })
            if "timestamp" in data.dtype.names:
                df.index = pd.to_datetime(data["timestamp"].astype(np.int64), unit="ms")
        elif data.ndim == 2 and data.shape[1] >= 5:
            df = pd.DataFrame({
                "open": data[:, 1].astype(np.float64),
                "high": data[:, 2].astype(np.float64),
                "low": data[:, 3].astype(np.float64),
                "close": data[:, 4].astype(np.float64),
                "volume": data[:, 5].astype(np.float64) if data.shape[1] > 5 else np.ones(len(data)),
            })
            if data.shape[1] > 0:
                timestamps = pd.to_datetime(data[:, 0].astype(np.int64), unit="ms")
                df.index = timestamps
        else:
            pytest.skip("Unexpected data shape in kline h5")

        return df

    def test_polars_l2_with_real_data(self, real_kline_data):
        """測試 Polars L2 path 在真實資料上正常運行"""
        from momentum.FeatureEngineering.polars_adapter import (
            pandas_to_polars,
            polars_l2_derived_momentum,
            polars_l2_derived_ratio,
            polars_to_pandas,
        )

        # Create simple L1-like features from real data
        df = real_kline_data  # Use all available rows
        n_rows = len(df)
        layer1 = pd.DataFrame({
            "close_trend_EMA_5": df["close"].ewm(span=5).mean().astype(np.float32),
            "close_trend_EMA_20": df["close"].ewm(span=20).mean().astype(np.float32),
            "close_trend_EMA_50": df["close"].ewm(span=50).mean().astype(np.float32),
        }, index=df.index)

        pl_l1 = pandas_to_polars(layer1)

        # Test ratio
        ratio_pairs = [
            ("close_trend_EMA_5", "close_trend_EMA_20", "EMA_5_20_Ratio"),
            ("close_trend_EMA_5", "close_trend_EMA_50", "EMA_5_50_Ratio"),
        ]
        ratio_result = polars_l2_derived_ratio(pl_l1, ratio_pairs)
        assert ratio_result.shape[0] == n_rows
        assert ratio_result.shape[1] == 2

        # Test momentum
        momentum_specs = [
            ("close_trend_EMA_5", 1, "EMA_5_Mom_L1"),
            ("close_trend_EMA_5", 5, "EMA_5_Mom_L5"),
        ]
        momentum_result = polars_l2_derived_momentum(pl_l1, momentum_specs)
        assert momentum_result.shape[0] == n_rows
        assert momentum_result.shape[1] == 2

        # Verify no inf in results
        ratio_pd = polars_to_pandas(ratio_result, index=df.index)
        assert not np.any(np.isinf(ratio_pd.values[~np.isnan(ratio_pd.values)]))

    def test_polars_l65_with_real_data(self, real_kline_data):
        """測試 Polars L6.5 path 在真實資料上正常運行"""
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        # Create simple features from real data
        df = real_kline_data
        features = pd.DataFrame({
            "close_ema5": df["close"].ewm(span=5).mean().astype(np.float32),
            "close_ema20": df["close"].ewm(span=20).mean().astype(np.float32),
            "volume_sma10": df["volume"].rolling(10).mean().astype(np.float32),
        }, index=df.index)

        config = {
            "winsorization": {"enabled": True, "method": "sigma", "sigma_k": 3.0, "apply_to": "all"},
            "rank_transform": {"enabled": True, "window": 50, "apply_to": "all"},
            "adaptive_zscore": {"enabled": True, "windows": [50], "epsilon": 1e-8, "apply_to": "all"},
            "gaussian_normalize": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "fractional_differencing": {"enabled": False},
            "mode": "replace",
        }

        # Pandas path
        os.environ["FFACT_USE_POLARS"] = "0"
        try:
            pd_result = FeaturePreprocessor(config).transform(features.copy())
        finally:
            os.environ.pop("FFACT_USE_POLARS", None)

        # Polars path
        os.environ["FFACT_USE_POLARS"] = "1"
        try:
            pl_result = FeaturePreprocessor(config).transform(features.copy())
        finally:
            os.environ.pop("FFACT_USE_POLARS", None)

        assert pd_result.shape == pl_result.shape

        # Compare results — allow up to 1 extra leading NaN from Polars
        # (rolling_std with ddof=1 on single point → null is a known edge case)
        for col in pd_result.columns:
            pd_vals = pd_result[col].values.astype(np.float64)
            pl_vals = pl_result[col].values.astype(np.float64)
            pd_nan = np.isnan(pd_vals)
            pl_nan = np.isnan(pl_vals)

            # Polars may have extra leading NaN due to rolling std ddof=1 edge
            extra_nan = int(np.sum(pl_nan)) - int(np.sum(pd_nan))
            assert extra_nan <= 1, (
                f"Too many extra NaN in '{col}': polars has {extra_nan} more NaN than pandas"
            )

            # Compare on mutually valid rows
            both_valid = ~pd_nan & ~pl_nan
            if both_valid.any():
                np.testing.assert_allclose(
                    pd_vals[both_valid], pl_vals[both_valid],
                    atol=5e-4, rtol=0,
                    err_msg=f"Numerical mismatch in '{col}' with real data"
                )
