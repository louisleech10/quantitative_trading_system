"""ICPERF Task 0.3 深度分析 oracle 測試——組 sensitivity_oos（docs/ICPERF_SPEC.md Task 0.3／0.4，第 108、109、123–127 行）。

被測模組（深度報告 `results.<模組鍵>`）：
- `parameter_sensitivity`：`momentum/Analysis/parameter_sensitivity_analyzer.py` `ParameterSensitivityAnalyzer.batch_analyze`
  （呼叫端 `momentum/Analysis/ic_filter_orchestrator.py:3026-3033` `_run_parameter_sensitivity`：全段 `features_df`、
  全段 `label_series`、請求之 `metadata`）。
- `rolling_oos`：`momentum/Analysis/rolling_oos_validator.py` `RollingOOSValidator.validate_batch`（呼叫端
  `ic_filter_orchestrator.py:3035-3041` `_run_rolling_oos`：`top_n=len(selected)`、不傳 `method` ⇒ 恆 spearman）。

本檔為**稽核**：參考實作 `ref_parameter_sensitivity`／`ref_rolling_oos` 以 numpy／scipy（Spearman＝`scipy.stats.rankdata`
平均秩後 `numpy.corrcoef`；Pearson＝`numpy.corrcoef`；Kendall＝`scipy.stats.kendalltau`）依產品公式（逐式註明 檔:行）
獨立重算，不呼叫被測模組；不一致項以 `xfail(strict=True)` 斷言正確（oracle）行為，不修產品碼。

- 秒級（不標 requires_kline）：明列邊界輸入（空、單特徵、常數、含 NaN、含 ±inf、樣本不足、全 NaN IC、metadata 分組、
  步長減半、門檻邊界、top_n 截斷）。
- 真實資料（`requires_kline`）：`data_cache/feature_klines/kline_cache.h5` 之 BTCUSDT 1h 末 2,000 根上之因果特徵
  （只用 0..t）與前瞻報酬標籤 close[t+h]／close[t]−1（`label_generator.py:45-47`）；須經共用監看執行（autouse 自證）。
"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from momentum.Analysis.ic_config_schema import ParameterSensitivityConfig, RollingOOSConfig
from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer
from momentum.Analysis.rolling_oos_validator import RollingOOSValidator

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
#: SPEC Task 0.3「驗證」：浮點對照之相對誤差門檻
REL_TOL = 1e-12
HEAVY_MARKERS = ("slow", "requires_kline")
NON_STAT = "非統計欄"
RECEIPT = "handoffs/run_receipts/20261029-icperf-correctness.json"
PS = "momentum/Analysis/parameter_sensitivity_analyzer.py"
OOS = "momentum/Analysis/rolling_oos_validator.py"
#: 逐實體（特徵名／家族名）之 dict 層：其子鍵於欄位路徑寫 `*`
ENTITY_PARENTS = ("families", "features")
#: 真實資料長度（rolling_oos 預設 train 252＋test 63 ⇒ 每特徵約 80 個切分）
REAL_ROWS = 2000


# ── 共用監看（同 tests/momentum/Analysis/test_icperf_correctness.py） ─────────────────────────────────────


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
    """相對誤差（兩者皆 NaN 或相等〔含同號 inf〕⇒ 0；一方 NaN ⇒ inf；b 為 0 ⇒ 絕對誤差）。"""
    if math.isnan(a) and math.isnan(b):
        return 0.0
    if math.isnan(a) or math.isnan(b):
        return math.inf
    if a == b:
        return 0.0
    return abs(a - b) / abs(b) if b != 0 else abs(a - b)


# ── 欄位清冊（results.<模組鍵> 之每一欄位路徑；以 `test_sensitivity_oos_fields_closed` 對實際輸出鍵封閉） ────────

MODULE_FIELDS: Dict[str, Dict[str, str]] = {
    # parameter_sensitivity（batch_analyze 回傳 :175-180；家族 analyze_from_variants 回傳 :104-114）
    "parameter_sensitivity/families/*/variants": {"oracle": NON_STAT, "producer": f"{PS}:105"},
    "parameter_sensitivity/families/*/param_axis": {"oracle": NON_STAT, "producer": f"{PS}:106"},
    "parameter_sensitivity/families/*/sensitivity_table/#/variant": {"oracle": NON_STAT, "producer": f"{PS}:78"},
    "parameter_sensitivity/families/*/sensitivity_table/#/param_value": {"oracle": NON_STAT, "producer": f"{PS}:79"},
    "parameter_sensitivity/families/*/sensitivity_table/#/ic_mean": {"oracle": "ps.point_spearman_ic",
                                                                     "producer": f"{PS}:80"},
    "parameter_sensitivity/families/*/sensitivity_table/#/icir": {"oracle": "ps.icir_proxy", "producer": f"{PS}:81"},
    "parameter_sensitivity/families/*/stability_metrics/ic_std_across_params": {"oracle": "ps.std_across_params",
                                                                               "producer": f"{PS}:101"},
    "parameter_sensitivity/families/*/stability_metrics/icir_std_across_params": {"oracle": "ps.std_across_params",
                                                                                 "producer": f"{PS}:102"},
    "parameter_sensitivity/families/*/stability_metrics/overfitting_risk": {"oracle": "ps.risk_class",
                                                                           "producer": f"{PS}:111"},
    "parameter_sensitivity/families/*/stability_metrics/best_param": {"oracle": "ps.best_param",
                                                                     "producer": f"{PS}:100"},
    "parameter_sensitivity/summary/total_families": {"oracle": NON_STAT, "producer": f"{PS}:166"},
    "parameter_sensitivity/summary/high_risk_count": {"oracle": "ps.risk_class", "producer": f"{PS}:167"},
    "parameter_sensitivity/summary/robust_count": {"oracle": "ps.risk_class", "producer": f"{PS}:168"},
    "parameter_sensitivity/high_risk_families": {"oracle": "ps.risk_class", "producer": f"{PS}:178"},
    "parameter_sensitivity/robust_families": {"oracle": "ps.risk_class", "producer": f"{PS}:179"},
    # rolling_oos（validate_batch 回傳 :147-161；逐特徵 validate 回傳 :106-110；跳過 :130-134）
    "rolling_oos/config/train_window": {"oracle": NON_STAT, "producer": f"{OOS}:149"},
    "rolling_oos/config/test_window": {"oracle": NON_STAT, "producer": f"{OOS}:150"},
    "rolling_oos/config/step": {"oracle": NON_STAT, "producer": f"{OOS}:151"},
    "rolling_oos/config/n_splits": {"oracle": "oos.splits", "producer": f"{OOS}:152"},
    "rolling_oos/features/*/skipped": {"oracle": NON_STAT, "producer": f"{OOS}:131"},
    "rolling_oos/features/*/reason": {"oracle": NON_STAT, "producer": f"{OOS}:132"},
    "rolling_oos/features/*/error_type": {"oracle": NON_STAT, "producer": f"{OOS}:133"},
    "rolling_oos/features/*/oos_stability/mean_oos_ic": {"oracle": "oos.split_ic_stats", "producer": f"{OOS}:93"},
    "rolling_oos/features/*/oos_stability/std_oos_ic": {"oracle": "oos.split_ic_stats", "producer": f"{OOS}:94"},
    "rolling_oos/features/*/oos_stability/oos_hit_rate": {"oracle": "oos.split_ic_stats", "producer": f"{OOS}:95"},
    "rolling_oos/features/*/oos_stability/mean_is_oos_gap": {"oracle": "oos.split_ic_stats", "producer": f"{OOS}:96"},
    "rolling_oos/features/*/oos_stability/oos_icir": {"oracle": "oos.split_ic_stats", "producer": f"{OOS}:97"},
    "rolling_oos/features/*/oos_stability/degradation_ratio": {"oracle": "oos.split_ic_stats",
                                                               "producer": f"{OOS}:88-90"},
    "rolling_oos/features/*/assessment": {"oracle": "oos.assessment", "producer": f"{OOS}:101-104"},
    "rolling_oos/features/*/splits_sampled/#/split_id": {"oracle": "oos.splits", "producer": f"{OOS}:75"},
    "rolling_oos/features/*/splits_sampled/#/is_ic": {"oracle": "oos.split_ic", "producer": f"{OOS}:68"},
    "rolling_oos/features/*/splits_sampled/#/oos_ic": {"oracle": "oos.split_ic", "producer": f"{OOS}:69"},
    "rolling_oos/summary/total_validated": {"oracle": "oos.assessment", "producer": f"{OOS}:156"},
    "rolling_oos/summary/robust_count": {"oracle": "oos.assessment", "producer": f"{OOS}:157"},
    "rolling_oos/summary/moderate_count": {"oracle": "oos.assessment", "producer": f"{OOS}:158"},
    "rolling_oos/summary/overfitting_count": {"oracle": "oos.assessment", "producer": f"{OOS}:159"},
}

#: oracle 項 id → 說明（收據 coverage 之 oracle 欄引用）
ORACLE_ITEMS: Dict[str, str] = {
    "ps.point_spearman_ic": "全段兩欄共同有效列（pd.concat→dropna）上 Spearman＝rankdata 平均秩之 numpy.corrcoef；"
                            "列數<5 或任一欄常數 ⇒ NaN（:183-190）",
    "ps.icir_proxy": "現行公式 mean(x·y)／std(x·y, ddof=1)（:193-201）重算；業界 ICIR（滾動 IC 均值／標準差）之對照見 "
                     "test_parameter_sensitivity_icir_invariant_under_monotone_transform*（xfail）",
    "ps.std_across_params": "家族內逐變體值之 std(ddof=0)、略 NaN（pandas skipna 語意，:101-102）",
    "ps.risk_class": "ic_std<low 且 icir_std<0.15 ⇒ low；ic_std<high 且 icir_std<0.3 ⇒ medium；否則 high（:116-129）；"
                     "high／low 家族名單與計數依家族順序（:156-168）",
    "ps.best_param": "有號 ic_mean 最大（NaN 視 −inf、同值取首個）之 param_value（:100、:112）；方向性之對照見 "
                     "test_parameter_sensitivity_best_param_sign_flip_invariant*（xfail）",
    "oos.splits": "固定窗切分 [s, s+train)→[s+train, s+train+test)、步長 step，切分數 < min_splits 則步長減半（至多 6 輪，"
                  ":163-186）；n_splits 以 labels.dropna() 長度產生（:152）",
    "oos.split_ic": "逐切分 IS／OOS IC：列數<5 ⇒ NaN、任一欄常數 ⇒ 0.0（現行 :190-193）；spearman＝rankdata＋numpy.corrcoef、"
                    "其餘 method＝numpy.corrcoef（:194-198）；非有限之切分略過（:70-71）；purge＝標籤 horizon h 時訓練段去末 h 根",
    "oos.split_ic_stats": "有效切分之 IS／OOS IC 陣列：mean、std(ddof=0)、mean(oos>0)、mean(is−oos)、mean/std（std≤0⇒NaN）、"
                          "(mean_is−mean_oos)/|mean_is|（mean_is=0⇒0.0）（:84-99）",
    "oos.assessment": "hit≥robust_hit 且 degr<robust_max ⇒ robust；hit≥moderate_hit 且 degr<moderate_max ⇒ moderate；否則 "
                      "overfitting（:200-205）；summary 計數（:137-159）",
}


# ── 參考實作（不呼叫被測模組） ─────────────────────────────────────────────────────────────────────────────

#: parameter_sensitivity_analyzer.py:45 之家族樣式、:205 之參數樣式
_FAMILY_RE = re.compile(r"^(.+?)_(\d+)$")
_PARAM_RE = re.compile(r"_(\d+)$")


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman＝平均秩（scipy.stats.rankdata）之 Pearson（numpy.corrcoef）。"""
    return float(np.corrcoef(stats.rankdata(x), stats.rankdata(y))[0, 1])


def _corr(x: np.ndarray, y: np.ndarray, method: str) -> float:
    if method == "spearman":
        return _spearman(x, y)
    if method == "kendall":
        return float(stats.kendalltau(x, y).statistic)
    return float(np.corrcoef(x, y)[0, 1])


def _pair(feature: pd.Series, labels: pd.Series, a: str = "x", b: str = "y") -> pd.DataFrame:
    """兩欄共同有效列（外連接後 dropna；同 :184、rolling_oos_validator.py:38）。±inf 不剔除（同產品）。"""
    return pd.concat([feature.rename(a), labels.rename(b)], axis=1).dropna()


def _ref_families(names: Sequence[str], metadata: Optional[Mapping[str, Any]]) -> Dict[str, List[str]]:
    """家族偵測（:33-54）：metadata 有 indicator 者依 `<data_source>_<indicator>` 分組（有任一組即只回此分組）；否則名稱
    `^(.+?)_(\\d+)$` 之前綴（不符者自成一族）。"""
    if metadata:
        grouped: Dict[str, List[str]] = {}
        for n in names:
            meta = metadata.get(n, {}) if isinstance(metadata, dict) else {}
            ind, src = str(meta.get("indicator", "")), str(meta.get("data_source", ""))
            if ind:
                grouped.setdefault(f"{src}_{ind}" if src else ind, []).append(n)
        if grouped:
            return grouped
    fams: Dict[str, List[str]] = {}
    for n in names:
        m = _FAMILY_RE.match(n)
        fams.setdefault(m.group(1) if m else n, []).append(n)
    return fams


def _ref_param_value(name: str) -> Any:
    m = _PARAM_RE.search(name)  # :204-208
    return int(m.group(1)) if m else name


def _ref_ps_ic(feature: pd.Series, labels: pd.Series) -> float:
    d = _pair(feature, labels)  # :183-190
    if len(d) < 5:
        return math.nan
    x, y = d["x"].to_numpy(dtype=float), d["y"].to_numpy(dtype=float)
    if np.unique(x).size <= 1 or np.unique(y).size <= 1:
        return math.nan
    v = _spearman(x, y)
    return v if math.isfinite(v) else math.nan


def _ref_ps_icir_proxy(feature: pd.Series, labels: pd.Series) -> float:
    d = _pair(feature, labels)  # :193-201
    if len(d) < 5:
        return math.nan
    p = d["x"].to_numpy(dtype=float) * d["y"].to_numpy(dtype=float)
    sd = float(np.std(p, ddof=1)) if p.size > 1 else math.nan
    if not math.isfinite(sd) or sd == 0:
        return math.nan
    return float(np.mean(p) / sd)


def ref_rolling_rank_icir(feature: pd.Series, labels: pd.Series, window: int) -> float:
    """業界 ICIR（對照用，非現行公式）：兩欄共同有效列上逐窗（長 window、步長 1、只用窗內資料）Spearman IC 序列之
    均值／標準差（ddof=0，同 `ic_engine.py:470-491` 之 ICIR 定義）；窗不足或 std≤0 ⇒ NaN。"""
    d = _pair(feature, labels)
    x, y = d["x"].to_numpy(dtype=float), d["y"].to_numpy(dtype=float)
    ics = []
    for end in range(window, len(d) + 1):
        xs, ys = x[end - window:end], y[end - window:end]
        if np.unique(xs).size > 1 and np.unique(ys).size > 1:
            ics.append(_spearman(xs, ys))
    if not ics:
        return math.nan
    arr = np.asarray(ics)
    sd = float(np.std(arr, ddof=0))
    return float(np.mean(arr) / sd) if sd > 0 else math.nan


def _nanstd0(values: Sequence[float]) -> float:
    """pandas Series.std(ddof=0) 之 skipna 語意（:101-102）：有限值 0 個 ⇒ NaN。"""
    arr = np.asarray([v for v in values if not math.isnan(v)], dtype=float)
    return float(np.std(arr, ddof=0)) if arr.size else math.nan


def _ref_risk(ic_std: float, icir_std: float, low: float, high: float) -> str:
    if ic_std < low and icir_std < 0.15:  # :116-129（icir 門檻 0.15／0.3 寫死）
        return "low"
    if ic_std < high and icir_std < 0.3:
        return "medium"
    return "high"


def ref_parameter_sensitivity(features_df: pd.DataFrame, labels: pd.Series, metadata: Optional[dict] = None,
                              config: Optional[dict] = None, *, best_by_abs: bool = False) -> Dict[str, Any]:
    """`batch_analyze` 之參考實作（設定以 `ParameterSensitivityConfig` 之 schema 預設補齊，同呼叫端 model_dump）。
    `best_by_abs=True` ⇒ best_param 改取 |ic_mean| 最大（方向中立之 oracle，供 xfail 對照）。"""
    cfg = ParameterSensitivityConfig(**(config or {})).model_dump()
    min_size = int(cfg["min_family_size"])
    low, high = float(cfg["ic_std_threshold_low"]), float(cfg["ic_std_threshold_high"])
    threshold = max(3, min_size)  # :144（batch_analyze 之 min_family_size 參數預設 3）
    fams = _ref_families(list(features_df.columns), metadata)
    out_fams: Dict[str, Any] = {}
    high_risk: List[str] = []
    robust: List[str] = []
    for fam, variants in fams.items():
        if len(variants) < threshold or len(variants) < min_size:  # :151-152、:63
            continue
        rows = []
        for v in variants:
            if v not in features_df.columns:  # :72
                continue
            rows.append({"variant": v, "param_value": _ref_param_value(v),
                         "ic_mean": _ref_ps_ic(features_df[v], labels),
                         "icir": _ref_ps_icir_proxy(features_df[v], labels)})
        if len(rows) < min_size:  # :85
            continue
        ics = [r["ic_mean"] for r in rows]
        if all(math.isnan(v) for v in ics):  # :93
            continue
        key = [(-math.inf if math.isnan(v) else (abs(v) if best_by_abs else v)) for v in ics]
        best = int(np.argmax(key))  # 同值取首個（同 idxmax）
        ic_std = _nanstd0(ics) if len(rows) > 1 else 0.0
        icir_std = _nanstd0([r["icir"] for r in rows]) if len(rows) > 1 else 0.0
        risk = _ref_risk(ic_std, icir_std, low, high)
        out_fams[fam] = {"variants": list(variants), "param_axis": "period", "sensitivity_table": rows,
                         "stability_metrics": {"ic_std_across_params": ic_std, "icir_std_across_params": icir_std,
                                               "overfitting_risk": risk, "best_param": rows[best]["param_value"]}}
        if risk == "high":
            high_risk.append(fam)
        if risk == "low":
            robust.append(fam)
    return {"families": out_fams,
            "summary": {"total_families": len(out_fams), "high_risk_count": len(high_risk),
                        "robust_count": len(robust)},
            "high_risk_families": high_risk, "robust_families": robust}


def _ref_splits(n: int, train: int, test: int, step: int, min_splits: int) -> List[Tuple[int, int, int]]:
    """切分（rolling_oos_validator.py:163-186）：(訓練起點, 訓練終點＝測試起點, 測試終點)。"""
    if n < train + test:
        return []
    splits: List[Tuple[int, int, int]] = []
    for _ in range(6):
        splits = []
        s = 0
        while s + train + test <= n:
            splits.append((s, s + train, s + train + test))
            s += step
        if len(splits) >= min_splits or step <= 1:
            break
        step = max(1, step // 2)
    return splits


def _ref_oos_ic(x: np.ndarray, y: np.ndarray, method: str, constant_ic: str) -> float:
    """逐切分 IC（:189-198）：列數<5 ⇒ NaN；任一欄常數 ⇒ `constant_ic`＝"zero"（現行 0.0）或 "nan"（scipy 語意：未定義）。"""
    if x.size < 5 or y.size < 5:
        return math.nan
    if np.unique(x).size <= 1 or np.unique(y).size <= 1:
        return 0.0 if constant_ic == "zero" else math.nan
    v = _corr(x, y, method)
    return v if math.isfinite(v) else math.nan


def _ref_assessment(hit: float, degr: float, th: Mapping[str, float]) -> str:
    if hit >= th["robust_hit_rate"] and degr < th["robust_max_degradation"]:  # :200-205
        return "robust"
    if hit >= th["moderate_hit_rate"] and degr < th["moderate_max_degradation"]:
        return "moderate"
    return "overfitting"


def _ref_split_stats(is_arr: np.ndarray, oos_arr: np.ndarray, sign_aligned: bool) -> Dict[str, float]:
    """:84-99。`sign_aligned=True` ⇒ 方向中立之 oracle（方向 d＝sign(mean_is)：hit＝mean(d·oos>0)、
    degradation＝(|mean_is|−d·mean_oos)/|mean_is|；mean_is>0 時與現行同值），供 xfail 對照。"""
    mean_is, mean_oos = float(np.mean(is_arr)), float(np.mean(oos_arr))
    d = -1.0 if (sign_aligned and mean_is < 0) else 1.0
    degr = float((d * mean_is - d * mean_oos) / abs(mean_is)) if mean_is != 0 else 0.0
    sd = float(np.std(oos_arr, ddof=0))
    return {"mean_oos_ic": mean_oos, "std_oos_ic": sd, "oos_hit_rate": float(np.mean(d * oos_arr > 0)),
            "mean_is_oos_gap": float(np.mean(is_arr - oos_arr)),
            "oos_icir": float(mean_oos / sd) if sd > 0 else math.nan, "degradation_ratio": degr}


def ref_rolling_oos(features_df: pd.DataFrame, labels: pd.Series, config: Optional[dict] = None, *,
                    top_n: Optional[int] = None, method: str = "spearman", horizon: int = 0,
                    constant_ic: str = "zero", sign_aligned: bool = False) -> Dict[str, Any]:
    """`validate_batch` 之參考實作（設定以 `RollingOOSConfig` schema 補齊）。`horizon`＝標籤前瞻根數 h：訓練段去末 h 根
    （purge，López de Prado；h=0 ⇒ 現行公式）；`top_n` None ⇒ 全部欄（同呼叫端 top_n=len(selected)）。"""
    cfg = RollingOOSConfig(**(config or {})).model_dump()
    train, test, step, min_splits = (int(cfg[k]) for k in ("train_window", "test_window", "step", "min_splits"))
    th = cfg["assessment_thresholds"]
    cols = list(features_df.columns)[: max(1, int(len(features_df.columns) if top_n is None else top_n))]
    results: Dict[str, Any] = {}
    counts = {"robust": 0, "moderate": 0, "overfitting": 0}
    ok = 0
    for name in cols:
        d = _pair(features_df[name], labels, "feature", "label")
        need = train + test
        if len(d) < need:
            results[name] = {"skipped": True, "reason": f"insufficient samples: {len(d)} < {need}",
                             "error_type": "INSUFFICIENT_DATA"}
            continue
        splits = _ref_splits(len(d), train, test, step, min_splits)
        if not splits:
            results[name] = {"skipped": True, "reason": "no valid splits generated", "error_type": "INSUFFICIENT_DATA"}
            continue
        x, y = d["feature"].to_numpy(dtype=float), d["label"].to_numpy(dtype=float)
        sampled, is_v, oos_v = [], [], []
        for sid, (a, b, c) in enumerate(splits):
            tr_end = b - int(horizon)
            is_ic = _ref_oos_ic(x[a:tr_end], y[a:tr_end], method, constant_ic) if tr_end > a else math.nan
            oos_ic = _ref_oos_ic(x[b:c], y[b:c], method, constant_ic)
            if not (math.isfinite(is_ic) and math.isfinite(oos_ic)):
                continue
            is_v.append(is_ic)
            oos_v.append(oos_ic)
            sampled.append({"split_id": sid, "is_ic": is_ic, "oos_ic": oos_ic})
        if not oos_v:
            results[name] = {"skipped": True, "reason": "all splits invalid", "error_type": "INSUFFICIENT_DATA"}
            continue
        st = _ref_split_stats(np.asarray(is_v), np.asarray(oos_v), sign_aligned)
        assess = _ref_assessment(st["oos_hit_rate"], st["degradation_ratio"], th)
        results[name] = {"oos_stability": st, "assessment": assess, "splits_sampled": sampled}
        ok += 1
        counts[assess] += 1
    return {"config": {"train_window": train, "test_window": test, "step": step,
                       "n_splits": len(_ref_splits(len(labels.dropna()), train, test, step, min_splits))},
            "features": results,
            "summary": {"total_validated": ok, "robust_count": counts["robust"], "moderate_count": counts["moderate"],
                        "overfitting_count": counts["overfitting"]}}


# ── 比對 ─────────────────────────────────────────────────────────────────────────────────────────────────


def _flatten(obj: Any, pattern: str, concrete: Tuple[Any, ...] = ()) -> List[Tuple[str, Tuple[Any, ...], Any]]:
    """(欄位路徑, 具體路徑, 葉值)：逐實體 dict 層子鍵→`*`、dict 之 list→`#`；純量 list 與空 dict 為葉。"""
    if isinstance(obj, dict) and obj:
        parent = pattern.rsplit("/", 1)[-1]
        out: List[Tuple[str, Tuple[Any, ...], Any]] = []
        for k, v in obj.items():
            seg = "*" if parent in ENTITY_PARENTS else str(k)
            out += _flatten(v, f"{pattern}/{seg}", concrete + (k,))
        return out
    if isinstance(obj, list) and obj and all(isinstance(e, dict) for e in obj):
        out = []
        for i, e in enumerate(obj):
            out += _flatten(e, f"{pattern}/#", concrete + (i,))
        return out
    return [(pattern, concrete, obj)]


def _field_keys(module_key: str, output: Mapping[str, Any]) -> set:
    return {p for p, _, _ in _flatten(dict(output), module_key)}


def _is_float(v: Any) -> bool:
    return isinstance(v, (float, np.floating))


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, (bool, np.bool_))


def _compare_trees(module_key: str, product: Mapping[str, Any], oracle: Mapping[str, Any],
                   fields: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    got: Dict[str, Dict[Tuple[Any, ...], Any]] = {}
    exp: Dict[str, Dict[Tuple[Any, ...], Any]] = {}
    for tree, sink in ((product, got), (oracle, exp)):
        for p, c, v in _flatten(dict(tree), module_key):
            sink.setdefault(p, {})[c] = v
    out: Dict[str, Dict[str, Any]] = {}
    for f in fields:
        g, e = got.get(f, {}), exp.get(f, {})
        bad: List[str] = []
        max_rel: Optional[float] = None
        n_finite = 0
        if set(g) != set(e):
            bad.append(f"具體路徑不同：產品獨有 {sorted(map(str, set(g) - set(e)))[:5]}、"
                       f"oracle 獨有 {sorted(map(str, set(e) - set(g)))[:5]}")
        for c in sorted(set(g) & set(e), key=str):
            a, b = g[c], e[c]
            if _is_float(a) or _is_float(b):
                if not (_is_num(a) and _is_num(b)):
                    bad.append(f"{c}: {a!r} vs {b!r}")
                    continue
                r = _rel(float(a), float(b))
                max_rel = r if max_rel is None else max(max_rel, r)
                n_finite += int(math.isfinite(float(a)))
                if r > REL_TOL:
                    bad.append(f"{c}: 產品 {a!r} vs oracle {b!r}（rel {r:.3e}）")
            else:
                if isinstance(a, list):
                    n_finite += len(a)
                elif a is not None:
                    n_finite += 1
                if a != b:
                    bad.append(f"{c}: 產品 {a!r} vs oracle {b!r}")
        out[f] = {"verdict": "不一致" if bad else "一致", "max_rel_diff": max_rel, "n_finite": n_finite,
                  "detail": "; ".join(bad[:5]) if bad else f"{len(g)} 值相符"}
    return out


def _stat_fields(module_key: str) -> List[str]:
    return [k for k, v in MODULE_FIELDS.items() if k.startswith(module_key + "/") and v["oracle"] != NON_STAT]


def compare_parameter_sensitivity(product_output: Mapping[str, Any], features_df: pd.DataFrame, labels: pd.Series,
                                  metadata: Optional[dict] = None, config: Optional[dict] = None,
                                  *, best_by_abs: bool = False) -> Dict[str, Dict[str, Any]]:
    """產品輸出（`results.parameter_sensitivity`）對 `ref_parameter_sensitivity` 逐統計欄比對；輸入＝呼叫端之同一組
    （`features_df[selected]`、`label_series`、`metadata`、`config.parameter_sensitivity.model_dump()`）。"""
    ref = ref_parameter_sensitivity(features_df, labels, metadata, config, best_by_abs=best_by_abs)
    return _compare_trees("parameter_sensitivity", product_output, ref, _stat_fields("parameter_sensitivity"))


def compare_rolling_oos(product_output: Mapping[str, Any], features_df: pd.DataFrame, labels: pd.Series,
                        config: Optional[dict] = None, *, horizon: int, top_n: Optional[int] = None,
                        method: str = "spearman", constant_ic: str = "zero",
                        sign_aligned: bool = False) -> Dict[str, Dict[str, Any]]:
    """產品輸出（`results.rolling_oos`）對 `ref_rolling_oos` 逐統計欄比對。`horizon` 必填：正確性判定須傳標籤之前瞻根數
    （purge ≥ h）；`horizon=0` 只驗現行公式之重算（不含 purge）。"""
    ref = ref_rolling_oos(features_df, labels, config, top_n=top_n, method=method, horizon=horizon,
                          constant_ic=constant_ic, sign_aligned=sign_aligned)
    return _compare_trees("rolling_oos", product_output, ref, _stat_fields("rolling_oos"))


def _assert_all_consistent(res: Mapping[str, Mapping[str, Any]]) -> None:
    bad = {k: v["detail"] for k, v in res.items() if v["verdict"] != "一致"}
    assert not bad, f"不一致：{bad}"


def _assert_non_stat_equal(module_key: str, product: Mapping[str, Any], oracle: Mapping[str, Any]) -> None:
    fields = [k for k, v in MODULE_FIELDS.items() if k.startswith(module_key + "/") and v["oracle"] == NON_STAT]
    _assert_all_consistent(_compare_trees(module_key, product, oracle, fields))


# ── 產品呼叫（同呼叫端：設定經 schema model_dump） ─────────────────────────────────────────────────────────


def _run_ps(df: pd.DataFrame, labels: pd.Series, metadata: Optional[dict] = None,
            config: Optional[dict] = None) -> Dict[str, Any]:
    cfg = ParameterSensitivityConfig(**(config or {})).model_dump()
    return ParameterSensitivityAnalyzer(cfg).batch_analyze(df, labels, metadata=metadata)


def _run_oos(df: pd.DataFrame, labels: pd.Series, config: Optional[dict] = None, *, top_n: Optional[int] = None,
             method: Optional[str] = None) -> Dict[str, Any]:
    cfg = RollingOOSConfig(**(config or {})).model_dump()
    kw = {} if method is None else {"method": method}
    return RollingOOSValidator(cfg).validate_batch(df, labels, top_n=len(df.columns) if top_n is None else top_n, **kw)


# ── 明列邊界輸入 ───────────────────────────────────────────────────────────────────────────────────────


def _idx(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")


def _ps_inputs(case: str) -> Tuple[pd.DataFrame, pd.Series, Optional[dict]]:
    """明列輸入：正向家族 a（3 變體）、反向家族 b、單特徵 c、2 變體家族 d（< 門檻）、含常數與 NaN 變體之家族 e、
    全常數家族 z（全 NaN IC ⇒ 略過）；標籤末 2 根 NaN（前瞻標籤形狀）。"""
    n = 4 if case == "short" else 120
    i = np.arange(n, dtype=float)
    label = pd.Series(0.01 * np.sin(i / 4.0) + 0.004 * np.cos(i / 2.3), index=_idx(n), name="label")
    label.iloc[-2:] = np.nan
    cols: Dict[str, np.ndarray] = {}
    for k in (5, 10, 20):
        cols[f"a_{k}"] = np.sin((i + 1 - k / 10.0) / 4.0) + 0.05 * k * np.cos(i / 3.0)
    for k in (1, 2, 3):
        cols[f"b_{k}"] = -(np.sin((i + 1 - k) / 4.0) + 0.3 * k * np.cos(i / 1.9))
    cols["c"] = np.cos(i / 9.0)
    cols["d_7"], cols["d_8"] = np.cos(i / 5.0), np.cos(i / 6.0)
    cols["e_3"] = np.sin(i / 3.0)
    cols["e_4"] = np.full(n, 1.5)
    e5 = np.sin(i / 2.0) + 2.0
    e5[[p for p in (3, 10, 50) if p < n]] = np.nan
    cols["e_5"] = e5
    for k in (1, 2, 3):
        cols[f"z_{k}"] = np.full(n, float(k))
    df = pd.DataFrame(cols, index=_idx(n))
    meta: Optional[dict] = None
    if case == "with_nan":
        df.loc[df.index[[2, 7, 40]], "a_10"] = np.nan
        label.iloc[[5, 60]] = np.nan
    elif case == "empty":
        df = df.iloc[:, :0]
    elif case == "single_feature":
        df = df[["c"]]
    elif case == "metadata":
        meta = {"symbol": "BTCUSDT", "a_5": {"indicator": "SIN", "data_source": "kline"},
                "a_10": {"indicator": "SIN", "data_source": "kline"}, "a_20": {"indicator": "SIN", "data_source": "kline"},
                "c": {"indicator": "COS"}, "e_3": {"category": "unknown"}}
    elif case == "metadata_no_indicator":
        meta = {name: {"name": name, "category": "unknown", "layer": 1} for name in df.columns}
    return df, label, meta


PS_CASES = ["base", "with_nan", "short", "empty", "single_feature", "metadata", "metadata_no_indicator"]


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("case", PS_CASES)
def test_parameter_sensitivity_matches_ref(case: str) -> None:
    """明列邊界輸入上 `batch_analyze` 逐欄 == `ref_parameter_sensitivity`（統計欄以 compare、非統計欄完全相等）。"""
    df, label, meta = _ps_inputs(case)
    got = _run_ps(df, label, meta)
    _assert_all_consistent(compare_parameter_sensitivity(got, df, label, meta))
    _assert_non_stat_equal("parameter_sensitivity", got, ref_parameter_sensitivity(df, label, meta))
    if case == "base":
        fams = got["families"]
        assert set(fams) == {"a", "b", "e"}, "前提：a、b、e 成族；d（2 變體）不足門檻、z（全 NaN IC）略過、c 單特徵"
        e_rows = {r["variant"]: r for r in fams["e"]["sensitivity_table"]}
        assert math.isnan(e_rows["e_4"]["ic_mean"]) and math.isfinite(e_rows["e_4"]["icir"]), "前提：常數變體 IC NaN"
    if case in ("short", "empty", "single_feature"):
        assert got["families"] == {} and got["summary"]["total_families"] == 0
    if case == "metadata":
        assert set(got["families"]) == {"kline_SIN"}, "前提：metadata 有 indicator ⇒ 只依 indicator 分組（其餘特徵不入）"


@pytest.mark.parametrize("ic_std,icir_std,expected", [
    (0.0199, 0.1499, "low"), (0.02, 0.1499, "medium"), (0.0199, 0.15, "medium"),
    (0.0499, 0.2999, "medium"), (0.05, 0.0, "high"), (0.0, 0.3, "high"), (math.nan, 0.0, "high"), (0.0, math.nan, "high"),
])
def test_overfitting_risk_threshold_boundaries(ic_std: float, icir_std: float, expected: str) -> None:
    """過擬合風險分級（:116-129）之門檻邊界（等於門檻 ⇒ 落下一級；NaN ⇒ high）== oracle。"""
    cfg = ParameterSensitivityConfig().model_dump()
    got = ParameterSensitivityAnalyzer(cfg).classify_overfitting_risk(ic_std, icir_std)
    assert got == _ref_risk(ic_std, icir_std, cfg["ic_std_threshold_low"], cfg["ic_std_threshold_high"]) == expected


def test_parameter_sensitivity_risk_lists_with_thresholds() -> None:
    """設定門檻改變時 high／low 名單與計數 == oracle（明列輸入；門檻取使 a、b、e 分屬不同級）。"""
    df, label, _ = _ps_inputs("base")
    ref0 = ref_parameter_sensitivity(df, label)
    stds = sorted(f["stability_metrics"]["ic_std_across_params"] for f in ref0["families"].values())
    cfg = {"ic_std_threshold_low": (stds[0] + stds[1]) / 2, "ic_std_threshold_high": (stds[1] + stds[2]) / 2}
    got = _run_ps(df, label, None, cfg)
    _assert_all_consistent(compare_parameter_sensitivity(got, df, label, None, cfg))
    risks = {f["stability_metrics"]["overfitting_risk"] for f in got["families"].values()}
    assert len(risks) >= 2 and got["high_risk_families"], f"前提：門檻須分出多級且含 high（實得 {risks}）"


@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：parameter_sensitivity 之 icir 為 mean(x·y)/std(x·y) 代理，"
                                       "非 IC 時間序列之 ICIR，隨特徵平移改變；收據 " + RECEIPT)
def test_parameter_sensitivity_icir_invariant_under_monotone_transform() -> None:
    """業界 ICIR＝IC 時間序列之均值／標準差；Spearman IC 對特徵之嚴格遞增變換不變 ⇒ ICIR 亦不變。明列輸入：x 與 x+100
    之 ic_mean 相同（前提），icir 須相同（現行代理 mean(x·y)/std(x·y)，:193-201，未去均值 ⇒ 隨平移改變）。"""
    df, label, _ = _ps_inputs("base")
    base = df[["a_5", "a_10", "a_20"]]
    shifted = (base + 100.0).rename(columns=lambda c: c.replace("a_", "s_"))
    got = _run_ps(pd.concat([base, shifted], axis=1), label)
    a = {r["param_value"]: r for r in got["families"]["a"]["sensitivity_table"]}
    s = {r["param_value"]: r for r in got["families"]["s"]["sensitivity_table"]}
    for k in a:
        assert _rel(a[k]["ic_mean"], s[k]["ic_mean"]) <= REL_TOL, "前提：Spearman IC 平移不變"
    for k in a:
        assert _rel(s[k]["icir"], a[k]["icir"]) <= REL_TOL, (
            f"param {k}：icir(x)={a[k]['icir']} vs icir(x+100)={s[k]['icir']}；oracle 滾動 ICIR(w=21)="
            f"{ref_rolling_rank_icir(base[f'a_{k}'], label, 21)}（平移不變）")


@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：parameter_sensitivity 之 best_param 取有號 IC 最大，"
                                       "反向家族取到最弱變體；收據 " + RECEIPT)
def test_parameter_sensitivity_best_param_sign_flip_invariant() -> None:
    """因子方向為符號約定（IC 頁之單調性、多空皆對稱處理）：家族整體取負不應改變「最佳參數」。明列輸入：家族 a 與
    −a（同參數）之 best_param 須相同（＝|IC| 最大者）；現行 :100 取有號最大 ⇒ −a 取到 |IC| 最小之變體。"""
    df, label, _ = _ps_inputs("base")
    base = df[["a_5", "a_10", "a_20"]]
    neg = (-base).rename(columns=lambda c: c.replace("a_", "n_"))
    got = _run_ps(pd.concat([base, neg], axis=1), label)
    ics = {r["param_value"]: r["ic_mean"] for r in got["families"]["n"]["sensitivity_table"]}
    assert len({round(abs(v), 12) for v in ics.values()}) == 3, "前提：三變體 |IC| 相異"
    exp = ref_parameter_sensitivity(neg, label, best_by_abs=True)["families"]["n"]["stability_metrics"]["best_param"]
    assert got["families"]["n"]["stability_metrics"]["best_param"] == got["families"]["a"]["stability_metrics"][
        "best_param"] == exp, f"−a 之 IC {ics}；best 產品 {got['families']['n']['stability_metrics']['best_param']}／" \
                              f"oracle(|IC| 最大) {exp}"


# ── rolling_oos 秒級 ────────────────────────────────────────────────────────────────────────────────────

OOS_SMALL = {"train_window": 30, "test_window": 10, "step": 5, "min_splits": 3}


def _oos_inputs(case: str) -> Tuple[pd.DataFrame, pd.Series, dict, Optional[str], Optional[int]]:
    """明列輸入（小設定 train 30／test 10／step 5／min_splits 3）。回 (features, labels, config, method, top_n)。"""
    n = 45 if case == "halving" else 120
    i = np.arange(n, dtype=float)
    y = pd.Series(0.01 * np.sin((i + 1) / 4.0) + 0.005 * np.cos(i / 2.9), index=_idx(n), name="label")
    y.iloc[-1:] = np.nan
    x = np.sin(i / 4.0) + 0.3 * np.cos(i / 1.7)
    df = pd.DataFrame({"f": x, "g": -x + 0.2 * np.cos(i / 5.0), "h": np.cos(i / 3.0)}, index=_idx(n))
    method: Optional[str] = None
    top_n: Optional[int] = None
    if case == "with_nan":
        df.loc[df.index[[4, 9, 33, 70]], "f"] = np.nan
        y.iloc[[12, 80]] = np.nan
    elif case == "insufficient":
        short = df["h"].copy()
        short.iloc[:85] = np.nan  # 有效 35－1 列 < 40
        df["short"] = short
    elif case == "constant":
        df["k"] = 2.0  # 全常數 ⇒ 現行逐切分 IC 0.0、mean_is=0 ⇒ degradation 0.0、std 0 ⇒ oos_icir NaN
    elif case == "pearson":
        method = "pearson"
    elif case == "pearson_inf":
        method = "pearson"
        inf = df["h"].copy()
        inf.iloc[::4] = np.inf  # 每窗含 inf ⇒ Pearson NaN ⇒ 全切分無效
        df["inf"] = inf
    elif case == "top_n":
        top_n = 1
    elif case == "empty_features":
        df = df.iloc[:, :0]
    return df, y, dict(OOS_SMALL), method, top_n


OOS_CASES = ["base", "with_nan", "halving", "insufficient", "constant", "pearson", "pearson_inf", "top_n"]


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("case", OOS_CASES)
def test_rolling_oos_matches_ref(case: str) -> None:
    """明列邊界輸入上 `validate_batch` 逐欄 == `ref_rolling_oos`（horizon=0：現行公式之重算；purge 見真實資料 xfail）。"""
    df, y, cfg, method, top_n = _oos_inputs(case)
    got = _run_oos(df, y, cfg, top_n=top_n, method=method)
    m = method or "spearman"
    _assert_all_consistent(compare_rolling_oos(got, df, y, cfg, horizon=0, top_n=top_n, method=m))
    _assert_non_stat_equal("rolling_oos", got, ref_rolling_oos(df, y, cfg, top_n=top_n, method=m))
    if case == "halving":
        assert len(got["features"]["f"]["splits_sampled"]) == 3, "前提：步長 5 只得 2 切分 < 3 ⇒ 減半為 2 得 3 切分"
    if case == "insufficient":
        assert got["features"]["short"]["skipped"] is True
    if case == "constant":
        st = got["features"]["k"]["oos_stability"]
        assert st["degradation_ratio"] == 0.0 and math.isnan(st["oos_icir"]), "前提：mean_is=0、std=0 分支"
    if case == "pearson_inf":
        assert got["features"]["inf"]["reason"] == "all splits invalid"
    if case == "top_n":
        assert list(got["features"]) == ["f"]


@pytest.mark.parametrize("hit,degr", [(0.7, 0.2999), (0.6999, 0.0), (0.7, 0.3), (0.5, 0.4999), (0.4999, 0.0),
                                      (0.5, 0.5), (1.0, -1.0)])
def test_rolling_oos_assessment_threshold_boundaries(hit: float, degr: float) -> None:
    """評等（:200-205）之門檻邊界 == oracle（等於 hit 門檻入該級、等於 degradation 門檻落下一級）。"""
    cfg = RollingOOSConfig().model_dump()
    assert RollingOOSValidator(cfg)._classify_assessment(hit, degr) == _ref_assessment(
        hit, degr, cfg["assessment_thresholds"])


def test_rolling_oos_split_generation_matches_ref() -> None:
    """切分數（`config/n_splits`，:152、:163-186）於門檻邊界之樣本數 == oracle（n<train+test ⇒ 0；恰等 ⇒ 1；減半路徑）。"""
    cfg = RollingOOSConfig(**OOS_SMALL).model_dump()
    v = RollingOOSValidator(cfg)
    for n in (0, 39, 40, 41, 44, 45, 50, 120):
        got = [(r[0].start, r[0].stop, r[1].stop) for r in v._generate_splits(n)]
        assert got == _ref_splits(n, 30, 10, 5, 3), f"n={n}"


@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：rolling_oos 之 method='kendall' 實算 Pearson"
                                       "（非 spearman 一律 numpy.corrcoef）；收據 " + RECEIPT)
def test_rolling_oos_kendall_method_uses_kendall_tau() -> None:
    """`validate(method="kendall")`（公開入口）之逐切分 IC 須 == `scipy.stats.kendalltau`；現行 :194-196 對非 spearman
    一律 `numpy.corrcoef`（Pearson）。"""
    df, y, cfg, _, _ = _oos_inputs("base")
    got = _run_oos(df, y, cfg, method="kendall")
    _assert_all_consistent(compare_rolling_oos(got, df, y, cfg, horizon=0, method="kendall"))


@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：rolling_oos 之常數窗 IC 記 0.0 並計入統計，"
                                       "相關係數於常數輸入未定義（scipy NaN）；收據 " + RECEIPT)
def test_rolling_oos_constant_window_ic_is_undefined() -> None:
    """窗內特徵常數時 IC 未定義（`scipy.stats.spearmanr` 回 NaN；同模組 parameter_sensitivity :187-188 與
    `pit_stats` 滾動 IC 皆記 NaN）⇒ 該切分應略過；現行 :192-193 記 0.0 計入 mean／hit／degradation。明列輸入：特徵前段
    常數（狀態旗標型）、後段變動。"""
    df, y, cfg, _, _ = _oos_inputs("base")
    flag = df["f"].copy()
    flag.iloc[:70] = 1.0
    df = pd.DataFrame({"flag": flag})
    got = _run_oos(df, y, cfg)
    with pytest.warns(stats.ConstantInputWarning):
        assert math.isnan(stats.spearmanr(np.ones(10), np.arange(10.0)).statistic), "前提：scipy 對常數輸入回 NaN"
    assert any(s["oos_ic"] == 0.0 for s in got["features"]["flag"]["splits_sampled"]), "前提：輸入含常數測試窗"
    _assert_all_consistent(compare_rolling_oos(got, df, y, cfg, horizon=0, constant_ic="nan"))


@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：rolling_oos 之 oos_hit_rate／degradation_ratio 以正 IC "
                                       "為準，反向因子恆判 overfitting；收據 " + RECEIPT)
def test_rolling_oos_sign_flip_invariant() -> None:
    """特徵取負（同一因子之反向使用）不應改變穩健性評等：明列輸入 f 與 −f 之 oos_hit_rate、degradation_ratio、
    assessment 須相同（＝方向中立 oracle `sign_aligned=True`）；現行 :95 計 oos>0、:88-90 以 (is−oos)/|is|。"""
    df, y, cfg, _, _ = _oos_inputs("base")
    pair = pd.DataFrame({"f": df["f"], "neg_f": -df["f"]})
    got = _run_oos(pair, y, cfg)
    _assert_all_consistent(compare_rolling_oos(got, pair, y, cfg, horizon=0, sign_aligned=True))
    a, b = got["features"]["f"], got["features"]["neg_f"]
    assert a["assessment"] == b["assessment"]


# ── 真實資料 ───────────────────────────────────────────────────────────────────────────────────────────


def _real_close(rows: int = REAL_ROWS, symbol: str = "BTCUSDT") -> pd.Series:
    import h5py

    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        data = f[f"{symbol}/1h/data"][-rows:]
    idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True)
    return pd.Series(data["close"].astype("float64"), index=idx, name="close")


def _real_label(close: pd.Series, horizon: int = 1) -> pd.Series:
    """真實標籤：簡單報酬 close[t+h]／close[t]−1（label_generator.py:45-47）。"""
    return (close.shift(-horizon) / close - 1.0).rename("label")


def _real_families(close: pd.Series) -> pd.DataFrame:
    """真實 kline 上之因果特徵家族（只用 0..t；命名同 FF `close_1h_<類>_<指標>_<週期>`，家族由名稱樣式偵測）：
    EMA 水位、ROC 動量、對 SMA 偏離、報酬波動率。"""
    ret = close.pct_change()
    cols: Dict[str, pd.Series] = {}
    for k in (5, 10, 20, 50):
        cols[f"close_1h_trend_EMA_{k}"] = close.ewm(span=k, adjust=False).mean()
    for k in (1, 3, 6, 12, 24):
        cols[f"close_1h_mom_ROC_{k}"] = close / close.shift(k) - 1.0
    for k in (10, 20, 50):
        cols[f"close_1h_dev_SMA_{k}"] = close / close.rolling(k).mean() - 1.0
    for k in (10, 20, 50):
        cols[f"close_1h_vol_STD_{k}"] = ret.rolling(k).std()
    return pd.DataFrame(cols)


def _real_sparse(close: pd.Series) -> pd.Series:
    """真實稀疏特徵（只在 UTC 0 時有值之 1 根報酬）：有效列 ≈ 2000／24 < 315 ⇒ rolling_oos 跳過分支。"""
    ret = close.pct_change()
    return ret.where(close.index.hour == 0).rename("close_1h_sparse_RET0")


#: 真實資料上使三級風險皆出現之門檻（schema 允許之公開設定；預設門檻下四族皆 low）
REAL_PS_STRICT = {"ic_std_threshold_low": 0.005, "ic_std_threshold_high": 0.006}


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_sensitivity_oos_fields_closed() -> None:
    """真實 kline 小輸入（四家族＋稀疏特徵）執行產品兩模組：實際欄位路徑集合 == `MODULE_FIELDS` 鍵集合（逐模組）；
    oracle 項皆有說明。"""
    close = _real_close()
    df = _real_families(close).assign(close_1h_sparse_RET0=_real_sparse(close))
    label = _real_label(close)
    ps = _run_ps(df, label, metadata={}, config=REAL_PS_STRICT)
    oos = _run_oos(df, label)
    keys = _field_keys("parameter_sensitivity", ps) | _field_keys("rolling_oos", oos)
    assert keys == set(MODULE_FIELDS), f"清冊多 {sorted(set(MODULE_FIELDS) - keys)}；少 {sorted(keys - set(MODULE_FIELDS))}"
    assert {v["oracle"] for v in MODULE_FIELDS.values()} - {NON_STAT} <= set(ORACLE_ITEMS)


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("config", [None, REAL_PS_STRICT], ids=["default", "strict"])
def test_parameter_sensitivity_matches_ref_on_real_kline(config: Optional[dict]) -> None:
    """真實 BTCUSDT 1h 2,000 根：`batch_analyze` 逐統計欄 == oracle，且每一統計欄至少一值為有限（名單欄非空者由兩組
    門檻合併涵蓋）。"""
    close = _real_close()
    df, label = _real_families(close), _real_label(close)
    got = _run_ps(df, label, metadata={}, config=config)
    res = compare_parameter_sensitivity(got, df, label, {}, config)
    _assert_all_consistent(res)
    _assert_non_stat_equal("parameter_sensitivity", got, ref_parameter_sensitivity(df, label, {}, config))
    assert got["summary"]["total_families"] == 4
    lists = ("parameter_sensitivity/high_risk_families", "parameter_sensitivity/robust_families")
    for f, r in res.items():
        if f not in lists:
            assert r["n_finite"] >= 1, f"{f}：無有限值（資料不足不算已驗）"
    if config is None:
        assert got["robust_families"], "預設門檻：須有 low 家族"
    else:
        assert got["high_risk_families"], "嚴格門檻：須有 high 家族"
        assert {f["stability_metrics"]["overfitting_risk"] for f in got["families"].values()} >= {"low", "high"}


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_rolling_oos_matches_ref_on_real_kline() -> None:
    """真實 BTCUSDT 1h 2,000 根（預設設定 train 252／test 63／step 21）：`validate_batch` 逐統計欄 == oracle（horizon=0：
    現行公式之重算），每一統計欄至少一特徵得有限值；稀疏特徵走跳過分支。"""
    close = _real_close()
    df = _real_families(close).assign(close_1h_sparse_RET0=_real_sparse(close))
    label = _real_label(close)
    got = _run_oos(df, label)
    res = compare_rolling_oos(got, df, label, horizon=0)
    _assert_all_consistent(res)
    _assert_non_stat_equal("rolling_oos", got, ref_rolling_oos(df, label))
    for f, r in res.items():
        assert r["n_finite"] >= 1, f"{f}：無有限值（資料不足不算已驗）"
    assert got["features"]["close_1h_sparse_RET0"]["skipped"] is True
    assert {v.get("assessment") for v in got["features"].values()} >= {"moderate", "overfitting"}


def _perturb_test_segment(close: pd.Series, feature_fn, horizon: int, cfg: dict) -> Tuple[pd.Series, pd.Series, int, int]:
    """回 (擾動後 close, 原 close, 第 0 切分訓練終點之位置, 測試終點之位置)：位置以「特徵∩標籤 dropna」後之列計
    （同 rolling_oos_validator.py:38、:59-60）；擾動＝該切分測試段之 close 乘 1.07（有限、不改缺值樣式）。"""
    feat, label = feature_fn(close), _real_label(close, horizon)
    data = _pair(feat, label)
    tr_end, te_end = int(cfg["train_window"]), int(cfg["train_window"]) + int(cfg["test_window"])
    seg = data.index[tr_end:te_end]
    bumped = close.copy()
    bumped.loc[seg] = bumped.loc[seg] * 1.07
    return bumped, close, tr_end, te_end


def _dev20(close: pd.Series) -> pd.Series:
    return (close / close.rolling(20).mean() - 1.0).rename("dev20")


@pytest.mark.requires_kline
@pytest.mark.parametrize("horizon", [1, 21])
def test_ref_purged_rolling_oos_is_invariant_to_test_prices(horizon: int) -> None:
    """oracle 自證（使 xfail 可證偽）：擾動第 0 切分測試段之真實 close ⇒ 未 purge（h=0 公式）之 IS IC 改變（擾動確實觸及
    訓練段末 h 根之標籤），purge ≥ h 之 IS IC 不變。"""
    cfg = RollingOOSConfig().model_dump()
    bumped, close, _, _ = _perturb_test_segment(_real_close(), _dev20, horizon, cfg)
    out = {}
    for tag, c in (("orig", close), ("bump", bumped)):
        f, y = _dev20(c).to_frame(), _real_label(c, horizon)
        out[tag] = (ref_rolling_oos(f, y, horizon=0)["features"]["dev20"]["splits_sampled"][0]["is_ic"],
                    ref_rolling_oos(f, y, horizon=horizon)["features"]["dev20"]["splits_sampled"][0]["is_ic"])
    assert out["orig"][0] != out["bump"][0], "前提：未 purge 之 IS IC 須受測試段價格影響"
    assert out["orig"][1] == out["bump"][1], "purge ≥ h 之 IS IC 須不受測試段價格影響"


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason="偷看未來：ICPERF Task 0.3 不一致：rolling_oos 訓練段後緊接測試段無 purge，"
                                       "訓練段末 h 根之標籤用到測試段價格；收據 " + RECEIPT)
@pytest.mark.parametrize("horizon", [1, 21])
def test_rolling_oos_train_labels_must_not_see_test_prices(horizon: int) -> None:
    """真實 BTCUSDT 1h：標籤＝h 根前瞻報酬。擾動第 0 切分測試段（[train_end, test_end)）之 close 後，該切分之 IS IC
    須不變（訓練段只得用測試段開始前已知之價格，purge ≥ h）；現行 rolling_oos_validator.py:174-179 訓練段
    [start, start+train) 緊接測試段，訓練段末 h 根之標籤 close[t+h]／close[t]−1 讀到測試段價格 ⇒ IS IC 改變。"""
    cfg = RollingOOSConfig().model_dump()
    bumped, close, _, _ = _perturb_test_segment(_real_close(), _dev20, horizon, cfg)
    vals = []
    for c in (close, bumped):
        out = _run_oos(_dev20(c).to_frame(), _real_label(c, horizon))
        vals.append(out["features"]["dev20"]["splits_sampled"][0])
    assert vals[0]["split_id"] == vals[1]["split_id"] == 0
    assert vals[0]["is_ic"] == vals[1]["is_ic"], f"h={horizon}：IS IC 原 {vals[0]['is_ic']!r} → 擾動測試段後 " \
                                                 f"{vals[1]['is_ic']!r}"


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.xfail(strict=True, reason="偷看未來：ICPERF Task 0.3 不一致：rolling_oos 之 IS IC 未 purge 標籤 horizon，"
                                       "與 purge ≥ h 之 oracle 不同；收據 " + RECEIPT)
@pytest.mark.parametrize("horizon", [1, 21])
def test_rolling_oos_matches_purged_oracle_on_real_kline(horizon: int) -> None:
    """真實 BTCUSDT 1h 四家族特徵、h 根前瞻標籤：`validate_batch` 逐統計欄須 == purge ≥ h 之 oracle（訓練段去末 h 根）。"""
    close = _real_close()
    df, label = _real_families(close), _real_label(close, horizon)
    got = _run_oos(df, label)
    _assert_all_consistent(compare_rolling_oos(got, df, label, horizon=horizon))


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：parameter_sensitivity 之 icir 為 mean(x·y)/std(x·y) 代理，"
                                       "隨特徵之遞增變換（水位→對數）改變；收據 " + RECEIPT)
def test_parameter_sensitivity_icir_invariant_under_monotone_transform_on_real_kline() -> None:
    """真實 BTCUSDT 1h：EMA 水位家族與其對數（嚴格遞增變換）之 ic_mean 相同（前提），icir 須相同（業界 ICIR 對遞增變換
    不變）；現行代理對水位型特徵近似 mean(r)/std(r)（標籤漂移），與因子排序能力無關。"""
    close = _real_close()
    ema = _real_families(close)[[f"close_1h_trend_EMA_{k}" for k in (5, 10, 20, 50)]]
    log_ema = np.log(ema).rename(columns=lambda c: c.replace("trend_EMA", "trend_LOGEMA"))
    label = _real_label(close)
    got = _run_ps(pd.concat([ema, log_ema], axis=1), label, metadata={})
    a = {r["param_value"]: r for r in got["families"]["close_1h_trend_EMA"]["sensitivity_table"]}
    b = {r["param_value"]: r for r in got["families"]["close_1h_trend_LOGEMA"]["sensitivity_table"]}
    for k in a:
        assert _rel(b[k]["ic_mean"], a[k]["ic_mean"]) <= REL_TOL, "前提：Spearman IC 遞增變換不變"
    msgs = [f"EMA_{k}: icir 水位 {a[k]['icir']:.6g} vs 對數 {b[k]['icir']:.6g}；oracle 滾動 ICIR(w=252) "
            f"{ref_rolling_rank_icir(ema[f'close_1h_trend_EMA_{k}'], label, 252):.6g}" for k in a]
    assert all(_rel(b[k]["icir"], a[k]["icir"]) <= REL_TOL for k in a), "; ".join(msgs)


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：parameter_sensitivity 之 best_param 取有號 IC 最大，"
                                       "真實反向家族（EMA 水位，IC<0）取到 |IC| 最小之變體；收據 " + RECEIPT)
def test_parameter_sensitivity_best_param_sign_flip_invariant_on_real_kline() -> None:
    """真實 BTCUSDT 1h EMA 水位家族（四變體 IC 皆 < 0）：best_param 須 == |IC| 最大之變體（方向中立 oracle）。"""
    close = _real_close()
    ema = _real_families(close)[[f"close_1h_trend_EMA_{k}" for k in (5, 10, 20, 50)]]
    label = _real_label(close)
    got = _run_ps(ema, label, metadata={})
    fam = got["families"]["close_1h_trend_EMA"]
    ics = {r["param_value"]: r["ic_mean"] for r in fam["sensitivity_table"]}
    assert all(v < 0 for v in ics.values()), f"前提：家族 IC 皆為負（實得 {ics}）"
    exp = ref_parameter_sensitivity(ema, label, {}, best_by_abs=True)["families"]["close_1h_trend_EMA"][
        "stability_metrics"]["best_param"]
    assert fam["stability_metrics"]["best_param"] == exp, f"IC {ics}；產品 {fam['stability_metrics']['best_param']}／" \
                                                          f"oracle(|IC| 最大) {exp}"


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：rolling_oos 之 oos_hit_rate／degradation_ratio 以正 IC "
                                       "為準，真實反向因子恆判 overfitting；收據 " + RECEIPT)
def test_rolling_oos_sign_flip_invariant_on_real_kline() -> None:
    """真實 BTCUSDT 1h EMA_5 水位（OOS IC 幾乎全負）與其取負：評等與 hit／degradation 須相同（方向中立 oracle）。"""
    close = _real_close()
    ema5 = _real_families(close)["close_1h_trend_EMA_5"]
    pair = pd.DataFrame({"ema5": ema5, "neg_ema5": -ema5})
    label = _real_label(close)
    got = _run_oos(pair, label)
    a, b = got["features"]["ema5"], got["features"]["neg_ema5"]
    assert (a["assessment"], a["oos_stability"]["oos_hit_rate"], a["oos_stability"]["degradation_ratio"]) == (
        b["assessment"], b["oos_stability"]["oos_hit_rate"], b["oos_stability"]["degradation_ratio"]), \
        f"ema5 {a['assessment']} {a['oos_stability']}；neg_ema5 {b['assessment']} {b['oos_stability']}"
