#!/usr/bin/env python3
"""Composer 第三家獨立實證：fracdiff d* Option A 是否二階。

設計差異（相對 Codex/Claude）：
- 4 symbols：ETH/SOL/LINK/ADA（非 BTC）
- 窗選：列索引中段 35%–65%（非固定日曆窗）
- 特徵：factory 真實 L1+L2（非手工 20 欄）
- 分支②：first-500 vs 全歷史固定參考 d*（兩 run 共用同一 d*）

read-only；輸出 /tmp；data_cache 全量 SHA256 diff 須空。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from momentum.Analysis.ic_engine import ICEngine
from momentum.FeatureEngineering.preprocessing._d_star_cache import PreprocessingContext
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.factories import create_feature_factory

KLINE_DIR = PROJECT_ROOT / "data_cache" / "feature_klines"
SYMBOLS = ["ETHUSDT", "SOLUSDT", "LINKUSDT", "ADAUSDT"]
TF = "1h"
OUT_DIR = Path("/tmp/dstar_empirical_composer")
IC_THRESHOLDS = (0.005, 0.01, 0.02)


def sha256_dir(root: Path) -> dict[str, str]:
    """全量 data_cache SHA256 指紋（hermetic 自證）。"""
    if not root.exists():
        return {}
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def diff_maps(before: dict[str, str], after: dict[str, str]) -> list[str]:
    lines: list[str] = []
    for k in sorted(set(before) | set(after)):
        if before.get(k) != after.get(k):
            lines.append(f"{k}: {before.get(k, 'MISSING')} -> {after.get(k, 'MISSING')}")
    return lines


class RecordingPreprocessor(FeaturePreprocessor):
    """記錄每欄 d*。"""

    def __init__(self, config: dict[str, Any], context: PreprocessingContext) -> None:
        super().__init__(config, context=context)
        self.d_star_by_column: dict[str, float] = {}
        self._current_column: str | None = None

    def _find_min_d(self, series: pd.Series, **kwargs: Any) -> float:
        d_star = float(super()._find_min_d(series, **kwargs))
        if self._current_column is not None:
            self.d_star_by_column[self._current_column] = d_star
        return d_star

    def _apply_fractional_differencing_serial(
        self, result: pd.DataFrame, eligible_columns: list[str], **kwargs: Any
    ) -> pd.DataFrame:
        for column in eligible_columns:
            self._current_column = str(column)
            try:
                result = super()._apply_fractional_differencing_serial(result, [column], **kwargs)
            finally:
                self._current_column = None
        return result


class FullHistoryCalibPreprocessor(RecordingPreprocessor):
    """d* 校準用全可得歷史（非前 500）。"""

    def _calibration_series(self, series: pd.Series) -> pd.Series:
        return series


class FixedDStarPreprocessor(RecordingPreprocessor):
    """套用預先算好的固定 d*（windowed/full 共用）。"""

    def __init__(
        self,
        config: dict[str, Any],
        context: PreprocessingContext,
        fixed_d: dict[str, float],
    ) -> None:
        super().__init__(config, context=context)
        self._fixed_d = dict(fixed_d)

    def _find_min_d(self, series: pd.Series, **kwargs: Any) -> float:
        if self._current_column is not None and self._current_column in self._fixed_d:
            d_star = float(self._fixed_d[self._current_column])
            self.d_star_by_column[self._current_column] = d_star
            return d_star
        return float(super()._find_min_d(series, **kwargs))


def minimal_config(timeframe: str = TF) -> dict[str, Any]:
    return {
        "preset": "minimal",
        "timeframes": {
            "primary": timeframe,
            "training": [timeframe],
            "alignment": "point_in_time",
            "alignment_mode": "open_minus",
        },
        "data_sources": {"enabled_sources": ["close", "volume"], "synthetic_sources": []},
        "cross_sectional": {"enabled": False},
        "preprocessing": {
            "enabled": True,
            "winsorization": {"enabled": True, "window": 100},
            "fractional_differencing": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "rank_transform": {"enabled": False},
            "adaptive_zscore": {"enabled": False},
            "gaussian_normalize": {"enabled": False},
        },
        "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
    }


def preprocessing_config(*, calibration_bars: int = 500) -> dict[str, Any]:
    return {
        "enabled": True,
        "mode": "replace",
        "causal_preprocessing": True,
        "calibration_bars": calibration_bars,
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.01, 0.99],
            "window": 252,
            "apply_to": "all",
        },
        "fractional_differencing": {
            "enabled": True,
            "d_range": [0.0, 1.0],
            "adf_threshold": 0.10,
            "weight_threshold": 1e-5,
            "precision": 0.01,
            "apply_to": "non_stationary",
            "cache_d_star": False,
        },
        "adf_differencing": {"enabled": False, "adf_threshold": 0.10, "sample_size": 500},
        "rank_transform": {"enabled": False},
        "gaussian_normalize": {"enabled": False},
        "adaptive_zscore": {"enabled": False},
        "adf_safe_skip": {"enabled": True},
    }


def read_kline_close(symbol: str, timeframe: str) -> pd.Series:
    """真實 kline close（IC 標籤用）。"""
    factory = create_feature_factory(cache_dir=str(KLINE_DIR), validate_continuity=False)
    config = factory._resolve_config(minimal_config(timeframe))
    raw = factory._layer0_data_ingestion(
        symbol,
        timeframe,
        config,
        start_date=factory._layer0_ingest_start_date_for_tf(timeframe, config.timeframes.primary),
        end_date=None,
    )
    if "close" in raw.columns:
        return raw["close"].astype(float)
    return raw.filter(regex=r"(?i)close").iloc[:, 0].astype(float)


def build_l12_features(symbol: str, timeframe: str) -> pd.DataFrame:
    """factory 真實 L1 指標 + 自衍 L2（L1_/L2_ 前綴，與 Codex 手工欄位不同）。"""
    factory = create_feature_factory(cache_dir=str(KLINE_DIR), validate_continuity=False)
    config = factory._resolve_config(minimal_config(timeframe))
    raw = factory._layer0_data_ingestion(
        symbol,
        timeframe,
        config,
        start_date=factory._layer0_ingest_start_date_for_tf(timeframe, config.timeframes.primary),
        end_date=None,
    )
    layer1 = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, raw, config
    ).data
    # factory minimal 產出無 L1_ 前綴；加前綴以符合 FFACT_FRACDIFF_APPLY_TO_LAYERS
    l1 = layer1.add_prefix("L1_")
    close = raw["close"].astype(float)
    ema21 = l1.get("L1_close_trend_EMA_21")
    ema55 = l1.get("L1_close_trend_EMA_55")
    sma21 = l1.get("L1_close_trend_SMA_21")
    rsi14 = l1.get("L1_close_momentum_RSI_14")
    macd_hist = l1.get("L1_close_momentum_MACD-Hist_12-26-9")
    vol_ema21 = l1.get("L1_volume_trend_EMA_21")

    l2 = pd.DataFrame(index=l1.index)
    if ema21 is not None and ema55 is not None:
        l2["L2_ema21_over_ema55"] = ema21 / ema55.replace(0.0, np.nan)
        l2["L2_log_ema21"] = np.log(ema21.clip(lower=1e-12))
    if sma21 is not None:
        l2["L2_close_over_sma21"] = close / sma21.replace(0.0, np.nan)
    if rsi14 is not None:
        l2["L2_rsi_centered"] = (rsi14 - 50.0) / 50.0
    if macd_hist is not None and ema21 is not None:
        l2["L2_macd_hist_per_ema21"] = macd_hist / ema21.replace(0.0, np.nan)
    if vol_ema21 is not None:
        l2["L2_sqrt_vol_ema21"] = np.sqrt(vol_ema21.clip(lower=0.0))
    l2["L2_log_close"] = np.log(close.clip(lower=1e-12))
    l2["L2_hl_range"] = (raw["high"] - raw["low"]) / close.replace(0.0, np.nan)

    combined = pd.concat([l1, l2], axis=1)
    cols = [c for c in combined.columns if pd.api.types.is_numeric_dtype(combined[c])]
    return combined[cols].copy()


def middle_index_window(index: pd.Index) -> tuple[pd.Timestamp, pd.Timestamp]:
    """列索引中段 35%–65%（與 Codex 固定日曆窗不同）。"""
    n = len(index)
    lo = int(n * 0.35)
    hi = int(n * 0.65)
    return index[lo], index[hi - 1]


def run_preprocessor(
    features: pd.DataFrame,
    symbol: str,
    timeframe: str,
    run_name: str,
    *,
    pp_cls: type[RecordingPreprocessor] = RecordingPreprocessor,
    fixed_d: dict[str, float] | None = None,
    calibration_bars: int = 500,
) -> tuple[pd.DataFrame, dict[str, float], list[str]]:
    context = PreprocessingContext(
        symbol=symbol,
        timeframe=timeframe,
        config_hash=run_name,
        row_count=len(features),
        time_range=(str(features.index.min()), str(features.index.max())),
    )
    cfg = preprocessing_config(calibration_bars=calibration_bars)
    if fixed_d is not None:
        pp = FixedDStarPreprocessor(cfg, context=context, fixed_d=fixed_d)
    elif pp_cls is FullHistoryCalibPreprocessor:
        pp = FullHistoryCalibPreprocessor(cfg, context=context)
    else:
        pp = RecordingPreprocessor(cfg, context=context)
    transformed = pp.transform(features)
    return transformed, pp.d_star_by_column, sorted(pp._fracdiff_processed_columns)


def summarize(vals: list[float]) -> dict[str, float | int | None]:
    arr = np.asarray([v for v in vals if np.isfinite(v)], dtype=np.float64)
    if arr.size == 0:
        return {"n": 0, "mean": None, "median": None, "p95": None, "max": None}
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p95": float(np.quantile(arr, 0.95)),
        "max": float(np.max(arr)),
    }


def value_stats(left: pd.Series, right: pd.Series) -> dict[str, Any]:
    aligned = pd.concat([left.rename("l"), right.rename("r")], axis=1)
    aligned = aligned.replace([np.inf, -np.inf], np.nan).dropna()
    if len(aligned) < 3:
        return {"n": int(len(aligned)), "pearson": None, "spearman": None}
    return {
        "n": int(len(aligned)),
        "pearson": float(aligned["l"].corr(aligned["r"], method="pearson")),
        "spearman": float(aligned["l"].corr(aligned["r"], method="spearman")),
    }


def selection_jaccard(
    ic_full: pd.Series, ic_win: pd.Series, *, top_n: int | None = None, threshold: float | None = None
) -> dict[str, Any]:
    ic_full = ic_full.dropna().astype(float)
    ic_win = ic_win.dropna().astype(float)
    if top_n is not None:
        full_set = set(ic_full.abs().nlargest(min(top_n, len(ic_full))).index)
        win_set = set(ic_win.abs().nlargest(min(top_n, len(ic_win))).index)
    elif threshold is not None:
        full_set = set(ic_full[ic_full.abs() >= threshold].index)
        win_set = set(ic_win[ic_win.abs() >= threshold].index)
    else:
        raise ValueError("need top_n or threshold")
    union = full_set | win_set
    return {
        "full": sorted(full_set),
        "window": sorted(win_set),
        "intersection": sorted(full_set & win_set),
        "jaccard": float(len(full_set & win_set) / len(union)) if union else 1.0,
    }


def analyze_pair(
    full_tf: pd.DataFrame,
    win_tf: pd.DataFrame,
    full_d: dict[str, float],
    win_d: dict[str, float],
    overlap_idx: pd.Index,
    forward_ret: pd.Series,
    common_cols: list[str],
) -> dict[str, Any]:
    engine = ICEngine({"methods": ["spearman"], "ic_threshold": 0.02})
    ic_full = engine.compute_ic(
        full_tf.loc[overlap_idx, common_cols], forward_ret, method="spearman"
    )
    ic_win = engine.compute_ic(
        win_tf.loc[overlap_idx, common_cols], forward_ret, method="spearman"
    )
    ic_full_s = pd.Series({k: float(v) for k, v in ic_full.items()}, dtype=float)
    ic_win_s = pd.Series({k: float(v) for k, v in ic_win.items()}, dtype=float)

    d_deltas: list[float] = []
    pearsons: list[float] = []
    spearmans: list[float] = []
    ic_deltas: list[float] = []
    rows: list[dict[str, Any]] = []

    for col in common_cols:
        dd = abs(float(full_d[col]) - float(win_d[col]))
        vs = value_stats(full_tf.loc[overlap_idx, col], win_tf.loc[overlap_idx, col])
        ic_d = abs(float(ic_full_s.get(col, np.nan)) - float(ic_win_s.get(col, np.nan)))
        d_deltas.append(dd)
        if vs["pearson"] is not None:
            pearsons.append(vs["pearson"])
        if vs["spearman"] is not None:
            spearmans.append(vs["spearman"])
        if np.isfinite(ic_d):
            ic_deltas.append(ic_d)
        rows.append(
            {
                "feature": col,
                "d_full": float(full_d[col]),
                "d_window": float(win_d[col]),
                "d_abs_delta": dd,
                "value_pearson": vs["pearson"],
                "value_spearman": vs["spearman"],
                "ic_full": float(ic_full_s.get(col, np.nan)),
                "ic_window": float(ic_win_s.get(col, np.nan)),
                "ic_abs_delta": ic_d,
            }
        )

    rank_full = ic_full_s.abs().rank(ascending=False, method="average")
    rank_win = ic_win_s.abs().rank(ascending=False, method="average")
    rank_delta = (rank_full - rank_win).abs()

    sel: dict[str, Any] = {}
    for n in (3, 5, min(10, len(common_cols))):
        if n > 0 and len(common_cols) >= n:
            sel[f"top{n}"] = selection_jaccard(ic_full_s, ic_win_s, top_n=n)
    for thr in IC_THRESHOLDS:
        sel[f"abs_ic_ge_{thr:g}"] = selection_jaccard(ic_full_s, ic_win_s, threshold=thr)

    return {
        "n_features": len(common_cols),
        "d_abs_delta": summarize(d_deltas),
        "value_pearson": summarize(pearsons),
        "value_spearman": summarize(spearmans),
        "ic_abs_delta": summarize(ic_deltas),
        "ic_rank_abs_delta": summarize(rank_delta.astype(float).tolist()),
        "ic_rank_spearman": float(rank_full.corr(rank_win, method="spearman")),
        "selection": sel,
        "top_d_delta": sorted(rows, key=lambda r: r["d_abs_delta"], reverse=True)[:5],
        "top_ic_delta": sorted(rows, key=lambda r: r["ic_abs_delta"], reverse=True)[:5],
    }


def run_symbol(symbol: str) -> dict[str, Any]:
    full_features = build_l12_features(symbol, TF)
    w_start, w_end = middle_index_window(full_features.index)
    win_features = full_features.loc[(full_features.index >= w_start) & (full_features.index <= w_end)].copy()

    px = read_kline_close(symbol, TF).reindex(full_features.index)
    fwd = px.pct_change().shift(-1)

    # ① Option A：各自 first-500 校準
    full_tf_a, full_d_a, _ = run_preprocessor(
        full_features, symbol, TF, f"{symbol}_full_optA"
    )
    win_tf_a, win_d_a, _ = run_preprocessor(
        win_features, symbol, TF, f"{symbol}_win_optA"
    )
    common_a = sorted(set(full_d_a) & set(win_d_a))
    overlap = full_tf_a.index.intersection(win_tf_a.index)
    opt_a = analyze_pair(
        full_tf_a, win_tf_a, full_d_a, win_d_a, overlap, fwd.reindex(overlap), common_a
    )

    # ② 全歷史固定參考 d*
    _, d_ref, processed_ref = run_preprocessor(
        full_features,
        symbol,
        TF,
        f"{symbol}_ref_fullhist",
        pp_cls=FullHistoryCalibPreprocessor,
    )
    fixed_d = {c: d_ref[c] for c in processed_ref if c in d_ref}
    full_tf_b, full_d_b, _ = run_preprocessor(
        full_features, symbol, TF, f"{symbol}_full_fixed", fixed_d=fixed_d
    )
    win_tf_b, win_d_b, _ = run_preprocessor(
        win_features, symbol, TF, f"{symbol}_win_fixed", fixed_d=fixed_d
    )
    common_b = sorted(set(full_d_b) & set(win_d_b) & set(fixed_d))
    if not common_b:
        common_b = sorted(set(fixed_d) & set(full_tf_b.columns) & set(win_tf_b.columns))
    opt_b = analyze_pair(
        full_tf_b, win_tf_b, full_d_b, win_d_b, overlap, fwd.reindex(overlap), common_b
    )

    # d_ref vs Option A 的 d 差（診斷校準來源）
    ref_vs_full_a = [
        abs(float(d_ref[c]) - float(full_d_a[c]))
        for c in common_a
        if c in d_ref and c in full_d_a
    ]
    ref_vs_win_a = [
        abs(float(d_ref[c]) - float(win_d_a[c]))
        for c in common_a
        if c in d_ref and c in win_d_a
    ]

    return {
        "symbol": symbol,
        "full_rows": int(len(full_features)),
        "window_rows": int(len(win_features)),
        "window_start": str(w_start),
        "window_end": str(w_end),
        "l12_cols": int(full_features.shape[1]),
        "fracdiff_common_optA": len(common_a),
        "fracdiff_common_fixed": len(common_b),
        "option_a_first500": opt_a,
        "fixed_fullhist_d": opt_b,
        "d_ref_vs_full_a": summarize(ref_vs_full_a),
        "d_ref_vs_win_a": summarize(ref_vs_win_a),
    }


def aggregate_across_symbols(per_symbol: list[dict[str, Any]], key: str) -> dict[str, Any]:
    """跨 symbol 彙總 mean of means。"""
    metrics = ("d_abs_delta", "value_pearson", "value_spearman", "ic_abs_delta")
    out: dict[str, Any] = {}
    for m in metrics:
        means = [
            s[key][m]["mean"]
            for s in per_symbol
            if s.get(key, {}).get(m, {}).get("mean") is not None
        ]
        out[m] = {"mean_of_means": float(np.mean(means)) if means else None, "per_symbol_means": means}
    # selection Jaccard at abs_ic>=0.01
    jkey = "abs_ic_ge_0.01"
    jvals = [
        s[key]["selection"][jkey]["jaccard"]
        for s in per_symbol
        if jkey in s.get(key, {}).get("selection", {})
    ]
    out["selection_jaccard_abs_ic_0.01"] = {
        "mean": float(np.mean(jvals)) if jvals else None,
        "per_symbol": jvals,
    }
    return out


def main() -> int:
    os.environ.setdefault("FFACT_FRACDIFF_APPLY_TO_LAYERS", "L1,L2")
    os.environ.setdefault("FFACT_L65_SLOWPATH_PARALLEL", "0")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("FFACT_CGSA_WORK_DIR", str(OUT_DIR / "cgsa_work"))

    dc_root = PROJECT_ROOT / "data_cache"
    before = sha256_dir(dc_root)

    results: list[dict[str, Any]] = []
    for sym in SYMBOLS:
        print(f"=== {sym} ===", flush=True)
        results.append(run_symbol(sym))

    after = sha256_dir(dc_root)
    hermetic_diff = diff_maps(before, after)
    list_hash = hashlib.sha256(
        "\n".join(f"{k}:{v}" for k, v in sorted(before.items())).encode()
    ).hexdigest()

    summary = {
        "design": {
            "symbols": SYMBOLS,
            "timeframe": TF,
            "window_method": "row_index_35pct_65pct",
            "features": "factory_L1_minimal_plus_derived_L2_L1_L2_prefix",
            "branch_a": "option_a_first500_per_run",
            "branch_b": "fixed_d_from_full_history_calibration",
        },
        "per_symbol": results,
        "aggregate_option_a": aggregate_across_symbols(results, "option_a_first500"),
        "aggregate_fixed_ref": aggregate_across_symbols(results, "fixed_fullhist_d"),
        "hermetic": {
            "data_cache_files": len(before),
            "list_hash": list_hash,
            "diff_lines": hermetic_diff,
            "diff_empty": len(hermetic_diff) == 0,
        },
    }

    out_json = OUT_DIR / "summary.json"
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["hermetic"]["diff_empty"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
