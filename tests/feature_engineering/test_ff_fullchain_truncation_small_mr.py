"""FFSTAT SPEC v60 Task 4.2 — 本機縮小版全鏈截斷 MR（單週期 1h）。

既有 `test_ff_fullchain_truncation_mr.py` 13 項於 8GB 本機無法完成（諮詢 r4：校準域合併 4.55GB＋複製 3.29GB，兩度 SIGKILL）。
基線（C2-1、C2-2、fracdiff 兩項）**直接呼叫既有測試函式本體**，只把其模組內之設定建構函式換成縮小生成範圍版
（`_small_values_gate_mr_config_payload`／`_small_fracdiff_mr_config_payload`：L1 只 trend＋momentum、資料源 close＋volume、
L3 窗 5／13；L2、L3 聚合器、L4、L6.5 同既有）。負控制呼叫 `ff_truncation_mr_helpers.run_control_*`——與既有檔同一本體、
只差 `MRScope`（v60：準備證據在捕獲區外、只收因果 gate 之失敗、max_lag 不設上限、校準擾動落在起始日之前）。

誠實邊界：證具名缺陷集合之鑑別力；不證未選指標／參數與全設定等價；完整版登 RM-FULLSCALE。
不含既有檔之 `test_b2_sampling_helper_smoke`（秒級、不生成，於既有檔照常執行）。
分母尺度全欄中位數 mutant 於本 MR 實跑存活（trunc 只少 10 根、中位數穩健）——由
`test_ffstat_stable_start.py::test_mutation_denominator_full_column_median_is_caught`（起算點相依）承接，不列於此。
"""

from __future__ import annotations

import pandas as pd
import pytest

import tests.feature_engineering.test_ff_fullchain_truncation_mr as orig
from momentum.factories import create_kline_storage_manager
from tests.feature_engineering.ff_truncation_mr_helpers import (
    KLINE_CACHE_DIR,
    SYMBOL,
    TIMEFRAME,
    MRScope,
    TruncationPair,
    _build_truncation_pair,
    _ensure_module_env,
    _required_window_bars,
    _small_fracdiff_mr_config_payload,
    _small_values_gate_mr_config_payload,
    run_control_causal_winsor_full_fit,
    run_control_fracdiff_calibration_perturb,
    run_control_fracdiff_full_fit_d_star,
    run_control_fracdiff_maxlag_len_coupling,
    run_control_l4_lag_shift_minus_one,
    run_control_numba_rolling_center_true,
)

pytestmark = [pytest.mark.requires_kline, pytest.mark.slow]


@pytest.fixture(autouse=True)
def _small_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """既有測試函式以模組全域名稱取設定 ⇒ 換成縮小版（每個測試結束自動還原）。"""
    monkeypatch.setattr(orig, "_values_gate_mr_config_payload", _small_values_gate_mr_config_payload)
    monkeypatch.setattr(orig, "_fracdiff_mr_config_payload", _small_fracdiff_mr_config_payload)


@pytest.fixture(scope="module")
def kline_df_module() -> pd.DataFrame:
    storage = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    df = storage.read_klines(SYMBOL, TIMEFRAME, validate_continuity=False)
    if df is None or df.empty:
        pytest.fail(f"missing kline: {SYMBOL}/{TIMEFRAME}")
    return df


@pytest.fixture(scope="module")
def small_values_gate_mr_pair(tmp_path_factory: pytest.TempPathFactory, kline_df_module: pd.DataFrame) -> TruncationPair:
    _ensure_module_env()
    payload = _small_values_gate_mr_config_payload()
    return _build_truncation_pair(
        tmp_path_factory.mktemp("c2_small_features"),
        kline_df_module,
        config_payload=payload,
        window_bars=_required_window_bars(payload),
    )


def test_small_c2_1_fullchain_bar_truncation_invariant(small_values_gate_mr_pair: TruncationPair) -> None:
    """基線（同既有 C2-1）：縮小設定下截斷尾 k bars → warmup 後前綴因果穩定；各 mutant 測試之正常基線。"""
    orig.test_c2_1_fullchain_bar_truncation_invariant(small_values_gate_mr_pair)


def test_small_c2_2_tail_perturbation_prefix_invariant(monkeypatch, tmp_path, kline_df_module) -> None:
    orig.test_c2_2_tail_perturbation_prefix_invariant(monkeypatch, tmp_path, kline_df_module)


def test_small_fracdiff_truncation_invariant(tmp_path, kline_df_module) -> None:
    """既有檔為 strict xfail（codec 精度路徑）；縮小設定下實跑 XPASS（主委 2026-10-02，906 秒）⇒ 依 SPEC 改為一般測試。"""
    orig.test_fracdiff_truncation_invariant(tmp_path, kline_df_module)


@pytest.mark.xfail(strict=True, reason=orig.test_fracdiff_tail_perturbation_invariant.pytestmark[0].kwargs["reason"])
def test_small_fracdiff_tail_perturbation_invariant(monkeypatch, tmp_path, kline_df_module) -> None:
    orig.test_fracdiff_tail_perturbation_invariant(monkeypatch, tmp_path, kline_df_module)


# 負控制：共用本體（ff_truncation_mr_helpers.run_control_*），與既有檔同一寫法、只差設定
SMALL_SCOPE = MRScope(values_payload=_small_values_gate_mr_config_payload,
                      fracdiff_payload=_small_fracdiff_mr_config_payload)


def test_small_mutation_fracdiff_maxlag_len_coupling_truncation_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_fracdiff_maxlag_len_coupling(SMALL_SCOPE, monkeypatch, tmp_path, kline_df_module)


# （v61 撤除尾擾動版長度耦合控制：實跑〔第 1 段〕mutant 只於值 gate 現形〔rel 4.2e-4〕，而尾擾動 fracdiff 基線本即因
#  codec 於值 gate 失敗 ⇒ 不可判別；同一 mutant 由截斷版與並行版承接。）


def test_small_mutation_fracdiff_maxlag_len_coupling_parallel_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_fracdiff_maxlag_len_coupling(SMALL_SCOPE, monkeypatch, tmp_path, kline_df_module, parallel=True)


def test_small_mutation_numba_rolling_center_true_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_numba_rolling_center_true(SMALL_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_small_mutation_causal_winsor_full_fit_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_causal_winsor_full_fit(SMALL_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_small_mutation_l4_lag_shift_minus_one_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_l4_lag_shift_minus_one(SMALL_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_small_mutation_fracdiff_calibration_perturb_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_fracdiff_calibration_perturb(SMALL_SCOPE, monkeypatch, tmp_path, kline_df_module)


def test_small_mutation_fracdiff_full_fit_d_star_fails(monkeypatch, tmp_path, kline_df_module) -> None:
    run_control_fracdiff_full_fit_d_star(SMALL_SCOPE, monkeypatch, tmp_path, kline_df_module)
