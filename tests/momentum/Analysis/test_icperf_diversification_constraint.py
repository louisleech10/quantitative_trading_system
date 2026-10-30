"""ICPERF Task 0.4 ㊲ 第 6 段多元化約束 oracle 測試（docs/ICPERF_SPEC.md v5.40 Task 0.4 擴列表 ㊲ 列；路 I）。

契約（㊲「修正」欄＋路 I 定案之約束規則；規則全文見 `RedundancyFilter.apply_diversification_constraint` docstring）：
第 6 段冗餘剔除後之倖存集合 S 須滿足 ①相異類別數 ≥ `min_categories` ②相異資料來源數 ≥ `min_data_sources`
③任一類別佔「類別已知之倖存數」比例 ≤ `max_same_category_pct`；`enabled`（預設 False）關 ⇒ 與改前完全相同。
metadata 缺漏（`metadata_source == "missing"` 或該欄為 None／無項）之特徵不計入任何類別或來源（③之分母亦不計），記數入報告。
排序鍵＝第 6 段冗餘所用之分數（同 tiebreaker；非有限 ⇒ 最低），同分依通過門檻名單之順序。候選＝通過門檻而不在 S 者，
須與當下 S 之每一成員 |Pearson（兩者皆有限之列）| ≤ `correlation_threshold`（相關 NaN 視為不冗餘）。

oracle：本檔自寫之參考實作（numpy 逐對 Pearson、獨立之排序與迴圈），不呼叫被測模組之任何計算函式。
秒級測試之輸入為明列邊界輸入（`scipy.linalg.hadamard(16)` 之 Walsh 欄：兩兩正交、均值 0；冗餘對＝w + 0.1·w′），
每條分支一案；真實資料測試以 `data_cache/feature_klines/kline_cache.h5` BTCUSDT 4h 末 2,000 根之真實因果特徵經產品
`analyze` 端到端（樣本外切分成立），oracle 以攔截之第 6 段實際輸入獨立重算冗餘與約束。本檔之 requires_kline 測試須經
共用監看執行（autouse 自證，同 test_icperf_correctness.py）。
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import h5py
import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError
from scipy.linalg import hadamard

from momentum.Analysis.ic_config_schema import ICConfig, RedundancyConfig, load_ic_config
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.Analysis.redundancy_filter import RedundancyFilter
from momentum.FeatureEngineering.feature_naming import stamp_h5_feature_naming_version
from momentum.factories import create_ic_analyzer, create_kline_storage_manager

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
HEAVY_MARKERS = ("slow", "requires_kline")
#: 比例比較之容差（整數計數 vs 浮點門檻；同產品）
EPS = 1e-9
REASONS = {"candidates_redundant", "no_candidate_with_new_value", "insufficient_categories", "coverage_protected"}


# ── 共用監看（同 test_icperf_correctness.py） ──────────────────────────────────────────────────────


def _watchdog_missing(markers: Sequence[str], environ: Mapping[str, str]) -> bool:
    """標 slow 或 requires_kline 而未在共用監看下執行 ⇒ True（共用監看對子行程恆注入 `WATCHDOG_STACK_FILE`）。"""
    return any(m in HEAVY_MARKERS for m in markers) and not environ.get("WATCHDOG_STACK_FILE")


@pytest.fixture(autouse=True)
def _heavy_tests_require_shared_watchdog(request: pytest.FixtureRequest) -> None:
    """本檔重型／真實資料測試於執行端自證經共用監看，未經即 FAIL。"""
    if _watchdog_missing([m.name for m in request.node.iter_markers()], os.environ):
        pytest.fail("本檔標 slow／requires_kline 之測試須經共用監看執行："
                    "venv/bin/python scripts/run_watched.py --log <路徑> -- <pytest 命令>（背景）")


# ── oracle：參考實作（不呼叫被測碼） ─────────────────────────────────────────────────────────────────


def oracle_score(scores: Mapping[str, Any], name: str, tiebreaker: str) -> float:
    """分數：dict ⇒ tiebreaker 鍵（缺 ⇒ icir）；數值 ⇒ 本身；非有限或缺 ⇒ −inf。"""
    v = (scores or {}).get(name)
    if isinstance(v, dict):
        s = v.get(tiebreaker)
        if s is None:
            s = v.get("icir", float("nan"))
        s = float(s)
    elif isinstance(v, (int, float)) and not isinstance(v, bool):
        s = float(v)
    else:
        return float("-inf")
    return s if math.isfinite(s) else float("-inf")


def oracle_pair_corr(x: np.ndarray, y: np.ndarray) -> float:
    """兩者皆有限之列之 Pearson（列 < 2 或任一常數 ⇒ NaN）。"""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    m = np.isfinite(x) & np.isfinite(y)
    if int(m.sum()) < 2:
        return float("nan")
    a, b = x[m] - x[m].mean(), y[m] - y[m].mean()
    den = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
    if den == 0.0:
        return float("nan")
    return float(np.dot(a, b) / den)


def _known(meta: Mapping[str, Any], name: str, key: str) -> Optional[str]:
    info = meta.get(name)
    if not isinstance(info, dict) or info.get("metadata_source") == "missing":
        return None
    v = info.get(key)
    return None if v is None else str(v)


def oracle_greedy(feats: pd.DataFrame, scores: Mapping[str, Any], threshold: float, tiebreaker: str) -> List[str]:
    """改前第 6 段 greedy 冗餘之參考實作：依分數降序（同分依欄序），與已選任一 |corr| > threshold 即略過。"""
    cols = list(feats.columns)
    order = sorted(cols, key=lambda n: (-oracle_score(scores, n, tiebreaker), cols.index(n)))
    chosen: List[str] = []
    for f in order:
        cs = [oracle_pair_corr(feats[f].to_numpy(), feats[s].to_numpy()) for s in chosen]
        if any(math.isfinite(c) and abs(c) > threshold for c in cs):
            continue
        chosen.append(f)
    return [c for c in cols if c in chosen]


def oracle_constraint(feats: pd.DataFrame, selected: Sequence[str], passed: Sequence[str], scores: Mapping[str, Any],
                      meta: Mapping[str, Any], *, min_categories: int, min_data_sources: int,
                      max_same_category_pct: float, threshold: float, tiebreaker: str) -> Dict[str, Any]:
    """約束規則之參考實作（規則見模組說明與產品 docstring）；回 {"final", "added", "removed", "satisfied", "unmet"}。"""
    passed = list(passed)
    idx = {n: i for i, n in enumerate(passed)}
    rank = sorted(passed, key=lambda n: (-oracle_score(scores, n, tiebreaker), idx[n]))
    S = [n for n in rank if n in set(selected)]
    gone: set = set()
    added: List[Tuple[str, str]] = []
    removed: List[Tuple[str, str, str]] = []
    unmet: Dict[str, str] = {}

    def vals(names: Sequence[str], key: str) -> List[str]:
        return [v for v in (_known(meta, n, key) for n in names) if v is not None]

    def redundant(e: str, members: Sequence[str]) -> bool:
        for s in members:
            c = oracle_pair_corr(feats[e].to_numpy(), feats[s].to_numpy())
            if math.isfinite(c) and abs(c) > threshold:
                return True
        return False

    def admissible(before: Sequence[str], after: Sequence[str]) -> bool:
        cb, ca = len(set(vals(before, "category"))), len(set(vals(after, "category")))
        sb, sa = len(set(vals(before, "data_source"))), len(set(vals(after, "data_source")))
        return ca >= min(min_categories, cb) and sa >= min(min_data_sources, sb)

    for cond, key, need in (("min_categories", "category", min_categories),
                            ("min_data_sources", "data_source", min_data_sources)):
        while len(set(vals(S, key))) < need:
            have = set(vals(S, key))
            new_val = [e for e in rank if e not in S and e not in gone
                       and _known(meta, e, key) is not None and _known(meta, e, key) not in have]
            pick = next((e for e in new_val if not redundant(e, S)), None)
            if pick is None:
                unmet[cond] = "candidates_redundant" if new_val else "no_candidate_with_new_value"
                break
            S.append(pick)
            added.append((pick, cond))

    while True:
        cats = vals(S, "category")
        n = len(cats)
        counts: Dict[str, int] = {}
        for c in cats:
            counts[c] = counts.get(c, 0) + 1
        if n == 0 or max(counts.values()) <= max_same_category_pct * n + EPS:
            break
        top = max(counts.values())
        k = sorted(c for c, v in counts.items() if v == top)[0]
        members = [m for m in reversed([r for r in rank if r in S]) if _known(meta, m, "category") == k]
        r = next((m for m in members if admissible(S, [x for x in S if x != m])), None)
        if r is None:
            unmet["max_same_category_pct"] = "coverage_protected"
            break
        rest = [x for x in S if x != r]
        swap = None
        for e in rank:
            if e in S or e in gone:
                continue
            ce = _known(meta, e, "category")
            if ce is None or ce == k or counts.get(ce, 0) + 1 > max_same_category_pct * n + EPS:
                continue
            if redundant(e, rest):
                continue
            swap = e
            break
        if swap is not None:
            S = rest + [swap]
            gone.add(r)
            removed.append((r, "max_same_category_pct", "swap"))
            added.append((swap, "max_same_category_pct"))
            continue
        if len(set(cats)) * max_same_category_pct < 1.0 - EPS:
            unmet["max_same_category_pct"] = "insufficient_categories"
            break
        S = rest
        gone.add(r)
        removed.append((r, "max_same_category_pct", "trim"))

    final = [n for n in passed if n in set(S)]
    cats = vals(final, "category")
    counts = {}
    for c in cats:
        counts[c] = counts.get(c, 0) + 1
    satisfied = {
        "min_categories": len(set(cats)) >= min_categories,
        "min_data_sources": len(set(vals(final, "data_source"))) >= min_data_sources,
        "max_same_category_pct": (not cats) or max(counts.values()) <= max_same_category_pct * len(cats) + EPS,
    }
    return {"final": final, "added": added, "removed": removed, "satisfied": satisfied, "unmet": unmet}


# ── 明列邊界輸入 ────────────────────────────────────────────────────────────────────────────────────

W = hadamard(16).astype(np.float64)[:, 1:]  # 15 欄 Walsh：兩兩正交、均值 0


def _frame(spec: Mapping[str, Any]) -> pd.DataFrame:
    """spec：{名: Walsh 欄號 int ｜ (欄號, 欄號′) ⇒ w + 0.1·w′（與 w 之 corr≈0.995）｜ ndarray}。"""
    cols = {}
    for name, s in spec.items():
        if isinstance(s, int):
            cols[name] = W[:, s]
        elif isinstance(s, tuple):
            cols[name] = W[:, s[0]] + 0.1 * W[:, s[1]]
        else:
            cols[name] = np.asarray(s, dtype=np.float64)
    return pd.DataFrame(cols)


def _m(cat: Optional[str], src: Optional[str], missing: bool = False) -> Dict[str, Any]:
    if missing:
        return {"category": None, "data_source": None, "layer": None, "metadata_source": "missing"}
    return {"category": cat, "data_source": src, "layer": "layer1", "metadata_source": "feature_name"}


def _filter(min_c: int = 1, min_s: int = 1, pct: float = 1.0, enabled: bool = True,
            threshold: float = 0.7) -> RedundancyFilter:
    cfg = RedundancyConfig.model_validate({
        "correlation_threshold": threshold,
        "diversification": {"enabled": enabled, "min_categories": min_c, "min_data_sources": min_s,
                            "max_same_category_pct": pct},
    })
    return RedundancyFilter(cfg.model_dump())


def _run_both(feats: pd.DataFrame, selected: Sequence[str], scores: Mapping[str, Any], meta: Mapping[str, Any],
              min_c: int = 1, min_s: int = 1, pct: float = 1.0) -> Tuple[List[str], Dict[str, Any], Dict[str, Any]]:
    """產品 apply_diversification_constraint 與 oracle 同輸入；回 (產品 final, 產品 log, oracle)。"""
    passed = list(feats.columns)
    got, log = _filter(min_c, min_s, pct).apply_diversification_constraint(feats, list(selected), passed, dict(scores),
                                                                           dict(meta))
    want = oracle_constraint(feats, selected, passed, scores, meta, min_categories=min_c, min_data_sources=min_s,
                             max_same_category_pct=pct, threshold=0.7, tiebreaker="icir")
    return got, log, want


def _assert_matches(got: List[str], log: Dict[str, Any], want: Dict[str, Any]) -> None:
    assert got == want["final"], f"final {got} != oracle {want['final']}"
    assert [(a["name"], a["condition"]) for a in log["added"]] == want["added"]
    assert [(r["name"], r["condition"], r["action"]) for r in log["removed"]] == want["removed"]
    assert log["satisfied"] == want["satisfied"]
    assert log["unmet_reasons"] == want["unmet"]
    assert set(log["unmet_reasons"].values()) <= REASONS
    assert log["n_before"] >= 0 and log["n_after"] == len(got)


# ── 設定（schema／API） ──────────────────────────────────────────────────────────────────────────────


def test_diversification_config_defaults_and_enabled_off() -> None:
    """`enabled` 預設 False（不改現行篩選結果，預設值待使用者定）；三數值預設照現行 schema。"""
    d = ICConfig().redundancy.diversification
    assert d.enabled is False
    assert (d.min_categories, d.min_data_sources, d.max_same_category_pct) == (3, 2, 0.4)
    assert load_ic_config().redundancy.diversification.enabled is False  # config/ic_config.yaml 未設 ⇒ 預設


@pytest.mark.parametrize("bad", [
    {"min_categories": 0}, {"min_data_sources": 0}, {"max_same_category_pct": 0.0},
    {"max_same_category_pct": 1.01}, {"enable": True},
])
def test_diversification_config_rejects_invalid(bad: Dict[str, Any]) -> None:
    """域外值與拼錯之鍵（如 `enable`）一律拒收（開關拼錯不得被靜默忽略）。"""
    with pytest.raises(ValidationError):
        RedundancyConfig.model_validate({"diversification": bad})


def test_diversification_settable_via_api_config_override() -> None:
    """API 請求 `config_override.redundancy.diversification`（服務 `_build_config_override` → `create_ic_analyzer`）
    之四值抵達第 6 段之 RedundancyFilter。"""
    from api.models.ic_models import ICAnalyzeRequest
    from api.services.ic_analysis_service import ICAnalysisService

    div = {"enabled": True, "min_categories": 4, "min_data_sources": 3, "max_same_category_pct": 0.25}
    req = ICAnalyzeRequest(symbol="BTCUSDT", timeframe="1h", config_hash="x",
                           config_override={"redundancy": {"diversification": div}})
    svc = ICAnalysisService.__new__(ICAnalysisService)
    orch = create_ic_analyzer(svc._build_config_override(req))
    assert orch._config.redundancy.diversification.model_dump() == div
    assert orch._redundancy.diversification_settings() == div


# ── 秒級：逐分支（明列邊界輸入） ────────────────────────────────────────────────────────────────────


def test_disabled_returns_selected_unchanged_without_log_key() -> None:
    """開關關：第 6 段倖存與改前（oracle greedy）相同，redundancy_log 不新增鍵。"""
    feats = _frame({"a": 0, "b": 1, "a2": (0, 2), "c": 3})
    meta = {"a": _m("trend", "close"), "b": _m("trend", "close"), "a2": _m("momentum", "close"),
            "c": _m("trend", "close")}
    scores = {"a": 0.9, "b": 0.8, "a2": 0.7, "c": 0.6}
    orch = ICFilterOrchestrator(ICConfig.model_validate({"redundancy": {"diversification": {
        "enabled": False, "min_categories": 3, "max_same_category_pct": 0.3}}}))
    out = orch._stage6_redundancy(feats, list(feats.columns), scores, meta)
    assert list(out["filtered_df"].columns) == oracle_greedy(feats, scores, 0.7, "icir") == ["a", "b", "c"]
    assert "diversification_constraint" not in out["redundancy_log"]
    assert set(out["redundancy_log"]) == {"method", "input_features", "output_features", "removed_features",
                                          "correlation_threshold"}


def test_min_categories_adds_top_eligible_skipping_redundant_and_missing() -> None:
    """①：依排序鍵補入新類別之最高者；與倖存冗餘者（a2≈a）與 metadata 缺漏者（x）略過。"""
    feats = _frame({"a": 0, "b": 1, "x": 2, "a2": (0, 4), "d": 5, "e": 6})
    meta = {"a": _m("trend", "close"), "b": _m("trend", "close"), "x": _m(None, None, missing=True),
            "a2": _m("momentum", "close"), "d": _m("momentum", "close"), "e": _m("volume", "close")}
    scores = {"a": 0.9, "b": 0.8, "x": 0.85, "a2": 0.7, "d": 0.6, "e": 0.5}
    got, log, want = _run_both(feats, ["a", "b"], scores, meta, min_c=3)
    _assert_matches(got, log, want)
    assert got == ["a", "b", "d", "e"]
    assert log["satisfied"]["min_categories"] is True


def test_min_categories_unmet_candidates_redundant() -> None:
    """①未滿足：新類別候選全與倖存冗餘 ⇒ `candidates_redundant`，集合不變。"""
    feats = _frame({"a": 0, "b": 1, "a2": (0, 4)})
    meta = {"a": _m("trend", "close"), "b": _m("trend", "close"), "a2": _m("momentum", "close")}
    got, log, want = _run_both(feats, ["a", "b"], {"a": 0.9, "b": 0.8, "a2": 0.7}, meta, min_c=2)
    _assert_matches(got, log, want)
    assert got == ["a", "b"] and log["unmet_reasons"] == {"min_categories": "candidates_redundant"}


def test_min_categories_unmet_no_new_value() -> None:
    """①未滿足：無新類別之候選 ⇒ `no_candidate_with_new_value`。"""
    feats = _frame({"a": 0, "b": 1, "c": 2})
    meta = {"a": _m("trend", "close"), "b": _m("trend", "close"), "c": _m("trend", "volume")}
    got, log, want = _run_both(feats, ["a", "b"], {"a": 0.9, "b": 0.8, "c": 0.7}, meta, min_c=2)
    _assert_matches(got, log, want)
    assert got == ["a", "b"] and log["unmet_reasons"] == {"min_categories": "no_candidate_with_new_value"}


def test_min_data_sources_adds_and_unmet() -> None:
    """②：補入新資料來源之最高者；再無新來源 ⇒ `no_candidate_with_new_value`。"""
    feats = _frame({"a": 0, "b": 1, "v": 2, "h": 3})
    meta = {"a": _m("trend", "close"), "b": _m("momentum", "close"), "v": _m("trend", "volume"),
            "h": _m("trend", "volume")}
    got, log, want = _run_both(feats, ["a", "b"], {"a": 0.9, "b": 0.8, "v": 0.5, "h": 0.6}, meta, min_s=3)
    _assert_matches(got, log, want)
    assert got == ["a", "b", "h"]
    assert log["unmet_reasons"] == {"min_data_sources": "no_candidate_with_new_value"}


def test_cap_swap_replaces_lowest_of_concentrated_category() -> None:
    """③ 換入：過度集中類別之最低排序者換成他類別最高之合格候選（集合大小不變）。"""
    feats = _frame({"t1": 0, "t2": 1, "t3": 2, "m1": 3, "v1": 4})
    meta = {"t1": _m("trend", "close"), "t2": _m("trend", "close"), "t3": _m("trend", "close"),
            "m1": _m("momentum", "close"), "v1": _m("volume", "volume")}
    scores = {"t1": 0.9, "t2": 0.8, "t3": 0.7, "m1": 0.6, "v1": 0.1}
    got, log, want = _run_both(feats, ["t1", "t2", "t3", "m1"], scores, meta, pct=0.5)
    _assert_matches(got, log, want)
    assert got == ["t1", "t2", "m1", "v1"]
    assert [(r["name"], r["action"]) for r in log["removed"]] == [("t3", "swap")]


def test_cap_trim_when_no_candidate() -> None:
    """③ 剔除：無合格候選且可行（類別數·比例 ≥ 1）⇒ 剔除最低排序者至滿足。"""
    feats = _frame({"t1": 0, "t2": 1, "t3": 2, "m1": 3})
    meta = {"t1": _m("trend", "close"), "t2": _m("trend", "close"), "t3": _m("trend", "close"),
            "m1": _m("momentum", "close")}
    got, log, want = _run_both(feats, list(feats.columns), {"t1": 0.9, "t2": 0.8, "t3": 0.7, "m1": 0.6}, meta,
                               pct=0.5)
    _assert_matches(got, log, want)
    assert got == ["t1", "m1"] and [r["action"] for r in log["removed"]] == ["trim", "trim"]


def test_cap_infeasible_insufficient_categories() -> None:
    """③ 不可行：只一類別、比例 0.5 ⇒ 不剔除、`insufficient_categories`。"""
    feats = _frame({"t1": 0, "t2": 1, "t3": 2})
    meta = {n: _m("trend", "close") for n in feats.columns}
    got, log, want = _run_both(feats, list(feats.columns), {"t1": 0.9, "t2": 0.8, "t3": 0.7}, meta, pct=0.5)
    _assert_matches(got, log, want)
    assert got == ["t1", "t2", "t3"]
    assert log["unmet_reasons"] == {"max_same_category_pct": "insufficient_categories"}


def test_cap_skips_member_whose_removal_breaks_source_coverage() -> None:
    """③：剔除會使資料來源數低於要求之成員受保護、改剔次低者；全部受保護 ⇒ `coverage_protected`。"""
    feats = _frame({"t1": 0, "t2": 1, "m1": 2})
    meta = {"t1": _m("trend", "close"), "t2": _m("trend", "volume"), "m1": _m("momentum", "close")}
    scores = {"t1": 0.9, "t2": 0.1, "m1": 0.5}
    got, log, want = _run_both(feats, list(feats.columns), scores, meta, min_s=2, pct=0.5)
    _assert_matches(got, log, want)
    assert got == ["t2", "m1"]  # t2 最低但為唯一 volume ⇒ 受保護，剔 t1
    meta2 = {"t1": _m("trend", "close"), "t2": _m("trend", "volume"), "m1": _m("momentum", "hl")}
    got, log, want = _run_both(feats, list(feats.columns), scores, meta2, min_s=3, pct=0.5)
    _assert_matches(got, log, want)
    assert got == ["t1", "t2", "m1"] and log["unmet_reasons"] == {"max_same_category_pct": "coverage_protected"}


def test_cap_boundary_equal_share_is_satisfied() -> None:
    """③ 邊界：佔比恰等於門檻（2/5＝0.4）⇒ 滿足、不動；高於門檻（3/5）⇒ 動作。"""
    feats = _frame({"t1": 0, "t2": 1, "m1": 2, "v1": 3, "h1": 4, "t3": 5})
    meta = {"t1": _m("trend", "close"), "t2": _m("trend", "close"), "m1": _m("momentum", "close"),
            "v1": _m("volume", "volume"), "h1": _m("volatility", "hl"), "t3": _m("trend", "close")}
    scores = {"t1": 0.9, "t2": 0.8, "m1": 0.7, "v1": 0.6, "h1": 0.5, "t3": 0.4}
    got, log, want = _run_both(feats, ["t1", "t2", "m1", "v1", "h1"], scores, meta, pct=0.4)
    _assert_matches(got, log, want)
    assert got == ["t1", "t2", "m1", "v1", "h1"] and log["added"] == [] and log["removed"] == []
    got, log, want = _run_both(feats, ["t1", "t2", "t3", "v1", "h1"], scores, meta, pct=0.4)
    _assert_matches(got, log, want)
    assert log["satisfied"]["max_same_category_pct"] is True and log["removed"]


def test_missing_metadata_not_counted_in_share_denominator() -> None:
    """metadata 缺漏者不計入類別、來源與③之分母（2/3 > 0.5 ⇒ 違反；若計入分母 2/4 不違反），並記數。"""
    feats = _frame({"t1": 0, "t2": 1, "x": 2, "m1": 3})
    meta = {"t1": _m("trend", "close"), "t2": _m("trend", "close"), "x": _m(None, None, missing=True),
            "m1": _m("momentum", "close")}
    got, log, want = _run_both(feats, list(feats.columns), {"t1": 0.9, "t2": 0.8, "x": 0.7, "m1": 0.6}, meta,
                               pct=0.5)
    _assert_matches(got, log, want)
    assert got == ["t1", "x", "m1"]
    assert log["metadata_missing"] == {"selected_before": 1, "candidates": 0, "final": 1}


def test_tie_and_nonfinite_score_ordering() -> None:
    """同分依通過名單順序；非有限分數排最低。"""
    feats = _frame({"a": 0, "b": 1, "n1": 2, "c1": 3, "c2": 4})
    meta = {"a": _m("trend", "close"), "b": _m("trend", "close"), "n1": _m("volume", "volume"),
            "c1": _m("momentum", "close"), "c2": _m("momentum", "close")}
    scores = {"a": 0.9, "b": 0.8, "n1": float("nan"), "c1": 0.3, "c2": 0.3}
    got, log, want = _run_both(feats, ["a", "b"], scores, meta, min_c=3)
    _assert_matches(got, log, want)
    assert got == ["a", "b", "n1", "c1"]  # momentum 取同分之先者 c1；volume 只 n1（−inf 仍合格）
    assert [a["name"] for a in log["added"]] == ["c1", "n1"]


def test_nan_and_constant_columns_correlation_semantics() -> None:
    """候選為常數欄（相關 NaN）⇒ 不冗餘；含 NaN 列 ⇒ 以兩者皆有限之列計相關（與 oracle 一致）。"""
    w0 = W[:, 0].copy()
    near = w0 + 0.1 * W[:, 6]
    near[:3] = np.nan
    feats = _frame({"a": 0, "b": 1, "const": np.ones(16), "nearnan": near})
    meta = {"a": _m("trend", "close"), "b": _m("trend", "close"), "const": _m("volume", "volume"),
            "nearnan": _m("momentum", "close")}
    got, log, want = _run_both(feats, ["a", "b"], {"a": 0.9, "b": 0.8, "const": 0.7, "nearnan": 0.75}, meta,
                               min_c=3)
    _assert_matches(got, log, want)
    assert got == ["a", "b", "const"]
    assert log["unmet_reasons"] == {"min_categories": "candidates_redundant"}


def test_stage6_enabled_wires_final_set_into_outputs() -> None:
    """第 6 段開：filtered_df、相關矩陣、多元化指標皆依約束後之集合；redundancy_log 帶約束記錄。"""
    feats = _frame({"t1": 0, "t2": 1, "t3": 2, "m1": 3, "v1": 4})
    meta = {"t1": _m("trend", "close"), "t2": _m("trend", "close"), "t3": _m("trend", "close"),
            "m1": _m("momentum", "close"), "v1": _m("volume", "volume")}
    scores = {"t1": 0.9, "t2": 0.8, "t3": 0.7, "m1": 0.6, "v1": 0.1}
    orch = ICFilterOrchestrator(ICConfig.model_validate({"redundancy": {"diversification": {
        "enabled": True, "min_categories": 3, "min_data_sources": 2, "max_same_category_pct": 0.5}}}))
    passed = ["t1", "t2", "t3", "m1"]  # v1 未通過門檻 ⇒ 不得補入
    out = orch._stage6_redundancy(feats, passed, scores, meta)
    want = oracle_constraint(feats, oracle_greedy(feats[passed], scores, 0.7, "icir"), passed, scores, meta,
                             min_categories=3, min_data_sources=2, max_same_category_pct=0.5, threshold=0.7,
                             tiebreaker="icir")
    final = list(out["filtered_df"].columns)
    assert final == want["final"] and "v1" not in final
    assert list(out["correlation_matrix"].columns) == final
    c = oracle_pair_corr(feats[final[0]].to_numpy(), feats[final[1]].to_numpy())
    assert abs(float(out["correlation_matrix"].iloc[0, 1]) - c) <= 1e-12
    log = out["redundancy_log"]
    assert log["output_features"] == len(final)
    assert log["removed_features"] == [n for n in passed if n not in final]
    assert log["diversification_constraint"]["satisfied"] == want["satisfied"]
    assert log["diversification_constraint"]["unmet_reasons"] == want["unmet"]
    cats = {meta[n]["category"] for n in final}
    assert out["diversification_metrics"]["category_coverage"] == pytest.approx(
        len(cats) / len({v["category"] for v in meta.values()}), abs=0)


def test_stage6_enabled_no_passed_features_records_vacuous_log() -> None:
    """第 6 段開而無通過門檻者：回空集合、約束記錄照寫（①②未滿足、③空集合視為滿足）。"""
    feats = _frame({"a": 0})
    orch = ICFilterOrchestrator(ICConfig.model_validate({"redundancy": {"diversification": {"enabled": True}}}))
    out = orch._stage6_redundancy(feats, [], {}, {"a": _m("trend", "close")})
    log = out["redundancy_log"]["diversification_constraint"]
    assert list(out["filtered_df"].columns) == []
    assert log["satisfied"] == {"min_categories": False, "min_data_sources": False, "max_same_category_pct": True}
    assert log["unmet_reasons"] == {"min_categories": "no_candidate_with_new_value",
                                    "min_data_sources": "no_candidate_with_new_value"}


# ── 真實資料：產品 analyze 端到端（BTCUSDT 4h 末 2,000 根，樣本外切分） ───────────────────────────────


def _real_kline(rows: int, timeframe: str = "4h", symbol: str = "BTCUSDT") -> pd.DataFrame:
    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        data = f[f"{symbol}/{timeframe}/data"][-rows:]
    idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True)
    return pd.DataFrame({k: data[k].astype("float64") for k in ("high", "low", "close", "volume")}, index=idx)


#: 真實因果特徵（只用 0..t）與其 metadata（四類別、三資料來源、一欄缺漏）
REAL_META: Dict[str, Tuple[Optional[str], Optional[str]]] = {
    "dev5": ("trend", "close"), "dev10": ("trend", "close"), "dev20": ("trend", "close"),
    "dev50": ("trend", "close"), "dev100": ("trend", "close"),
    "ret1": ("momentum", "close"), "ret3": ("momentum", "close"), "ret6": ("momentum", "close"),
    "ret12": ("momentum", "close"), "ret24": ("momentum", "close"),
    "hlr": ("volatility", "hl"), "hlr10": ("volatility", "hl"),
    "volz20": ("volume", "volume"), "volr50": ("volume", "volume"),
    "ret48": (None, None),
}


def _real_inputs(tmp_path: Path) -> Tuple[pd.DataFrame, Dict[str, Path]]:
    k = _real_kline(2000)
    c, v = k["close"], k["volume"]
    feats = pd.DataFrame({
        **{f"dev{w}": c / c.rolling(w).mean() - 1.0 for w in (5, 10, 20, 50, 100)},
        **{f"ret{w}": c / c.shift(w) - 1.0 for w in (1, 3, 6, 12, 24, 48)},
        "hlr": (k["high"] - k["low"]) / c,
        "hlr10": ((k["high"] - k["low"]) / c).rolling(10).mean(),
        "volz20": (v - v.rolling(20).mean()) / v.rolling(20).std(),
        "volr50": v / v.rolling(50).mean(),
    })[list(REAL_META)].astype(np.float32).astype(np.float64)
    label = (c.shift(-1) / c - 1.0).astype(np.float32).astype(np.float64).rename("return_1")
    paths = {"features": tmp_path / "features.h5", "labels": tmp_path / "labels.h5", "meta": tmp_path / "meta.json"}
    for path, name, frame, names_key in ((paths["features"], "features", feats, "feature_names"),
                                         (paths["labels"], "labels", label.to_frame(), "label_names")):
        with h5py.File(path, "w") as f:
            stamp_h5_feature_naming_version(f.attrs)
            g = f.create_group("BTCUSDT/4h")
            g.create_dataset(name, data=frame.to_numpy(dtype=np.float32))
            g.create_dataset("timestamps", data=(frame.index.asi8 // 10**9).astype(np.int64))
            g.create_dataset(names_key, data=np.array(frame.columns.tolist(), dtype=object),
                             dtype=h5py.string_dtype(encoding="utf-8"))
    meta: Dict[str, Any] = {"symbol": "BTCUSDT", "timeframe": "4h", "case_id": "icperf_diversification"}
    for n, (cat, src) in REAL_META.items():
        meta[n] = _m(cat, src, missing=cat is None) | {"name": n}
    paths["meta"].write_text(json.dumps(meta), encoding="utf-8")
    return feats, paths


def _real_override(div: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "preprocessing": {"winsorization": {"enabled": False, "method": "none"},
                          "missing_values": {"max_fill_forward": 0, "min_coverage": 0.0}},
        "report": {"include_decay_analysis": False, "include_turnover_analysis": False,
                   "include_quantile_curves": False, "include_correlation_heatmap": False,
                   "include_layer_analysis": False, "include_regime_analysis": False, "ai_summary": False},
        "turnover": {"enabled": False},
        "ic_calculation": {"grouped_analysis": {"by_regime": False, "by_year": False, "by_quarter": False,
                                                "by_category": False, "by_data_source": False, "by_layer": False}},
        "thresholds": {"ic_mean_min": -1.0, "icir_min": -1.0, "p_value_max": 1.0, "ic_hit_rate_min": 0.0,
                       "monotonicity_score_min": 0.0, "coverage_min": 0.0, "long_short_spread": {"enabled": False}},
        "marginal_ic": {"enabled": False},
    }
    if div is not None:
        out["redundancy"] = {"diversification": div}
    return out


def _analyze_with_stage6_spy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                             div: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], Any, Dict[str, Any]]:
    """產品 analyze（同 API：create_ic_analyzer(override) 再 analyze(config_override=…)）並攔截第 6 段實際輸入。"""
    feats, paths = _real_inputs(tmp_path)
    seen: Dict[str, Any] = {}
    orig = ICFilterOrchestrator._stage6_redundancy

    def spy(self: Any, features_df: Any, passed_features: Any, ic_scores: Any, metadata: Any,
            split_context: Any = None) -> Any:
        mask = (split_context or {}).get("test_mask")
        rows = features_df if mask is None else features_df.loc[features_df.index[np.asarray(mask, dtype=bool)]]
        seen.update({"rows": rows[list(passed_features)].copy(), "passed": list(passed_features),
                     "scores": dict(ic_scores), "metadata": {k: v for k, v in metadata.items() if isinstance(v, dict)},
                     "split": mask is not None})
        return orig(self, features_df, passed_features, ic_scores, metadata, split_context=split_context)

    monkeypatch.setattr(ICFilterOrchestrator, "_stage6_redundancy", spy)
    override = _real_override(div)
    orch = create_ic_analyzer(override)
    report = orch.analyze(features_path=str(paths["features"]), labels_path=str(paths["labels"]),
                          meta_path=str(paths["meta"]), config_override=override,
                          kline_reader=create_kline_storage_manager(cache_dir=str(KLINE_CACHE.parent)))
    return report, orch, seen


@pytest.mark.requires_kline
@pytest.mark.usefixtures("ic_persist_redirect")
@pytest.mark.ic_persist_redirect
def test_real_kline_disabled_equals_pre_change_greedy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """真實資料、約束關：倖存＝oracle 改前 greedy（攔截之第 6 段輸入獨立重算）；filter log 無約束鍵。"""
    report, orch, seen = _analyze_with_stage6_spy(tmp_path, monkeypatch, None)
    assert seen["split"] is True and len(seen["passed"]) == len(REAL_META)
    base = oracle_greedy(seen["rows"], seen["scores"], 0.7, "icir")
    assert list(orch.get_filtered_features().columns) == base
    assert "diversification_constraint" not in report["filter_log"]["stage6_redundancy"]


@pytest.mark.requires_kline
@pytest.mark.usefixtures("ic_persist_redirect")
@pytest.mark.ic_persist_redirect
@pytest.mark.parametrize("settings, satisfiable", [
    # 可滿足：倖存 momentum 4／6 > 0.5 ⇒ 換入或剔除至滿足（三類別、三來源）
    ((3, 3, 0.5), True),
    # 不可滿足之真實分支：trend 候選皆與 momentum 倖存冗餘（①candidates_redundant）、3 類別 × 0.3 < 1（③insufficient）
    ((4, 3, 0.3), False),
])
def test_real_kline_enabled_survivors_match_oracle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                   settings: Tuple[int, int, float], satisfiable: bool) -> None:
    """真實資料、約束開：倖存＝oracle（攔截之第 6 段輸入，oracle greedy 後 oracle 約束）、filter log 之補入／剔除／
    滿足／原因與 oracle 逐項相同、缺漏 metadata 欄記數；可滿足之設定 ⇒ 三條件皆滿足且約束確有動作（非空真），不可滿足
    之設定 ⇒ 未滿足原因非空且不剔除至違反保護。"""
    min_c, min_s, pct = settings
    div = {"enabled": True, "min_categories": min_c, "min_data_sources": min_s, "max_same_category_pct": pct}
    report, orch, seen = _analyze_with_stage6_spy(tmp_path, monkeypatch, div)
    base = oracle_greedy(seen["rows"], seen["scores"], 0.7, "icir")
    want = oracle_constraint(seen["rows"], base, seen["passed"], seen["scores"], seen["metadata"],
                             min_categories=min_c, min_data_sources=min_s, max_same_category_pct=pct, threshold=0.7,
                             tiebreaker="icir")
    diag = f"base={base} oracle={want}"
    final = list(orch.get_filtered_features().columns)
    assert final == want["final"], diag
    log = report["filter_log"]["stage6_redundancy"]["diversification_constraint"]
    assert [(a["name"], a["condition"]) for a in log["added"]] == want["added"]
    assert [(r["name"], r["condition"], r["action"]) for r in log["removed"]] == want["removed"]
    assert log["satisfied"] == want["satisfied"] and log["unmet_reasons"] == want["unmet"]
    assert log["metadata_missing"]["selected_before"] + log["metadata_missing"]["candidates"] == 1
    if satisfiable:
        assert want["satisfied"] == {"min_categories": True, "min_data_sources": True,
                                     "max_same_category_pct": True}, diag
        assert want["added"] or want["removed"], "約束未動作：本案設定須使約束生效（非空真）"
    else:
        assert want["unmet"] and set(want["unmet"].values()) <= REASONS, diag
