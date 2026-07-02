"""P0-FF-2 Task 2.1/2.2 — 全鏈 bar 級截斷 MR + 尾端擾動 MR + fracdiff 專屬 MR。

主 MR（三方收斂 B2 設計，見 handoffs/20260629-FF-B2-CAUSALITY-SIGNOFF-RECONCILE.md §二）：
- columns gate：交集；不對稱掉欄 > max(100, 0.1%×|union|) 才 fail
- values gate：交集欄 × [warmup:n_trunc) × both-non-NaN，allclose(rtol=2e-3, atol=1e-12)
- NaN mask 分層：fill_rate≥95% 共同欄 exact mask；低 fill_rate informational
- 覆蓋率守衛：≥95% 共同欄有 post-warmup both-non-NaN cell
明確全開 atomic + preprocessing（含 gaussian），排除 fracdiff/adf。
fracdiff 專屬 MR 維持嚴格（columns equality、d-star、atol=1e-8、exact NaN mask）。
L7 dead_drop 在測試 config 關閉：其 min_valid 依總列數，非因果計算洩漏。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.operators.lag_processor import LagProcessor
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.factories import create_kline_storage_manager

from tests.feature_engineering.ff_truncation_mr_helpers import (
    FRACDIFF_ATOL,
    KLINE_CACHE_DIR,
    PERTURB_DELTA,
    SYMBOL,
    TIMEFRAME,
    TRUNC_K,
    TruncationPair,
    _assert_fracdiff_truncation_invariants,
    _assert_mutation_layer_coverage,
    _assert_truncation_invariants,
    _assert_values_gate_main,
    _assert_warmup_nan_masks_equal,
    _build_column_frame_map,
    _build_sampled_columns,
    _build_truncation_pair,
    _ensure_module_env,
    _fracdiff_mr_config_payload,
    _fracdiff_window_bars,
    _patch_kline_calibration_ohlcv,
    _patch_kline_tail_ohlcv,
    _required_window_bars,
    _values_gate_mr_config_payload,
)

pytestmark = [pytest.mark.requires_kline, pytest.mark.slow]


@pytest.fixture(scope="module")
def kline_df_module() -> pd.DataFrame:
    storage = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    df = storage.read_klines(SYMBOL, TIMEFRAME, validate_continuity=False)
    if df is None or df.empty:
        pytest.fail(f"missing kline: {SYMBOL}/{TIMEFRAME}")
    return df


@pytest.fixture(scope="module")
def module_features_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    _ensure_module_env()
    return tmp_path_factory.mktemp("c2_features")


@pytest.fixture(scope="module")
def values_gate_window_bars() -> int:
    return _required_window_bars(_values_gate_mr_config_payload())


@pytest.fixture(scope="module")
def values_gate_mr_pair(
    module_features_root: Path,
    kline_df_module: pd.DataFrame,
    values_gate_window_bars: int,
) -> TruncationPair:
    """共用 full+trunc baseline（test_c2_1 不重跑 generate_features）。"""
    return _build_truncation_pair(
        module_features_root,
        kline_df_module,
        config_payload=_values_gate_mr_config_payload(),
        window_bars=values_gate_window_bars,
    )


def test_c2_1_fullchain_bar_truncation_invariant(values_gate_mr_pair: TruncationPair) -> None:
    """C2-1：截斷尾 k bars → warmup 後前綴因果穩定（交集+分層 gate）。"""
    _assert_truncation_invariants(values_gate_mr_pair)


def test_c2_2_tail_perturbation_prefix_invariant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
) -> None:
    """C2-2：尾 k bar OHLCV ±1e6 → 截斷點前（含 warmup mask）不變。"""
    pair = _build_truncation_pair(
        tmp_path / "features",
        kline_df_module,
        config_payload=_values_gate_mr_config_payload(),
        patch_fetch=lambda df: _patch_kline_tail_ohlcv(df, k=TRUNC_K, delta=PERTURB_DELTA),
        monkeypatch=monkeypatch,
    )
    _assert_truncation_invariants(pair)


# 2026-07-02 三方委員會定案(20260702-FF-DSTAR-GATE-{CLAUDE,CODEX,COMPOSER}):
# fracdiff max_lag = min(max(2, len(df)//10), 252) 以「整段長度」推導,把總長度洩進
# d* 計算(full 600→60, trunc 590→59)→ d* 差一格網格 → 截斷不變性破壞。
# 非 look-ahead(d* 校準只吃 first-500 prefix,不用未來值),量化因果安全,但屬真實作缺陷。
# 修法=max_lag 改由 calibration/固定推導,會改變全部 fracdiff 特徵值 → 獨立 epic
# (ROADMAP「fracdiff max_lag 截斷不變修復」,併 P1-FF-6,FF 深稽完成後執行,修完本 xfail 應轉綠)。
@pytest.mark.xfail(
    strict=True,
    reason="fracdiff max_lag 長度依賴(len(df)//10)破壞截斷不變;非 look-ahead;修法在 d*/max_lag epic",
)
def test_fracdiff_truncation_invariant(
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
) -> None:
    """fracdiff MR：600→590、d-star 相同、fracdiff 值 atol≤1e-8、NaN mask exact。"""
    pair = _build_truncation_pair(
        tmp_path / "features",
        kline_df_module,
        config_payload=_fracdiff_mr_config_payload(),
        window_bars=_fracdiff_window_bars(_fracdiff_mr_config_payload()),
        d_star_parent=tmp_path / "dstar",
    )
    _assert_fracdiff_truncation_invariants(pair)


# 同上:max_lag 長度依賴,見 test_fracdiff_truncation_invariant 註解與委員會三腿檔。
@pytest.mark.xfail(
    strict=True,
    reason="fracdiff max_lag 長度依賴(len(df)//10)破壞截斷不變;非 look-ahead;修法在 d*/max_lag epic",
)
def test_fracdiff_tail_perturbation_invariant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
) -> None:
    """fracdiff：尾端擾動僅在 calibration 之後；d-star 與前綴 fracdiff 不變。"""
    pair = _build_truncation_pair(
        tmp_path / "features",
        kline_df_module,
        config_payload=_fracdiff_mr_config_payload(),
        window_bars=_fracdiff_window_bars(_fracdiff_mr_config_payload()),
        d_star_parent=tmp_path / "dstar_tail",
        patch_fetch=lambda df: _patch_kline_tail_ohlcv(df, k=TRUNC_K, delta=PERTURB_DELTA),
        monkeypatch=monkeypatch,
    )
    _assert_fracdiff_truncation_invariants(pair)


def test_mutation_numba_rolling_center_true_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
) -> None:
    """C2 mutant①：L3 numba rolling 改 center=True → 截斷 MR 必 FAIL。"""
    import momentum.FeatureEngineering.operators.numba_rolling as numba_rolling

    original_multi = numba_rolling.fused_rolling_stats_multi_window

    def _centered_multi(values: np.ndarray, windows: np.ndarray) -> np.ndarray:
        output = original_multi(values, windows)
        series = pd.Series(np.asarray(values, dtype=np.float64))
        for widx in range(windows.shape[0]):
            window = int(windows[widx])
            if window <= 0:
                continue
            output[:, widx, 0] = series.rolling(window, center=True, min_periods=window).mean().to_numpy()
        return output

    monkeypatch.setattr(numba_rolling, "fused_rolling_stats_multi_window", _centered_multi)
    with pytest.raises(AssertionError):
        pair = _build_truncation_pair(
            tmp_path / "features",
            kline_df_module,
            config_payload=_values_gate_mr_config_payload(),
            monkeypatch=monkeypatch,
        )
        _assert_truncation_invariants(pair)


def test_mutation_causal_winsor_full_fit_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
) -> None:
    """C2 mutant②：causal winsor 改全量 fit → 截斷 MR 必 FAIL。"""
    original = FeaturePreprocessor._apply_winsorization

    def _full_fit_winsor(self: FeaturePreprocessor, df: pd.DataFrame) -> pd.DataFrame:
        apply_to = self.winsor_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        if not columns:
            return df
        result = df.copy()
        selected = result.loc[:, columns].astype(float)
        method = self.winsor_config.get("method", "sigma")
        if method == "quantile":
            qrange = self.winsor_config.get("quantile_range", [0.01, 0.99])
            lower = selected.quantile(float(qrange[0]))
            upper = selected.quantile(float(qrange[1]))
            clipped = selected.clip(lower=lower, upper=upper, axis=1)
        else:
            mean = selected.mean()
            std = selected.std()
            lower = mean - float(self.winsor_config.get("sigma_k", 3.0)) * std
            upper = mean + float(self.winsor_config.get("sigma_k", 3.0)) * std
            clipped = selected.clip(lower=lower, upper=upper, axis=1)
        result.loc[:, columns] = clipped.astype(np.float32)
        return result

    monkeypatch.setattr(FeaturePreprocessor, "_apply_winsorization", _full_fit_winsor)
    with pytest.raises(AssertionError):
        pair = _build_truncation_pair(
            tmp_path / "features",
            kline_df_module,
            config_payload=_values_gate_mr_config_payload(),
            monkeypatch=monkeypatch,
        )
        _assert_truncation_invariants(pair)


def test_mutation_l4_lag_shift_minus_one_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
) -> None:
    """C2 mutant③：L4 lag shift(-lag)（含 fast path）→ 尾端擾動前綴 MR 必 FAIL。"""
    original_compute_all = LagProcessor.compute_all
    original_shift = pd.DataFrame.shift

    def _lookahead_compute_all(self: LagProcessor, features_df: pd.DataFrame) -> pd.DataFrame:
        """覆蓋 fast path 與 chunked path：所有 lag 產出走 shift(-lag)。"""

        def _inverted_shift(
            df: pd.DataFrame,
            periods: int = 1,
            *args: Any,
            **kwargs: Any,
        ) -> pd.DataFrame:
            if isinstance(periods, int) and periods > 0:
                return original_shift(df, -periods, *args, **kwargs)
            return original_shift(df, periods, *args, **kwargs)

        pd.DataFrame.shift = _inverted_shift  # type: ignore[method-assign]
        try:
            return original_compute_all(self, features_df)
        finally:
            pd.DataFrame.shift = original_shift  # type: ignore[method-assign]

    monkeypatch.setattr(LagProcessor, "compute_all", _lookahead_compute_all)
    with pytest.raises(AssertionError):
        pair = _build_truncation_pair(
            tmp_path / "features",
            kline_df_module,
            config_payload=_values_gate_mr_config_payload(),
            patch_fetch=lambda df: _patch_kline_tail_ohlcv(df, k=TRUNC_K, delta=PERTURB_DELTA),
            monkeypatch=monkeypatch,
        )
        _assert_truncation_invariants(pair)


def test_mutation_fracdiff_calibration_perturb_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
) -> None:
    """fracdiff negative control：擾動 calibration 窗內 → fracdiff MR 必 FAIL。"""
    original_calibration = FeaturePreprocessor._calibration_series
    calibration_calls: List[int] = [0]

    def _calibration_spy(self: FeaturePreprocessor, series: pd.Series) -> pd.Series:
        calibration_calls[0] += 1
        return original_calibration(self, series)

    monkeypatch.setattr(FeaturePreprocessor, "_calibration_series", _calibration_spy)
    with pytest.raises(AssertionError):
        pair = _build_truncation_pair(
            tmp_path / "features",
            kline_df_module,
            config_payload=_fracdiff_mr_config_payload(),
            window_bars=_fracdiff_window_bars(_fracdiff_mr_config_payload()),
            d_star_parent=tmp_path / "dstar_mut_cal",
            patch_fetch=lambda df: _patch_kline_calibration_ohlcv(
                df,
                window_bars=_fracdiff_window_bars(_fracdiff_mr_config_payload()),
                calibration_bars=500,
                delta=PERTURB_DELTA,
            ),
            monkeypatch=monkeypatch,
        )
        _assert_fracdiff_truncation_invariants(pair)
    assert calibration_calls[0] > 0, "fracdiff calibration path must be exercised"


def test_mutation_fracdiff_full_fit_d_star_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
) -> None:
    """fracdiff negative control：d-star 改全量 fit → fracdiff MR 必 FAIL。"""
    def _full_series(self: FeaturePreprocessor, series: pd.Series) -> pd.Series:
        return series

    monkeypatch.setattr(FeaturePreprocessor, "_calibration_series", _full_series)
    with pytest.raises(AssertionError):
        pair = _build_truncation_pair(
            tmp_path / "features",
            kline_df_module,
            config_payload=_fracdiff_mr_config_payload(),
            window_bars=_fracdiff_window_bars(_fracdiff_mr_config_payload()),
            d_star_parent=tmp_path / "dstar_mut_full",
            monkeypatch=monkeypatch,
        )
        _assert_fracdiff_truncation_invariants(pair)


def test_b2_sampling_helper_smoke(tmp_path: Path) -> None:
    """秒級 smoke：分層抽樣 + batch 讀邏輯（非全鏈 generate）。"""
    full_dir = tmp_path / "full"
    trunc_dir = tmp_path / "trunc"
    full_dir.mkdir()
    trunc_dir.mkdir()

    warmup, n_trunc = 5, 20
    rows = np.arange(n_trunc, dtype=np.float32)
    full_rows = np.concatenate([rows, np.full(TRUNC_K, 999.0, dtype=np.float32)])

    l3_cols = [f"close_trend_EMA_5_mean_W{w}" for w in (10, 20, 30, 40, 50)]
    l4_cols = [f"close_trend_EMA_5_Lag_{lag}" for lag in (1, 2, 3, 4, 5)]
    l65_cols = [
        "close_trend_EMA_5_rank",
        "close_trend_EMA_5_gaussian",
        "close_trend_EMA_5_zscore_20",
    ]
    filler = [f"close_volatility_ATR_14_mean_W{w}" for w in range(100)]
    all_cols = l3_cols + l4_cols + l65_cols + filler

    full_l3 = pd.DataFrame({col: full_rows + 0.01 * i for i, col in enumerate(l3_cols)})
    trunc_l3 = pd.DataFrame({col: rows + 0.01 * i for i, col in enumerate(l3_cols)})
    full_l3.to_parquet(full_dir / "1h_L3_rolling.parquet")
    trunc_l3.to_parquet(trunc_dir / "1h_L3_rolling.parquet")

    full_l4 = pd.DataFrame({col: full_rows + 0.02 * i for i, col in enumerate(l4_cols)})
    trunc_l4 = pd.DataFrame({col: rows + 0.02 * i for i, col in enumerate(l4_cols)})
    full_l4.to_parquet(full_dir / "1h_L4_lag.parquet")
    trunc_l4.to_parquet(trunc_dir / "1h_L4_lag.parquet")

    full_l65 = pd.DataFrame({col: full_rows + 0.03 * i for i, col in enumerate(l65_cols)})
    trunc_l65 = pd.DataFrame({col: rows + 0.03 * i for i, col in enumerate(l65_cols)})
    full_l65.to_parquet(full_dir / "1h_L1_trend_EMA_5_L65.parquet")
    trunc_l65.to_parquet(trunc_dir / "1h_L1_trend_EMA_5_L65.parquet")

    full_fill = pd.DataFrame({col: full_rows for col in filler})
    trunc_fill = pd.DataFrame({col: rows for col in filler})
    full_fill.to_parquet(full_dir / "1h_L3_rolling_2.parquet")
    trunc_fill.to_parquet(trunc_dir / "1h_L3_rolling_2.parquet")

    common_cols = sorted(set(all_cols))
    col_map = _build_column_frame_map(full_dir)
    sampled, report = _build_sampled_columns(common_cols, col_map)

    assert report.sampled_count >= len({*l3_cols, *l4_cols, *l65_cols})
    assert report.group_count >= 4
    assert report.required_probe_count >= 1
    _assert_mutation_layer_coverage(sampled, col_map)

    sampled_cols, full_map = _assert_values_gate_main(
        full_dir, trunc_dir, warmup=warmup, n_trunc=n_trunc
    )
    _assert_warmup_nan_masks_equal(
        full_dir,
        trunc_dir,
        warmup=warmup,
        n_trunc=n_trunc,
        sampled_cols=sampled_cols,
        col_to_parquet=full_map,
    )
