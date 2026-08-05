#!/usr/bin/env python3
"""Read-only empirical check for fracdiff d* Option A.

Outputs JSON/CSV under /tmp by default. Does not write product cache.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from momentum.Analysis.ic_engine import ICEngine
from momentum.FeatureEngineering.preprocessing._d_star_cache import PreprocessingContext
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


class RecordingPreprocessor(FeaturePreprocessor):
    def __init__(self, config: dict[str, Any], context: PreprocessingContext) -> None:
        super().__init__(config, context=context)
        self.d_star_by_column: dict[str, float] = {}
        self._current_column: str | None = None

    def _find_min_d(self, series: pd.Series, **kwargs: Any) -> float:
        d_star = float(super()._find_min_d(series, **kwargs))
        if self._current_column is not None:
            self.d_star_by_column[self._current_column] = d_star
        return d_star

    def _apply_fractional_differencing_serial(self, result: pd.DataFrame, eligible_columns: list[str], **kwargs: Any) -> pd.DataFrame:
        for column in eligible_columns:
            self._current_column = str(column)
            try:
                result = super()._apply_fractional_differencing_serial(result, [column], **kwargs)
            finally:
                self._current_column = None
        return result


def read_kline(path: Path, symbol: str, timeframe: str) -> pd.DataFrame:
    with h5py.File(path, "r") as h5:
        values = h5[f"/{symbol}/{timeframe}/data"][:]
    frame = pd.DataFrame.from_records(values)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"].astype("int64"), unit="s", utc=True)
    frame = frame.set_index("timestamp").sort_index()
    return frame.astype({c: "float64" for c in frame.columns if c != "number_of_trades"})


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def build_l12_features(kline: pd.DataFrame) -> pd.DataFrame:
    close = kline["close"]
    high = kline["high"]
    low = kline["low"]
    volume = kline["volume"]
    quote_volume = kline["quote_volume"]
    trades = kline["number_of_trades"].astype("float64")
    typical = (high + low + close) / 3.0
    cum_pv = (typical * volume).rolling(168, min_periods=168).sum()
    cum_v = volume.rolling(168, min_periods=168).sum()
    vwap = cum_pv / cum_v.replace(0.0, np.nan)
    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)

    features = pd.DataFrame(index=kline.index)
    features["L1_close"] = close
    features["L1_high"] = high
    features["L1_low"] = low
    features["L1_volume"] = volume
    features["L1_quote_volume"] = quote_volume
    features["L1_number_of_trades"] = trades
    features["L1_EMA_20"] = ema(close, 20)
    features["L1_EMA_50"] = ema(close, 50)
    features["L1_SMA_50"] = close.rolling(50, min_periods=50).mean()
    features["L1_ATR_14"] = tr.rolling(14, min_periods=14).mean()
    features["L1_BBANDS_upper_20"] = close.rolling(20, min_periods=20).mean() + 2.0 * close.rolling(20, min_periods=20).std()
    features["L1_VWAP_168"] = vwap
    features["L2_log_close"] = np.log(close)
    features["L2_sqrt_volume"] = np.sqrt(volume.clip(lower=0.0))
    features["L2_close_over_SMA_50"] = close / features["L1_SMA_50"]
    features["L2_EMA_20_over_EMA_50"] = features["L1_EMA_20"] / features["L1_EMA_50"]
    features["L2_price_x_volume"] = close * volume
    features["L2_quote_per_trade"] = quote_volume / trades.replace(0.0, np.nan)
    features["L2_range_scaled_close"] = (high - low) / close.replace(0.0, np.nan)
    features["L2_decay_linear_close_20"] = close.rolling(20, min_periods=20).apply(
        lambda x: float(np.dot(x, np.arange(1, len(x) + 1)) / np.arange(1, len(x) + 1).sum()),
        raw=True,
    )
    return features


def preprocessing_config() -> dict[str, Any]:
    return {
        "enabled": True,
        "mode": "replace",
        "causal_preprocessing": True,
        "calibration_bars": 500,
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


def run_preprocessor(features: pd.DataFrame, symbol: str, timeframe: str, run_name: str) -> tuple[pd.DataFrame, dict[str, float], list[str]]:
    context = PreprocessingContext(
        symbol=symbol,
        timeframe=timeframe,
        config_hash=run_name,
        row_count=len(features),
        time_range=(str(features.index.min()), str(features.index.max())),
    )
    pp = RecordingPreprocessor(preprocessing_config(), context=context)
    transformed = pp.transform(features)
    return transformed, pp.d_star_by_column, sorted(pp._fracdiff_processed_columns)


def corr_and_allclose(left: pd.Series, right: pd.Series) -> dict[str, Any]:
    aligned = pd.concat([left.rename("left"), right.rename("right")], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(aligned) < 3:
        return {"n": int(len(aligned)), "pearson": None, "spearman": None, "allclose": False, "max_abs_delta": None}
    delta = (aligned["left"] - aligned["right"]).abs()
    return {
        "n": int(len(aligned)),
        "pearson": float(aligned["left"].corr(aligned["right"], method="pearson")),
        "spearman": float(aligned["left"].corr(aligned["right"], method="spearman")),
        "allclose": bool(np.allclose(aligned["left"].to_numpy(), aligned["right"].to_numpy(), rtol=1e-5, atol=1e-8, equal_nan=True)),
        "max_abs_delta": float(delta.max()),
        "median_abs_delta": float(delta.median()),
    }


def summarize(values: list[float]) -> dict[str, float | int | None]:
    arr = np.asarray([v for v in values if np.isfinite(v)], dtype=np.float64)
    if arr.size == 0:
        return {"n": 0, "mean": None, "median": None, "p95": None, "max": None}
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p95": float(np.quantile(arr, 0.95)),
        "max": float(np.max(arr)),
    }


def build_detail(
    *,
    full_transformed: pd.DataFrame,
    window_transformed: pd.DataFrame,
    full_d: dict[str, float],
    window_d: dict[str, float],
    overlap_index: pd.Index,
    forward_return: pd.Series,
    common_cols: list[str],
) -> pd.DataFrame:
    engine = ICEngine({"methods": ["spearman"], "ic_threshold": 0.02})
    full_ic = engine.compute_ic(full_transformed.loc[overlap_index, common_cols], forward_return, method="spearman")
    window_ic = engine.compute_ic(window_transformed.loc[overlap_index, common_cols], forward_return, method="spearman")
    rows: list[dict[str, Any]] = []
    for col in common_cols:
        value_stats = corr_and_allclose(full_transformed.loc[overlap_index, col], window_transformed.loc[overlap_index, col])
        rows.append(
            {
                "feature": col,
                "d_full": float(full_d[col]),
                "d_window": float(window_d[col]),
                "d_abs_delta": abs(float(full_d[col]) - float(window_d[col])),
                "value_pearson": value_stats["pearson"],
                "value_spearman": value_stats["spearman"],
                "value_allclose": value_stats["allclose"],
                "value_n": value_stats["n"],
                "value_max_abs_delta": value_stats["max_abs_delta"],
                "ic_full": float(full_ic.get(col, np.nan)),
                "ic_window": float(window_ic.get(col, np.nan)),
                "ic_abs_delta": abs(float(full_ic.get(col, np.nan)) - float(window_ic.get(col, np.nan))),
            }
        )
    return pd.DataFrame(rows).sort_values(["d_abs_delta", "ic_abs_delta"], ascending=False)


def selected_overlap(detail: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for top_n in (3, 5, min(10, len(detail))):
        full_top = set(detail.sort_values("ic_full", key=lambda s: s.abs(), ascending=False).head(top_n)["feature"])
        window_top = set(detail.sort_values("ic_window", key=lambda s: s.abs(), ascending=False).head(top_n)["feature"])
        union = full_top | window_top
        result[f"top_abs_ic_{top_n}"] = {
            "full": sorted(full_top),
            "window": sorted(window_top),
            "intersection": sorted(full_top & window_top),
            "jaccard": float(len(full_top & window_top) / len(union)) if union else 1.0,
        }
    for threshold in (0.005, 0.01, 0.02):
        full_set = set(detail.loc[detail["ic_full"].abs() >= threshold, "feature"])
        window_set = set(detail.loc[detail["ic_window"].abs() >= threshold, "feature"])
        union = full_set | window_set
        result[f"threshold_abs_ic_{threshold:g}"] = {
            "full_count": len(full_set),
            "window_count": len(window_set),
            "intersection_count": len(full_set & window_set),
            "full_only": sorted(full_set - window_set),
            "window_only": sorted(window_set - full_set),
            "jaccard": float(len(full_set & window_set) / len(union)) if union else 1.0,
        }
    return result


def detail_summary(detail: pd.DataFrame) -> dict[str, Any]:
    rank_full = detail.set_index("feature")["ic_full"].abs().rank(ascending=False, method="average")
    rank_window = detail.set_index("feature")["ic_window"].abs().rank(ascending=False, method="average")
    rank_delta = (rank_full - rank_window).abs()
    return {
        "d_abs_delta": summarize(detail["d_abs_delta"].astype(float).tolist()),
        "value_pearson": summarize(detail["value_pearson"].astype(float).tolist()),
        "value_spearman": summarize(detail["value_spearman"].astype(float).tolist()),
        "value_allclose_count": int(detail["value_allclose"].sum()),
        "ic_abs_delta": summarize(detail["ic_abs_delta"].astype(float).tolist()),
        "ic_rank_abs_delta": summarize(rank_delta.astype(float).tolist()),
        "ic_rank_spearman_abs_ic": float(rank_full.corr(rank_window, method="spearman")),
        "selected_overlap": selected_overlap(detail),
        "largest_d_delta": detail.head(5).to_dict(orient="records"),
        "largest_ic_delta": detail.sort_values("ic_abs_delta", ascending=False).head(5).to_dict(orient="records"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kline", type=Path, default=Path("data_cache/feature_klines/kline_cache.h5"))
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--window-start", default="2024-09-01T00:00:00Z")
    parser.add_argument("--window-end", default="2025-05-31T23:00:00Z")
    parser.add_argument("--out-dir", type=Path, default=Path("/tmp/dstar_option_a_empirical"))
    args = parser.parse_args()

    os.environ.setdefault("FFACT_FRACDIFF_APPLY_TO_LAYERS", "L1,L2")
    os.environ.setdefault("FFACT_L65_SLOWPATH_PARALLEL", "0")
    os.environ.setdefault("FFACT_CGSA_WORK_DIR", str(args.out_dir / "cgsa_work"))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    kline = read_kline(args.kline, args.symbol, args.timeframe)
    full_features = build_l12_features(kline)
    start = pd.Timestamp(args.window_start)
    end = pd.Timestamp(args.window_end)
    window_features = full_features.loc[(full_features.index >= start) & (full_features.index <= end)].copy()
    if len(window_features) < 500:
        raise RuntimeError(f"window too short: {len(window_features)} rows")

    full_transformed, full_d, full_processed = run_preprocessor(full_features, args.symbol, args.timeframe, "full_range")
    window_transformed, window_d, window_processed = run_preprocessor(window_features, args.symbol, args.timeframe, "date_windowed")

    common_cols = sorted(set(full_d) & set(window_d))
    overlap_index = full_transformed.index.intersection(window_transformed.index)
    close = kline["close"].reindex(overlap_index)
    forward_return = close.shift(-1) / close - 1.0
    detail = build_detail(
        full_transformed=full_transformed,
        window_transformed=window_transformed,
        full_d=full_d,
        window_d=window_d,
        overlap_index=overlap_index,
        forward_return=forward_return,
        common_cols=common_cols,
    )
    trimmed_overlap_index = overlap_index[1000:]
    trimmed_forward_return = (kline["close"].reindex(trimmed_overlap_index).shift(-1) / kline["close"].reindex(trimmed_overlap_index) - 1.0)
    trimmed_detail = build_detail(
        full_transformed=full_transformed,
        window_transformed=window_transformed,
        full_d=full_d,
        window_d=window_d,
        overlap_index=trimmed_overlap_index,
        forward_return=trimmed_forward_return,
        common_cols=common_cols,
    )

    summary = {
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "kline_path": str(args.kline),
        "full_rows": int(len(full_features)),
        "window_rows": int(len(window_features)),
        "window_start": str(window_features.index.min()),
        "window_end": str(window_features.index.max()),
        "overlap_rows": int(len(overlap_index)),
        "candidate_features": int(full_features.shape[1]),
        "full_fracdiff_processed": len(full_processed),
        "window_fracdiff_processed": len(window_processed),
        "full_processed_without_recorded_dstar": sorted(set(full_processed) - set(full_d)),
        "window_processed_without_recorded_dstar": sorted(set(window_processed) - set(window_d)),
        "common_dstar_features": len(common_cols),
        "all_overlap": detail_summary(detail),
        "trimmed_overlap_after_1000_bars": {
            "overlap_rows": int(len(trimmed_overlap_index)),
            **detail_summary(trimmed_detail),
        },
    }

    detail.to_csv(args.out_dir / "feature_detail.csv", index=False)
    trimmed_detail.to_csv(args.out_dir / "feature_detail_trimmed_after_1000.csv", index=False)
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
