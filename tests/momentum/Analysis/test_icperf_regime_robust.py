"""ICPERF Task 0.4 ㉓ `summary_table.regime_robust` oracle 測試（docs/ICPERF_SPEC.md v5.35 Task 0.4 擴列表 ㉓ 列）。

契約（SPEC ㉓「修正」欄）：由同請求 `grouped_ic.by_regime` 導出（不另算 IC）。合格 regime＝該 regime 之 IC 有限且
（特徵, 標籤）有限配對數 ≥ `regime_robust_min_samples`（預設 30）；合格 ≥ 2 ⇒ True ⟺ 每一合格 regime 之 d·IC > 0
（d＝同列 `direction`＝sign(ic_mean)），任一 ≤ 0 ⇒ False；合格 < 2 ⇒ None／`insufficient_regimes`；`by_regime` 未算
⇒ None／`regime_analysis_off`。regime 標籤須 PIT。

oracle（不呼叫被測模組之計算函式）：
- 規則型 regime 遮罩：pandas `ewm`／`rolling(55).std`／`expanding(min_periods=100).quantile`（只用過去）；
- kmeans regime 標籤：測試自寫之段因果流程（pandas 特徵、sklearn `StandardScaler`＋`KMeans` 只以段前 prefix fit、
  prefix 再預測依 cluster 平均波動降序命名、首段委派同一 PIT 規則標籤）；
- 逐 regime IC：`scipy.stats.spearmanr`／`pearsonr`／`kendalltau`（兩者皆有限之配對）；
- regime_robust：依上列契約之測試自寫判定。

真實資料：`data_cache/feature_klines/kline_cache.h5`（BTCUSDT 1h 末 1,200 根；端到端用 BTCUSDT 4h 末 2,000 根、
跨標的用 BTCUSDT／ETHUSDT 4h）。構造特徵（以真實標籤組成，專供命中 True／False／None 各分支與邊界）與真實因果特徵
（過去 1 根報酬、對 20 根均線偏離）並列。本檔之 requires_kline 測試須經共用監看執行（autouse 自證，同
test_icperf_correctness.py）。
"""

from __future__ import annotations

import json
import math
import os
import warnings
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import h5py
import numpy as np
import pandas as pd
import pytest
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from momentum.Analysis import ic_filter_orchestrator as orch_mod
from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.Analysis.regime_detector import RegimeDetector
from momentum.FeatureEngineering.feature_naming import stamp_h5_feature_naming_version
from momentum.factories import create_ic_analyzer, create_kline_storage_manager

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
HEAVY_MARKERS = ("slow", "requires_kline")
#: IC 比對之絕對誤差門檻（同模組 scipy 對照之浮點容差）
IC_ATOL = 1e-12
SCIPY: Dict[str, Callable[..., Any]] = {
    "spearman": stats.spearmanr,
    "pearson": stats.pearsonr,
    "kendall": stats.kendalltau,
}
#: SPEC ㉓ 預設（code review r48 CODEX-P1-04）
MIN_SAMPLES = 30
RULE_DEFS = {"high_vol_percentile": 80, "low_vol_percentile": 20}
KMEANS_CFG = {"n_clusters": 4, "lookback": 55, "min_samples_for_fit": 100, "refit_interval": 50}
#: 規則型／kmeans 之語義（regime_detector 文件：依 cluster 平均波動降序）
KMEANS_NAMES_4 = ("high_vol_trending", "mid_vol_trending", "mid_vol_ranging", "low_vol_ranging")
REASONS = {"regime_analysis_off", "insufficient_regimes"}


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


# ── 真實資料 ────────────────────────────────────────────────────────────────────────────────────────


def _real_kline(rows: int, timeframe: str = "1h", symbol: str = "BTCUSDT") -> pd.DataFrame:
    """真實 kline 末 rows 根（close／volume，float64；UTC 時間索引）。"""
    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        data = f[f"{symbol}/{timeframe}/data"][-rows:]
    idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True)
    return pd.DataFrame(
        {"close": data["close"].astype("float64"), "volume": data["volume"].astype("float64")}, index=idx
    )


def _forward_return(close: pd.Series) -> pd.Series:
    """標籤＝1 根前瞻簡單報酬 close[t+1]／close[t] − 1。"""
    return (close.shift(-1) / close - 1.0).rename("label")


def _causal_features(close: pd.Series) -> pd.DataFrame:
    """真實 kline 上之因果特徵（只用 0..t）。"""
    return pd.DataFrame({
        "ret1": close / close.shift(1) - 1.0,
        "dev20": close / close.rolling(20).mean() - 1.0,
    })


# ── oracle：regime 標籤 ─────────────────────────────────────────────────────────────────────────────


def oracle_rule_masks(close: pd.Series, lookback: int = 55, lo_pct: float = 20.0, hi_pct: float = 80.0,
                      min_samples: int = 100) -> Dict[str, np.ndarray]:
    """規則型 regime（bull／bear／high_vol／low_vol）之獨立 pandas 實作；門檻＝至 t 之有限波動 expanding 分位
    （有限觀測 < min_samples ⇒ 無門檻、high／low 皆 False）。"""
    ema = close.ewm(span=lookback, adjust=False).mean()
    vol = (close / close.shift(1) - 1.0).rolling(lookback).std()
    lo = vol.expanding(min_periods=min_samples).quantile(lo_pct / 100.0)
    hi = vol.expanding(min_periods=min_samples).quantile(hi_pct / 100.0)
    return {
        "bull": (close > ema).to_numpy(dtype=bool),
        "bear": (close < ema).to_numpy(dtype=bool),
        "high_vol": (vol >= hi).to_numpy(dtype=bool),
        "low_vol": (vol <= lo).to_numpy(dtype=bool),
    }


def _oracle_rule_labels(close: pd.Series, lookback: int) -> np.ndarray:
    """kmeans 首段委派之 PIT 規則標籤（四名語義；bear 含 close == ema）。"""
    ema = close.ewm(span=lookback, adjust=False).mean()
    vol = (close / close.shift(1) - 1.0).rolling(lookback).std()
    if vol.notna().sum() < 2:
        return np.full(len(close), "unknown", dtype=object)
    lo = vol.expanding(min_periods=100).quantile(0.2)
    hi = vol.expanding(min_periods=100).quantile(0.8)
    bull = (close > ema).to_numpy()
    bear = (close <= ema).to_numpy()
    high = (vol >= hi).to_numpy()
    low = (vol <= lo).to_numpy()
    out = np.full(len(close), "mid_vol_ranging", dtype=object)
    out[bull & high] = "high_vol_trending"
    out[bull & ~high & ~low] = "mid_vol_trending"
    out[bear & high] = "high_vol_trending"
    out[bear & ~high & ~low] = "mid_vol_ranging"
    out[low] = "low_vol_ranging"
    return out


def oracle_kmeans_labels(close: pd.Series, volume: pd.Series, n_clusters: int = 4, lookback: int = 55,
                         min_fit: int = 100, refit: int = 50, seed: int = 42) -> np.ndarray:
    """kmeans regime 之獨立段因果實作：段 [p_k, p_{k+1}) 只以 [0, p_k) 之有效列 fit（標準化＋KMeans）、prefix 再預測後依
    cluster 平均波動降序命名；p_0 = 0 之首段（prefix 不足）用 PIT 規則標籤；無效列（特徵含 NaN）標空字串。"""
    assert n_clusters == 4
    vol = (close / close.shift(1) - 1.0).rolling(lookback, min_periods=max(5, lookback // 2)).std()
    ema = close.ewm(span=lookback, adjust=False).mean()
    rng = close.rolling(lookback, min_periods=5).max() - close.rolling(lookback, min_periods=5).min()
    feats = {"volatility": vol, "trend_strength": (close - ema).abs() / rng.where(rng != 0)}
    vma = volume.rolling(lookback, min_periods=5).mean()
    feats["volume_ratio"] = volume / vma.where(vma != 0)
    x = pd.DataFrame(feats, index=close.index)
    valid = x.notna().all(axis=1).to_numpy()
    xv = x[valid]
    n = len(xv)
    min_fit = max(min_fit, n_clusters * 5)
    assert n >= min_fit, "前提：有效列足以進入 kmeans 段"
    rule = _oracle_rule_labels(close[valid], lookback)
    labels = np.full(n, "unknown", dtype=object)
    bounds = list(range(min_fit, n, refit)) + [n]
    start = 0
    for end in bounds:
        if start < min_fit:
            labels[start:end] = rule[start:end]
        else:
            scaler = StandardScaler().fit(xv.iloc[:start].to_numpy())
            x_train = scaler.transform(xv.iloc[:start].to_numpy())
            model = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10, max_iter=300).fit(x_train)
            prefix = model.predict(x_train)
            vols = xv["volatility"].to_numpy()[:start]
            ids = sorted(set(int(c) for c in prefix))
            mean_vol = {c: float(np.mean(vols[prefix == c])) for c in ids}
            order = sorted(ids, key=lambda c: mean_vol[c], reverse=True)
            names = {c: KMEANS_NAMES_4[i] for i, c in enumerate(order)}
            seg = model.predict(scaler.transform(xv.iloc[start:end].to_numpy()))
            labels[start:end] = [names.get(int(c), "unknown") for c in seg]
        start = end
    out = np.full(len(close), "", dtype=object)
    out[valid] = labels
    return out


def _kmeans_masks(labels: np.ndarray) -> Dict[str, np.ndarray]:
    names = sorted({str(v) for v in labels if v not in ("", "unknown")})
    return {name: labels == name for name in names}


# ── oracle：逐 regime IC 與 regime_robust ───────────────────────────────────────────────────────────


def oracle_ic(x: np.ndarray, y: np.ndarray, method: str) -> Tuple[float, int]:
    """（IC, 有限配對數）：兩者皆有限之配對以 scipy 對應函式；配對 < 2 或任一常數 ⇒ NaN。"""
    ok = np.isfinite(x) & np.isfinite(y)
    n = int(ok.sum())
    if n < 2 or np.std(x[ok]) == 0 or np.std(y[ok]) == 0:
        return math.nan, n
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return float(SCIPY[method](x[ok], y[ok])[0]), n


def oracle_by_regime(features: pd.DataFrame, label: pd.Series, masks: Mapping[str, np.ndarray],
                     method: str) -> Dict[str, Dict[str, Tuple[float, int]]]:
    y = label.to_numpy(dtype=float)
    return {
        regime: {f: oracle_ic(features[f].to_numpy(dtype=float)[m], y[m], method) for f in features.columns}
        for regime, m in masks.items()
    }


def oracle_regime_robust(direction: int, per_regime: Optional[Mapping[str, Tuple[float, int]]],
                         min_samples: int) -> Tuple[Optional[bool], Optional[str]]:
    if per_regime is None:
        return None, "regime_analysis_off"
    qualified = [ic for ic, n in per_regime.values() if math.isfinite(ic) and n >= min_samples]
    if len(qualified) < 2:
        return None, "insufficient_regimes"
    return all(direction * ic > 0 for ic in qualified), None


def _sign(v: float) -> int:
    return 0 if (not math.isfinite(v) or v == 0) else (1 if v > 0 else -1)


# ── 構造特徵（真實標籤組成；專供命中各分支） ───────────────────────────────────────────────────────


def _branch_features(close: pd.Series, label: pd.Series, masks: Mapping[str, np.ndarray],
                     a: str, b: str, exclude: Sequence[str] = ()) -> pd.DataFrame:
    """以兩個互斥 regime a、b（且不在 exclude 之任一 regime）為底建構造特徵：
    pos_all＝標籤（各 regime IC＝1）；neg_all＝−標籤（direction −1，對齊後 > 0）；mixed＝a 列為標籤、其餘為 −標籤
    （a 正 b 負）；sparse＝只在 a 之純列有值（合格 regime 1 個）；b30／b29＝a 之純列全部＋b 之純列恰 30／29 列
    （合格門檻邊界）；const＝常數（IC 非有限）；另附真實因果特徵 ret1、dev20。"""
    y = label.to_numpy(dtype=float)
    n = len(y)
    other = np.zeros(n, dtype=bool)
    for name in exclude:
        other |= masks[name]
    pure_a = masks[a] & ~masks[b] & ~other
    pure_b = masks[b] & ~masks[a] & ~other
    fin = np.isfinite(y)
    idx_b = np.flatnonzero(pure_b & fin)
    assert int((pure_a & fin).sum()) >= MIN_SAMPLES and idx_b.size >= MIN_SAMPLES, "前提：兩 regime 之純列足以構造邊界案"
    feats = _causal_features(close)
    feats["pos_all"] = y
    feats["neg_all"] = -y
    feats["mixed"] = np.where(masks[a], y, -y)
    feats["sparse"] = np.where(pure_a, y, np.nan)
    for k in (MIN_SAMPLES, MIN_SAMPLES - 1):
        keep = pure_a.copy()
        keep[idx_b[:k]] = True
        feats[f"b{k}"] = np.where(keep, y, np.nan)
    feats["const"] = 1.0
    feats["zero_dir"] = y
    return feats


def _product_by_regime(features: pd.DataFrame, label: pd.Series, kline: pd.DataFrame, regime_method: str,
                       method: str) -> Tuple[Dict[str, Any], Dict[str, Dict[str, int]]]:
    cfg = {"by_regime": True, "regime_method": regime_method, "regime_definitions": dict(RULE_DEFS),
           "regime_kmeans": dict(KMEANS_CFG), "method": method}
    counts: Dict[str, Dict[str, int]] = {}
    grouped = ICEngine({"methods": [method]}).compute_grouped_ic(
        features, label, kline[["close", "volume"]], {}, cfg, regime_pair_counts=counts
    )
    return grouped, counts


def _product_summary(features: pd.DataFrame, grouped: Any, counts: Any, point_ic: Mapping[str, float],
                     min_samples: int = MIN_SAMPLES) -> Dict[str, dict]:
    """產品 summary 組裝（ic_filter_orchestrator `_build_summary_table`；ic_mean 取 point_ic）。"""
    rows = ICFilterOrchestrator._build_summary_table(
        SimpleNamespace(), list(features.columns), {}, {}, {}, {}, {}, {}, point_ic=dict(point_ic),
        grouped_ic=grouped, regime_pair_counts=counts, regime_robust_min_samples=min_samples,
    )
    return {r["feature_name"]: r for r in rows}


def _point_ic(features: pd.DataFrame, label: pd.Series) -> Dict[str, float]:
    """summary 之 ic_mean 來源（測試指定）：全段 spearman；zero_dir 設 0（direction 0 之分支）。"""
    out = {f: oracle_ic(features[f].to_numpy(dtype=float), label.to_numpy(dtype=float), "spearman")[0]
           for f in features.columns}
    if "zero_dir" in out:
        out["zero_dir"] = 0.0
    return out


def robust_mismatches(rows: Mapping[str, dict], oracle: Mapping[str, Mapping[str, Tuple[float, int]]],
                      min_samples: int = MIN_SAMPLES, computed: bool = True) -> List[str]:
    """產品 summary 之 regime_robust／reason 與 oracle 判定不一致之特徵清單（含 direction 須為 sign(ic_mean)）。"""
    bad: List[str] = []
    for f, row in rows.items():
        d = int(row["direction"])
        if d != _sign(float(row["ic_mean"]) if row["ic_mean"] is not None else math.nan):
            bad.append(f"{f}: direction {d} != sign(ic_mean)")
        per = {r: v[f] for r, v in oracle.items()} if computed else None
        exp = oracle_regime_robust(d, per, min_samples)
        got = (row["regime_robust"], row["regime_robust_reason"])
        if got != exp or (got[0] is not None and not isinstance(got[0], bool)):
            bad.append(f"{f}: got {got} != oracle {exp}")
    return bad


def _assert_by_regime_matches(grouped: Mapping[str, Any], counts: Mapping[str, Mapping[str, int]],
                              oracle: Mapping[str, Mapping[str, Tuple[float, int]]]) -> None:
    """產品 by_regime（IC）與有限配對數 == oracle；regime 名稱集合相同（空 regime 於產品為 {}，配對數 0）。"""
    by = grouped["by_regime"]
    assert set(by) == set(oracle), f"regime 集合：產品 {sorted(by)} vs oracle {sorted(oracle)}"
    for regime, per in oracle.items():
        for f, (ic, n) in per.items():
            assert counts.get(regime, {}).get(f, 0) == n, f"{regime}/{f} 有限配對數 {counts.get(regime, {}).get(f)} vs {n}"
            got = (by[regime] or {}).get(f, math.nan)
            if math.isnan(ic):
                assert got is None or math.isnan(float(got)), f"{regime}/{f}：產品 {got} vs oracle NaN"
            else:
                assert abs(float(got) - ic) <= IC_ATOL, f"{regime}/{f}：產品 {got} vs oracle {ic}"


def _expect_branches(rows: Mapping[str, dict]) -> None:
    """構造特徵之分支必達（防 oracle 與產品同錯而全落同一路）。"""
    assert rows["pos_all"]["regime_robust"] is True
    assert rows["neg_all"]["regime_robust"] is True and rows["neg_all"]["direction"] == -1
    assert rows["mixed"]["regime_robust"] is False
    assert rows["zero_dir"]["regime_robust"] is False and rows["zero_dir"]["direction"] == 0
    assert (rows["sparse"]["regime_robust"], rows["sparse"]["regime_robust_reason"]) == (None, "insufficient_regimes")
    assert (rows["const"]["regime_robust"], rows["const"]["regime_robust_reason"]) == (None, "insufficient_regimes")
    assert rows[f"b{MIN_SAMPLES}"]["regime_robust"] is True
    assert (rows[f"b{MIN_SAMPLES - 1}"]["regime_robust"],
            rows[f"b{MIN_SAMPLES - 1}"]["regime_robust_reason"]) == (None, "insufficient_regimes")


# ── 秒級：設定與判定之純邏輯 ───────────────────────────────────────────────────────────────────────


def test_regime_robust_min_samples_setting_default_30() -> None:
    """分組設定 `regime_robust_min_samples` 入 schema，預設 30（SPEC ㉓；code review r48 CODEX-P1-04）。"""
    cfg = ICConfig()
    assert cfg.ic_calculation.grouped_analysis.regime_robust_min_samples == MIN_SAMPLES
    assert ICConfig.model_validate(
        {"ic_calculation": {"grouped_analysis": {"regime_robust_min_samples": 50}}}
    ).ic_calculation.grouped_analysis.regime_robust_min_samples == 50


def test_regime_robust_reason_closed_set() -> None:
    """`regime_robust_reason` 封閉值集＝{regime_analysis_off, insufficient_regimes}（產品常數與契約同）。"""
    assert set(orch_mod.REGIME_ROBUST_REASONS) == REASONS


#: 判定邊界之逐 regime（IC, 有限配對數）表：每列＝(特徵, ic_mean, {regime: (IC, n)})；值為手寫之精確輸入
_DECISION_CASES: Tuple[Tuple[str, float, Dict[str, Tuple[float, int]]], ...] = (
    ("all_pos", 0.1, {"bull": (0.2, 40), "bear": (0.05, 40)}),
    ("mixed", 0.1, {"bull": (0.2, 40), "bear": (-0.05, 40)}),
    ("neg_aligned", -0.1, {"bull": (-0.2, 40), "bear": (-0.05, 40)}),
    ("neg_mixed", -0.1, {"bull": (-0.2, 40), "bear": (0.05, 40)}),
    ("zero_ic_regime", 0.1, {"bull": (0.2, 40), "bear": (0.0, 40)}),
    ("zero_direction", 0.0, {"bull": (0.2, 40), "bear": (0.05, 40)}),
    ("one_qualified", 0.1, {"bull": (0.2, 40), "bear": (-0.3, MIN_SAMPLES - 1)}),
    ("at_threshold", 0.1, {"bull": (0.2, MIN_SAMPLES), "bear": (0.1, MIN_SAMPLES)}),
    ("nan_regime", 0.1, {"bull": (0.2, 40), "bear": (math.nan, 40), "range": (-0.1, 40)}),
    ("nan_skipped_rest_pos", 0.1, {"bull": (0.2, 40), "bear": (math.nan, 40), "range": (0.1, 40)}),
    ("three_one_neg", 0.1, {"bull": (0.2, 40), "bear": (0.1, 40), "range": (-0.01, 40)}),
)


def _decision_inputs() -> Tuple[Dict[str, Any], Dict[str, Dict[str, int]], Dict[str, float],
                                Dict[str, Dict[str, Tuple[float, int]]]]:
    """手寫表 ⇒ 產品之 grouped_ic／pair_counts／point_ic 與測試 oracle 之 {regime: {特徵: (IC, n)}}。"""
    regimes = sorted({r for _f, _m, per in _DECISION_CASES for r in per})
    by: Dict[str, Dict[str, float]] = {r: {} for r in regimes}
    counts: Dict[str, Dict[str, int]] = {r: {} for r in regimes}
    oracle: Dict[str, Dict[str, Tuple[float, int]]] = {r: {} for r in regimes}
    for f, _m, per in _DECISION_CASES:
        for r in regimes:
            ic, n = per.get(r, (math.nan, 0))
            by[r][f] = ic
            counts[r][f] = n
            oracle[r][f] = (ic, n)
    return {"by_regime": by}, counts, {f: m for f, m, _p in _DECISION_CASES}, oracle


def test_regime_robust_decision_matches_oracle_exact() -> None:
    """產品 `_build_summary_table`（含 `_regime_robust_fields`）於手寫逐 regime IC／配對數表上 == 本檔 oracle 判定，
    且各分支必達（True／False／None、direction −1 對齊、direction 0、IC＝0、配對數 29／30 邊界、IC 非有限略過）。
    秒級：產品判定改壞（如恆 True、恆 None、忽略 direction、門檻改 >）⇒ 本測試紅（code review r51 CODEX-R51-P1-01）。"""
    grouped, counts, point_ic, oracle = _decision_inputs()
    rows = {r["feature_name"]: r for r in ICFilterOrchestrator._build_summary_table(
        SimpleNamespace(), [f for f, _m, _p in _DECISION_CASES], {}, {}, {}, {}, {}, {}, point_ic=point_ic,
        grouped_ic=grouped, regime_pair_counts=counts, regime_robust_min_samples=MIN_SAMPLES)}
    assert robust_mismatches(rows, oracle) == []
    got = {f: (r["regime_robust"], r["regime_robust_reason"]) for f, r in rows.items()}
    assert got == {
        "all_pos": (True, None), "mixed": (False, None), "neg_aligned": (True, None), "neg_mixed": (False, None),
        "zero_ic_regime": (False, None), "zero_direction": (False, None),
        "one_qualified": (None, "insufficient_regimes"), "at_threshold": (True, None),
        "nan_regime": (False, None), "nan_skipped_rest_pos": (True, None), "three_one_neg": (False, None),
    }
    off = {r["feature_name"]: r for r in ICFilterOrchestrator._build_summary_table(
        SimpleNamespace(), ["all_pos"], {}, {}, {}, {}, {}, {}, point_ic={"all_pos": 0.1},
        grouped_ic={}, regime_pair_counts={}, regime_robust_min_samples=MIN_SAMPLES)}
    assert (off["all_pos"]["regime_robust"], off["all_pos"]["regime_robust_reason"]) == (None, "regime_analysis_off")


# ── 真實 kline：規則型與 kmeans 兩分支 ─────────────────────────────────────────────────────────────


@pytest.mark.requires_kline
def test_rule_regime_masks_match_pandas_oracle_and_prefix_invariant() -> None:
    """規則型：產品遮罩（`ICEngine._build_regime_rule_masks`）== 獨立 pandas 實作；截斷未來（末 1/3、與任一中段點）
    不改既有遮罩（前綴不變性）。"""
    close = _real_kline(1200)["close"]
    engine = ICEngine({"methods": ["spearman"]})
    cfg = {"regime_definitions": dict(RULE_DEFS)}
    full = engine._build_regime_rule_masks(close, cfg)
    exp = oracle_rule_masks(close)
    for name, m in exp.items():
        np.testing.assert_array_equal(full[name].to_numpy(dtype=bool), m, err_msg=name)
    assert all(m.sum() > 0 for m in exp.values()), "前提：四個 regime 皆非空"
    for k in (800, 977):
        trunc = engine._build_regime_rule_masks(close.iloc[:k], cfg)
        for name in exp:
            np.testing.assert_array_equal(trunc[name].to_numpy(dtype=bool), full[name].to_numpy(dtype=bool)[:k],
                                          err_msg=f"{name} 截斷於 {k}")


@pytest.mark.requires_kline
def test_kmeans_regime_labels_match_oracle_and_prefix_invariant() -> None:
    """kmeans：產品 `RegimeDetector.detect` 標籤 == 測試自寫段因果實作；截斷未來（段界上與段中）不改既有標籤；
    regime 名稱 ≥ 2 個（資料充足判準）。"""
    k = _real_kline(1200)
    det = RegimeDetector(**{"n_clusters": 4, "lookback": 55, "min_samples_for_fit": 100, "refit_interval": 50})
    full = det.detect(k["close"], k["volume"]).labels
    exp = oracle_kmeans_labels(k["close"], k["volume"])
    np.testing.assert_array_equal(np.asarray(full, dtype=object), exp)
    assert len(_kmeans_masks(exp)) >= 2
    first_valid = int(np.flatnonzero(exp != "")[0])
    boundary = first_valid + 100 + 50 * 14  # 有效列座標之段界（refit 點 100＋50j）
    for cut in (boundary, boundary + 25):  # 段界上、段中
        trunc = det.detect(k["close"].iloc[:cut], k["volume"].iloc[:cut]).labels
        np.testing.assert_array_equal(np.asarray(trunc, dtype=object), np.asarray(full, dtype=object)[:cut],
                                      err_msg=f"截斷於 {cut}")


@pytest.mark.requires_kline
@pytest.mark.parametrize("method", sorted(SCIPY))
@pytest.mark.parametrize("regime_method", ["rule", "kmeans"])
def test_regime_robust_matches_oracle_on_real_kline(regime_method: str, method: str) -> None:
    """真實 BTCUSDT 1h 末 1,200 根：產品 `compute_grouped_ic` 之 by_regime 逐 regime IC 與有限配對數 == scipy oracle
    （regime 以 oracle 標籤取列）；summary 之 regime_robust／reason == oracle 判定（True／False／None 三路、
    insufficient_regimes 含配對數 29／30 邊界、IC 非有限、direction −1 對齊與 0）。"""
    k = _real_kline(1200)
    close = k["close"]
    label = _forward_return(close)
    if regime_method == "rule":
        masks = oracle_rule_masks(close)
        feats = _branch_features(close, label, masks, "bull", "bear", exclude=("high_vol", "low_vol"))
    else:
        masks = _kmeans_masks(oracle_kmeans_labels(close, k["volume"]))
        sizes = sorted(masks, key=lambda r: int(masks[r].sum()), reverse=True)
        feats = _branch_features(close, label, masks, sizes[0], sizes[1])
    grouped, counts = _product_by_regime(feats, label, k, regime_method, method)
    oracle = oracle_by_regime(feats, label, masks, method)
    _assert_by_regime_matches(grouped, counts, oracle)
    rows = _product_summary(feats, grouped, counts, _point_ic(feats, label))
    assert robust_mismatches(rows, oracle) == []
    _expect_branches(rows)


@pytest.mark.requires_kline
@pytest.mark.parametrize("regime_method", ["rule", "kmeans"])
def test_regime_robust_vectorized_path_on_real_kline(regime_method: str) -> None:
    """無缺值之輸入（`compute_ic` 走整矩陣 spearman 路徑）：真實因果特徵於暖機後、標籤有限之列上，by_regime 與
    regime_robust == oracle。"""
    k = _real_kline(1200)
    close = k["close"]
    label = _forward_return(close)
    feats = _causal_features(close)
    feats["neg_label"] = -label
    rows_ok = feats.notna().all(axis=1) & label.notna()
    k, feats, label = k[rows_ok], feats[rows_ok], label[rows_ok]
    close = k["close"]
    masks = oracle_rule_masks(close) if regime_method == "rule" else _kmeans_masks(
        oracle_kmeans_labels(close, k["volume"]))
    grouped, counts = _product_by_regime(feats, label, k, regime_method, "spearman")
    oracle = oracle_by_regime(feats, label, masks, "spearman")
    _assert_by_regime_matches(grouped, counts, oracle)
    rows = _product_summary(feats, grouped, counts, _point_ic(feats, label))
    assert robust_mismatches(rows, oracle) == []
    assert rows["neg_label"]["regime_robust"] is True and rows["neg_label"]["direction"] == -1


@pytest.mark.requires_kline
def test_regime_robust_min_samples_setting_changes_qualification() -> None:
    """設定 `regime_robust_min_samples` 生效：同一 by_regime，門檻 31 ⇒ b30 由 True 變 None／insufficient_regimes；
    門檻 29 ⇒ b29 由 None 變 True。"""
    k = _real_kline(1200)
    close = k["close"]
    label = _forward_return(close)
    masks = oracle_rule_masks(close)
    feats = _branch_features(close, label, masks, "bull", "bear", exclude=("high_vol", "low_vol"))
    grouped, counts = _product_by_regime(feats, label, k, "rule", "spearman")
    oracle = oracle_by_regime(feats, label, masks, "spearman")
    for thr in (MIN_SAMPLES - 1, MIN_SAMPLES + 1):
        rows = _product_summary(feats, grouped, counts, _point_ic(feats, label), min_samples=thr)
        assert robust_mismatches(rows, oracle, min_samples=thr) == []
    rows31 = _product_summary(feats, grouped, counts, _point_ic(feats, label), min_samples=MIN_SAMPLES + 1)
    assert (rows31[f"b{MIN_SAMPLES}"]["regime_robust"], rows31[f"b{MIN_SAMPLES}"]["regime_robust_reason"]) == \
        (None, "insufficient_regimes")
    rows29 = _product_summary(feats, grouped, counts, _point_ic(feats, label), min_samples=MIN_SAMPLES - 1)
    assert rows29[f"b{MIN_SAMPLES - 1}"]["regime_robust"] is True


@pytest.mark.requires_kline
def test_regime_robust_off_when_by_regime_not_computed() -> None:
    """by_regime 未算 ⇒ 全列 None／regime_analysis_off：分組 IC 未跑（grouped_ic 為空）、`by_regime` 關（其餘分組照算）。"""
    k = _real_kline(600)
    close = k["close"]
    label = _forward_return(close)
    feats = _causal_features(close)
    pic = _point_ic(feats, label)
    for grouped in ({}, None):
        rows = _product_summary(feats, grouped, {}, pic)
        assert robust_mismatches(rows, {}, computed=False) == []
        assert {(r["regime_robust"], r["regime_robust_reason"]) for r in rows.values()} == \
            {(None, "regime_analysis_off")}
    cfg = {"by_regime": False, "by_year": True}
    counts: Dict[str, Dict[str, int]] = {}
    grouped = ICEngine({"methods": ["spearman"]}).compute_grouped_ic(
        feats, label, k[["close", "volume"]], {}, cfg, regime_pair_counts=counts)
    assert "by_regime" not in grouped and "by_year" in grouped and counts == {}
    rows = _product_summary(feats, grouped, counts, pic)
    assert {(r["regime_robust"], r["regime_robust_reason"]) for r in rows.values()} == {(None, "regime_analysis_off")}


@pytest.mark.requires_kline
def test_regime_robust_mutation_fixed_true_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """判定靈敏度（真實資料）：`regime_robust` 固定 True 時，兩 regime 一正一負 IC 之特徵（mixed：bull 正、bear 負）必被
    本檔之真實資料比對（`robust_mismatches`）抓到；固定 None 亦然。產品本身之判定改壞由秒級
    `test_regime_robust_decision_matches_oracle_exact` 與上列真實資料 oracle 測試直接轉紅（code review r51 CODEX-R51-P1-01）。"""
    k = _real_kline(1200)
    close = k["close"]
    label = _forward_return(close)
    masks = oracle_rule_masks(close)
    feats = _branch_features(close, label, masks, "bull", "bear", exclude=("high_vol", "low_vol"))
    grouped, counts = _product_by_regime(feats, label, k, "rule", "spearman")
    oracle = oracle_by_regime(feats, label, masks, "spearman")
    assert oracle["bull"]["mixed"][0] > 0 > oracle["bear"]["mixed"][0], "前提：mixed 於兩 regime 一正一負"
    for fixed in ({"regime_robust": True, "regime_robust_reason": None},
                  {"regime_robust": None, "regime_robust_reason": "insufficient_regimes"}):
        monkeypatch.setattr(orch_mod, "_regime_robust_fields", lambda *_a, _v=fixed, **_k: dict(_v))
        rows = _product_summary(feats, grouped, counts, _point_ic(feats, label))
        bad = robust_mismatches(rows, oracle)
        assert any(b.startswith("mixed:") for b in bad), f"突變 {fixed} 未被抓到：{bad}"


# ── 端到端：主流程（stage5 summary）、refilter、跨標的 ──────────────────────────────────────────────


def _write_h5(path: Path, group_key: str, name: str, frame: pd.DataFrame, names_key: str) -> None:
    with h5py.File(path, "w") as f:
        stamp_h5_feature_naming_version(f.attrs)
        g = f.create_group(group_key)
        g.create_dataset(name, data=frame.to_numpy(dtype=np.float32))
        g.create_dataset("timestamps", data=(frame.index.asi8 // 10**9).astype(np.int64))
        g.create_dataset(names_key, data=np.array(frame.columns.tolist(), dtype=object),
                         dtype=h5py.string_dtype(encoding="utf-8"))


def _e2e_inputs(tmp_path: Path, rows: int = 2000) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, Dict[str, Path]]:
    """真實 BTCUSDT 4h 末 rows 根：特徵＝真實因果特徵＋±標籤（float32 交接，oracle 用同一 float32 值）。"""
    k = _real_kline(rows, timeframe="4h")
    close = k["close"]
    label = _forward_return(close).astype(np.float32).astype(np.float64).rename("return_1")
    feats = _causal_features(close)
    feats["pos_label"] = label
    feats["neg_label"] = -label
    feats = feats.astype(np.float32).astype(np.float64)
    paths = {"features": tmp_path / "features.h5", "labels": tmp_path / "labels.h5", "meta": tmp_path / "meta.json"}
    _write_h5(paths["features"], "BTCUSDT/4h", "features", feats, "feature_names")
    _write_h5(paths["labels"], "BTCUSDT/4h", "labels", label.to_frame(), "label_names")
    meta = {"symbol": "BTCUSDT", "timeframe": "4h", "case_id": "icperf_regime_robust"}
    meta.update({c: {"name": c, "category": "trend", "layer": 1, "data_source": "close"} for c in feats.columns})
    paths["meta"].write_text(json.dumps(meta), encoding="utf-8")
    return k, feats, label, paths


def _e2e_override(regime_method: Optional[str], include_regime: bool = True) -> Dict[str, Any]:
    grouped: Dict[str, Any] = {"by_regime": True, "by_year": False, "by_quarter": False, "by_category": False,
                               "by_data_source": False, "by_layer": False}
    if regime_method is not None:
        grouped["regime_method"] = regime_method
    return {
        "preprocessing": {"winsorization": {"enabled": False, "method": "none"},
                          "missing_values": {"max_fill_forward": 0, "min_coverage": 0.0}},
        "report": {"include_regime_analysis": include_regime, "include_decay_analysis": False,
                   "include_turnover_analysis": False, "include_quantile_curves": False,
                   "include_correlation_heatmap": False, "include_layer_analysis": False, "ai_summary": False},
        "turnover": {"enabled": False},
        "ic_calculation": {"grouped_analysis": grouped},
        "thresholds": {"ic_mean_min": -1.0, "icir_min": -1.0, "p_value_max": 1.0, "ic_hit_rate_min": 0.0,
                       "monotonicity_score_min": 0.0, "coverage_min": 0.0, "long_short_spread": {"enabled": False}},
    }


def _scope_rows(report: Mapping[str, Any], index: pd.DatetimeIndex) -> np.ndarray:
    """grouped IC 之列範圍：切分成立 ⇒ 測試段時間界內；否則全樣本。"""
    split = (report.get("metadata") or {}).get("ic_train_test_split") or {}
    if not split.get("applied"):
        return np.ones(len(index), dtype=bool)
    lo, hi = (pd.Timestamp(t) for t in split["test_time_bounds"])
    naive = index.tz_convert("UTC").tz_localize(None)
    return np.asarray((naive >= lo) & (naive <= hi), dtype=bool)


@pytest.mark.requires_kline
@pytest.mark.usefixtures("ic_persist_redirect")
@pytest.mark.ic_persist_redirect
@pytest.mark.parametrize("regime_method", ["rule", "kmeans"])
def test_regime_robust_end_to_end_analyze_and_refilter(tmp_path: Path, regime_method: str) -> None:
    """產品 `analyze`（真實 BTCUSDT 4h 末 2,000 根、樣本外切分）之 summary_table regime_robust／reason == oracle：
    regime 以 oracle 於分組 IC 同一列範圍之真實 kline 重算、逐 regime IC 以 scipy.spearmanr 重算；報告 grouped_ic.by_regime
    == oracle；refilter 後同值（同一來源）。"""
    k, feats, label, paths = _e2e_inputs(tmp_path)
    override = _e2e_override(regime_method)
    # 同 API（ic_analysis_service：`create_ic_analyzer(config_override)` 再 analyze(config_override=…)）：前處理器於建構時取設定
    orch = create_ic_analyzer(override)
    report = orch.analyze(features_path=str(paths["features"]), labels_path=str(paths["labels"]),
                          meta_path=str(paths["meta"]), config_override=override,
                          kline_reader=create_kline_storage_manager(cache_dir=str(KLINE_CACHE.parent)))
    scope = _scope_rows(report, feats.index)
    ks, fs, ls = k[scope], feats[scope], label[scope]
    masks = oracle_rule_masks(ks["close"]) if regime_method == "rule" else _kmeans_masks(
        oracle_kmeans_labels(ks["close"], ks["volume"]))
    oracle = oracle_by_regime(fs, ls, masks, "spearman")
    by = report["grouped_ic"]["by_regime"]
    assert set(by) == set(oracle)
    for regime, per in oracle.items():
        for f, (ic, _n) in per.items():
            got = (by[regime] or {}).get(f)
            assert (got is None and math.isnan(ic)) or abs(float(got) - ic) <= 1e-9, f"{regime}/{f}: {got} vs {ic}"
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    assert set(rows) == set(feats.columns)
    assert robust_mismatches(rows, oracle) == []
    assert rows["pos_label"]["regime_robust"] is True and rows["neg_label"]["regime_robust"] is True
    refiltered = orch.refilter({"ic_mean_min": -1.0})
    rows2 = {r["feature_name"]: r for r in refiltered["summary_table"]}
    assert {f: (r["regime_robust"], r["regime_robust_reason"]) for f, r in rows2.items()} == \
        {f: (r["regime_robust"], r["regime_robust_reason"]) for f, r in rows.items()}


@pytest.mark.requires_kline
@pytest.mark.usefixtures("ic_persist_redirect")
@pytest.mark.ic_persist_redirect
def test_regime_robust_end_to_end_uses_request_ic_method(tmp_path: Path) -> None:
    """主 IC 估計量（`global_settings.default_method`＝pearson）與 `ic_calculation.methods[0]`（spearman）不同時：
    報告 grouped_ic.by_regime == scipy.pearsonr oracle（與主 IC 同估計量），且至少一格與 spearman oracle 不同（非空真）；
    summary regime_robust == pearson oracle 判定（code review r51 CODEX-R51-P1-02）。"""
    k, feats, label, paths = _e2e_inputs(tmp_path)
    override = _e2e_override("rule")
    override["global"] = {"default_method": "pearson"}  # ICConfig.global_settings 之 alias（合併以 by_alias）
    override["ic_calculation"]["methods"] = ["spearman"]
    orch = create_ic_analyzer(override)
    report = orch.analyze(features_path=str(paths["features"]), labels_path=str(paths["labels"]),
                          meta_path=str(paths["meta"]), config_override=override,
                          kline_reader=create_kline_storage_manager(cache_dir=str(KLINE_CACHE.parent)))
    scope = _scope_rows(report, feats.index)
    ks, fs, ls = k[scope], feats[scope], label[scope]
    masks = oracle_rule_masks(ks["close"])
    oracle = oracle_by_regime(fs, ls, masks, "pearson")
    spear = oracle_by_regime(fs, ls, masks, "spearman")
    by = report["grouped_ic"]["by_regime"]
    assert set(by) == set(oracle)
    differs = 0
    for regime, per in oracle.items():
        for f, (ic, _n) in per.items():
            got = (by[regime] or {}).get(f)
            assert (got is None and math.isnan(ic)) or abs(float(got) - ic) <= 1e-9, f"{regime}/{f}: {got} vs {ic}"
            s = spear[regime][f][0]
            differs += int(math.isfinite(ic) and math.isfinite(s) and abs(ic - s) > 1e-6)
    assert differs > 0, "前提：pearson 與 spearman 之逐 regime IC 須有可區分之格"
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    assert robust_mismatches(rows, oracle) == []


@pytest.mark.requires_kline
@pytest.mark.usefixtures("ic_persist_redirect")
@pytest.mark.ic_persist_redirect
def test_regime_robust_end_to_end_regime_analysis_off(tmp_path: Path) -> None:
    """產品 `analyze` 於 include_regime_analysis 關：grouped_ic 未算 ⇒ 全列 None／regime_analysis_off。"""
    _k, feats, _label, paths = _e2e_inputs(tmp_path)
    override = _e2e_override("rule", include_regime=False)
    report = create_ic_analyzer(override).analyze(
        features_path=str(paths["features"]), labels_path=str(paths["labels"]), meta_path=str(paths["meta"]),
        config_override=override,
        kline_reader=create_kline_storage_manager(cache_dir=str(KLINE_CACHE.parent)))
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    assert set(rows) == set(feats.columns)
    assert {(r["regime_robust"], r["regime_robust_reason"]) for r in rows.values()} == {(None, "regime_analysis_off")}


@pytest.mark.requires_kline
@pytest.mark.usefixtures("ic_persist_redirect")
@pytest.mark.ic_persist_redirect
def test_regime_robust_cross_sectional_path_off() -> None:
    """跨標的路徑（真實 BTCUSDT／ETHUSDT 4h 末 300 根）：分組 IC 不適用（grouped_ic＝not_applicable）⇒ 全列
    None／regime_analysis_off。"""
    frames = []
    for sym in ("BTCUSDT", "ETHUSDT"):
        close = _real_kline(300, timeframe="4h", symbol=sym)["close"]
        df = pd.DataFrame({"ret1": close / close.shift(1) - 1.0, "return_1": _forward_return(close)})
        df["symbol"] = sym
        frames.append(df.rename_axis("timestamp").reset_index())
    data = pd.concat(frames).set_index(["timestamp", "symbol"]).sort_index()
    report = create_ic_analyzer().analyze_cross_sectional(data, config_override={"ic_train_test_split": False})
    assert report["grouped_ic"]["status"] == "not_applicable"
    rows = report["summary_table"]
    assert rows and {(r["regime_robust"], r["regime_robust_reason"]) for r in rows} == {(None, "regime_analysis_off")}
