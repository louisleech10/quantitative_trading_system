"""ICPERF Task 0.4 ㊷ 第 6 段 VIF 樣本數判定 oracle 測試（docs/ICPERF_SPEC.md v5.57 Task 0.4 擴列表 ㊷ 列；路 P2）。

契約（㊷「修正」欄，v5.57 處理方式 B）：第 6 段 `redundancy.method == "vif"` 時，以測試段有效列數 n（同 `vif_filter`
之前處理：`apply(pd.to_numeric, errors="coerce").dropna()` 後之列數）與欄數 k 判定——
  ① n ≤ k＋1（輔助回歸殘差自由度 ≤ 1，R² 恆為或近 1）或
  ② null 基準 (n−1)/(n−k) ≥ `max_vif`（欄間完全無關時 VIF 之平均尺度已達門檻）
任一成立 ⇒ 不跑 VIF、改相關係數貪婪法（同 `correlation_threshold`／`tiebreaker`，輸入同 method="greedy"），
`redundancy_log["vif_sample_insufficient"]` 揭露原因、n、k、基準值；兩者皆不成立 ⇒ 路徑與結果與改前相同、log 不增鍵。
k ≤ 1 時 VIF 本不計算（單欄原樣保留），不判定。

oracle：本檔自寫之參考實作——樣本判定、逐對 Pearson 貪婪法（numpy、兩者皆有限之列）、逐步 VIF 以 statsmodels
`variance_inflation_factor`（exog 含常數，對齊方式見 `handoffs/run_receipts/20261101-icperf-vif-study.json`
`alignment_note`）；不呼叫被測模組之任何計算函式。輸入為 seeded 明列設計（每案一條路徑）；真實資料之改前改後選欄
差異表見研究收據 `v557_implementation` 鍵（三份第 6 段真實輸入存檔）。

mutation：拿掉樣本判定（或改用扣缺值前之列數、或改 ≥ 為 >）⇒ 本檔對應案紅。
"""

from __future__ import annotations

import math
import warnings
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.Analysis.redundancy_filter import RedundancyFilter

#: 產品之 inf 判準（`_compute_vif_scores`：R² ≥ 0.999999 記 inf）
R2_CAP = 0.999999
LEGACY_LOG_KEYS = {"method", "input_features", "output_features", "removed_features", "correlation_threshold"}


# ── 參考實作（oracle） ──────────────────────────────────────────────────────────────────────────────


def ref_effective(df: pd.DataFrame) -> pd.DataFrame:
    """同 vif_filter 之前處理：逐欄轉數值（失敗 ⇒ NaN）後丟掉含缺值之列。"""
    return df.apply(pd.to_numeric, errors="coerce").dropna()


def ref_guard(n: int, k: int, max_vif: float) -> Optional[Dict[str, object]]:
    """樣本判定參考：成立 ⇒ 回原因與基準；不成立 ⇒ None。"""
    baseline = (n - 1) / (n - k) if n > k else None
    if n <= k + 1:
        return {"reason": "n_le_k_plus_1", "n": n, "k": k, "null_vif_baseline": baseline}
    if baseline is not None and baseline >= max_vif:
        return {"reason": "null_vif_baseline_ge_max_vif", "n": n, "k": k, "null_vif_baseline": baseline}
    return None


def ref_score(scores: Optional[dict], name: str, tiebreaker: str = "icir") -> float:
    """排序分數：dict 取 tiebreaker（缺則 icir）、純數值直接用；非有限或缺 ⇒ −inf。"""
    if not scores:
        return float("-inf")
    value = scores.get(name)
    if isinstance(value, dict):
        raw = value.get(tiebreaker, value.get("icir", float("nan")))
    elif isinstance(value, (int, float)):
        raw = value
    else:
        return float("-inf")
    raw = float(raw)
    return raw if math.isfinite(raw) else float("-inf")


def ref_pearson(a: np.ndarray, b: np.ndarray) -> float:
    """兩者皆有限之列之 Pearson；有效列 < 2 或零變異 ⇒ NaN。"""
    mask = np.isfinite(a) & np.isfinite(b)
    if mask.sum() < 2:
        return float("nan")
    x = a[mask] - a[mask].mean()
    y = b[mask] - b[mask].mean()
    den = math.sqrt(float((x * x).sum()) * float((y * y).sum()))
    return float("nan") if den == 0.0 else float((x * y).sum()) / den


def ref_greedy(df: pd.DataFrame, scores: Optional[dict], threshold: float, tiebreaker: str = "icir") -> List[str]:
    """逐對相關貪婪法：依分數由高至低（同分保持欄序），與已選任一者 |r| > threshold 即略過（NaN 不算冗餘）。"""
    cols = list(df.columns)
    arr = {c: pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float) for c in cols}
    order = sorted(cols, key=lambda c: ref_score(scores, c, tiebreaker), reverse=True)
    picked: List[str] = []
    for c in order:
        rs = [abs(ref_pearson(arr[c], arr[s])) for s in picked]
        if any(r > threshold for r in rs if not math.isnan(r)):
            continue
        picked.append(c)
    keep = set(picked)
    return [c for c in cols if c in keep]


def ref_sm_vifs(data: pd.DataFrame) -> Dict[str, float]:
    """statsmodels oracle：exog＝含常數之設計矩陣；R² ≥ 0.999999（含 R²＝1）或零變異 ⇒ inf。"""
    x = data.to_numpy(dtype=float)
    exog = sm.add_constant(x, has_constant="add")
    out: Dict[str, float] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i, c in enumerate(data.columns):
            if np.std(x[:, i]) == 0:
                out[c] = float("inf")
                continue
            v = float(variance_inflation_factor(exog, i + 1))
            r2 = 1.0 - 1.0 / v if math.isfinite(v) and v != 0 else 1.0
            out[c] = float("inf") if (not math.isfinite(v)) or r2 >= R2_CAP else v
    return out


def ref_vif_stepwise(df: pd.DataFrame, max_vif: float, scores: Optional[dict], tiebreaker: str = "icir") -> List[str]:
    """逐步 VIF 參考：每輪刪最大 VIF 欄（並列且有分數 ⇒ 刪分數最低者），最大 ≤ max_vif 或剩 1 欄即停。"""
    data = ref_effective(df)
    cols = list(data.columns)
    while len(cols) > 1:
        vifs = ref_sm_vifs(data[cols])
        top = max(vifs.values())
        if top <= max_vif:
            break
        tied = [c for c in cols if vifs[c] == top]
        victim = min(tied, key=lambda c: ref_score(scores, c, tiebreaker)) if (len(tied) > 1 and scores) else tied[0]
        cols.remove(victim)
    return cols


def ref_expected(df: pd.DataFrame, scores: dict, max_vif: float, threshold: float) -> tuple:
    """完整參考：(預期選欄, 預期揭露或 None)。"""
    k = df.shape[1]
    n = int(ref_effective(df).shape[0])
    guard = ref_guard(n, k, max_vif) if k > 1 else None
    if guard is None:
        return ref_vif_stepwise(df, max_vif, scores), None
    return ref_greedy(df, scores, threshold), guard


# ── 輸入設計（seeded；每案一條路徑） ────────────────────────────────────────────────────────────────


def _independent(n: int, k: int, seed: int, prefix: str = "x") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.normal(size=(n, k)), columns=[f"{prefix}{i:02d}" for i in range(k)])


def _with_pairs(n: int, k: int, seed: int, n_pairs: int) -> pd.DataFrame:
    """k 欄：前 n_pairs 對為 |r|≈0.95 之冗餘對（b＝a＋0.3·噪），其餘獨立。"""
    rng = np.random.default_rng(seed)
    df = _independent(n, k, seed)
    cols = list(df.columns)
    for p in range(n_pairs):
        a, b = cols[2 * p], cols[2 * p + 1]
        df[b] = df[a] + 0.3 * rng.normal(size=n)
    return df


def _scores(cols: List[str], seed: int) -> dict:
    rng = np.random.default_rng(seed)
    vals = rng.permutation(len(cols)).astype(float) / 10.0
    return {c: {"icir": float(v)} for c, v in zip(cols, vals)}


def _rf(max_vif: float = 10.0, threshold: float = 0.7) -> RedundancyFilter:
    return RedundancyFilter({"method": "vif", "correlation_threshold": threshold, "vif": {"max_vif": max_vif}})


def _assert_guard_log(log: dict, expected: Dict[str, object], max_vif: float, threshold: float) -> None:
    got = log["vif_sample_insufficient"]
    assert got["reason"] == expected["reason"]
    assert got["n"] == expected["n"] and got["k"] == expected["k"]
    if expected["null_vif_baseline"] is None:
        assert got["null_vif_baseline"] is None
    else:
        assert got["null_vif_baseline"] == pytest.approx(expected["null_vif_baseline"], rel=0, abs=1e-12)
    assert got["max_vif"] == max_vif
    assert got["fallback_method"] == "greedy"
    assert got["correlation_threshold"] == threshold


# ── 案一：n＞k（判定不成立 ⇒ VIF 路徑、結果同 statsmodels 逐步、log 不增鍵） ──────────────────────────


def test_n_gt_k_runs_vif_matching_statsmodels_and_log_unchanged() -> None:
    rng = np.random.default_rng(7)
    df = _independent(300, 5, seed=7)
    df["x05"] = df["x01"] + df["x02"] + df["x03"] + 0.2 * rng.normal(size=300)  # 多重共線、逐對 |r|≈0.57
    scores = _scores(list(df.columns), seed=8)
    expected, guard = ref_expected(df, scores, 10.0, 0.7)
    assert guard is None
    # 本案須能分辨兩法（VIF 刪多重共線欄、貪婪法因逐對 |r| ≤ 0.7 全留）
    assert expected != ref_greedy(df, scores, 0.7)

    filtered, log = _rf().filter(df, scores, method="vif")
    assert list(filtered.columns) == expected
    assert set(log) == LEGACY_LOG_KEYS
    assert _rf().vif_filter(df, max_vif=10.0, ic_scores=scores) == expected


# ── 案二：n≈k（null 基準 ≥ max_vif ⇒ 貪婪法） ─────────────────────────────────────────────────────


def test_n_near_k_baseline_ge_max_vif_falls_back_to_greedy() -> None:
    df = _with_pairs(40, 37, seed=11, n_pairs=4)  # (40−1)/(40−37)=13 ≥ 10；n＝40 ＞ k＋1
    scores = _scores(list(df.columns), seed=12)
    expected, guard = ref_expected(df, scores, 10.0, 0.7)
    assert guard is not None and guard["reason"] == "null_vif_baseline_ge_max_vif"
    assert guard["null_vif_baseline"] == pytest.approx(13.0)
    # 本案須能分辨兩法（改前逐步 VIF 於 n≈k 會刪掉無關欄）
    assert expected != ref_vif_stepwise(df, 10.0, scores)

    filtered, log = _rf().filter(df, scores, method="vif")
    assert list(filtered.columns) == expected
    _assert_guard_log(log, guard, 10.0, 0.7)
    assert log["method"] == "vif"
    assert log["removed_features"] == [c for c in df.columns if c not in set(expected)]


def test_baseline_equal_max_vif_is_insufficient_and_one_more_row_is_not() -> None:
    """邊界：(21−1)/(21−19)＝10.0 恰等於 max_vif ⇒ 成立（≥）；n＝22 ⇒ 21/3＝7 ＜ 10 不成立。"""
    scores = _scores([f"x{i:02d}" for i in range(19)], seed=14)
    at = _with_pairs(21, 19, seed=13, n_pairs=3)
    expected, guard = ref_expected(at, scores, 10.0, 0.7)
    assert guard is not None and guard["reason"] == "null_vif_baseline_ge_max_vif"
    filtered, log = _rf().filter(at, scores, method="vif")
    assert list(filtered.columns) == expected
    _assert_guard_log(log, guard, 10.0, 0.7)

    above = _with_pairs(22, 19, seed=13, n_pairs=3)
    expected, guard = ref_expected(above, scores, 10.0, 0.7)
    assert guard is None
    filtered, log = _rf().filter(above, scores, method="vif")
    assert list(filtered.columns) == expected
    assert set(log) == LEGACY_LOG_KEYS


# ── 案三：n ≤ k＋1（與 max_vif 無關；含 n＜k 基準無定義） ─────────────────────────────────────────


@pytest.mark.parametrize("n,k", [(12, 11), (9, 11)])
def test_n_le_k_plus_1_falls_back_regardless_of_max_vif(n: int, k: int) -> None:
    max_vif = 1000.0  # 基準 (n−1)/(n−k) 遠低於此 ⇒ 只有 n ≤ k＋1 一條件成立
    df = _with_pairs(n, k, seed=20 + n, n_pairs=2)
    scores = _scores(list(df.columns), seed=21)
    expected, guard = ref_expected(df, scores, max_vif, 0.7)
    assert guard is not None and guard["reason"] == "n_le_k_plus_1"
    assert (guard["null_vif_baseline"] is None) == (n <= k)

    rf = _rf(max_vif=max_vif)
    filtered, log = rf.filter(df, scores, method="vif")
    assert list(filtered.columns) == expected
    _assert_guard_log(log, guard, max_vif, 0.7)


# ── 案四：含缺值（n＝扣缺值後之列數） ─────────────────────────────────────────────────────────────


def test_missing_values_shrink_effective_n_below_threshold() -> None:
    """扣缺值前 200 列（基準 199/195≈1.02 充足），扣缺值後只剩 6 列 ≤ k＋1＝6 ⇒ 成立且揭露 n＝6。"""
    df = _with_pairs(200, 5, seed=31, n_pairs=1)
    rng = np.random.default_rng(32)
    keep_complete = set(rng.choice(200, size=6, replace=False).tolist())
    cols = list(df.columns)
    for row in range(200):
        if row not in keep_complete:
            df.iat[row, int(rng.integers(0, len(cols)))] = np.nan
    assert ref_effective(df).shape[0] == 6
    scores = _scores(cols, seed=33)
    expected, guard = ref_expected(df, scores, 10.0, 0.7)
    assert guard is not None and guard["n"] == 6 and guard["reason"] == "n_le_k_plus_1"

    filtered, log = _rf().filter(df, scores, method="vif")
    assert list(filtered.columns) == expected
    _assert_guard_log(log, guard, 10.0, 0.7)


def test_missing_values_with_sufficient_effective_n_keep_vif_path() -> None:
    """含缺值但扣缺值後 n 仍充足 ⇒ VIF 路徑（同 statsmodels 逐步）、log 不增鍵。"""
    rng = np.random.default_rng(41)
    df = _independent(300, 5, seed=41)
    df["x05"] = df["x01"] + df["x02"] + df["x03"] + 0.2 * rng.normal(size=300)
    for c in df.columns:
        df.loc[rng.choice(300, size=10, replace=False), c] = np.nan
    n_eff = ref_effective(df).shape[0]
    assert 200 < n_eff < 300
    scores = _scores(list(df.columns), seed=42)
    expected, guard = ref_expected(df, scores, 10.0, 0.7)
    assert guard is None

    filtered, log = _rf().filter(df, scores, method="vif")
    assert list(filtered.columns) == expected
    assert set(log) == LEGACY_LOG_KEYS


def test_all_rows_have_missing_values_n_zero_falls_back() -> None:
    """每列皆有缺值 ⇒ n＝0 ≤ k＋1 ⇒ 貪婪法（逐對相關以兩者皆有限之列計）；基準無定義。"""
    df = _with_pairs(120, 4, seed=51, n_pairs=1)
    for row in range(120):
        df.iat[row, row % 4] = np.nan
    assert ref_effective(df).shape[0] == 0
    scores = _scores(list(df.columns), seed=52)
    expected, guard = ref_expected(df, scores, 10.0, 0.7)
    assert guard is not None and guard["n"] == 0 and guard["null_vif_baseline"] is None

    filtered, log = _rf().filter(df, scores, method="vif")
    assert list(filtered.columns) == expected
    _assert_guard_log(log, guard, 10.0, 0.7)


# ── 非 vif 方法與單欄不受影響 ──────────────────────────────────────────────────────────────────────


def test_single_column_and_other_methods_unaffected() -> None:
    one = _independent(3, 1, seed=61)
    filtered, log = _rf().filter(one, {}, method="vif")
    assert list(filtered.columns) == ["x00"] and set(log) == LEGACY_LOG_KEYS

    df = _with_pairs(40, 37, seed=11, n_pairs=4)
    scores = _scores(list(df.columns), seed=12)
    for method in ("greedy", "hierarchical"):
        _, log = _rf().filter(df, scores, method=method)
        assert set(log) == LEGACY_LOG_KEYS


# ── 第 6 段呼叫端：n＝測試段列數 ────────────────────────────────────────────────────────────────────


def test_stage6_uses_test_segment_rows_for_n() -> None:
    """全段 300 列（充足）、測試段 20 列 × 19 欄 ⇒ 基準 19 ≥ 10 成立；揭露 n＝20 而非 300。"""
    df = _with_pairs(300, 19, seed=71, n_pairs=3)
    df.index = pd.date_range("2024-01-01", periods=300, freq="h")
    test_mask = np.zeros(300, dtype=bool)
    test_mask[-20:] = True
    scores = _scores(list(df.columns), seed=72)
    test_df = df.loc[df.index[test_mask]]
    expected, guard = ref_expected(test_df, scores, 10.0, 0.7)
    assert guard is not None and guard["n"] == 20 and guard["k"] == 19

    orch = ICFilterOrchestrator(ICConfig.model_validate({"redundancy": {"method": "vif"}}))
    out = orch._stage6_redundancy(df, list(df.columns), scores, {}, split_context={"test_mask": test_mask})
    assert list(out["filtered_df"].columns) == expected
    log = out["redundancy_log"]
    assert log["scope"] == "test"
    _assert_guard_log(log, guard, 10.0, 0.7)
