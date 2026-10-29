"""ICPERF Task 0.3 — 深度分析 factor_centrality／trend_analysis 之獨立 oracle 對照（組名 centrality_trend；
docs/ICPERF_SPEC.md Task 0.3 第 108、109 行深度分析涵蓋與資料充足判準、第 127 行讀碼盤點；派工 brief
handoffs/20261029-ICPERF-T03-DEEP-ORACLE-BRIEF.md）。

被測：`momentum/Analysis/factor_centrality_analyzer.py`（呼叫端 `ic_filter_orchestrator.py` `_run_factor_centrality`
:2984-3008）與 `momentum/Analysis/trend_analyzer.py`（`_run_trend_analysis` :3010-3022）；兩者吃滾動 IC 序列，經
`_extract_rolling_ic_series`（:3363-3372）取每特徵最長之窗。本檔為**稽核**：oracle＝`numpy.linalg.eigh`（PCA）、
`scipy.stats`（rankdata／linregress／pearsonr／spearmanr）、`statsmodels.api.OLS`（含 HAC）與測試自寫之最簡參考實作
（`ref_*`，逐條註明產品 `檔:行`）；不呼叫被測模組或其內部函式當 oracle。不一致項標 `xfail(strict=True)`，不修產品碼。

輸入：秒級測試以明列輸入（邊界案）直接餵產品公開入口（`ICFilterOrchestrator._run_factor_centrality`／
`_run_trend_analysis`，以只帶 `_ic_cache["rolling_ic"]` 之 stub 呼叫）；真實資料測試以
`data_cache/feature_klines/kline_cache.h5` 之真實 1h kline 建因果特徵與前瞻 1 根簡單報酬標籤，**先剔除任一欄非有限之列**
再交 `ICEngine.compute_rolling_ic` 建滾動 IC（故不依賴 SPEC Task 0.4 ④ 之跨特徵聯合 dropna 錯誤：輸入已全有限，聯合
dropna 為恆等）。
"""

from __future__ import annotations

import copy
import math
import os
import types
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats

from momentum.Analysis import factor_centrality_analyzer as fca_mod
from momentum.Analysis.factor_centrality_analyzer import FactorCentralityAnalyzer
from momentum.Analysis.ic_config_schema import FactorCentralityConfig, ICConfig, TrendAnalysisConfig
from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.Analysis.trend_analyzer import TrendAnalyzer
from momentum.core.exceptions import InsufficientDataError

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
#: SPEC Task 0.3「驗證」：浮點對照之相對誤差門檻
REL_TOL = 1e-12
NON_STAT = "非統計欄"
HEAVY_MARKERS = ("slow", "requires_kline")
RECEIPT = "handoffs/run_receipts/<日期>-icperf-correctness.json"
#: 真實資料：末 2,600 根 1h（滾動 IC 調整後窗 252／756／1512〔ic_engine.py:1553-1565，參考週期 12h〕三窗皆非空）
REAL_ROWS = 2600

_FC = "momentum/Analysis/factor_centrality_analyzer.py"
_TA = "momentum/Analysis/trend_analyzer.py"
_ORC = "momentum/Analysis/ic_filter_orchestrator.py"

#: 欄位清冊：深度報告 `results.factor_centrality`／`results.trend_analysis` 之每一欄位路徑（模組鍵為首段；逐特徵之特徵名段
#: 寫 `*`、list 索引寫 `#`）→ oracle 項 id 與產生之檔:行。封閉性由 `test_centrality_trend_fields_closed` 以真實 kline 之
#: 實際輸出鍵集合對照。
MODULE_FIELDS: Dict[str, Dict[str, str]] = {
    "factor_centrality/pca_summary/explained_variance_ratio/#": {"oracle": "centrality.pca_eigh", "producer": f"{_FC}:61,88"},
    "factor_centrality/pca_summary/total_variance_explained": {"oracle": "centrality.pca_eigh", "producer": f"{_FC}:89"},
    "factor_centrality/pca_summary/effective_rank": {"oracle": "centrality.effective_rank", "producer": f"{_FC}:83-84"},
    "factor_centrality/pca_summary/n_components_used": {"oracle": "centrality.n_components_rule", "producer": f"{_FC}:53-54,91"},
    "factor_centrality/features/*/centrality": {"oracle": "centrality.pca_eigh", "producer": f"{_FC}:60-63,76"},
    "factor_centrality/features/*/crowded": {"oracle": "centrality.crowded_rule", "producer": f"{_FC}:70,77"},
    "factor_centrality/features/*/risk_level": {"oracle": "centrality.crowded_rule", "producer": f"{_FC}:78"},
    "factor_centrality/features/*/percentile_rank": {"oracle": "centrality.rank_pct", "producer": f"{_FC}:64,79"},
    "factor_centrality/features/*/trend": {"oracle": "centrality.feature_trend（unimplemented：寫死 flat）",
                                           "producer": f"{_FC}:80"},
    "factor_centrality/crowded_features/#": {"oracle": "centrality.crowded_rule", "producer": f"{_FC}:67-72,94"},
    "factor_centrality/independent_features/#": {"oracle": "centrality.crowded_rule", "producer": f"{_FC}:73-74,95"},
    "factor_centrality/rolling_centrality/*/#": {"oracle": "centrality.rolling_pit",
                                                 "producer": f"{_FC}:129-158；{_ORC}:3000,3006"},
    "factor_centrality/regimes/*/feature": {"oracle": NON_STAT, "producer": f"{_FC}:187-188"},
    "factor_centrality/regimes/*/regime": {"oracle": "centrality.regime", "producer": f"{_FC}:186"},
    "factor_centrality/regimes/*/crowding_ratio": {"oracle": "centrality.regime", "producer": f"{_FC}:182"},
    "factor_centrality/regimes/*/trend": {"oracle": "centrality.regime_slope", "producer": f"{_FC}:183-185"},
    "factor_centrality/regimes/*/latest": {"oracle": "centrality.regime", "producer": f"{_FC}:192"},
    "trend_analysis/*/ic_trend/slope": {"oracle": "trend.ols", "producer": f"{_TA}:46-50"},
    "trend_analysis/*/ic_trend/p_value": {"oracle": "trend.ols", "producer": f"{_TA}:51"},
    "trend_analysis/*/ic_trend/r_squared": {"oracle": "trend.ols_r2", "producer": f"{_TA}:52"},
    "trend_analysis/*/ic_trend/tail_estimate": {"oracle": "trend.ols", "producer": f"{_TA}:61"},
    "trend_analysis/*/ic_trend/trend": {"oracle": "trend.classify", "producer": f"{_TA}:54-59"},
    "trend_analysis/*/ic_trend/interpretation": {"oracle": "trend.classify", "producer": f"{_TA}:62,154-162"},
    "trend_analysis/*/combined_signal/recommendation": {"oracle": "trend.combined_signal", "producer": f"{_TA}:170-210"},
    "trend_analysis/*/combined_signal/reason": {"oracle": "trend.combined_signal", "producer": f"{_TA}:170-210"},
    "trend_analysis/*/combined_signal/action": {"oracle": "trend.combined_signal", "producer": f"{_TA}:170-210"},
}
#: PCA 例外時之相關係數退回路徑（factor_centrality_analyzer.py:97-127）另有之鍵（真實資料不走此路徑，故不入 MODULE_FIELDS；
#: 以 `test_factor_centrality_fallback_matches_reference` 明列輸入驗）
MODULE_FIELDS_FALLBACK: Dict[str, Dict[str, str]] = {
    "factor_centrality/pca_summary/fallback": {"oracle": NON_STAT, "producer": f"{_FC}:122"},
}
#: 浮點欄（相對誤差 ≤ 1e-12）；其餘欄（整數、布林、標籤、字串、清單元素）須完全相等
NUMERIC_PATHS = {
    "factor_centrality/pca_summary/explained_variance_ratio/#", "factor_centrality/pca_summary/total_variance_explained",
    "factor_centrality/pca_summary/effective_rank", "factor_centrality/features/*/centrality",
    "factor_centrality/features/*/percentile_rank", "factor_centrality/rolling_centrality/*/#",
    "factor_centrality/regimes/*/crowding_ratio", "factor_centrality/regimes/*/latest",
    "trend_analysis/*/ic_trend/slope", "trend_analysis/*/ic_trend/p_value", "trend_analysis/*/ic_trend/r_squared",
    "trend_analysis/*/ic_trend/tail_estimate",
}
#: 逐特徵鍵之 dict 層（其鍵寫 `*`）
_FEATURE_KEYED = {"factor_centrality/features", "factor_centrality/rolling_centrality", "factor_centrality/regimes",
                  "trend_analysis"}


# ── 共用監看（同 test_icperf_correctness.py）─────────────────────────────────────────────────────────────


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
    """相對誤差（兩者皆 NaN 或相等 ⇒ 0；一方 NaN ⇒ inf；b 為 0 ⇒ 絕對誤差）。"""
    if a == b:
        return 0.0
    if math.isnan(a) and math.isnan(b):
        return 0.0
    if math.isnan(a) or math.isnan(b) or math.isinf(a) or math.isinf(b):
        return math.inf
    return abs(a - b) / abs(b) if b != 0 else abs(a - b)


# ── 產品公開入口（呼叫端原樣；stub 只帶 `_ic_cache["rolling_ic"]`）─────────────────────────────────────────


def _stub(rolling_ic: dict) -> Any:
    return types.SimpleNamespace(_ic_cache={"rolling_ic": rolling_ic},
                                 _extract_rolling_ic_series=ICFilterOrchestrator._extract_rolling_ic_series)


def _config(centrality: Optional[dict] = None, trend: Optional[dict] = None) -> ICConfig:
    cfg = ICConfig()
    update: Dict[str, Any] = {}
    if centrality:
        update["factor_centrality"] = FactorCentralityConfig(**{**cfg.factor_centrality.model_dump(), **centrality})
    if trend:
        update["trend_analysis"] = TrendAnalysisConfig(**{**cfg.trend_analysis.model_dump(), **trend})
    return cfg.model_copy(update=update) if update else cfg


def run_factor_centrality(rolling_ic: dict, selected: Sequence[str], cfg: ICConfig) -> dict:
    """產品：`ICFilterOrchestrator._run_factor_centrality`（ic_filter_orchestrator.py:2984-3008）。"""
    return ICFilterOrchestrator._run_factor_centrality(_stub(rolling_ic), list(selected), cfg)


def run_trend_analysis(rolling_ic: dict, selected: Sequence[str], cfg: ICConfig) -> dict:
    """產品：`ICFilterOrchestrator._run_trend_analysis`（ic_filter_orchestrator.py:3010-3022）。"""
    return ICFilterOrchestrator._run_trend_analysis(_stub(rolling_ic), list(selected), cfg)


# ── 參考實作（不呼叫被測模組；逐條註明產品檔:行）────────────────────────────────────────────────────────


class RefSkip:
    """參考實作之「略過」（產品回 SkippedResult 或呼叫端拋 InsufficientDataError）；reason 與產品字串同。"""

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def __repr__(self) -> str:
        return f"RefSkip({self.reason!r})"


def ref_extract_rolling_ic_series(window_dict: Any) -> Tuple[Optional[str], np.ndarray]:
    """`_extract_rolling_ic_series`（ic_filter_orchestrator.py:3363-3372）：取 list 長度最大之窗（非 list 計 0；同長取
    字典序首個——`max` 回首個最大者），值原樣轉 float，時間戳不保留（位置索引）。回 (窗鍵, 值)。"""
    if not isinstance(window_dict, dict) or not window_dict:
        return None, np.empty(0, dtype=float)
    best_key, best_len = None, -1
    for key, val in window_dict.items():
        length = len(val) if isinstance(val, list) else 0
        if length > best_len:
            best_key, best_len = key, length
    values = window_dict.get(best_key, [])
    return best_key, np.asarray(values, dtype=float).reshape(-1)


def ref_ic_matrix(rolling_ic: dict, selected: Sequence[str]) -> Tuple[List[str], np.ndarray, List[Optional[str]]]:
    """呼叫端建矩陣（ic_filter_orchestrator.py:2987-2992、:3013-3018）：依 rolling_ic 之鍵序，只取 selected 內且值為 dict
    者；各欄自位置 0 對齊（`pd.DataFrame({name: Series})` 之 RangeIndex 聯集），較短者尾端補 NaN。"""
    names: List[str] = []
    cols: List[np.ndarray] = []
    keys: List[Optional[str]] = []
    sel = set(selected)
    for name, value in rolling_ic.items():
        if name in sel and isinstance(value, dict):
            key, arr = ref_extract_rolling_ic_series(value)
            names.append(name)
            cols.append(arr)
            keys.append(key)
    n = max((len(c) for c in cols), default=0)
    mat = np.full((n, len(cols)), np.nan)
    for j, col in enumerate(cols):
        mat[: len(col), j] = col
    return names, mat, keys


def _ref_normalize(mat: np.ndarray) -> np.ndarray:
    """`_normalize_ic_matrix`（factor_centrality_analyzer.py:196-201）：±inf→NaN，再以各欄有限值均值補 NaN（全 NaN 欄仍 NaN）。"""
    m = np.where(np.isfinite(mat), mat, np.nan)
    finite = ~np.isnan(m)
    cnt = finite.sum(axis=0)
    sums = np.where(finite, m, 0.0).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = np.where(cnt > 0, sums / np.maximum(cnt, 1), np.nan)
    return np.where(finite, m, mu[None, :])


def ref_centrality(mat: np.ndarray, names: Sequence[str], cfg: Mapping[str, Any], pca_fails: bool = False) -> Any:
    """`compute_centrality`（factor_centrality_analyzer.py:28-127）。PCA 路徑之 oracle＝標準化（ddof=0，StandardScaler
    :55-56）後之樣本共變異矩陣（ddof=1）以 `numpy.linalg.eigh` 求特徵值／向量（降冪），取前 k＝max(1, min(n_components,
    p−1, n−1)) 個（:53-54）；evr＝λ_k／trace（:61）、centrality_i＝Σ_k v_ik²·evr_k（:60-62）、effective_rank＝(Σλ_k)²／Σλ_k²
    （只對保留之 k 個，:83-84）、percentile_rank＝`scipy.stats.rankdata(average)`／p×100（:64）、crowded＝centrality ≥ 門檻
    （:70）。`pca_fails` ⇒ 退回路徑（:97-127）：Spearman 相關絕對值逐列平均（含對角線 1，:99-103）。"""
    if mat.size == 0:
        return RefSkip("empty ic matrix")
    m = _ref_normalize(mat)
    keep_c = ~np.all(np.isnan(m), axis=0)
    m = m[:, keep_c]
    cols = [n for n, k in zip(names, keep_c) if k]
    if m.shape[1]:
        m = m[~np.all(np.isnan(m), axis=1)]
    if m.shape[1] < 3:
        return RefSkip(f"n_features({m.shape[1]}) < min_required(3)")
    min_samples = int(cfg["min_samples_for_pca"])
    if m.shape[0] < min_samples:
        return RefSkip(f"n_samples({m.shape[0]}) < min_required({min_samples})")
    nonconst = [j for j in range(m.shape[1]) if np.unique(m[:, j]).size > 1]
    m = m[:, nonconst]
    cols = [cols[j] for j in nonconst]
    if m.shape[1] < 2:
        return RefSkip("all features are constant")
    thr = float(cfg["crowded_threshold"])
    n, p = m.shape
    if pca_fails:
        return _ref_centrality_fallback(m, cols, thr)
    k = max(1, min(int(cfg["n_components"]), p - 1, n - 1))
    z = (m - m.mean(axis=0)) / m.std(axis=0)
    cov = z.T @ z / (n - 1)
    lam, vec = np.linalg.eigh(cov)
    lam, vec = lam[::-1], vec[:, ::-1]
    evr = lam[:k] / np.trace(cov)
    cen = (vec[:, :k] ** 2) @ evr
    lam_k = lam[:k]
    denom = float(np.sum(lam_k ** 2))
    eff = float(lam_k.sum() ** 2 / denom) if denom > 0 else 1.0
    rank = stats.rankdata(cen, method="average") / p * 100.0
    features: Dict[str, dict] = {}
    for j, name in enumerate(cols):
        crowded = bool(cen[j] >= thr)
        features[name] = {"centrality": float(cen[j]), "crowded": crowded, "risk_level": "high" if crowded else "low",
                          "percentile_rank": float(rank[j]), "trend": "flat"}
    return {
        "pca_summary": {"explained_variance_ratio": [float(v) for v in evr], "total_variance_explained": float(evr.sum()),
                        "effective_rank": eff, "n_components_used": int(k)},
        "features": features,
        "crowded_features": [c for j, c in enumerate(cols) if cen[j] >= thr],
        "independent_features": [c for j, c in enumerate(cols) if not cen[j] >= thr],
        "_all_eigenvalues": lam,
    }


def _spearman_matrix(m: np.ndarray) -> np.ndarray:
    p = m.shape[1]
    if p == 2:
        r = float(stats.spearmanr(m[:, 0], m[:, 1])[0])
        return np.array([[1.0, r], [r, 1.0]])
    return np.asarray(stats.spearmanr(m)[0], dtype=float)


def _ref_centrality_fallback(m: np.ndarray, cols: Sequence[str], thr: float, exclude_self: bool = False) -> dict:
    """退回路徑（factor_centrality_analyzer.py:97-127）：|Spearman 相關| 之逐列平均（產品含對角線；`exclude_self` ⇒
    只對其他特徵平均之業界定義〔平均絕對相關〕）。"""
    corr = np.abs(_spearman_matrix(m))
    p = corr.shape[0]
    if exclude_self:
        cen = (corr.sum(axis=1) - np.diag(corr)) / (p - 1)
    else:
        cen = corr.mean(axis=1)
    rank = stats.rankdata(cen, method="average") / p * 100.0
    features = {name: {"centrality": float(cen[j]), "crowded": bool(cen[j] >= thr),
                       "risk_level": "high" if cen[j] >= thr else "low", "percentile_rank": float(rank[j]),
                       "trend": "flat"} for j, name in enumerate(cols)}
    return {
        "pca_summary": {"explained_variance_ratio": [], "total_variance_explained": math.nan, "effective_rank": math.nan,
                        "n_components_used": 0, "fallback": "correlation_based"},
        "features": features,
        "crowded_features": [c for j, c in enumerate(cols) if cen[j] >= thr],
        "independent_features": [c for j, c in enumerate(cols) if cen[j] < thr],
    }


def ref_rolling_centrality(mat: np.ndarray, names: Sequence[str], cfg: Mapping[str, Any],
                           pca_fails: bool = False) -> Dict[str, List[float]]:
    """`compute_rolling_centrality`（factor_centrality_analyzer.py:129-158）：窗長＝min(rolling_window, 列數)、< 5 ⇒ 空；
    逐窗終點 end 只用 [end−w, end) 之列（PIT），窗內獨立重做正規化與 PCA；略過之窗不留列；欄依名稱排序（:158），缺者 NaN。"""
    n = mat.shape[0]
    if mat.size == 0:
        return {}
    w = min(int(cfg["rolling_window"]), n)
    if w < 5:
        return {}
    rows: List[Dict[str, float]] = []
    for end in range(w, n + 1):
        res = ref_centrality(mat[end - w: end], names, cfg, pca_fails=pca_fails)
        if isinstance(res, RefSkip) or not res["features"]:
            continue
        rows.append({k: v["centrality"] for k, v in res["features"].items()})
    if not rows:
        return {}
    cols = sorted(set().union(*rows))
    return {c: [row.get(c, math.nan) for row in rows] for c in cols}


def ref_regime(rolling: Mapping[str, List[float]], name: str, thr: float) -> dict:
    """`detect_crowding_regime`（factor_centrality_analyzer.py:160-193）：crowding_ratio＝有限值中 ≥ 門檻之比例（:182）、
    斜率＝`scipy.stats.linregress` 對位置之 OLS 斜率（長度 < 3 ⇒ 0，:184；常數序列之斜率依定義為 0）、趨勢依斜率正負（:185）、
    regime 依 ratio ≥ 0.5（:186）、latest＝末值（:192）。"""
    unknown = {"feature": name, "regime": "unknown", "crowding_ratio": math.nan, "trend": "indeterminate"}
    if not rolling or name not in rolling:
        return unknown
    s = np.asarray(rolling[name], dtype=float)
    s = s[~np.isnan(s)]
    if s.size == 0:
        return unknown
    ratio = float(np.mean(s >= thr))
    if s.size < 3 or np.unique(s).size == 1:
        slope = 0.0
    else:
        slope = float(stats.linregress(np.arange(s.size, dtype=float), s).slope)
    trend = "rising" if slope > 0 else "falling" if slope < 0 else "flat"
    return {"feature": name, "regime": "crowded" if ratio >= 0.5 else "normal", "crowding_ratio": ratio,
            "trend": trend, "latest": float(s[-1])}


def ref_factor_centrality(rolling_ic: dict, selected: Sequence[str], cfg: Mapping[str, Any],
                          pca_fails: bool = False) -> Any:
    """呼叫端 `_run_factor_centrality`（ic_filter_orchestrator.py:2984-3008）之參考：矩陣空 ⇒ 略過（:2993-2994）；
    centrality 略過 ⇒ 略過（:2998-2999）；否則併 rolling_centrality（原矩陣，:3000）與逐欄 regimes（:3001-3004）。"""
    names, mat, _ = ref_ic_matrix(rolling_ic, selected)
    if mat.size == 0:
        return RefSkip("rolling_ic matrix unavailable")
    cen = ref_centrality(mat, names, cfg, pca_fails=pca_fails)
    if isinstance(cen, RefSkip):
        return cen
    rolling = ref_rolling_centrality(mat, names, cfg, pca_fails=pca_fails)
    thr = float(cfg["crowded_threshold"])
    out = {k: v for k, v in cen.items() if not k.startswith("_")}
    out["rolling_centrality"] = rolling
    out["regimes"] = {name: ref_regime(rolling, name, thr) for name in names}
    out["_all_eigenvalues"] = cen.get("_all_eigenvalues")
    return out


_INTERP = {"down": "呈現顯著下降趨勢，可能衰減", "up": "呈現顯著上升趨勢", "flat": "趨勢不顯著或近乎持平"}


def _ref_winsorize(s: np.ndarray) -> np.ndarray:
    """`_winsorize`（trend_analyzer.py:148-152）：1%／99% 分位（線性內插＝pandas 預設）截尾。"""
    lo = float(np.quantile(s, 0.01))
    hi = float(np.quantile(s, 0.99))
    return np.clip(s, lo, hi)


def _ref_classify(slope: float, p_value: float, r2: float, cfg: Mapping[str, Any]) -> str:
    """趨勢判定（trend_analyzer.py:54-59）。"""
    if not math.isfinite(slope) or not math.isfinite(r2):
        return "indeterminate"
    if p_value <= float(cfg["significance_level"]) and r2 >= float(cfg["r_squared_threshold"]):
        return "up" if slope > 0 else "down" if slope < 0 else "flat"
    return "flat"


def ref_trend_series(values: Any, cfg: Mapping[str, Any], window_lags: Optional[int] = None) -> Optional[dict]:
    """`analyze_trend`（trend_analyzer.py:26-71）：去 NaN（:27，±inf 保留）；有效數 < min_samples ⇒ None（:28-33）；相異值
    ≤ 1 ⇒ 常數結果（:35-44）；winsorize 後對位置 0..n−1（去 NaN 後重編，:47）以 `statsmodels.api.OLS`（非穩健共變異）取斜率、
    截距、斜率 p 值（:48-51），R²＝`scipy.stats.pearsonr(x, y)` 之 r²（:52）；截尾後 y 為常數 ⇒ 斜率 0、p 1、R² 0（同 scipy
    linregress 之零變異約定）；含非有限 ⇒ 斜率／尾端 NaN、p 1、R² 0（:51-55）。`window_lags` 給定時另以
    `cov_type="HAC"`（Bartlett、maxlags＝window_lags、無小樣本修正、t 分布）算業界之重疊窗 p 值 `p_value_hac` 與
    `trend_hac`。"""
    s = np.asarray(values, dtype=float).reshape(-1)
    s = s[~np.isnan(s)]
    if s.size < int(cfg["min_samples"]):
        return None
    if np.unique(s).size <= 1:
        return {"slope": 0.0, "p_value": 1.0, "r_squared": 0.0, "tail_estimate": float(s[0]), "trend": "flat",
                "interpretation": "序列近乎常數，趨勢為平坦"}
    with np.errstate(invalid="ignore"):
        yw = _ref_winsorize(s)
    n = yw.size
    x = np.arange(n, dtype=float)
    p_hac = math.nan
    t_abs, df_resid = math.nan, math.nan
    if not np.all(np.isfinite(yw)):
        slope, intercept, p_value, r2 = math.nan, math.nan, 1.0, 0.0
    elif np.unique(yw).size == 1:
        slope, intercept, p_value, r2 = 0.0, float(yw[0]), 1.0, 0.0
        p_hac = 1.0
    else:
        exog = sm.add_constant(x)
        fit = sm.OLS(yw, exog).fit()
        slope, intercept, p_value = float(fit.params[1]), float(fit.params[0]), float(fit.pvalues[1])
        t_abs, df_resid = abs(float(fit.tvalues[1])), float(fit.df_resid)
        r2 = float(stats.pearsonr(x, yw)[0]) ** 2
        if window_lags is not None and window_lags < n - 2:
            hac = sm.OLS(yw, exog).fit(cov_type="HAC", use_t=True,
                                       cov_kwds={"maxlags": int(window_lags), "kernel": "bartlett",
                                                 "use_correction": False})
            p_hac = float(hac.pvalues[1])
    if not math.isfinite(p_value):
        p_value = 1.0
    trend = _ref_classify(slope, p_value, r2, cfg)
    out = {"slope": slope, "p_value": p_value, "r_squared": r2, "tail_estimate": float(intercept + slope * (n - 1)),
           "trend": trend, "interpretation": _INTERP.get(trend, "趨勢不確定"), "_t_abs": t_abs, "_df": df_resid}
    if window_lags is not None:
        ph = p_hac if math.isfinite(p_hac) else 1.0
        out["p_value_hac"] = ph
        out["trend_hac"] = _ref_classify(slope, ph, r2, cfg)
    return out


def ref_combined_signal(ic_trend: Optional[str], centrality_trend: Optional[str],
                        half_life: Optional[float]) -> dict:
    """`_combine_signal`（trend_analyzer.py:170-210）規則表；缺維度 ⇒ "flat"（:176-177）。"""
    ic = ic_trend or "flat"
    ce = centrality_trend or "flat"
    rec, reason, action = "正常", "訊號穩定", "維持觀察"
    if ic == "down" and ce == "up":
        rec, reason, action = "危險", "IC 下降 + Centrality 上升", "建議降低配置"
    elif (ic == "down" and ce == "flat") or (ic == "flat" and ce == "up"):
        rec, reason, action = "警告", "存在衰減或擁擠訊號", "建議提高監控頻率"
    elif ic == "up" and ce == "down":
        rec, reason, action = "正常", "IC 改善且擁擠度降低", "可維持配置"
    if half_life is not None and math.isfinite(half_life) and half_life < 5:
        if rec == "正常":
            rec, reason = "警告", reason + " + half_life 偏短"
        elif rec == "警告":
            rec, reason = "危險", reason + " + half_life 偏短"
    return {"recommendation": rec, "reason": reason, "action": action}


def _window_lags(window_key: Optional[str], n: int, stride: int) -> int:
    """重疊窗之 HAC 落後期數：max(Newey–West 自動頻寬 int(4·(n/100)^(2/9))，相鄰值共用觀測之落後數 ceil(w/stride)−1)——
    同本專案 HAC 慣例（statistical_validator.py:118-122 以 max(自動, horizon−1)）。"""
    try:
        w = int(str(window_key).rsplit("_", 1)[1])
    except (IndexError, ValueError):
        w = 1
    return max(int(4 * (n / 100.0) ** (2.0 / 9.0)), int(math.ceil(w / max(1, stride))) - 1)


def ref_trend_analysis(rolling_ic: dict, selected: Sequence[str], cfg: Mapping[str, Any],
                       rolling_stride: int = 1, with_hac: bool = False) -> Any:
    """呼叫端 `_run_trend_analysis`（ic_filter_orchestrator.py:3010-3022）＋`batch_analyze`（trend_analyzer.py:119-146）：
    取矩陣前 max(1, len(selected)) 欄（:126），每欄只算 IC 維度（呼叫端未傳 centrality／half_life，:3022）；有效數不足者無
    `ic_trend` 鍵、combined_signal 依缺維度＝flat。"""
    names, mat, keys = ref_ic_matrix(rolling_ic, selected)
    if mat.size == 0:
        return RefSkip("rolling_ic matrix unavailable")
    out: Dict[str, dict] = {}
    for j, name in enumerate(names[: max(1, len(selected))]):
        col = mat[:, j]
        lags = None
        if with_hac:
            lags = _window_lags(keys[j], int(np.sum(~np.isnan(col))), rolling_stride)
        res = ref_trend_series(col, cfg, window_lags=lags)
        entry: Dict[str, Any] = {}
        if res:
            entry["ic_trend"] = res
        entry["combined_signal"] = ref_combined_signal(res["trend"] if res else None, None, None)
        out[name] = entry
    return out


# ── 比對（收據腳本可直接以實際輸入與輸出呼叫）──────────────────────────────────────────────────────────


def _paths(obj: Any, path: str) -> set:
    """輸出之欄位路徑集合（逐特徵段→`*`、純量 list→`/#`）。"""
    if isinstance(obj, dict):
        out: set = set()
        for k, v in obj.items():
            seg = "*" if path in _FEATURE_KEYED else str(k)
            out |= _paths(v, f"{path}/{seg}")
        return out or {path}
    if isinstance(obj, list):
        if any(isinstance(e, (dict, list)) for e in obj):
            out = set()
            for e in obj:
                out |= _paths(e, f"{path}/#")
            return out
        return {f"{path}/#"}
    return {path}


def _leaves(obj: Any, path: str, tag: str = "") -> List[Tuple[str, str, Any]]:
    """(欄位路徑, 位置標記, 值)：逐特徵段之鍵與 list 索引記入位置標記，供逐元素對照。"""
    if isinstance(obj, dict):
        out: List[Tuple[str, str, Any]] = []
        for k, v in obj.items():
            if str(k).startswith("_"):
                continue
            if path in _FEATURE_KEYED:
                out += _leaves(v, f"{path}/*", f"{tag}[{k}]")
            else:
                out += _leaves(v, f"{path}/{k}", tag)
        return out
    if isinstance(obj, list):
        out = []
        for i, e in enumerate(obj):
            out += _leaves(e, f"{path}/#", f"{tag}#{i}")
        if not obj:
            out.append((f"{path}/#", f"{tag}#∅", None))
        return out
    return [(path, tag, obj)]


def _to_float(v: Any) -> float:
    if v is None:
        return math.nan
    return float(v)


def _verdict_numeric(pairs: List[Tuple[str, Any, Any]]) -> Dict[str, Any]:
    max_rel, n_fin, bad = 0.0, 0, []
    for tag, pv, ov in pairs:
        if pv is None and ov is None:
            continue
        a, b = _to_float(pv), _to_float(ov)
        if math.isfinite(a):
            n_fin += 1
        r = _rel(a, b)
        max_rel = max(max_rel, r)
        if r > REL_TOL:
            bad.append(f"{tag}: 產品 {a!r} vs oracle {b!r}")
    return {"verdict": "一致" if not bad else "不一致", "max_rel_diff": max_rel if pairs else None, "n_finite": n_fin,
            "detail": "; ".join(bad[:5])}


def _p_consistent(p_prod: float, p_orc: float, t_abs: float, df: float) -> Tuple[bool, float]:
    """p 值一致判定：p 相對誤差 ≤ 1e-12，**或**產品 p 落於 oracle |t| 擾動 ±1e-12（相對）所對應之雙尾 p 區間
    [2·t.sf(|t|(1+1e-12)), 2·t.sf(|t|(1−1e-12))]（`scipy.stats.t`，df＝n−2；後向誤差判定）。理由：雙尾 p 對 t 之條件數約
    |t|·(df+1)|t|／(df+t²)，極端尾部（如 p≈1e-76、|t|≈45）時 t 之 1e-14 捨入差即放大為 p 之 1e-12 以上，不屬計算錯誤；
    t 為良態量（反推用之 `t.isf` 於此尾部本身僅約 1e-11 精度，故不採反推）。回 (一致, p 之相對誤差)。"""
    r = _rel(p_prod, p_orc)
    if r <= REL_TOL:
        return True, r
    if math.isfinite(t_abs) and math.isfinite(df) and t_abs > 0 and math.isfinite(p_prod):
        lo = 2.0 * float(stats.t.sf(t_abs * (1.0 + REL_TOL), df))
        hi = 2.0 * float(stats.t.sf(t_abs * (1.0 - REL_TOL), df))
        if lo * (1.0 - REL_TOL) <= p_prod <= hi * (1.0 + REL_TOL):
            return True, r
    return False, r


def _verdict_pvalue(items: List[Tuple[str, Any, Any, float, float]]) -> Dict[str, Any]:
    max_rel, n_fin, bad = 0.0, 0, []
    for tag, pv, ov, t_abs, df in items:
        a, b = _to_float(pv), _to_float(ov)
        n_fin += int(math.isfinite(a))
        ok, r = _p_consistent(a, b, t_abs, df)
        max_rel = max(max_rel, r)
        if not ok:
            bad.append(f"{tag}: 產品 {a!r} vs oracle {b!r}")
    return {"verdict": "一致" if not bad else "不一致", "max_rel_diff": max_rel if items else None, "n_finite": n_fin,
            "detail": "; ".join(bad[:5]) + ("（p 或其對應 |t| 之相對誤差 ≤ 1e-12 即一致）" if items else "")}


def _verdict_exact(pairs: List[Tuple[str, Any, Any]]) -> Dict[str, Any]:
    bad = [f"{tag}: 產品 {pv!r} vs oracle {ov!r}" for tag, pv, ov in pairs if pv != ov]
    n_fin = sum(1 for _, pv, _ in pairs if pv is not None)
    return {"verdict": "一致" if not bad else "不一致", "max_rel_diff": None, "n_finite": n_fin, "detail": "; ".join(bad[:5])}


def _compare_trees(product: Any, oracle: Any, root: str) -> Dict[str, Dict[str, Any]]:
    prod = _leaves(product, root)
    orc = _leaves(oracle, root)
    by_path: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for path, tag, v in prod:
        by_path.setdefault(path, {"p": {}, "o": {}})["p"][tag] = v
    for path, tag, v in orc:
        by_path.setdefault(path, {"p": {}, "o": {}})["o"][tag] = v
    out: Dict[str, Dict[str, Any]] = {}
    for path, d in sorted(by_path.items()):
        tags_p, tags_o = set(d["p"]), set(d["o"])
        if path not in MODULE_FIELDS and path not in MODULE_FIELDS_FALLBACK:
            out[path] = {"verdict": "不一致", "max_rel_diff": None, "n_finite": len(tags_p),
                         "detail": "未登錄於 MODULE_FIELDS 之欄位"}
            continue
        if tags_p != tags_o:
            out[path] = {"verdict": "不一致", "max_rel_diff": None, "n_finite": len(tags_p),
                         "detail": f"位置不同：只產品 {sorted(tags_p - tags_o)[:5]}；只 oracle {sorted(tags_o - tags_p)[:5]}"}
            continue
        pairs = [(t, d["p"][t], d["o"][t]) for t in sorted(tags_p)]
        out[path] = _verdict_numeric(pairs) if path in NUMERIC_PATHS else _verdict_exact(pairs)
    return out


def compare_factor_centrality(product_output: Any, rolling_ic: dict, selected_features: Sequence[str],
                              config: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """`results.factor_centrality` 逐欄對照。輸入＝產品公開入口之同一組（`_ic_cache["rolling_ic"]`、selected、
    `config.factor_centrality.model_dump()`）；`product_output` 為產品回傳 dict 或其拋出之例外。另附兩項業界／一致性
    oracle（鍵帶 `@`）：`effective_rank@all_eigen`（全部特徵值之參與率）、`features/*/trend@regimes`（同模組
    regimes 之斜率趨勢）。"""
    pca_fails = isinstance(product_output, dict) and "fallback" in product_output.get("pca_summary", {})
    ref = ref_factor_centrality(rolling_ic, selected_features, config, pca_fails=pca_fails)
    if isinstance(ref, RefSkip) or isinstance(product_output, BaseException):
        prod_reason = str(product_output) if isinstance(product_output, BaseException) else "（產品未略過）"
        ref_reason = ref.reason if isinstance(ref, RefSkip) else "（oracle 未略過）"
        ok = isinstance(product_output, InsufficientDataError) and isinstance(ref, RefSkip) and prod_reason == ref_reason
        return {"factor_centrality（略過）": {"verdict": "一致" if ok else "不一致", "max_rel_diff": None, "n_finite": 0,
                                           "detail": f"產品 {prod_reason!r} vs oracle {ref_reason!r}"}}
    out = _compare_trees(product_output, ref, "factor_centrality")
    lam = ref.get("_all_eigenvalues")
    if lam is not None:
        lam = np.clip(np.asarray(lam, dtype=float), 0.0, None)
        eff_all = float(lam.sum() ** 2 / np.sum(lam ** 2))
        out["factor_centrality/pca_summary/effective_rank@all_eigen"] = _verdict_numeric(
            [("", product_output["pca_summary"]["effective_rank"], eff_all)])
    out["factor_centrality/features/*/trend@regimes"] = _verdict_exact(
        [(f"[{n}]", v.get("trend"), ref["regimes"].get(n, {}).get("trend"))
         for n, v in product_output.get("features", {}).items()])
    return out


def compare_trend_analysis(product_output: Any, rolling_ic: dict, selected_features: Sequence[str],
                           config: Mapping[str, Any], rolling_stride: int = 1) -> Dict[str, Dict[str, Any]]:
    """`results.trend_analysis` 逐欄對照（輸入同產品公開入口；`config`＝`config.trend_analysis.model_dump()`，
    `rolling_stride`＝`config.ic_calculation.rolling_stride`）。另附業界 oracle（鍵帶 `@`）：`ic_trend/p_value@hac`、
    `ic_trend/trend@hac`——重疊窗滾動 IC 之斜率以 HAC（Newey–West）標準誤檢定。"""
    ref = ref_trend_analysis(rolling_ic, selected_features, config, rolling_stride=rolling_stride, with_hac=True)
    if isinstance(ref, RefSkip) or isinstance(product_output, BaseException):
        prod_reason = str(product_output) if isinstance(product_output, BaseException) else "（產品未略過）"
        ref_reason = ref.reason if isinstance(ref, RefSkip) else "（oracle 未略過）"
        ok = isinstance(product_output, InsufficientDataError) and isinstance(ref, RefSkip) and prod_reason == ref_reason
        return {"trend_analysis（略過）": {"verdict": "一致" if ok else "不一致", "max_rel_diff": None, "n_finite": 0,
                                        "detail": f"產品 {prod_reason!r} vs oracle {ref_reason!r}"}}
    plain = {n: {k: ({kk: vv for kk, vv in v.items() if not kk.endswith("_hac")} if k == "ic_trend" else v)
                 for k, v in e.items()} for n, e in ref.items()}
    out = _compare_trees(product_output, plain, "trend_analysis")
    pkey = "trend_analysis/*/ic_trend/p_value"
    if pkey in out and "位置不同" not in out[pkey]["detail"] and "未登錄" not in out[pkey]["detail"]:
        out[pkey] = _verdict_pvalue([(f"[{n}]", product_output[n]["ic_trend"]["p_value"], e["ic_trend"]["p_value"],
                                      e["ic_trend"].get("_t_abs", math.nan), e["ic_trend"].get("_df", math.nan))
                                     for n, e in ref.items() if "ic_trend" in e])
    out["trend_analysis/*（鍵集合）"] = _verdict_exact([("", list(product_output), list(ref))])
    hac_p, hac_t = [], []
    for n, e in ref.items():
        if "ic_trend" in e and "p_value_hac" in e["ic_trend"]:
            prod = product_output.get(n, {}).get("ic_trend", {})
            hac_p.append((f"[{n}]", prod.get("p_value"), e["ic_trend"]["p_value_hac"]))
            hac_t.append((f"[{n}]", prod.get("trend"), e["ic_trend"]["trend_hac"]))
    out["trend_analysis/*/ic_trend/p_value@hac"] = _verdict_numeric(hac_p)
    out["trend_analysis/*/ic_trend/trend@hac"] = _verdict_exact(hac_t)
    return out


def _formula_verdicts(res: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """依產品公式之對照項（不含 `@` 業界／一致性項）。"""
    return {k: v for k, v in res.items() if "@" not in k}


def _assert_all_consistent(res: Dict[str, Dict[str, Any]]) -> None:
    bad = {k: v["detail"] for k, v in _formula_verdicts(res).items() if v["verdict"] != "一致"}
    assert not bad, f"不一致：{bad}"


# ── 明列輸入（秒級邊界案）──────────────────────────────────────────────────────────────────────────────


def _ic_dict(cols: Mapping[str, Sequence[float]], key: str = "window_21", extra: Optional[Mapping[str, list]] = None) -> dict:
    """明列之滾動 IC：{特徵: {窗鍵: list}}（extra 給其他較短之窗）。"""
    out = {}
    for name, vals in cols.items():
        d = {key: [float(v) for v in vals]}
        for k, v in (extra or {}).items():
            d[k] = list(v)
        out[name] = d
    return out


def _factor_ic(n: int, p: int, seed: int, rank: int = 2, noise: float = 0.5) -> Dict[str, np.ndarray]:
    """明列輸入：低秩共同成分＋個別雜訊之 IC 矩陣（固定 seed，值域約 ±0.3）。"""
    rng = np.random.default_rng(seed)
    base = rng.standard_normal((n, rank)) @ rng.standard_normal((rank, p)) + noise * rng.standard_normal((n, p))
    base = 0.1 * base
    return {f"f{j:02d}": base[:, j] for j in range(p)}


def _cfg_c(**kw: Any) -> dict:
    return {**FactorCentralityConfig().model_dump(), **kw}


def _cfg_t(**kw: Any) -> dict:
    return {**TrendAnalysisConfig().model_dump(), **kw}


def _run_c(rolling_ic: dict, selected: Sequence[str], **kw: Any) -> Tuple[Any, dict]:
    cfg = _config(centrality=kw or None)
    try:
        out: Any = run_factor_centrality(rolling_ic, selected, cfg)
    except InsufficientDataError as exc:
        out = exc
    return out, cfg.factor_centrality.model_dump()


def _run_t(rolling_ic: dict, selected: Sequence[str], **kw: Any) -> Tuple[Any, dict]:
    cfg = _config(trend=kw or None)
    try:
        out: Any = run_trend_analysis(rolling_ic, selected, cfg)
    except InsufficientDataError as exc:
        out = exc
    return out, cfg.trend_analysis.model_dump()


# ── 秒級：_extract_rolling_ic_series ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("window_dict", [
    {},
    {"window_21": [0.1, 0.2, 0.3], "window_63": [0.4]},
    {"window_21": [0.1, 0.2], "window_63": [0.3, 0.4]},
    {"window_21": "x", "window_63": [0.5, 0.6]},
    {"window_21": [], "window_63": []},
    {"window_21": [0.1, math.nan, 0.3]},
])
def test_extract_rolling_ic_series_matches_reference(window_dict: dict) -> None:
    """取最長之 list 窗（非 list 計 0、同長取首個）、值原樣、索引為位置（RangeIndex）。"""
    got = ICFilterOrchestrator._extract_rolling_ic_series(window_dict)
    _, exp = ref_extract_rolling_ic_series(window_dict)
    assert isinstance(got.index, pd.RangeIndex)
    np.testing.assert_array_equal(got.to_numpy(dtype=float), exp)


# ── 秒級：factor_centrality ───────────────────────────────────────────────────────────────────────────


def test_factor_centrality_skip_boundaries() -> None:
    """略過分支：空矩陣、特徵 < 3（含全 NaN 欄被剔除後）、列數 < min_samples_for_pca、非常數欄 < 2——產品拋
    InsufficientDataError 之 reason 與參考實作同字串。"""
    ic = _factor_ic(80, 3, seed=1)
    cases = [
        ({}, ["a"]),
        (_ic_dict({"a": ic["f00"], "b": ic["f01"]}), ["a", "b"]),
        (_ic_dict({"a": ic["f00"], "b": ic["f01"], "c": [math.nan] * 80}), ["a", "b", "c"]),
        (_ic_dict({k: v[:29] for k, v in ic.items()}), list(ic)),
        (_ic_dict({"a": ic["f00"], "b": [0.1] * 80, "c": [0.2] * 80}), ["a", "b", "c"]),
        (_ic_dict({"a": ic["f00"], "b": ic["f01"]}), ["z"]),
    ]
    for rolling_ic, sel in cases:
        prod, cfg = _run_c(rolling_ic, sel)
        assert isinstance(prod, InsufficientDataError), f"預期略過：{prod!r}"
        res = compare_factor_centrality(prod, rolling_ic, sel, cfg)
        assert res["factor_centrality（略過）"]["verdict"] == "一致", res


_C_CASES = {
    "clean_4x80": (lambda: _ic_dict(_factor_ic(80, 4, seed=2)), {}),
    "nan_and_inf": (lambda: _ic_dict({k: np.where(np.arange(90) % 7 == 3, math.nan,
                                                   np.where(np.arange(90) == 11, math.inf, v))
                                      for k, v in _factor_ic(90, 5, seed=3).items()}), {}),
    "one_constant_k1": (lambda: _ic_dict({**{k: v for k, v in _factor_ic(70, 2, seed=4).items()}, "c": [0.05] * 70}), {}),
    "rows_below_window": (lambda: _ic_dict(_factor_ic(40, 4, seed=5)), {}),
    "low_threshold_crowded": (lambda: _ic_dict(_factor_ic(90, 4, seed=6, rank=1, noise=0.2)), {"crowded_threshold": 0.2}),
    "all_nan_column": (lambda: {**_ic_dict(_factor_ic(80, 3, seed=7)), "dead": {"window_21": [math.nan] * 80}}, {}),
    "n_components_1": (lambda: _ic_dict(_factor_ic(80, 6, seed=8)), {"n_components": 1}),
    "unequal_lengths": (lambda: _ic_dict({k: (v if k != "f02" else v[:60]) for k, v in _factor_ic(80, 4, seed=9).items()}), {}),
    "window_tie_and_extra": (lambda: _ic_dict(_factor_ic(75, 4, seed=10), extra={"window_63": [0.1] * 10}), {}),
}


@pytest.mark.parametrize("case", sorted(_C_CASES))
def test_factor_centrality_matches_oracle(case: str) -> None:
    """明列邊界（乾淨、含 NaN／inf、單一常數欄致 k＝1、列數 < 滾動窗致單窗、低門檻致擁擠、全 NaN 欄、n_components＝1、
    各欄長度不等〔位置對齊尾端補 NaN 再以均值補〕、多窗擇最長）：逐欄 == oracle（PCA＝numpy.linalg.eigh；相對誤差 ≤ 1e-12）。"""
    build, kw = _C_CASES[case]
    rolling_ic = build()
    sel = list(rolling_ic)
    prod, cfg = _run_c(rolling_ic, sel, **kw)
    assert isinstance(prod, dict), prod
    res = compare_factor_centrality(prod, rolling_ic, sel, cfg)
    _assert_all_consistent(res)
    if case == "low_threshold_crowded":
        assert prod["crowded_features"] and any(r["regime"] == "crowded" for r in prod["regimes"].values())
    if case == "rows_below_window":
        assert all(len(v) == 1 for v in prod["rolling_centrality"].values())
        assert all(r["trend"] == "flat" for r in prod["regimes"].values())
    if case == "one_constant_k1":
        assert prod["pca_summary"]["n_components_used"] == 1 and prod["regimes"]["c"]["regime"] == "unknown"


def test_rolling_centrality_below_five_and_regime_unknown() -> None:
    """窗長 < 5 ⇒ 滾動中心性為空、regime 為 unknown（factor_centrality_analyzer.py:140-141、:165-171）。"""
    ic = pd.DataFrame(_factor_ic(40, 4, seed=11))
    an = FactorCentralityAnalyzer(_cfg_c())
    rolling = an.compute_rolling_centrality(ic, window=4)
    assert rolling.empty and ref_rolling_centrality(ic.to_numpy(), list(ic), {**_cfg_c(), "rolling_window": 4}) == {}
    for name in ic.columns:
        got = an.detect_crowding_regime(rolling, name)
        exp = ref_regime({}, name, 0.3)
        assert got["regime"] == exp["regime"] == "unknown" and got["trend"] == exp["trend"]
        assert math.isnan(got["crowding_ratio"]) and set(got) == set(exp)


def test_rolling_centrality_prefix_invariant() -> None:
    """防偷看未來：截去末 15 列後，前段之逐窗中心性不變（每窗只用 [end−w, end)）。"""
    ic = _factor_ic(100, 4, seed=12)
    full, _ = _run_c(_ic_dict(ic), list(ic))
    cut, _ = _run_c(_ic_dict({k: v[:85] for k, v in ic.items()}), list(ic))
    for name, vals in cut["rolling_centrality"].items():
        np.testing.assert_array_equal(np.asarray(vals), np.asarray(full["rolling_centrality"][name][: len(vals)]))


def test_factor_centrality_fallback_matches_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    """PCA 例外 ⇒ 相關係數退回路徑（factor_centrality_analyzer.py:97-127；全部窗亦退回）：逐欄 == 參考實作（含對角線之
    |Spearman| 平均＝產品現行公式），欄位集合 == MODULE_FIELDS 之 centrality 部分＋MODULE_FIELDS_FALLBACK。"""

    class _Boom:
        def __init__(self, *a: Any, **k: Any) -> None:
            raise np.linalg.LinAlgError("forced")

    monkeypatch.setattr(fca_mod, "PCA", _Boom)
    ic = _factor_ic(80, 4, seed=13)
    rolling_ic = _ic_dict(ic)
    prod, cfg = _run_c(rolling_ic, list(ic))
    assert prod["pca_summary"].get("fallback") == "correlation_based"
    _assert_all_consistent(compare_factor_centrality(prod, rolling_ic, list(ic), cfg))
    exp_paths = {k for k in MODULE_FIELDS if k.startswith("factor_centrality/")} | set(MODULE_FIELDS_FALLBACK)
    assert _paths(prod, "factor_centrality") == exp_paths


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：退回路徑之中心性含自身相關 1（對角線），3 特徵時下限 1/3 ≥ "
                                       f"門檻 0.3 ⇒ 全部判擁擠；收據 {RECEIPT}")
def test_fallback_centrality_excludes_self_correlation(monkeypatch: pytest.MonkeyPatch) -> None:
    """業界之平均絕對相關不含自身：3 個近乎獨立之特徵，退回路徑之中心性應 == 對其他特徵之 |Spearman| 平均（且不全判擁擠）。"""

    class _Boom:
        def __init__(self, *a: Any, **k: Any) -> None:
            raise np.linalg.LinAlgError("forced")

    monkeypatch.setattr(fca_mod, "PCA", _Boom)
    rng = np.random.default_rng(14)
    cols = {f"f{j}": 0.1 * rng.standard_normal(80) for j in range(3)}
    prod, cfg = _run_c(_ic_dict(cols), list(cols))
    names, mat, _ = ref_ic_matrix(_ic_dict(cols), list(cols))
    exp = _ref_centrality_fallback(_ref_normalize(mat), names, 0.3, exclude_self=True)
    for n in names:
        assert _rel(prod["features"][n]["centrality"], exp["features"][n]["centrality"]) <= REL_TOL
    assert prod["crowded_features"] == exp["crowded_features"]


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：effective_rank 只以保留之前 k（≤ n_components）個特徵值計參與率，"
                                       f"非 IC 矩陣之有效秩（恆 ≤ k）；收據 {RECEIPT}")
def test_effective_rank_uses_all_eigenvalues() -> None:
    """有效秩（參與率 (Σλ)²／Σλ²）應以相關矩陣全部特徵值計（`numpy.linalg.eigh`）；8 特徵、n_components 5。"""
    ic = _factor_ic(120, 8, seed=15, rank=3, noise=1.0)
    rolling_ic = _ic_dict(ic)
    prod, cfg = _run_c(rolling_ic, list(ic))
    res = compare_factor_centrality(prod, rolling_ic, list(ic), cfg)
    assert res["factor_centrality/pca_summary/effective_rank@all_eigen"]["verdict"] == "一致", res[
        "factor_centrality/pca_summary/effective_rank@all_eigen"]


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致（unimplemented）：features.*.trend 寫死 flat，與同模組 regimes.*.trend"
                                       f"（滾動中心性斜率）不一致；收據 {RECEIPT}")
def test_feature_trend_field_reflects_regime_trend() -> None:
    """同一特徵之 `features.*.trend` 應反映其滾動中心性之趨勢（== `regimes.*.trend`）；明列輸入中心性隨時間變化。"""
    n = 200
    t = np.arange(n) / n
    rng = np.random.default_rng(16)
    common = rng.standard_normal(n)
    cols = {"a": 0.1 * (t * common + 0.3 * rng.standard_normal(n)), "b": 0.1 * (t * common + 0.3 * rng.standard_normal(n)),
            "c": 0.1 * rng.standard_normal(n), "d": 0.1 * rng.standard_normal(n)}
    rolling_ic = _ic_dict(cols)
    prod, cfg = _run_c(rolling_ic, list(cols))
    assert any(r["trend"] in ("rising", "falling") for r in prod["regimes"].values())
    res = compare_factor_centrality(prod, rolling_ic, list(cols), cfg)
    assert res["factor_centrality/features/*/trend@regimes"]["verdict"] == "一致", res[
        "factor_centrality/features/*/trend@regimes"]


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：regimes 趨勢以 np.polyfit 斜率之正負判定，常數序列之斜率為捨入"
                                       f"殘值（約 1e-18）⇒ 報 rising／falling 而非 flat；收據 {RECEIPT}")
@pytest.mark.parametrize("value", [0.1, 0.3])
def test_detect_crowding_regime_constant_series_is_flat(value: float) -> None:
    """常數之滾動中心性無趨勢：regime 趨勢應為 flat（oracle：常數序列斜率依定義為 0）。"""
    rolling = pd.DataFrame({"a": [value] * 50})
    got = FactorCentralityAnalyzer(_cfg_c()).detect_crowding_regime(rolling, "a")
    assert got["trend"] == ref_regime({"a": [value] * 50}, "a", 0.3)["trend"] == "flat"


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：特徵數多（n < 10p 且 max(n,p) > 500）時 sklearn PCA "
                                       f"svd_solver='auto' 走 randomized 而 random_state=None ⇒ 中心性非精確且每次執行不同；"
                                       f"收據 {RECEIPT}")
def test_centrality_exact_and_reproducible_with_many_features() -> None:
    """600 列 × 70 特徵（randomized 求解條件）：中心性須 == 精確特徵分解（numpy.linalg.eigh，≤ 1e-12），且兩次執行相同。"""
    ic = _factor_ic(600, 70, seed=17, rank=3)
    an = FactorCentralityAnalyzer(_cfg_c())
    mat = pd.DataFrame(ic)
    state = np.random.get_state()
    try:
        np.random.seed(0)
        a = an.compute_centrality(mat)
        np.random.seed(1)
        b = an.compute_centrality(mat)
    finally:
        np.random.set_state(state)
    ref = ref_centrality(mat.to_numpy(), list(mat.columns), _cfg_c())
    for n in mat.columns:
        assert a["features"][n]["centrality"] == b["features"][n]["centrality"], f"{n}：兩次執行不同"
        assert _rel(a["features"][n]["centrality"], ref["features"][n]["centrality"]) <= REL_TOL


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：滾動中心性略過之窗不留位置、輸出無時間戳（位置索引經 to_dict "
                                       f"丟棄）⇒ 序列與滾動 IC 之時間軸錯位；收據 {RECEIPT}")
def test_rolling_centrality_keeps_time_axis_when_windows_skipped() -> None:
    """每一窗終點應有一值（略過之窗為 NaN），長度 == 列數 − 窗長 + 1：c 欄前 70 列全 NaN ⇒ 前段窗只 2 欄而略過。"""
    ic = _factor_ic(120, 3, seed=18)
    ic["f02"] = np.where(np.arange(120) < 70, math.nan, ic["f02"])
    prod, cfg = _run_c(_ic_dict(ic), list(ic))
    w = min(cfg["rolling_window"], 120)
    assert all(len(v) == 120 - w + 1 for v in prod["rolling_centrality"].values()), {
        k: len(v) for k, v in prod["rolling_centrality"].items()}


# ── 秒級：trend_analysis ──────────────────────────────────────────────────────────────────────────────


def _trend_series(kind: str, n: int = 120, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    if kind == "up":
        return 0.001 * t + 0.01 * rng.standard_normal(n)
    if kind == "down":
        return -0.001 * t + 0.01 * rng.standard_normal(n)
    if kind == "noise":
        return 0.05 * rng.standard_normal(n)
    if kind == "outliers":
        y = 0.0005 * t + 0.01 * rng.standard_normal(n)
        y[[5, 50, 99]] = [2.0, -3.0, 5.0]
        return y
    if kind == "constant":
        return np.full(n, 0.07)
    if kind == "winsor_collapse":
        return np.r_[np.zeros(199), 1.0]
    if kind == "with_inf":
        return np.r_[np.linspace(0.0, 1.0, 30), math.inf]
    if kind == "short":
        return 0.01 * rng.standard_normal(19)
    if kind == "nan_mid":
        y = 0.001 * t + 0.01 * rng.standard_normal(n)
        y[40:60] = math.nan
        return y
    raise KeyError(kind)


_T_KINDS = ["up", "down", "noise", "outliers", "constant", "winsor_collapse", "with_inf", "short", "nan_mid"]


def test_trend_analysis_matches_oracle() -> None:
    """明列邊界（顯著上升／下降、雜訊、離群值截尾、常數、截尾後常數、含 inf、樣本不足、中段 NaN）經呼叫端：逐欄 == oracle
    （statsmodels OLS 斜率／p、pearsonr² 、規則表）；selected 外之特徵與非 dict 值不入。"""
    rolling_ic = {k: {"window_21": [float(v) for v in _trend_series(k, seed=i)]} for i, k in enumerate(_T_KINDS)}
    rolling_ic["not_selected"] = {"window_21": [0.1] * 30}
    rolling_ic["not_dict"] = [0.1] * 30  # type: ignore[assignment]
    sel = _T_KINDS + ["not_dict"]
    prod, cfg = _run_t(rolling_ic, sel)
    res = compare_trend_analysis(prod, rolling_ic, sel, cfg)
    _assert_all_consistent(res)
    assert prod["up"]["ic_trend"]["trend"] == "up" and prod["down"]["ic_trend"]["trend"] == "down"
    assert prod["down"]["combined_signal"]["recommendation"] == "警告"
    assert prod["with_inf"]["ic_trend"]["trend"] == "indeterminate" and "ic_trend" not in prod["short"]
    assert set(prod) == set(_T_KINDS)


def test_trend_skip_when_matrix_empty() -> None:
    """矩陣空（無 selected 內之 dict 值）⇒ 呼叫端拋 InsufficientDataError（ic_filter_orchestrator.py:3019-3020）。"""
    for rolling_ic, sel in [({}, ["a"]), ({"a": {"window_21": [0.1] * 30}}, ["b"]), ({"a": {}}, ["a"])]:
        prod, cfg = _run_t(rolling_ic, sel)
        res = compare_trend_analysis(prod, rolling_ic, sel, cfg)
        assert res["trend_analysis（略過）"]["verdict"] == "一致", res


@pytest.mark.parametrize("ic_kind", ["up", "down", "constant"])
@pytest.mark.parametrize("cen_kind", ["up", "down", "constant", None])
@pytest.mark.parametrize("half_life", [None, 3.0, 10.0, math.nan])
def test_trend_multi_dimension_and_combined_signal(ic_kind: str, cen_kind: Optional[str], half_life: Optional[float]) -> None:
    """`analyze_multi_dimension`（四維與 half_life 規則；呼叫端現只傳 IC 維）：各維 == ref_trend_series、combined_signal
    == 規則表（trend_analyzer.py:73-117、:170-210）。"""
    cfg = _cfg_t()
    an = TrendAnalyzer(cfg)
    ic = pd.Series(_trend_series(ic_kind, seed=1))
    cen = pd.Series(_trend_series(cen_kind, seed=2)) if cen_kind else None
    fr = pd.Series(_trend_series("up", seed=3))
    ls = pd.Series(_trend_series("short", seed=4))
    got = an.analyze_multi_dimension("x", rolling_ic=ic, rolling_centrality=cen, factor_return_cumulative=fr,
                                     ls_spread_series=ls, ic_decay_half_life=half_life)["x"]
    exp_ic = ref_trend_series(ic.to_numpy(), cfg)
    exp_cen = ref_trend_series(cen.to_numpy(), cfg) if cen is not None else None
    exp_fr = ref_trend_series(fr.to_numpy(), cfg)
    exp = {"ic_trend": exp_ic, "factor_return_trend": exp_fr}
    if exp_cen is not None:
        exp["centrality_trend"] = exp_cen
    exp["combined_signal"] = ref_combined_signal(exp_ic["trend"], exp_cen["trend"] if exp_cen else None, half_life)
    assert set(got) == set(exp), (set(got), set(exp))
    for dim in ("ic_trend", "factor_return_trend", "centrality_trend"):
        if dim not in exp:
            continue
        for k in ("slope", "r_squared", "tail_estimate"):
            assert _rel(got[dim][k], exp[dim][k]) <= REL_TOL, f"{dim}/{k}: {got[dim][k]} vs {exp[dim][k]}"
        assert _p_consistent(got[dim]["p_value"], exp[dim]["p_value"], exp[dim].get("_t_abs", math.nan),
                              exp[dim].get("_df", math.nan))[0], (
            f"{dim}/p_value: {got[dim]['p_value']} vs {exp[dim]['p_value']}")
        assert got[dim]["trend"] == exp[dim]["trend"] and got[dim]["interpretation"] == exp[dim]["interpretation"]
    assert got["combined_signal"] == exp["combined_signal"]


def _overlap_ma(n: int, w: int, seed: int) -> np.ndarray:
    """重疊窗統計量之明列代理：iid 雜訊之 w 期移動平均（相鄰值共用 w−1 個觀測，同滾動 IC 之重疊結構）。"""
    e = np.random.default_rng(seed).standard_normal(n + w - 1)
    return np.convolve(e, np.ones(w) / w, mode="valid")


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：趨勢斜率 p 值以 iid OLS 處理重疊窗之滾動 IC（相鄰值共用 w−1 個"
                                       f"觀測），未用 HAC（Newey–West）⇒ p 值嚴重偏小；收據 {RECEIPT}")
def test_trend_p_value_uses_hac_for_overlapping_windows() -> None:
    """重疊窗（w＝100）之移動平均序列：產品 p 值應 == statsmodels HAC（Bartlett、maxlags＝max(自動, w−1)）之 p 值。"""
    cols = {f"s{i}": _overlap_ma(1500, 100, seed=20 + i) for i in range(3)}
    rolling_ic = {k: {"window_100": [float(x) for x in v]} for k, v in cols.items()}
    prod, cfg = _run_t(rolling_ic, list(cols))
    res = compare_trend_analysis(prod, rolling_ic, list(cols), cfg)
    _assert_all_consistent(res)
    assert res["trend_analysis/*/ic_trend/p_value@hac"]["verdict"] == "一致", res["trend_analysis/*/ic_trend/p_value@hac"]


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：趨勢迴歸之自變數為去 NaN 後重編之 0..n−1（滾動 IC 經 "
                                       f"_extract_rolling_ic_series 丟時間戳），中段缺值時壓縮時間軸 ⇒ 斜率與尾端估計偏誤；"
                                       f"收據 {RECEIPT}")
def test_trend_slope_uses_time_position_across_nan_gap() -> None:
    """中段 20 根 NaN：斜率應 == 以原時間位置為自變數之 OLS 斜率（statsmodels，去 NaN 列但保留原位置）。"""
    y = _trend_series("nan_mid", n=120, seed=21)
    rolling_ic = {k: {"window_21": [float(v) for v in y]} for k in ("a",)}
    prod, cfg = _run_t(rolling_ic, ["a"])
    pos = np.flatnonzero(~np.isnan(y)).astype(float)
    yw = _ref_winsorize(y[~np.isnan(y)])
    fit = sm.OLS(yw, sm.add_constant(pos)).fit()
    assert _rel(prod["a"]["ic_trend"]["slope"], float(fit.params[1])) <= REL_TOL


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致（unimplemented）：trend_analysis.dimensions 預設含 centrality、"
                                       f"factor_return、ls_spread，呼叫端只傳 IC 維（未接滾動中心性與 half_life）⇒ "
                                       f"combined_signal 之擁擠／半衰期規則恆不觸發；收據 {RECEIPT}")
def test_trend_analysis_honors_configured_dimensions() -> None:
    """設定 `dimensions` 含 "centrality"（ic_config_schema.py:252-254）⇒ 每特徵輸出應含 `centrality_trend`。"""
    ic = _factor_ic(150, 4, seed=22)
    prod, _ = _run_t(_ic_dict(ic), list(ic))
    assert "centrality" in TrendAnalysisConfig().dimensions
    assert all("centrality_trend" in v for v in prod.values()), {k: sorted(v) for k, v in prod.items()}


# ── 真實 kline（requires_kline）────────────────────────────────────────────────────────────────────────


def _load_kline(symbol: str, rows: int) -> pd.DataFrame:
    import h5py

    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        data = f[f"{symbol}/1h/data"][-rows:]
    idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True)
    return pd.DataFrame({"close": data["close"].astype("float64"), "volume": data["volume"].astype("float64")}, index=idx)


def _real_features(k: pd.DataFrame, wide: bool = False) -> pd.DataFrame:
    """真實 kline 上之因果特徵（只用 0..t）。wide ⇒ 2..79 根動量／均線偏離／波動率之前 240 欄（randomized 求解條件）。"""
    close, volume = k["close"], k["volume"]
    ret = close.pct_change()
    if wide:
        cols: Dict[str, pd.Series] = {}
        for w in range(2, 80):
            cols[f"mom{w}"] = close / close.shift(w) - 1.0
            cols[f"dev{w}"] = close / close.rolling(w).mean() - 1.0
            cols[f"vol{w}"] = ret.rolling(w).std()
        return pd.DataFrame(cols).iloc[:, :240]
    return pd.DataFrame({
        "ret1": ret, "dev20": close / close.rolling(20).mean() - 1.0, "vol20": ret.rolling(20).std(),
        "mom10": close / close.shift(10) - 1.0, "mom50": close / close.shift(50) - 1.0,
        "dev100": close / close.rolling(100).mean() - 1.0, "vchg": volume.pct_change(5),
    })


@lru_cache(maxsize=None)
def _real_case(symbol: str, wide: bool = False) -> Tuple[dict, Tuple[str, ...], pd.DatetimeIndex]:
    """真實 1h 末 REAL_ROWS 根：特徵＋前瞻 1 根簡單報酬標籤（label_generator.py:45-47），剔除任一欄非有限之列後，以
    `ICEngine({"timeframe": "1h"}).compute_rolling_ic`（Spearman、預設窗 21／63／126 經 12h→1h 調整為 252／756／1512、
    stride 1）建滾動 IC。回 (rolling_ic, 特徵名, 有效列時間索引)。"""
    k = _load_kline(symbol, REAL_ROWS)
    feats = _real_features(k, wide=wide)
    label = (k["close"].shift(-1) / k["close"] - 1.0).rename("label")
    ok = np.isfinite(feats.to_numpy()).all(axis=1) & np.isfinite(label.to_numpy())
    feats, label = feats[ok], label[ok]
    rolling = ICEngine({"timeframe": "1h"}).compute_rolling_ic(feats, label, [21, 63, 126], 1, "spearman")
    return rolling, tuple(feats.columns), feats.index


def _real(symbol: str, wide: bool = False) -> Tuple[dict, List[str], pd.DatetimeIndex]:
    rolling, names, idx = _real_case(symbol, wide)
    return copy.deepcopy(rolling), list(names), idx


@pytest.mark.requires_kline
def test_centrality_trend_fields_closed() -> None:
    """真實 BTCUSDT 1h：產品兩模組實際輸出之欄位路徑集合 == MODULE_FIELDS 鍵集合（封閉）；每欄之 oracle 與產生處非空。"""
    rolling_ic, names, _ = _real("BTCUSDT")
    cfg = _config(centrality={"crowded_threshold": 0.14})
    got = _paths(run_factor_centrality(rolling_ic, names, cfg), "factor_centrality") | _paths(
        run_trend_analysis(rolling_ic, names, cfg), "trend_analysis")
    assert got == set(MODULE_FIELDS), (sorted(got - set(MODULE_FIELDS)), sorted(set(MODULE_FIELDS) - got))
    assert all(v["oracle"] and v["producer"] for v in {**MODULE_FIELDS, **MODULE_FIELDS_FALLBACK}.values())


@pytest.mark.requires_kline
def test_factor_centrality_matches_oracle_on_real_kline() -> None:
    """真實 BTCUSDT 1h（7 特徵、窗 252 之滾動 IC 2,249 點）：預設門檻 0.3 與 0.14 兩設定逐欄 == oracle；資料充足——每一浮點欄
    至少一有限值、擁擠／非擁擠與 regime 之 crowded／normal、趨勢 rising／falling 皆出現。"""
    rolling_ic, names, _ = _real("BTCUSDT")
    finite: Dict[str, int] = {}
    seen: Dict[str, set] = {"crowded": set(), "regime": set(), "trend": set()}
    for thr in (0.3, 0.14):
        prod, cfg = _run_c(rolling_ic, names, crowded_threshold=thr)
        res = compare_factor_centrality(prod, rolling_ic, names, cfg)
        _assert_all_consistent(res)
        for k, v in res.items():
            finite[k] = finite.get(k, 0) + v["n_finite"]
        seen["crowded"] |= {v["crowded"] for v in prod["features"].values()}
        seen["regime"] |= {v["regime"] for v in prod["regimes"].values()}
        seen["trend"] |= {v["trend"] for v in prod["regimes"].values()}
    missing = [p for p in MODULE_FIELDS if p.startswith("factor_centrality/") and p in NUMERIC_PATHS and not finite.get(p)]
    assert not missing, f"無有限值之欄：{missing}"
    assert seen["crowded"] == {True, False}, seen
    assert {"crowded", "normal"} <= seen["regime"] and {"rising", "falling"} <= seen["trend"], seen


@pytest.mark.requires_kline
def test_rangeindex_has_no_numeric_effect_on_real_kline() -> None:
    """盤點待證（SPEC 第 127 行）之 centrality 部分：呼叫端以位置（RangeIndex）對齊各特徵之滾動 IC；同請求各特徵之窗終點
    相同（共用時間軸），故位置矩陣 == 以窗終點時間戳對齊之矩陣，且兩者算得之中心性相同 ⇒ 數值無影響（時間戳之喪失見
    `test_rolling_centrality_keeps_time_axis_when_windows_skipped`）。"""
    rolling_ic, names, idx = _real("BTCUSDT")
    _, pos_mat, keys = ref_ic_matrix(rolling_ic, names)
    w = int(str(keys[0]).rsplit("_", 1)[1])
    timed = pd.DataFrame({n: pd.Series(rolling_ic[n][keys[j]], index=idx[w - 1:]) for j, n in enumerate(names)})
    np.testing.assert_array_equal(timed.to_numpy(), pos_mat)
    an = FactorCentralityAnalyzer(_cfg_c())
    a = an.compute_centrality(timed)
    b = an.compute_centrality(pd.DataFrame(pos_mat, columns=names))
    assert a["features"] == b["features"]


@pytest.mark.requires_kline
def test_rolling_centrality_prefix_invariant_on_real_kline() -> None:
    """防偷看未來（真實）：滾動 IC 截去末 200 點後，前段之逐窗中心性不變（只取前 500 點以控耗時）。"""
    rolling_ic, names, _ = _real("BTCUSDT")
    head = {n: {"window_252": rolling_ic[n]["window_252"][:500]} for n in names}
    cut = {n: {"window_252": rolling_ic[n]["window_252"][:300]} for n in names}
    full, _ = _run_c(head, names)
    part, _ = _run_c(cut, names)
    for n, vals in part["rolling_centrality"].items():
        np.testing.assert_array_equal(np.asarray(vals), np.asarray(full["rolling_centrality"][n][: len(vals)]))


@pytest.mark.requires_kline
def test_trend_analysis_matches_oracle_on_real_kline() -> None:
    """真實 BTCUSDT 與 ETHUSDT 1h：逐欄 == oracle（statsmodels OLS／pearsonr²／規則表）；資料充足——每一浮點欄至少一有限值，
    趨勢 up／down／flat 與建議 正常／警告 皆出現。"""
    finite: Dict[str, int] = {}
    trends, recs = set(), set()
    for sym in ("BTCUSDT", "ETHUSDT"):
        rolling_ic, names, _ = _real(sym)
        prod, cfg = _run_t(rolling_ic, names)
        res = compare_trend_analysis(prod, rolling_ic, names, cfg)
        _assert_all_consistent(res)
        for k, v in res.items():
            finite[k] = finite.get(k, 0) + v["n_finite"]
        trends |= {v["ic_trend"]["trend"] for v in prod.values()}
        recs |= {v["combined_signal"]["recommendation"] for v in prod.values()}
    missing = [p for p in MODULE_FIELDS if p.startswith("trend_analysis/") and p in NUMERIC_PATHS and not finite.get(p)]
    assert not missing, f"無有限值之欄：{missing}"
    assert {"up", "down", "flat"} <= trends and {"正常", "警告"} <= recs, (trends, recs)


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：趨勢 p 值以 iid OLS 處理重疊窗滾動 IC，真實 BNBUSDT dev20 iid p "
                                       f"≈ 7e-73 判 down，HAC p ≈ 0.095 應判 flat；收據 {RECEIPT}")
def test_trend_p_value_hac_on_real_kline() -> None:
    """真實 BNBUSDT 1h：產品之趨勢判定與 p 值應 == HAC（Bartlett、maxlags＝max(自動, 251)）之結果。"""
    rolling_ic, names, _ = _real("BNBUSDT")
    prod, cfg = _run_t(rolling_ic, names)
    res = compare_trend_analysis(prod, rolling_ic, names, cfg)
    assert res["trend_analysis/*/ic_trend/trend@hac"]["verdict"] == "一致", res["trend_analysis/*/ic_trend/trend@hac"]
    assert res["trend_analysis/*/ic_trend/p_value@hac"]["verdict"] == "一致", res["trend_analysis/*/ic_trend/p_value@hac"]


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：effective_rank 只計保留之前 k 個特徵值（真實 BTCUSDT 7 特徵："
                                       f"3.753 vs 全部特徵值 3.930）；收據 {RECEIPT}")
def test_effective_rank_all_eigen_on_real_kline() -> None:
    rolling_ic, names, _ = _real("BTCUSDT")
    prod, cfg = _run_c(rolling_ic, names)
    res = compare_factor_centrality(prod, rolling_ic, names, cfg)
    assert res["factor_centrality/pca_summary/effective_rank@all_eigen"]["verdict"] == "一致", res[
        "factor_centrality/pca_summary/effective_rank@all_eigen"]


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致（unimplemented）：features.*.trend 寫死 flat，真實 BTCUSDT 之 "
                                       f"regimes.*.trend 為 rising／falling；收據 {RECEIPT}")
def test_feature_trend_reflects_rolling_centrality_on_real_kline() -> None:
    rolling_ic, names, _ = _real("BTCUSDT")
    prod, cfg = _run_c(rolling_ic, names)
    res = compare_factor_centrality(prod, rolling_ic, names, cfg)
    assert res["factor_centrality/features/*/trend@regimes"]["verdict"] == "一致", res[
        "factor_centrality/features/*/trend@regimes"]


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：真實 BTCUSDT 234 特徵時 PCA 走 randomized（random_state=None）"
                                       f"⇒ 中心性與精確特徵分解差約 1e-9、兩次執行不同；收據 {RECEIPT}")
def test_centrality_exact_and_reproducible_wide_on_real_kline() -> None:
    rolling_ic, names, _ = _real("BTCUSDT", wide=True)
    _, mat, _ = ref_ic_matrix(rolling_ic, names)
    an = FactorCentralityAnalyzer(_cfg_c())
    frame = pd.DataFrame(mat, columns=names)
    state = np.random.get_state()
    try:
        np.random.seed(0)
        a = an.compute_centrality(frame)
        np.random.seed(1)
        b = an.compute_centrality(frame)
    finally:
        np.random.set_state(state)
    ref = ref_centrality(mat, names, _cfg_c())
    assert set(a["features"]) == set(ref["features"])
    for n in a["features"]:
        assert a["features"][n]["centrality"] == b["features"][n]["centrality"], f"{n}：兩次執行不同"
        assert _rel(a["features"][n]["centrality"], ref["features"][n]["centrality"]) <= REL_TOL
