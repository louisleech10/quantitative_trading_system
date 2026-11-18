#!/usr/bin/env python3
"""gap2_budget_bench.py — GAP-2 預算基準（SPEC §G R4 CODEX-R4-P1-03；IC_QUANT_GAP_REGISTRY G2-R7 拆出）。

`budget_bench(n, k, m)`：合成 k 個 survivors＋m 個 removed、n 列（seed 20260818），跑 `compute_marginal_ic`＋
`combine_factors`，以 `fit_projection` 之獨立 spy 計每次設計矩陣欄數；另跑兩個超預算案（max_survivors_for_loo＝k−1、
max_removed_candidates＝m−1）。回傳計數與觀測值（wall、ru_maxrss；觀測資料無通過閾值——R7 CODEX-R7-P1-03）。

- 測試（`tests/momentum/Analysis/test_gap2_golden.py::test_budget_bench_receipt`）以小規模（n＝2,000、k＝m＝20）呼叫，
  斷言計數語意（n_regressions＝2k＋m＝spy 次數、欄數上界 k、超預算視角零 fit）——計數與預算邊界與規模無關。
- 全規模（SPEC 原值 n＝20,000、k＝m＝200）之 wall／RSS 觀測改由本腳本手動跑（TESTSEL I10：原在測試內每次約 146 秒，
  且測試把收據寫進 repo）：
    venv/bin/python scripts/gap2_budget_bench.py --write-receipt
  寫 `handoffs/run_receipts/<UTC>-gap2-budget-bench.log`。何時須重跑：`momentum/Analysis/marginal_ic.py` 或
  `momentum/Analysis/factor_combiner.py` 改動（影響回歸次數或單次成本）時。
"""
from __future__ import annotations

import argparse
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from momentum.Analysis import marginal_ic as mic  # noqa: E402
from momentum.Analysis.factor_combiner import combine_factors  # noqa: E402
from momentum.Analysis.marginal_ic import MarginalICParams, compute_marginal_ic  # noqa: E402

SEED = 20260818
FULL_SCALE = {"n": 20000, "k": 200, "m": 200}


def bench_data(n: int, k: int, m: int):
    """合成資料（同原測試 `_bench_data` 之生成式，規模參數化）：前 60% 為 train。"""
    rng = np.random.default_rng(SEED)
    X = rng.standard_normal((n, k + m))
    cols = [f"s{i:03d}" for i in range(k)] + [f"r{i:03d}" for i in range(m)]
    y = 0.02 * X[:, :k].sum(axis=1) + rng.standard_normal(n)
    df = pd.DataFrame(X, columns=cols)
    tr = np.zeros(n, dtype=bool)
    tr[: int(n * 0.6)] = True
    return df, pd.Series(y), tr, ~tr, cols[:k], cols[k:]


def budget_bench(n: int, k: int, m: int) -> Dict[str, Any]:
    """跑主案與兩超預算案；回傳計數（spy 與 counter）與觀測值。spy 以替換模組屬性為之，結束必還原。"""
    df, y, tr, te, surv, removed = bench_data(n, k, m)
    calls: List[int] = []
    real = mic.fit_projection

    def spy(z_target, z_basis):
        calls.append(int(np.asarray(z_basis).shape[1]) if np.asarray(z_basis).ndim == 2 else 0)
        return real(z_target, z_basis)

    mic.fit_projection = spy
    try:
        p = MarginalICParams(n_bootstrap=1, block_len=5, max_survivors_for_loo=k, max_removed_candidates=m)
        t0 = time.time()
        res = compute_marginal_ic(df, y, train_mask=tr, test_mask=te, survivors=surv, extra_candidates=removed,
                                  params=p, fit_scope="train")
        comp = combine_factors(df, y, train_mask=tr, test_mask=te, survivors=surv, params=p, fit_scope="train")
        wall = time.time() - t0
        main_calls = list(calls)
        calls.clear()
        over1 = compute_marginal_ic(df, y, train_mask=tr, test_mask=te, survivors=surv, extra_candidates=[],
                                    params=MarginalICParams(n_bootstrap=1, max_survivors_for_loo=k - 1,
                                                            max_removed_candidates=m),
                                    fit_scope="train")
        spy_over1 = len(calls)
        calls.clear()
        over2 = compute_marginal_ic(df, y, train_mask=tr, test_mask=te, survivors=surv, extra_candidates=removed,
                                    params=MarginalICParams(n_bootstrap=1, max_survivors_for_loo=k,
                                                            max_removed_candidates=m - 1),
                                    fit_scope="train")
        spy_over2 = len(calls)
    finally:
        mic.fit_projection = real
    return {
        "n": n, "k": k, "m": m, "seed": SEED,
        "n_regressions": int(res.n_regressions), "spy_main": len(main_calls),
        "max_design_cols_main": max(main_calls) if main_calls else None,
        "combine_status": comp.status, "composite_ic": comp.composite_ic,
        "over1_spy": spy_over1, "over1_n_regressions": int(over1.n_regressions),
        "over2_spy": spy_over2, "over2_n_regressions": int(over2.n_regressions),
        "wall_time_s": wall, "ru_maxrss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def receipt_text(r: Dict[str, Any], ts: str) -> str:
    return "\n".join([
        f"[gap2-budget-bench] ts={ts} n={r['n']} k={r['k']} m={r['m']} seed={r['seed']} n_bootstrap=1",
        f"n_regressions={r['n_regressions']} fit_projection_spy={r['spy_main']} "
        f"max_design_cols={r['max_design_cols_main']}(main run: ≤{r['k']})",
        f"over_budget_survivors(max_survivors_for_loo={r['k'] - 1}): spy={r['over1_spy']} "
        f"n_regressions={r['over1_n_regressions']}",
        f"over_budget_removed(max_removed_candidates={r['m'] - 1}): spy={r['over2_spy']} "
        f"n_regressions={r['over2_n_regressions']}",
        f"wall_time_s={r['wall_time_s']:.1f} ru_maxrss={r['ru_maxrss']} （觀測資料；無通過閾值——R7 CODEX-R7-P1-03；"
        f"OOM 保護宣稱僅計數上界）",
        f"composite_ic={r['composite_ic']}",
    ]) + "\n"


def write_receipt(r: Dict[str, Any], out_dir: Path, ts: Optional[str] = None) -> Path:
    ts = ts or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = Path(out_dir) / f"{ts}-gap2-budget-bench.log"
    path.write_text(receipt_text(r, ts), encoding="utf-8")
    return path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write-receipt", action="store_true", help="寫 handoffs/run_receipts/<UTC>-gap2-budget-bench.log")
    args = ap.parse_args(argv)
    r = budget_bench(**FULL_SCALE)
    k, m = FULL_SCALE["k"], FULL_SCALE["m"]
    ok = (r["n_regressions"] == r["spy_main"] == 2 * k + m and r["max_design_cols_main"] <= k
          and r["combine_status"] == "ok" and r["over1_spy"] == 0 == r["over1_n_regressions"]
          and r["over2_spy"] == 2 * k == r["over2_n_regressions"])
    sys.stdout.write(receipt_text(r, "-"))
    if args.write_receipt:
        sys.stdout.write(f"receipt: {write_receipt(r, REPO / 'handoffs' / 'run_receipts')}\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
