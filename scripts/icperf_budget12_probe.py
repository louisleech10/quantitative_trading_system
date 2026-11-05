"""ICPERF Task 0.4 ㊺ BUDGET-12：跨標的 EWC（A）與趨勢不重疊子序列推論（B）之每特徵耗時與記憶體。

SPEC §B ICPERF-BUDGET-12：冷（首個設計）、共用（同設計）、最壞（每特徵設計不同）三路；合成小規模量測後以實測外推
43 萬欄。受測者全為產品碼：A＝`ic_filter_orchestrator._compute_hac_on_ic_series`＋`_xsec_data_warning`；B＝
`TrendAnalyzer.analyze_trend`（推論＋精確 p＋資料不足警示）。每一量測點於獨立子行程執行（冷啟、記憶體互不污染）。

記憶體分三量（r109 委員：峰值不能兼作持久快取斜率）：
- `rss_current`＝psutil 目前 RSS（持久成長）；`rss_peak`＝ru_maxrss 高水位（暫存峰值）；
- `cache_bytes`／`cache_entries`＝產品行程內快取持有之 ndarray 位元組與條目數（A：`hac_ewc` 之虛無 p 值與中位數函數
  快取，鍵為有效長度 n ⇒ 種類有限、會飽和；B：另加 `trend_inference._DESIGN_CACHE`，有界 LRU 上限
  `DESIGN_CACHE_MAXSIZE`）。
每點於特徵數之幾何檢查點取樣，得成長曲線；外推：時間＝冷＋(N−1)×穩態每特徵；記憶體＝快取飽和上界（A：有效長度
種類數×每種位元組；B：LRU 上限×每設計位元組），不以高水位差分線性外推。

用法：
  python scripts/icperf_budget12_probe.py measure --path a|b --mode shared|worst --m M --features F   # 子行程，印一行 JSON
  python scripts/icperf_budget12_probe.py all --out handoffs/run_receipts/20261105-icperf-budget12.json
記憶體須獨占機器量（T4）；全程經 `scripts/run_watched.py` 背景執行。
"""

from __future__ import annotations

import argparse
import json
import platform
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import numpy as np

REPO = Path(__file__).resolve().parents[1]
TARGET_FEATURES = 430_000  # 使用者 2026-10-27「目前特徵生長全量開啟就有43萬欄位了」
ALPHA = 0.05
B_SPAN = 25  # B 共用設計之支撐長（w＝21、h＝5 之滾動 IC：w＋h−1）
B_HOLD = 0.8  # B 最壞路徑之持倉比例（多空 5 分位取 4、5 與 1、2 ⇒ 約 80%）
B_H = 5


def _rss_peak() -> int:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(r if sys.platform == "darwin" else r * 1024)  # macOS 位元組、Linux KiB


def _rss_current() -> int:
    import psutil

    return int(psutil.Process().memory_info().rss)


def _nbytes(obj) -> int:
    if isinstance(obj, np.ndarray):
        return int(obj.nbytes)
    if isinstance(obj, dict):
        return sum(_nbytes(v) for v in obj.values())
    if isinstance(obj, (tuple, list)):
        return sum(_nbytes(v) for v in obj)
    return 0


def _cache_stats(path: str) -> Dict[str, int]:
    from momentum.Analysis import hac_ewc as he

    out = {"hac_null_entries": len(he._NULL_PVALUE_CACHE), "hac_null_bytes": _nbytes(he._NULL_PVALUE_CACHE),
           "hac_median_entries": len(he._LS_MEDIAN_CACHE), "hac_median_bytes": _nbytes(he._LS_MEDIAN_CACHE)}
    if path == "b":
        from momentum.Analysis import trend_inference as ti

        out["design_entries"] = len(ti._DESIGN_CACHE)
        out["design_bytes"] = _nbytes(dict(ti._DESIGN_CACHE))
        out["design_maxsize"] = int(ti.DESIGN_CACHE_MAXSIZE)
    out["cache_bytes"] = sum(v for k, v in out.items() if k.endswith("_bytes"))
    return out


def _ar1(rng: np.random.Generator, n: int, phi: float = 0.5) -> np.ndarray:
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    s = np.sqrt(1 - phi * phi)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + s * e[t]
    return x


def _checkpoints(features: int) -> List[int]:
    pts, k = [], 1
    while k < features:
        pts.append(k)
        k *= 2
    return sorted(set(pts + [features]))


def measure(path: str, mode: str, m: int, features: int) -> dict:
    rng = np.random.Generator(np.random.PCG64(20261105))
    distinct = None
    if path == "a":
        from momentum.Analysis.ic_filter_orchestrator import _compute_hac_on_ic_series, _xsec_data_warning

        # 最壞：每特徵有效長度不同，種類數 K＝min(m//2, 特徵數)（長度種類有限 ⇒ 快取鍵飽和；K 種之後循環）
        distinct = 1 if mode == "shared" else max(1, min(m // 2, features))

        def one(i: int) -> dict:
            n = m if mode == "shared" else m - (i % distinct)
            z = _ar1(rng, n) * 0.05
            hac = _compute_hac_on_ic_series(z, horizon=1)
            return _xsec_data_warning(z, hac, ALPHA)
    else:
        import pandas as pd

        from momentum.Analysis.ic_config_schema import TrendAnalysisConfig
        from momentum.Analysis.trend_analyzer import TrendAnalyzer

        cfg = TrendAnalysisConfig().model_dump()
        analyzer = TrendAnalyzer(cfg)
        if mode == "shared":
            L = m * B_SPAN
            start = np.arange(L, dtype=np.int64)
            sup = (start, start + B_SPAN - 1)

            def one(i: int) -> dict:
                return analyzer.analyze_trend(pd.Series(_ar1(rng, L, 0.95) * 0.1), "ic", support=sup)
        else:
            L = int(np.ceil(m * B_H / B_HOLD))

            def one(i: int) -> dict:  # ls_spread 型：每特徵持倉點不同 ⇒ 選取設計不同
                y = rng.standard_normal(L)
                y[rng.random(L) > B_HOLD] = np.nan
                return analyzer.analyze_trend(pd.Series(y), "ls_spread", overlap_window=B_H, select_finite_only=True)
    rss_import_cur, rss_import_peak = _rss_current(), _rss_peak()
    times: List[float] = []
    points: List[int] = []
    curve: List[dict] = []
    marks = set(_checkpoints(features))
    t_start = time.perf_counter()
    for i in range(features):
        t0 = time.perf_counter()
        out = one(i)
        times.append(time.perf_counter() - t0)
        points.append(int(out.get("subsample_points") or 0) if path == "b" else 0)
        if i + 1 in marks:
            curve.append({"features_done": i + 1, "elapsed_s": time.perf_counter() - t_start,
                          "rss_current_bytes": _rss_current(), "rss_peak_bytes": _rss_peak(), **_cache_stats(path)})
    t = np.asarray(times)
    tail = t[len(t) // 2:] if t.size > 1 else t  # 穩態：後半段（A 最壞含循環後之命中）
    return {"path": path, "mode": mode, "m": m, "features": features, "distinct_lengths": distinct,
            "first_s": float(t[0]), "rest_mean_s": float(t[1:].mean()) if t.size > 1 else None,
            "steady_mean_s": float(tail.mean()), "steady_median_s": float(np.median(tail)),
            "total_s": float(t.sum()), "rss_after_import_current_bytes": rss_import_cur,
            "rss_after_import_peak_bytes": rss_import_peak, "curve": curve,
            "subsample_points_median": float(np.median(points)) if path == "b" else None}


#: 量測點（A：m＝刪期後有效點數，取測試段可達：1h 主檔 20,352 根之 20%＝4,070；B：m＝目標子序列點數，實際選取
#: 點數記於 subsample_points_median）。B 最壞 m＝15 跑 300 特徵以越過 LRU 上限 256 觀察飽和。
GRID: List[dict] = (
    [{"path": "a", "mode": "shared", "m": m, "features": f} for m, f in ((250, 400), (1000, 400), (4070, 200))]
    + [{"path": "a", "mode": "worst", "m": m, "features": f} for m, f in ((250, 400), (1000, 800), (4070, 600))]
    + [{"path": "b", "mode": "shared", "m": m, "features": f} for m, f in ((15, 60), (40, 60), (150, 30), (400, 12))]
    + [{"path": "b", "mode": "worst", "m": m, "features": f}
       for m, f in ((15, 300), (40, 8), (150, 5), (400, 3), (1000, 2))]
)


def _child(cell: dict) -> dict:
    cmd = [sys.executable, str(Path(__file__).resolve()), "measure", "--path", cell["path"], "--mode", cell["mode"],
           "--m", str(cell["m"]), "--features", str(cell["features"])]
    res = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"{cell} rc={res.returncode}\n{res.stderr[-2000:]}")
    line = [ln for ln in res.stdout.splitlines() if ln.startswith("{")][-1]
    return json.loads(line)


def _per_unit_bytes(row: dict, entries_key: str, bytes_key: str) -> float:
    last = row["curve"][-1]
    return float(last[bytes_key]) / max(1, int(last[entries_key]))


def _hac_cache_bound_bytes(m: int) -> int:
    """A 型快取（`hac_ewc`，鍵為 n 幾何節點）之飽和上界：有效長度 ≤ m 之節點數 ×（φ 網格點數＋參照）× R × 8 位元組
    （虛無 p 值）＋節點數 × φ 網格點數 × 8（中位數函數）。節點為 round(8·1.05^k)，與實際 n 種類數無關。"""
    from momentum.Analysis import hac_ewc as he

    nodes, k = set(), 0
    while True:
        v = he._node_value(k)
        if v > m:
            break
        nodes.add(v)
        k += 1
    nodes.add(he.node_bracket(m)[1])
    g = len(he.PHI_GRID)
    return len(nodes) * ((g + 1) * he.WARNING_SIM_REPLICATIONS * 8 + g * 8)


def _extrapolate(rows: List[dict]) -> Dict[str, dict]:
    """43 萬欄外推（每量測點各一列）：時間＝冷＋(N−1)×穩態每特徵均值；快取記憶體＝飽和上界——A：`hac_ewc` 節點快取
    上界（:func:`_hac_cache_bound_bytes`）；B：LRU 上限×每設計位元組。B 之 N 為入選趨勢之特徵數（≤ 43 萬，以 43 萬為
    上界）。"""
    out: Dict[str, dict] = {}
    for r in rows:
        last = r["curve"][-1]
        entry = {
            "per_feature_steady_s": r["steady_mean_s"], "cold_first_s": r["first_s"],
            "extrapolated_total_s": r["first_s"] + (TARGET_FEATURES - 1) * r["steady_mean_s"],
            "extrapolated_total_hours": (r["first_s"] + (TARGET_FEATURES - 1) * r["steady_mean_s"]) / 3600.0,
            "hac_cache_bytes_observed": last["hac_null_bytes"] + last["hac_median_bytes"],
            "hac_cache_saturation_bound_bytes": _hac_cache_bound_bytes(int(r["m"])) if r["path"] == "a" else None,
            "rss_current_last_bytes": last["rss_current_bytes"], "rss_peak_last_bytes": last["rss_peak_bytes"],
        }
        if r["path"] == "b":
            per_design = _per_unit_bytes(r, "design_entries", "design_bytes")
            entry["design_bytes_per_entry"] = per_design
            entry["design_cache_saturation_bound_bytes"] = per_design * last["design_maxsize"]
            entry["subsample_points_median"] = r["subsample_points_median"]
        out[f'{r["path"]}_{r["mode"]}_m{r["m"]}'] = entry
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m_ = sub.add_parser("measure")
    m_.add_argument("--path", choices=("a", "b"), required=True)
    m_.add_argument("--mode", choices=("shared", "worst"), required=True)
    m_.add_argument("--m", type=int, required=True)
    m_.add_argument("--features", type=int, required=True)
    a_ = sub.add_parser("all")
    a_.add_argument("--out", required=True)
    args = ap.parse_args()
    # 母行程之 `_extrapolate` 亦 import 產品模組（`_hac_cache_bound_bytes`）⇒ 兩子命令皆須
    sys.path.insert(0, str(REPO))
    if args.cmd == "measure":
        print(json.dumps(measure(args.path, args.mode, args.m, args.features), ensure_ascii=False), flush=True)
        return 0
    rows = []
    for cell in GRID:
        r = _child(cell)
        rows.append(r)
        print(json.dumps({k: v for k, v in r.items() if k != "curve"}, ensure_ascii=False), flush=True)
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True).stdout.strip()
    receipt = {
        "budget_id": "ICPERF-BUDGET-12", "spec_path": "docs/ICPERF_SPEC.md", "head": git,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hardware": {"machine": platform.machine(), "platform": platform.platform()},
        "target_features": TARGET_FEATURES, "alpha": ALPHA,
        "method": ("每量測點獨立子行程；首特徵＝冷（含建快取／JIT），穩態＝後半段特徵均值；記憶體分 psutil 目前 RSS、"
                   "ru_maxrss 高水位與產品快取持有之 ndarray 位元組，於幾何檢查點取樣；外推用快取飽和上界"),
        "rows": rows, "extrapolation": _extrapolate(rows),
    }
    out = REPO / args.out
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(REPO)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
