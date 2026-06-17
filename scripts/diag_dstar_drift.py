"""Claude 自產診斷 spike — d* 漂移 / walk-forward 成本量測（真實 kline，read-only，不進生產路徑）。

研究問題：
  Q1 d* 隨時間漂多少？(rolling 窗 d* 軌跡的 std/range)
  Q2 若漂得小 → walk-forward 解假問題；若大 → 值得，但選最便宜變體。
  Q3 時間成本：single-window vs walk-forward(rolling) vs walk-forward(anchored-expanding)。
  Q4 記憶體峰值差多少。

忠於生產：直接用 FeaturePreprocessor._find_min_d（同一 bisection+ADF+fracdiff convolve）。
誠實邊界：本版用「原始非平穩 level 序列(log_close/log_volume/log_quote/close)」作 fracdiff 目標代表，
  非完整生成特徵——委員會可擴充到真實 L1 特徵。多 symbol×tf。
"""
from __future__ import annotations

import time
import tracemalloc

import numpy as np
import pandas as pd

from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

SYMBOLS = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "XRPUSDT"]
TFS = ["1h"]
CAL_BARS = 500          # 與生產預設 calibration_bars 一致
STEP = 250              # rolling d* 取樣步長
INTERVAL = 500          # walk-forward 重估間隔(= 生產提案預設)

PP_CONFIG = {
    "calibration_bars": CAL_BARS,
    "causal_preprocessing": True,
    "fractional_differencing": {"enabled": True, "weight_threshold": 1e-5, "precision": 0.02},
    "adf_differencing": {"enabled": True, "sample_size": CAL_BARS},
}


def build_target_series(df: pd.DataFrame) -> dict[str, pd.Series]:
    close = df["close"].astype(float)
    vol = df["volume"].astype(float).replace(0, np.nan)
    qv = df["quote_volume"].astype(float).replace(0, np.nan) if "quote_volume" in df else None
    out = {
        "close": close,
        "log_close": np.log(close),
        "log_volume": np.log(vol),
    }
    if qv is not None:
        out["log_quote_volume"] = np.log(qv)
    return out


def rolling_dstar(pp: FeaturePreprocessor, series: pd.Series) -> list[float]:
    """每 STEP 步、用最近 CAL_BARS bar 估一次 d*（rolling，PIT）。"""
    s = series.reset_index(drop=True)
    n = len(s)
    ds = []
    t = CAL_BARS
    while t <= n:
        window = s.iloc[t - CAL_BARS : t]
        # _find_min_d 內部會再 _calibration_series(取前 CAL_BARS)，window 長度=CAL_BARS → 即用整窗
        d = pp._find_min_d(window)
        ds.append(d)
        t += STEP
    return ds


def time_variants(pp: FeaturePreprocessor, series: pd.Series) -> dict[str, float]:
    s = series.reset_index(drop=True)
    n = len(s)

    # single-window (現況): 前 CAL_BARS 估一次
    t0 = time.perf_counter()
    pp._find_min_d(s.iloc[:CAL_BARS])
    single = time.perf_counter() - t0

    # walk-forward rolling: 每 INTERVAL 一段,用最近 CAL_BARS
    seg_starts = list(range(CAL_BARS, n, INTERVAL))
    t0 = time.perf_counter()
    for ss in seg_starts:
        pp._find_min_d(s.iloc[ss - CAL_BARS : ss])
    rolling = time.perf_counter() - t0

    # walk-forward anchored-expanding: 每 INTERVAL 一段,用 [0, ss)
    t0 = time.perf_counter()
    for ss in seg_starts:
        pp._find_min_d(s.iloc[:ss])
    expanding = time.perf_counter() - t0

    return {
        "n_segments": len(seg_starts),
        "single_s": single,
        "rolling_s": rolling,
        "expanding_s": expanding,
        "rolling_x": rolling / single if single else float("nan"),
        "expanding_x": expanding / single if single else float("nan"),
    }


def main() -> None:
    pp = FeaturePreprocessor(PP_CONFIG)
    rows = []
    timing_rows = []
    for sym in SYMBOLS:
        for tf in TFS:
            try:
                df = KlineStorageManager(cache_dir="data_cache/feature_klines").read_klines(
                    symbol=sym, timeframe=tf, validate_continuity=False
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[skip] {sym}/{tf}: {exc}")
                continue
            if df is None or df.empty:
                print(f"[skip] {sym}/{tf}: empty")
                continue
            targets = build_target_series(df)
            for name, series in targets.items():
                ds = rolling_dstar(pp, series)
                arr = np.array(ds, dtype=float)
                rows.append({
                    "symbol": sym, "tf": tf, "feature": name, "n_bars": len(series),
                    "n_dstar": len(arr),
                    "d_mean": round(float(np.nanmean(arr)), 4),
                    "d_std": round(float(np.nanstd(arr)), 4),
                    "d_min": round(float(np.nanmin(arr)), 4),
                    "d_max": round(float(np.nanmax(arr)), 4),
                    "d_range": round(float(np.nanmax(arr) - np.nanmin(arr)), 4),
                })
            # timing + memory on log_close (代表性)
            tracemalloc.start()
            tm = time_variants(pp, targets["log_close"])
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            tm.update({"symbol": sym, "tf": tf, "peak_mb": round(peak / 1e6, 2)})
            timing_rows.append(tm)

    drift = pd.DataFrame(rows)
    timing = pd.DataFrame(timing_rows)
    pd.set_option("display.width", 200)
    print("\n================ Q1/Q2  d* 漂移（rolling 窗）================")
    print(drift.to_string(index=False))
    print("\n  per-feature 跨 symbol 平均 d_std / d_range:")
    print(drift.groupby("feature")[["d_std", "d_range"]].mean().round(4).to_string())
    print("\n================ Q3/Q4  時間 + 記憶體峰值（log_close）================")
    print(timing[["symbol", "tf", "n_segments", "single_s", "rolling_s", "expanding_s",
                  "rolling_x", "expanding_x", "peak_mb"]].round(3).to_string(index=False))
    print("\n  彙總: rolling 平均 {:.1f}x / expanding 平均 {:.1f}x  vs single".format(
        timing["rolling_x"].mean(), timing["expanding_x"].mean()))


if __name__ == "__main__":
    main()
