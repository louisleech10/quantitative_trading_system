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

import numpy as np
import pandas as pd
import pytest

from momentum.factories import create_kline_storage_manager

from tests.feature_engineering.ff_truncation_mr_helpers import (
    KLINE_CACHE_DIR,
    PERTURB_DELTA,
    SYMBOL,
    TIMEFRAME,
    TRUNC_K,
    MRScope,
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
    _patch_kline_tail_ohlcv,
    _required_window_bars,
    _values_gate_mr_config_payload,
    run_control_causal_winsor_full_fit,
    run_control_fracdiff_calibration_perturb,
    run_control_fracdiff_full_fit_d_star,
    run_control_fracdiff_maxlag_len_coupling,
    run_control_l4_lag_shift_minus_one,
    run_control_numba_rolling_center_true,
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "pre-existing materialization 精度路徑截斷變異(B1,非 max_lag;"
        "證據=handoffs/20260703-FRACDIFF-MAXLAG-MRFAIL-RECONCILE.md idx508 artifact);"
        "修法=storage codec/精度 epic"
    ),
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "真實護面（尾擾值級因果比對）暫停——pre-existing storage codec（per-column float16/32 "
        "依全窗值域選型）使跨 run 儲存精度不可比（證據=094044Z dtype dump 2^-7 量化差）；"
        "非 max_lag/conv 問題；storage epic 修 codec 決定論後轉綠"
    ),
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


# FFSTAT SPEC v60 Task 4.2：負控制本體移入 ff_truncation_mr_helpers（與縮小版共用；改前寫法之寬捕獲、max_lag 252 飽和、
# 校準擾動落在公開域三缺陷於共用本體修正）。本檔以全設定呼叫；本機 8GB 無法執行，完整版登大機器驗證清單。
FULL_SCOPE = MRScope(values_payload=_values_gate_mr_config_payload, fracdiff_payload=_fracdiff_mr_config_payload)


def test_mutation_fracdiff_maxlag_len_coupling_truncation_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    """fracdiff mutant：max_lag 依當次長度（不設上限）→ 截斷 MR 必 FAIL。"""
    run_control_fracdiff_maxlag_len_coupling(FULL_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_mutation_fracdiff_maxlag_len_coupling_tail_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    """fracdiff mutant：max_lag 依當次長度 → 尾端擾動 MR 必 FAIL（只承認值 gate 之前之失敗）。"""
    run_control_fracdiff_maxlag_len_coupling(FULL_SCOPE, monkeypatch, tmp_path, kline_df_module, tail_perturb=True)


def test_mutation_fracdiff_maxlag_len_coupling_parallel_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    """fracdiff mutant：parallel slow path 也必須吃到 resolver seam。"""
    run_control_fracdiff_maxlag_len_coupling(FULL_SCOPE, monkeypatch, tmp_path, kline_df_module, parallel=True)


def test_mutation_numba_rolling_center_true_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    """C2 mutant①：L3 numba rolling 改 center=True → 截斷 MR 必 FAIL。"""
    run_control_numba_rolling_center_true(FULL_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_mutation_causal_winsor_full_fit_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    """C2 mutant②：causal winsor 改全量 fit → 截斷 MR 必 FAIL。"""
    run_control_causal_winsor_full_fit(FULL_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_mutation_l4_lag_shift_minus_one_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    """C2 mutant③：L4 lag shift(-lag)（含 fast path）→ 尾端擾動前綴 MR 必 FAIL。"""
    run_control_l4_lag_shift_minus_one(FULL_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_mutation_fracdiff_calibration_perturb_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    """fracdiff negative control：擾動 full 側起始日之前之前史 → strict 欄集合或 d* gate 必 FAIL。"""
    run_control_fracdiff_calibration_perturb(FULL_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_mutation_fracdiff_full_fit_d_star_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    """fracdiff negative control：d-star 改全量 fit → fracdiff MR 必 FAIL。"""
    run_control_fracdiff_full_fit_d_star(FULL_SCOPE, monkeypatch, tmp_path, kline_df_module)


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
