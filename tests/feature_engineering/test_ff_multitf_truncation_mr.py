"""P0-FF-3 — 多 TF 全鏈 bar 級截斷 MR + 對齊 look-ahead mutation。

primary=1h, training=[1h,4h,12h], open_minus, BTCUSDT。
複用 ff_truncation_mr_helpers（B2 收斂 gate + 對齊層覆蓋守衛）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.operators.lag_processor import LagProcessor
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner
from momentum.factories import create_kline_storage_manager

from tests.feature_engineering.ff_truncation_mr_helpers import (
    ALIGN_MARGIN,
    GenerationArtifacts,
    KLINE_CACHE_DIR,
    PERTURB_DELTA,
    SYMBOL,
    TRUNC_K,
    TruncationPair,
    _assert_align_coarse_boundary_lookahead_detected,
    _assert_mutation_layer_coverage,
    _assert_truncation_invariants,
    _assert_values_gate_main,
    _assert_warmup_nan_masks_equal,
    _bar_window_dates_at_12h_boundary,
    _build_column_frame_map,
    _build_sampled_columns,
    _build_truncation_pair,
    _coarse_tf_from_column,
    _ensure_module_env,
    _ORIGINAL_BUILD_ASOF_INDEX_MAP,
    _patch_kline_tail_ohlcv,
    _required_window_bars,
    _values_gate_mr_config_payload,
)

pytestmark = [pytest.mark.requires_kline, pytest.mark.slow]

PRIMARY_TF = "1h"
TRAINING_TFS = ["1h", "4h", "12h"]
ALIGN_COARSE_TFS = ["4h", "12h"]
EXPECTED_TRAINING_TFS = TRAINING_TFS


def _multitf_config_payload() -> dict[str, Any]:
    return _values_gate_mr_config_payload(
        primary_tf=PRIMARY_TF,
        training_tfs=TRAINING_TFS,
        alignment_mode="open_minus",
    )


def _multitf_window_bars() -> int:
    return _required_window_bars(
        _multitf_config_payload(),
        primary_tf=PRIMARY_TF,
        training_tfs=TRAINING_TFS,
        align_margin=ALIGN_MARGIN,
    )


@pytest.fixture(scope="module")
def kline_df_module() -> pd.DataFrame:
    storage = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    df = storage.read_klines(SYMBOL, PRIMARY_TF, validate_continuity=False)
    if df is None or df.empty:
        pytest.fail(f"missing kline: {SYMBOL}/{PRIMARY_TF}")
    return df


@pytest.fixture(scope="module")
def module_features_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    _ensure_module_env()
    return tmp_path_factory.mktemp("c3_features")


@pytest.fixture(scope="module")
def multitf_window_bars() -> int:
    return _multitf_window_bars()


@pytest.fixture(scope="module")
def multitf_mr_pair(
    module_features_root: Path,
    kline_df_module: pd.DataFrame,
    multitf_window_bars: int,
) -> TruncationPair:
    """共用 multi-TF full+trunc baseline。"""
    return _build_truncation_pair(
        module_features_root,
        kline_df_module,
        config_payload=_multitf_config_payload(),
        primary_tf=PRIMARY_TF,
        training_tfs=TRAINING_TFS,
        window_bars=multitf_window_bars,
        align_margin=ALIGN_MARGIN,
    )


def test_c3_multitf_truncation_invariant(multitf_mr_pair: TruncationPair) -> None:
    """C3：multi-TF 截斷尾 k bars → warmup 後前綴因果穩定（含對齊層/metadata）。"""
    _assert_truncation_invariants(
        multitf_mr_pair,
        align_coarse_tfs=ALIGN_COARSE_TFS,
        expected_training_tfs=EXPECTED_TRAINING_TFS,
    )


def test_c3_multitf_tail_perturbation_prefix_invariant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
    multitf_window_bars: int,
) -> None:
    """C3-2：尾 k bar OHLCV ±1e6 → 截斷點前（含 warmup mask）不變。"""
    pair = _build_truncation_pair(
        tmp_path / "features",
        kline_df_module,
        config_payload=_multitf_config_payload(),
        primary_tf=PRIMARY_TF,
        training_tfs=TRAINING_TFS,
        window_bars=multitf_window_bars,
        align_margin=ALIGN_MARGIN,
        patch_fetch=lambda df: _patch_kline_tail_ohlcv(df, k=TRUNC_K, delta=PERTURB_DELTA),
        monkeypatch=monkeypatch,
    )
    _assert_truncation_invariants(
        pair,
        align_coarse_tfs=ALIGN_COARSE_TFS,
        expected_training_tfs=EXPECTED_TRAINING_TFS,
    )


def test_mutation_align_lookahead_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
    multitf_window_bars: int,
) -> None:
    """M3-1：對齊 build_asof_index_map +1 forward 偏置（僅 trunc 側）→ MR/oracle 必 FAIL。"""
    # 靜態探針錨：顯式觸碰對齊層；實際注入由 align_lookahead_side 不對稱切換
    monkeypatch.setattr(
        TimeframeAligner,
        "build_asof_index_map",
        staticmethod(_ORIGINAL_BUILD_ASOF_INDEX_MAP),
    )
    pair = _build_truncation_pair(
        tmp_path / "features",
        kline_df_module,
        config_payload=_multitf_config_payload(),
        primary_tf=PRIMARY_TF,
        training_tfs=TRAINING_TFS,
        window_bars=multitf_window_bars,
        align_margin=ALIGN_MARGIN,
        window_date_fn=_bar_window_dates_at_12h_boundary,
        align_lookahead_side="trunc",
        monkeypatch=monkeypatch,
    )
    _assert_align_coarse_boundary_lookahead_detected(
        pair, align_coarse_tfs=ALIGN_COARSE_TFS
    )
    with pytest.raises(AssertionError):
        _assert_truncation_invariants(
            pair,
            align_coarse_tfs=ALIGN_COARSE_TFS,
            expected_training_tfs=EXPECTED_TRAINING_TFS,
        )


def test_mutation_align_lookahead_with_tail_perturb_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
    multitf_window_bars: int,
) -> None:
    """M3-2：align lookahead（僅 trunc 側）+ 尾 k OHLCV ±1e6 → MR/oracle 必 FAIL。"""
    monkeypatch.setattr(
        TimeframeAligner,
        "build_asof_index_map",
        staticmethod(_ORIGINAL_BUILD_ASOF_INDEX_MAP),
    )
    pair = _build_truncation_pair(
        tmp_path / "features",
        kline_df_module,
        config_payload=_multitf_config_payload(),
        primary_tf=PRIMARY_TF,
        training_tfs=TRAINING_TFS,
        window_bars=multitf_window_bars,
        align_margin=ALIGN_MARGIN,
        window_date_fn=_bar_window_dates_at_12h_boundary,
        patch_fetch=lambda df: _patch_kline_tail_ohlcv(df, k=TRUNC_K, delta=PERTURB_DELTA),
        align_lookahead_side="trunc",
        monkeypatch=monkeypatch,
    )
    _assert_align_coarse_boundary_lookahead_detected(
        pair, align_coarse_tfs=ALIGN_COARSE_TFS
    )
    with pytest.raises(AssertionError):
        _assert_truncation_invariants(
            pair,
            align_coarse_tfs=ALIGN_COARSE_TFS,
            expected_training_tfs=EXPECTED_TRAINING_TFS,
        )


def test_mutation_numba_rolling_center_true_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
    multitf_window_bars: int,
) -> None:
    """B2 mutant①（multi-TF config）：L3 center=True → 截斷 MR 必 FAIL。"""
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
            config_payload=_multitf_config_payload(),
            primary_tf=PRIMARY_TF,
            training_tfs=TRAINING_TFS,
            window_bars=multitf_window_bars,
            align_margin=ALIGN_MARGIN,
            monkeypatch=monkeypatch,
        )
        _assert_truncation_invariants(
            pair,
            align_coarse_tfs=ALIGN_COARSE_TFS,
            expected_training_tfs=EXPECTED_TRAINING_TFS,
        )


def test_mutation_causal_winsor_full_fit_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
    multitf_window_bars: int,
) -> None:
    """B2 mutant②（multi-TF config）：causal winsor 全量 fit → 截斷 MR 必 FAIL。"""
    def _full_fit_winsor(self: FeaturePreprocessor, df: pd.DataFrame) -> pd.DataFrame:
        apply_to = self.winsor_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        if not columns:
            return df
        result = df.copy()
        selected = result.loc[:, columns].astype(float)
        mean = selected.mean()
        std = selected.std()
        lower = mean - float(self.winsor_config.get("sigma_k", 3.0)) * std
        upper = mean + float(self.winsor_config.get("sigma_k", 3.0)) * std
        result.loc[:, columns] = selected.clip(lower=lower, upper=upper, axis=1).astype(np.float32)
        return result

    monkeypatch.setattr(FeaturePreprocessor, "_apply_winsorization", _full_fit_winsor)
    with pytest.raises(AssertionError):
        pair = _build_truncation_pair(
            tmp_path / "features",
            kline_df_module,
            config_payload=_multitf_config_payload(),
            primary_tf=PRIMARY_TF,
            training_tfs=TRAINING_TFS,
            window_bars=multitf_window_bars,
            align_margin=ALIGN_MARGIN,
            monkeypatch=monkeypatch,
        )
        _assert_truncation_invariants(
            pair,
            align_coarse_tfs=ALIGN_COARSE_TFS,
            expected_training_tfs=EXPECTED_TRAINING_TFS,
        )


def test_mutation_l4_lag_shift_minus_one_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
    multitf_window_bars: int,
) -> None:
    """B2 mutant③（multi-TF config）：L4 shift(-lag) → 尾端擾動前綴 MR 必 FAIL。"""
    original_compute_all = LagProcessor.compute_all
    original_shift = pd.DataFrame.shift

    def _lookahead_compute_all(self: LagProcessor, features_df: pd.DataFrame) -> pd.DataFrame:
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
            config_payload=_multitf_config_payload(),
            primary_tf=PRIMARY_TF,
            training_tfs=TRAINING_TFS,
            window_bars=multitf_window_bars,
            align_margin=ALIGN_MARGIN,
            patch_fetch=lambda df: _patch_kline_tail_ohlcv(df, k=TRUNC_K, delta=PERTURB_DELTA),
            monkeypatch=monkeypatch,
        )
        _assert_truncation_invariants(
            pair,
            align_coarse_tfs=ALIGN_COARSE_TFS,
            expected_training_tfs=EXPECTED_TRAINING_TFS,
        )


def test_multitf_sampling_helper_smoke(tmp_path: Path) -> None:
    """秒級 smoke：multi-TF 對齊層探針 + 分層抽樣（非全鏈 generate）。"""
    full_dir = tmp_path / "full"
    trunc_dir = tmp_path / "trunc"
    full_dir.mkdir()
    trunc_dir.mkdir()

    warmup, n_trunc = 5, 20
    rows = np.arange(n_trunc, dtype=np.float32)
    full_rows = np.concatenate([rows, np.full(TRUNC_K, 999.0, dtype=np.float32)])

    l3_cols = [f"close_trend_EMA_5_mean_W{w}" for w in (10, 20, 30)]
    l4_cols = [f"close_trend_EMA_5_Lag_{lag}" for lag in (1, 2)]
    align_4h = [f"close_4h_trend_EMA_5", f"volume_4h_raw"]
    align_12h = [f"close_12h_trend_EMA_5", f"volume_12h_raw"]
    filler = [f"close_volatility_ATR_14_mean_W{w}" for w in range(80)]
    all_cols = l3_cols + l4_cols + align_4h + align_12h + filler

    def _write_pair(name: str, cols: List[str]) -> None:
        full_df = pd.DataFrame({col: full_rows + 0.01 * i for i, col in enumerate(cols)})
        trunc_df = pd.DataFrame({col: rows + 0.01 * i for i, col in enumerate(cols)})
        full_df.to_parquet(full_dir / name)
        trunc_df.to_parquet(trunc_dir / name)

    _write_pair("1h_L3_rolling.parquet", l3_cols + filler[:40])
    _write_pair("1h_L4_lag.parquet", l4_cols)
    _write_pair("1h_L1_4h_trend.parquet", align_4h)
    _write_pair("1h_L1_12h_trend.parquet", align_12h)
    _write_pair("1h_L3_rolling_2.parquet", filler[40:])

    common_cols = sorted(set(all_cols))
    col_map = _build_column_frame_map(full_dir)
    sampled, report = _build_sampled_columns(
        common_cols, col_map, align_coarse_tfs=ALIGN_COARSE_TFS
    )

    assert report.required_probe_count >= 3
    coarse_in_sample = {_coarse_tf_from_column(c) for c in sampled}
    assert "4h" in coarse_in_sample
    assert "12h" in coarse_in_sample
    _assert_mutation_layer_coverage(sampled, col_map, align_coarse_tfs=ALIGN_COARSE_TFS)

    sampled_cols, full_map = _assert_values_gate_main(
        full_dir,
        trunc_dir,
        warmup=warmup,
        n_trunc=n_trunc,
        align_coarse_tfs=ALIGN_COARSE_TFS,
    )
    _assert_warmup_nan_masks_equal(
        full_dir,
        trunc_dir,
        warmup=warmup,
        n_trunc=n_trunc,
        sampled_cols=sampled_cols,
        col_to_parquet=full_map,
    )


def test_align_lookahead_oracle_smoke(tmp_path: Path) -> None:
    """smoke,非驗收證據：12h 邊界 oracle 在 synthetic mismatch 時可偵測差異。"""
    full_dir = tmp_path / "full"
    trunc_dir = tmp_path / "trunc"
    full_dir.mkdir()
    trunc_dir.mkdir()

    warmup, n_trunc = 5, 24
    h1 = 3600
    # 11:00 open → 12:00 close 落 12h grid（與 _is_12h_close_boundary_bar_open 一致）
    first_open = int(pd.Timestamp("2026-01-01 11:00:00").timestamp())
    ts_vals = np.array(
        [first_open + i * h1 for i in range(n_trunc)],
        dtype=np.int64,
    )
    boundary_idxs = [
        i
        for i in range(warmup, n_trunc)
        if (int(ts_vals[i]) + h1) % (12 * h1) == 0
    ]
    assert boundary_idxs, "smoke fixture must include a 12h boundary row"

    col = "close_12h_trend_EMA_5"
    full_rows = np.linspace(1.0, 2.0, n_trunc, dtype=np.float32)
    trunc_rows = full_rows.copy()
    trunc_rows[boundary_idxs[0]] = full_rows[boundary_idxs[0]] + 0.5

    pd.DataFrame({col: full_rows}).to_parquet(full_dir / "1h_L1_12h_trend.parquet")
    pd.DataFrame({col: trunc_rows}).to_parquet(trunc_dir / "1h_L1_12h_trend.parquet")

    run_trunc = tmp_path / "run_trunc"
    run_trunc.mkdir()
    pd.DataFrame({"timestamp": ts_vals}).to_parquet(run_trunc / "timestamps.parquet")
    row_index = {
        "path": "timestamps.parquet",
        "count": n_trunc,
        "unit": "s",
        "tz": "UTC",
    }

    pair = TruncationPair(
        warmup=warmup,
        n_trunc=n_trunc,
        full=GenerationArtifacts(
            raw_dir=full_dir,
            run_dir=tmp_path / "run_full",
            metadata={},
            manifest={},
            row_count=n_trunc,
        ),
        trunc=GenerationArtifacts(
            raw_dir=trunc_dir,
            run_dir=run_trunc,
            metadata={},
            manifest={"row_index": row_index},
            row_count=n_trunc,
        ),
    )
    _assert_align_coarse_boundary_lookahead_detected(
        pair, align_coarse_tfs=ALIGN_COARSE_TFS
    )
