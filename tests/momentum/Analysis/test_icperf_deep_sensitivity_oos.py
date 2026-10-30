"""ICPERF Task 0.3／0.4 深度分析 oracle 測試——組 sensitivity_oos（docs/ICPERF_SPEC.md Task 0.3、Task 0.4 擴列表
⑧（best_param 以 |IC| 判強度並記方向）、⑬（IC-13 時間軸對齊）、⑳（SO-1～SO-7））。

被測模組（深度報告 `results.<模組鍵>`）：
- `parameter_sensitivity`：`momentum/Analysis/parameter_sensitivity_analyzer.py` `ParameterSensitivityAnalyzer.batch_analyze(
  features_df, labels, metadata=None, *, method, direction)`。
- `rolling_oos`：`momentum/Analysis/rolling_oos_validator.py` `RollingOOSValidator.validate_batch(features_df, labels, *,
  horizon, method, direction, top_n)`——`horizon` 必填。

參考實作 `ref_parameter_sensitivity`／`ref_rolling_oos` 以 numpy／scipy（Spearman＝`scipy.stats.rankdata` 平均秩後
`numpy.corrcoef`；Pearson＝`numpy.corrcoef`；Kendall＝`scipy.stats.kendalltau`）依 SPEC 之修正定義獨立重算，不呼叫被測
模組。**時間軸**：一律以特徵之原始索引位置為軸、標籤依索引對齊（`_finite_pairs` 只做逐對有限值遮罩，不 dropna 壓縮時間軸）；
rolling_oos 之切分於原始位置、訓練段為 [s, s+train−h)（purge ≥ h）；parameter_sensitivity 之滾動 IC 時間軸＝標籤有限之列
（SPEC Task 0.4 ④）、逐窗逐 scipy 計。

- 秒級（不標 requires_kline）：明列邊界輸入（空、單特徵、常數、含 NaN、中段缺標籤、特徵專屬缺值、±inf、樣本不足、全 NaN
  IC、metadata 分組、auto_detect_families 關閉、步長減半、門檻邊界、top_n 截斷、h＝0／1／21、跨訓練測試邊界之價格擾動、
  不傳 horizon ⇒ TypeError、kendall、±同強度名次、方向取上游）。
- 真實資料（`requires_kline`）：`data_cache/feature_klines/kline_cache.h5` 之 BTCUSDT 1h 末 2,000 根上之因果特徵
  （只用 0..t）與前瞻報酬標籤 close[t+h]／close[t]−1（`label_generator.py:45-47`）；須經共用監看執行（autouse 自證）。
"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

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
PS = "momentum/Analysis/parameter_sensitivity_analyzer.py"
OOS = "momentum/Analysis/rolling_oos_validator.py"
#: 逐實體（特徵名／家族名）之 dict 層：其子鍵於欄位路徑寫 `*`
ENTITY_PARENTS = ("families", "features")
#: 真實資料長度（rolling_oos 預設 train 252＋test 63 ⇒ 每特徵約 80 個切分）
REAL_ROWS = 2000
#: parameter_sensitivity 之 ICIR 窗預設（設定 dict 未帶 `icir_window` 時）
DEFAULT_ICIR_WINDOW = 63
METHODS = ("spearman", "pearson", "kendall")


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
    # parameter_sensitivity（batch_analyze 回傳 :209-214；家族 analyze_from_variants 回傳 :128-141）
    "parameter_sensitivity/families/*/variants": {"oracle": NON_STAT, "producer": f"{PS}:129"},
    "parameter_sensitivity/families/*/param_axis": {"oracle": NON_STAT, "producer": f"{PS}:130"},
    "parameter_sensitivity/families/*/sensitivity_table/#/variant": {"oracle": NON_STAT, "producer": f"{PS}:108"},
    "parameter_sensitivity/families/*/sensitivity_table/#/param_value": {"oracle": NON_STAT, "producer": f"{PS}:109"},
    "parameter_sensitivity/families/*/sensitivity_table/#/ic_mean": {"oracle": "ps.point_ic", "producer": f"{PS}:110"},
    "parameter_sensitivity/families/*/sensitivity_table/#/icir": {"oracle": "ps.rolling_icir", "producer": f"{PS}:111"},
    "parameter_sensitivity/families/*/stability_metrics/ic_std_across_params": {"oracle": "ps.std_across_params",
                                                                               "producer": f"{PS}:124"},
    "parameter_sensitivity/families/*/stability_metrics/icir_std_across_params": {"oracle": "ps.std_across_params",
                                                                                 "producer": f"{PS}:125"},
    "parameter_sensitivity/families/*/stability_metrics/overfitting_risk": {"oracle": "ps.risk_class",
                                                                           "producer": f"{PS}:135"},
    "parameter_sensitivity/families/*/stability_metrics/best_param": {"oracle": "ps.best_param",
                                                                     "producer": f"{PS}:123"},
    "parameter_sensitivity/families/*/stability_metrics/best_param_direction": {"oracle": "ps.best_param",
                                                                               "producer": f"{PS}:137"},
    "parameter_sensitivity/summary/total_families": {"oracle": NON_STAT, "producer": f"{PS}:199"},
    "parameter_sensitivity/summary/high_risk_count": {"oracle": "ps.risk_class", "producer": f"{PS}:200"},
    "parameter_sensitivity/summary/robust_count": {"oracle": "ps.risk_class", "producer": f"{PS}:201"},
    "parameter_sensitivity/high_risk_families": {"oracle": "ps.risk_class", "producer": f"{PS}:211"},
    "parameter_sensitivity/robust_families": {"oracle": "ps.risk_class", "producer": f"{PS}:212"},
    # rolling_oos（validate_batch 回傳 :181-195；逐特徵 validate 回傳 :125-131；跳過 :163-167）
    "rolling_oos/config/train_window": {"oracle": NON_STAT, "producer": f"{OOS}:183"},
    "rolling_oos/config/test_window": {"oracle": NON_STAT, "producer": f"{OOS}:184"},
    "rolling_oos/config/step": {"oracle": "oos.splits", "producer": f"{OOS}:185"},
    "rolling_oos/config/n_splits": {"oracle": "oos.splits", "producer": f"{OOS}:186"},
    "rolling_oos/features/*/skipped": {"oracle": NON_STAT, "producer": f"{OOS}:164"},
    "rolling_oos/features/*/reason": {"oracle": NON_STAT, "producer": f"{OOS}:165"},
    "rolling_oos/features/*/error_type": {"oracle": NON_STAT, "producer": f"{OOS}:166"},
    "rolling_oos/features/*/oos_stability/mean_oos_ic": {"oracle": "oos.split_ic_stats", "producer": f"{OOS}:115"},
    "rolling_oos/features/*/oos_stability/std_oos_ic": {"oracle": "oos.split_ic_stats", "producer": f"{OOS}:116"},
    "rolling_oos/features/*/oos_stability/oos_hit_rate": {"oracle": "oos.split_ic_stats", "producer": f"{OOS}:109"},
    "rolling_oos/features/*/oos_stability/mean_is_oos_gap": {"oracle": "oos.split_ic_stats", "producer": f"{OOS}:118"},
    "rolling_oos/features/*/oos_stability/oos_icir": {"oracle": "oos.split_ic_stats", "producer": f"{OOS}:119"},
    "rolling_oos/features/*/oos_stability/degradation_ratio": {"oracle": "oos.split_ic_stats",
                                                               "producer": f"{OOS}:110-112"},
    "rolling_oos/features/*/assessment": {"oracle": "oos.assessment", "producer": f"{OOS}:123"},
    "rolling_oos/features/*/direction": {"oracle": "oos.direction", "producer": f"{OOS}:128"},
    "rolling_oos/features/*/n_valid_splits": {"oracle": "oos.splits", "producer": f"{OOS}:129"},
    "rolling_oos/features/*/splits_sampled/#/split_id": {"oracle": "oos.splits", "producer": f"{OOS}:91"},
    "rolling_oos/features/*/splits_sampled/#/is_ic": {"oracle": "oos.split_ic", "producer": f"{OOS}:85"},
    "rolling_oos/features/*/splits_sampled/#/oos_ic": {"oracle": "oos.split_ic", "producer": f"{OOS}:86"},
    "rolling_oos/summary/total_validated": {"oracle": "oos.assessment", "producer": f"{OOS}:190"},
    "rolling_oos/summary/robust_count": {"oracle": "oos.assessment", "producer": f"{OOS}:191"},
    "rolling_oos/summary/moderate_count": {"oracle": "oos.assessment", "producer": f"{OOS}:192"},
    "rolling_oos/summary/overfitting_count": {"oracle": "oos.assessment", "producer": f"{OOS}:193"},
}

#: oracle 項 id → 說明（收據 coverage 之 oracle 欄引用）
ORACLE_ITEMS: Dict[str, str] = {
    "ps.point_ic": "全段：標籤依特徵索引對齊後逐對有限值（±inf 剔除）上依 method 計（spearman＝rankdata＋numpy.corrcoef、"
                   "pearson＝numpy.corrcoef、kendall＝scipy.stats.kendalltau）；列數<5 或任一欄常數 ⇒ NaN",
    "ps.rolling_icir": "滾動 IC（時間軸＝標籤有限之列，窗長 icir_window〔預設 63〕、步長 1；窗內特徵非有限或常數 ⇒ 該窗 NaN）"
                       "之 nanmean／nanstd(ddof=0)（同 ICEngine.compute_icir；std≤0 或無有限窗 ⇒ NaN）",
    "ps.std_across_params": "家族內逐變體值之 std(ddof=0)、略 NaN（pandas skipna 語意）",
    "ps.risk_class": "ic_std<low 且 icir_std<0.15 ⇒ low；ic_std<high 且 icir_std<0.3 ⇒ medium；否則 high；high／low 家族名單與"
                     "計數依家族順序",
    "ps.best_param": "|ic_mean| 最大（NaN 視 −inf、同強度取首個）之 param_value；best_param_direction＝上游 direction（有傳且含"
                     "該變體）否則 sign(該變體 ic_mean)（0／NaN ⇒ 0）",
    "oos.splits": "原始時間位置上之固定窗切分 [s, s+train)→[s+train, s+train+test)、步長 step，切分數 < min_splits 則步長減半"
                  "（至多 6 輪）；config.step＝實際步長、n_splits＝len(features_df.index) 之切分數；n_valid_splits＝入統計之切分數",
    "oos.split_ic": "逐切分 IS IC 於 [s, s+train−h)（purge ≥ h）、OOS IC 於 [s+train, s+train+test)，各段內逐對有限值；列數<5 或"
                    "常數 ⇒ NaN、該切分略過；method 同 ps.point_ic",
    "oos.direction": "上游 direction（有傳且含該特徵）否則 sign(全段逐對有限值上之點 IC)（0／NaN ⇒ 0）",
    "oos.split_ic_stats": "有效切分之 IS／OOS IC：mean、std(ddof=0)、hit＝mean(d·oos>0)、mean(is−oos)、mean/std（std≤0⇒NaN）、"
                          "degradation＝(d·mean_is−d·mean_oos)/|mean_is|（mean_is=0⇒0.0）；d＝0 ⇒ hit、degradation NaN",
    "oos.assessment": "hit≥robust_hit 且 degr<robust_max ⇒ robust；hit≥moderate_hit 且 degr<moderate_max ⇒ moderate；否則 "
                      "overfitting；summary 計數",
}


# ── 參考實作（不呼叫被測模組） ─────────────────────────────────────────────────────────────────────────────

_FAMILY_RE = re.compile(r"^(.+?)_(\d+)$")
_PARAM_RE = re.compile(r"_(\d+)$")


def _corr(x: np.ndarray, y: np.ndarray, method: str) -> float:
    if method == "spearman":
        v = float(np.corrcoef(stats.rankdata(x), stats.rankdata(y))[0, 1])
    elif method == "kendall":
        v = float(stats.kendalltau(x, y).statistic)
    elif method == "pearson":
        v = float(np.corrcoef(x, y)[0, 1])
    else:
        raise AssertionError(method)
    return v if math.isfinite(v) else math.nan


def _aligned(feature: pd.Series, labels: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
    """原始時間軸＝特徵索引；標籤依索引取值（缺 ⇒ NaN）。不剔除任何列。"""
    lab = dict(zip(labels.index, labels.to_numpy(dtype=float)))
    y = np.array([lab.get(t, math.nan) for t in feature.index], dtype=float)
    return feature.to_numpy(dtype=float), y


def _finite_pairs(x: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """逐對有限值遮罩（NaN 與 ±inf 皆剔除）；只用於計算 IC，不改變時間軸位置。"""
    m = np.isfinite(x) & np.isfinite(y)
    return x[m], y[m]


def _ref_ic(x: np.ndarray, y: np.ndarray, method: str) -> float:
    """逐對有限值上之 IC；列數<5 或任一欄常數（相關未定義）⇒ NaN。"""
    xs, ys = _finite_pairs(x, y)
    if xs.size < 5 or np.unique(xs).size <= 1 or np.unique(ys).size <= 1:
        return math.nan
    return _corr(xs, ys, method)


def _sign(v: float) -> int:
    return 0 if (math.isnan(v) or v == 0) else (1 if v > 0 else -1)


def _ref_families(names: Sequence[str], metadata: Optional[Mapping[str, Any]], auto: bool) -> Dict[str, List[str]]:
    if metadata:
        grouped: Dict[str, List[str]] = {}
        for n in names:
            meta = metadata.get(n, {}) if isinstance(metadata, dict) else {}
            ind, src = str(meta.get("indicator", "")), str(meta.get("data_source", ""))
            if ind:
                grouped.setdefault(f"{src}_{ind}" if src else ind, []).append(n)
        if grouped:
            return grouped
    if not auto:
        return {}
    fams: Dict[str, List[str]] = {}
    for n in names:
        m = _FAMILY_RE.match(n)
        fams.setdefault(m.group(1) if m else n, []).append(n)
    return fams


def _ref_param_value(name: str) -> Any:
    m = _PARAM_RE.search(name)
    return int(m.group(1)) if m else name


def ref_rolling_icir(feature: pd.Series, labels: pd.Series, window: int, method: str = "spearman") -> float:
    """業界 ICIR：時間軸＝標籤有限之列（不依特徵缺值壓縮）；逐窗（長 window、步長 1）只用窗內資料；窗內特徵有非有限值
    或常數（或標籤常數）⇒ 該窗 NaN；ICIR＝nanmean／nanstd(ddof=0)，無有限窗或 std≤0 ⇒ NaN。"""
    x, y = _aligned(feature, labels)
    keep = np.isfinite(y)
    x, y = x[keep], y[keep]
    ics = []
    for end in range(window, len(y) + 1):
        xs, ys = x[end - window:end], y[end - window:end]
        if window <= 1 or not np.isfinite(xs).all() or np.unique(xs).size <= 1 or np.unique(ys).size <= 1:
            ics.append(math.nan)
        else:
            ics.append(_corr(xs, ys, method))
    arr = np.asarray(ics, dtype=float)
    fin = arr[np.isfinite(arr)]
    if fin.size == 0:
        return math.nan
    sd = float(np.std(fin, ddof=0))
    return float(np.mean(fin) / sd) if sd > 0 else math.nan


def _nanstd0(values: Sequence[float]) -> float:
    arr = np.asarray([v for v in values if not math.isnan(v)], dtype=float)
    return float(np.std(arr, ddof=0)) if arr.size else math.nan


def _ref_risk(ic_std: float, icir_std: float, low: float, high: float) -> str:
    if ic_std < low and icir_std < 0.15:
        return "low"
    if ic_std < high and icir_std < 0.3:
        return "medium"
    return "high"


def ref_parameter_sensitivity(features_df: pd.DataFrame, labels: pd.Series, metadata: Optional[dict] = None,
                              config: Optional[dict] = None, *, method: str = "spearman",
                              direction: Optional[Mapping[str, int]] = None) -> Dict[str, Any]:
    """`batch_analyze` 之參考實作（設定以 `ParameterSensitivityConfig` 補齊；`icir_window` 取 config 鍵，預設 63）。"""
    raw = dict(config or {})
    window = int(raw.pop("icir_window", DEFAULT_ICIR_WINDOW))
    cfg = ParameterSensitivityConfig(**raw).model_dump()
    min_size = int(cfg["min_family_size"])
    low, high = float(cfg["ic_std_threshold_low"]), float(cfg["ic_std_threshold_high"])
    threshold = max(3, min_size)
    fams = _ref_families(list(features_df.columns), metadata, bool(cfg["auto_detect_families"]))
    out_fams: Dict[str, Any] = {}
    high_risk: List[str] = []
    robust: List[str] = []
    for fam, variants in fams.items():
        if len(variants) < threshold or len(variants) < min_size:
            continue
        present = [v for v in variants if v in features_df.columns]
        if len(present) < min_size:
            continue
        rows = []
        for v in present:
            x, y = _aligned(features_df[v], labels)
            rows.append({"variant": v, "param_value": _ref_param_value(v), "ic_mean": _ref_ic(x, y, method),
                         "icir": ref_rolling_icir(features_df[v], labels, window, method)})
        ics = [r["ic_mean"] for r in rows]
        if all(math.isnan(v) for v in ics):
            continue
        best = int(np.argmax([(-math.inf if math.isnan(v) else abs(v)) for v in ics]))
        bv = rows[best]["variant"]
        bdir = int(direction[bv]) if (direction is not None and bv in direction) else _sign(rows[best]["ic_mean"])
        ic_std = _nanstd0(ics)
        icir_std = _nanstd0([r["icir"] for r in rows])
        risk = _ref_risk(ic_std, icir_std, low, high)
        out_fams[fam] = {"variants": list(variants), "param_axis": "period", "sensitivity_table": rows,
                         "stability_metrics": {"ic_std_across_params": ic_std, "icir_std_across_params": icir_std,
                                               "overfitting_risk": risk, "best_param": rows[best]["param_value"],
                                               "best_param_direction": bdir}}
        if risk == "high":
            high_risk.append(fam)
        if risk == "low":
            robust.append(fam)
    return {"families": out_fams,
            "summary": {"total_families": len(out_fams), "high_risk_count": len(high_risk),
                        "robust_count": len(robust)},
            "high_risk_families": high_risk, "robust_families": robust}


def _ref_splits(n: int, train: int, test: int, step: int, min_splits: int) -> Tuple[List[Tuple[int, int, int]], int]:
    """原始時間位置上之切分 (訓練起點, 測試起點, 測試終點) 與實際步長。"""
    if n < train + test:
        return [], step
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
    return splits, step


def _ref_assessment(hit: float, degr: float, th: Mapping[str, float]) -> str:
    if hit >= th["robust_hit_rate"] and degr < th["robust_max_degradation"]:
        return "robust"
    if hit >= th["moderate_hit_rate"] and degr < th["moderate_max_degradation"]:
        return "moderate"
    return "overfitting"


def ref_rolling_oos(features_df: pd.DataFrame, labels: pd.Series, config: Optional[dict] = None, *, horizon: int,
                    method: str = "spearman", direction: Optional[Mapping[str, int]] = None,
                    top_n: Optional[int] = None) -> Dict[str, Any]:
    """`validate_batch` 之參考實作。時間軸＝`features_df.index`；切分於原始位置；訓練段 [s, s+train−h)；各段只取逐對有限值。"""
    cfg = RollingOOSConfig(**(config or {})).model_dump()
    train, test, step, min_splits = (int(cfg[k]) for k in ("train_window", "test_window", "step", "min_splits"))
    th = cfg["assessment_thresholds"]
    n_axis = len(features_df.index)
    splits, actual_step = _ref_splits(n_axis, train, test, step, min_splits)
    k = len(features_df.columns) if top_n is None else top_n
    cols = list(features_df.columns)[: max(1, int(k))]
    results: Dict[str, Any] = {}
    counts = {"robust": 0, "moderate": 0, "overfitting": 0}
    ok = 0
    for name in cols:
        x, y = _aligned(features_df[name], labels)
        n_fin = int((np.isfinite(x) & np.isfinite(y)).sum())
        if n_fin < train + test:
            results[name] = {"skipped": True, "reason": f"insufficient samples: {n_fin} < {train + test}",
                             "error_type": "INSUFFICIENT_DATA"}
            continue
        if not splits:
            results[name] = {"skipped": True, "reason": "no valid splits generated", "error_type": "INSUFFICIENT_DATA"}
            continue
        if direction is not None and name in direction:
            d = int(direction[name])
        else:
            d = _sign(_ref_ic(x, y, method))
        sampled, is_v, oos_v = [], [], []
        for sid, (a, b, c) in enumerate(splits):
            te = b - int(horizon)
            is_ic = _ref_ic(x[a:te], y[a:te], method) if te > a else math.nan
            oos_ic = _ref_ic(x[b:c], y[b:c], method)
            if not (math.isfinite(is_ic) and math.isfinite(oos_ic)):
                continue
            is_v.append(is_ic)
            oos_v.append(oos_ic)
            sampled.append({"split_id": sid, "is_ic": is_ic, "oos_ic": oos_ic})
        if not oos_v:
            results[name] = {"skipped": True, "reason": "all splits invalid", "error_type": "INSUFFICIENT_DATA"}
            continue
        is_a, oos_a = np.asarray(is_v), np.asarray(oos_v)
        mean_is, mean_oos = float(np.mean(is_a)), float(np.mean(oos_a))
        sd = float(np.std(oos_a, ddof=0))
        if d == 0:
            hit, degr = math.nan, math.nan
        else:
            hit = float(np.mean(d * oos_a > 0))
            degr = float((d * mean_is - d * mean_oos) / abs(mean_is)) if mean_is != 0 else 0.0
        st = {"mean_oos_ic": mean_oos, "std_oos_ic": sd, "oos_hit_rate": hit,
              "mean_is_oos_gap": float(np.mean(is_a - oos_a)),
              "oos_icir": float(mean_oos / sd) if sd > 0 else math.nan, "degradation_ratio": degr}
        assess = _ref_assessment(hit, degr, th)
        results[name] = {"oos_stability": st, "assessment": assess, "direction": d, "n_valid_splits": len(sampled),
                         "splits_sampled": sampled}
        ok += 1
        counts[assess] += 1
    return {"config": {"train_window": train, "test_window": test, "step": actual_step, "n_splits": len(splits)},
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
                                  metadata: Optional[dict] = None, config: Optional[dict] = None, *,
                                  method: str = "spearman",
                                  direction: Optional[Mapping[str, int]] = None) -> Dict[str, Dict[str, Any]]:
    """產品輸出（`results.parameter_sensitivity`）對 `ref_parameter_sensitivity` 逐統計欄比對；輸入＝產品入口之同一組。"""
    ref = ref_parameter_sensitivity(features_df, labels, metadata, config, method=method, direction=direction)
    return _compare_trees("parameter_sensitivity", product_output, ref, _stat_fields("parameter_sensitivity"))


def compare_rolling_oos(product_output: Mapping[str, Any], features_df: pd.DataFrame, labels: pd.Series,
                        config: Optional[dict] = None, *, horizon: int, method: str = "spearman",
                        direction: Optional[Mapping[str, int]] = None,
                        top_n: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """產品輸出（`results.rolling_oos`）對 `ref_rolling_oos` 逐統計欄比對。`horizon`＝標籤前瞻根數（必填）。"""
    ref = ref_rolling_oos(features_df, labels, config, horizon=horizon, method=method, direction=direction, top_n=top_n)
    return _compare_trees("rolling_oos", product_output, ref, _stat_fields("rolling_oos"))


def _assert_all_consistent(res: Mapping[str, Mapping[str, Any]]) -> None:
    bad = {k: v["detail"] for k, v in res.items() if v["verdict"] != "一致"}
    assert not bad, f"不一致：{bad}"


def _assert_non_stat_equal(module_key: str, product: Mapping[str, Any], oracle: Mapping[str, Any]) -> None:
    fields = [k for k, v in MODULE_FIELDS.items() if k.startswith(module_key + "/") and v["oracle"] == NON_STAT]
    _assert_all_consistent(_compare_trees(module_key, product, oracle, fields))


# ── 產品呼叫 ──────────────────────────────────────────────────────────────────────────────────────────


def _ps_cfg(config: Optional[dict]) -> dict:
    raw = dict(config or {})
    extra = {"icir_window": raw.pop("icir_window")} if "icir_window" in raw else {}
    return {**ParameterSensitivityConfig(**raw).model_dump(), **extra}


def _run_ps(df: pd.DataFrame, labels: pd.Series, metadata: Optional[dict] = None, config: Optional[dict] = None, *,
            method: str = "spearman", direction: Optional[Mapping[str, int]] = None) -> Dict[str, Any]:
    return ParameterSensitivityAnalyzer(_ps_cfg(config)).batch_analyze(df, labels, metadata=metadata, method=method,
                                                                       direction=direction)


def _run_oos(df: pd.DataFrame, labels: pd.Series, config: Optional[dict] = None, *, horizon: int,
             method: str = "spearman", direction: Optional[Mapping[str, int]] = None,
             top_n: Optional[int] = None) -> Dict[str, Any]:
    cfg = RollingOOSConfig(**(config or {})).model_dump()
    return RollingOOSValidator(cfg).validate_batch(df, labels, horizon=horizon, method=method, direction=direction,
                                                   top_n=len(df.columns) if top_n is None else top_n)


# ── parameter_sensitivity 秒級 ──────────────────────────────────────────────────────────────────────────


def _idx(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")


#: 秒級輸入之 ICIR 窗（明列：輸入 120 列）
PS_SMALL = {"icir_window": 20}


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
    elif case == "mid_label_gap":
        label.iloc[40:55] = np.nan  # 中段缺標籤（缺價）：滾動 IC 時間軸＝標籤有限之列，點 IC 逐對有限
    elif case == "inf":
        df.loc[df.index[[6, 30]], "a_5"] = np.inf
        df.loc[df.index[[12]], "a_20"] = -np.inf
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


PS_CASES = ["base", "with_nan", "mid_label_gap", "inf", "short", "empty", "single_feature", "metadata",
            "metadata_no_indicator"]


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("case", PS_CASES)
def test_parameter_sensitivity_matches_ref(case: str, method: str) -> None:
    """明列邊界輸入 × 三方法：`batch_analyze` 逐欄 == `ref_parameter_sensitivity`（統計欄以 compare、非統計欄完全相等）。"""
    df, label, meta = _ps_inputs(case)
    got = _run_ps(df, label, meta, PS_SMALL, method=method)
    _assert_all_consistent(compare_parameter_sensitivity(got, df, label, meta, PS_SMALL, method=method))
    _assert_non_stat_equal("parameter_sensitivity", got, ref_parameter_sensitivity(df, label, meta, PS_SMALL,
                                                                                   method=method))
    if case == "base":
        fams = got["families"]
        assert set(fams) == {"a", "b", "e"}, "前提：a、b、e 成族；d（2 變體）不足門檻、z（全 NaN IC）略過、c 單特徵"
        e_rows = {r["variant"]: r for r in fams["e"]["sensitivity_table"]}
        assert math.isnan(e_rows["e_4"]["ic_mean"]) and math.isnan(e_rows["e_4"]["icir"]), "前提：常數變體 IC／ICIR NaN"
        assert all(math.isfinite(r["icir"]) for r in fams["a"]["sensitivity_table"]), "前提：ICIR 有限值"
    if case in ("short", "empty", "single_feature"):
        assert got["families"] == {} and got["summary"]["total_families"] == 0
    if case == "metadata":
        assert set(got["families"]) == {"kline_SIN"}, "前提：metadata 有 indicator ⇒ 只依 indicator 分組（其餘特徵不入）"


def test_parameter_sensitivity_kendall_ic_equals_scipy_kendalltau() -> None:
    """method＝kendall 時 ic_mean == `scipy.stats.kendalltau`（逐對有限值；SPEC ⑧ 驗收 v5.29 ⑤）。"""
    df, label, _ = _ps_inputs("with_nan")
    got = _run_ps(df, label, None, PS_SMALL, method="kendall")
    for r in got["families"]["a"]["sensitivity_table"]:
        pair = pd.concat([df[r["variant"]], label], axis=1).to_numpy(dtype=float)
        pair = pair[np.isfinite(pair).all(axis=1)]
        exp = stats.kendalltau(pair[:, 0], pair[:, 1]).statistic
        assert _rel(r["ic_mean"], float(exp)) <= REL_TOL, f"{r['variant']}：{r['ic_mean']} vs kendalltau {exp}"


def test_parameter_sensitivity_mid_label_gap_does_not_compress_time_axis() -> None:
    """中段缺標籤：滾動 ICIR 之窗不跨越「特徵缺值」壓縮——特徵專屬缺值落在窗內 ⇒ 該窗 NaN（而非剔除後滑窗）。明列輸入：
    a_10 中段 1 根 NaN；oracle（標籤有限之軸、窗內非有限 ⇒ NaN）與「先 dropna 再滑窗」之值須不同（前提），產品 == oracle。"""
    df, label, _ = _ps_inputs("with_nan")
    got = _run_ps(df, label, None, PS_SMALL)
    row = {r["variant"]: r for r in got["families"]["a"]["sensitivity_table"]}["a_10"]
    pair = pd.concat([df["a_10"], label], axis=1).dropna()
    compressed = ref_rolling_icir(pair.iloc[:, 0], pair.iloc[:, 1], 20)
    exp = ref_rolling_icir(df["a_10"], label, 20)
    assert _rel(compressed, exp) > 1e-6, "前提：壓縮時間軸與否須可區分"
    assert _rel(row["icir"], exp) <= REL_TOL, f"產品 {row['icir']} vs oracle {exp}（壓縮版 {compressed}）"


def test_auto_detect_families_false_uses_metadata_only() -> None:
    """`auto_detect_families`＝False ⇒ 不依名稱樣式成族（只 metadata indicator）；無 indicator ⇒ 無家族。"""
    df, label, _ = _ps_inputs("base")
    cfg = {**PS_SMALL, "auto_detect_families": False}
    got = _run_ps(df, label, None, cfg)
    assert got["families"] == {} and got == ref_parameter_sensitivity(df, label, None, cfg)
    meta = {f"a_{k}": {"indicator": "SIN"} for k in (5, 10, 20)}
    got2 = _run_ps(df, label, meta, cfg)
    assert set(got2["families"]) == {"SIN"}
    _assert_all_consistent(compare_parameter_sensitivity(got2, df, label, meta, cfg))


@pytest.mark.parametrize("ic_std,icir_std,expected", [
    (0.0199, 0.1499, "low"), (0.02, 0.1499, "medium"), (0.0199, 0.15, "medium"),
    (0.0499, 0.2999, "medium"), (0.05, 0.0, "high"), (0.0, 0.3, "high"), (math.nan, 0.0, "high"), (0.0, math.nan, "high"),
])
def test_overfitting_risk_threshold_boundaries(ic_std: float, icir_std: float, expected: str) -> None:
    """過擬合風險分級之門檻邊界（等於門檻 ⇒ 落下一級；NaN ⇒ high）== oracle。"""
    cfg = ParameterSensitivityConfig().model_dump()
    got = ParameterSensitivityAnalyzer(cfg).classify_overfitting_risk(ic_std, icir_std)
    assert got == _ref_risk(ic_std, icir_std, cfg["ic_std_threshold_low"], cfg["ic_std_threshold_high"]) == expected


def test_parameter_sensitivity_risk_lists_with_thresholds() -> None:
    """設定門檻改變時 high／low 名單與計數 == oracle（明列輸入；門檻取使 a、b、e 分屬不同級）。"""
    df, label, _ = _ps_inputs("base")
    ref0 = ref_parameter_sensitivity(df, label, None, PS_SMALL)
    stds = sorted(f["stability_metrics"]["ic_std_across_params"] for f in ref0["families"].values())
    cfg = {**PS_SMALL, "ic_std_threshold_low": (stds[0] + stds[1]) / 2,
           "ic_std_threshold_high": (stds[1] + stds[2]) / 2}
    got = _run_ps(df, label, None, cfg)
    _assert_all_consistent(compare_parameter_sensitivity(got, df, label, None, cfg))
    risks = {f["stability_metrics"]["overfitting_risk"] for f in got["families"].values()}
    assert got["high_risk_families"], f"前提：門檻須分出 high（實得 {risks}）"


def test_parameter_sensitivity_icir_invariant_under_monotone_transform() -> None:
    """業界 ICIR＝IC 時間序列之均值／標準差；Spearman IC 對特徵之嚴格遞增變換不變 ⇒ ICIR 亦不變。明列輸入：x 與 x+100
    之 ic_mean 相同（前提），icir 須相同且 == oracle 滾動 ICIR（SPEC ⑳；修正前代理 mean(x·y)/std(x·y) 隨平移改變）。"""
    df, label, _ = _ps_inputs("base")
    base = df[["a_5", "a_10", "a_20"]]
    shifted = (base + 100.0).rename(columns=lambda c: c.replace("a_", "s_"))
    got = _run_ps(pd.concat([base, shifted], axis=1), label, None, PS_SMALL)
    a = {r["param_value"]: r for r in got["families"]["a"]["sensitivity_table"]}
    s = {r["param_value"]: r for r in got["families"]["s"]["sensitivity_table"]}
    for k in a:
        assert _rel(a[k]["ic_mean"], s[k]["ic_mean"]) <= REL_TOL, "前提：Spearman IC 平移不變"
    for k in a:
        exp = ref_rolling_icir(base[f"a_{k}"], label, 20)
        assert _rel(s[k]["icir"], a[k]["icir"]) <= REL_TOL and _rel(a[k]["icir"], exp) <= REL_TOL, (
            f"param {k}：icir(x)={a[k]['icir']} vs icir(x+100)={s[k]['icir']}；oracle 滾動 ICIR(w=20)={exp}")


def test_parameter_sensitivity_best_param_sign_flip_invariant() -> None:
    """因子方向為符號約定：家族整體取負不改變「最佳參數」（|IC| 最大；SPEC ⑧）。明列輸入：家族 a 與 −a 之 best_param
    相同（＝|IC| 最大者），best_param_direction 分別為 +1、−1。"""
    df, label, _ = _ps_inputs("base")
    base = df[["a_5", "a_10", "a_20"]]
    neg = (-base).rename(columns=lambda c: c.replace("a_", "n_"))
    got = _run_ps(pd.concat([base, neg], axis=1), label, None, PS_SMALL)
    ics = {r["param_value"]: r["ic_mean"] for r in got["families"]["n"]["sensitivity_table"]}
    assert len({round(abs(v), 12) for v in ics.values()}) == 3, "前提：三變體 |IC| 相異"
    exp = ref_parameter_sensitivity(neg, label, None, PS_SMALL)["families"]["n"]["stability_metrics"]["best_param"]
    exp_abs = max(ics, key=lambda k: abs(ics[k]))
    na, aa = got["families"]["n"]["stability_metrics"], got["families"]["a"]["stability_metrics"]
    assert na["best_param"] == aa["best_param"] == exp == exp_abs, f"−a 之 IC {ics}；best 產品 {na['best_param']}"
    assert (aa["best_param_direction"], na["best_param_direction"]) == (_sign(-ics[exp_abs]), _sign(ics[exp_abs]))


def test_parameter_sensitivity_equal_strength_opposite_sign_ties_first() -> None:
    """±同強度名次相同：家族內 x 與 −x 之 |IC| 相等 ⇒ 依變體順序取首個（不論號）；整族取負後結果相同。"""
    df, label, _ = _ps_inputs("base")
    x = df["a_10"]
    fam = pd.DataFrame({"t_1": -x, "t_2": x, "t_3": df["a_20"] * 0.0 + df["c"]})
    got = _run_ps(fam, label, None, PS_SMALL)
    flipped = _run_ps(-fam, label, None, PS_SMALL)
    ics = {r["param_value"]: r["ic_mean"] for r in got["families"]["t"]["sensitivity_table"]}
    assert abs(ics[1]) == abs(ics[2]) and abs(ics[1]) > abs(ics[3]), f"前提：t_1、t_2 同強度且最強（{ics}）"
    assert got["families"]["t"]["stability_metrics"]["best_param"] == flipped["families"]["t"]["stability_metrics"][
        "best_param"] == 1


def test_parameter_sensitivity_direction_from_upstream() -> None:
    """上游 direction 優先：best_param_direction 取呼叫端傳入值（即使與該變體點 IC 之號相反）；未含該變體 ⇒ sign(IC)。"""
    df, label, _ = _ps_inputs("base")
    fam = df[["a_5", "a_10", "a_20"]]
    plain = _run_ps(fam, label, None, PS_SMALL)
    best = plain["families"]["a"]["stability_metrics"]
    bv = f"a_{best['best_param']}"
    forced = {bv: -best["best_param_direction"]}
    got = _run_ps(fam, label, None, PS_SMALL, direction=forced)
    assert got["families"]["a"]["stability_metrics"]["best_param_direction"] == forced[bv]
    _assert_all_consistent(compare_parameter_sensitivity(got, fam, label, None, PS_SMALL, direction=forced))
    other = _run_ps(fam, label, None, PS_SMALL, direction={"unrelated": -1})
    assert other["families"]["a"]["stability_metrics"]["best_param_direction"] == best["best_param_direction"]


def test_parameter_sensitivity_rejects_unknown_method() -> None:
    df, label, _ = _ps_inputs("base")
    with pytest.raises(ValueError):
        _run_ps(df, label, None, PS_SMALL, method="spearmann")


# ── rolling_oos 秒級 ────────────────────────────────────────────────────────────────────────────────────

OOS_SMALL = {"train_window": 30, "test_window": 10, "step": 5, "min_splits": 3}


def _price(n: int) -> pd.Series:
    """明列價格路徑（確定性、正值）。"""
    i = np.arange(n, dtype=float)
    return pd.Series(100.0 * np.exp(0.01 * np.sin(i / 4.0) + 0.004 * np.cos(i / 2.9) + 0.0005 * i), index=_idx(n))


def _fwd(p: pd.Series, h: int) -> pd.Series:
    return (p.shift(-h) / p - 1.0).rename("label")


def _oos_inputs(case: str) -> Tuple[pd.DataFrame, pd.Series, dict, str, Optional[int]]:
    """明列輸入（小設定 train 30／test 10／step 5／min_splits 3）。回 (features, labels, config, method, top_n)。"""
    n = 45 if case == "halving" else 120
    i = np.arange(n, dtype=float)
    y = pd.Series(0.01 * np.sin((i + 1) / 4.0) + 0.005 * np.cos(i / 2.9), index=_idx(n), name="label")
    y.iloc[-1:] = np.nan
    x = np.sin(i / 4.0) + 0.3 * np.cos(i / 1.7)
    df = pd.DataFrame({"f": x, "g": -x + 0.2 * np.cos(i / 5.0), "h": np.cos(i / 3.0)}, index=_idx(n))
    method = "spearman"
    top_n: Optional[int] = None
    if case == "with_nan":
        df.loc[df.index[[4, 9, 33, 70]], "f"] = np.nan  # 特徵專屬缺值
        y.iloc[[12, 80]] = np.nan
    elif case == "mid_label_gap":
        y.iloc[50:62] = np.nan  # 中段缺標籤：切分仍於原始位置
    elif case == "inf":
        df.loc[df.index[[3, 41, 77]], "f"] = np.inf
        df.loc[df.index[[20, 95]], "g"] = -np.inf
    elif case == "insufficient":
        short = df["h"].copy()
        short.iloc[:85] = np.nan
        df["short"] = short
    elif case == "constant":
        df["k"] = 2.0  # 全常數 ⇒ 全切分 IC 未定義 ⇒ all splits invalid
    elif case == "constant_window":
        flag = df["f"].copy()
        flag.iloc[:70] = 1.0  # 狀態旗標型：前段常數之窗 NaN、不入統計
        df["flag"] = flag
    elif case == "sparse":
        sp = df["h"].copy()
        sp[(np.arange(n) % 9) != 0] = np.nan  # 有限列分散 ⇒ 每窗 < 5 列 ⇒ 全切分無效
        sp.iloc[:] = sp.to_numpy()
        df = pd.DataFrame({"sparse": sp, "f": df["f"]})
    elif case in ("pearson", "kendall"):
        method = case
    elif case == "top_n":
        top_n = 1
    return df, y, dict(OOS_SMALL), method, top_n


OOS_CASES = ["base", "with_nan", "mid_label_gap", "inf", "halving", "insufficient", "constant", "constant_window",
             "pearson", "kendall", "top_n"]


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("horizon", [0, 1, 21])
@pytest.mark.parametrize("case", OOS_CASES)
def test_rolling_oos_matches_ref(case: str, horizon: int) -> None:
    """明列邊界輸入 × h＝0／1／21：`validate_batch` 逐欄 == `ref_rolling_oos`（原始位置切分、訓練段去末 h 根）。"""
    df, y, cfg, method, top_n = _oos_inputs(case)
    got = _run_oos(df, y, cfg, horizon=horizon, method=method, top_n=top_n)
    _assert_all_consistent(compare_rolling_oos(got, df, y, cfg, horizon=horizon, method=method, top_n=top_n))
    _assert_non_stat_equal("rolling_oos", got, ref_rolling_oos(df, y, cfg, horizon=horizon, method=method, top_n=top_n))
    if case == "halving":
        assert got["config"]["step"] == 2 and len(got["features"]["f"]["splits_sampled"]) == 3, \
            "前提：步長 5 只得 2 切分 < 3 ⇒ 減半為 2 得 3 切分，config.step 回顯實際步長"
    if case == "insufficient":
        assert got["features"]["short"]["skipped"] is True
    if case == "constant":
        assert got["features"]["k"]["reason"] == "all splits invalid", "前提：常數窗 IC 未定義、不入統計"
    if case == "mid_label_gap":
        assert got["config"]["n_splits"] == len(_ref_splits(len(df.index), 30, 10, 5, 3)[0]), "切分數依原始時間軸"
    if case == "top_n":
        assert list(got["features"]) == ["f"]


def test_rolling_oos_sparse_feature_all_splits_invalid() -> None:
    """有限列分散（每切分 < 5 列）：產品與 oracle 皆以原始位置切分 ⇒ 全切分無效而跳過（壓縮時間軸則會得到有效切分）。"""
    df, y, cfg, _, _ = _oos_inputs("sparse")
    cfg = {**cfg}
    got = _run_oos(df, y, {"train_window": 30, "test_window": 10, "step": 5, "min_splits": 3}, horizon=1)
    _assert_all_consistent(compare_rolling_oos(got, df, y, cfg, horizon=1))


def test_rolling_oos_mid_label_gap_splits_on_original_positions() -> None:
    """中段缺標籤：切分於原始位置（測試段終點之時間戳＝原始索引第 s+train+test−1 列），與「先 dropna 再切分」不同（前提）。"""
    df, y, cfg, _, _ = _oos_inputs("mid_label_gap")
    got = _run_oos(df[["f"]], y, cfg, horizon=1)
    exp = ref_rolling_oos(df[["f"]], y, cfg, horizon=1)
    pair = pd.concat([df["f"], y], axis=1).dropna()
    compressed = ref_rolling_oos(pair[["f"]], pair["label"], cfg, horizon=1)
    assert compressed["features"]["f"]["splits_sampled"] != exp["features"]["f"]["splits_sampled"], "前提：可區分"
    assert got["features"]["f"]["splits_sampled"] == exp["features"]["f"]["splits_sampled"] or not any(
        v["verdict"] != "一致" for v in compare_rolling_oos(got, df[["f"]], y, cfg, horizon=1).values())
    _assert_all_consistent(compare_rolling_oos(got, df[["f"]], y, cfg, horizon=1))


@pytest.mark.parametrize("horizon", [1, 21])
def test_rolling_oos_cross_boundary_price_perturbation_seconds(horizon: int) -> None:
    """明列價格路徑：擾動第 0 切分測試段（[train_end, test_end)）之價格（交替乘 1.07／0.93，打亂排名），標籤＝h 根前瞻
    報酬、特徵＝對 3 根均線之偏離（因果）⇒ 第 0 切分 IS IC 不變（purge ≥ h）；未 purge 之 oracle（h＝0）則改變（前提）。"""
    cfg = dict(OOS_SMALL)
    p = _price(120)
    tr_end, te_end = cfg["train_window"], cfg["train_window"] + cfg["test_window"]
    bumped = p.copy()
    bumped.iloc[tr_end:te_end] *= np.where(np.arange(te_end - tr_end) % 2 == 0, 1.07, 0.93)
    vals, unpurged = [], []
    for c in (p, bumped):
        f = (c / c.rolling(3).mean() - 1.0).rename("dev3").to_frame()
        lab = _fwd(c, horizon)
        vals.append(_run_oos(f, lab, cfg, horizon=horizon)["features"]["dev3"]["splits_sampled"][0])
        unpurged.append(ref_rolling_oos(f, lab, cfg, horizon=0)["features"]["dev3"]["splits_sampled"][0]["is_ic"])
    assert unpurged[0] != unpurged[1], "前提：未 purge 之 IS IC 須受測試段價格影響"
    assert vals[0]["split_id"] == vals[1]["split_id"] == 0
    assert vals[0]["is_ic"] == vals[1]["is_ic"], f"h={horizon}：IS IC {vals[0]['is_ic']!r} → {vals[1]['is_ic']!r}"


def test_rolling_oos_horizon_is_required_keyword() -> None:
    """不傳 horizon ⇒ TypeError（validate_batch 與 validate 皆然）；負值／非整數 ⇒ ValueError。"""
    df, y, cfg, _, _ = _oos_inputs("base")
    v = RollingOOSValidator(RollingOOSConfig(**cfg).model_dump())
    with pytest.raises(TypeError):
        v.validate_batch(df, y)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        v.validate(df["f"], y)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        v.validate_batch(df, y, 1)  # type: ignore[misc]
    for bad in (-1, 1.5, True):
        with pytest.raises(ValueError):
            v.validate_batch(df, y, horizon=bad)  # type: ignore[arg-type]


def test_rolling_oos_rejects_unknown_method_and_direction() -> None:
    df, y, cfg, _, _ = _oos_inputs("base")
    with pytest.raises(ValueError):
        _run_oos(df, y, cfg, horizon=1, method="spearmann")
    with pytest.raises(ValueError):
        _run_oos(df, y, cfg, horizon=1, direction={"f": 2})


@pytest.mark.parametrize("hit,degr", [(0.7, 0.2999), (0.6999, 0.0), (0.7, 0.3), (0.5, 0.4999), (0.4999, 0.0),
                                      (0.5, 0.5), (1.0, -1.0), (math.nan, math.nan)])
def test_rolling_oos_assessment_threshold_boundaries(hit: float, degr: float) -> None:
    """評等之門檻邊界 == oracle（等於 hit 門檻入該級、等於 degradation 門檻落下一級；NaN ⇒ overfitting）。"""
    cfg = RollingOOSConfig().model_dump()
    assert RollingOOSValidator(cfg)._classify_assessment(hit, degr) == _ref_assessment(
        hit, degr, cfg["assessment_thresholds"])


def test_rolling_oos_split_generation_matches_ref() -> None:
    """切分與實際步長於門檻邊界之樣本數 == oracle（n<train+test ⇒ 0；恰等 ⇒ 1；減半路徑）。"""
    cfg = RollingOOSConfig(**OOS_SMALL).model_dump()
    v = RollingOOSValidator(cfg)
    for n in (0, 39, 40, 41, 44, 45, 50, 120):
        splits, step = v._generate_splits_with_step(n)
        got = [(r[0].start, r[0].stop, r[1].stop) for r in splits]
        assert (got, step) == _ref_splits(n, 30, 10, 5, 3), f"n={n}"


def test_rolling_oos_kendall_method_uses_kendall_tau() -> None:
    """`method="kendall"` 之逐切分 IC == `scipy.stats.kendalltau`（SPEC ⑳；修正前非 spearman 一律 numpy.corrcoef）。"""
    df, y, cfg, _, _ = _oos_inputs("base")
    got = _run_oos(df, y, cfg, horizon=1, method="kendall")
    _assert_all_consistent(compare_rolling_oos(got, df, y, cfg, horizon=1, method="kendall"))
    s0 = got["features"]["f"]["splits_sampled"][0]
    xs = df["f"].to_numpy()[30:40]
    ys = y.to_numpy()[30:40]
    assert _rel(s0["oos_ic"], float(stats.kendalltau(xs, ys).statistic)) <= REL_TOL


def test_rolling_oos_constant_window_ic_is_undefined() -> None:
    """窗內特徵常數時 IC 未定義（`scipy.stats.spearmanr` 回 NaN）⇒ 該切分略過，不以 0.0 入 mean／hit／degradation
    （SPEC ⑳）。明列輸入：特徵前段常數（狀態旗標型）、後段變動。"""
    df, y, cfg, _, _ = _oos_inputs("base")
    flag = df["f"].copy()
    flag.iloc[:70] = 1.0
    df = pd.DataFrame({"flag": flag})
    got = _run_oos(df, y, cfg, horizon=1)
    with pytest.warns(stats.ConstantInputWarning):
        assert math.isnan(stats.spearmanr(np.ones(10), np.arange(10.0)).statistic), "前提：scipy 對常數輸入回 NaN"
    assert all(s["oos_ic"] != 0.0 for s in got["features"]["flag"]["splits_sampled"])
    assert got["features"]["flag"]["n_valid_splits"] < got["config"]["n_splits"], "前提：輸入含常數窗而被略過"
    _assert_all_consistent(compare_rolling_oos(got, df, y, cfg, horizon=1))


def test_rolling_oos_sign_flip_invariant() -> None:
    """特徵取負不改變穩健性評等（未傳方向 ⇒ d＝sign(全段點 IC)；SPEC ⑳／⑧）：f 與 −f 之 hit、degradation、assessment 相同、
    direction 相反。"""
    df, y, cfg, _, _ = _oos_inputs("base")
    pair = pd.DataFrame({"f": df["f"], "neg_f": -df["f"]})
    got = _run_oos(pair, y, cfg, horizon=1)
    _assert_all_consistent(compare_rolling_oos(got, pair, y, cfg, horizon=1))
    a, b = got["features"]["f"], got["features"]["neg_f"]
    assert a["assessment"] == b["assessment"] and a["direction"] == -b["direction"] != 0
    for k in ("oos_hit_rate", "degradation_ratio"):
        assert _rel(a["oos_stability"][k], b["oos_stability"][k]) <= REL_TOL


def test_rolling_oos_direction_from_upstream_overrides_split_sign() -> None:
    """SPEC ⑧ 驗收②：上游 direction 優先（不以逐切分 IS IC 定方向）。明列輸入：g（全段點 IC < 0）傳 direction +1 ⇒
    hit＝mean(oos>0)、degradation＝(is−oos)/|is|；direction 0 ⇒ hit、degradation NaN。"""
    df, y, cfg, _, _ = _oos_inputs("base")
    g = df[["g"]]
    plain = _run_oos(g, y, cfg, horizon=1)
    assert plain["features"]["g"]["direction"] == -1, "前提：g 之全段點 IC < 0"
    got = _run_oos(g, y, cfg, horizon=1, direction={"g": 1})
    _assert_all_consistent(compare_rolling_oos(got, g, y, cfg, horizon=1, direction={"g": 1}))
    oos = np.array([s["oos_ic"] for s in got["features"]["g"]["splits_sampled"]])
    assert got["features"]["g"]["direction"] == 1
    assert _rel(got["features"]["g"]["oos_stability"]["oos_hit_rate"], float(np.mean(oos > 0))) <= REL_TOL
    zero = _run_oos(g, y, cfg, horizon=1, direction={"g": 0})
    st = zero["features"]["g"]["oos_stability"]
    assert math.isnan(st["oos_hit_rate"]) and math.isnan(st["degradation_ratio"])
    _assert_all_consistent(compare_rolling_oos(zero, g, y, cfg, horizon=1, direction={"g": 0}))


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
    """真實 kline 上之因果特徵家族（只用 0..t；命名同 FF `close_1h_<類>_<指標>_<週期>`）：EMA 水位、ROC 動量、
    對 SMA 偏離、報酬波動率。"""
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


def _real_label_with_gap(close: pd.Series, horizon: int) -> pd.Series:
    """真實標籤加中段缺價（第 900–939 根 close 視為缺 ⇒ 該段與其前 h 根之標籤 NaN）。"""
    c = close.copy()
    c.iloc[900:940] = np.nan
    return _real_label(c, horizon)


#: 真實資料之 ICIR 窗（1h 上 IC 頁之 ICIR 窗為 252，`ic_engine.py:1553-1565` 以 12h 參考週期換算 21）
REAL_PS = {"icir_window": 252}


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_sensitivity_oos_fields_closed() -> None:
    """真實 kline 小輸入（四家族＋稀疏特徵）執行產品兩模組：實際欄位路徑集合 == `MODULE_FIELDS` 鍵集合（逐模組）；
    oracle 項皆有說明。"""
    close = _real_close()
    df = _real_families(close).assign(close_1h_sparse_RET0=_real_sparse(close))
    label = _real_label(close)
    ps = _run_ps(df, label, {}, REAL_PS)
    oos = _run_oos(df, label, horizon=1)
    keys = _field_keys("parameter_sensitivity", ps) | _field_keys("rolling_oos", oos)
    assert keys == set(MODULE_FIELDS), f"清冊多 {sorted(set(MODULE_FIELDS) - keys)}；少 {sorted(keys - set(MODULE_FIELDS))}"
    assert {v["oracle"] for v in MODULE_FIELDS.values()} - {NON_STAT} <= set(ORACLE_ITEMS)


def _real_ps_thresholds(close: pd.Series) -> Dict[str, Dict[str, float]]:
    """依 oracle 之真實家族 ic_std 取兩組門檻：寬（全部 ic_std 之上、icir 門檻寫死者不論）與窄（使至少一族 high）。"""
    ref = ref_parameter_sensitivity(_real_families(close), _real_label(close), {}, REAL_PS)
    stds = sorted(f["stability_metrics"]["ic_std_across_params"] for f in ref["families"].values())
    return {"wide": {**REAL_PS, "ic_std_threshold_low": 0.99, "ic_std_threshold_high": 1.0},
            "narrow": {**REAL_PS, "ic_std_threshold_low": stds[0] / 2, "ic_std_threshold_high": stds[0]}}


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("method", METHODS)
def test_parameter_sensitivity_matches_ref_on_real_kline(method: str) -> None:
    """真實 BTCUSDT 1h 2,000 根 × 三方法：`batch_analyze` 逐統計欄 == oracle；每一統計欄至少一值為有限；high／low 名單
    非空由寬窄兩組門檻合併涵蓋。"""
    close = _real_close()
    df, label = _real_families(close), _real_label(close)
    lists = ("parameter_sensitivity/high_risk_families", "parameter_sensitivity/robust_families")
    seen = {"high": False, "low": False}
    for tag, cfg in _real_ps_thresholds(close).items():
        got = _run_ps(df, label, {}, cfg, method=method)
        res = compare_parameter_sensitivity(got, df, label, {}, cfg, method=method)
        _assert_all_consistent(res)
        _assert_non_stat_equal("parameter_sensitivity", got, ref_parameter_sensitivity(df, label, {}, cfg, method=method))
        assert got["summary"]["total_families"] == 4
        for f, r in res.items():
            if f not in lists:
                assert r["n_finite"] >= 1, f"{tag}/{f}：無有限值（資料不足不算已驗）"
        seen["high"] |= bool(got["high_risk_families"])
        seen["low"] |= bool(got["robust_families"])
    assert seen["high"], "須有 high 家族"
    if method == "spearman":
        assert seen["low"] or all(
            f["stability_metrics"]["icir_std_across_params"] >= 0.15
            for f in ref_parameter_sensitivity(df, label, {}, REAL_PS)["families"].values()), "low 名單：依定義不可達以外須出現"


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("horizon", [1, 21])
def test_rolling_oos_matches_ref_on_real_kline(horizon: int) -> None:
    """真實 BTCUSDT 1h 2,000 根（預設 train 252／test 63／step 21）、h 根前瞻標籤：`validate_batch` 逐統計欄 == purge ≥ h
    之 oracle（SPEC ⑳ SO-1），每一統計欄至少一特徵得有限值；稀疏特徵走跳過分支。"""
    close = _real_close()
    df = _real_families(close).assign(close_1h_sparse_RET0=_real_sparse(close))
    label = _real_label(close, horizon)
    got = _run_oos(df, label, horizon=horizon)
    res = compare_rolling_oos(got, df, label, horizon=horizon)
    _assert_all_consistent(res)
    _assert_non_stat_equal("rolling_oos", got, ref_rolling_oos(df, label, horizon=horizon))
    for f, r in res.items():
        assert r["n_finite"] >= 1, f"{f}：無有限值（資料不足不算已驗）"
    assert got["features"]["close_1h_sparse_RET0"]["skipped"] is True
    assert len({v.get("assessment") for v in got["features"].values()} - {None}) >= 2


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("horizon", [1, 21])
def test_rolling_oos_matches_ref_on_real_kline_with_mid_gap(horizon: int) -> None:
    """真實 kline 中段缺價（40 根）：切分於原始位置、各段逐對有限值 == oracle（三方法之 spearman；IC-13）。"""
    close = _real_close()
    df = _real_families(close)
    label = _real_label_with_gap(close, horizon)
    got = _run_oos(df, label, horizon=horizon)
    _assert_all_consistent(compare_rolling_oos(got, df, label, horizon=horizon))
    assert got["config"]["n_splits"] == len(_ref_splits(len(df.index), 252, 63, 21, 5)[0])


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("horizon", [1, 21])
def test_rolling_oos_matches_purged_oracle_on_real_kline(horizon: int) -> None:
    """偷看未來（SPEC ⑳ SO-1）：真實 BTCUSDT 1h 四家族特徵、h 根前瞻標籤：`validate_batch` 逐統計欄 == purge ≥ h 之 oracle
    （訓練段去末 h 根）。"""
    close = _real_close()
    df, label = _real_families(close), _real_label(close, horizon)
    got = _run_oos(df, label, horizon=horizon)
    _assert_all_consistent(compare_rolling_oos(got, df, label, horizon=horizon))


def _dev20(close: pd.Series) -> pd.Series:
    return (close / close.rolling(20).mean() - 1.0).rename("dev20")


def _bump_test_segment(close: pd.Series, cfg: dict) -> pd.Series:
    """第 0 切分測試段（原始位置 [train, train+test)）之 close 乘 1.07。"""
    tr_end, te_end = int(cfg["train_window"]), int(cfg["train_window"]) + int(cfg["test_window"])
    bumped = close.copy()
    bumped.iloc[tr_end:te_end] *= 1.07
    return bumped


@pytest.mark.requires_kline
@pytest.mark.parametrize("horizon", [1, 21])
def test_ref_purged_rolling_oos_is_invariant_to_test_prices(horizon: int) -> None:
    """oracle 自證（使主斷言可證偽）：擾動第 0 切分測試段之真實 close ⇒ 未 purge（h=0）之 IS IC 改變，purge ≥ h 者不變。"""
    cfg = RollingOOSConfig().model_dump()
    close = _real_close()
    out = {}
    for tag, c in (("orig", close), ("bump", _bump_test_segment(close, cfg))):
        f, y = _dev20(c).to_frame(), _real_label(c, horizon)
        out[tag] = (ref_rolling_oos(f, y, horizon=0)["features"]["dev20"]["splits_sampled"][0]["is_ic"],
                    ref_rolling_oos(f, y, horizon=horizon)["features"]["dev20"]["splits_sampled"][0]["is_ic"])
    assert out["orig"][0] != out["bump"][0], "前提：未 purge 之 IS IC 須受測試段價格影響"
    assert out["orig"][1] == out["bump"][1], "purge ≥ h 之 IS IC 須不受測試段價格影響"


@pytest.mark.requires_kline
@pytest.mark.parametrize("horizon", [1, 21])
def test_rolling_oos_train_labels_must_not_see_test_prices(horizon: int) -> None:
    """偷看未來（SPEC ⑳ SO-1）：真實 BTCUSDT 1h、標籤＝h 根前瞻報酬。擾動第 0 切分測試段之 close 後，該切分之 IS IC 須不變
    （訓練段只用 [start, train_end−h)，其標籤不讀測試段價格）。"""
    cfg = RollingOOSConfig().model_dump()
    close = _real_close()
    vals = []
    for c in (close, _bump_test_segment(close, cfg)):
        out = _run_oos(_dev20(c).to_frame(), _real_label(c, horizon), horizon=horizon)
        vals.append(out["features"]["dev20"]["splits_sampled"][0])
    assert vals[0]["split_id"] == vals[1]["split_id"] == 0
    assert vals[0]["is_ic"] == vals[1]["is_ic"], f"h={horizon}：IS IC 原 {vals[0]['is_ic']!r} → 擾動測試段後 " \
                                                 f"{vals[1]['is_ic']!r}"


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_parameter_sensitivity_icir_invariant_under_monotone_transform_on_real_kline() -> None:
    """真實 BTCUSDT 1h：EMA 水位家族與其對數（嚴格遞增變換）之 ic_mean 與 icir 皆相同，且 icir == oracle 滾動 ICIR。"""
    close = _real_close()
    ema = _real_families(close)[[f"close_1h_trend_EMA_{k}" for k in (5, 10, 20, 50)]]
    log_ema = np.log(ema).rename(columns=lambda c: c.replace("trend_EMA", "trend_LOGEMA"))
    label = _real_label(close)
    got = _run_ps(pd.concat([ema, log_ema], axis=1), label, {}, REAL_PS)
    a = {r["param_value"]: r for r in got["families"]["close_1h_trend_EMA"]["sensitivity_table"]}
    b = {r["param_value"]: r for r in got["families"]["close_1h_trend_LOGEMA"]["sensitivity_table"]}
    for k in a:
        assert _rel(b[k]["ic_mean"], a[k]["ic_mean"]) <= REL_TOL, "前提：Spearman IC 遞增變換不變"
    for k in a:
        exp = ref_rolling_icir(ema[f"close_1h_trend_EMA_{k}"], label, 252)
        assert _rel(b[k]["icir"], a[k]["icir"]) <= REL_TOL and _rel(a[k]["icir"], exp) <= REL_TOL, \
            f"EMA_{k}: icir 水位 {a[k]['icir']} vs 對數 {b[k]['icir']}；oracle {exp}"


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_parameter_sensitivity_best_param_sign_flip_invariant_on_real_kline() -> None:
    """真實 BTCUSDT 1h EMA 水位家族（四變體 IC 皆 < 0）：best_param == |IC| 最大之變體、best_param_direction −1。"""
    close = _real_close()
    ema = _real_families(close)[[f"close_1h_trend_EMA_{k}" for k in (5, 10, 20, 50)]]
    label = _real_label(close)
    got = _run_ps(ema, label, {}, REAL_PS)
    fam = got["families"]["close_1h_trend_EMA"]
    ics = {r["param_value"]: r["ic_mean"] for r in fam["sensitivity_table"]}
    assert all(v < 0 for v in ics.values()), f"前提：家族 IC 皆為負（實得 {ics}）"
    exp = max(ics, key=lambda k: abs(ics[k]))
    assert fam["stability_metrics"]["best_param"] == exp, f"IC {ics}；產品 {fam['stability_metrics']['best_param']}"
    assert fam["stability_metrics"]["best_param_direction"] == -1


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_rolling_oos_sign_flip_invariant_on_real_kline() -> None:
    """真實 BTCUSDT 1h EMA_5 水位（OOS IC 幾乎全負）與其取負：評等與 hit／degradation 相同、direction 相反。"""
    close = _real_close()
    ema5 = _real_families(close)["close_1h_trend_EMA_5"]
    pair = pd.DataFrame({"ema5": ema5, "neg_ema5": -ema5})
    label = _real_label(close)
    got = _run_oos(pair, label, horizon=1)
    a, b = got["features"]["ema5"], got["features"]["neg_ema5"]
    assert a["assessment"] == b["assessment"] and a["direction"] == -b["direction"] == -1, (a, b)
    for k in ("oos_hit_rate", "degradation_ratio"):
        assert _rel(a["oos_stability"][k], b["oos_stability"][k]) <= REL_TOL, (k, a["oos_stability"], b["oos_stability"])
