"""ICPERF Task 0.4 ㊻（SPEC v5.81；諮詢 r113）：深度分析候選欄規則與逐欄篩選通過狀態。

規則：手選 ⇒ 用之；未手選且有倖存 ⇒ 倖存欄（給 top_n 則倖存中排名前 top_n）；未手選且倖存為空 ⇒ 依排序鍵
（`icir_aligned`）對完整 summary_table 全域取前 n（預設 30）並標診斷模式；任何情況不取 features_df 全部欄。
oracle：測試自持之排名（依 icir_aligned 降冪手算）與倖存集合，不呼叫被測之 `_deep_candidate_selection`。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis import ic_filter_orchestrator as ifo
from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.core.exceptions import InvalidInputError

N_FEATURES = 45


def _orchestrator(survivors: Optional[List[str]]) -> tuple[ICFilterOrchestrator, List[str], Dict[str, int]]:
    """45 欄合成特徵、summary_table 之 icir_aligned 互異（亂序給入）；`survivors` None ⇒ 未執行篩選。回 (orc, 全部欄,
    oracle 名次)。"""
    rng = np.random.default_rng(20261105)
    names = [f"f{i:02d}" for i in range(N_FEATURES)]
    feats = pd.DataFrame(rng.standard_normal((60, N_FEATURES)), columns=names)
    icir = rng.permutation(np.linspace(-2.0, 2.0, N_FEATURES))
    table = [{"feature_name": n, "icir_aligned": float(v), "p_value": 0.01 * (i + 1), "p_value_adj": 0.02 * (i + 1)}
             for i, (n, v) in enumerate(zip(names, icir))]
    oracle_order = [n for _, n in sorted(zip(-icir, names))]
    rank = {n: i + 1 for i, n in enumerate(oracle_order)}
    orc = ICFilterOrchestrator(ICConfig())
    orc._ic_cache = {"features_df": feats, "label_series": pd.Series(rng.standard_normal(60)), "metadata": {},
                     "icir": {}, "rolling_ic": {}, "ic_decay": {}, "grouped_ic": {}, "event_info": {},
                     "stage0_log": {}, "preproc_log": {}, "split_context": {"effective_horizon": 1}}
    orc._filtered_features_df = None if survivors is None else feats[survivors]
    orc._report = {"summary_table": table,
                   "metadata": {"significance": {"n_tests": 44, "fdr": {"method": "bh", "enabled": True}}}}
    return orc, names, rank


def _run(orc: ICFilterOrchestrator, monkeypatch: pytest.MonkeyPatch, **kw: Any) -> tuple[Any, List[str]]:
    """端到端走 `run_deep_analysis`，只跑 factor_returns 一模組且以紀錄器取代其計算（取得實際候選欄）。"""
    seen: List[str] = []

    def record(selected: List[str], config: Any) -> dict:
        seen[:] = list(selected)
        return {"recorded": True}

    monkeypatch.setattr(orc, "_run_factor_return", record)
    rep = orc.run_deep_analysis(force_modules=["factor_returns"], **kw)
    return rep, seen


def test_no_survivors_runs_global_top_n_not_all_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    """倖存為空且未手選 ⇒ 全域前 30（預設）、標診斷模式、逐欄 filter_passed＝False、名次 1..30；不再跑全部 45 欄。
    mutation：還原舊退路（取 features_df 全部欄）⇒ 候選 45 欄而紅。"""
    orc, names, rank = _orchestrator(survivors=[])
    rep, seen = _run(orc, monkeypatch)
    want = sorted(names, key=lambda n: rank[n])[: ifo.DEEP_DIAGNOSTIC_TOP_N]
    assert seen == want and len(seen) == 30 < N_FEATURES
    cs = rep.candidate_selection
    assert cs["source"] == "diagnostic_top_n" and cs["diagnostic_mode"] is True
    assert cs["n_survivors"] == 0 and cs["n_ranked"] == N_FEATURES and cs["n_selected"] == 30
    assert cs["sort_key"] == "icir_aligned" and cs["top_n_requested"] is None
    assert cs["n_tests"] == 44 and cs["fdr"] == {"method": "bh", "enabled": True}
    assert [f["feature_name"] for f in cs["features"]] == want
    assert all(f["filter_passed"] is False for f in cs["features"])
    assert [f["global_rank"] for f in cs["features"]] == list(range(1, 31))
    # 原始 p 與 BH 調整後 p 原樣取自 summary_table（不在 Top_n 重算）
    idx = {n: i for i, n in enumerate(names)}
    assert [(f["p_value"], f["p_value_adj"]) for f in cs["features"]] == [
        (0.01 * (idx[n] + 1), 0.02 * (idx[n] + 1)) for n in want]
    assert all(f["mw_p_value"] is None and f["mw_p_value_adj"] is None for f in cs["features"])


@pytest.mark.parametrize("n", [1, 7, 50, 100])
def test_no_survivors_top_n_requested(monkeypatch: pytest.MonkeyPatch, n: int) -> None:
    """請求 top_n ⇒ 取全域前 min(n, 受檢數)；n 超過受檢數（50、100 ＞ 45）時取全部受檢欄、不報錯（無固定上限）。"""
    orc, names, rank = _orchestrator(survivors=[])
    rep, seen = _run(orc, monkeypatch, top_n=n)
    assert seen == sorted(names, key=lambda x: rank[x])[:n]
    assert rep.candidate_selection["top_n_requested"] == n
    assert rep.candidate_selection["n_selected"] == min(n, N_FEATURES)


def test_survivors_without_top_n_uses_all_survivors(monkeypatch: pytest.MonkeyPatch) -> None:
    """有倖存且未手選、未給 top_n（內部 analyze_full 路徑）⇒ 全部倖存欄、非診斷模式、filter_passed 全 True。"""
    surv = ["f03", "f10", "f22", "f40"]
    orc, _, _ = _orchestrator(survivors=surv)
    rep, seen = _run(orc, monkeypatch)
    assert seen == surv
    cs = rep.candidate_selection
    assert cs["source"] == "survivors" and cs["diagnostic_mode"] is False and cs["n_survivors"] == 4
    assert all(f["filter_passed"] is True for f in cs["features"])


def test_survivors_with_top_n_takes_best_ranked_survivors(monkeypatch: pytest.MonkeyPatch) -> None:
    """有倖存且給 top_n（API 未手選）⇒ 倖存中依全域名次前 top_n，不混入未通過者。"""
    surv = ["f03", "f10", "f22", "f40", "f41"]
    orc, _, rank = _orchestrator(survivors=surv)
    rep, seen = _run(orc, monkeypatch, top_n=3)
    assert seen == sorted(surv, key=lambda x: rank[x])[:3]
    assert rep.candidate_selection["source"] == "survivors"


def test_manual_selection_marks_each_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    """手選（含未通過者）⇒ 原樣使用，逐欄 filter_passed 依倖存集合、名次依全域排名。"""
    orc, _, rank = _orchestrator(survivors=["f01", "f02"])
    pick = ["f02", "f30", "f01", "f44"]
    rep, seen = _run(orc, monkeypatch, selected_features=pick)
    assert seen == pick
    cs = rep.candidate_selection
    assert cs["source"] == "manual" and cs["diagnostic_mode"] is False
    assert [(f["feature_name"], f["filter_passed"], f["global_rank"]) for f in cs["features"]] == [
        ("f02", True, rank["f02"]), ("f30", False, rank["f30"]), ("f01", True, rank["f01"]), ("f44", False, rank["f44"])]


def test_screening_not_run_marks_filter_passed_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    """未執行篩選（_filtered_features_df 為 None）⇒ 診斷 Top_n、filter_passed 為 None（不得宣稱未通過）、n_survivors None。"""
    orc, _, _ = _orchestrator(survivors=None)
    rep, _ = _run(orc, monkeypatch, top_n=5)
    cs = rep.candidate_selection
    assert cs["n_survivors"] is None and cs["diagnostic_mode"] is True
    assert all(f["filter_passed"] is None for f in cs["features"])


@pytest.mark.parametrize("bad", [0, -3])
def test_top_n_must_be_positive(bad: int) -> None:
    orc, _, _ = _orchestrator(survivors=[])
    with pytest.raises(InvalidInputError):
        orc.run_deep_analysis(force_modules=["factor_returns"], top_n=bad)


def test_api_top_n_has_no_fixed_upper_bound() -> None:
    """API `DeepAnalysisRequest.top_n`：正整數校驗、不設固定上限（舊 le=200 移除）。"""
    from pydantic import ValidationError

    from api.models.ic_models import DeepAnalysisRequest

    assert DeepAnalysisRequest().top_n == 30
    assert DeepAnalysisRequest(top_n=5000).top_n == 5000
    with pytest.raises(ValidationError):
        DeepAnalysisRequest(top_n=0)
