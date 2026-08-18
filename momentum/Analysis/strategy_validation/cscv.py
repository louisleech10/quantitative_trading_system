"""Task 4.1 — CSCV 分割器（`票 GAP-1/C3`）：S 塊組合 lazy iterator；雙重預算 fail-closed。

SPEC ref：Task 4.1。Bailey et al. (2015) *The Probability of Backtest Overfitting* Algorithm 2.3 之組合切分：
把 T 個觀測切成 S 個連續塊，取 S/2 塊為 IS、其餘為 OOS，枚舉 C(S, S/2) 條 path（**不隨機抽樣**、不回傳 list）。
"""

from __future__ import annotations

import itertools
import math
from typing import Iterator, List, Tuple

import numpy as np

_MAX_PATHS = 20_000
_MAX_ELEMENTS = 20_000_000


class CscvBudgetExceeded(RuntimeError):
    """path 數或 path×n_obs 超過預算（防 OOM；在建立 generator 前 raise）。"""


def cscv_path_count(s_blocks: int) -> int:
    """`C(S, S/2)`；S 須為 ≥2 之偶數。"""
    if not isinstance(s_blocks, int) or isinstance(s_blocks, bool) or s_blocks < 2 or s_blocks % 2 != 0:
        raise ValueError(f"s_blocks 須為 >=2 之偶數，得到 {s_blocks!r}")
    return math.comb(s_blocks, s_blocks // 2)


def _block_bounds(n_obs: int, s_blocks: int) -> List[np.ndarray]:
    """塊邊界：`base=n_obs//S; rem=n_obs%S`；前 `rem` 塊長 `base+1`，其餘 `base`。"""
    base, rem = divmod(n_obs, s_blocks)
    blocks: List[np.ndarray] = []
    start = 0
    for i in range(s_blocks):
        length = base + (1 if i < rem else 0)
        blocks.append(np.arange(start, start + length))
        start += length
    return blocks


def iter_cscv_splits(*, n_obs: int, s_blocks: int) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """逐 path yield `(is_idx, oos_idx)`（升冪索引陣列；IS∪OOS＝全索引、交集空）。

    Raises:
        ValueError: `s_blocks` 奇數／<2／`s_blocks > n_obs`／`n_obs < 1`。
        CscvBudgetExceeded: `path_count > 20000` 或 `path_count * n_obs > 20_000_000`（generator 建立前）。
    """
    path_count = cscv_path_count(s_blocks)
    if not isinstance(n_obs, int) or isinstance(n_obs, bool) or n_obs < 1:
        raise ValueError(f"n_obs 須為 >=1 之 int，得到 {n_obs!r}")
    if s_blocks > n_obs:
        raise ValueError(f"s_blocks={s_blocks} > n_obs={n_obs}")
    if path_count > _MAX_PATHS or path_count * n_obs > _MAX_ELEMENTS:
        raise CscvBudgetExceeded(
            f"CSCV 預算超限：path_count={path_count}（上限 {_MAX_PATHS}）、"
            f"path_count*n_obs={path_count * n_obs}（上限 {_MAX_ELEMENTS}）"
        )
    return _iter_splits(n_obs, s_blocks)


def _iter_splits(n_obs: int, s_blocks: int) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    blocks = _block_bounds(n_obs, s_blocks)
    all_blocks = set(range(s_blocks))
    for combo in itertools.combinations(range(s_blocks), s_blocks // 2):
        is_idx = np.concatenate([blocks[i] for i in combo])
        oos_idx = np.concatenate([blocks[i] for i in sorted(all_blocks - set(combo))])
        yield is_idx, oos_idx
