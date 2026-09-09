"""EVTLABEL ASSUME-2／R2 D2 成本探針：Mann-Whitney 向量化 + 20 次置亂於 39,373 欄之耗時。

用法：PYTHONPATH=. venv/bin/python handoffs/20260910-probe-mw-bench.py [n_rows=31] [n_cols=39373] [n_shuffles=20]
印 receipt：single_mw_seconds、shuffles_seconds、nan_path_seconds（10% 欄含 NaN）；rc=0 ⇔ 全部 < 120s。
合成矩陣只用於**耗時**（統計 oracle 另在 tests；此處不做任何正確性主張）。
"""
from __future__ import annotations

import sys
import time

import numpy as np
from scipy.stats import mannwhitneyu

n_rows = int(sys.argv[1]) if len(sys.argv) > 1 else 31
n_cols = int(sys.argv[2]) if len(sys.argv) > 2 else 39373
n_sh = int(sys.argv[3]) if len(sys.argv) > 3 else 20
rng = np.random.default_rng(20260910)
X = rng.standard_normal((n_rows, n_cols))
y = (rng.random(n_rows) < 0.55).astype(int)
if y.sum() == 0 or y.sum() == n_rows:
    y[0], y[1] = 1, 0


def mw(Xm: np.ndarray, ym: np.ndarray) -> np.ndarray:
    r = mannwhitneyu(Xm[ym == 1], Xm[ym == 0], alternative="two-sided", method="auto", axis=0)
    return r.pvalue


t0 = time.perf_counter(); p = mw(X, y); t_single = time.perf_counter() - t0
t0 = time.perf_counter()
for i in range(n_sh):
    ys = rng.permutation(y)
    if ys.sum() in (0, n_rows):
        continue
    mw(X, ys)
t_sh = time.perf_counter() - t0
# NaN 路徑：10% 欄逐欄
Xn = X.copy(); cols = rng.choice(n_cols, n_cols // 10, replace=False)
for c in cols:
    Xn[rng.integers(0, n_rows), c] = np.nan
t0 = time.perf_counter()
clean = ~np.isnan(Xn).any(axis=0)
mw(Xn[:, clean], y)
for c in np.where(~clean)[0]:
    m = ~np.isnan(Xn[:, c]); yy = y[m]
    if 0 < yy.sum() < m.sum():
        mannwhitneyu(Xn[m, c][yy == 1], Xn[m, c][yy == 0], alternative="two-sided", method="auto")
t_nan = time.perf_counter() - t0
print(f"n_rows={n_rows} n_cols={n_cols} n_shuffles={n_sh} single_mw_seconds={t_single:.3f} "
      f"shuffles_seconds={t_sh:.3f} nan_path_seconds={t_nan:.3f} finite_p={np.isfinite(p).all()}")
sys.exit(0 if max(t_single, t_sh, t_nan) < 120 else 1)
