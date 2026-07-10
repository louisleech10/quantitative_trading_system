"""Circular block bootstrap 驗證腿（僅 tests/，不進 production）。

對 (x, y) 對同步重抽，每輪重算 Spearman IC（rank corr 貢獻 mean(z)），
估計 H0: IC=0 下的雙尾 p，供與 HAC kernel p 對照（D-B / Task 1.3）。
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from scipy import stats


def _contribution_z(x: np.ndarray, y: np.ndarray) -> Optional[np.ndarray]:
    """u=zscore(rank(x),ddof=1)*zscore(rank(y),ddof=1)；rank 退化回 None。"""
    if x.size < 2 or x.size != y.size:
        return None
    rx = stats.rankdata(x, method="average").astype(float)
    ry = stats.rankdata(y, method="average").astype(float)
    sx = float(np.std(rx, ddof=1))
    sy = float(np.std(ry, ddof=1))
    if sx == 0.0 or sy == 0.0 or not np.isfinite(sx) or not np.isfinite(sy):
        return None
    u = (rx - float(np.mean(rx))) / sx
    v = (ry - float(np.mean(ry))) / sy
    return u * v


def _spearman_ic(x: np.ndarray, y: np.ndarray) -> Optional[float]:
    """對當前 (x,y) 重算 Spearman IC = mean(z)；退化回 None。"""
    z = _contribution_z(x, y)
    if z is None:
        return None
    return float(np.mean(z))


def circular_block_indices(
    n: int, block: int, rng: np.random.Generator
) -> np.ndarray:
    """Circular block bootstrap 索引，長度 n。"""
    if n < 1:
        return np.array([], dtype=int)
    block = max(1, int(block))
    starts = rng.integers(0, n, size=int(math.ceil(n / block)))
    idx: list[int] = []
    for s in starts:
        for k in range(block):
            idx.append(int((int(s) + k) % n))
            if len(idx) >= n:
                return np.asarray(idx[:n], dtype=int)
    return np.asarray(idx[:n], dtype=int)


def block_bootstrap_ic_pvalue(
    x: np.ndarray,
    y: np.ndarray,
    horizon: int,
    *,
    n_bootstrap: int = 2000,
    seed: int = 0,
) -> dict:
    """Circular block bootstrap 雙尾 p（H0: Spearman IC = 0）。

    D-B 凍結：對 (x,y) **成對**重抽（同步 circular block indices 取
    x[idx], y[idx]），每次重算 Spearman IC，得 IC 分布；雙尾 p 由置中
    IC 分布對 observed IC 計算（null-imposed）。

    block = max(h, ceil(n**(1/3)))；B 預設 2000。

    Returns:
        dict: observed_ic, p_value, block, n, n_bootstrap, ic_distribution,
        skip / skip_reason。n < 2*block 或 rank 退化時 skip=True。
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    n = int(x.size)
    h = max(1, int(horizon))
    block = max(h, int(math.ceil(n ** (1.0 / 3.0)))) if n > 0 else h

    empty = {
        "observed_ic": np.nan,
        "observed_mean": np.nan,  # 別名相容舊鍵
        "p_value": np.nan,
        "block": int(block),
        "n": n,
        "n_bootstrap": int(n_bootstrap),
        "ic_distribution": np.array([], dtype=float),
        "skip": True,
        "skip_reason": "",
    }

    if n < 2:
        empty["skip_reason"] = "n<2"
        return empty
    if n < 2 * block:
        empty["skip_reason"] = "n<2*block"
        return empty

    obs_ic = _spearman_ic(x, y)
    if obs_ic is None:
        empty["skip_reason"] = "rank_degenerate"
        return empty

    rng = np.random.default_rng(int(seed))
    boot_ics = np.empty(int(n_bootstrap), dtype=float)
    for b in range(int(n_bootstrap)):
        idx = circular_block_indices(n, block, rng)
        # 成對重抽後每輪重算 rank corr（非對固定 z 重抽）
        ic_b = _spearman_ic(x[idx], y[idx])
        boot_ics[b] = float(ic_b) if ic_b is not None else np.nan

    finite = boot_ics[np.isfinite(boot_ics)]
    if finite.size == 0:
        empty["skip_reason"] = "rank_degenerate"
        empty["observed_ic"] = obs_ic
        empty["observed_mean"] = obs_ic
        return empty

    # null-imposed：置中 IC 分布，雙尾 p 對 |observed IC|
    centered = finite - obs_ic
    ge = int(np.sum(np.abs(centered) >= abs(obs_ic)))
    p_value = float((1 + ge) / (int(finite.size) + 1))

    return {
        "observed_ic": obs_ic,
        "observed_mean": obs_ic,
        "p_value": p_value,
        "block": int(block),
        "n": n,
        "n_bootstrap": int(n_bootstrap),
        "ic_distribution": boot_ics,
        "skip": False,
        "skip_reason": "",
    }
