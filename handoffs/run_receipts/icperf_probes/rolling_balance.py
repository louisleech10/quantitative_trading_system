"""ICPERF Task 0.4 ㉗／㉘ 四項平衡實測（r55 群集 H）：於指定 repo 樹之 `ICEngine.compute_rolling_ic` 量測
滾動 Pearson／Kendall 之耗時、峰值 RSS、對 scipy 之精度與輸出大小。

用法（每次只量一個方法、獨立行程，峰值 RSS 不互相污染）：
  venv/bin/python handoffs/run_receipts/icperf_probes/rolling_balance.py --repo <樹根> --method pearson|kendall --out <json>

輸入：真實 kline `data_cache/feature_klines/kline_cache.h5` BTCUSDT 1h 全部根數之收盤；特徵＝只用 0..t 之 12 欄
（收盤水準、5／20／60 根均線、報酬、5／20 根動量、20／60 根報酬波動、成交量水準與其 20 根均線、高低價差），含價格水準欄
（㉘ 相消誤差之觸發型態）；標籤＝1 根前瞻簡單報酬。窗＝[63, 252]（原生 1h，不經週期換算）。精度：每欄每窗均勻取 40 個
窗終點，逐點以 scipy.stats.pearsonr／kendalltau 重算，記最大相對誤差（|oracle| < 1e-8 之點記絕對誤差另列）。
"""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from scipy import stats

WINDOWS = [63, 252]
N_SAMPLE = 40


def _inputs(kline: Path) -> tuple[pd.DataFrame, pd.Series]:
    with h5py.File(kline, "r") as f:
        d = f["BTCUSDT/1h/data"][:]
    idx = pd.to_datetime(d["timestamp"].astype("int64"), unit="s", utc=True)
    c = pd.Series(d["close"].astype("float64"), index=idx)
    v = pd.Series(d["volume"].astype("float64"), index=idx)
    hl = pd.Series((d["high"] - d["low"]).astype("float64"), index=idx)
    r = c.pct_change()
    F = pd.DataFrame({
        "close": c, "sma5": c.rolling(5).mean(), "sma20": c.rolling(20).mean(), "sma60": c.rolling(60).mean(),
        "ret1": r, "mom5": c.pct_change(5), "mom20": c.pct_change(20), "vol20": r.rolling(20).std(),
        "vol60": r.rolling(60).std(), "volume": v, "volume_sma20": v.rolling(20).mean(), "hl": hl,
    }).iloc[60:]
    y = (c.shift(-1) / c - 1.0).reindex(F.index).rename("label")
    return F, y


def _series_of(entry):
    if isinstance(entry, dict):
        vals = entry.get("values", entry.get("ic"))
        if vals is not None:
            return np.asarray(vals, dtype=float)
    return np.asarray(entry, dtype=float)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--method", required=True, choices=["pearson", "kendall"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--windows", default="63,252", help="逗號分隔窗長（原生根數，不經週期換算）")
    a = ap.parse_args()
    global WINDOWS
    WINDOWS = [int(w) for w in a.windows.split(",")]
    repo = Path(a.repo).resolve()
    sys.path.insert(0, str(repo))
    from momentum.Analysis.ic_engine import ICEngine  # noqa: E402

    F, y = _inputs(Path("/Users/louis/Desktop/quantitative_trading_system/data_cache/feature_klines/kline_cache.h5"))
    eng = ICEngine({})
    eng.compute_rolling_ic(F.iloc[:600], y.iloc[:600], WINDOWS, 1, a.method)  # numba 編譯暖身（不計時）
    rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    t0 = time.perf_counter()
    out = eng.compute_rolling_ic(F, y, WINDOWS, 1, a.method)
    wall = time.perf_counter() - t0
    rss1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    blob = json.dumps(out, default=float, sort_keys=True).encode("utf-8")
    size = len(blob)
    import hashlib

    out_sha = hashlib.sha256(blob).hexdigest()  # 平行與循序逐位元相同之比對用
    fn = stats.pearsonr if a.method == "pearson" else stats.kendalltau
    # 時間軸＝標籤有限之列（ic_engine.py compute_rolling_ic ④）；輸出第 k 個值＝於該軸上終點 w−1+k 之窗
    axis = np.isfinite(y.to_numpy(dtype=float))
    xv, yv = F.to_numpy(dtype=float)[axis], y.to_numpy(dtype=float)[axis]
    max_rel, max_abs_small, n_checked = 0.0, 0.0, 0
    for j, col in enumerate(F.columns):
        for w in WINDOWS:
            key = f"window_{w}"
            ser = out.get(col, {}).get(key)
            if ser is None:
                continue
            vals = _series_of(ser)
            ends = np.linspace(w - 1, len(yv) - 1, N_SAMPLE).astype(int)
            for e in ends:
                xs, ys = xv[e - w + 1:e + 1, j], yv[e - w + 1:e + 1]
                ok = np.isfinite(xs) & np.isfinite(ys)
                k = e - (w - 1)
                if ok.sum() != w or k >= vals.size or not np.isfinite(vals[k]):
                    continue
                ref = float(fn(xs, ys)[0])
                if not np.isfinite(ref):
                    continue
                n_checked += 1
                if abs(ref) < 1e-8:
                    max_abs_small = max(max_abs_small, abs(vals[k] - ref))
                else:
                    max_rel = max(max_rel, abs(vals[k] - ref) / abs(ref))
    rec = {"repo": str(repo), "method": a.method, "rows": int(len(F)), "features": int(F.shape[1]), "windows": WINDOWS,
           "wall_seconds": wall, "peak_rss_bytes_after": int(rss1), "peak_rss_bytes_before": int(rss0),
           "output_json_bytes": size, "output_sha256": out_sha,
           "numba_num_threads": __import__("os").environ.get("NUMBA_NUM_THREADS"), "precision": {"n_checked": n_checked, "max_rel_vs_scipy": max_rel,
                                                    "max_abs_vs_scipy_near_zero": max_abs_small}}
    Path(a.out).write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rec, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
