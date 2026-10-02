"""FFSTAT SPEC v59 Task 4.2 — 本機縮小版多週期截斷 MR（primary 1h、training 1h＋4h）。

既有 `test_ff_multitf_truncation_mr.py`（1h＋4h＋12h）於現行倍數表下需 BTCUSDT 1h ≥ 34,302 根，本機 `kline_cache.h5`
僅 20,352 根 ⇒ 該檔目前於 `requires_kline` 即 fail（資料長度，非記憶體）。本檔**直接呼叫既有測試函式本體**，只把其模組全域
之週期清單與設定換成 1h＋4h 縮小版（`_small_values_gate_mr_config_payload`），對齊 look-ahead 之粗週期為 4h；
窗末選 12h 收盤邊界（亦為 4h 邊界）之既有選窗函式不變。

誠實邊界：12h 對齊不在本檔；完整版登 RM-FULLSCALE。不含既有檔兩個秒級 smoke（不生成，於既有檔照常執行）。
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

import tests.feature_engineering.test_ff_multitf_truncation_mr as orig
from momentum.factories import create_kline_storage_manager
from tests.feature_engineering.ff_truncation_mr_helpers import (
    ALIGN_MARGIN,
    MRScope,
    run_control_align_lookahead,
    run_control_align_lookahead_with_tail_perturb,
    run_control_causal_winsor_full_fit,
    run_control_l4_lag_shift_minus_one,
    run_control_numba_rolling_center_true,
    KLINE_CACHE_DIR,
    SYMBOL,
    TruncationPair,
    _build_truncation_pair,
    _ensure_module_env,
    _required_window_bars,
    _small_values_gate_mr_config_payload,
)

pytestmark = [pytest.mark.requires_kline, pytest.mark.slow]

PRIMARY_TF = "1h"
SMALL_TRAINING_TFS = ["1h", "4h"]
SMALL_ALIGN_COARSE_TFS = ["4h"]


def _small_multitf_config_payload() -> dict[str, Any]:
    payload = _small_values_gate_mr_config_payload(training_tfs=list(SMALL_TRAINING_TFS))
    payload["timeframes"]["primary"] = PRIMARY_TF
    return payload


def _small_multitf_window_bars() -> int:
    return _required_window_bars(
        _small_multitf_config_payload(),
        primary_tf=PRIMARY_TF,
        training_tfs=list(SMALL_TRAINING_TFS),
        align_margin=ALIGN_MARGIN,
    )


@pytest.fixture(autouse=True)
def _small_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """既有測試函式以模組全域名稱取週期與設定 ⇒ 換成 1h＋4h 縮小版（每個測試結束自動還原）。"""
    monkeypatch.setattr(orig, "TRAINING_TFS", list(SMALL_TRAINING_TFS))
    monkeypatch.setattr(orig, "EXPECTED_TRAINING_TFS", list(SMALL_TRAINING_TFS))
    monkeypatch.setattr(orig, "ALIGN_COARSE_TFS", list(SMALL_ALIGN_COARSE_TFS))
    monkeypatch.setattr(orig, "_multitf_config_payload", _small_multitf_config_payload)
    monkeypatch.setattr(orig, "_multitf_window_bars", _small_multitf_window_bars)


@pytest.fixture(scope="module")
def kline_df_module() -> pd.DataFrame:
    storage = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    df = storage.read_klines(SYMBOL, PRIMARY_TF, validate_continuity=False)
    if df is None or df.empty:
        pytest.fail(f"missing kline: {SYMBOL}/{PRIMARY_TF}")
    return df


@pytest.fixture(scope="module")
def small_multitf_window_bars() -> int:
    return _small_multitf_window_bars()


@pytest.fixture(scope="module")
def small_multitf_mr_pair(
    tmp_path_factory: pytest.TempPathFactory,
    kline_df_module: pd.DataFrame,
    small_multitf_window_bars: int,
) -> TruncationPair:
    _ensure_module_env()
    return _build_truncation_pair(
        tmp_path_factory.mktemp("c3_small_features"),
        kline_df_module,
        config_payload=_small_multitf_config_payload(),
        primary_tf=PRIMARY_TF,
        training_tfs=list(SMALL_TRAINING_TFS),
        window_bars=small_multitf_window_bars,
        align_margin=ALIGN_MARGIN,
    )


def test_small_c3_multitf_truncation_invariant(small_multitf_mr_pair: TruncationPair) -> None:
    """基線（同既有 C3）：1h＋4h 縮小設定下截斷尾 k bars → warmup 後前綴因果穩定（含對齊層／metadata）。"""
    orig.test_c3_multitf_truncation_invariant(small_multitf_mr_pair)


def test_small_c3_multitf_tail_perturbation_prefix_invariant(
    monkeypatch, tmp_path, kline_df_module, small_multitf_window_bars
) -> None:
    orig.test_c3_multitf_tail_perturbation_prefix_invariant(
        monkeypatch, tmp_path, kline_df_module, small_multitf_window_bars
    )


# 負控制：共用本體（ff_truncation_mr_helpers.run_control_*），與既有檔同一寫法、只差設定
SMALL_MULTITF_SCOPE = MRScope(
    values_payload=_small_multitf_config_payload,
    fracdiff_payload=_small_multitf_config_payload,
    primary_tf=PRIMARY_TF,
    training_tfs=tuple(SMALL_TRAINING_TFS),
    align_coarse_tfs=tuple(SMALL_ALIGN_COARSE_TFS),
    align_margin=ALIGN_MARGIN,
)


def test_small_mutation_align_lookahead_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_align_lookahead(SMALL_MULTITF_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_small_mutation_align_lookahead_with_tail_perturb_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_align_lookahead_with_tail_perturb(SMALL_MULTITF_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_small_mutation_numba_rolling_center_true_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_numba_rolling_center_true(SMALL_MULTITF_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_small_mutation_causal_winsor_full_fit_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_causal_winsor_full_fit(SMALL_MULTITF_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_small_mutation_l4_lag_shift_minus_one_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_l4_lag_shift_minus_one(SMALL_MULTITF_SCOPE, monkeypatch, tmp_path, kline_df_module)
