"""TESTSEL I10 — 全鏈截斷 MR 之全類別小規模姊妹測試（單週期 1h）。

`test_ff_fullchain_truncation_mr.py`（全設定完整版，RM-FULLSCALE、需 24GB）原樣保留；縮小版
`test_ff_fullchain_truncation_small_mr.py` 只開 trend＋momentum 少數指標。本檔補兩者之間之缺口：**全 10 類 atomic、
每指標只留最大週期**（`_l1_all_categories_mr_config_payload`）——各指標之因果＝獨立程式路徑，必須全類；最大週期使每個
指標以其最長回看進入截斷比對。L2 關、L3（mean、窗 3）與 L4（lag 1）各留最小 seam（抽樣層覆蓋守衛所需）、L6.5 只縮尾；
L2／L3 聚合器全部／L6.5 rank·zscore·gaussian 之 seam 與欄來源類別無關，由縮小版承擔。

負控制（改壞對照）：與縮小版、完整版同一 `ff_truncation_mr_helpers.run_control_*` 本體、同一 patch 點，於本檔全類設定
執行——L3 置中窗、縮尾全量擬合、L4 反向 shift 三個 mutant 於全類抽樣面上必被因果 gate 抓到。

誠實邊界：不證全寬 L2／L3／L4／L6.5 同時開之交互作用（完整版之 small_scale_gap，列豁免由完整版承擔）。
"""

from __future__ import annotations

from pathlib import Path

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
    _assert_truncation_invariants,
    _build_truncation_pair,
    _ensure_module_env,
    _l1_all_categories_fracdiff_mr_config_payload,
    _l1_all_categories_mr_config_payload,
    _patch_kline_tail_ohlcv,
    _required_window_bars,
    run_control_causal_winsor_full_fit,
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
def allcat_mr_pair(tmp_path_factory: pytest.TempPathFactory, kline_df_module: pd.DataFrame) -> TruncationPair:
    _ensure_module_env()
    payload = _l1_all_categories_mr_config_payload()
    return _build_truncation_pair(
        tmp_path_factory.mktemp("c2_allcat_features"),
        kline_df_module,
        config_payload=payload,
        window_bars=_required_window_bars(payload),
    )


def test_allcat_c2_1_fullchain_bar_truncation_invariant(allcat_mr_pair: TruncationPair) -> None:
    """全類 L1（最大週期）截斷尾 k bars → warmup 後前綴因果穩定（交集＋分層 gate）。"""
    _assert_truncation_invariants(allcat_mr_pair)


def test_allcat_c2_2_tail_perturbation_prefix_invariant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kline_df_module: pd.DataFrame,
) -> None:
    """全類 L1（最大週期）尾 k bar OHLCV ±1e6 → 截斷點前（含 warmup mask）不變。"""
    pair = _build_truncation_pair(
        tmp_path / "features",
        kline_df_module,
        config_payload=_l1_all_categories_mr_config_payload(),
        patch_fetch=lambda df: _patch_kline_tail_ohlcv(df, k=TRUNC_K, delta=PERTURB_DELTA),
        monkeypatch=monkeypatch,
    )
    _assert_truncation_invariants(pair)


ALLCAT_SCOPE = MRScope(values_payload=_l1_all_categories_mr_config_payload,
                       fracdiff_payload=_l1_all_categories_fracdiff_mr_config_payload)


def test_allcat_mutation_numba_rolling_center_true_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_numba_rolling_center_true(ALLCAT_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_allcat_mutation_causal_winsor_full_fit_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_causal_winsor_full_fit(ALLCAT_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_allcat_mutation_l4_lag_shift_minus_one_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_l4_lag_shift_minus_one(ALLCAT_SCOPE, monkeypatch, tmp_path, kline_df_module)
