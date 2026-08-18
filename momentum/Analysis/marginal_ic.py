"""GAP-2a 邊際 IC（semi-partial 秩 IC）純函式（Task 1.1／1.2）。

定義（SPEC §A D1／D3／D3′／D3″／D4；字面值一律由 ``ic_survivor_contract.json`` 讀出）：
- 秩常態分數 ``normal_scores``（van der Waerden）；投影 ``fit_projection`` **只**在呼叫方切好的 train 陣列估計；
  ``apply_residual`` 用同一 β̂ 於任意段取殘差。
- ``compute_marginal_ic``：對每候選 f 與條件集 S，於 train 列擬合 z_f ~ [1, Z_S]，於 test 列取殘差
  r_te，**先**判 ``var(r_te) <= degenerate_threshold`` ⇒ ``not_computed:residual_degenerate``，再算
  ``spearmanr(r_te, y_te)`` 為邊際 IC；另附 gross IC、保留比、train in-sample 邊際 IC、moving-block
  bootstrap CI。三視角：``loo``（S＝survivors∖{f}）／``sequential``（依 |train_ic| 遞減，S＝前序）／
  ``removed_candidates``（S＝全部 survivors）。
- ``fit_scope`` 為呼叫方 typed 傳入，本模組**禁**由 masks 形狀猜；``oos_guarantees``／``pass_class``
  由 orchestrator ``_stage7_report`` 依 root 注入（A1-3），本模組回 ``None`` 佔位、``with_root()`` 供測試填值。
- 純函式：不 log、不讀 orchestrator 狀態；NaN/inf 逐列 finite 過濾並回報 ``n_used_*``（禁 fillna）。

Python 3.9 相容（無 ``match``、無 ``X | Y`` 型別聯集）。
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from momentum.Analysis.survivor_contract import load_survivor_contract

__all__ = [
    "Projection",
    "normal_scores",
    "fit_projection",
    "apply_residual",
    "block_bootstrap_ci",
    "MarginalICParams",
    "MarginalICResult",
    "compute_marginal_ic",
]


# ============================================================================
# Task 1.1 — 原語
# ============================================================================
@dataclass(frozen=True)
class Projection:
    """train 段最小平方投影參數（含截距）。"""

    beta: np.ndarray  # 長度 1+k（第 0 個為截距）
    condition_number: float
    r2_train: float
    n_train: int


def normal_scores(x: np.ndarray) -> np.ndarray:
    """van der Waerden 秩常態分數：``norm.ppf(rank_avg/(n+1))``。

    - ``x`` 須一維且全部有限（否則 ``ValueError``）；``n<2`` ⇒ ``ValueError``。
    - 對嚴格單調變換不變；全 ties ⇒ 全 0。
    """
    arr = np.asarray(x, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"normal_scores expects 1-D input, got ndim={arr.ndim}")
    if not np.isfinite(arr).all():
        raise ValueError("normal_scores input contains non-finite values")
    n = arr.shape[0]
    if n < 2:
        raise ValueError(f"normal_scores needs n>=2, got n={n}")
    r = stats.rankdata(arr, method="average")
    return stats.norm.ppf(r / (n + 1.0))


def fit_projection(z_target: np.ndarray, z_basis: np.ndarray) -> Projection:
    """最小平方擬合 ``z_target ~ [1, z_basis]``（``rcond=None``）。

    ``z_basis`` 形狀 ``(n, k)``，``k`` 可為 0（只剩截距 ⇒ ``beta=[mean]``）。長度不符 ⇒ ``ValueError``。
    共線 basis 不 raise（``condition_number`` 極大），由呼叫方依殘差退化判。
    """
    target = np.asarray(z_target, dtype=float)
    basis = np.asarray(z_basis, dtype=float)
    if target.ndim != 1:
        raise ValueError("fit_projection: z_target must be 1-D")
    n = target.shape[0]
    if basis.ndim == 1:
        basis = basis.reshape(n, -1) if basis.size else np.empty((n, 0))
    if basis.ndim != 2 or basis.shape[0] != n:
        raise ValueError(
            f"fit_projection: z_basis shape {basis.shape} incompatible with n={n}"
        )
    if not (np.isfinite(target).all() and np.isfinite(basis).all()):
        raise ValueError("fit_projection: non-finite input")
    X = np.column_stack([np.ones(n), basis])
    beta, *_ = np.linalg.lstsq(X, target, rcond=None)
    fitted = X @ beta
    ss_res = float(np.sum((target - fitted) ** 2))
    ss_tot = float(np.sum((target - target.mean()) ** 2))
    r2_train = 0.0 if ss_tot == 0.0 else 1.0 - ss_res / ss_tot
    condition_number = float(np.linalg.cond(X))
    return Projection(
        beta=np.asarray(beta, dtype=float),
        condition_number=condition_number,
        r2_train=float(r2_train),
        n_train=int(n),
    )


def apply_residual(z_target: np.ndarray, z_basis: np.ndarray, projection: Projection) -> np.ndarray:
    """以 ``projection.beta`` 於任意段取殘差 ``z_target - [1, z_basis] @ beta``；欄數不符 ⇒ ``ValueError``。"""
    target = np.asarray(z_target, dtype=float)
    basis = np.asarray(z_basis, dtype=float)
    m = target.shape[0]
    if basis.ndim == 1:
        basis = basis.reshape(m, -1) if basis.size else np.empty((m, 0))
    if basis.ndim != 2 or basis.shape[0] != m:
        raise ValueError(
            f"apply_residual: z_basis shape {basis.shape} incompatible with m={m}"
        )
    X = np.column_stack([np.ones(m), basis])
    if X.shape[1] != projection.beta.shape[0]:
        raise ValueError(
            f"apply_residual: basis columns {X.shape[1]} != beta length {projection.beta.shape[0]}"
        )
    return target - X @ projection.beta


# ============================================================================
# Task 1.2 — moving-block bootstrap（B2 Task 2.1 搬至 factor_combiner.py，簽名不變）
# ============================================================================
def block_bootstrap_ci(
    stat_fn: Callable[..., float],
    arrays: Sequence[np.ndarray],
    *,
    block_len: int,
    n_bootstrap: int,
    seed: int,
) -> Optional[Tuple[float, float]]:
    """成對 moving-block bootstrap 95% CI。

    - ``arrays`` 為同長度陣列（同一組 block 索引同時重抽 ⇒ 成對）；``block_len<=0`` ⇒ ``ValueError``；
      ``n_bootstrap<1`` ⇒ ``ValueError``；``block_len>n`` 時截為 ``n``（單一 block）。
    - 每次抽 ``ceil(n/block_len)`` 個起點 ``rng.integers(0, n-block_len+1)``，串接後切至 ``n``。
    - 統計量非有限者略過；全部非有限 ⇒ 回 ``None``；否則 ``(q0.025, q0.975)``。
    """
    if block_len <= 0:
        raise ValueError(f"block_len must be >= 1, got {block_len}")
    if n_bootstrap < 1:
        raise ValueError(f"n_bootstrap must be >= 1, got {n_bootstrap}")
    arrs = [np.asarray(a) for a in arrays]
    if not arrs:
        raise ValueError("block_bootstrap_ci needs at least one array")
    n = arrs[0].shape[0]
    if any(a.shape[0] != n for a in arrs):
        raise ValueError("block_bootstrap_ci arrays must share length")
    if n == 0:
        return None
    b = min(int(block_len), n)
    n_blocks = int(math.ceil(n / b))
    rng = np.random.default_rng(seed)
    out: List[float] = []
    offsets = np.arange(b)
    for _ in range(int(n_bootstrap)):
        starts = rng.integers(0, n - b + 1, size=n_blocks)
        idx = (starts[:, None] + offsets[None, :]).reshape(-1)[:n]
        val = stat_fn(*[a[idx] for a in arrs])
        val = float(val)
        if math.isfinite(val):
            out.append(val)
    if not out:
        return None
    return (float(np.quantile(out, 0.025)), float(np.quantile(out, 0.975)))


# ============================================================================
# Task 1.2 — 參數／結果 dataclass
# ============================================================================
@dataclass(frozen=True)
class MarginalICParams:
    """邊際 IC 計算參數（預設值鏡像 B4 ``MarginalICConfig``；``block_len`` 由呼叫方依 horizon 決定）。"""

    min_test_rows: int = 30
    min_rows_per_regressor: int = 5
    degenerate_threshold: float = 1e-10
    n_bootstrap: int = 1000
    block_len: int = 5
    seed: int = 20260818
    weights_method: str = "equal"
    max_survivors_for_loo: int = 200
    max_removed_candidates: int = 200


@dataclass(frozen=True)
class MarginalICResult:
    """``compute_marginal_ic`` typed 結果；``to_dict()`` 鍵集 == 契約 ``marginal_ic_section_keys.section_keys``。"""

    status: str
    reason: Optional[str]
    fit_scope: Optional[str]
    oos_guarantees: Optional[bool]
    pass_class: Optional[str]
    statistic: str
    projection_space: str
    independent_oos_validation: bool
    selection_sample: str
    oos_semantics: str
    algorithm_version: str
    views: Mapping[str, Dict[str, Optional[str]]]
    per_feature: Mapping[str, Dict[str, Any]]
    sequential: Tuple[Dict[str, Any], ...]
    removed_candidates: Mapping[str, Dict[str, Any]]
    train_ic: Mapping[str, Optional[float]]
    n_train: Optional[int]
    n_test: Optional[int]
    n_regressions: int
    budget: Mapping[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """JSON 友善 deep copy（tuple → list；Mapping → dict）。"""
        return {
            "status": self.status,
            "reason": self.reason,
            "fit_scope": self.fit_scope,
            "oos_guarantees": self.oos_guarantees,
            "pass_class": self.pass_class,
            "statistic": self.statistic,
            "projection_space": self.projection_space,
            "independent_oos_validation": self.independent_oos_validation,
            "selection_sample": self.selection_sample,
            "oos_semantics": self.oos_semantics,
            "algorithm_version": self.algorithm_version,
            "views": copy.deepcopy(dict(self.views)),
            "per_feature": copy.deepcopy(dict(self.per_feature)),
            "sequential": copy.deepcopy(list(self.sequential)),
            "removed_candidates": copy.deepcopy(dict(self.removed_candidates)),
            "train_ic": copy.deepcopy(dict(self.train_ic)),
            "n_train": self.n_train,
            "n_test": self.n_test,
            "n_regressions": self.n_regressions,
            "budget": copy.deepcopy(dict(self.budget)),
        }

    def with_root(self, analysis_status: str) -> "MarginalICResult":
        """依 root ``analysis_status`` 填 OOS 兩欄（單一來源＝root；``ok_oos`` ⇒ (True, "oos")）。"""
        if analysis_status == "ok_oos":
            oos, pc = True, "oos"
        else:
            oos, pc = False, "full_sample_research_only"
        return MarginalICResult(**{**self.__dict__, "oos_guarantees": oos, "pass_class": pc})


# ============================================================================
# 內部 helper
# ============================================================================
def _finite_or_none(value: Any) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman ρ；``n<2`` 或任一常數 ⇒ NaN（不 raise、不 warning）。"""
    if a.shape[0] < 2 or np.ptp(a) == 0.0 or np.ptp(b) == 0.0:
        return float("nan")
    return float(stats.spearmanr(a, b)[0])


def _not_computed_stat(reason: str, conditioning_set: Sequence[str], n_used_train: int, n_used_test: int) -> Dict[str, Any]:
    return {
        "status": "not_computed",
        "reason": reason,
        "conditioning_set": list(conditioning_set),
        "marginal_ic": None,
        "gross_ic": None,
        "ic_retained_ratio": None,
        "marginal_ic_train_insample": None,
        "ci95": None,
        "condition_number": None,
        "r2_train": None,
        "n_used_train": int(n_used_train),
        "n_used_test": int(n_used_test),
    }


def _empty_result(
    *,
    status: str,
    reason: str,
    fit_scope: Optional[str],
    literals: Dict[str, Any],
    views: Dict[str, Dict[str, Optional[str]]],
    train_ic: Optional[Dict[str, Optional[float]]] = None,
    n_train: Optional[int] = None,
    n_test: Optional[int] = None,
    n_regressions: int = 0,
    budget: Optional[Dict[str, int]] = None,
) -> MarginalICResult:
    return MarginalICResult(
        status=status,
        reason=reason,
        fit_scope=fit_scope,
        oos_guarantees=None,
        pass_class=None,
        statistic=literals["statistic"],
        projection_space=literals["projection_space"],
        independent_oos_validation=False,
        selection_sample=literals["selection_sample"],
        oos_semantics=literals["oos_semantics"],
        algorithm_version=literals["algorithm_version"],
        views=views,
        per_feature={},
        sequential=(),
        removed_candidates={},
        train_ic=train_ic or {},
        n_train=n_train,
        n_test=n_test,
        n_regressions=int(n_regressions),
        budget=budget or {},
    )


def _load_literals() -> Dict[str, Any]:
    contract = load_survivor_contract()
    return {
        "statistic": contract["statistic_values"][0],
        "projection_space": contract["projection_space_values"][0],
        "selection_sample": contract["selection_sample_values"][0],
        "oos_semantics": contract["oos_semantics_values"][0],
        "algorithm_version": contract["algorithm_version"],
        "fit_scope_values": tuple(contract["fit_scope_values"]),
        "view_values": tuple(contract["view_values"]),
        "reasons_section": tuple(contract["reasons"]["marginal_ic"]),
        "reasons_feature": tuple(contract["reasons"]["marginal_ic_feature"]),
    }


def _reason(literals: Dict[str, Any], group: str, name: str) -> str:
    """reason 字面必來自契約（不寫死）；不在契約 ⇒ 程式錯誤（KeyError 級，非資料錯）。"""
    pool = literals["reasons_section"] if group == "section" else literals["reasons_feature"]
    if name not in pool:
        raise KeyError(f"reason {name!r} not in contract reasons.{group}")
    return name


# ============================================================================
# Task 1.2 — 主計算
# ============================================================================
def compute_marginal_ic(
    features_df: pd.DataFrame,
    label: pd.Series,
    *,
    train_mask: Optional[np.ndarray],
    test_mask: Optional[np.ndarray],
    survivors: List[str],
    extra_candidates: Sequence[str] = (),
    params: MarginalICParams,
    fit_scope: str,
) -> MarginalICResult:
    """semi-partial 秩 IC 完整計算（loo＋sequential＋removed_candidates）。詳見模組 docstring。"""
    literals = _load_literals()
    if fit_scope not in literals["fit_scope_values"]:
        raise ValueError(f"fit_scope must be one of {literals['fit_scope_values']}, got {fit_scope!r}")
    view_names = literals["view_values"]  # ("loo", "sequential", "removed_candidates")

    def _views(status: str, reason: Optional[str]) -> Dict[str, Dict[str, Optional[str]]]:
        return {v: {"status": status, "reason": reason} for v in view_names}

    # ---- fit_scope 守衛（步驟 1）：不由 masks 形狀猜；只驗互斥組合 ----
    n_rows = int(len(features_df.index))
    if fit_scope == "train":
        if train_mask is None or test_mask is None:
            r = _reason(literals, "section", "no_holdout_split")
            return _empty_result(status="not_applicable", reason=r, fit_scope=fit_scope,
                                 literals=literals, views=_views("not_applicable", r))
        tr = np.asarray(train_mask, dtype=bool)
        te = np.asarray(test_mask, dtype=bool)
        if tr.shape[0] != n_rows or te.shape[0] != n_rows:
            raise ValueError("train_mask/test_mask length must equal len(features_df)")
        if tr.all() and te.all():
            raise ValueError("fit_scope=train with all-True masks")
    else:  # full_sample：呼叫方（loud fallback）傳全 True；None 視為全 True
        tr = np.ones(n_rows, dtype=bool) if train_mask is None else np.asarray(train_mask, dtype=bool)
        te = np.ones(n_rows, dtype=bool) if test_mask is None else np.asarray(test_mask, dtype=bool)
        if tr.shape[0] != n_rows or te.shape[0] != n_rows:
            raise ValueError("train_mask/test_mask length must equal len(features_df)")

    survivors = list(survivors)
    if len(set(survivors)) != len(survivors):
        raise ValueError("survivors contains duplicates")
    n_train = int(tr.sum())
    n_test = int(te.sum())

    if len(survivors) == 0:
        r = _reason(literals, "section", "no_survivors")
        return _empty_result(status="not_applicable", reason=r, fit_scope=fit_scope,
                             literals=literals, views=_views("not_applicable", r),
                             n_train=n_train, n_test=n_test)

    missing = [c for c in survivors if c not in features_df.columns]
    if missing:
        raise KeyError(f"survivors not in features_df: {missing}")

    # ---- 預算 gate（步驟 2；先於任何計算）----
    removed_names = [c for c in dict.fromkeys(extra_candidates) if c not in set(survivors)]
    missing_extra = [c for c in removed_names if c not in features_df.columns]
    if missing_extra:
        raise KeyError(f"extra_candidates not in features_df: {missing_extra}")
    budget = {
        "max_survivors_for_loo": int(params.max_survivors_for_loo),
        "max_removed_candidates": int(params.max_removed_candidates),
        "n_survivors": int(len(survivors)),
        "n_removed_candidates": int(len(removed_names)),
    }
    loo_budget_ok = len(survivors) <= params.max_survivors_for_loo
    removed_budget_ok = len(removed_names) <= params.max_removed_candidates
    budget_reason = _reason(literals, "section", "candidate_budget_exceeded")

    # ---- 全域列數 gate ----
    if n_test < params.min_test_rows:
        r = _reason(literals, "section", "insufficient_test_rows")
        return _empty_result(status="not_computed", reason=r, fit_scope=fit_scope,
                             literals=literals, views=_views("not_computed", r),
                             n_train=n_train, n_test=n_test, budget=budget)
    if n_train < params.min_test_rows:
        r = _reason(literals, "section", "insufficient_train_rows")
        return _empty_result(status="not_computed", reason=r, fit_scope=fit_scope,
                             literals=literals, views=_views("not_computed", r),
                             n_train=n_train, n_test=n_test, budget=budget)

    # ---- 資料矩陣（float；缺值→NaN；逐列 finite 過濾於各候選內做，禁 fillna）----
    all_cols = list(dict.fromkeys(survivors + removed_names))
    X = features_df[all_cols].to_numpy(dtype=float, na_value=np.nan)
    col_idx = {c: i for i, c in enumerate(all_cols)}
    y = pd.to_numeric(label, errors="coerce").to_numpy(dtype=float, na_value=np.nan)
    if y.shape[0] != n_rows:
        raise ValueError("label length must equal len(features_df)")
    finite_y = np.isfinite(y)
    finite_X = np.isfinite(X)

    # ---- train_ic（排序／符號唯一來源＝train 段；步驟 3）----
    def _rank_ic(rows_mask: np.ndarray) -> Dict[str, Optional[float]]:
        out: Dict[str, Optional[float]] = {}
        for name in survivors:
            j = col_idx[name]
            rows = rows_mask & finite_X[:, j] & finite_y
            out[name] = _finite_or_none(_spearman(X[rows, j], y[rows])) if rows.sum() >= 2 else None
        return out

    train_rows_mask = tr
    test_rows_mask = te
    train_ic = _rank_ic(train_rows_mask)
    order_key_ic = train_ic  # 🔒 sequential 排序只准用 train IC（§V-5 mutation 目標行）
    order = sorted(
        survivors,
        key=lambda n: (-abs(order_key_ic[n]) if order_key_ic[n] is not None else 0.0, n),
    )

    n_regressions = 0
    thr = float(params.degenerate_threshold)

    # ---- 單候選計算（步驟 4）----
    def _one(f: str, S: Sequence[str]) -> Dict[str, Any]:
        nonlocal n_regressions
        S = list(S)
        cols = [col_idx[f]] + [col_idx[s] for s in S]
        finite_rows = finite_X[:, cols].all(axis=1) & finite_y
        rows_tr = train_rows_mask & finite_rows
        rows_te = test_rows_mask & finite_rows
        n_used_train = int(rows_tr.sum())
        n_used_test = int(rows_te.sum())
        need = max(int(params.min_test_rows), int(params.min_rows_per_regressor) * len(S))
        if n_used_test < need or n_used_train < need or n_used_train < 2 or n_used_test < 2:
            return _not_computed_stat(_reason(literals, "feature", "insufficient_rows"), S, n_used_train, n_used_test)

        f_tr_raw = X[rows_tr, col_idx[f]]
        f_te_raw = X[rows_te, col_idx[f]]
        y_tr = y[rows_tr]
        y_te = y[rows_te]
        # A1-7 K4：label 於任一段為常數 ⇒ 秩相關無定義 ⇒ 候選 not_computed（先於任何 Spearman）
        if np.ptp(y_te) == 0.0 or np.ptp(y_tr) == 0.0:
            return _not_computed_stat(_reason(literals, "feature", "label_degenerate"), S, n_used_train, n_used_test)
        z_f_tr = normal_scores(f_tr_raw)
        z_f_te = normal_scores(f_te_raw)
        Z_S_tr = (
            np.column_stack([normal_scores(X[rows_tr, col_idx[s]]) for s in S])
            if S else np.empty((n_used_train, 0))
        )
        Z_S_te = (
            np.column_stack([normal_scores(X[rows_te, col_idx[s]]) for s in S])
            if S else np.empty((n_used_test, 0))
        )
        proj = fit_projection(z_f_tr, Z_S_tr)  # 🔒 投影只在 train 估計（§V-1 mutation 目標行）
        n_regressions += 1
        r_te = apply_residual(z_f_te, Z_S_te, proj)
        # 🔒 先判退化，再算 Spearman（§V-21 mutation 目標行）
        if float(np.var(r_te)) <= thr:
            return _not_computed_stat(_reason(literals, "feature", "residual_degenerate"), S, n_used_train, n_used_test)
        marginal_ic = _spearman(r_te, y_te)  # 🔒 秩相關（§V-3 mutation 目標行）
        gross_ic = _spearman(f_te_raw, y_te)
        ratio = (marginal_ic / gross_ic) if abs(gross_ic) >= 1e-12 and math.isfinite(gross_ic) else float("nan")
        r_tr = apply_residual(z_f_tr, Z_S_tr, proj)
        if float(np.var(r_tr)) <= thr:
            insample = float("nan")
        else:
            insample = _spearman(r_tr, y_tr)  # 🔒 train in-sample 於 train 段評估（§V-17a mutation 目標行）
        ci = block_bootstrap_ci(
            lambda a, b: _spearman(a, b),
            (r_te, y_te),
            block_len=params.block_len,
            n_bootstrap=params.n_bootstrap,
            seed=params.seed,
        )
        return {
            "status": "ok",
            "reason": None,
            "conditioning_set": list(S),
            "marginal_ic": _finite_or_none(marginal_ic),
            "gross_ic": _finite_or_none(gross_ic),
            "ic_retained_ratio": _finite_or_none(ratio),
            "marginal_ic_train_insample": _finite_or_none(insample),
            "ci95": [ci[0], ci[1]] if ci is not None else None,
            "condition_number": _finite_or_none(proj.condition_number),
            "r2_train": _finite_or_none(proj.r2_train),
            "n_used_train": n_used_train,
            "n_used_test": n_used_test,
        }

    # ---- 三視角（步驟 5）----
    views: Dict[str, Dict[str, Optional[str]]] = {}
    per_feature: Dict[str, Dict[str, Any]] = {}
    sequential: List[Dict[str, Any]] = []
    removed: Dict[str, Dict[str, Any]] = {}

    no_computable = _reason(literals, "section", "no_computable_candidates")

    def _view_status(entries: Sequence[Dict[str, Any]]) -> Dict[str, Optional[str]]:
        """A1-7 K4(a)：視角 ok 僅當至少一候選 ok；否則 not_computed:no_computable_candidates。"""
        if any(e["status"] == "ok" for e in entries):
            return {"status": "ok", "reason": None}
        return {"status": "not_computed", "reason": no_computable}

    if loo_budget_ok:  # 🔒 超限 ⇒ 整體 not_computed、無部分值（§V-22a mutation 目標行）
        for f in survivors:
            S = [s for s in survivors if s != f]  # 🔒 依名稱排除自身（§V-4／V-18 mutation 目標行）
            per_feature[f] = _one(f, S)
        for i, f in enumerate(order):
            stat = _one(f, order[:i])
            sequential.append({"feature": f, "step": i, **stat})
        views["loo"] = _view_status(list(per_feature.values()))
        views["sequential"] = _view_status(sequential)
    else:
        views["loo"] = {"status": "not_computed", "reason": budget_reason}
        views["sequential"] = {"status": "not_computed", "reason": budget_reason}

    if not removed_names:
        views["removed_candidates"] = {
            "status": "not_applicable",
            "reason": _reason(literals, "section", "no_removed_candidates"),
        }
    elif removed_budget_ok:
        for c in removed_names:
            removed[c] = _one(c, survivors)
        views["removed_candidates"] = _view_status(list(removed.values()))
    else:
        views["removed_candidates"] = {"status": "not_computed", "reason": budget_reason}

    # A1-7 K4(b)：節級 status/reason ＝ loo 視角（removed 成功不抬升節 status）
    section_status = views["loo"]["status"]
    section_reason = views["loo"]["reason"]

    return MarginalICResult(
        status=section_status,
        reason=section_reason,
        fit_scope=fit_scope,
        oos_guarantees=None,
        pass_class=None,
        statistic=literals["statistic"],
        projection_space=literals["projection_space"],
        independent_oos_validation=False,
        selection_sample=literals["selection_sample"],
        oos_semantics=literals["oos_semantics"],
        algorithm_version=literals["algorithm_version"],
        views=views,
        per_feature=per_feature,
        sequential=tuple(sequential),
        removed_candidates=removed,
        train_ic=train_ic,
        n_train=n_train,
        n_test=n_test,
        n_regressions=int(n_regressions),
        budget=budget,
    )
