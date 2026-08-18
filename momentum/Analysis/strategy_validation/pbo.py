"""Task 4.2／4.3 — PBO（CSCV）與候選宇宙污染防護（`票 GAP-1/C3`）。

SPEC ref：Task 4.2／4.3 ＋ A1-2（golden 生成式）／A1-3（§V-4 可證偽形式）／A1-4（`universe_scope`）／A1-15（champion 索引與 path 級退化）。

演算法（Bailey et al. 2015, Algorithm 2.3）：對每條 CSCV path——IS 選 champion（有效候選中 IS metric 最大、平手取最小原始欄索引）、
OOS 取 champion 之升冪名次 `rank`（`scipy.stats.rankdata(method="average")`），`r = rank/(n_valid+1)`、`ω = ln(r/(1-r))`；
`PBO = mean(ω < 0)`，分母＝**實際使用之 path 數** `n_paths_used`。
🔴 A1-15：名次一律以 `pos = {原始欄索引: 壓縮位置}` 取；champion 於 IS 或 OOS 非有限 ⇒ **跳過該 path**（不重選）。
🔴 A1-4：守衛 ok ⇒ `universe_scope="ledger_recorded_only"`（今日唯一合法值；三項守衛**不**證明 ledger 自身完整，見 G1-R9）。
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, NamedTuple, Optional, Sequence

import numpy as np
from scipy.stats import rankdata

from momentum.Analysis.strategy_validation.contract import load_strategy_validation_contract
from momentum.Analysis.strategy_validation.cscv import cscv_path_count, iter_cscv_splits
from momentum.Analysis.strategy_validation.ledger import LedgerReadResult
from momentum.Analysis.strategy_validation.min_btl import _validated_status
from momentum.Analysis.strategy_validation.sharpe import compute_sharpe

_REASON_CONTAMINATED = "universe_selection_contaminated"
_REASON_UNVERIFIABLE = "universe_provenance_unverifiable"
_REASON_INSUFFICIENT = "insufficient_candidates"
_REASON_ALL_DEGENERATE = "all_paths_degenerate"
_UNIVERSE_SCOPE_LEDGER_ONLY = "ledger_recorded_only"
_SOURCE_LEDGER_ALL = "ledger_all_candidates"


@dataclass(frozen=True)
class UniverseProvenance:
    """候選宇宙來源宣告（Task 4.3；`__post_init__` 驗型別；`source` 值集合住契約 `universe_source_values`）。"""

    selection_free: bool
    source: str
    candidate_set_hash: str
    candidate_count: int
    declared_by: str

    def __post_init__(self) -> None:
        if type(self.selection_free) is not bool:
            raise ValueError("selection_free 須為 bool")
        if type(self.source) is not str or not self.source:
            raise ValueError("source 須為非空 str")
        if type(self.candidate_set_hash) is not str:
            raise ValueError("candidate_set_hash 須為 str")
        if type(self.candidate_count) is not int or self.candidate_count < 0:
            raise ValueError("candidate_count 須為 >=0 之 int")
        if type(self.declared_by) is not str or not self.declared_by:
            raise ValueError("declared_by 須為非空 str")


@dataclass(frozen=True)
class PBOResult:
    """PBO 結果（退化／守衛非 ok 時 `value` 與 logits 為 NaN、status 非 ok）。"""

    value: float
    logits_min: float
    logits_median: float
    logits_max: float
    n_paths: int
    n_paths_used: int
    n_paths_skipped: int
    n_path_exclusions: int
    n_candidates_invalid: int
    universe_scope: Optional[str]
    status: str
    reason: str


class GuardResult(NamedTuple):
    """Task 4.3 守衛結果（tuple 相容：可解包／與 `("ok", "")` 相等；具名欄位供 wiring 閘 W3 passthrough `guard.reason`）。"""

    status: str
    reason: str


def candidate_set_hash(candidate_ids: Sequence[str]) -> str:
    """守衛用之 canonical hash：`sha256(",".join(sorted(ids)))`（唯一定義處；呼叫方自備 hash 不作證明）。"""
    return hashlib.sha256(",".join(sorted(candidate_ids)).encode("utf-8")).hexdigest()


def check_universe_provenance(
    prov: Optional[UniverseProvenance],
    candidate_ids: Sequence[str],
    n_candidates: int,
    ledger_result: Optional[LedgerReadResult],
) -> GuardResult:
    """Task 4.3 守衛：回 `(status, reason)`；唯一成功路徑＝`ledger_all_candidates` 且三項全符。

    Raises:
        ValueError: `prov is None`／`source` 不在契約 `universe_source_values`。
    """
    if prov is None:
        raise ValueError("universe_provenance 必填（禁 None）")
    allowed = load_strategy_validation_contract()["universe_source_values"]
    if prov.source not in allowed:
        raise ValueError(f"universe_provenance.source {prov.source!r} 不在契約 universe_source_values {allowed}")
    if prov.selection_free is not True:
        return GuardResult(_validated_status("not_computed"), _REASON_CONTAMINATED)
    if prov.source != _SOURCE_LEDGER_ALL:
        return GuardResult(_validated_status("unavailable"), _REASON_UNVERIFIABLE)  # full_grid／external_declared：無例外
    if ledger_result is None or ledger_result.status != "ok":
        return GuardResult(_validated_status("unavailable"), _REASON_UNVERIFIABLE)
    ids = list(candidate_ids)
    set_ok = frozenset(ids) == frozenset(ledger_result.candidate_ids)
    count_ok = (
        prov.candidate_count == ledger_result.n_candidates_considered == n_candidates == len(ids)
        and len(frozenset(ids)) == len(ids)
    )
    hash_ok = prov.candidate_set_hash == candidate_set_hash(ids)
    if set_ok and count_ok and hash_ok:
        return GuardResult(_validated_status("ok"), "")
    return GuardResult(_validated_status("unavailable"), _REASON_UNVERIFIABLE)


def _fail(
    *, status: str, reason: str, n_paths: int, universe_scope: Optional[str],
    n_paths_used: int = 0, n_paths_skipped: int = 0, n_path_exclusions: int = 0, n_candidates_invalid: int = 0,
) -> PBOResult:
    nan = float("nan")
    return PBOResult(
        value=nan, logits_min=nan, logits_median=nan, logits_max=nan,
        n_paths=n_paths, n_paths_used=n_paths_used, n_paths_skipped=n_paths_skipped,
        n_path_exclusions=n_path_exclusions, n_candidates_invalid=n_candidates_invalid,
        universe_scope=universe_scope, status=_validated_status(status), reason=reason,
    )


def _metric(col: np.ndarray, idx: np.ndarray, selection_metric: str) -> float:
    """單欄單 path 之選擇指標（參考實作；`sharpe` 直接走 Task 1.2 `compute_sharpe`）。"""
    if selection_metric == "sharpe":
        return float(compute_sharpe(col[idx], periods_per_year=1).value_per_period)  # per-period；退化 ⇒ NaN
    return float(np.mean(col[idx]))  # mean_return


def _sharpe_pp_1d(col: np.ndarray) -> float:
    """per-period Sharpe（rf=0）：與 `compute_sharpe(col, periods_per_year=1).value_per_period` **逐位相同**之 1-D 縮減
    （同一 `values.mean()`／`values.std(ddof=1)` 呼叫序與退化判定：`n<2`／含非有限／`std==0`／**元素位元全等 `ptp==0`（G1-R11）** ⇒ NaN）。
    B4 review N5：2-D `axis=0` 縮減與 1-D 縮減之浮點順序不同，近常數欄會給出不同巨大值 ⇒ 改逐欄 1-D。
    """
    values = np.asarray(col, dtype=float).ravel()
    if values.size < 2 or not np.all(np.isfinite(values)):
        return float("nan")
    std = float(values.std(ddof=1))
    if std == 0.0 or not np.isfinite(std) or float(np.ptp(values)) == 0.0:  # 同 compute_sharpe（G1-R11：常數＝位元全等）
        return float("nan")
    return float(values.mean()) / std


def _metrics_columns(sub: np.ndarray, selection_metric: str) -> np.ndarray:
    """對 `sub`（rows=該 path 之觀測、cols=候選）逐欄算選擇指標，回 shape `(n_cols,)`。

    `sharpe` 逐欄走 `_sharpe_pp_1d`（與 `compute_sharpe` 逐位相同，含近常數欄；
    `test_pbo.py::test_vectorized_sharpe_matches_compute_sharpe` 以 `==` 鎖住）；不逐欄呼叫 `compute_sharpe` 本體是為避開
    scipy 矩計算之成本（924 path × 50 候選 ~30s／案例 → 秒級），統計量定義未變。
    """
    if selection_metric != "sharpe":
        return np.mean(sub, axis=0)
    return np.array([_sharpe_pp_1d(sub[:, j]) for j in range(sub.shape[1])], dtype=float)


def probability_of_backtest_overfitting(
    *,
    returns_matrix: np.ndarray,
    n_obs: int,
    n_candidates: int,
    candidate_ids: Sequence[str],
    s_blocks: int,
    selection_metric: str,
    universe_provenance: UniverseProvenance,
    ledger_result: Optional[LedgerReadResult] = None,
) -> PBOResult:
    """PBO 值（Task 4.2）。

    Raises:
        ValueError: `selection_metric` 不在契約枚舉；`returns_matrix.shape != (n_obs, n_candidates)`；
            `len(candidate_ids) != n_candidates`；守衛之 `ValueError`（prov None／source 非法）。
        CscvBudgetExceeded／ValueError（來自 Task 4.1）：S 非法或超預算。
    """
    contract = load_strategy_validation_contract()
    if selection_metric not in contract["selection_metric_values"]:
        raise ValueError(f"selection_metric {selection_metric!r} 不在契約 selection_metric_values")

    n_paths = cscv_path_count(s_blocks)
    guard = check_universe_provenance(universe_provenance, candidate_ids, n_candidates, ledger_result)
    if guard.status != "ok":
        return _fail(status=guard.status, reason=guard.reason, n_paths=n_paths, universe_scope=None)
    universe_scope = _UNIVERSE_SCOPE_LEDGER_ONLY  # A1-4：守衛 ok 之唯一今日值

    m = np.asarray(returns_matrix, dtype=float)
    if m.ndim != 2 or m.shape != (n_obs, n_candidates):
        raise ValueError(f"returns_matrix.shape={m.shape} != (n_obs, n_candidates)=({n_obs}, {n_candidates})")
    if len(candidate_ids) != n_candidates:
        raise ValueError(f"len(candidate_ids)={len(candidate_ids)} != n_candidates={n_candidates}")

    finite_cols = np.all(np.isfinite(m), axis=0)
    valid_cols = [int(c) for c in np.flatnonzero(finite_cols)]  # 升冪之原始欄索引
    n_invalid = int(n_candidates - len(valid_cols))
    if len(valid_cols) < 2:
        return _fail(
            status="not_computed", reason=_REASON_INSUFFICIENT, n_paths=n_paths,
            universe_scope=universe_scope, n_candidates_invalid=n_invalid,
        )
    pos = {c: i for i, c in enumerate(valid_cols)}

    n_used = n_skipped = n_excl = 0
    logits = []
    m_valid = m[:, valid_cols]  # 欄序＝valid_cols 升冪；壓縮位置 = pos[c]
    for is_idx, oos_idx in iter_cscv_splits(n_obs=n_obs, s_blocks=s_blocks):
        is_metrics = _metrics_columns(m_valid[is_idx], selection_metric)
        path_valid = [c for c in valid_cols if math.isfinite(is_metrics[pos[c]])]
        n_excl += len(valid_cols) - len(path_valid)
        if len(path_valid) < 2:
            n_skipped += 1
            continue
        # champion：path 有效候選中 IS metric 最大者；平手取最小原始欄索引（path_valid 已升冪，argmax 取首個）
        champ = path_valid[int(np.argmax([is_metrics[pos[c]] for c in path_valid]))]
        oos_all = _metrics_columns(m_valid[oos_idx], selection_metric)
        oos_vals = np.array([oos_all[pos[c]] for c in path_valid])
        n_oos_bad = int(np.count_nonzero(~np.isfinite(oos_vals)))
        n_excl += n_oos_bad  # 每候選每 path 至多 +1（B4 review N3；含 champion，不再額外 +1）
        if n_oos_bad > 0:
            # 守 Frozen 字面（B4 review N2）：名次母體＝path_valid、分母＝len(path_valid)+1；任一候選 OOS 非有限即無法
            # 在該母體上取名次（`rankdata` 對 NaN 不可用、縮小母體會系統性改變 r）⇒ 跳過該 path（含 A1-15 之 champion 情形），不重選
            n_skipped += 1
            continue
        oos_pos = {c: i for i, c in enumerate(path_valid)}  # A1-15：以壓縮位置取名次，禁原始索引
        rank = float(rankdata(oos_vals, method="average")[oos_pos[champ]])
        r = rank / (len(path_valid) + 1)
        omega = math.log(r / (1.0 - r))
        logits.append(omega)
        n_used += 1

    if n_used == 0:
        return _fail(
            status="not_computed", reason=_REASON_ALL_DEGENERATE, n_paths=n_paths, universe_scope=universe_scope,
            n_paths_used=0, n_paths_skipped=n_skipped, n_path_exclusions=n_excl, n_candidates_invalid=n_invalid,
        )
    arr = np.asarray(logits, dtype=float)
    return PBOResult(
        value=float(np.mean(arr < 0)),
        logits_min=float(arr.min()),
        logits_median=float(np.median(arr)),
        logits_max=float(arr.max()),
        n_paths=n_paths,
        n_paths_used=n_used,
        n_paths_skipped=n_skipped,
        n_path_exclusions=n_excl,
        n_candidates_invalid=n_invalid,
        universe_scope=universe_scope,
        status=_validated_status("ok"),
        reason="",
    )
