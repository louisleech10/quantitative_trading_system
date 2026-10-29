"""ICPERF Task 0.3 — 深度分析 `factor_orthogonalization`／`factor_exposure` 之獨立 oracle 對照（稽核）。

規格：`docs/ICPERF_SPEC.md` Task 0.3／0.4（v5.26：深度分析全部模組含預設關閉者之全部欄位；資料充足判準；讀碼盤點第 124、127 行）。
兩模組於 `ic_config_schema.py:283-294` 皆預設 `enabled=False`。

- 產品入口：`ICFilterOrchestrator.run_deep_analysis(force_modules=[...])` → `_run_factor_orthogonalization`
  （`ic_filter_orchestrator.py:3043-3090`）／`_run_factor_exposure`（`:3092-3199`），例外由 `run_deep_analysis`
  （`:2795-2809`）包成 `{skipped, reason, error_type}`；深度報告 `results.<模組鍵>` 經 `dataclasses.asdict`（同
  `api/services/ic_analysis_service.py:3211-3225` `_serialize_deep_report`）。
- oracle：`statsmodels.api.OLS`（Gram–Schmidt 殘差、beta 中和之斜率）、`numpy.corrcoef`、`numpy.linalg.svd`（PCA），
  與測試自寫之最簡參考實作（排序、曝險、集中度、逐根滾動標準差，每一公式註明產品檔:行）；**不呼叫被測模組或其內部函式**。
- 不一致（稽核要找的結果）標 `xfail(strict=True)`，reason 引收據路徑；不修產品碼（改值落 Task 0.4）。
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
#: SPEC Task 0.3「驗證」：浮點對照之相對誤差門檻
REL_TOL = 1e-12
HEAVY_MARKERS = ("slow", "requires_kline")
NON_STAT = "非統計欄"
RECEIPT = "handoffs/run_receipts/<日期>-icperf-correctness.json"
ORTH = "factor_orthogonalization"
EXPO = "factor_exposure"
#: factor_orthogonalizer.py:22 之預設（ICConfig 無此欄 ⇒ 產品恆用預設）
DEGENERATE_THRESHOLD = 1e-10
#: 真實資料格列數（SPEC Task 0.3 長資料格 L＝2,000 列）
REAL_ROWS = 2000


def _watchdog_missing(markers: Sequence[str], environ: Mapping[str, str]) -> bool:
    """標 slow 或 requires_kline 而未在共用監看下執行 ⇒ True（共用監看對子行程恆注入 `WATCHDOG_STACK_FILE`）。"""
    return any(m in HEAVY_MARKERS for m in markers) and not environ.get("WATCHDOG_STACK_FILE")


@pytest.fixture(autouse=True)
def _heavy_tests_require_shared_watchdog(request: pytest.FixtureRequest) -> None:
    """同 test_icperf_gate.py：本檔重型／真實資料測試於執行端自證經共用監看，未經即 FAIL。"""
    if _watchdog_missing([m.name for m in request.node.iter_markers()], os.environ):
        pytest.fail("本檔標 slow／requires_kline 之測試須經共用監看執行："
                    "venv/bin/python scripts/run_watched.py --log <路徑> -- <pytest 命令>（背景）")


def _rel(a: float, b: float) -> float:
    """相對誤差（相等含同號 inf ⇒ 0；兩者皆 NaN ⇒ 0；一方 NaN ⇒ inf；b 為 0 ⇒ 絕對誤差）。"""
    if math.isnan(a) and math.isnan(b):
        return 0.0
    if math.isnan(a) or math.isnan(b):
        return math.inf
    if a == b:
        return 0.0
    if math.isinf(a) or math.isinf(b):
        return math.inf
    return abs(a - b) / abs(b) if b != 0 else abs(a - b)


# ── 欄位清冊 ────────────────────────────────────────────────────────────────────────────────────────────

#: oracle 項 id → 說明（MODULE_FIELDS 之 oracle 欄引用）
ORACLES: Dict[str, str] = {
    "orth.priority_order": "測試自寫排序參考：icir_scores 非空且全有限 ⇒ ICIR 降序（值為 dict 取 'icir'，ic_engine.py:488-493 之形狀），"
                           "否則 |值| 均值降序（factor_orthogonalizer.py:127-142）",
    "orth.correlation_before": "numpy.corrcoef（同列剔除後之排序矩陣）取絕對值之非對角 nanmean（factor_orthogonalizer.py:65、:144-153）",
    "orth.correlation_after": "Gram–Schmidt 定義：逐欄以 statsmodels OLS（無截距、對前序欄）殘差單位化為正交基（數值零殘差之欄為零向量），"
                              "numpy.corrcoef 絕對值之非對角 nanmean（factor_orthogonalizer.py:43-44、:66）",
    "orth.residual_variance": "statsmodels.api.OLS(target, 前序欄).fit().resid 之 np.var（ddof=0）（factor_orthogonalizer.py:49-56）",
    "orth.degenerate": "同上殘差變異 ≤ degenerate_threshold（factor_orthogonalizer.py:57-59）",
    "pca.explained_variance_ratio": "numpy.linalg.svd(去均值矩陣) 之 s²／Σs²（全部成分為分母，同 sklearn 定義）",
    "pca.loadings": "numpy.linalg.svd 右奇異向量，符號依 sklearn svd_flip(u_based_decision=False)：每成分絕對值最大之分量為正；"
                    "單位向量故以絕對誤差判",
    "exposure.portfolio_exposure": "測試自寫：Σ_t 有限值 x_t／列數 n（缺值當 0、時間等權 1/n；ic_filter_orchestrator.py:3115-3117、"
                                   "factor_exposure_analyzer.py:176-184）",
    "exposure.concentration": "測試自寫：w=|e|/Σ|e|、HHI=Σw²、argmax 取首、門檻與警告規則（factor_exposure_analyzer.py:302-337）",
    "exposure.neutralized": "none：缺值當 0；beta_neutral：statsmodels OLS（含截距）於 x 與市場代理共同有效樣本之斜率 β，x−β·m；"
                            "vol_neutral：逐根 PIT 滾動標準差（numpy ddof=1，只用 0..t）；inf→NaN→0 後同曝險公式"
                            "（factor_exposure_analyzer.py:97-159；代理＝收盤簡單報酬落後 1 根，ic_filter_orchestrator.py:3109-3113）",
    "exposure.delta_hhi": "原始 HHI − 中和後 HHI（ic_filter_orchestrator.py:3140-3144）",
}

_ORCH = "ic_filter_orchestrator.py"
_FO = "factor_orthogonalizer.py"
_FE = "factor_exposure_analyzer.py"

#: 正交化 envelope（非統計欄）：相對模組 dict 之路徑 → 產生之檔:行
_ORTH_ENVELOPE: Dict[str, str] = {
    "typed_result/module": f"{_ORCH}:3072-3077、:3080",
    "typed_result/oos_guarantees": f"{_ORCH}:3072-3077",
    "typed_result/fit_scope": f"{_ORCH}:3072-3077",
    "typed_result/payload/method": f"{_ORCH}:3068",
    "typed_result/payload/orthogonalized_hash": f"{_ORCH}:3062-3069",
    "typed_result/payload/summary/transformed_shape/#": f"{_ORCH}:3070",
    "module": f"{_ORCH}:3081",
    "oos_guarantees": f"{_ORCH}:3082",
    "fit_scope": f"{_ORCH}:3083",
    "payload/method": f"{_ORCH}:3068、:3084",
    "payload/orthogonalized_hash": f"{_ORCH}:3062-3069、:3084",
    "payload/summary/transformed_shape/#": f"{_ORCH}:3070、:3084",
    "transformed_shape/#": f"{_ORCH}:3085",
    "export_scope": f"{_ORCH}:3086",
    "consumer_deny": f"{_ORCH}:3087",
}
#: Gram–Schmidt 摘要：相對 summary 之路徑 → (oracle, 檔:行)；摘要於模組 dict 出現三份（頂層 :3089、payload/summary :3070、
#: typed_result/payload/summary :3072-3077）
_ORTH_GS: Dict[str, Tuple[str, str]] = {
    "method": (NON_STAT, f"{_FO}:69"),
    "priority_order/#": ("orth.priority_order", f"{_FO}:70（:39、:127-142）"),
    "correlation_before": ("orth.correlation_before", f"{_FO}:71（:65、:144-153）"),
    "correlation_after": ("orth.correlation_after", f"{_FO}:72（:43-44、:66、:144-153）"),
    "features/*/residual_variance": ("orth.residual_variance", f"{_FO}:60-61（:48-56）"),
    "features/*/degenerate": ("orth.degenerate", f"{_FO}:62（:57）"),
    "degenerate_features/#": ("orth.degenerate", f"{_FO}:74（:58-59）"),
}
_ORTH_PCA: Dict[str, Tuple[str, str]] = {
    "method": (NON_STAT, f"{_FO}:115"),
    "n_components": (NON_STAT, f"{_FO}:116（:99-101；計數）"),
    "explained_variance_ratio/#": ("pca.explained_variance_ratio", f"{_FO}:117（:103-104）"),
    "loadings/*/PC#": ("pca.loadings", f"{_FO}:118（:108-112）"),
    "principal_components/#": (NON_STAT, f"{_FO}:119（:105；名單）"),
}
_ORTH_SKIP: Dict[str, Tuple[str, str]] = {
    "module_name": (NON_STAT, f"{_FO}:33、:86、:93"),
    "skipped": (NON_STAT, f"{_FO}:34、:87、:94；頂層另由 {_ORCH}:2801（runner 例外）"),
    "reason": (NON_STAT, f"{_FO}:35、:88、:95；頂層另由 {_ORCH}:2802"),
    "error_type": (NON_STAT, f"{_FO}:36、:89、:96；頂層另由 {_ORCH}:2803"),
}
_EXPO_ENVELOPE: Dict[str, str] = {
    "typed_result/module": f"{_ORCH}:3181-3186、:3190",
    "typed_result/oos_guarantees": f"{_ORCH}:3181-3186",
    "typed_result/fit_scope": f"{_ORCH}:3181-3186",
    "typed_result/payload/proxy_kind": f"{_ORCH}:3178",
    "typed_result/payload/exposure_hash": f"{_ORCH}:3170-3179",
    "module": f"{_ORCH}:3191",
    "oos_guarantees": f"{_ORCH}:3192",
    "fit_scope": f"{_ORCH}:3193",
    "payload/proxy_kind": f"{_ORCH}:3178、:3194",
    "payload/exposure_hash": f"{_ORCH}:3170-3179、:3194",
    "export_scope": f"{_ORCH}:3195",
    "consumer_deny": f"{_ORCH}:3196",
}
_CONC = {
    "max_exposure_factor": f"{_FE}:321、:312",
    "max_exposure_value": f"{_FE}:322、:313",
    "hhi": f"{_FE}:320、:314",
    "concentrated": f"{_FE}:335、:315",
    "warnings/#": f"{_FE}:325-329、:316",
}
_EXPO_SUMMARY: Dict[str, Tuple[str, str]] = {
    "portfolio_exposure/*": ("exposure.portfolio_exposure", f"{_ORCH}:3155（:3115-3117、:3127；{_FE}:161-184）"),
    "factor_attribution/status": (NON_STAT, f"{_ORCH}:3156-3160（寫死 unavailable）"),
    "factor_attribution/value": (NON_STAT, f"{_ORCH}:3156-3160"),
    "factor_attribution/reason": (NON_STAT, f"{_ORCH}:3149-3153、:3156-3160"),
    **{f"concentration/{k}": ("exposure.concentration", f"{_ORCH}:3161（:3131-3134；{v}）") for k, v in _CONC.items()},
    "neutralization_mode": (NON_STAT, f"{_ORCH}:3162（設定回顯）"),
    "neutralization_lookback": (NON_STAT, f"{_ORCH}:3163（設定回顯）"),
    "neutralized_portfolio_exposure/*": ("exposure.neutralized", f"{_ORCH}:3164（:3113、:3120-3130；{_FE}:97-159）"),
    **{f"neutralized_concentration/{k}": ("exposure.concentration", f"{_ORCH}:3165（:3135-3138；{v}）")
       for k, v in _CONC.items()},
    "neutralization_delta_hhi": ("exposure.delta_hhi", f"{_ORCH}:3166（:3140-3144）"),
    "proxy_kind": (NON_STAT, f"{_ORCH}:3167"),
    "proxy_lag": (NON_STAT, f"{_ORCH}:3168"),
}
#: runner 例外（如 TypeError、InvalidInputError）由 run_deep_analysis 包之 envelope（只此三鍵）
_RUNNER_ERROR: Dict[str, Tuple[str, str]] = {
    "skipped": (NON_STAT, f"{_ORCH}:2801"),
    "reason": (NON_STAT, f"{_ORCH}:2802"),
    "error_type": (NON_STAT, f"{_ORCH}:2803"),
}
_SUMMARY_COPIES = ("", "payload/summary/", "typed_result/payload/summary/")


def _expand(module: str, envelope: Mapping[str, str], summary: Mapping[str, Tuple[str, str]]) -> Dict[str, Dict[str, str]]:
    out = {f"{module}/{p}": {"oracle": NON_STAT, "producer": prod} for p, prod in envelope.items()}
    for pre in _SUMMARY_COPIES:
        where = {"": f"頂層攤平", "payload/summary/": "payload.summary", "typed_result/payload/summary/": "typed_result.payload.summary"}[pre]
        for p, (oracle, prod) in summary.items():
            out[f"{module}/{pre}{p}"] = {"oracle": oracle, "producer": f"{prod}；{where}"}
    return out


def _error_fields(module: str) -> Dict[str, Dict[str, str]]:
    return {f"{module}/{p}": {"oracle": o, "producer": prod} for p, (o, prod) in _RUNNER_ERROR.items()}


#: 分支 → 該分支產品輸出之欄位清冊（測試 `test_orth_exposure_fields_closed` 逐分支以真實 kline 實跑對照）
BRANCH_FIELDS: Dict[str, Dict[str, Dict[str, str]]] = {
    "orth_gram_schmidt": _expand(ORTH, _ORTH_ENVELOPE, _ORTH_GS),
    "orth_pca": _expand(ORTH, _ORTH_ENVELOPE, _ORTH_PCA),
    "orth_skipped": _expand(ORTH, _ORTH_ENVELOPE, _ORTH_SKIP),
    "orth_runner_error": _error_fields(ORTH),
    "exposure_ok": _expand(EXPO, _EXPO_ENVELOPE, _EXPO_SUMMARY),
    "exposure_runner_error": _error_fields(EXPO),
}
#: 欄位清冊（深度報告 `results.<模組鍵>` 之全部欄位路徑，首段為模組鍵）；分支間同路徑合併 producer
MODULE_FIELDS: Dict[str, Dict[str, str]] = {}
for _branch in BRANCH_FIELDS.values():
    for _path, _spec in _branch.items():
        if _path in MODULE_FIELDS and MODULE_FIELDS[_path]["producer"] != _spec["producer"]:
            assert MODULE_FIELDS[_path]["oracle"] == _spec["oracle"]
            MODULE_FIELDS[_path] = {"oracle": _spec["oracle"],
                                    "producer": f"{MODULE_FIELDS[_path]['producer']}｜{_spec['producer']}"}
        else:
            MODULE_FIELDS.setdefault(_path, dict(_spec))


# ── 攤平與比對 ──────────────────────────────────────────────────────────────────────────────────────────

_EMPTY = object()
_ENVELOPE_PREFIXES = (("typed_result", "payload", "summary"), ("payload", "summary"))


def _to_plain(obj: Any) -> Any:
    """dataclass → dict（同序列化之 asdict），其餘原樣。"""
    return asdict(obj) if is_dataclass(obj) and not isinstance(obj, type) else obj


def _flatten(obj: Any, feats: Set[str], path: Tuple = (), wild: Tuple = ()) -> List[Tuple[Tuple, Optional[Tuple], Any]]:
    """→ [(萬用路徑, 具體路徑, 葉值)]；特徵名段＝`*`、`PC<n>`＝`PC#`、list 索引＝`#`；空 list 記一筆 `#`（值 _EMPTY）。"""
    obj = _to_plain(obj)
    if isinstance(obj, Mapping):
        if not obj:
            return [(wild, path, {})]
        out: List[Tuple[Tuple, Optional[Tuple], Any]] = []
        for k, v in obj.items():
            k = str(k)
            w = "*" if k in feats else ("PC#" if re.fullmatch(r"PC\d+", k) else k)
            out += _flatten(v, feats, path + (k,), wild + (w,))
        return out
    if isinstance(obj, (list, tuple)):
        if not obj:
            return [(wild + ("#",), None, _EMPTY)]
        out = []
        for i, v in enumerate(obj):
            out += _flatten(v, feats, path + (i,), wild + ("#",))
        return out
    return [(wild, path, obj)]


def _field_keys(module: str, output: Any, feats: Sequence[str]) -> Set[str]:
    return {"/".join((module,) + w) for w, _, _ in _flatten(output, set(feats))}


def _is_num(x: Any) -> bool:
    return isinstance(x, (float, int, np.floating, np.integer)) and not isinstance(x, (bool, np.bool_))


def _as_float(x: Any) -> float:
    return float("nan") if x is None else float(x)


Closeness = Callable[[Tuple, float, float], float]


def _verdict(pv: Dict[Tuple, Any], ov: Dict[Tuple, Any], closeness: Optional[Closeness] = None) -> Dict[str, Any]:
    """單一欄位之判定：路徑集合須相等；浮點以 closeness（預設相對誤差）≤ REL_TOL；其餘型別 `==`。"""
    n_finite = sum(1 for v in pv.values() if (_is_num(v) and math.isfinite(float(v))) or (not _is_num(v) and v is not None))
    if set(pv) != set(ov):
        extra = sorted(map(str, set(pv) - set(ov)))[:4]
        miss = sorted(map(str, set(ov) - set(pv)))[:4]
        return {"verdict": "不一致", "max_rel_diff": None, "n_finite": n_finite,
                "detail": f"路徑集合不同：產品多 {extra}，產品缺 {miss}"}
    if not pv:
        return {"verdict": "一致", "max_rel_diff": None, "n_finite": 0, "detail": "雙方皆無值"}
    max_rel: Optional[float] = None
    bad: List[str] = []
    for k in sorted(pv, key=str):
        p, o = pv[k], ov[k]
        if _is_num(p) or _is_num(o) or (p is None and _is_num(o)) or (o is None and _is_num(p)):
            if not ((_is_num(p) or p is None) and (_is_num(o) or o is None)):
                bad.append(f"{k}: 型別不符 {p!r} vs {o!r}")
                continue
            pf, of = _as_float(p), _as_float(o)
            r = closeness(k, pf, of) if closeness else _rel(pf, of)
            max_rel = r if max_rel is None else max(max_rel, r)
            if not r <= REL_TOL:
                bad.append(f"{k}: 產品 {pf!r} vs oracle {of!r}（差 {r:.3g}）")
        elif p != o or type(p) is not type(o) and not (isinstance(p, (bool, np.bool_)) and isinstance(o, (bool, np.bool_))):
            bad.append(f"{k}: 產品 {p!r} vs oracle {o!r}")
    if bad:
        return {"verdict": "不一致", "max_rel_diff": max_rel, "n_finite": n_finite, "detail": "；".join(bad[:4])}
    return {"verdict": "一致", "max_rel_diff": max_rel, "n_finite": n_finite, "detail": f"{len(pv)} 值"}


def _strip_prefix(wild: Tuple) -> int:
    for pre in _ENVELOPE_PREFIXES:
        if wild[: len(pre)] == pre:
            return len(pre)
    return 0


def _compare(module: str, product_output: Any, oracle_summary: Mapping[str, Any], feats: Sequence[str],
             closeness_by_field: Optional[Mapping[str, Closeness]] = None) -> Dict[str, Dict[str, Any]]:
    """對 MODULE_FIELDS 中本模組每一統計欄位（含三份摘要拷貝）逐一判定。"""
    fset = set(feats)
    prod = _flatten(product_output, fset)
    orc = _flatten(oracle_summary, fset)
    results: Dict[str, Dict[str, Any]] = {}
    for path, spec in MODULE_FIELDS.items():
        if not path.startswith(module + "/") or spec["oracle"] == NON_STAT:
            continue
        wild = tuple(path.split("/")[1:])
        k = _strip_prefix(wild)
        rel = wild[k:]
        pv = {c[k:]: v for w, c, v in prod if w == wild and v is not _EMPTY}
        ov = {c: v for w, c, v in orc if w == rel and v is not _EMPTY}
        closeness = (closeness_by_field or {}).get("/".join(rel))
        results[path] = _verdict(pv, ov, closeness)
    return results


# ── 參考實作：factor_orthogonalizer ────────────────────────────────────────────────────────────────────


def _ref_icir_score(value: Any) -> float:
    """ICIR 分數：值為 dict（ic_engine.py:488-493 之 {ic_mean, ic_std, icir, ic_hit_rate}）取 'icir'，否則以數值讀。"""
    if isinstance(value, Mapping):
        value = value.get("icir", float("nan"))
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _ref_priority_order(clean: pd.DataFrame, icir_scores: Mapping[str, Any]) -> List[str]:
    """factor_orthogonalizer.py:132-142：icir 非空 ⇒ 依分數降序（缺者 −inf、Python 穩定排序），全有限才採用；否則 |x| 均值降序。"""
    cols = list(clean.columns)
    if icir_scores:
        scores = {c: (_ref_icir_score(icir_scores[c]) if c in icir_scores else -math.inf) for c in cols}
        order = sorted(cols, key=lambda c: scores[c], reverse=True)
        if all(math.isfinite(scores[c]) for c in cols):
            return order
    abs_mean = np.mean(np.abs(clean.to_numpy(dtype=float)), axis=0)
    return [cols[i] for i in np.argsort(-abs_mean, kind="stable")]


def _offdiag_abs_mean(matrix: np.ndarray) -> float:
    """|corrcoef| 之非對角 nanmean（factor_orthogonalizer.py:144-153；p<2 ⇒ 0.0）。"""
    p = matrix.shape[1]
    if p < 2:
        return 0.0
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.abs(np.corrcoef(matrix, rowvar=False))
    sel = corr[~np.eye(p, dtype=bool)]
    if np.all(np.isnan(sel)):
        return float("nan")
    return float(np.nanmean(sel))


def _skip(reason: str) -> Dict[str, Any]:
    return {"module_name": ORTH, "skipped": True, "reason": reason, "error_type": "INSUFFICIENT_DATA"}


def ref_factor_orthogonalizer(factors: pd.DataFrame, icir_scores: Mapping[str, Any], method: str = "gram_schmidt",
                              degenerate_threshold: float = DEGENERATE_THRESHOLD) -> Dict[str, Any]:
    """正交化摘要之獨立參考（不呼叫產品模組）。

    共同前處理（factor_orthogonalizer.py:30、:82）：數值化後剔除任一欄缺值之列。特徵 < 2 ⇒ 略過（:31-37、:84-90）。
    Gram–Schmidt：樣本 < 特徵 ⇒ 依 PCA 同規則略過（:91-97；產品 GS 缺此守門，見 xfail 測試）。
    """
    clean = factors.apply(pd.to_numeric, errors="coerce").dropna(axis=0, how="any")
    n, p = clean.shape
    if p < 2:
        return _skip("n_features < 2")
    if n < p:
        return _skip(f"n_samples({n}) < n_features({p})")
    if method == "pca":
        X = clean.to_numpy(dtype=float)
        k = max(1, min(n - 1, p))
        _, s, vt = np.linalg.svd(X - X.mean(axis=0), full_matrices=False)
        ev = s ** 2
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = ev / ev.sum()
        comps = vt[:k].copy()
        for j in range(k):
            comps[j] *= np.sign(comps[j, np.argmax(np.abs(comps[j]))]) or 1.0
        names = [f"PC{j + 1}" for j in range(k)]
        return {
            "method": "pca",
            "n_components": k,
            "explained_variance_ratio": [float(v) for v in ratio[:k]],
            "loadings": {c: {names[j]: float(comps[j, i]) for j in range(k)} for i, c in enumerate(clean.columns)},
            "principal_components": names,
        }
    order = _ref_priority_order(clean, icir_scores)
    X = clean[order].to_numpy(dtype=float)
    basis = np.zeros_like(X)
    feats_meta: Dict[str, Dict[str, Any]] = {}
    degenerate: List[str] = []
    for i, name in enumerate(order):
        y = X[:, i]
        r = y.copy() if i == 0 else sm.OLS(y, X[:, :i]).fit().resid
        rv = float(np.var(r))
        deg = bool(rv <= degenerate_threshold)
        nr = float(np.linalg.norm(r))
        if nr > 1e-8 * max(float(np.linalg.norm(y)), 1e-300):
            basis[:, i] = r / nr
        if deg:
            degenerate.append(name)
        feats_meta[name] = {"residual_variance": rv, "degenerate": deg}
    return {
        "method": "gram_schmidt",
        "priority_order": order,
        "correlation_before": _offdiag_abs_mean(X),
        "correlation_after": _offdiag_abs_mean(basis),
        "features": feats_meta,
        "degenerate_features": degenerate,
    }


def compare_factor_orthogonalizer(product_output: Any, factors: pd.DataFrame, icir_scores: Mapping[str, Any],
                                  method: str = "gram_schmidt",
                                  degenerate_threshold: float = DEGENERATE_THRESHOLD) -> Dict[str, Dict[str, Any]]:
    """產品 `results.factor_orthogonalization` vs oracle（輸入＝`_run_factor_orthogonalization` 之 features_df[selected]、
    `_ic_cache['icir']`、`config.factor_orthogonalization.method`）。退化殘差（兩者皆 ≤ 門檻）為數值零，不比相對誤差。
    PCA loadings 為單位向量之分量，以絕對誤差判。"""
    oracle = ref_factor_orthogonalizer(factors, icir_scores, method, degenerate_threshold)

    def _resid(_k: Tuple, p: float, o: float) -> float:
        if p <= degenerate_threshold and o <= degenerate_threshold:
            return 0.0
        return _rel(p, o)

    def _unit(_k: Tuple, p: float, o: float) -> float:
        return 0.0 if (math.isnan(p) and math.isnan(o)) else abs(p - o)

    return _compare(ORTH, product_output, oracle, list(factors.columns),
                    {"features/*/residual_variance": _resid, "loadings/*/PC#": _unit})


# ── 參考實作：factor_exposure_analyzer ─────────────────────────────────────────────────────────────────


def _ref_market_proxy(close_series: Optional[pd.Series], index: pd.Index) -> pd.Series:
    """收盤簡單報酬落後 1 根：m_t＝close[t−1]／close[t−2]−1（ic_filter_orchestrator.py:3109-3113；缺價 ⇒ NaN，不前補）。"""
    c = pd.to_numeric(close_series, errors="coerce").reindex(index)
    return (c / c.shift(1) - 1.0).shift(1)


def _ref_time_exposure(frame: pd.DataFrame, n_rows: int) -> Dict[str, float]:
    """factor_exposure_analyzer.py:176-184 與 ic_filter_orchestrator.py:3115-3117：Σ 有限值／列數（缺值當 0）。"""
    if frame.shape[1] == 0 or n_rows == 0:
        return {}
    w = 1.0 / max(1, n_rows)
    return {c: float(np.nansum(frame[c].to_numpy(dtype=float)) * w) for c in frame.columns}


def _ref_concentration(exposure: Mapping[str, float], threshold: float) -> Dict[str, Any]:
    """factor_exposure_analyzer.py:302-337。"""
    names = list(exposure)
    vals = np.array([exposure[n] for n in names], dtype=float)
    vals = np.where(np.isnan(vals), 0.0, vals)
    a = np.abs(vals)
    total = float(a.sum())
    if total == 0.0:
        return {"max_exposure_factor": None, "max_exposure_value": 0.0, "hhi": 0.0, "concentrated": False,
                "warnings": ["near_zero_exposures"]}
    share = a / total
    hhi = float(np.sum(share ** 2))
    i = int(np.nanargmax(share))
    mx = float(share[i])
    warnings: List[str] = []
    if mx > threshold:
        warnings.append("single_factor_exposure_too_high")
    if np.all(share < 0.05):
        warnings.append("near_zero_exposures")
    return {"max_exposure_factor": names[i], "max_exposure_value": mx, "hhi": hhi, "concentrated": bool(mx > threshold),
            "warnings": warnings}


def _ref_rolling_std(x: np.ndarray, window: int, min_periods: int) -> np.ndarray:
    """逐根 PIT 滾動標準差（只用 [t−window+1, t] 之非缺值，個數 ≥ min_periods 才算，ddof=1；同 pandas rolling 語意）。"""
    out = np.full(len(x), np.nan)
    for t in range(len(x)):
        w = x[max(0, t - window + 1): t + 1]
        w = w[~np.isnan(w)]
        if len(w) >= min_periods and len(w) >= 2:
            out[t] = float(np.std(w, ddof=1))
    return out


def _ref_neutralize(F: pd.DataFrame, proxy: pd.Series, mode: str, lookback: int) -> pd.DataFrame:
    """factor_exposure_analyzer.py:97-159 之定義；beta 依 OLS 定義取 x 與 m 之共同有效樣本。"""
    if F.empty:
        return pd.DataFrame()
    if mode == "beta_neutral":
        m = proxy.reindex(F.index)
        mv = m.to_numpy(dtype=float)
        fin = np.isfinite(mv)
        if fin.sum() < 10 or float(np.var(mv[fin])) == 0.0:      # :127-134（var 為 0 ⇒ 斜率無定義）
            return F.fillna(0.0)
        out = pd.DataFrame(index=F.index)
        for col in F.columns:
            x = F[col]
            al = pd.concat([x.rename("x"), m.rename("m")], axis=1).dropna()
            if len(al) < 10:                                        # :140-142
                out[col] = x
                continue
            fit = sm.OLS(al["x"].to_numpy(dtype=float), sm.add_constant(al["m"].to_numpy(dtype=float), has_constant="add")).fit()
            out[col] = x - float(fit.params[1]) * m
        return out.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if mode == "vol_neutral":
        window = max(5, int(lookback))
        minp = max(5, window // 3)                                  # :155-156
        out = pd.DataFrame(index=F.index)
        for col in F.columns:
            x = F[col].to_numpy(dtype=float)
            sd = _ref_rolling_std(x, window, minp)
            sd = np.where(sd == 0.0, np.nan, sd)                    # :157
            with np.errstate(invalid="ignore", divide="ignore"):
                out[col] = x / sd
        return out.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return F.fillna(0.0)                                            # none 與未知模式（:110-111、:118-119）


def ref_factor_exposure_analyzer(factors: pd.DataFrame, close_series: Optional[pd.Series],
                                 neutralization_mode: str = "none", neutralization_lookback: int = 63,
                                 max_single_exposure: float = 0.4) -> Dict[str, Any]:
    """曝險摘要之獨立參考（不呼叫產品模組）；非統計欄（設定回顯、寫死欄）照產品常數。"""
    F = factors.apply(pd.to_numeric, errors="coerce")
    n = len(F)
    proxy = _ref_market_proxy(close_series, F.index)
    exposure = _ref_time_exposure(F, n)
    neutral = _ref_neutralize(F, proxy, neutralization_mode, neutralization_lookback)
    n_exposure = _ref_time_exposure(neutral, n) if not neutral.empty else {}
    conc = _ref_concentration(exposure, max_single_exposure)
    n_conc = _ref_concentration(n_exposure, max_single_exposure)
    return {
        "portfolio_exposure": exposure,
        "concentration": conc,
        "neutralization_mode": neutralization_mode,
        "neutralization_lookback": int(neutralization_lookback),
        "neutralized_portfolio_exposure": n_exposure,
        "neutralized_concentration": n_conc,
        "neutralization_delta_hhi": float(conc["hhi"]) - float(n_conc["hhi"]),
        "proxy_kind": "trailing_close_ret",
        "proxy_lag": 1,
    }


def compare_factor_exposure_analyzer(product_output: Any, factors: pd.DataFrame, close_series: Optional[pd.Series],
                                     neutralization_mode: str = "none", neutralization_lookback: int = 63,
                                     max_single_exposure: float = 0.4) -> Dict[str, Dict[str, Any]]:
    """產品 `results.factor_exposure` vs oracle（輸入＝`_run_factor_exposure` 之 features_df[selected]、
    `_ic_cache['close_series']`、`config.factor_exposure` 三欄）。"""
    oracle = ref_factor_exposure_analyzer(factors, close_series, neutralization_mode, neutralization_lookback,
                                          max_single_exposure)
    return _compare(EXPO, product_output, oracle, list(factors.columns))


# ── 產品執行 ────────────────────────────────────────────────────────────────────────────────────────────


def _orchestrator(feats: pd.DataFrame, close: Optional[pd.Series], icir: Optional[Mapping[str, Any]]) -> ICFilterOrchestrator:
    """`_ic_cache` 同 ic_filter_orchestrator.py:4829-4840 之形狀（只填兩模組讀取之鍵與 run_deep_analysis 必需鍵）。"""
    orch = ICFilterOrchestrator(ICConfig())
    orch._ic_cache = {"features_df": feats, "label_series": None, "close_series": close, "metadata": {},
                      "icir": {} if icir is None else dict(icir), "rolling_ic": {}, "ic_decay": {}, "grouped_ic": {},
                      "event_info": {}, "stage0_log": {}, "preproc_log": {}}
    orch._filtered_features_df = None
    return orch


def _run_product(module: str, feats: pd.DataFrame, *, close: Optional[pd.Series] = None,
                 icir: Optional[Mapping[str, Any]] = None, **cfg: Any) -> Dict[str, Any]:
    """經 `run_deep_analysis(force_modules=[module])` 執行產品（含例外 envelope），回 `asdict` 後之 `results[module]`。"""
    orch = _orchestrator(feats, close, icir)
    if feats.shape[1] == 0:
        config = orch._apply_tier_config(orch._apply_config_override({module: {"enabled": True, **cfg}}))
        runner = orch._run_factor_orthogonalization if module == ORTH else orch._run_factor_exposure
        return asdict_results(runner([], config))
    report = orch.run_deep_analysis(selected_features=list(feats.columns),
                                    config_override={module: {"enabled": True, **cfg}}, force_modules=[module])
    return asdict(report)["results"][module]


def asdict_results(result: Mapping[str, Any]) -> Dict[str, Any]:
    return {k: _to_plain(v) for k, v in result.items()}


def _all_consistent(res: Mapping[str, Mapping[str, Any]]) -> List[str]:
    return [f"{p}: {r['detail']}" for p, r in res.items() if r["verdict"] != "一致"]


def _branch(res: Mapping[str, Mapping[str, Any]], branch: str) -> Dict[str, Mapping[str, Any]]:
    """比對結果中屬某分支之統計欄（GS 與 PCA 欄互為「雙方皆無值」，計有限值時只看本分支）。"""
    return {p: r for p, r in res.items() if p in BRANCH_FIELDS[branch]}


# ── 明列輸入（秒級） ────────────────────────────────────────────────────────────────────────────────────


def _idx(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")


def _explicit_factors(n: int = 240, seed: int = 7) -> pd.DataFrame:
    """四欄明列輸入：相關結構不同、尺度不同、首段缺值（暖機）與中段缺值各一。"""
    rng = np.random.default_rng(seed)
    a = rng.normal(0.0, 1.0, n)
    b = 0.6 * a + rng.normal(0.0, 0.8, n)
    c = rng.normal(2.0, 0.5, n)            # 非零均值
    d = 0.01 * rng.normal(0.0, 1.0, n)     # 小尺度
    df = pd.DataFrame({"a": a, "b": b, "c": c, "d": d}, index=_idx(n))
    df.iloc[:15, 1] = np.nan
    df.iloc[100:104, 3] = np.nan
    return df


def _explicit_close(n: int = 240, seed: int = 11, vol: float = 0.01) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(100.0 * np.cumprod(1.0 + vol * rng.normal(0.0, 1.0, n)), index=_idx(n), name="close")


def _production_icir(icir_values: Mapping[str, float]) -> Dict[str, Dict[str, float]]:
    """`_ic_cache['icir']` 之實際形狀（ic_engine.py:488-493：逐特徵 {ic_mean, ic_std, icir, ic_hit_rate}）。"""
    return {k: {"ic_mean": 0.01 * v, "ic_std": 0.01, "icir": float(v), "ic_hit_rate": 0.5} for k, v in icir_values.items()}


# ── 秒級：欄位清冊 ──────────────────────────────────────────────────────────────────────────────────────


def test_module_fields_well_formed() -> None:
    """每欄皆有 oracle 與 producer；統計欄之 oracle id 皆在 ORACLES；每一統計 oracle 至少被一欄引用。"""
    assert MODULE_FIELDS, "清冊為空"
    used = set()
    for path, spec in MODULE_FIELDS.items():
        assert path.split("/")[0] in (ORTH, EXPO), path
        assert set(spec) == {"oracle", "producer"} and spec["producer"], path
        if spec["oracle"] != NON_STAT:
            assert spec["oracle"] in ORACLES, f"{path}: 未知 oracle {spec['oracle']}"
            used.add(spec["oracle"])
    assert used == set(ORACLES), f"未被引用之 oracle：{set(ORACLES) - used}"


# ── 秒級：Gram–Schmidt ──────────────────────────────────────────────────────────────────────────────────


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_gram_schmidt_proxy_order_matches_oracle() -> None:
    """icir 快取為空（`_ic_cache.get('icir', {})` 之 {}）⇒ |均值| 降序；含缺值列（同列剔除）、非零均值欄、小尺度欄。"""
    feats = _explicit_factors()
    out = _run_product(ORTH, feats, icir={}, method="gram_schmidt")
    res = compare_factor_orthogonalizer(out, feats, {}, "gram_schmidt")
    assert not _all_consistent(res), _all_consistent(res)
    assert out["transformed_shape"] == [int(feats.dropna().shape[0]), 4]
    gs = _branch(res, "orth_gram_schmidt")
    assert len(gs) == 18 and all(r["n_finite"] > 0 for p, r in gs.items() if not p.endswith("degenerate_features/#")), gs


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("scores,expect_icir_order", [
    ({"a": 0.1, "b": 0.9, "c": -0.5, "d": 0.3}, True),
    ({"a": 0.1, "b": float("nan"), "c": -0.5, "d": 0.3}, False),   # 含 NaN ⇒ 退回 |均值|（:138）
    ({"a": 0.1, "c": -0.5, "d": 0.3}, False),                      # 缺鍵 ⇒ 退回（:138 get→nan）
])
def test_gram_schmidt_float_icir_order_matches_oracle(scores: Dict[str, float], expect_icir_order: bool) -> None:
    """icir 值為裸浮點（舊測試 test_la2_lookahead.py:1400 所用形狀）⇒ 依 ICIR 有號降序；非全有限 ⇒ 退回 |均值|。"""
    feats = _explicit_factors()
    out = _run_product(ORTH, feats, icir=scores, method="gram_schmidt")
    res = compare_factor_orthogonalizer(out, feats, scores, "gram_schmidt")
    assert not _all_consistent(res), _all_consistent(res)
    order = out["priority_order"]
    assert (order == ["b", "d", "a", "c"]) is expect_icir_order


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_gram_schmidt_constant_column_matches_oracle() -> None:
    """常數欄：殘差變異 0 ⇒ degenerate（np.var，非向量範數）；其 |corr| 為 NaN 而 nanmean 略過。"""
    feats = _constant_column_factors()
    out = _run_product(ORTH, feats, icir={}, method="gram_schmidt")
    res = compare_factor_orthogonalizer(out, feats, {}, "gram_schmidt")
    bad = [b for b in _all_consistent(res) if "correlation_after" not in b]
    assert not bad, bad
    assert out["degenerate_features"] == ["k"]


def _constant_column_factors() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    return pd.DataFrame({"k": np.full(60, 5.0), "u": rng.normal(size=60), "v": rng.normal(size=60)}, index=_idx(60))


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：常數欄之正交基欄於數學上為常數，QR 捨入使其帶 1e-17 級雜訊，"
                                       f"pandas corr 對雜訊回非 NaN 之相關並計入 correlation_after（factor_orthogonalizer.py:43-44、:66）；"
                                       f"收據 {RECEIPT}")
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_gram_schmidt_constant_column_correlation_after() -> None:
    """常數欄 k 排第一（|均值| 最大）⇒ 其正交基為常數向量，相關無定義（NaN，nanmean 略過）；u、v 之正交基相關 ≈ 0。"""
    feats = _constant_column_factors()
    out = _run_product(ORTH, feats, icir={}, method="gram_schmidt")
    res = compare_factor_orthogonalizer(out, feats, {}, "gram_schmidt")
    assert not _all_consistent(res), _all_consistent(res)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_gram_schmidt_degenerate_flag_matches_oracle() -> None:
    """完全共線欄（b＝2a）：退化旗標與退化名單、退化欄之前與退化欄本身之殘差變異 == oracle（其後各欄見下列 xfail）。"""
    rng = np.random.default_rng(5)
    a = rng.normal(size=300)
    feats = pd.DataFrame({"a": a, "b": 2.0 * a, "c": rng.normal(size=300), "d": rng.normal(size=300)}, index=_idx(300))
    scores = {"a": 0.4, "b": 0.3, "c": 0.2, "d": 0.1}
    out = _run_product(ORTH, feats, icir=scores, method="gram_schmidt")
    res = compare_factor_orthogonalizer(out, feats, scores, "gram_schmidt")
    for pre in _SUMMARY_COPIES:
        for f in ("priority_order/#", "features/*/degenerate", "degenerate_features/#", "correlation_before"):
            assert res[f"{ORTH}/{pre}{f}"]["verdict"] == "一致", res[f"{ORTH}/{pre}{f}"]
    assert out["degenerate_features"] == ["b"]
    exp = ref_factor_orthogonalizer(feats, scores)
    for f in ("a", "b"):
        rv = out["features"][f]["residual_variance"]
        assert rv == pytest.approx(exp["features"][f]["residual_variance"], rel=1e-12, abs=DEGENERATE_THRESHOLD)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_degenerate_threshold_is_absolute_variance() -> None:
    """方法論證據（非公式不一致）：門檻為絕對變異 1e-10（factor_orthogonalizer.py:22、:57），小尺度但獨立之特徵被標退化。"""
    rng = np.random.default_rng(9)
    feats = pd.DataFrame({"big": rng.normal(size=200), "tiny": 1e-6 * rng.normal(size=200)}, index=_idx(200))
    out = _run_product(ORTH, feats, icir={}, method="gram_schmidt")
    res = compare_factor_orthogonalizer(out, feats, {}, "gram_schmidt")
    assert not _all_consistent(res), _all_consistent(res)
    assert out["degenerate_features"] == ["tiny"]
    assert abs(float(np.corrcoef(feats["big"], feats["tiny"])[0, 1])) < 0.2, "前提：兩欄近乎獨立"


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("method", ["gram_schmidt", "pca"])
@pytest.mark.parametrize("cols", [[], ["a"]])
def test_orthogonalization_skips_below_two_features(method: str, cols: List[str]) -> None:
    """空與單特徵 ⇒ 略過 INSUFFICIENT_DATA（factor_orthogonalizer.py:31-37、:84-90）；統計欄雙方皆無值。"""
    feats = _explicit_factors()[cols]
    out = _run_product(ORTH, feats, icir={}, method=method)
    exp = ref_factor_orthogonalizer(feats, {}, method)
    for k in ("module_name", "skipped", "reason", "error_type"):
        assert out[k] == exp[k]
    assert out["transformed_shape"] == [int(len(feats.dropna())) if cols else len(feats), 0]
    res = compare_factor_orthogonalizer(out, feats, {}, method)
    assert not _all_consistent(res) and all(r["n_finite"] == 0 for r in res.values())


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：Gram–Schmidt 以 float(icir_scores[name]) 取排序鍵，而 "
                                       f"_ic_cache['icir'] 之值為 dict（ic_engine.py:488-493）⇒ TypeError，產品恆回 skipped；收據 {RECEIPT}")
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_gram_schmidt_accepts_production_icir_cache_shape() -> None:
    """`_run_factor_orthogonalization` 傳入之 icir_scores＝`_ic_cache['icir']`（ic_filter_orchestrator.py:3053、:4834），
    其值為 {ic_mean, ic_std, icir, ic_hit_rate}；正確行為＝依 ICIR 排序並輸出 oracle 之全部統計欄。"""
    feats = _explicit_factors()
    icir = _production_icir({"a": 0.1, "b": 0.9, "c": -0.5, "d": 0.3})
    out = _run_product(ORTH, feats, icir=icir, method="gram_schmidt")
    res = compare_factor_orthogonalizer(out, feats, icir, "gram_schmidt")
    assert not _all_consistent(res), _all_consistent(res)


def test_gram_schmidt_production_icir_shape_currently_errors() -> None:
    """（現況紀錄，供收據）同上輸入之產品輸出＝run_deep_analysis 例外 envelope（ic_filter_orchestrator.py:2795-2809）。"""
    feats = _explicit_factors()
    out = _run_product(ORTH, feats, icir=_production_icir({"a": 0.1, "b": 0.9, "c": -0.5, "d": 0.3}), method="gram_schmidt")
    assert set(out) == {"skipped", "reason", "error_type"}
    assert out["skipped"] is True and out["error_type"] == "INTERNAL_ERROR" and "dict" in out["reason"]


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：完全共線欄之 QR 正交基欄為捨入雜訊方向，其後各欄再對其投影，"
                                       f"殘差變異與 correlation_after 偏離 OLS 定義（factor_orthogonalizer.py:43、:53-55）；收據 {RECEIPT}")
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_gram_schmidt_residuals_after_degenerate_feature_match_ols() -> None:
    """b＝2a 排第二 ⇒ c、d 之殘差應等於對 [a, b] 之 OLS 殘差（statsmodels pinv）；產品對雜訊方向多投影一次。"""
    rng = np.random.default_rng(5)
    a = rng.normal(size=300)
    feats = pd.DataFrame({"a": a, "b": 2.0 * a, "c": rng.normal(size=300), "d": rng.normal(size=300)}, index=_idx(300))
    scores = {"a": 0.4, "b": 0.3, "c": 0.2, "d": 0.1}
    out = _run_product(ORTH, feats, icir=scores, method="gram_schmidt")
    res = compare_factor_orthogonalizer(out, feats, scores, "gram_schmidt")
    assert not _all_consistent(res), _all_consistent(res)


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：Gram–Schmidt 缺「樣本 < 特徵」守門（PCA 有，"
                                       f"factor_orthogonalizer.py:91-97），QR 經濟形狀與欄名不符 ⇒ ValueError／LAPACK 錯，報 INTERNAL_ERROR"
                                       f"而非 INSUFFICIENT_DATA；收據 {RECEIPT}")
@pytest.mark.parametrize("n_rows", [0, 3])
def test_gram_schmidt_fewer_samples_than_features_skips_like_pca(n_rows: int) -> None:
    """同列剔除後樣本 < 特徵（含 0 列；寬請求同列剔除常致此）⇒ 應同 PCA 回 INSUFFICIENT_DATA 略過。"""
    feats = _explicit_factors(n=40).iloc[15:15 + n_rows]
    out = _run_product(ORTH, feats, icir={}, method="gram_schmidt")
    exp = ref_factor_orthogonalizer(feats, {}, "gram_schmidt")
    assert out.get("error_type") == "INSUFFICIENT_DATA" and out.get("reason") == exp["reason"], out


# ── 秒級：PCA ────────────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("n_rows", [240, 4, 3])
def test_pca_matches_oracle(n_rows: int) -> None:
    """PCA（sklearn，去均值、不標準化）：一般、樣本＝特徵（成分＝n−1，:99）、樣本 < 特徵（略過，:91-97）。"""
    feats = _explicit_factors().iloc[15:].iloc[:n_rows] if n_rows < 240 else _explicit_factors()
    feats = feats.drop(feats.index[(feats.index >= feats.index[0] + pd.Timedelta(hours=85))
                                   & (feats.index < feats.index[0] + pd.Timedelta(hours=89))]) if n_rows == 240 else feats
    out = _run_product(ORTH, feats, icir={}, method="pca")
    res = compare_factor_orthogonalizer(out, feats, {}, "pca")
    assert not _all_consistent(res), _all_consistent(res)
    exp = ref_factor_orthogonalizer(feats, {}, "pca")
    if n_rows >= 4:
        assert out["n_components"] == exp["n_components"] == min(len(feats.dropna()) - 1, 4)
        assert out["principal_components"] == exp["principal_components"]
        pca = _branch(res, "orth_pca")
        assert len(pca) == 6 and all(r["n_finite"] > 0 for r in pca.values()), pca
    else:
        assert out["error_type"] == exp["error_type"] == "INSUFFICIENT_DATA" and out["reason"] == exp["reason"]


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_pca_all_constant_ratio_nan() -> None:
    """全常數輸入：總變異 0 ⇒ explained_variance_ratio 全 NaN（0/0）；loadings 任一正交基皆合定義，不比。"""
    feats = pd.DataFrame({"a": np.full(10, 1.0), "b": np.full(10, 5.0)}, index=_idx(10))
    out = _run_product(ORTH, feats, icir={}, method="pca")
    exp = ref_factor_orthogonalizer(feats, {}, "pca")
    assert out["n_components"] == exp["n_components"] == 2
    assert all(math.isnan(v) for v in out["explained_variance_ratio"]) and all(math.isnan(v) for v in exp["explained_variance_ratio"])


# ── 秒級：曝險 ───────────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("mode", ["none", "vol_neutral"])
@pytest.mark.parametrize("lookback", [5, 63])
def test_exposure_matches_oracle(mode: str, lookback: int) -> None:
    """none（預設）與 vol_neutral（逐根 PIT 滾動標準差，窗 max(5, lookback)、最少 max(5, 窗//3)）；含暖機與中段缺值。"""
    feats = _explicit_factors()
    close = _explicit_close()
    out = _run_product(EXPO, feats, close=close, neutralization_mode=mode, neutralization_lookback=lookback)
    res = compare_factor_exposure_analyzer(out, feats, close, mode, lookback, 0.4)
    assert not _all_consistent(res), _all_consistent(res)
    assert all(r["n_finite"] > 0 for p, r in res.items() if not p.endswith("warnings/#")), res


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_exposure_beta_neutral_matches_oracle_on_common_sample() -> None:
    """beta_neutral：特徵缺值列 ⊆ 代理缺值列（首 2 根）⇒ 產品 cov／var 與 OLS 斜率同樣本，須一致；另含一欄共同樣本 < 10 ⇒ 保留原值（:140-142）。"""
    n = 240
    close = _explicit_close(n)
    proxy = close.pct_change().shift(1)
    rng = np.random.default_rng(13)
    sparse = pd.Series(np.nan, index=_idx(n))
    sparse.iloc[50:58] = rng.normal(size=8)
    feats = pd.DataFrame({"x": 2.0 * proxy + 0.01 * rng.normal(size=n), "y": -proxy.fillna(0.0) + 0.02,
                          "s": sparse}, index=_idx(n))
    feats.iloc[:2, 0] = np.nan
    out = _run_product(EXPO, feats, close=close, neutralization_mode="beta_neutral")
    res = compare_factor_exposure_analyzer(out, feats, close, "beta_neutral", 63, 0.4)
    assert not _all_consistent(res), _all_consistent(res)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("case", ["proxy_lt_10", "flat_close"])
def test_exposure_beta_neutral_skip_branches(case: str) -> None:
    """代理有限值 < 10（:127-129）與代理變異為 0（收盤不變，:131-134）⇒ 不中和（缺值當 0）。"""
    n = 60 if case == "flat_close" else 11
    close = pd.Series(100.0, index=_idx(n)) if case == "flat_close" else _explicit_close(n)
    feats = _explicit_factors(n)
    out = _run_product(EXPO, feats, close=close, neutralization_mode="beta_neutral")
    res = compare_factor_exposure_analyzer(out, feats, close, "beta_neutral", 63, 0.4)
    assert not _all_consistent(res), _all_consistent(res)
    assert out["neutralized_portfolio_exposure"] == out["portfolio_exposure"]


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("case", ["empty", "all_zero", "many_features", "below_threshold"])
def test_exposure_concentration_branches(case: str) -> None:
    """集中度分支：無特徵（空 dict）、曝險全 0（:310-317）、≥21 欄均分 ⇒ near_zero 警告（:328）、最大占比 ≤ 門檻（不警告）。"""
    n = 50
    close = _explicit_close(n)
    rng = np.random.default_rng(17)
    if case == "empty":
        feats = pd.DataFrame(index=_idx(n))
    elif case == "all_zero":
        feats = pd.DataFrame({"a": np.zeros(n), "b": np.full(n, np.nan)}, index=_idx(n))
    elif case == "many_features":
        feats = pd.DataFrame({f"f{i}": 1.0 + 0.001 * rng.normal(size=n) for i in range(25)}, index=_idx(n))
    else:
        feats = pd.DataFrame({"a": np.full(n, 1.0), "b": np.full(n, -1.0), "c": np.full(n, 0.9)}, index=_idx(n))
    out = _run_product(EXPO, feats, close=close)
    res = compare_factor_exposure_analyzer(out, feats, close, "none", 63, 0.4)
    assert not _all_consistent(res), _all_consistent(res)
    exp_warn = {"empty": ["near_zero_exposures"], "all_zero": ["near_zero_exposures"],
                "many_features": ["near_zero_exposures"], "below_threshold": []}[case]
    assert out["concentration"]["warnings"] == exp_warn


def test_exposure_without_close_carrier_errors() -> None:
    """無 close carrier ⇒ InvalidInputError（ic_filter_orchestrator.py:3103-3108）⇒ runner 例外 envelope。"""
    feats = _explicit_factors()
    out = _run_product(EXPO, feats, close=None)
    assert set(out) == {"skipped", "reason", "error_type"} and out["skipped"] is True


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：beta 分子 cov 取特徵與代理共同樣本、分母 var 取代理全部有限樣本"
                                       f"（factor_exposure_analyzer.py:131、:139-145），兩者樣本不同時 beta ≠ OLS 斜率；收據 {RECEIPT}")
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_exposure_beta_uses_common_sample() -> None:
    """特徵首 40 根缺值（暖機）而代理只缺首 2 根，且代理前段波動較大 ⇒ 正確 beta＝共同樣本之 OLS 斜率。"""
    n = 240
    rng = np.random.default_rng(19)
    vol = np.where(np.arange(n) < 40, 0.03, 0.01)
    close = pd.Series(100.0 * np.cumprod(1.0 + vol * rng.normal(size=n)), index=_idx(n))
    proxy = close.pct_change().shift(1)
    x = 1.5 * proxy + 0.005 * rng.normal(size=n)
    x.iloc[:40] = np.nan
    feats = pd.DataFrame({"x": x, "z": rng.normal(size=n)}, index=_idx(n))
    out = _run_product(EXPO, feats, close=close, neutralization_mode="beta_neutral")
    res = compare_factor_exposure_analyzer(out, feats, close, "beta_neutral", 63, 0.4)
    assert not _all_consistent(res), _all_consistent(res)


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：代理變異以 np.isclose(var, 0)（絕對容差 1e-8）判近零，"
                                       f"報酬標準差 < 1e-4 之低波動標的 beta 中和被靜默跳過（factor_exposure_analyzer.py:132、:145）；收據 {RECEIPT}")
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_exposure_beta_neutral_low_volatility_proxy() -> None:
    """代理報酬標準差 5e-5（變異 2.5e-9 > 0）⇒ OLS 斜率有定義，應中和。"""
    n = 240
    close = _explicit_close(n, vol=5e-5)
    proxy = close.pct_change().shift(1)
    rng = np.random.default_rng(23)
    feats = pd.DataFrame({"x": 3.0 * proxy + 1e-5 * rng.normal(size=n), "z": rng.normal(1.0, 0.1, size=n)}, index=_idx(n))
    feats.iloc[:2, 0] = np.nan
    assert 0.0 < float(np.nanvar(proxy.to_numpy())) < 1e-8, "前提：代理變異落於 (0, 1e-8)"
    out = _run_product(EXPO, feats, close=close, neutralization_mode="beta_neutral")
    res = compare_factor_exposure_analyzer(out, feats, close, "beta_neutral", 63, 0.4)
    assert not _all_consistent(res), _all_consistent(res)


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：市場代理以 pct_change() 預設 fill_method='pad' 前補缺價，"
                                       f"缺價根之報酬被造為 0、其後一根為跨兩根報酬（ic_filter_orchestrator.py:3113）；收據 {RECEIPT}")
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.filterwarnings("ignore::FutureWarning")
def test_exposure_market_proxy_does_not_fabricate_returns_over_missing_close() -> None:
    """close carrier 中段缺價（特徵無缺值，排除共同樣本問題）⇒ 缺價相鄰之代理應為 NaN，不得為 0。"""
    n = 240
    close = _explicit_close(n)
    proxy_true = (close / close.shift(1) - 1.0).shift(1)
    rng = np.random.default_rng(29)
    feats = pd.DataFrame({"x": (2.0 * proxy_true).fillna(0.0) + 0.01 * rng.normal(size=n),
                          "z": rng.normal(size=n)}, index=_idx(n))
    close_gap = close.copy()
    close_gap.iloc[120:123] = np.nan
    out = _run_product(EXPO, feats, close=close_gap, neutralization_mode="beta_neutral")
    res = compare_factor_exposure_analyzer(out, feats, close_gap, "beta_neutral", 63, 0.4)
    assert not _all_consistent(res), _all_consistent(res)


# ── 秒級：比對器自證（改壞會 FAIL） ────────────────────────────────────────────────────────────────────


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_compare_detects_perturbation() -> None:
    """改動產品輸出任一統計值（相對 1e-9）或名單 ⇒ 該欄判「不一致」，其餘仍「一致」。"""
    feats = _explicit_factors()
    out = _run_product(ORTH, feats, icir={}, method="gram_schmidt")
    out["correlation_before"] *= 1.0 + 1e-9
    out["payload"]["summary"]["priority_order"] = list(reversed(out["payload"]["summary"]["priority_order"]))
    res = compare_factor_orthogonalizer(out, feats, {}, "gram_schmidt")
    bad = {p for p, r in res.items() if r["verdict"] != "一致"}
    assert bad == {f"{ORTH}/correlation_before", f"{ORTH}/payload/summary/priority_order/#"}, bad
    close = _explicit_close()
    eo = _run_product(EXPO, feats, close=close)
    eo["typed_result"]["payload"]["summary"]["portfolio_exposure"]["c"] *= 1.0 + 1e-9
    eo["neutralized_concentration"]["concentrated"] = not eo["neutralized_concentration"]["concentrated"]
    res = compare_factor_exposure_analyzer(eo, feats, close)
    bad = {p for p, r in res.items() if r["verdict"] != "一致"}
    assert bad == {f"{EXPO}/typed_result/payload/summary/portfolio_exposure/*",
                   f"{EXPO}/neutralized_concentration/concentrated"}, bad


# ── 真實 kline（requires_kline） ─────────────────────────────────────────────────────────────────────────


def _real_close(rows: int = REAL_ROWS, symbol: str = "BTCUSDT") -> pd.Series:
    import h5py

    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        data = f[f"{symbol}/1h/data"][-rows:]
    idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True)
    return pd.Series(data["close"].astype("float64"), index=idx, name="close")


def _real_features(close: pd.Series) -> pd.DataFrame:
    """真實 kline 上之因果特徵（只用 0..t）：1 根報酬、20 根均線偏離、20 根報酬波動率、10 根動量（暖機長度各異）。"""
    ret = close.pct_change()
    return pd.DataFrame({"ret1": ret, "dev20": close / close.rolling(20).mean() - 1.0, "vol20": ret.rolling(20).std(),
                         "mom10": close / close.shift(10) - 1.0})


def _real_label(close: pd.Series, horizon: int = 1) -> pd.Series:
    """前瞻報酬標籤 close[t+h]／close[t]−1（label_generator.py:45-47；只供產品產生 icir 快取）。"""
    return (close.shift(-horizon) / close - 1.0).rename("label")


def _real_production_icir(feats: pd.DataFrame, close: pd.Series) -> Dict[str, Dict[str, float]]:
    """以產品產生器得 `_ic_cache['icir']`（ic_engine.py compute_rolling_ic → compute_icir，同 ic_filter_orchestrator.py:4343）。"""
    eng = ICEngine({})
    return eng.compute_icir(eng.compute_rolling_ic(feats, _real_label(close), [63]))


def _real_scenarios() -> Dict[str, Tuple[str, Dict[str, Any], Dict[str, Dict[str, Any]], Optional[Set[str]]]]:
    """真實資料情境 → (模組, 產品輸出, 比對結果, 應一致之相對欄位集合〔None＝全部〕)。"""
    close = _real_close()
    feats = _real_features(close)
    out: Dict[str, Tuple[str, Dict[str, Any], Dict[str, Dict[str, Any]], Optional[Set[str]]]] = {}
    o = _run_product(ORTH, feats, icir={}, method="gram_schmidt")
    out["gs_proxy_order"] = (ORTH, o, compare_factor_orthogonalizer(o, feats, {}, "gram_schmidt"), None)
    icir_float = {k: v["icir"] for k, v in _real_production_icir(feats, close).items()}
    o = _run_product(ORTH, feats, icir=icir_float, method="gram_schmidt")
    out["gs_float_icir"] = (ORTH, o, compare_factor_orthogonalizer(o, feats, icir_float, "gram_schmidt"), None)
    o = _run_product(ORTH, feats, icir={}, method="pca")
    out["pca"] = (ORTH, o, compare_factor_orthogonalizer(o, feats, {}, "pca"), None)
    dup = feats.assign(mom10_pct=100.0 * feats["mom10"])
    o = _run_product(ORTH, dup, icir={}, method="gram_schmidt")
    out["gs_degenerate"] = (ORTH, o, compare_factor_orthogonalizer(o, dup, {}, "gram_schmidt"),
                            {"priority_order/#", "features/*/degenerate", "degenerate_features/#", "correlation_before"})
    for mode in ("none", "vol_neutral"):
        o = _run_product(EXPO, feats, close=close, neutralization_mode=mode)
        out[f"exposure_{mode}"] = (EXPO, o, compare_factor_exposure_analyzer(o, feats, close, mode, 63, 0.4), None)
    common = pd.DataFrame({"ret1": feats["ret1"], "ret2": close / close.shift(2) - 1.0})
    o = _run_product(EXPO, common, close=close, neutralization_mode="beta_neutral")
    out["exposure_beta_common"] = (EXPO, o, compare_factor_exposure_analyzer(o, common, close, "beta_neutral", 63, 0.4), None)
    return out


def _rel_field(path: str) -> str:
    wild = tuple(path.split("/")[1:])
    return "/".join(wild[_strip_prefix(wild):])


@pytest.fixture(scope="module")
def real_scenarios() -> Dict[str, Tuple[str, Dict[str, Any], Dict[str, Dict[str, Any]], Optional[Set[str]]]]:
    return _real_scenarios()


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_orth_exposure_fields_closed() -> None:
    """真實 BTCUSDT 1h 末 400 根：逐分支執行產品，實際鍵集合 == BRANCH_FIELDS 該分支；各分支聯集 == MODULE_FIELDS。"""
    close = _real_close(400)
    feats = _real_features(close)
    runs = {
        "orth_gram_schmidt": (ORTH, _run_product(ORTH, feats, icir={}, method="gram_schmidt"), feats),
        "orth_pca": (ORTH, _run_product(ORTH, feats, icir={}, method="pca"), feats),
        "orth_skipped": (ORTH, _run_product(ORTH, feats[["ret1"]], icir={}, method="gram_schmidt"), feats[["ret1"]]),
        "orth_runner_error": (ORTH, _run_product(ORTH, feats, icir=_real_production_icir(feats, close), method="gram_schmidt"), feats),
        "exposure_ok": (EXPO, _run_product(EXPO, feats, close=close), feats),
        "exposure_runner_error": (EXPO, _run_product(EXPO, feats, close=None), feats),
    }
    assert set(runs) == set(BRANCH_FIELDS)
    union: Set[str] = set()
    for branch, (module, output, f) in runs.items():
        got = _field_keys(module, output, list(f.columns))
        assert got == set(BRANCH_FIELDS[branch]), (branch, sorted(got ^ set(BRANCH_FIELDS[branch])))
        union |= got
    assert union == set(MODULE_FIELDS)


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_orth_exposure_match_oracle_on_real_kline(real_scenarios) -> None:
    """真實 BTCUSDT 1h 2,000 根：各情境之統計欄 == oracle（gs_degenerate 只驗退化旗標與名單等，其後殘差見 xfail）。"""
    bad = []
    for name, (_m, _o, res, subset) in real_scenarios.items():
        for path, r in res.items():
            if (subset is None or _rel_field(path) in subset) and r["verdict"] != "一致":
                bad.append(f"{name} {path}: {r['detail']}")
    assert not bad, bad
    assert real_scenarios["gs_degenerate"][1]["degenerate_features"] == ["mom10"]


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_every_stat_field_verified_finite_on_real_kline(real_scenarios) -> None:
    """SPEC v5.26 資料充足判準：MODULE_FIELDS 每一統計欄於真實資料至少一情境「一致」且有限值數 ≥ 1。"""
    verified: Set[str] = set()
    for _name, (_m, _o, res, subset) in real_scenarios.items():
        for path, r in res.items():
            if (subset is None or _rel_field(path) in subset) and r["verdict"] == "一致" and r["n_finite"] >= 1:
                verified.add(path)
    stat = {p for p, s in MODULE_FIELDS.items() if s["oracle"] != NON_STAT}
    assert stat - verified == set(), sorted(stat - verified)


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：Gram–Schmidt 以 float() 讀 dict 形之 _ic_cache['icir'] ⇒ TypeError，"
                                       f"真實請求恆 skipped；收據 {RECEIPT}")
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_gram_schmidt_production_icir_on_real_kline() -> None:
    """真實 BTCUSDT 1h 2,000 根，icir 快取由產品 compute_rolling_ic → compute_icir 產生 ⇒ 正確行為＝全部統計欄 == oracle。"""
    close = _real_close()
    feats = _real_features(close)
    icir = _real_production_icir(feats, close)
    out = _run_product(ORTH, feats, icir=icir, method="gram_schmidt")
    res = compare_factor_orthogonalizer(out, feats, icir, "gram_schmidt")
    assert not _all_consistent(res), _all_consistent(res)


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：完全共線欄（mom10 與其百分比）之後，各欄殘差變異與 correlation_after "
                                       f"含對雜訊方向之投影（factor_orthogonalizer.py:43、:53-55）；收據 {RECEIPT}")
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_gram_schmidt_residuals_after_degenerate_on_real_kline(real_scenarios) -> None:
    """真實 BTCUSDT 1h：特徵加 mom10_pct＝100·mom10（同指標不同單位）⇒ 退化欄之後各欄殘差應 == OLS。"""
    res = real_scenarios["gs_degenerate"][2]
    assert not _all_consistent(res), _all_consistent(res)


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：beta 分子分母樣本不同（factor_exposure_analyzer.py:131、:139-145），"
                                       f"真實資料上 dev20／vol20／mom10 之 beta 偏離 OLS 斜率約 3%；收據 {RECEIPT}")
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_exposure_beta_neutral_on_real_kline() -> None:
    """真實 BTCUSDT 1h 2,000 根，四特徵暖機長度各異（1／19／20／10 根）而代理缺首 2 根 ⇒ beta 須為共同樣本 OLS 斜率。"""
    close = _real_close()
    feats = _real_features(close)
    out = _run_product(EXPO, feats, close=close, neutralization_mode="beta_neutral")
    res = compare_factor_exposure_analyzer(out, feats, close, "beta_neutral", 63, 0.4)
    assert not _all_consistent(res), _all_consistent(res)
