"""EVTLABEL `[A-2]`（SPEC ASSUME-2）：39,373 欄 × ≤165 列之 Mann-Whitney 向量化耗時。

否證觀測：實測 > 60 秒（SPEC 之否證門檻）。Task 3.7 之測試門檻為 120 秒（完整路徑）。
含 NaN 情境（10%）——R1 已知 clean 很快，NaN 逐欄才是風險。
"""
from __future__ import annotations

import sys
import time

import numpy as np
from scipy import stats

N_ROWS, N_COLS = 165, 39_373


def bench(label: str, x: np.ndarray, y: np.ndarray) -> float:
    t0 = time.time()
    pos, neg = x[y == 1], x[y == 0]
    res = stats.mannwhitneyu(pos, neg, axis=0, alternative="two-sided", nan_policy="omit")
    wall = time.time() - t0
    u = np.asarray(res.statistic, dtype="float64")
    p = np.asarray(res.pvalue, dtype="float64")
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    auc = u / (n_pos * n_neg)
    finite = int(np.isfinite(p).sum())
    print(f"{label}: {wall:.2f}s  u.shape={u.shape}  finite_p={finite}/{len(p)}  "
          f"auc[min,max]=[{np.nanmin(auc):.3f},{np.nanmax(auc):.3f}]")
    return wall


def main() -> int:
    rng = np.random.default_rng(20260910)
    y = np.zeros(N_ROWS, dtype=int)
    y[: 136] = 1                      # 與受理批同形：136 正 / 29 反
    rng.shuffle(y)

    x = rng.standard_normal((N_ROWS, N_COLS))
    w_clean = bench("clean", x, y)

    x_nan = x.copy()
    mask = rng.random(x_nan.shape) < 0.10
    x_nan[mask] = np.nan
    w_nan = bench("10%NaN", x_nan, y)

    # 植入 oracle：一欄完全可分 ⇒ AUC 必須 ≈ 1
    x_planted = x.copy()
    x_planted[:, 0] = y * 10.0 + rng.standard_normal(N_ROWS) * 0.01
    pos, neg = x_planted[y == 1, 0], x_planted[y == 0, 0]
    u0 = stats.mannwhitneyu(pos, neg, alternative="two-sided").statistic
    auc0 = u0 / (len(pos) * len(neg))
    print(f"planted-oracle: auc={auc0:.4f} rank_biserial={2 * auc0 - 1:.4f}")
    if not (auc0 > 0.99):
        print("ORACLE FAIL: 完全可分之欄 AUC 未達 0.99")
        return 1

    worst = max(w_clean, w_nan)
    print(f"WORST={worst:.2f}s  否證門檻=60s  Task3.7 測試門檻=120s")
    if worst > 60.0:
        print("A2 DISPROVED: 超過 60 秒")
        return 1
    print("A2 ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
