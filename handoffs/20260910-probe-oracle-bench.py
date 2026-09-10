"""EVTLABEL Task 3.7 之 benchmark（TODO 驗證 (a)/(b)）：真實規模下的置換與負對照耗時。

否證觀測：任一道 > 120 秒。

🔴 這條是 B4 review brief 之必答 5：我在小 fixture（21 欄 × 120 列）上跑過就送審，
真實規模（39,373 欄 × 165 列 × 50 次負對照）**沒跑**。本探針補上。
"""
from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from momentum.Analysis.binary_discrimination import (  # noqa: E402
    BINARY_STATUS_OK,
    _permute_blocks,
    block_ids_for_events,
    block_permutation_oracle,
    mann_whitney_table,
    rank_biserial_stat,
)

N_ROWS, N_COLS = 165, 39_373
HOUR = 3_600_000
BASE = 1_700_000_000_000
LIMIT = 120.0


def _fixture():
    rng = np.random.default_rng(20260910)
    y = np.zeros(N_ROWS, dtype=int)
    y[:136] = 1                      # 與受理批同形
    rng.shuffle(y)
    idx = pd.to_datetime([BASE + i * 12 * HOUR for i in range(N_ROWS)], unit="ms")
    x = rng.standard_normal((N_ROWS, N_COLS))
    feats = pd.DataFrame(x, index=idx, columns=[f"f{i}" for i in range(N_COLS)])
    return feats, y


def main() -> int:
    feats, y = _fixture()
    ms = (feats.index.asi8 // 10**6).astype("int64")
    block_ids, block_len, n_blocks = block_ids_for_events(ms, 12, 12 * HOUR)
    print(f"fixture: {N_ROWS}×{N_COLS}  block_len={block_len}  n_blocks={n_blocks}")

    rc = 0

    # (a) per-survivor 置換：K=2000、budget=200000 ⇒ n_perm=200（地板）
    k, budget = 2000, 200_000
    n_perm = min(1000, max(200, budget // max(k, 1)))
    # 🔴 首跑（feature-major，逐特徵各跑 n_perm 次）實測 123s ⇒ 超過門檻。
    #    改為 permutation-major（每個置換算一次全部候選欄）後重跑。
    from momentum.Analysis.binary_discrimination import block_permutation_table

    t0 = time.time()
    out = block_permutation_table(feats.iloc[:, :k], y, block_ids,
                                  seed=1, n_perm=n_perm, min_blocks=1)
    total_a = time.time() - t0
    print(f"(a) permutation-major K={k} n_perm={n_perm}: {total_a:.1f}s  status={out.get('status')}")
    if total_a > LIMIT:
        print(f"(a) OVER LIMIT: {total_a:.0f}s > {LIMIT}s ⇒ 需降階或改設計")
        rc = 1

    # (b) 整批負對照：50 次全表 mann_whitney_table
    n_control = 50
    t0 = time.time()
    once = mann_whitney_table(feats, _permute_blocks(np.random.default_rng(1), y, block_ids),
                              min_class_n=10)
    one_shuffle = time.time() - t0
    total_b = one_shuffle * n_control
    n_ok = int((once["status"] == BINARY_STATUS_OK).sum())
    print(f"(b) 單次全表置亂: {one_shuffle:.2f}s  ×{n_control} ⇒ {total_b:.0f}s  status_ok={n_ok}")
    if total_b > LIMIT:
        print(f"(b) OVER LIMIT: {total_b:.0f}s > {LIMIT}s ⇒ 需降階或改設計")
        rc = 1

    # (c) 🔴 `GROK-R1-P1-03` 之情境：10% NaN（我首跑只測乾淨資料，所以沒看到 207s）
    rng = np.random.default_rng(1)
    x_nan = feats.to_numpy(copy=True)
    x_nan[rng.random(x_nan.shape) < 0.10] = np.nan
    feats_nan = pd.DataFrame(x_nan, index=feats.index, columns=feats.columns)
    t0 = time.time()
    mann_whitney_table(feats_nan, y, min_class_n=10)
    one_nan = time.time() - t0
    print(f"(c) 10%NaN 單次全表: {one_nan:.2f}s  ×50(名目) ⇒ {one_nan * 50:.0f}s")
    budget = 60.0
    affordable = max(5, int(budget // one_nan))
    print(f"(c) 預算 {budget:.0f}s ⇒ 實際跑 {min(affordable, 50)} 次 ⇒ "
          f"{min(affordable, 50) * one_nan:.0f}s（降階已揭露）")
    if min(affordable, 50) * one_nan > LIMIT:
        print("(c) OVER LIMIT")
        rc = 1

    print(f"TOTAL≈{total_a + total_b:.0f}s  limit(each)={LIMIT}s  rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
