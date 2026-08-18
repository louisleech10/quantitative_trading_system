"""GAP-2a 多因子組合 IC（Task 2.1）＋ paired moving-block bootstrap（自 Task 1.2 搬入，簽名不變）。

定義（SPEC §A D5；字面由 ``ic_survivor_contract.json`` 讀出）：
- 訊號合成：test 列上 ``composite = Σ w_i·sign_i·normal_scores(f_i)``；``sign_i``／``w_i`` **只**由 train 段
  Spearman IC 決定（``equal``：1/k′；``ic_weighted``：|train_ic_i|/Σ|train_ic|）；``sign_i==0`` 或 NaN 之因子
  排除（``excluded[name]="zero_train_ic"``）；全排除 ⇒ ``not_computed:all_zero_train_ic``。
- ``composite_ic = spearmanr(composite, y_te)``；``composite_ic_train_insample``＝同權重／符號於 train 列評估。
- 對照：``top_train_single``＝train 段 |IC| 最大者（其 test IC）；``best_single_test_ic``＝test 段 max|IC|（只作參考，
  **不**當比較基準）；``delta_vs_top_train_single = composite_ic − top_train_single_test_ic``，``delta_ci95``＝成對
  block bootstrap（同一 block 索引重抽 (composite, f_top, y)，統計量＝兩 Spearman 之差）。
- ``fit_scope`` typed 傳入；``oos_guarantees`` 由 orchestrator root 注入，本模組回 ``None`` 佔位。
- 純函式：不 log、不 fillna；complete-case 逐列 finite 過濾並回報 ``n_used_*``。

循環 import：``marginal_ic`` 於模組層 ``from factor_combiner import block_bootstrap_ci``；本模組對 ``marginal_ic``
之原語（``normal_scores``／``_spearman``）於**函式內** lazy import（避免 import 順序相依）。
Python 3.9 相容。
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

try:  # Python 3.8+ 皆有 typing.Literal
    from typing import Literal
except ImportError:  # pragma: no cover
    from typing_extensions import Literal  # type: ignore

import numpy as np
import pandas as pd

from momentum.Analysis.survivor_contract import load_survivor_contract

if TYPE_CHECKING:  # 只供型別檢查；runtime 以 lazy import 避免循環
    from momentum.Analysis.marginal_ic import MarginalICParams

__all__ = ["block_bootstrap_ci", "CompositeResult", "combine_factors"]


# ============================================================================
# paired moving-block bootstrap（Task 1.2 搬入；簽名不變）
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
    - 回傳＝percentile CI 與觀測統計量之**包絡** ``(min(q0.025, point), max(q0.975, point))``（A1-8：恆含點估，含 ``n_bootstrap=1``）。
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
    b = min(int(block_len), n)  # 🔒 block_len 由呼叫方決定（§V-9 mutation 目標行）
    n_blocks = int(math.ceil(n / b))
    rng = np.random.default_rng(seed)
    out: List[float] = []
    point = float(stat_fn(*arrs))  # 觀測統計量（A1-8：CI 取與其之包絡，恆含點估）
    offsets = np.arange(b)
    for _ in range(int(n_bootstrap)):
        starts = rng.integers(0, n - b + 1, size=n_blocks)
        idx = (starts[:, None] + offsets[None, :]).reshape(-1)[:n]
        val = float(stat_fn(*[a[idx] for a in arrs]))
        if math.isfinite(val):
            out.append(val)
    if not out:
        return None
    lo, hi = float(np.quantile(out, 0.025)), float(np.quantile(out, 0.975))
    if math.isfinite(point):  # A1-8（R15 CODEX-R15-P1-01）：percentile CI 與觀測統計量之包絡 ⇒ 恆含點估（n_bootstrap=1 亦然）
        lo, hi = min(lo, point), max(hi, point)
    return (lo, hi)


# ============================================================================
# 結果 dataclass
# ============================================================================
@dataclass(frozen=True)
class CompositeResult:
    """``combine_factors`` typed 結果；``to_dict()`` 鍵集 == 契約 ``marginal_ic_section_keys.composite_keys``。"""

    status: str
    reason: Optional[str]
    method: str
    weights: Mapping[str, float]
    signs: Mapping[str, float]
    excluded: Mapping[str, str]
    composite_ic: Optional[float]
    composite_ic_train_insample: Optional[float]
    top_train_single: Optional[str]
    top_train_single_test_ic: Optional[float]
    best_single_test_ic: Optional[float]
    best_single_feature: Optional[str]
    delta_vs_top_train_single: Optional[float]
    delta_ci95: Optional[Tuple[float, float]]
    n_used_test: int
    n_used_train: int
    fit_scope: Optional[str]
    oos_guarantees: Optional[bool]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "method": self.method,
            "weights": copy.deepcopy(dict(self.weights)),
            "signs": copy.deepcopy(dict(self.signs)),
            "excluded": copy.deepcopy(dict(self.excluded)),
            "composite_ic": self.composite_ic,
            "composite_ic_train_insample": self.composite_ic_train_insample,
            "top_train_single": self.top_train_single,
            "top_train_single_test_ic": self.top_train_single_test_ic,
            "best_single_test_ic": self.best_single_test_ic,
            "best_single_feature": self.best_single_feature,
            "delta_vs_top_train_single": self.delta_vs_top_train_single,
            "delta_ci95": list(self.delta_ci95) if self.delta_ci95 is not None else None,
            "n_used_test": self.n_used_test,
            "n_used_train": self.n_used_train,
            "fit_scope": self.fit_scope,
            "oos_guarantees": self.oos_guarantees,
        }


def _empty(status: str, reason: str, method: str, fit_scope: Optional[str], n_used_test: int = 0, n_used_train: int = 0, excluded: Optional[Dict[str, str]] = None) -> CompositeResult:
    return CompositeResult(
        status=status, reason=reason, method=method, weights={}, signs={}, excluded=excluded or {},
        composite_ic=None, composite_ic_train_insample=None, top_train_single=None,
        top_train_single_test_ic=None, best_single_test_ic=None, best_single_feature=None,
        delta_vs_top_train_single=None, delta_ci95=None, n_used_test=int(n_used_test),
        n_used_train=int(n_used_train), fit_scope=fit_scope, oos_guarantees=None,
    )


def _reason(contract: Dict[str, Any], group: str, name: str) -> str:
    """reason 字面必來自契約（成員檢查 fail-closed；A1-7 K2）。"""
    pool = contract["reasons"]["marginal_ic"] if group == "section" else contract["reasons"]["marginal_ic_feature"]
    if name not in pool:
        raise KeyError(f"reason {name!r} not in contract reasons.{group}")
    return name


# ============================================================================
# combine_factors
# ============================================================================
def combine_factors(
    features_df: pd.DataFrame,
    label: pd.Series,
    *,
    train_mask: Optional[np.ndarray],
    test_mask: Optional[np.ndarray],
    survivors: List[str],
    params: MarginalICParams,
    fit_scope: Literal["train", "full_sample"],
) -> CompositeResult:
    """等權／``ic_weighted`` 訊號合成之 test 段 IC，附 train-only 符號／權重與對 ``top_train_single`` 之 delta CI。"""
    from momentum.Analysis.marginal_ic import _finite_or_none, _spearman, normal_scores  # lazy：避免循環 import

    contract = load_survivor_contract()
    fit_scope_values = tuple(contract["fit_scope_values"])
    if fit_scope not in fit_scope_values:
        raise ValueError(f"fit_scope must be one of {fit_scope_values}, got {fit_scope!r}")
    method = str(getattr(params, "weights_method", "equal"))
    if method not in contract["weights_method_values"]:
        raise ValueError(f"weights_method must be one of {contract['weights_method_values']}, got {method!r}")

    n_rows = int(len(features_df.index))
    if fit_scope == "train":
        if train_mask is None or test_mask is None:
            return _empty("not_applicable", _reason(contract, "section", "no_holdout_split"), method, fit_scope)
        tr = np.asarray(train_mask, dtype=bool)
        te = np.asarray(test_mask, dtype=bool)
        if tr.shape[0] != n_rows or te.shape[0] != n_rows:
            raise ValueError("train_mask/test_mask length must equal len(features_df)")
        if tr.all() and te.all():
            raise ValueError("fit_scope=train with all-True masks")
    else:
        tr = np.ones(n_rows, dtype=bool) if train_mask is None else np.asarray(train_mask, dtype=bool)
        te = np.ones(n_rows, dtype=bool) if test_mask is None else np.asarray(test_mask, dtype=bool)
        if tr.shape[0] != n_rows or te.shape[0] != n_rows:
            raise ValueError("train_mask/test_mask length must equal len(features_df)")

    survivors = list(survivors)
    if len(set(survivors)) != len(survivors):
        raise ValueError("survivors contains duplicates")
    if len(survivors) == 0:
        return _empty("not_applicable", _reason(contract, "section", "no_survivors"), method, fit_scope)
    missing = [c for c in survivors if c not in features_df.columns]
    if missing:
        raise KeyError(f"survivors not in features_df: {missing}")

    X = features_df[survivors].to_numpy(dtype=float, na_value=np.nan)
    y = pd.to_numeric(label, errors="coerce").to_numpy(dtype=float, na_value=np.nan)
    if y.shape[0] != n_rows:
        raise ValueError("label length must equal len(features_df)")
    finite_rows = np.isfinite(X).all(axis=1) & np.isfinite(y)
    rows_te = te & finite_rows  # complete-case（步驟 2）
    rows_tr = tr & finite_rows
    n_used_test = int(rows_te.sum())
    n_used_train = int(rows_tr.sum())
    min_rows = int(getattr(params, "min_test_rows"))
    if n_used_test < min_rows:
        return _empty("not_computed", _reason(contract, "section", "insufficient_test_rows"), method, fit_scope, n_used_test, n_used_train)
    if n_used_train < min_rows:
        return _empty("not_computed", _reason(contract, "section", "insufficient_train_rows"), method, fit_scope, n_used_test, n_used_train)

    X_tr, X_te = X[rows_tr], X[rows_te]
    y_tr, y_te = y[rows_tr], y[rows_te]

    # ---- 步驟 3：train_ic／sign（只用 train 段；🔒 §V-7 mutation 目標行）----
    sign_source_X, sign_source_y = X_tr, y_tr
    train_ic: Dict[str, float] = {name: _spearman(sign_source_X[:, j], sign_source_y) for j, name in enumerate(survivors)}
    # test 段單因子 IC：只作 best_single 參考輸出，**禁**用於符號／權重（步驟 5 消費）
    test_ic_all: Dict[str, float] = {name: _spearman(X_te[:, j], y_te) for j, name in enumerate(survivors)}
    signs: Dict[str, float] = {}
    excluded: Dict[str, str] = {}
    for name in survivors:
        v = train_ic[name]
        s = float(np.sign(v)) if math.isfinite(v) else 0.0
        if s == 0.0:
            excluded[name] = _reason(contract, "feature", "zero_train_ic")
        else:
            signs[name] = s
    kept = [n for n in survivors if n in signs]
    if not kept:
        return _empty("not_computed", _reason(contract, "section", "all_zero_train_ic"), method, fit_scope, n_used_test, n_used_train, excluded)

    # ---- 步驟 4：權重（只用 train 段 |IC|；🔒 §V-8 mutation 目標行）----
    weight_source_ic = train_ic
    if method == "equal":
        weights = {n: 1.0 / len(kept) for n in kept}
    else:
        tot = float(sum(abs(weight_source_ic[n]) for n in kept))
        weights = {n: abs(weight_source_ic[n]) / tot for n in kept}

    def _composite(Xm: np.ndarray) -> np.ndarray:
        cols = []
        for n in kept:
            j = survivors.index(n)
            cols.append(weights[n] * signs[n] * normal_scores(Xm[:, j]))
        return np.sum(np.column_stack(cols), axis=1)

    comp_te = _composite(X_te)
    comp_tr = _composite(X_tr)
    composite_ic = _spearman(comp_te, y_te)
    composite_ic_tr = _spearman(comp_tr, y_tr)

    # ---- 步驟 5：對照單因子 ----
    top = max(kept, key=lambda n: (abs(train_ic[n]), -survivors.index(n)))  # tie 依原順序
    j_top = survivors.index(top)
    top_test_ic = test_ic_all[top]
    finite_test = {n: v for n, v in test_ic_all.items() if math.isfinite(v)}
    if finite_test:
        best_name = max(finite_test, key=lambda n: (abs(finite_test[n]), -survivors.index(n)))
        best_ic: Optional[float] = finite_test[best_name]
    else:
        best_name, best_ic = None, None
    delta = composite_ic - top_test_ic if math.isfinite(composite_ic) and math.isfinite(top_test_ic) else float("nan")
    f_top_te = X_te[:, j_top]
    ci = block_bootstrap_ci(
        lambda c, f, yy: _spearman(c, yy) - _spearman(f, yy),
        (comp_te, f_top_te, y_te),
        block_len=int(getattr(params, "block_len")),
        n_bootstrap=int(getattr(params, "n_bootstrap")),
        seed=int(getattr(params, "seed")),
    )
    return CompositeResult(
        status="ok",
        reason=None,
        method=method,
        weights=weights,
        signs=signs,
        excluded=excluded,
        composite_ic=_finite_or_none(composite_ic),
        composite_ic_train_insample=_finite_or_none(composite_ic_tr),
        top_train_single=top,
        top_train_single_test_ic=_finite_or_none(top_test_ic),
        best_single_test_ic=_finite_or_none(best_ic) if best_ic is not None else None,
        best_single_feature=best_name,
        delta_vs_top_train_single=_finite_or_none(delta),
        delta_ci95=ci,
        n_used_test=n_used_test,
        n_used_train=n_used_train,
        fit_scope=fit_scope,
        oos_guarantees=None,
    )
